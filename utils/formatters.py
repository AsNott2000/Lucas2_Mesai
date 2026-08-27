import discord
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

def format_duration(seconds: int) -> str:
    """Saniye cinsinden süreyi Türkçe saat, dakika, saniye metnine dönüştürür."""
    if seconds < 0:
        seconds = 0
    
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60

    parts = []
    if hours > 0:
        parts.append(f"{hours} saat")
    if minutes > 0:
        parts.append(f"{minutes} dk")
    if secs > 0 or not parts:
        parts.append(f"{secs} sn")

    return " ".join(parts)

def to_unix_timestamp(dt: datetime) -> int:
    """Datetime nesnesini Unix timestamp (saniye) değerine dönüştürür."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp())

def parse_iso_or_datetime(value: Any) -> Optional[datetime]:
    """ISO formatındaki string veya datetime nesnesini datetime'a çevirir."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value)
        except Exception:
            return None
    return None

def get_discord_timestamp(dt_value: Any, style: str = "f") -> str:
    """Discord dinamik zaman damgası döndürür (Örn: <t:1700000000:R>)."""
    dt = parse_iso_or_datetime(dt_value)
    if not dt:
        return "Bilinmiyor"
    unix = to_unix_timestamp(dt)
    return f"<t:{unix}:{style}>"

def create_shift_panel_embed() -> discord.Embed:
    """#mesai kanalında kalıcı duracak ana embed paneli."""
    embed = discord.Embed(
        title="⏱️ PERSONEL MESAİ VE VARDİYA TAKİP SİSTEMİ",
        description=(
            "Aşağıdaki butonları kullanarak mesainizi başlatabilir veya sonlandırabilirsiniz.\n\n"
            "🟢 **Mesai Başlat:** Vardiyanızı başlatır ve çalışma saatinizi kaydeder.\n"
            "🔴 **Mesai Bitir:** Aktif vardiyanızı sonlandırır ve toplam süreyi raporlar.\n\n"
            "📌 *Not: Lütfen mesaiye başladığınızda ve ayrılırken butonları kullanmayı unutmayınız.*"
        ),
        color=0x5865F2  # Discord Blurple
    )
    embed.add_field(
        name="📋 Bilgilendirme & Kurallar",
        value=(
            "• Tüm giriş/çıkış kayıtları veritabanında güvenle saklanır.\n"
            "• Mesai boyunca her 45 dakikada bir aktiflik doğrulaması istenir.\n"
            "• Birden fazla çakışan mesai başlatılamaz."
        ),
        inline=False
    )
    embed.set_footer(text="Lucas2 Mesai Takip Botu • Güvenli & Otomatik Kayıt")
    return embed

def create_admin_panel_embed() -> discord.Embed:
    """#admin-settings kanalında kalıcı duracak yönetici paneli embedi."""
    embed = discord.Embed(
        title="🛡️ YÖNETİCİ MESAİ KONTROL VE RAPOR PANELİ",
        description=(
            "Bu panel yalnızca yetkili yöneticilerin kullanımı içindir.\n\n"
            "📊 **Genel Rapor Al:** Tüm personellerin toplam mesai sürelerini ve oturum sayılarını listeler.\n"
            "🟢 **Anlık Aktif Mesailer:** Şu anda mesaisi devam eden personelleri gösterir.\n"
        ),
        color=0x2B2D31  # Koyu Gri / Dark Slate
    )
    embed.add_field(
        name="🔒 Yetki Koruması",
        value="Bu butonlar yalnızca Yönetici veya Yetkili Rolüne sahip kullanıcılar tarafından çalıştırılabilir.",
        inline=False
    )
    embed.set_footer(text="Lucas2 Yönetici Paneli • Gizli & Yetkili Erişim")
    return embed

def create_shift_started_embed(user: discord.User | discord.Member, start_time: datetime) -> discord.Embed:
    """Mesai başlatıldığında kullanıcıya dönen onay embedi."""
    unix = to_unix_timestamp(start_time)
    embed = discord.Embed(
        title="✅ Mesainiz Başarıyla Başlatıldı",
        description=f"İyi çalışmalar dileriz, **{user.display_name}**!",
        color=0x2ECC71  # Emerald Green
    )
    embed.add_field(name="🕒 Başlangıç Saati", value=f"<t:{unix}:T> (<t:{unix}:t>)", inline=True)
    embed.add_field(name="📅 Başlangıç Tarihi", value=f"<t:{unix}:D>", inline=True)
    embed.add_field(name="⏱️ Sayaç", value=f"<t:{unix}:R>", inline=False)
    embed.set_footer(text="Mesainiz bittiğinde 'Mesai Bitir' butonuna basınız.")
    return embed

