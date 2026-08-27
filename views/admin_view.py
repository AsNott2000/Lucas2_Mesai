from datetime import datetime, timezone
import discord
from database import db
from services.panel_manager import panel_manager
from utils.permissions import has_admin_permission
from utils.formatters import (
    create_admin_report_embed,
    create_active_shifts_embed,
    create_error_embed,
    create_warning_embed,
    create_log_embed,
    format_duration,
)

class AdminView(discord.ui.View):
    """
    #admin-settings kanalındaki kalıcı (Persistent) yönetim butonlarını barındıran View sınıfı.
    timeout=None ve custom_id değerleri sayesinde bot restart attığında da yetki doğrulamasıyla çalışır.
    """

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Genel Rapor Al",
        style=discord.ButtonStyle.primary,
        emoji="📊",
        custom_id="btn_get_report",
        row=0
    )
    async def get_report_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Yetkili kullanıcılara tüm personellerin mesai sürelerini özetleyen rapor sunar."""
        guild = interaction.guild
        if not guild:
            await interaction.response.send_message(
                embed=create_error_embed("Hata", "Bu işlem yalnızca bir sunucu içerisinde çalıştırılabilir."),
                ephemeral=True
            )
            return

        # Yetki Doğrulaması
        if not has_admin_permission(interaction.user):
            await interaction.response.send_message(
                embed=create_error_embed(
                    "Yetkisiz Erişim Engellendi",
                    "Bu raporu görüntüleme yetkiniz bulunmamaktadır. Yalnızca Yöneticiler veya Yetkili Rolüne sahip kişiler erişebilir."
                ),
                ephemeral=True
            )
            return

        # Rapor verilerini çek
        reports = await db.get_guild_report(guild.id)
        embed = create_admin_report_embed(reports=reports, guild=guild)

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(
        label="Anlık Aktif Mesailer",
        style=discord.ButtonStyle.secondary,
        emoji="🟢",
        custom_id="btn_active_shifts",
        row=0
    )
    async def active_shifts_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Şu anda aktif görevde olan personelleri anlık listeler."""
        guild = interaction.guild
        if not guild:
            await interaction.response.send_message(
                embed=create_error_embed("Hata", "Bu işlem yalnızca bir sunucu içerisinde çalıştırılabilir."),
                ephemeral=True
            )
            return

        # Yetki Doğrulaması
        if not has_admin_permission(interaction.user):
            await interaction.response.send_message(
                embed=create_error_embed(
                    "Yetkisiz Erişim Engellendi",
                    "Bu bilgiyi görüntüleme yetkiniz bulunmamaktadır."
                ),
                ephemeral=True
            )
            return

        active_shifts = await db.get_all_active_shifts(guild.id)
        embed = create_active_shifts_embed(active_shifts)

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(
        label="Tüm Mesaileri Kapat",
        style=discord.ButtonStyle.danger,
        emoji="🛑",
        custom_id="btn_force_close_all",
        row=1
    )
    async def force_close_all_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Sunucuda devam eden tüm aktif mesaileri anlık zaman damgasıyla toplu olarak sonlandırır."""
        guild = interaction.guild
        if not guild:
            await interaction.response.send_message(
                embed=create_error_embed("Hata", "Bu işlem yalnızca bir sunucu içerisinde çalıştırılabilir."),
                ephemeral=True
            )
            return

        # Yetki Doğrulaması
        if not has_admin_permission(interaction.user):
            await interaction.response.send_message(
                embed=create_error_embed(
                    "Yetkisiz Erişim Engellendi",
                    "Bu işlemi gerçekleştirme yetkiniz bulunmamaktadır. Yalnızca Yöneticiler veya Yetkili Rolüne sahip kişiler erişebilir."
                ),
                ephemeral=True
            )
            return

        # Aktif mesaileri sorgula
        active_shifts = await db.get_all_active_shifts(guild.id)
        if not active_shifts:
            await interaction.response.send_message(
                embed=create_warning_embed(
                    title="Aktif Mesai Bulunamadı",
                    message="Şu anda sunucuda devam eden aktif bir personel mesaisi bulunmamaktadır."
                ),
                ephemeral=True
            )
            return

        now = datetime.now(timezone.utc)
        count, closed_records = await db.force_end_all_shifts(
            guild_id=guild.id,
            admin_name=interaction.user.display_name
        )

        # Canlı Panelleri Anında Güncelle
        await panel_manager.update_all_panels(guild)

        # Denetim Logunu Gönder
        log_embed = create_log_embed(
            action_type="FORCE_CLOSED_ALL",
            user=interaction.user,
            details={
                "👮 İşlemi Yapan Yetkili": interaction.user.display_name,
                "👥 Kapatılan Mesai Sayısı": f"{count} personel",
                "🕒 Kapatılma Zamanı": f"<t:{int(now.timestamp())}:F>"
            }
        )
        await panel_manager.send_audit_log(guild, log_embed)

        # Yöneticiye Özet Ephemeral Rapor Hazırla
        summary_embed = discord.Embed(
            title="🛑 Tüm Aktif Mesailer Başarıyla Kapatıldı",
            description=f"Sunucudaki **{count}** personelin açık olan mesai oturumu başarıyla sonlandırıldı.",
            color=0xE74C3C
        )
        summary_embed.add_field(name="👮 Kapatan Yetkili", value=interaction.user.mention, inline=True)
        summary_embed.add_field(name="👥 Kapatılan Personel Sayısı", value=f"**{count}** kişi", inline=True)
        summary_embed.add_field(name="🕒 Kapatılma Zamanı", value=f"<t:{int(now.timestamp())}:F>", inline=False)

        if closed_records:
            user_list = [
                f"• <@{rec['user_id']}> (`{rec['user_name']}`) — Süre: `{format_duration(rec['duration_seconds'])}`"
                for rec in closed_records[:10]
            ]
            if len(closed_records) > 10:
                user_list.append(f"... ve {len(closed_records) - 10} kişi daha.")
            summary_embed.add_field(name="📋 Kapatılan Personeller", value="\n".join(user_list), inline=False)

        summary_embed.set_footer(text="Lucas2 Yönetim Paneli • Canlı Paneller Güncellendi")
        summary_embed.timestamp = now

        await interaction.response.send_message(embed=summary_embed, ephemeral=True)
