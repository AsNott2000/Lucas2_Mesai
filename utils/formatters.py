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

def format_duration_detailed(seconds: int) -> str:
    """
    Süreyi gün, saat ve dakika cinsinden okunabilir metne dönüştürür.
    Örn: '1 Gün, 4 Saat, 20 Dakika' veya '2 Saat, 15 Dakika' veya '45 Dakika'.
    """
    if seconds < 0:
        seconds = 0

    days = seconds // 86400
    hours = (seconds % 86400) // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60

    if days > 0:
        return f"{days} Gün, {hours} Saat, {minutes} Dakika"

    if hours > 0:
        return f"{hours} Saat, {minutes} Dakika"

    if minutes > 0:
        return f"{minutes} Dakika"

    if secs > 0:
        return f"{secs} Saniye"

    return "0 Dakika"

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
            "🔴 **Mesai Bitir:** Aktif vardiyanızı sonlandırır ve toplam süreyi raporlar.\n"
            "🔵 **Mesai Süremi Öğren:** Toplam mesai sürenizi ve anlık durumunuzu sorgular.\n\n"
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
            "📊 **Genel Rapor Al & Sıfırla:** Aktif mesaileri kapatır, `.txt` raporunu teslim eder ve dönemi sıfırlar.\n"
            "🟢 **Anlık Aktif Mesailer:** Şu anda mesaisi devam eden personelleri anlık listeler.\n"
            "🛑 **Tüm Mesaileri Kapat:** Açık olan tüm kullanıcı mesailerini onay ile sonlandırır.\n"
            "👤 **Kişi Mesaisi Kapat:** Belirli bir personelin açık mesaisini listeden seçerek sonlandırır.\n"
            "⏱️ **Manuel Mesai Düzenle:** Belirli bir personelin mesai süresine manuel dakika ekler veya siler.\n"
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