def create_shift_ended_embed(
    user: discord.User | discord.Member,
    start_time: datetime,
    end_time: datetime,
    duration_seconds: int,
    total_completed_shifts: int,
    total_lifetime_seconds: int,
) -> discord.Embed:
    """Mesai bitirildiğinde kullanıcıya dönen detaylı özet embedi."""
    start_unix = to_unix_timestamp(start_time)
    end_unix = to_unix_timestamp(end_time)

    embed = discord.Embed(
        title="🛑 Mesainiz Başarıyla Sonlandırıldı",
        description=f"Bugünkü emeğiniz için teşekkürler, **{user.display_name}**.",
        color=0xE74C3C  # Soft Red
    )
    embed.add_field(name="🟢 Başlangıç", value=f"<t:{start_unix}:F>", inline=True)
    embed.add_field(name="🔴 Bitiş", value=f"<t:{end_unix}:F>", inline=True)
    embed.add_field(
        name="⌛ Bu Oturumun Süresi",
        value=f"**{format_duration(duration_seconds)}**",
        inline=False
    )
    embed.add_field(
        name="📈 Toplam Mesai Sayınız",
        value=f"{total_completed_shifts} oturum",
        inline=True
    )
    embed.add_field(
        name="🏆 Genel Toplam Süreniz",
        value=f"{format_duration(total_lifetime_seconds)}",
        inline=True
    )
    embed.set_footer(text="Kayıt veritabanına işlendi.")
    return embed

def create_warning_embed(title: str, message: str) -> discord.Embed:
    """Uyarı bildirim embedi."""
    embed = discord.Embed(
        title=f"⚠️ {title}",
        description=message,
        color=0xF1C40F  # Warning Yellow
    )
    return embed

def create_error_embed(title: str, message: str) -> discord.Embed:
    """Hata bildirim embedi."""
    embed = discord.Embed(
        title=f"❌ {title}",
        description=message,
        color=0xE74C3C  # Danger Red
    )
    return embed

def create_live_active_shifts_embed(active_shifts: List[Dict[str, Any]]) -> discord.Embed:
    """#aktif-mesailer kanalı için canlı, dinamik güncellenen embed paneli."""
    embed = discord.Embed(
        title="🟢 CANLI AKTİF MESAİ TAKİBİ",
        color=0x2ECC71 if active_shifts else 0x747F8D
    )

    if not active_shifts:
        embed.description = (
            "```yaml\nŞu an aktif mesaide kimse bulunmamaktadır.\n```\n"
            "📌 *Mesai başlatmak için lütfen ilgili mesai kanalındaki butonları kullanınız.*"
        )
        embed.set_footer(text="Lucas2 Canlı Mesai Takip Sistemi • Otomatik Güncellenir")
        embed.timestamp = datetime.now(timezone.utc)
        return embed

    embed.description = f"Şu anda sunucuda aktif görevde bulunan **{len(active_shifts)}** personel listelenmektedir:\n"

    for idx, shift in enumerate(active_shifts, 1):
        user_id = shift.get("user_id")
        user_name = shift.get("user_name", "Bilinmiyor")
        start_time_raw = shift.get("start_time")
        start_dt = parse_iso_or_datetime(start_time_raw)
        
        start_clock = get_discord_timestamp(start_dt, "T") if start_dt else "Bilinmiyor"
        start_rel = get_discord_timestamp(start_dt, "R") if start_dt else "Bilinmiyor"

        # Geçen tahmini süre
        if start_dt:
            if start_dt.tzinfo is None:
                start_dt = start_dt.replace(tzinfo=timezone.utc)
            elapsed_sec = max(0, int((datetime.now(timezone.utc) - start_dt).total_seconds()))
            elapsed_text = format_duration(elapsed_sec)
        else:
            elapsed_text = "Hesaplanıyor"

        field_value = (
            f"👤 **Personel:** <@{user_id}> (`{user_name}`)\n"
            f"🕒 **Başlangıç:** {start_clock} ({start_rel})\n"
            f"⌛ **Aktif Süre:** `{elapsed_text}`"
        )
        embed.add_field(
            name=f"🟢 {idx}. {user_name}",
            value=field_value,
            inline=False
        )

    embed.set_footer(text=f"Lucas2 Canlı Takip • Toplam {len(active_shifts)} Personel Aktif")
    embed.timestamp = datetime.now(timezone.utc)
    return embed

