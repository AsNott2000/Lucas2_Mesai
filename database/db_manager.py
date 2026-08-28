import aiosqlite
import asyncio
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from config import config

class DatabaseManager:
    """Asenkron SQLite veritabanı işlemlerini yöneten sınıf."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or config.DATABASE_PATH
        self._lock = asyncio.Lock()

    async def init_db(self) -> None:
        """Gerekli tabloları, indeksleri ve migrasyonları oluşturur."""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        
        async with aiosqlite.connect(self.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            
            # Mesailer tablosu
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS shifts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    user_name TEXT NOT NULL,
                    start_time TEXT NOT NULL,
                    end_time TEXT,
                    duration_seconds INTEGER DEFAULT 0,
                    status TEXT NOT NULL DEFAULT 'ACTIVE',
                    note TEXT,
                    last_verified_at TEXT,
                    verification_sent_at TEXT,
                    created_at TEXT DEFAULT (datetime('now'))
                )
            """)

            # Ayarlar ve Panel ID'leri tablosu
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    guild_id INTEGER NOT NULL,
                    key TEXT NOT NULL,
                    value TEXT NOT NULL,
                    updated_at TEXT DEFAULT (datetime('now')),
                    PRIMARY KEY (guild_id, key)
                )
            """)
            
            # Migrasyon: Eski veritabanlarında eksik sütunları kontrol et ve ekle
            async with conn.execute("PRAGMA table_info(shifts)") as cursor:
                columns = [row["name"] for row in await cursor.fetchall()]
                if "last_verified_at" not in columns:
                    await conn.execute("ALTER TABLE shifts ADD COLUMN last_verified_at TEXT")
                if "verification_sent_at" not in columns:
                    await conn.execute("ALTER TABLE shifts ADD COLUMN verification_sent_at TEXT")

            # Performans için indeksler
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_shifts_user_active 
                ON shifts (guild_id, user_id, status)
            """)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_shifts_guild_status 
                ON shifts (guild_id, status)
            """)
            await conn.commit()

    # ==========================================
    # AYARLAR (SETTINGS) YÖNETİMİ
    # ==========================================

    async def get_setting(self, guild_id: int, key: str) -> Optional[str]:
        """Sunucuya özel kaydedilmiş bir ayarı döndürür."""
        async with aiosqlite.connect(self.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            async with conn.execute(
                "SELECT value FROM settings WHERE guild_id = ? AND key = ?",
                (guild_id, key)
            ) as cursor:
                row = await cursor.fetchone()
                return str(row["value"]) if row else None

    async def set_setting(self, guild_id: int, key: str, value: str) -> None:
        """Sunucuya özel bir ayar kaydeder veya günceller."""
        async with self._lock:
            async with aiosqlite.connect(self.db_path) as conn:
                await conn.execute(
                    """
                    INSERT INTO settings (guild_id, key, value, updated_at)
                    VALUES (?, ?, ?, datetime('now'))
                    ON CONFLICT(guild_id, key) DO UPDATE SET
                        value = excluded.value,
                        updated_at = datetime('now')
                    """,
                    (guild_id, key, str(value))
                )
                await conn.commit()

    async def get_all_settings(self, guild_id: int) -> Dict[str, str]:
        """Sunucunun tüm kayıtlı ayarlarını sözlük olarak döndürür."""
        async with aiosqlite.connect(self.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            async with conn.execute(
                "SELECT key, value FROM settings WHERE guild_id = ?",
                (guild_id,)
            ) as cursor:
                rows = await cursor.fetchall()
                return {row["key"]: row["value"] for row in rows}

    # ==========================================
    # MESAİ VE VARDİYA İŞLEMLERİ
    # ==========================================

    async def get_active_shift(self, guild_id: int, user_id: int) -> Optional[Dict[str, Any]]:
        """Kullanıcının belirtilen sunucudaki aktif mesaisini döndürür."""
        async with aiosqlite.connect(self.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            async with conn.execute(
                """
                SELECT * FROM shifts 
                WHERE guild_id = ? AND user_id = ? AND status = 'ACTIVE'
                ORDER BY id DESC LIMIT 1
                """,
                (guild_id, user_id)
            ) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None

    async def start_shift(
        self, guild_id: int, user_id: int, user_name: str, start_time: Optional[datetime] = None
    ) -> Tuple[bool, Optional[Dict[str, Any]], str]:
        """
        Yeni bir mesai başlatır. 
        Kullanıcının zaten açık bir mesaisi varsa engeller ve False döner.
        """
        if start_time is None:
            start_time = datetime.now(timezone.utc)
        elif start_time.tzinfo is None:
            start_time = start_time.replace(tzinfo=timezone.utc)

        start_time_iso = start_time.isoformat()

        async with self._lock:
            active = await self.get_active_shift(guild_id, user_id)
            if active:
                return False, active, "Zaten devam eden aktif bir mesainiz bulunmaktadır."

            async with aiosqlite.connect(self.db_path) as conn:
                conn.row_factory = aiosqlite.Row
                cursor = await conn.execute(
                    """
                    INSERT INTO shifts (guild_id, user_id, user_name, start_time, status, last_verified_at)
                    VALUES (?, ?, ?, ?, 'ACTIVE', ?)
                    """,
                    (guild_id, user_id, user_name, start_time_iso, start_time_iso)
                )
                await conn.commit()
                shift_id = cursor.lastrowid

                async with conn.execute("SELECT * FROM shifts WHERE id = ?", (shift_id,)) as cur2:
                    row = await cur2.fetchone()
                    return True, dict(row) if row else None, "Mesai başarıyla başlatıldı."

    async def end_shift(
        self, guild_id: int, user_id: int, end_time: Optional[datetime] = None
    ) -> Tuple[bool, Optional[Dict[str, Any]], str]:
        """
        Kullanıcının aktif mesaisini sonlandırır ve istatistikleri hesaplar.
        """
        if end_time is None:
            end_time = datetime.now(timezone.utc)
        elif end_time.tzinfo is None:
            end_time = end_time.replace(tzinfo=timezone.utc)

        async with self._lock:
            active = await self.get_active_shift(guild_id, user_id)
            if not active:
                return False, None, "Şu anda açık bir mesainiz bulunmamaktadır."

            shift_id = active["id"]
            start_time_str = active["start_time"]
            start_dt = datetime.fromisoformat(start_time_str)
            if start_dt.tzinfo is None:
                start_dt = start_dt.replace(tzinfo=timezone.utc)

            duration_seconds = max(0, int((end_time - start_dt).total_seconds()))
            end_time_iso = end_time.isoformat()

            async with aiosqlite.connect(self.db_path) as conn:
                conn.row_factory = aiosqlite.Row
                await conn.execute(
                    """
                    UPDATE shifts 
                    SET end_time = ?, duration_seconds = ?, status = 'COMPLETED'
                    WHERE id = ?
                    """,
                    (end_time_iso, duration_seconds, shift_id)
                )
                await conn.commit()

                # Kullanıcının genel toplam istatistiklerini hesapla
                async with conn.execute(
                    """
                    SELECT COUNT(*) as total_shifts, COALESCE(SUM(duration_seconds), 0) as total_seconds
                    FROM shifts
                    WHERE guild_id = ? AND user_id = ? AND status IN ('COMPLETED', 'FORCE_CLOSED', 'AFK_CLOSED')
                    """,
                    (guild_id, user_id)
                ) as cur_stats:
                    stats_row = await cur_stats.fetchone()
                    total_shifts = stats_row["total_shifts"] if stats_row else 1
                    total_seconds = stats_row["total_seconds"] if stats_row else duration_seconds

                result_data = {
                    "id": shift_id,
                    "guild_id": guild_id,
                    "user_id": user_id,
                    "user_name": active["user_name"],
                    "start_time": start_dt,
                    "end_time": end_time,
                    "duration_seconds": duration_seconds,
                    "total_completed_shifts": total_shifts,
                    "total_lifetime_seconds": total_seconds,
                }
                return True, result_data, "Mesai başarıyla sonlandırıldı."

    async def end_shift_afk(
        self, guild_id: int, user_id: int, end_time: Optional[datetime] = None, note: Optional[str] = None
    ) -> Tuple[bool, Optional[Dict[str, Any]], str]:
        """
        AFK doğrulama süresi aşımı nedeniyle mesaiyi otomatik sonlandırır.
        Son 61 dakikalık dilim mesai süresinden silinir/düşülür.
        Toplam süre 61 dakikadan az ise oturum süresi 0 sn (geçersiz) olarak kayda geçer.
        """
        if end_time is None:
            end_time = datetime.now(timezone.utc)
        elif end_time.tzinfo is None:
            end_time = end_time.replace(tzinfo=timezone.utc)

        async with self._lock:
            active = await self.get_active_shift(guild_id, user_id)
            if not active:
                return False, None, "Aktif mesai bulunamadı."

            shift_id = active["id"]
            start_time_str = active["start_time"]
            start_dt = datetime.fromisoformat(start_time_str)
            if start_dt.tzinfo is None:
                start_dt = start_dt.replace(tzinfo=timezone.utc)

            raw_duration_seconds = max(0, int((end_time - start_dt).total_seconds()))
            penalty_seconds = config.AFK_PENALTY_MINUTES * 60  # 61 * 60 = 3660 sn
            final_duration_seconds = max(0, raw_duration_seconds - penalty_seconds)
            deducted_seconds = min(raw_duration_seconds, penalty_seconds)
            note_text = note or f"AFK - Doğrulama Yapılmadı ({config.AFK_PENALTY_MINUTES} dk düşüldü)"

            async with aiosqlite.connect(self.db_path) as conn:
                conn.row_factory = aiosqlite.Row
                await conn.execute(
                    """
                    UPDATE shifts 
                    SET end_time = ?, duration_seconds = ?, status = 'AFK_CLOSED', note = ?
                    WHERE id = ?
                    """,
                    (end_time.isoformat(), final_duration_seconds, note_text, shift_id)
                )
                await conn.commit()

                # Kullanıcının genel toplam istatistiklerini hesapla
                async with conn.execute(
                    """
                    SELECT COUNT(*) as total_shifts, COALESCE(SUM(duration_seconds), 0) as total_seconds
                    FROM shifts
                    WHERE guild_id = ? AND user_id = ? AND status IN ('COMPLETED', 'FORCE_CLOSED', 'AFK_CLOSED')
                    """,
                    (guild_id, user_id)
                ) as cur_stats:
                    stats_row = await cur_stats.fetchone()
                    total_shifts = stats_row["total_shifts"] if stats_row else 1
                    total_seconds = stats_row["total_seconds"] if stats_row else final_duration_seconds

                result_data = {
                    "id": shift_id,
                    "guild_id": guild_id,
                    "user_id": user_id,
                    "user_name": active["user_name"],
                    "start_time": start_dt,
                    "end_time": end_time,
                    "raw_duration_seconds": raw_duration_seconds,
                    "deducted_seconds": deducted_seconds,
                    "duration_seconds": final_duration_seconds,
                    "penalty_applied": True,
                    "total_completed_shifts": total_shifts,
                    "total_lifetime_seconds": total_seconds,
                }
                return True, result_data, "Mesai AFK zaman aşımı ve ceza uygulanarak sonlandırıldı."

    async def update_last_verified(
        self, guild_id: int, user_id: int, verified_at: Optional[datetime] = None
    ) -> bool:
        """Kullanıcının aktiflik doğrulama zamanını yeniler ve bekleyen doğrulama durumunu temizler."""
        if verified_at is None:
            verified_at = datetime.now(timezone.utc)
        elif verified_at.tzinfo is None:
            verified_at = verified_at.replace(tzinfo=timezone.utc)

        async with self._lock:
            async with aiosqlite.connect(self.db_path) as conn:
                cursor = await conn.execute(
                    """
                    UPDATE shifts 
                    SET last_verified_at = ?, verification_sent_at = NULL
                    WHERE guild_id = ? AND user_id = ? AND status = 'ACTIVE'
                    """,
                    (verified_at.isoformat(), guild_id, user_id)
                )
                await conn.commit()
                return cursor.rowcount > 0

    async def set_verification_sent(
        self, guild_id: int, user_id: int, sent_at: Optional[datetime] = None
    ) -> bool:
        """Kullanıcıya AFK doğrulama mesajı gönderildiğinde zaman damgasını işler."""
        if sent_at is None:
            sent_at = datetime.now(timezone.utc)
        elif sent_at.tzinfo is None:
            sent_at = sent_at.replace(tzinfo=timezone.utc)

        async with self._lock:
            async with aiosqlite.connect(self.db_path) as conn:
                cursor = await conn.execute(
                    """
                    UPDATE shifts 
                    SET verification_sent_at = ?
                    WHERE guild_id = ? AND user_id = ? AND status = 'ACTIVE'
                    """,
                    (sent_at.isoformat(), guild_id, user_id)
                )
                await conn.commit()
                return cursor.rowcount > 0

    async def get_all_active_shifts(self, guild_id: int) -> List[Dict[str, Any]]:
        """Sunucuda devam eden tüm aktif mesaileri listeler."""
        async with aiosqlite.connect(self.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            async with conn.execute(
                """
                SELECT * FROM shifts 
                WHERE guild_id = ? AND status = 'ACTIVE'
                ORDER BY id ASC
                """,
                (guild_id,)
            ) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    async def get_all_active_shifts_global(self) -> List[Dict[str, Any]]:
        """Tüm sunuculardaki aktif mesaileri döner (Arka plan AFK kontrolü için)."""
        async with aiosqlite.connect(self.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            async with conn.execute(
                """
                SELECT * FROM shifts 
                WHERE status = 'ACTIVE'
                ORDER BY id ASC
                """
            ) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    async def get_guild_report(self, guild_id: int) -> List[Dict[str, Any]]:
        """Sunucudaki tüm personellerin toplam mesai sürelerini ve oturum sayılarını döndürür."""
        async with aiosqlite.connect(self.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            async with conn.execute(
                """
                SELECT 
                    user_id,
                    user_name,
                    COUNT(id) as shift_count,
                    COALESCE(SUM(duration_seconds), 0) as total_duration,
                    MAX(COALESCE(end_time, start_time)) as last_active
                FROM shifts
                WHERE guild_id = ? AND status IN ('COMPLETED', 'FORCE_CLOSED', 'AFK_CLOSED')
                GROUP BY user_id
                ORDER BY total_duration DESC
                """,
                (guild_id,)
            ) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    async def get_user_stats(self, guild_id: int, user_id: int) -> Dict[str, Any]:
        """Tek bir personelin genel istatistiklerini ve aktif durumunu döndürür."""
        active = await self.get_active_shift(guild_id, user_id)
        async with aiosqlite.connect(self.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            async with conn.execute(
                """
                SELECT 
                    COUNT(id) as shift_count,
                    COALESCE(SUM(duration_seconds), 0) as total_duration,
                    MAX(end_time) as last_ended
                FROM shifts
                WHERE guild_id = ? AND user_id = ? AND status IN ('COMPLETED', 'FORCE_CLOSED', 'AFK_CLOSED')
                """,
                (guild_id, user_id)
            ) as cursor:
                row = await cursor.fetchone()
                return {
                    "is_active": active is not None,
                    "active_shift": active,
                    "total_shifts": row["shift_count"] if row else 0,
                    "total_duration": row["total_duration"] if row else 0,
                    "last_ended": row["last_ended"] if row else None,
                }

    async def force_end_shift(
        self, guild_id: int, user_id: int, admin_name: str
    ) -> Tuple[bool, Optional[Dict[str, Any]], str]:
        """Yetkili tarafından açık unutulmuş bir mesaiyi zorla kapatır."""
        now = datetime.now(timezone.utc)
        async with self._lock:
            active = await self.get_active_shift(guild_id, user_id)
            if not active:
                return False, None, "Bu kullanıcının aktif bir mesaisi bulunmuyor."

            shift_id = active["id"]
            start_time_str = active["start_time"]
            start_dt = datetime.fromisoformat(start_time_str)
            if start_dt.tzinfo is None:
                start_dt = start_dt.replace(tzinfo=timezone.utc)

            duration_seconds = max(0, int((now - start_dt).total_seconds()))

            async with aiosqlite.connect(self.db_path) as conn:
                await conn.execute(
                    """
                    UPDATE shifts 
                    SET end_time = ?, duration_seconds = ?, status = 'FORCE_CLOSED',
                        note = ?
                    WHERE id = ?
                    """,
                    (now.isoformat(), duration_seconds, f"Yönetici ({admin_name}) tarafından kapatıldı.", shift_id)
                )
                await conn.commit()

            return True, {
                "id": shift_id,
                "duration_seconds": duration_seconds,
                "start_time": start_dt,
                "end_time": now
            }, f"Mesai yönetici {admin_name} tarafından sonlandırıldı."

    async def force_end_all_shifts(
        self, guild_id: int, admin_name: str
    ) -> Tuple[int, List[Dict[str, Any]]]:
        """
        Sunucudaki tüm aktif mesaileri anlık zaman damgasıyla toplu olarak sonlandırır.
        Kapatılan mesai sayısını ve kapatılan oturumların özet listesini döner.
        """
        now = datetime.now(timezone.utc)
        now_iso = now.isoformat()
        closed_records: List[Dict[str, Any]] = []

        async with self._lock:
            async with aiosqlite.connect(self.db_path) as conn:
                conn.row_factory = aiosqlite.Row
                async with conn.execute(
                    "SELECT * FROM shifts WHERE guild_id = ? AND status = 'ACTIVE' ORDER BY id ASC",
                    (guild_id,)
                ) as cursor:
                    active_rows = await cursor.fetchall()

                if not active_rows:
                    return 0, []

                for row in active_rows:
                    shift_id = row["id"]
                    start_time_str = row["start_time"]
                    start_dt = datetime.fromisoformat(start_time_str)
                    if start_dt.tzinfo is None:
                        start_dt = start_dt.replace(tzinfo=timezone.utc)

                    duration_seconds = max(0, int((now - start_dt).total_seconds()))
                    note = f"Yönetici ({admin_name}) tarafından toplu kapatıldı."

                    await conn.execute(
                        """
                        UPDATE shifts 
                        SET end_time = ?, duration_seconds = ?, status = 'FORCE_CLOSED', note = ?
                        WHERE id = ?
                        """,
                        (now_iso, duration_seconds, note, shift_id)
                    )

                    closed_records.append({
                        "id": shift_id,
                        "user_id": row["user_id"],
                        "user_name": row["user_name"],
                        "start_time": start_dt,
                        "end_time": now,
                        "duration_seconds": duration_seconds,
                    })

                await conn.commit()

            return len(closed_records), closed_records

    async def get_guild_detailed_shifts(self, guild_id: int) -> List[Dict[str, Any]]:
        """
        Sunucudaki tüm mesai oturumlarının (kullanıcı, başlangıç/bitiş, süre, durum, not)
        detaylı kayıtlarını kronolojik ve kullanıcı bazlı sıralı döndürür.
        """
        async with aiosqlite.connect(self.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            async with conn.execute(
                """
                SELECT 
                    id,
                    guild_id,
                    user_id,
                    user_name,
                    start_time,
                    end_time,
                    duration_seconds,
                    status,
                    note,
                    created_at
                FROM shifts
                WHERE guild_id = ?
                ORDER BY user_name ASC, id ASC
                """,
                (guild_id,)
            ) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    async def reset_guild_shifts(self, guild_id: int) -> int:
        """
        Sunucudaki tüm mesai kayıtlarını kalıcı olarak siler ve dönemi sıfırlar.
        Silinen toplam kayıt sayısını döndürür.
        """
        async with self._lock:
            async with aiosqlite.connect(self.db_path) as conn:
                cursor = await conn.execute(
                    "DELETE FROM shifts WHERE guild_id = ?",
                    (guild_id,)
                )
                await conn.commit()
                return cursor.rowcount

# Singleton veritabanı nesnesi
db = DatabaseManager()
