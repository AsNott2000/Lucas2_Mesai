import logging
import discord
from datetime import datetime, timezone
from database import db
from services.panel_manager import panel_manager
from utils.formatters import (
    create_shift_started_embed,
    create_shift_ended_embed,
    create_user_shift_duration_embed,
    create_warning_embed,
    create_error_embed,
    create_log_embed,
    format_duration,
    format_duration_detailed,
    get_discord_timestamp,
    parse_iso_or_datetime,
)

logger = logging.getLogger("Lucas2MesaiBot.ShiftView")

class ShiftView(discord.ui.View):
    """
    #mesai kanalındaki kalıcı (Persistent) butonları barındıran View sınıfı.
    timeout=None ve butonlardaki sabit custom_id değerleri sayesinde 
    bot yeniden başlatılsa dahi çalışmaya devam eder.
    """

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Mesai Başlat",
        style=discord.ButtonStyle.success,
        emoji="🟢",
        custom_id="btn_start_shift"
    )
    async def start_shift_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Kullanıcının mesaisini başlatan buton aksiyonu."""
        guild = interaction.guild
        if not guild:
            await interaction.response.send_message(
                embed=create_error_embed("Hata", "Bu buton yalnızca bir sunucu içerisinde kullanılabilir."),
                ephemeral=True
            )
            return

        user = interaction.user
        now = datetime.now(timezone.utc)

        success, shift_data, message = await db.start_shift(
            guild_id=guild.id,
            user_id=user.id,
            user_name=user.display_name,
            start_time=now
        )

        if success:
            embed = create_shift_started_embed(user=user, start_time=now)
            await interaction.response.send_message(embed=embed, ephemeral=True)

            # Canlı Panelleri ve Logları Güncelle
            await panel_manager.update_active_shifts_panel(guild)
            log_embed = create_log_embed(
                action_type="START",
                user=user,
                details={
                    "🕒 Başlangıç": f"<t:{int(now.timestamp())}:T>",
                    "📅 Tarih": f"<t:{int(now.timestamp())}:D>"
                }
            )
            await panel_manager.send_audit_log(guild, log_embed)
        else:
            # Zaten aktif mesaisi var
            start_time_raw = shift_data.get("start_time") if shift_data else None
            start_time_desc = f"\n\nBaşlangıç Zamanınız: {get_discord_timestamp(start_time_raw, 'F')} ({get_discord_timestamp(start_time_raw, 'R')})" if start_time_raw else ""
            embed = create_warning_embed(
                title="Aktif Mesainiz Bulunuyor!",
                message=f"Zaten devam eden bir mesai oturumunuz mevcut.{start_time_desc}\n\nMesainizi bitirmek için lütfen **'Mesai Bitir'** butonunu kullanınız."
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(
        label="Mesai Bitir",
        style=discord.ButtonStyle.danger,
        emoji="🔴",
        custom_id="btn_end_shift"
    )
    async def end_shift_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Kullanıcının aktif mesaisini bitiren buton aksiyonu."""
        guild = interaction.guild
        if not guild:
            await interaction.response.send_message(
                embed=create_error_embed("Hata", "Bu buton yalnızca bir sunucu içerisinde kullanılabilir."),
                ephemeral=True
            )
            return

        user = interaction.user
        now = datetime.now(timezone.utc)

        success, result_data, message = await db.end_shift(
            guild_id=guild.id,
            user_id=user.id,
            end_time=now
        )

        if success and result_data:
            embed = create_shift_ended_embed(
                user=user,
                start_time=result_data["start_time"],
                end_time=result_data["end_time"],
                duration_seconds=result_data["duration_seconds"],
                total_completed_shifts=result_data["total_completed_shifts"],
                total_lifetime_seconds=result_data["total_lifetime_seconds"],
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

            # Canlı Panelleri ve Tabloyu Güncelle
            await panel_manager.update_all_panels(guild)

            # Kanal Temizliğini Tetikle (#mesai kanalı için)
            if isinstance(interaction.channel, discord.TextChannel):
                await panel_manager.cleanup_mesai_channel(interaction.channel)

            # Denetim Logunu Gönder
            log_embed = create_log_embed(
                action_type="END",
                user=user,
                details={
                    "⌛ Oturum Süresi": format_duration(result_data["duration_seconds"]),
                    "🏆 Genel Toplam": format_duration(result_data["total_lifetime_seconds"]),
                    "📈 Oturum Sayısı": f"{result_data['total_completed_shifts']} adet"
                }
            )
            await panel_manager.send_audit_log(guild, log_embed)
        else:
            # Açık mesaisi yok
            embed = create_error_embed(
                title="Açık Mesai Bulunamadı",
                message="Şu anda aktif veya devam eden bir mesai kaydınız bulunmuyor.\nÖnce **'Mesai Başlat'** butonuna basarak yeni bir mesai başlatabilirsiniz."
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(
        label="Mesai Süremi Öğren",
        style=discord.ButtonStyle.primary,
        emoji="⏱️",
        custom_id="btn_check_my_shift_duration"
    )
    async def check_shift_duration_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Kullanıcının toplam mesai süresini ve aktif durumunu anlık sorgulayan buton aksiyonu."""
        guild = interaction.guild
        if not guild:
            await interaction.response.send_message(
                embed=create_error_embed("Hata", "Bu buton yalnızca bir sunucu içerisinde kullanılabilir."),
                ephemeral=True
            )
            return

        user = interaction.user
        stats = await db.get_user_stats(guild_id=guild.id, user_id=user.id)

        is_active = stats.get("is_active", False)
        active_shift = stats.get("active_shift")
        completed_shifts = stats.get("total_shifts", 0)
        past_duration = stats.get("total_duration", 0)

        # Veritabanında hiç mesai kaydı bulunmayan kullanıcılar için kontrol
        if not is_active and completed_shifts == 0 and past_duration == 0:
            embed = create_warning_embed(
                title="Mesai Kaydı Bulunamadı",
                message="Henüz kayıtlı bir mesai geçmişiniz bulunmamaktadır.\n\nMesaiye başlamak için lütfen **'Mesai Başlat'** butonunu kullanınız."
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        active_session_seconds = 0
        active_start_dt = None
        if is_active and active_shift:
            start_time_raw = active_shift.get("start_time")
            active_start_dt = parse_iso_or_datetime(start_time_raw)
            if active_start_dt:
                if active_start_dt.tzinfo is None:
                    active_start_dt = active_start_dt.replace(tzinfo=timezone.utc)
                now = datetime.now(timezone.utc)
                active_session_seconds = max(0, int((now - active_start_dt).total_seconds()))

        total_duration_seconds = past_duration + active_session_seconds

        embed = create_user_shift_duration_embed(
            user=user,
            total_duration_seconds=total_duration_seconds,
            completed_shifts_count=completed_shifts,
            is_active=is_active,
            active_session_seconds=active_session_seconds,
            active_start_time=active_start_dt
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