def create_leaderboard_embed(reports: List[Dict[str, Any]], guild: Optional[discord.Guild] = None) -> discord.Embed:
    """#mesai-tablo kanalı için sıralı liderlik ve genel istatistik tablosu."""
    embed = discord.Embed(
        title="🏆 PERSONEL GENEL MESAİ TABLOSU & İSTATİSTİKLERİ",
        description="Sunucumuzdaki personellerin kayıtlı toplam çalışma süreleri ve performans sıralaması:\n",
        color=0xF1C40F  # Gold
    )

    if not reports:
        embed.description += "\n*Henüz sisteme kaydedilmiş tamamlanmış bir mesai kaydı bulunmamaktadır.*"
        embed.set_footer(text="Lucas2 Mesai Tablosu • Düzenli Olarak Güncellenir")
        embed.timestamp = datetime.now(timezone.utc)
        return embed

    total_guild_seconds = 0
    total_guild_shifts = 0
    lines = []

    medals = {1: "🥇", 2: "🥈", 3: "🥉"}

    for idx, row in enumerate(reports, 1):
        user_id = row.get("user_id")
        user_name = row.get("user_name", "Bilinmiyor")
        total_seconds = row.get("total_duration", 0)
        shift_count = row.get("shift_count", 0)
        last_active = row.get("last_active")

        total_guild_seconds += total_seconds
        total_guild_shifts += shift_count

        badge = medals.get(idx, f"`{idx}.`")
        last_active_text = get_discord_timestamp(last_active, "R") if last_active else "Kayıt yok"

        lines.append(
            f"{badge} **<@{user_id}>** (`{user_name}`)\n"
            f"   ⏱️ Toplam Süre: **{format_duration(total_seconds)}**\n"
            f"   📊 Oturum: **{shift_count}** adet | Son Aktif: {last_active_text}"
        )

    # Embed karakter limitlerine göre parçalama
    chunk = ""
    field_count = 1
    for line in lines:
        if len(chunk) + len(line) + 2 > 1000:
            embed.add_field(name=f"📋 Sıralama Tablosu (Sayfa {field_count})", value=chunk, inline=False)
            chunk = line + "\n\n"
            field_count += 1
        else:
            chunk += line + "\n\n"

    if chunk:
        title_name = "📋 Sıralama Tablosu" if field_count == 1 else f"📋 Sıralama Tablosu (Sayfa {field_count})"
        embed.add_field(name=title_name, value=chunk, inline=False)

    # Genel İstatistikler Kutusu
    embed.add_field(
        name="🌐 Genel Sunucu Toplam İstatistikleri",
        value=(
            f"👥 **Toplam Kayıtlı Personel:** `{len(reports)}` kişi\n"
            f"📈 **Toplam Tamamlanan Oturum:** `{total_guild_shifts}` oturum\n"
            f"⏳ **Genel Birikmiş Çalışma Süresi:** `{format_duration(total_guild_seconds)}`"
        ),
        inline=False
    )

    embed.set_footer(text=f"Lucas2 Mesai Tablosu • Toplam {len(reports)} Personel")
    embed.timestamp = datetime.now(timezone.utc)
    return embed

def create_admin_report_embed(reports: List[Dict[str, Any]], guild: Optional[discord.Guild] = None) -> discord.Embed:
    """Tüm personellerin mesai sürelerini listeleyen yönetici rapor embedi."""
    return create_leaderboard_embed(reports, guild)

def create_active_shifts_embed(active_shifts: List[Dict[str, Any]]) -> discord.Embed:
    """Anlık olarak mesaisi devam eden personelleri listeleyen embed."""
    return create_live_active_shifts_embed(active_shifts)

