import logging
import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional

from config import config
from database import db
from services.panel_manager import panel_manager
from views.admin_view import AdminView
from views.shift_view import ShiftView
from utils.permissions import has_admin_permission
from utils.formatters import (
    create_admin_panel_embed,
    create_leaderboard_embed,
    create_live_active_shifts_embed,
    create_shift_panel_embed,
    create_log_embed,
    create_error_embed,
    format_duration,
)

logger = logging.getLogger("Lucas2MesaiBot.AdminCog")

class AdminCog(commands.Cog):
    """Yönetici kontrolleri, panel kurulumları ve raporlama komut seti."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ==========================================
    # KURULUM KOMUTLARI (SETUP)
    # ==========================================

    @app_commands.command(
        name="kurulum-aktif-mesailer",
        description="#aktif-mesailer kanalına dinamik güncellenen Canlı Aktif Mesai panelini kurar."
    )
    @app_commands.describe(kanal="Canlı panelin gönderileceği metin kanalı (Boş bırakılırsa mevcut kanal kullanılır)")
    async def setup_aktif_mesailer(self, interaction: discord.Interaction, kanal: Optional[discord.TextChannel] = None):
        """#aktif-mesailer paneli kurulum komutu."""
        if not has_admin_permission(interaction.user):
            await interaction.response.send_message(
                embed=create_error_embed("Yetkisiz Erişim", "Bu komutu yalnızca yöneticiler kullanabilir."),
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

        try:
            await target_channel.purge(limit=20, check=lambda m: not m.pinned)
            active_shifts = await db.get_all_active_shifts(interaction.guild_id)
            embed = create_live_active_shifts_embed(active_shifts)
            msg = await target_channel.send(embed=embed)

            await db.set_setting(interaction.guild_id, "panel_aktif_mesailer_channel_id", str(target_channel.id))
            await db.set_setting(interaction.guild_id, "panel_aktif_mesailer_message_id", str(msg.id))

            await interaction.response.send_message(
                f"🟢 Canlı Aktif Mesai paneli başarıyla {target_channel.mention} kanalına kuruldu!",
                ephemeral=True
            )
        except discord.Forbidden:
            await interaction.response.send_message(
                embed=create_error_embed("Yetki Hatası", f"Botun {target_channel.mention} kanalına mesaj gönderme yetkisi yok."),
                ephemeral=True
            )

    @app_commands.command(
        name="kurulum-mesai-tablo",
        description="#mesai-tablo kanalına genel sıralama ve istatistik panelini kurar."
    )
    @app_commands.describe(kanal="Sıralama panelinin gönderileceği kanal (Boş bırakılırsa mevcut kanal kullanılır)")
    async def setup_mesai_tablo(self, interaction: discord.Interaction, kanal: Optional[discord.TextChannel] = None):
        """#mesai-tablo paneli kurulum komutu."""
        if not has_admin_permission(interaction.user):
            await interaction.response.send_message(
                embed=create_error_embed("Yetkisiz Erişim", "Bu komutu yalnızca yöneticiler kullanabilir."),
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

        try:
            await target_channel.purge(limit=20, check=lambda m: not m.pinned)
            reports = await db.get_guild_report(interaction.guild_id)
            embed = create_leaderboard_embed(reports, interaction.guild)
            msg = await target_channel.send(embed=embed)

            await db.set_setting(interaction.guild_id, "panel_mesai_tablo_channel_id", str(target_channel.id))
            await db.set_setting(interaction.guild_id, "panel_mesai_tablo_message_id", str(msg.id))

            await interaction.response.send_message(
                f"🏆 Mesai Sıralama Tablosu başarıyla {target_channel.mention} kanalına kuruldu!",
                ephemeral=True
            )
        except discord.Forbidden:
            await interaction.response.send_message(
                embed=create_error_embed("Yetki Hatası", f"Botun {target_channel.mention} kanalına mesaj gönderme yetkisi yok."),
                ephemeral=True
            )

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
            await target_channel.purge(limit=20, check=lambda m: not m.pinned)
            panel_msg = await target_channel.send(embed=embed, view=view)

            await db.set_setting(interaction.guild_id, "panel_admin_channel_id", str(target_channel.id))
            await db.set_setting(interaction.guild_id, "panel_admin_message_id", str(panel_msg.id))

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
        name="kurulum-hepsi",
        description="Tek tıkla tüm mesai kanallarını ve panellerini otomatik olarak kurar."
    )
    async def setup_all(self, interaction: discord.Interaction):
        """Tek tıkla tam otomatik sunucu kurulumu."""
        if not has_admin_permission(interaction.user):
            await interaction.response.send_message(
                embed=create_error_embed("Yetkisiz Erişim", "Bu komutu yalnızca yöneticiler kullanabilir."),
                ephemeral=True
            )
            return

        guild = interaction.guild
        if not guild:
            await interaction.response.send_message("Bu komut yalnızca sunucularda çalıştırılabilir.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        created_channels = []
        panels_info = [
            ("mesai", "panel_mesai_channel_id", "panel_mesai_message_id", "Mesai Başlat/Bitir Paneli"),
            ("aktif-mesailer", "panel_aktif_mesailer_channel_id", "panel_aktif_mesailer_message_id", "Canlı Aktif Mesai Paneli"),
            ("mesai-tablo", "panel_mesai_tablo_channel_id", "panel_mesai_tablo_message_id", "Genel Mesai Tablosu"),
            ("admin-settings", "panel_admin_channel_id", "panel_admin_message_id", "Yönetici Paneli"),
            ("mesai-log", "panel_log_channel_id", None, "Mesai Denetim Log Kanalı"),
        ]

        # Kategori bul veya oluştur
        category = discord.utils.get(guild.categories, name="⏱️ MESAİ SİSTEMİ")
        if not category:
            try:
                category = await guild.create_category("⏱️ MESAİ SİSTEMİ")
            except Exception:
                category = None

        for ch_name, db_ch_key, db_msg_key, desc in panels_info:
            target_ch = discord.utils.get(guild.text_channels, name=ch_name)
            if not target_ch:
                try:
                    target_ch = await guild.create_text_channel(name=ch_name, category=category)
                except Exception as e:
                    logger.error(f"Kanal oluşturulamadı ({ch_name}): {e}")
                    continue

            await db.set_setting(guild.id, db_ch_key, str(target_ch.id))

            # Panele göre mesaj gönder
            if ch_name == "mesai":
                await target_ch.purge(limit=20, check=lambda m: not m.pinned)
                msg = await target_ch.send(embed=create_shift_panel_embed(), view=ShiftView())
                await db.set_setting(guild.id, db_msg_key, str(msg.id))
            elif ch_name == "aktif-mesailer":
                await target_ch.purge(limit=20, check=lambda m: not m.pinned)
                active = await db.get_all_active_shifts(guild.id)
                msg = await target_ch.send(embed=create_live_active_shifts_embed(active))
                await db.set_setting(guild.id, db_msg_key, str(msg.id))
            elif ch_name == "mesai-tablo":
                await target_ch.purge(limit=20, check=lambda m: not m.pinned)
                reports = await db.get_guild_report(guild.id)
                msg = await target_ch.send(embed=create_leaderboard_embed(reports, guild))
                await db.set_setting(guild.id, db_msg_key, str(msg.id))
            elif ch_name == "admin-settings":
                await target_ch.purge(limit=20, check=lambda m: not m.pinned)
                msg = await target_ch.send(embed=create_admin_panel_embed(), view=AdminView())
                await db.set_setting(guild.id, db_msg_key, str(msg.id))

            created_channels.append(f"• {target_ch.mention} ({desc})")

        response_text = "🎉 **Otomatik Kurulum Başarıyla Tamamlandı!**\n\nAşağıdaki kanallar ve paneller aktif edildi:\n" + "\n".join(created_channels)
        await interaction.followup.send(response_text, ephemeral=True)

    @app_commands.command(
        name="mesai-temizle",
        description="Belirtilen mesai kanalındaki kirliliği temizler ve yalnızca ana paneli bırakır."
    )
    @app_commands.describe(kanal="Temizlenecek kanal (Boş bırakılırsa mevcut kanal)")
    async def cleanup_channel_command(self, interaction: discord.Interaction, kanal: Optional[discord.TextChannel] = None):
        """Kanal temizleme komutu."""
        if not has_admin_permission(interaction.user):
            await interaction.response.send_message(
                embed=create_error_embed("Yetkisiz Erişim", "Bu komutu yalnızca yöneticiler kullanabilir."),
                ephemeral=True
            )
            return

        target_ch = kanal or interaction.channel
        if not isinstance(target_ch, discord.TextChannel):
            await interaction.response.send_message("Lütfen geçerli bir metin kanalı belirtiniz.", ephemeral=True)
            return

        deleted_count = await panel_manager.cleanup_mesai_channel(target_ch)
        await interaction.response.send_message(
            f"🧹 {target_ch.mention} kanalında **{deleted_count}** adet gereksiz mesaj temizlendi.",
            ephemeral=True
        )

    # ==========================================
    # YÖNETİCİ RAPOR VE MÜDAHALE
    # ==========================================

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
        embed = create_leaderboard_embed(reports=reports, guild=guild)
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

            # Panelleri ve Denetim Logunu Güncelle
            await panel_manager.update_all_panels(guild)
            log_embed = create_log_embed(
                action_type="FORCE_CLOSED",
                user=kullanici,
                details={
                    "👮 Kapatan Yetkili": interaction.user.display_name,
                    "⌛ Kaydedilen Süre": format_duration(result["duration_seconds"])
                }
            )
            await panel_manager.send_audit_log(guild, log_embed)
        else:
            await interaction.response.send_message(
                embed=create_error_embed("İşlem Başarısız", message),
                ephemeral=True
            )

async def setup(bot: commands.Bot):
    await bot.add_cog(AdminCog(bot))

