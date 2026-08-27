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
        name="📋 Bilgilendirme",
        value="• Tüm giriş/çıkış kayıtları veritabanında güvenle saklanır.\n• Birden fazla çakışan mesai başlatılamaz.",
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

def create_admin_report_embed(reports: List[Dict[str, Any]], guild: Optional[discord.Guild] = None) -> discord.Embed:
    """Tüm personellerin mesai sürelerini listeleyen yönetici rapor embedi."""
    embed = discord.Embed(
        title="📊 TÜM PERSONEL MESAİ ÖZET RAPORU",
        description="Aşağıda sunucudaki personellerin toplam çalışma istatistikleri listelenmiştir:\n",
        color=0x3498DB  # Info Blue
    )

    if not reports:
        embed.description += "\n*Henüz sisteme kaydedilmiş tamamlanmış bir mesai verisi bulunmamaktadır.*"
        embed.set_footer(text="Lucas2 Mesai Sistemi")
        return embed

    lines = []
    total_guild_seconds = 0
    total_guild_shifts = 0

    for idx, row in enumerate(reports, 1):
        user_id = row.get("user_id")
        user_name = row.get("user_name", "Bilinmiyor")
        total_seconds = row.get("total_duration", 0)
        shift_count = row.get("shift_count", 0)
        last_active = row.get("last_active")

        total_guild_seconds += total_seconds
        total_guild_shifts += shift_count

        last_active_text = get_discord_timestamp(last_active, "R") if last_active else "Kayıt yok"
        user_mention = f"<@{user_id}>"

        lines.append(
            f"**{idx}. {user_mention}** (`{user_name}`)\n"
            f"   • Toplam Süre: **{format_duration(total_seconds)}**\n"
            f"   • Oturum Sayısı: **{shift_count}** adet | Son Aktif: {last_active_text}"
        )

    # Discord embed limitlerine göre bölme (her alanda max 1024 karakter)
    chunk = ""
    field_count = 1
    for line in lines:
        if len(chunk) + len(line) + 2 > 1000:
            embed.add_field(name=f"👥 Personel Listesi (Bölüm {field_count})", value=chunk, inline=False)
            chunk = line + "\n"
            field_count += 1
        else:
            chunk += line + "\n"

    if chunk:
        name_title = "👥 Personel Listesi" if field_count == 1 else f"👥 Personel Listesi (Bölüm {field_count})"
        embed.add_field(name=name_title, value=chunk, inline=False)

    # Genel toplam istatistikleri
    embed.add_field(
        name="🌐 Genel Sunucu Toplamları",
        value=(
            f"• Toplam Personel Sayısı: **{len(reports)}**\n"
            f"• Toplam Tamamlanan Oturum: **{total_guild_shifts}**\n"
            f"• Toplam Birikmiş Mesai Süresi: **{format_duration(total_guild_seconds)}**"
        ),
        inline=False
    )
    embed.set_footer(text=f"Rapor Oluşturulma Tarihi • Toplam {len(reports)} personel")
    embed.timestamp = datetime.now(timezone.utc)
    return embed

def create_active_shifts_embed(active_shifts: List[Dict[str, Any]]) -> discord.Embed:
    """Anlık olarak mesaisi devam eden personelleri listeleyen embed."""
    embed = discord.Embed(
        title="🟢 ANLIK AKTİF MESAİDEKİ PERSONELLER",
        color=0x2ECC71
    )

    if not active_shifts:
        embed.description = "Şu anda aktif mesaisi devam eden **hiçbir personel bulunmamaktadır**."
        embed.set_footer(text="Lucas2 Mesai Takip")
        return embed

    embed.description = f"Şu anda toplam **{len(active_shifts)}** personel aktif görevdedir:\n"

    for idx, shift in enumerate(active_shifts, 1):
        user_id = shift.get("user_id")
        user_name = shift.get("user_name", "Bilinmiyor")
        start_time = shift.get("start_time")
        start_ts = get_discord_timestamp(start_time, "R")
        start_clock = get_discord_timestamp(start_time, "T")

        embed.add_field(
            name=f"{idx}. {user_name}",
            value=f"• Kullanıcı: <@{user_id}>\n• Başlangıç: {start_clock} ({start_ts})",
            inline=True
        )

    embed.set_footer(text="Canlı Durum Sorgusu")
    embed.timestamp = datetime.now(timezone.utc)
    return embed