def create_afk_prompt_embed(
    user: discord.User | discord.Member,
    minutes_active: int = 45,
    timeout_minutes: int = 5
) -> discord.Embed:
    """Kullanıcıya 45 dakika dolduğunda iletilen aktiflik doğrulama embedi."""
    embed = discord.Embed(
        title="⚠️ MESAİ AKTİFLİK DOĞRULAMASI",
        description=(
            f"Sayın **{user.display_name}**,\n\n"
            f"Mesainiz **{minutes_active} dakikadır** kesintisiz olarak devam etmektedir.\n"
            f"Görevinizin başında aktif olduğunuzu teyit etmek için lütfen aşağıdaki butona tıklayınız.\n\n"
            f"⏳ **Yanıt Süreniz:** **{timeout_minutes} dakika**\n"
            f"📌 *Belirtilen süre içerisinde doğrulama yapmazsanız mesainiz AFK sebebiyle otomatik olarak sonlandırılacaktır.*"
        ),
        color=0xE67E22  # Orange
    )
    embed.set_footer(text="Lucas2 Aktiflik & Güvenlik Doğrulama Sistemi")
    embed.timestamp = datetime.now(timezone.utc)
    return embed

def create_afk_verified_embed(user: discord.User | discord.Member) -> discord.Embed:
    """Kullanıcı aktiflik doğrulama butonuna bastığında gösterilen onay embedi."""
    embed = discord.Embed(
        title="✅ Aktiflik Başarıyla Doğrulandı!",
        description=f"Teşekkürler **{user.display_name}**! Aktifliğiniz onaylandı ve mesainiz devam ediyor.\n\n*İyi çalışmalar ve kolaylıklar dileriz.*",
        color=0x2ECC71  # Green
    )
    embed.set_footer(text="Lucas2 Mesai Takip")
    embed.timestamp = datetime.now(timezone.utc)
    return embed

def create_afk_timeout_embed(
    user: discord.User | discord.Member,
    duration_seconds: int,
    timeout_minutes: int = 5
) -> discord.Embed:
    """Zaman aşımına uğrayıp kapatılan mesai bildirim embedi."""
    embed = discord.Embed(
        title="🛑 Mesainiz AFK Nedeniyle Kapatıldı",
        description=(
            f"Sayın **{user.display_name}**,\n\n"
            f"**{timeout_minutes} dakika** içinde aktiflik doğrulamasına yanıt verilmediği için mesainiz **AFK / Zaman Aşımı** gerekçesiyle otomatik olarak sonlandırılmıştır.\n\n"
            f"⌛ **Kaydedilen Toplam Süre:** **{format_duration(duration_seconds)}**\n\n"
            f"📌 *Tekrar göreve başladığınızda lütfen mesai kanalından yeni bir oturum başlatınız.*"
        ),
        color=0xE74C3C  # Danger Red
    )
    embed.set_footer(text="Lucas2 Otomatik Güvenlik & AFK Sistemi")
    embed.timestamp = datetime.now(timezone.utc)
    return embed

def create_log_embed(
    action_type: str,
    user: discord.User | discord.Member,
    details: Dict[str, Any]
) -> discord.Embed:
    """Log kanalı için detaylı denetim kayıt embedi."""
    colors = {
        "START": 0x2ECC71,       # Yeşil
        "END": 0x3498DB,         # Mavi
        "AFK_TIMEOUT": 0xE74C3C, # Kırmızı
        "FORCE_CLOSED": 0xE67E22 # Turuncu
    }
    
    titles = {
        "START": "🟢 Mesai Başlatıldı",
        "END": "🔴 Mesai Sonlandırıldı",
        "AFK_TIMEOUT": "⚠️ Mesai AFK Zaman Aşımı ile Kapatıldı",
        "FORCE_CLOSED": "👮 Mesai Yönetici Tarafından Kapatıldı"
    }

    embed = discord.Embed(
        title=titles.get(action_type, f"📋 Mesai İşlemi: {action_type}"),
        color=colors.get(action_type, 0x5865F2)
    )
    embed.add_field(name="👤 Personel", value=f"{user.mention} (`{user.display_name}` - ID: `{user.id}`)", inline=False)
    
    for key, value in details.items():
        embed.add_field(name=key, value=str(value), inline=True)

    embed.set_footer(text="Lucas2 Mesai Denetim Günlüğü")
    embed.timestamp = datetime.now(timezone.utc)
    return embed

