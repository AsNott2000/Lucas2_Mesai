import logging
import discord
from datetime import datetime, timezone
from database import db
from services.panel_manager import panel_manager
from utils.formatters import (
    create_shift_started_embed,
    create_shift_ended_embed,
    create_warning_embed,
    create_error_embed,
    create_log_embed,
    format_duration,
    get_discord_timestamp,
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

