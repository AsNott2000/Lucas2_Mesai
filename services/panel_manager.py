import logging
import discord
from typing import Optional
from discord.ext import commands
from config import config
from database import db
from utils.formatters import (
    create_live_active_shifts_embed,
    create_leaderboard_embed,
    create_shift_panel_embed,
)

logger = logging.getLogger("Lucas2MesaiBot.PanelManager")

class PanelManager:
    """Sunucu kanallarındaki canlı panellerin (Live Embeds) ve temizliğin yönetim servisi."""

    @staticmethod
    async def get_target_channel(
        guild: discord.Guild,
        setting_key: str,
        config_id: Optional[int],
        fallback_name: str
    ) -> Optional[discord.TextChannel]:
        """
        Kanalı sırasıyla veritabanı ayarlarından, config dosyasından veya kanal isminden tespit eder.
        """
        # 1. DB Ayarından bak
        saved_id_str = await db.get_setting(guild.id, setting_key)
        if saved_id_str and saved_id_str.isdigit():
            ch = guild.get_channel(int(saved_id_str))
            if isinstance(ch, discord.TextChannel):
                return ch

        # 2. Config dosyasından bak
        if config_id:
            ch = guild.get_channel(config_id)
            if isinstance(ch, discord.TextChannel):
                return ch

        # 3. İsim benzerliğinden bak
        for ch in guild.text_channels:
            clean_name = ch.name.lower().replace("-", "").replace("_", "")
            target_clean = fallback_name.lower().replace("-", "").replace("_", "")
            if clean_name == target_clean or target_clean in clean_name:
                return ch

        return None

    @classmethod
    async def update_active_shifts_panel(cls, guild: discord.Guild) -> bool:
        """#aktif-mesailer kanalındaki canlı mesai listesi panelini günceller."""
        try:
            channel = await cls.get_target_channel(
                guild=guild,
                setting_key="panel_aktif_mesailer_channel_id",
                config_id=config.AKTIF_MESAILER_CHANNEL_ID,
                fallback_name="aktif-mesailer"
            )
            if not channel:
                return False

            active_shifts = await db.get_all_active_shifts(guild.id)
            embed = create_live_active_shifts_embed(active_shifts)

            saved_msg_id_str = await db.get_setting(guild.id, "panel_aktif_mesailer_message_id")
            if saved_msg_id_str and saved_msg_id_str.isdigit():
                try:
                    msg = await channel.fetch_message(int(saved_msg_id_str))
                    await msg.edit(embed=embed)
                    return True
                except (discord.NotFound, discord.HTTPException):
                    pass

            # Mesaj bulunamadıysa veya silinmişse yenisini oluştur
            new_msg = await channel.send(embed=embed)
            await db.set_setting(guild.id, "panel_aktif_mesailer_channel_id", str(channel.id))
            await db.set_setting(guild.id, "panel_aktif_mesailer_message_id", str(new_msg.id))
            logger.info(f"Yeni #aktif-mesailer paneli oluşturuldu (Kanal: {channel.name}, Msg ID: {new_msg.id})")
            return True
        except Exception as e:
            logger.error(f"Aktif mesailer paneli güncellenirken hata ({guild.name}): {e}", exc_info=True)
            return False

    @classmethod
    async def update_leaderboard_panel(cls, guild: discord.Guild) -> bool:
        """#mesai-tablo kanalındaki genel istatistik ve sıralama panelini günceller."""
        try:
            channel = await cls.get_target_channel(
                guild=guild,
                setting_key="panel_mesai_tablo_channel_id",
                config_id=config.MESAI_TABLO_CHANNEL_ID,
                fallback_name="mesai-tablo"
            )
            if not channel:
                return False

            reports = await db.get_guild_report(guild.id)
            embed = create_leaderboard_embed(reports, guild)

            saved_msg_id_str = await db.get_setting(guild.id, "panel_mesai_tablo_message_id")
            if saved_msg_id_str and saved_msg_id_str.isdigit():
                try:
                    msg = await channel.fetch_message(int(saved_msg_id_str))
                    await msg.edit(embed=embed)
                    return True
                except (discord.NotFound, discord.HTTPException):
                    pass

            # Mesaj bulunamadıysa yenisini gönder
            new_msg = await channel.send(embed=embed)
            await db.set_setting(guild.id, "panel_mesai_tablo_channel_id", str(channel.id))
            await db.set_setting(guild.id, "panel_mesai_tablo_message_id", str(new_msg.id))
            logger.info(f"Yeni #mesai-tablo paneli oluşturuldu (Kanal: {channel.name}, Msg ID: {new_msg.id})")
            return True
        except Exception as e:
            logger.error(f"Mesai tablosu paneli güncellenirken hata ({guild.name}): {e}", exc_info=True)
            return False

    @classmethod
    async def update_all_panels(cls, guild: discord.Guild) -> None:
        """Sunucudaki tüm canlı panelleri eşzamanlı olarak yeniler."""
        await cls.update_active_shifts_panel(guild)
        await cls.update_leaderboard_panel(guild)

    @classmethod
    async def cleanup_mesai_channel(cls, channel: discord.TextChannel, panel_message_id: Optional[int] = None) -> int:
        """
        #mesai kanalındaki gereksiz kullanıcı ve sistem mesajlarını temizler.
        Yalnızca ana butonlu paneli korur.
        """
        if not panel_message_id:
            saved_id_str = await db.get_setting(channel.guild.id, "panel_mesai_message_id")
            if saved_id_str and saved_id_str.isdigit():
                panel_message_id = int(saved_id_str)

        def should_delete(message: discord.Message) -> bool:
            if panel_message_id and message.id == panel_message_id:
                return False
            # Pinned mesajları koru
            if message.pinned:
                return False
            return True

        try:
            deleted = await channel.purge(limit=50, check=should_delete)
            return len(deleted)
        except Exception as e:
            logger.warning(f"Kanal temizliği yapılırken hata ({channel.name}): {e}")
            return 0

    @classmethod
    async def send_audit_log(cls, guild: discord.Guild, embed: discord.Embed) -> None:
        """Denetim log kanalına bildirim iletir."""
        try:
            log_channel = await cls.get_target_channel(
                guild=guild,
                setting_key="panel_log_channel_id",
                config_id=config.LOG_CHANNEL_ID,
                fallback_name="mesai-log"
            )
            if log_channel:
                await log_channel.send(embed=embed)
        except Exception as e:
            logger.warning(f"Log mesajı gönderilirken hata: {e}")

panel_manager = PanelManager()
