import logging
import asyncio
from datetime import datetime, timezone
import discord
from discord.ext import commands, tasks
from typing import Dict, Any, Optional

from config import config
from database import db
from services.panel_manager import panel_manager
from views.afk_view import AFKVerificationView
from utils.formatters import (
    create_afk_prompt_embed,
    create_afk_timeout_embed,
    create_log_embed,
    parse_iso_or_datetime,
    format_duration,
)

logger = logging.getLogger("Lucas2MesaiBot.TrackerCog")

class TrackerCog(commands.Cog):
    """
    Arka plan zamanlanmış görevleri (Tasks):
    1. 45 Dakikalık AFK Doğrulama Sistemi
    2. Doğrulama Zaman Aşımı ve Otomatik Mesai Kapatma
    3. #aktif-mesailer ve #mesai-tablo Canlı Panellerinin Periyodik Senkronizasyonu
    4. #mesai Kanalı Otomatik Mesaj Temizleme Dinleyicisi
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._loop_counter = 0
        self.tracker_loop.start()

    def cog_unload(self):
        self.tracker_loop.cancel()

    @tasks.loop(seconds=15)
    async def tracker_loop(self):
        """Her 15 saniyede bir çalışan ana arka plan denetleyicisi."""
        self._loop_counter += 1
        now = datetime.now(timezone.utc)

        try:
            active_shifts = await db.get_all_active_shifts_global()
            if not active_shifts:
                # Aktif mesai yoksa ama periyodik güncelleme sırası geldiyse (her 2 dakikada bir = 8 döngü)
                if self._loop_counter % 8 == 0:
                    for guild in self.bot.guilds:
                        await panel_manager.update_active_shifts_panel(guild)
                return

            afk_interval_sec = config.AFK_CHECK_INTERVAL_MINUTES * 60
            timeout_sec = config.AFK_TIMEOUT_MINUTES * 60

            for shift in active_shifts:
                guild_id = shift["guild_id"]
                user_id = shift["user_id"]

                guild = self.bot.get_guild(guild_id)
                if not guild:
                    continue

                member = guild.get_member(user_id)
                if not member:
                    try:
                        member = await guild.fetch_member(user_id)
                    except Exception:
                        member = None

                # Doğrulama zamanlarını kontrol et
                last_verified_str = shift.get("last_verified_at") or shift.get("start_time")
                last_verified_dt = parse_iso_or_datetime(last_verified_str)
                if not last_verified_dt:
                    continue
                if last_verified_dt.tzinfo is None:
                    last_verified_dt = last_verified_dt.replace(tzinfo=timezone.utc)

                verification_sent_str = shift.get("verification_sent_at")
                verification_sent_dt = parse_iso_or_datetime(verification_sent_str)
                if verification_sent_dt and verification_sent_dt.tzinfo is None:
                    verification_sent_dt = verification_sent_dt.replace(tzinfo=timezone.utc)

                # DURUM 1: Henüz doğrulama gönderilmemiş ve 45 dakika dolmuş
                if not verification_sent_dt:
                    elapsed_since_verified = (now - last_verified_dt).total_seconds()
                    if elapsed_since_verified >= afk_interval_sec:
                        await self._send_afk_verification_prompt(guild, member, user_id, now)

                # DURUM 2: Doğrulama mesajı gönderilmiş ve bekleme süresi (1 dk) aşılmış
                else:
                    elapsed_since_prompt = (now - verification_sent_dt).total_seconds()
                    if elapsed_since_prompt >= timeout_sec:
                        await self._handle_afk_timeout(guild, member, user_id, now)

            # Her 1 dakikada bir (4 döngüde bir) canlı panelleri güncelle
            if self._loop_counter % 4 == 0:
                for guild in self.bot.guilds:
                    await panel_manager.update_active_shifts_panel(guild)

            # Her 5 dakikada bir (20 döngüde bir) genel tabloyu güncelle
            if self._loop_counter % 20 == 0:
                for guild in self.bot.guilds:
                    await panel_manager.update_leaderboard_panel(guild)

        except Exception as e:
            logger.error(f"Tracker döngüsünde beklenmeyen hata: {e}", exc_info=True)

    @tracker_loop.before_loop
    async def before_tracker_loop(self):
        """Bot tamamen hazır olana kadar bekle."""
        await self.bot.wait_until_ready()
        logger.info("AFK ve Canlı Panel Takip Döngüsü (TrackerLoop) başlatıldı.")

    async def _send_afk_verification_prompt(
        self, guild: discord.Guild, member: Optional[discord.Member], user_id: int, now: datetime
    ):
        """Kullanıcıya DM veya kanal üzerinden 45 dakikalık AFK doğrulama butonu gönderir."""
        await db.set_verification_sent(guild.id, user_id, now)

        user_obj = member
        if not user_obj:
            try:
                user_obj = await self.bot.fetch_user(user_id)
            except Exception:
                pass

        if not user_obj:
            logger.warning(f"Kullanıcı ID {user_id} Discord üzerinde bulunamadı.")
            return

        embed = create_afk_prompt_embed(
            user=user_obj,
            minutes_active=config.AFK_CHECK_INTERVAL_MINUTES,
            timeout_minutes=config.AFK_TIMEOUT_MINUTES
        )
        view = AFKVerificationView()

        dm_sent = False
        try:
            await user_obj.send(embed=embed, view=view)
            dm_sent = True
            logger.info(f"Kullanıcıya ({user_obj.name}) DM üzerinden 45 dk AFK doğrulama mesajı gönderildi.")
        except (discord.Forbidden, discord.HTTPException):
            logger.warning(f"Kullanıcıya ({user_obj.name}) DM kapalı olduğu için mesaj iletilemedi.")

        # DM kapalıysa ve sunucuda log/mesai kanalı varsa alternatif uyarı bırak
        if not dm_sent and member:
            mesai_ch = await panel_manager.get_target_channel(
                guild=guild,
                setting_key="panel_mesai_channel_id",
                config_id=config.MESAI_CHANNEL_ID,
                fallback_name="mesai"
            )
            if mesai_ch:
                try:
                    timeout_label = f"{config.AFK_TIMEOUT_MINUTES} dakika (60 saniye)" if config.AFK_TIMEOUT_MINUTES == 1 else f"{config.AFK_TIMEOUT_MINUTES} dakika"
                    await mesai_ch.send(
                        content=f"⚠️ {member.mention} **Mesai Doğrulaması:** DM kutunuz kapalı olduğu için buraya iletildi! Lütfen {timeout_label} içinde onaylayınız (Aksi halde son 45 dakikanız silinecektir):",
                        embed=embed,
                        view=view,
                        delete_after=config.AFK_TIMEOUT_MINUTES * 60
                    )
                except Exception as e:
                    logger.warning(f"Kanal üzerinden AFK uyarısı gönderilemedi: {e}")

    async def _handle_afk_timeout(
        self, guild: discord.Guild, member: Optional[discord.Member], user_id: int, now: datetime
    ):
        """Doğrulama yapmayan personelin mesaisini otomatik kapatır, son 45 dakikayı siler ve loglar."""
        success, result_data, msg = await db.end_shift_afk(
            guild_id=guild.id,
            user_id=user_id,
            end_time=now,
            note="AFK - Doğrulama Yapılmadı (45 dk düşüldü)"
        )

        if not success or not result_data:
            return

        duration_sec = result_data["duration_seconds"]
        raw_duration_sec = result_data.get("raw_duration_seconds", duration_sec)
        deducted_sec = result_data.get("deducted_seconds", 0)
        user_name = result_data.get("user_name", str(user_id))

        logger.info(
            f"Personel {user_name} (ID: {user_id}) AFK zaman aşımı nedeniyle mesaisi kapatıldı "
            f"(Ham: {raw_duration_sec} sn, Düşülen: {deducted_sec} sn, Net: {duration_sec} sn)."
        )

        user_obj = member
        if not user_obj:
            try:
                user_obj = await self.bot.fetch_user(user_id)
            except Exception:
                pass

        # Kullanıcıya bilgilendirme DM'i gönder
        if user_obj:
            try:
                timeout_embed = create_afk_timeout_embed(
                    user=user_obj,
                    duration_seconds=duration_sec,
                    raw_duration_seconds=raw_duration_sec,
                    deducted_seconds=deducted_sec,
                    timeout_minutes=config.AFK_TIMEOUT_MINUTES
                )
                await user_obj.send(embed=timeout_embed)
            except Exception:
                pass

        # Denetim logu gönder
        if user_obj:
            log_embed = create_log_embed(
                action_type="AFK_TIMEOUT",
                user=user_obj,
                details={
                    "⏱️ Ham Oturum Süresi": format_duration(raw_duration_sec),
                    "⚠️ Uygulanan Ceza": f"-{format_duration(deducted_sec)} (45 dk silindi)",
                    "⌛ Kaydedilen Net Süre": format_duration(duration_sec),
                    "📌 Kapatma Nedeni": "AFK - Doğrulama Yapılmadı (45 dk düşüldü)",
                    "🕒 Kapatılma Zamanı": f"<t:{int(now.timestamp())}:F>"
                }
            )
            await panel_manager.send_audit_log(guild, log_embed)

        # Panelleri anında güncelle
        await panel_manager.update_all_panels(guild)

    # ==========================================
    # KANAL TEMİZLEME DİNLENMESİ (#mesai)
    # ==========================================

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """
        #mesai kanalında mesaj kirliliğini önler:
        Kullanıcılar tarafından atılan sohbet mesajlarını temizler.
        """
        if message.author.bot or not message.guild:
            return

        # Mesai kanalı olup olmadığını kontrol et
        saved_mesai_ch = await db.get_setting(message.guild.id, "panel_mesai_channel_id")
        is_mesai_channel = False

        if saved_mesai_ch and str(message.channel.id) == saved_mesai_ch:
            is_mesai_channel = True
        elif config.MESAI_CHANNEL_ID and message.channel.id == config.MESAI_CHANNEL_ID:
            is_mesai_channel = True
        elif message.channel.name.lower() == "mesai":
            is_mesai_channel = True

        if is_mesai_channel:
            # Mesajı temizle ve paneli temiz tut
            try:
                await message.delete()
            except (discord.Forbidden, discord.HTTPException):
                pass

async def setup(bot: commands.Bot):
    await bot.add_cog(TrackerCog(bot))
