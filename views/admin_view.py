import discord
from database import db
from utils.permissions import has_admin_permission
from utils.formatters import (
    create_admin_report_embed,
    create_active_shifts_embed,
    create_error_embed,
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
        custom_id="btn_get_report"
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
        custom_id="btn_active_shifts"
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
