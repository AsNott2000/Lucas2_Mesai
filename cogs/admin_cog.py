import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional
from config import config
from database import db
from views.admin_view import AdminView
from utils.permissions import has_admin_permission
from utils.formatters import (
    create_admin_panel_embed,
    create_admin_report_embed,
    create_error_embed,
    format_duration,
)

class AdminCog(commands.Cog):
    """Yönetici kontrolleri ve raporlama komut seti."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="kurulum-admin",
        description="Belirtilen kanala kalıcı Yönetici Kontrol ve Rapor panelini gönderir."
    )
    @app_commands.describe(kanal="Yönetici panelinin gönderileceği kanal (Boş bırakılırsa mevcut kanal kullanılır)")
    async def setup_admin(self, interaction: discord.Interaction, kanal: Optional[discord.TextChannel] = None):
        """#admin-settings kanalına kalıcı yönetim panelini kurar."""
        if not has_admin_permission(interaction.user):
            await interaction.response.send_message(
                embed=create_error_embed("Yetkisiz Erişim", "Bu kurulum komutunu yalnızca yöneticiler kullanabilir."),
                ephemeral=True
            )
            return

        target_channel = kanal or interaction.channel
        if not isinstance(target_channel, discord.TextChannel):
            await interaction.response.send_message(
                embed=create_error_embed("Hata", "Lütfen geçerli bir metin kanalı belirtiniz."),
                ephemeral=True
            )
            return

        embed = create_admin_panel_embed()
        view = AdminView()

        try:
            await target_channel.send(embed=embed, view=view)
            await interaction.response.send_message(
                f"🛡️ Yönetici paneli başarıyla {target_channel.mention} kanalına gönderildi!",
                ephemeral=True
            )
        except discord.Forbidden:
            await interaction.response.send_message(
                embed=create_error_embed("Yetki Hatası", f"Botun {target_channel.mention} kanalına mesaj gönderme yetkisi yok."),
                ephemeral=True
            )

    @app_commands.command(
        name="mesai-rapor",
        description="Tüm personellerin mesai sürelerini ve oturum sayılarını listeler."
    )
    async def report_command(self, interaction: discord.Interaction):
        """Yönetici raporunu slash komut olarak sunar."""
        if not has_admin_permission(interaction.user):
            await interaction.response.send_message(
                embed=create_error_embed("Yetkisiz Erişim", "Bu komutu yalnızca yöneticiler kullanabilir."),
                ephemeral=True
            )
            return

        guild = interaction.guild
        if not guild:
            await interaction.response.send_message("Bu komut yalnızca sunucularda kullanılabilir.", ephemeral=True)
            return

        reports = await db.get_guild_report(guild.id)
        embed = create_admin_report_embed(reports=reports, guild=guild)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(
        name="mesai-bitir-yetkili",
        description="Açık unutulmuş bir personelin mesaisini yönetici olarak zorla sonlandırır."
    )
    @app_commands.describe(kullanici="Mesaisi kapatılacak personel")
    async def force_end_command(self, interaction: discord.Interaction, kullanici: discord.Member):
        """Yetkili tarafından açık mesaiyi kapatma komutu."""
        if not has_admin_permission(interaction.user):
            await interaction.response.send_message(
                embed=create_error_embed("Yetkisiz Erişim", "Bu komutu yalnızca yöneticiler kullanabilir."),
                ephemeral=True
            )
            return

        guild = interaction.guild
        if not guild:
            await interaction.response.send_message("Bu komut yalnızca sunucularda kullanılabilir.", ephemeral=True)
            return

        success, result, message = await db.force_end_shift(
            guild_id=guild.id,
            user_id=kullanici.id,
            admin_name=interaction.user.display_name
        )

        if success and result:
            embed = discord.Embed(
                title="⚠️ Mesai Yönetici Tarafından Kapatıldı",
                description=f"**{kullanici.mention}** kullanıcısının açık mesaisi başarıyla sonlandırıldı.",
                color=0xE67E22  # Orange
            )
            embed.add_field(name="⌛ Hesaplanan Süre", value=format_duration(result["duration_seconds"]), inline=True)
            embed.add_field(name="👮 Kapatan Yetkili", value=interaction.user.display_name, inline=True)
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message(
                embed=create_error_embed("İşlem Başarısız", message),
                ephemeral=True
            )

async def setup(bot: commands.Bot):
    await bot.add_cog(AdminCog(bot))
