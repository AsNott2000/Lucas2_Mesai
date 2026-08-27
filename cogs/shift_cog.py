import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional
from config import config
from database import db
from views.shift_view import ShiftView
from utils.permissions import has_admin_permission
from utils.formatters import (
    create_shift_panel_embed,
    create_error_embed,
    create_warning_embed,
    create_active_shifts_embed,
    format_duration,
    get_discord_timestamp,
)

class ShiftCog(commands.Cog):
    """Personel mesai ve vardiya işlemlerini yöneten komut seti."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="kurulum-mesai",
        description="Belirtilen kanala kalıcı Mesai Başlat / Bitir panelini gönderir ve kanalı temizler."
    )
    @app_commands.describe(kanal="Mesai panelinin gönderileceği metin kanalı (Boş bırakılırsa mevcut kanal kullanılır)")
    async def setup_mesai(self, interaction: discord.Interaction, kanal: Optional[discord.TextChannel] = None):
        """#mesai kanalına kalıcı kontrol panelini kurar ve kanal kirliliğini temizler."""
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

        embed = create_shift_panel_embed()
        view = ShiftView()

        try:
            # Önceki eski mesajları temizle
            await target_channel.purge(limit=50, check=lambda m: not m.pinned)
            
            # Kalıcı paneli gönder
            panel_msg = await target_channel.send(embed=embed, view=view)
            
            # Veritabanına panel bilgilerini kaydet
            await db.set_setting(interaction.guild_id, "panel_mesai_channel_id", str(target_channel.id))
            await db.set_setting(interaction.guild_id, "panel_mesai_message_id", str(panel_msg.id))

            await interaction.response.send_message(
                f"✅ Mesai paneli başarıyla {target_channel.mention} kanalına kuruldu ve kaydedildi!",
                ephemeral=True
            )
        except discord.Forbidden:
            await interaction.response.send_message(
                embed=create_error_embed("Yetki Hatası", f"Botun {target_channel.mention} kanalına mesaj gönderme veya silme yetkisi yok."),
                ephemeral=True
            )


    @app_commands.command(
        name="mesaim",
        description="Kendi aktif mesainizi ve toplam çalışma istatistiklerinizi görüntüler."
    )
    async def my_shift(self, interaction: discord.Interaction):
        """Kullanıcının bireysel mesai durumunu gösterir."""
        guild_id = interaction.guild_id
        if not guild_id:
            await interaction.response.send_message("Bu komut yalnızca sunucularda kullanılabilir.", ephemeral=True)
            return

        user = interaction.user
        stats = await db.get_user_stats(guild_id, user.id)

        embed = discord.Embed(
            title=f"👤 {user.display_name} - Mesai Bilgileriniz",
            color=0x5865F2
        )

        if stats["is_active"] and stats["active_shift"]:
            active = stats["active_shift"]
            start_time = active.get("start_time")
            embed.add_field(
                name="🟢 Aktif Mesai Durumu",
                value=f"Şu an **MESAİDESİNİZ**!\nBaşlangıç: {get_discord_timestamp(start_time, 'T')} ({get_discord_timestamp(start_time, 'R')})",
                inline=False
            )
        else:
            embed.add_field(
                name="⚪ Aktif Mesai Durumu",
                value="Şu anda aktif bir mesainiz bulunmuyor.",
                inline=False
            )

        embed.add_field(
            name="📊 Tamamlanan Oturum",
            value=f"**{stats['total_shifts']}** adet",
            inline=True
        )
        embed.add_field(
            name="⌛ Toplam Süre",
            value=f"**{format_duration(stats['total_duration'])}**",
            inline=True
        )

        if stats.get("last_ended"):
            embed.add_field(
                name="🕒 Son Mesai Bitişi",
                value=get_discord_timestamp(stats["last_ended"], "F"),
                inline=False
            )

        embed.set_footer(text="Lucas2 Mesai Takip")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(
        name="aktif-mesailer",
        description="Şu anda mesaide olan tüm personelleri listeler."
    )
    async def active_shifts_command(self, interaction: discord.Interaction):
        """Aktif mesaideki personelleri listeler."""
        guild_id = interaction.guild_id
        if not guild_id:
            await interaction.response.send_message("Bu komut yalnızca sunucularda kullanılabilir.", ephemeral=True)
            return

        active_shifts = await db.get_all_active_shifts(guild_id)
        embed = create_active_shifts_embed(active_shifts)
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(ShiftCog(bot))