def create_user_shift_duration_embed(
    user: discord.User | discord.Member,
    total_duration_seconds: int,
    completed_shifts_count: int,
    is_active: bool,
    active_session_seconds: Optional[int] = None,
    active_start_time: Optional[datetime] = None
) -> discord.Embed:
    """
    Kullanıcının 'Mesai Süremi Öğren' butonuna bastığında gördüğü kişisel özet embedi.
    """
    embed = discord.Embed(
        title="⏱️ KİŞİSEL MESAİ SÜRESİ BİLGİLENDİRMESİ",
        description=f"Sayın **{user.display_name}**, güncel mesai ve oturum durumunuz aşağıda belirtilmiştir:\n",
        color=0x3498DB  # Discord Primary Blue
    )

    # 1. Toplam Mesai Süresi
    embed.add_field(
        name="🏆 Toplam Mesai Süresi",
        value=f"**{format_duration_detailed(total_duration_seconds)}**",
        inline=False
    )

    # 2. Mevcut Durum
    if is_active:
        session_text = format_duration_detailed(active_session_seconds or 0)
        status_value = f"🟢 **Aktif Mesaidesiniz** (Şu anki oturum: {session_text})"
        if active_start_time:
            unix = to_unix_timestamp(active_start_time)
            status_value += f"\n🕒 **Başlangıç:** <t:{unix}:T> (<t:{unix}:R>)"
    else:
        status_value = "🔴 **Şu an aktif mesaide değilsiniz.**"

    embed.add_field(
        name="📊 Mevcut Durum",
        value=status_value,
        inline=False
    )

    # 3. Tamamlanan Oturum Sayısı
    embed.add_field(
        name="📈 Tamamlanan Oturum Sayısı",
        value=f"**{completed_shifts_count}** adet",
        inline=True
    )

    if hasattr(user, "display_avatar") and user.display_avatar:
        embed.set_thumbnail(url=user.display_avatar.url)

    embed.set_footer(text="Lucas2 Mesai Takip • Anlık Süre Sorgulama")
    embed.timestamp = datetime.now(timezone.utc)
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
    timeout_minutes: int = 15,
    penalty_minutes: int = 61
) -> discord.Embed:
    """Kullanıcıya 45 dakika dolduğunda iletilen aktiflik doğrulama embedi."""
    timeout_text = f"{timeout_minutes} dakika (60 saniye)" if timeout_minutes == 1 else f"{timeout_minutes} dakika"
    embed = discord.Embed(
        title="⚠️ MESAİ AKTİFLİK DOĞRULAMASI",
        description=(
            f"Sayın **{user.display_name}**,\n\n"
            f"Mesainiz **{minutes_active} dakikadır** kesintisiz olarak devam etmektedir.\n"
            f"Görevinizin başında aktif olduğunuzu teyit etmek için lütfen aşağıdaki butona tıklayınız.\n\n"
            f"⏳ **Yanıt Süreniz:** **{timeout_text}**\n\n"
            f"⚠️ **ÖNEMLİ CEZA KURALI:**\n"
            f"• Belirtilen süre içerisinde doğrulama yapmazsanız mesainiz otomatik olarak kapatılır.\n"
            f"• Oturumunuzdan **son {penalty_minutes} dakikalık süre silinir/düşülür** (Toplam süre {penalty_minutes} dk altındaysa oturum geçersiz sayılır)."
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
    raw_duration_seconds: Optional[int] = None,
    deducted_seconds: Optional[int] = None,
    timeout_minutes: int = 15,
    penalty_minutes: int = 61
) -> discord.Embed:
    """Zaman aşımına uğrayıp kapatılan mesai bildirim embedi."""
    timeout_text = f"{timeout_minutes} dakika (60 saniye)" if timeout_minutes == 1 else f"{timeout_minutes} dakika"
    
    desc_lines = [
        f"Sayın **{user.display_name}**,\n",
        f"**{timeout_text}** içinde aktiflik doğrulamasına yanıt verilmediği için mesainiz **AFK / Zaman Aşımı** gerekçesiyle otomatik olarak sonlandırılmıştır.\n",
    ]

    if raw_duration_seconds is not None and deducted_seconds is not None:
        desc_lines.append(f"⏱️ **Ham Oturum Süresi:** `{format_duration(raw_duration_seconds)}`")
        desc_lines.append(f"⚠️ **Uygulanan Ceza:** `-{format_duration(deducted_seconds)}` (Son {penalty_minutes} dk silindi)")
        desc_lines.append(f"⌛ **Kayda Geçen Net Süre:** **{format_duration(duration_seconds)}**\n")
    else:
        desc_lines.append(f"⌛ **Kaydedilen Toplam Süre:** **{format_duration(duration_seconds)}**\n")

    desc_lines.append("📌 *Tekrar göreve başladığınızda lütfen mesai kanalından yeni bir oturum başlatınız.*")

    embed = discord.Embed(
        title="🛑 Mesainiz AFK Nedeniyle Kapatıldı",
        description="\n".join(desc_lines),
        color=0xE74C3C  # Danger Red
    )
    embed.set_footer(text="Lucas2 Otomatik Güvenlik & AFK Sistemi • Ceza Uygulandı")
    embed.timestamp = datetime.now(timezone.utc)
    return embed

def create_captcha_prompt_embed(
    user: discord.User | discord.Member,
    target_name: str,
    target_emoji: str,
    minutes_active: int = 45,
    timeout_seconds: int = 60,
    penalty_minutes: int = 45
) -> discord.Embed:
    """Kullanıcıya CAPTCHA hedef nesne seçimini soran interaktif güvenlik embedi."""
    embed = discord.Embed(
        title="🧩 GÜVENLİK & CAPTCHA DOĞRULAMASI",
        description=(
            f"Sayın **{user.display_name}**,\n\n"
            f"Mesainiz **{minutes_active} dakikadır** kesintisiz olarak devam etmektedir.\n"
            f"Bot veya otomatik tıklama kullanımını önlemek amacıyla lütfen aşağıdaki güvenlik görevini tamamlayınız.\n\n"
            f"🎯 **HEDEF GÖREV:**\n"
            f"Lütfen aşağıdaki butonlardan **\"{target_name}\"** ({target_emoji}) olan seçeneğe tıklayınız.\n\n"
            f"⏳ **Yanıt Süreniz:** `{timeout_seconds} saniye` (1 Dakika)\n\n"
            f"⚠️ **CEZA UYARISI:**\n"
            f"• **Yanlış butona basarsanız** veya **{timeout_seconds} saniye içinde yanıt vermezseniz** mesainiz anında kapatılır.\n"
            f"• Toplam mesainizden **son {penalty_minutes} dakika silinir/kesilir**."
        ),
        color=0xE67E22  # Orange
    )
    embed.set_footer(text="Lucas2 Anti-Bot & CAPTCHA Güvenlik Sistemi")
    embed.timestamp = datetime.now(timezone.utc)
    return embed

def create_captcha_success_embed(
    user: discord.User | discord.Member,
    challenge: Any
) -> discord.Embed:
    """Kullanıcı doğru CAPTCHA seçeneğini tıkladığında gösterilen onay embedi."""
    target_name = getattr(challenge, "target_name", "Doğru Seçenek")
    target_emoji = getattr(challenge, "target_emoji", "✅")
    embed = discord.Embed(
        title="✅ CAPTCHA Başarıyla Doğrulandı!",
        description=(
            f"Tebrikler **{user.display_name}**!\n\n"
            f"Doğru nesneyi (**{target_name}** {target_emoji}) başarıyla seçtiniz.\n"
            f"Aktifliğiniz onaylandı ve mesainiz bir sonraki kontrole kadar kesintisiz devam ediyor.\n\n"
            f"*İyi çalışmalar ve kolaylıklar dileriz!*"
        ),
        color=0x2ECC71  # Green
    )
    embed.set_footer(text="Lucas2 Mesai Takip • Güvenlik Doğrulandı")
    embed.timestamp = datetime.now(timezone.utc)
    return embed

def create_captcha_failed_embed(
    user: discord.User | discord.Member,
    target_name: str,
    target_emoji: str,
    chosen_name: str,
    chosen_emoji: str,
    duration_seconds: int,
    raw_duration_seconds: Optional[int] = None,
    deducted_seconds: Optional[int] = None,
    penalty_minutes: int = 45
) -> discord.Embed:
    """Kullanıcı hatalı CAPTCHA seçimi yaptığında gösterilen bildirim embedi."""
    desc_lines = [
        f"Sayın **{user.display_name}**,\n",
        f"Güvenlik doğrulamasında **hatalı butona tıkladınız!**\n",
        f"🎯 **İstenen Nesne:** `{target_name}` {target_emoji}",
        f"❌ **Seçtiğiniz:** `{chosen_name}` {chosen_emoji}\n",
        f"Bu nedenle mesainiz **CAPTCHA Başarısız / Hatalı Seçim** gerekçesiyle derhal sonlandırılmıştır.\n",
    ]

    if raw_duration_seconds is not None and deducted_seconds is not None:
        desc_lines.append(f"⏱️ **Ham Oturum Süresi:** `{format_duration(raw_duration_seconds)}`")
        desc_lines.append(f"⚠️ **Uygulanan Ceza:** `-{format_duration(deducted_seconds)}` (Son {penalty_minutes} dk silindi)")
        desc_lines.append(f"⌛ **Kayda Geçen Net Süre:** **{format_duration(duration_seconds)}**\n")
    else:
        desc_lines.append(f"⌛ **Kaydedilen Toplam Süre:** **{format_duration(duration_seconds)}**\n")

    desc_lines.append("📌 *Tekrar göreve başladığınızda lütfen mesai kanalından yeni bir oturum başlatınız.*")

    embed = discord.Embed(
        title="🛑 CAPTCHA Başarısız! Mesainiz Kapatıldı",
        description="\n".join(desc_lines),
        color=0xE74C3C  # Danger Red
    )
    embed.set_footer(text="Lucas2 Anti-Bot & Güvenlik Sistemi • Ceza Uygulandı")
    embed.timestamp = datetime.now(timezone.utc)
    return embed

def create_report_closed_shift_dm_embed(
    user_name: str,
    duration_seconds: int,
    admin_name: str = "Yönetici"
) -> discord.Embed:
    """Genel rapor alındığı için mesaisi otomatik kapatılan personele gönderilen bilgilendirme embedi."""
    embed = discord.Embed(
        title="🔔 MESAİ BİLGİLENDİRMESİ",
        description=(
            f"Sayın **{user_name}**,\n\n"
            f"Yetkili yönetici (**{admin_name}**) tarafından **Genel Dönem Raporu** alındığı ve yeni çalışma dönemi "
            f"başlatıldığı için mevcut mesai oturumunuz sistem tarafından otomatik olarak sonlandırılmıştır.\n\n"
            f"⏱️ **Kapanan Oturum Süreniz:** `{format_duration(duration_seconds)}` (Dönem raporuna kaydedildi)\n\n"
            f"📌 **ÖNEMLİ:** Görevinizin başında çalışmaya devam ediyorsanız, lütfen mesai kanalından "
            f"**'Mesai Başlat'** butonunu kullanarak yeni bir mesai oturumu başlatmayı unutmayınız!"
        ),
        color=0x3498DB  # Blue / Info
    )
    embed.set_footer(text="Lucas2 Mesai Takip • Dönem Kapanış Bildirimi")
    embed.timestamp = datetime.now(timezone.utc)
    return embed

def create_log_embed(
    action_type: str,
    user: Optional[discord.User | discord.Member] = None,
    details: Optional[Dict[str, Any]] = None
) -> discord.Embed:
    """Log kanalı için detaylı denetim kayıt embedi."""
    details = details or {}
    colors = {
        "START": 0x2ECC71,             # Yeşil
        "END": 0x3498DB,               # Mavi
        "AFK_TIMEOUT": 0xE74C3C,       # Kırmızı
        "FORCE_CLOSED": 0xE67E22,      # Turuncu
        "FORCE_CLOSED_ALL": 0x992D22,  # Koyu Kırmızı
        "REPORT_AND_RESET": 0x9B59B6,  # Mor
        "MANUAL_ADJUST": 0xF39C12,     # Amber / Turuncu
    }
    
    titles = {
        "START": "🟢 Mesai Başlatıldı",
        "END": "🔴 Mesai Sonlandırıldı",
        "AFK_TIMEOUT": "⚠️ Mesai AFK Zaman Aşımı & Ceza ile Kapatıldı",
        "FORCE_CLOSED": "👮 Mesai Yönetici Tarafından Kapatıldı",
        "FORCE_CLOSED_ALL": "🛑 Tüm Mesailer Yönetici Tarafından Kapatıldı",
        "REPORT_AND_RESET": "📊 Dönem Raporu Alındı & Veriler Sıfırlandı",
        "MANUAL_ADJUST": "⏱️ Manuel Mesai Süresi Düzenlendi",
    }

    embed = discord.Embed(
        title=titles.get(action_type, f"📋 Mesai İşlemi: {action_type}"),
        color=colors.get(action_type, 0x5865F2)
    )
    if user:
        embed.add_field(name="👤 Personel / Yetkili", value=f"{user.mention} (`{user.display_name}` - ID: `{user.id}`)", inline=False)
    
    for key, value in details.items():
        embed.add_field(name=key, value=str(value), inline=True)

    embed.set_footer(text="Lucas2 Mesai Denetim Günlüğü")
    embed.timestamp = datetime.now(timezone.utc)
    return embed

def generate_shift_report_txt(
    guild_name: str,
    reports: List[Dict[str, Any]],
    detailed_shifts: List[Dict[str, Any]],
    admin_name: str,
    report_time: Optional[datetime] = None
) -> str:
    """
    Tüm personel özetlerini ve detaylı oturum dökümlerini içeren UTF-8 metin raporu üretir.
    """
    if report_time is None:
        report_time = datetime.now(timezone.utc)
    elif report_time.tzinfo is None:
        report_time = report_time.replace(tzinfo=timezone.utc)

    total_personnel = len(reports)
    total_shifts = sum(r.get("shift_count", 0) for r in reports)
    total_duration_sec = sum(r.get("total_duration", 0) for r in reports)
    date_str = report_time.strftime("%Y-%m-%d %H:%M:%S UTC")

    lines = []
    lines.append("=" * 80)
    lines.append("LUCAS2 MESAİ VE VARDİYA TAKİP SİSTEMİ — DÖNEM SONU RAPORU")
    lines.append("=" * 80)
    lines.append(f"Sunucu Adı          : {guild_name}")
    lines.append(f"Rapor Tarihi        : {date_str}")
    lines.append(f"Raporu Alan Yetkili : {admin_name}")
    lines.append(f"Toplam Personel     : {total_personnel} kişi")
    lines.append(f"Toplam Oturum       : {total_shifts} adet")
    lines.append(f"Genel Toplam Süre   : {format_duration(total_duration_sec)} ({total_duration_sec} saniye)")
    lines.append("=" * 80)
    lines.append("")
    lines.append("[ BÖLÜM 1: PERSONEL GENEL PERFORMANS & SIRALAMA TABLOSU ]")
    lines.append("-" * 80)
    lines.append(f"{'Sıra':<5} | {'Personel Adı':<22} | {'Discord ID':<20} | {'Oturum':<7} | {'Toplam Süre':<18}")
    lines.append("-" * 80)

    if not reports:
        lines.append("Bu dönem için kayıtlı tamamlanmış personel mesaisi bulunmamaktadır.")
    else:
        for idx, row in enumerate(reports, 1):
            u_name = str(row.get("user_name", "Bilinmiyor"))[:20]
            u_id = str(row.get("user_id", ""))
            s_count = str(row.get("shift_count", 0))
            dur_str = format_duration(row.get("total_duration", 0))
            lines.append(f"{idx:<5} | {u_name:<22} | {u_id:<20} | {s_count:<7} | {dur_str:<18}")

    lines.append("-" * 80)
    lines.append("")
    lines.append("[ BÖLÜM 2: DETAYLI MESAİ OTURUM GEÇMİŞİ DÖKÜMÜ ]")
    lines.append("-" * 80)
    lines.append(f"{'ID':<6} | {'Personel Adı':<18} | {'Başlangıç (UTC)':<19} | {'Bitiş (UTC)':<19} | {'Süre':<14} | {'Durum':<12} | {'Not'}")
    lines.append("-" * 80)

    if not detailed_shifts:
        lines.append("Detaylı oturum kaydı bulunmamaktadır.")
    else:
        for s in detailed_shifts:
            s_id = str(s.get("id", ""))
            u_name = str(s.get("user_name", "Bilinmiyor"))[:16]
            start_raw = s.get("start_time", "")
            end_raw = s.get("end_time", "")

            st_dt = parse_iso_or_datetime(start_raw)
            en_dt = parse_iso_or_datetime(end_raw)
            st_str = st_dt.strftime("%Y-%m-%d %H:%M") if st_dt else str(start_raw)[:19]
            en_str = en_dt.strftime("%Y-%m-%d %H:%M") if en_dt else (str(end_raw)[:19] if end_raw else "Devam Ediyor")

            dur_text = format_duration(s.get("duration_seconds", 0))
            status = str(s.get("status", ""))
            note = str(s.get("note") or "-")
            lines.append(f"{s_id:<6} | {u_name:<18} | {st_str:<19} | {en_str:<19} | {dur_text:<14} | {status:<12} | {note}")

    lines.append("-" * 80)
    lines.append("")
    lines.append("=" * 80)
    lines.append("RAPOR SONU • Veritabanı sıfırlama işlemi öncesinde sistem tarafından derlenmiştir.")
    lines.append("=" * 80)

    return "\n".join(lines)

def create_report_and_reset_summary_embed(
    admin: discord.User | discord.Member,
    closed_active_count: int,
    reported_user_count: int,
    total_shifts_count: int,
    total_duration_seconds: int,
    deleted_records_count: int,
    filename: str
) -> discord.Embed:
    """Rapor alma ve dönem sıfırlama işlemi tamamlandığında iletilen özet embed."""
    embed = discord.Embed(
        title="📊 Dönem Raporu Alındı & Veritabanı Sıfırlandı",
        description=(
            "Tüm mesai oturumları derlenmiş, ekteki rapor dosyasına aktarılmış ve "
            "sunucu için yeni dönem başlatılarak canlı tablolar sıfırlanmıştır."
        ),
        color=0x2ECC71  # Yeşil
    )
    embed.add_field(name="👮 İşlemi Yapan Yetkili", value=admin.mention, inline=True)
    embed.add_field(name="📄 Oluşturulan Dosya", value=f"`{filename}`", inline=True)
    embed.add_field(name="👥 Raporlanan Personel", value=f"**{reported_user_count}** kişi", inline=True)
    embed.add_field(name="📈 Toplam Oturum Sayısı", value=f"**{total_shifts_count}** oturum", inline=True)
    embed.add_field(name="⏳ Birikmiş Toplam Süre", value=f"**{format_duration(total_duration_seconds)}**", inline=True)
    embed.add_field(name="🧹 Temizlenen Kayıt Sayısı", value=f"**{deleted_records_count}** satır", inline=True)

    if closed_active_count > 0:
        embed.add_field(
            name="⚠️ Otomatik Kapatılan Aktif Mesailer",
            value=f"Rapor alınırken açık olan **{closed_active_count}** personelin mesaisi otomatik olarak kapatılıp rapora dahil edildi.",
            inline=False
        )

    embed.set_footer(text="Lucas2 Yönetim Paneli • Canlı Paneller Sıfırlandı")
    embed.timestamp = datetime.now(timezone.utc)
    return embed


