import asyncio
import os
import shutil
import unittest
from datetime import datetime, timedelta, timezone
from database.db_manager import DatabaseManager
from utils.formatters import format_duration, get_discord_timestamp, to_unix_timestamp

class TestDatabaseAndLogic(unittest.IsolatedAsyncioTestCase):
    """Veritabanı ve iş mantığı birim testleri."""

    async def asyncSetUp(self):
        self.test_dir = "tests/temp_data"
        self.test_db_path = os.path.join(self.test_dir, "test_mesai.db")
        os.makedirs(self.test_dir, exist_ok=True)
        self.db = DatabaseManager(db_path=self.test_db_path)
        await self.db.init_db()

    async def asyncTearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir, ignore_errors=True)

    async def test_start_and_conflict_shift(self):
        """Mesai başlatma ve çakışan mesai engelleme testi."""
        guild_id = 9999
        user_id = 12345
        user_name = "TestUser"
        start_time = datetime(2026, 8, 27, 8, 0, 0, tzinfo=timezone.utc)

        # 1. İlk mesaiyi başlat
        success, shift, msg = await self.db.start_shift(guild_id, user_id, user_name, start_time)
        self.assertTrue(success)
        self.assertIsNotNone(shift)
        self.assertEqual(shift["status"], "ACTIVE")
        self.assertEqual(shift["user_id"], user_id)

        # 2. İkinci mesaiyi başlatmayı dene (Hata vermeli)
        success2, active_shift, msg2 = await self.db.start_shift(guild_id, user_id, user_name, start_time)
        self.assertFalse(success2)
        self.assertIn("Zaten", msg2)
        self.assertEqual(active_shift["id"], shift["id"])

    async def test_end_shift_duration_calculation(self):
        """Mesai bitirme ve süre hesaplama testi."""
        guild_id = 9999
        user_id = 54321
        user_name = "StaffMember"
        start_time = datetime(2026, 8, 27, 10, 0, 0, tzinfo=timezone.utc)
        # 2 saat 30 dakika 15 saniye sonrası
        end_time = start_time + timedelta(hours=2, minutes=30, seconds=15)

        # Mesai başlat
        await self.db.start_shift(guild_id, user_id, user_name, start_time)

        # Mesai bitir
        success, result, msg = await self.db.end_shift(guild_id, user_id, end_time)
        self.assertTrue(success)
        self.assertIsNotNone(result)
        expected_seconds = 2 * 3600 + 30 * 60 + 15
        self.assertEqual(result["duration_seconds"], expected_seconds)
        self.assertEqual(result["total_completed_shifts"], 1)
        self.assertEqual(result["total_lifetime_seconds"], expected_seconds)

        # Açık mesai yokken tekrar bitirmeyi dene
        success_empty, result_empty, msg_empty = await self.db.end_shift(guild_id, user_id, end_time)
        self.assertFalse(success_empty)
        self.assertIn("bulunmamaktadır", msg_empty)

    async def test_guild_reports_and_multiple_shifts(self):
        """Toplu raporlama ve çoklu mesai hesaplama testi."""
        guild_id = 8888
        u1, u2 = 101, 102
        t0 = datetime(2026, 8, 27, 9, 0, 0, tzinfo=timezone.utc)

        # U1: 1. vardiya (1 saat)
        await self.db.start_shift(guild_id, u1, "UserOne", t0)
        await self.db.end_shift(guild_id, u1, t0 + timedelta(hours=1))

        # U1: 2. vardiya (2 saat)
        await self.db.start_shift(guild_id, u1, "UserOne", t0 + timedelta(hours=2))
        await self.db.end_shift(guild_id, u1, t0 + timedelta(hours=4))

        # U2: 1. vardiya (45 dakika)
        await self.db.start_shift(guild_id, u2, "UserTwo", t0)
        await self.db.end_shift(guild_id, u2, t0 + timedelta(minutes=45))

        # Rapor al
        reports = await self.db.get_guild_report(guild_id)
        self.assertEqual(len(reports), 2)
        
        # U1 ilk sırada olmalı (toplam 3 saat = 10800 sn)
        self.assertEqual(reports[0]["user_id"], u1)
        self.assertEqual(reports[0]["shift_count"], 2)
        self.assertEqual(reports[0]["total_duration"], 3 * 3600)

        # U2 ikinci sırada olmalı (toplam 45 dk = 2700 sn)
        self.assertEqual(reports[1]["user_id"], u2)
        self.assertEqual(reports[1]["shift_count"], 1)
        self.assertEqual(reports[1]["total_duration"], 45 * 60)

    async def test_force_end_shift(self):
        """Yönetici tarafından mesai zorla kapatma testi."""
        guild_id = 7777
        user_id = 701
        start_time = datetime(2026, 8, 27, 10, 0, 0, tzinfo=timezone.utc)

        await self.db.start_shift(guild_id, user_id, "ForgottenUser", start_time)
        active = await self.db.get_active_shift(guild_id, user_id)
        self.assertIsNotNone(active)

        success, result, msg = await self.db.force_end_shift(guild_id, user_id, "AdminUser")
        self.assertTrue(success)

        # Artık aktif mesaisi olmamalı
        active_after = await self.db.get_active_shift(guild_id, user_id)
        self.assertIsNone(active_after)

    async def test_settings_storage(self):
        """Settings tablosu okuma ve yazma testi."""
        guild_id = 9999
        await self.db.set_setting(guild_id, "panel_aktif_mesailer_channel_id", "123456789")
        await self.db.set_setting(guild_id, "panel_aktif_mesailer_message_id", "987654321")

        val1 = await self.db.get_setting(guild_id, "panel_aktif_mesailer_channel_id")
        val2 = await self.db.get_setting(guild_id, "panel_aktif_mesailer_message_id")
        val_none = await self.db.get_setting(guild_id, "non_existent_key")

        self.assertEqual(val1, "123456789")
        self.assertEqual(val2, "987654321")
        self.assertIsNone(val_none)

        all_settings = await self.db.get_all_settings(guild_id)
        self.assertEqual(len(all_settings), 2)
        self.assertEqual(all_settings["panel_aktif_mesailer_channel_id"], "123456789")

    async def test_afk_shift_end_and_verification(self):
        """AFK doğrulama ve AFK mesai kapatma testi."""
        guild_id = 9999
        user_id = 7788
        start_time = datetime(2026, 8, 27, 8, 0, 0, tzinfo=timezone.utc)

        # Mesai başlat
        success, shift, msg = await self.db.start_shift(guild_id, user_id, "AFKUser", start_time)
        self.assertTrue(success)
        self.assertEqual(shift["last_verified_at"], start_time.isoformat())

        # Doğrulama mesajı gönderildiğini işaretle
        sent_time = start_time + timedelta(minutes=45)
        sent_ok = await self.db.set_verification_sent(guild_id, user_id, sent_time)
        self.assertTrue(sent_ok)

        # Doğrulamayı onayla
        verified_time = sent_time + timedelta(minutes=2)
        ver_ok = await self.db.update_last_verified(guild_id, user_id, verified_time)
        self.assertTrue(ver_ok)

        active = await self.db.get_active_shift(guild_id, user_id)
        self.assertEqual(active["last_verified_at"], verified_time.isoformat())
        self.assertIsNone(active["verification_sent_at"])

        # Zaman aşımı ile AFK kapat
        end_time = verified_time + timedelta(minutes=50)
        afk_success, afk_result, afk_msg = await self.db.end_shift_afk(guild_id, user_id, end_time)
        self.assertTrue(afk_success)
        self.assertIsNotNone(afk_result)

        # Raporlarda AFK oturumunun süresi ve sayısı doğru hesaplanmalı
        stats = await self.db.get_user_stats(guild_id, user_id)
        self.assertEqual(stats["total_shifts"], 1)
        self.assertGreater(stats["total_duration"], 0)
        self.assertFalse(stats["is_active"])

    async def test_force_end_all_shifts(self):
        """Yönetici tarafından sunucudaki tüm aktif mesaileri toplu kapatma testi."""
        guild_id = 6666
        u1, u2, u3 = 601, 602, 603
        t0 = datetime(2026, 8, 27, 10, 0, 0, tzinfo=timezone.utc)

        # 3 kullanıcı için aktif mesai başlat
        await self.db.start_shift(guild_id, u1, "User1", t0)
        await self.db.start_shift(guild_id, u2, "User2", t0 + timedelta(minutes=15))
        await self.db.start_shift(guild_id, u3, "User3", t0 + timedelta(minutes=30))

        active_before = await self.db.get_all_active_shifts(guild_id)
        self.assertEqual(len(active_before), 3)

        # Toplu kapat
        count, closed_records = await self.db.force_end_all_shifts(guild_id, "SuperAdmin")
        self.assertEqual(count, 3)
        self.assertEqual(len(closed_records), 3)

        # Artık aktif mesai kalmamış olmalı
        active_after = await self.db.get_all_active_shifts(guild_id)
        self.assertEqual(len(active_after), 0)

        # Raporları kontrol et
        reports = await self.db.get_guild_report(guild_id)
        self.assertEqual(len(reports), 3)

        # Boş sunucuda toplu kapatma testi (0 dönmeli)
        count_empty, closed_empty = await self.db.force_end_all_shifts(guild_id, "SuperAdmin")
        self.assertEqual(count_empty, 0)
        self.assertEqual(len(closed_empty), 0)

    async def test_afk_penalty_deduction(self):
        """AFK zaman aşımında son 61 dakikanın düşülmesi ve sınır durumların testi."""
        guild_id = 5555
        u_long = 501  # 2 saatlik oturum
        u_short = 502 # 30 dakikalık oturum
        t0 = datetime(2026, 8, 27, 8, 0, 0, tzinfo=timezone.utc)

        # 1. Durum: 2 saat (120 dk) çalışan personel -> 61 dk düşülüp 59 dk (3540 sn) olmalı
        await self.db.start_shift(guild_id, u_long, "LongWorker", t0)
        end_time_long = t0 + timedelta(hours=2)
        success_long, res_long, msg_long = await self.db.end_shift_afk(guild_id, u_long, end_time_long)
        self.assertTrue(success_long)
        self.assertEqual(res_long["raw_duration_seconds"], 2 * 3600)  # 7200 sn
        self.assertEqual(res_long["deducted_seconds"], 61 * 60)       # 3660 sn
        self.assertEqual(res_long["duration_seconds"], 59 * 60)       # 3540 sn (59 dk)

        # 2. Durum: 30 dakika çalışan personel (61 dk'dan az) -> Oturum 0 sn (geçersiz) olmalı
        await self.db.start_shift(guild_id, u_short, "ShortWorker", t0)
        end_time_short = t0 + timedelta(minutes=30)
        success_short, res_short, msg_short = await self.db.end_shift_afk(guild_id, u_short, end_time_short)
        self.assertTrue(success_short)
        self.assertEqual(res_short["raw_duration_seconds"], 30 * 60)  # 1800 sn
        self.assertEqual(res_short["deducted_seconds"], 30 * 60)      # 1800 sn (en fazla ham süre kadar düşülebilir)
        self.assertEqual(res_short["duration_seconds"], 0)            # 0 sn

        # İstatistik kontrolü
        stats_long = await self.db.get_user_stats(guild_id, u_long)
        self.assertEqual(stats_long["total_duration"], 3540)
        self.assertEqual(stats_long["total_shifts"], 1)

        stats_short = await self.db.get_user_stats(guild_id, u_short)
        self.assertEqual(stats_short["total_duration"], 0)
        self.assertEqual(stats_short["total_shifts"], 1)

    async def test_get_guild_detailed_shifts_and_reset(self):
        """Detaylı oturum sorgusu ve veritabanı sıfırlama testi."""
        guild_id = 4444
        u1, u2 = 401, 402
        t0 = datetime(2026, 8, 27, 8, 0, 0, tzinfo=timezone.utc)

        # Oturumlar oluştur
        await self.db.start_shift(guild_id, u1, "UserAlpha", t0)
        await self.db.end_shift(guild_id, u1, t0 + timedelta(hours=1))

        await self.db.start_shift(guild_id, u2, "UserBeta", t0 + timedelta(hours=1))
        await self.db.end_shift(guild_id, u2, t0 + timedelta(hours=3))

        # Detaylı dökümü çek
        detailed = await self.db.get_guild_detailed_shifts(guild_id)
        self.assertEqual(len(detailed), 2)
        self.assertEqual(detailed[0]["user_name"], "UserAlpha")
        self.assertEqual(detailed[0]["duration_seconds"], 3600)
        self.assertEqual(detailed[1]["user_name"], "UserBeta")
        self.assertEqual(detailed[1]["duration_seconds"], 7200)

        # Veritabanını sıfırla
        deleted_count = await self.db.reset_guild_shifts(guild_id)
        self.assertEqual(deleted_count, 2)

        # Sıfırlama sonrası kontroller
        detailed_after = await self.db.get_guild_detailed_shifts(guild_id)
        self.assertEqual(len(detailed_after), 0)
        reports_after = await self.db.get_guild_report(guild_id)
        self.assertEqual(len(reports_after), 0)

    def test_generate_shift_report_txt(self):
        """TXT rapor formatlayıcısının hatasız metin ürettiğini doğrula."""
        from utils.formatters import generate_shift_report_txt
        reports = [
            {"user_id": 111, "user_name": "Ahmet", "shift_count": 2, "total_duration": 7200, "last_active": "2026-08-27T10:00:00+00:00"},
            {"user_id": 222, "user_name": "Mehmet", "shift_count": 1, "total_duration": 3600, "last_active": "2026-08-27T12:00:00+00:00"},
        ]
        detailed = [
            {"id": 1, "user_id": 111, "user_name": "Ahmet", "start_time": "2026-08-27T08:00:00+00:00", "end_time": "2026-08-27T09:00:00+00:00", "duration_seconds": 3600, "status": "COMPLETED", "note": None},
            {"id": 2, "user_id": 111, "user_name": "Ahmet", "start_time": "2026-08-27T09:00:00+00:00", "end_time": "2026-08-27T10:00:00+00:00", "duration_seconds": 3600, "status": "COMPLETED", "note": None},
            {"id": 3, "user_id": 222, "user_name": "Mehmet", "start_time": "2026-08-27T11:00:00+00:00", "end_time": "2026-08-27T12:00:00+00:00", "duration_seconds": 3600, "status": "COMPLETED", "note": None},
        ]
        txt = generate_shift_report_txt(
            guild_name="Lucas2 Test Sunucusu",
            reports=reports,
            detailed_shifts=detailed,
            admin_name="SuperAdmin",
            report_time=datetime(2026, 8, 27, 12, 30, 0, tzinfo=timezone.utc)
        )
        self.assertIn("LUCAS2 MESAİ VE VARDİYA TAKİP SİSTEMİ", txt)
        self.assertIn("Lucas2 Test Sunucusu", txt)
        self.assertIn("Ahmet", txt)
        self.assertIn("Mehmet", txt)
        self.assertIn("BÖLÜM 1: PERSONEL GENEL PERFORMANS", txt)
        self.assertIn("BÖLÜM 2: DETAYLI MESAİ OTURUM GEÇMİŞİ", txt)
        self.assertIn("RAPOR SONU", txt)

    def test_duration_formatter(self):
        """Formatlayıcı metin testi."""
        self.assertEqual(format_duration(0), "0 sn")
        self.assertEqual(format_duration(45), "45 sn")
        self.assertEqual(format_duration(125), "2 dk 5 sn")
        self.assertEqual(format_duration(3665), "1 saat 1 dk 5 sn")
        self.assertEqual(format_duration(7200), "2 saat")

if __name__ == "__main__":
    unittest.main()


