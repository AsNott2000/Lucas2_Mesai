import logging
from datetime import datetime, timezone
from typing import Optional, Callable
import discord

from config import config
from database import db
from services.captcha_service import CaptchaChallenge, CaptchaOption
from services.panel_manager import panel_manager
from utils.formatters import (
    create_captcha_success_embed,
    create_captcha_failed_embed,
    create_error_embed,
    create_log_embed,
    format_duration,
)

logger = logging.getLogger("Lucas2MesaiBot.CaptchaView")

class CaptchaVerificationView(discord.ui.View):
    """
    Kullanıcıya özel oluşturulan dinamik CAPTCHA doğrulama View'i.
    Tek kullanımlık butonlar, rastgele şıklar ve anti-spam mekanizması içerir.
    """

    def __init__(
        self,
        challenge: CaptchaChallenge,
        bot: Optional[discord.Client] = None,
        message: Optional[discord.Message] = None
    ):
        super().__init__(timeout=float(challenge.timeout_seconds))
        self.challenge = challenge
        self.bot = bot
        self.message = message
        self._build_buttons()

    def _build_buttons(self) -> None:
        """Challenge seçeneklerine göre dinamik butonları view'e ekler."""
        self.clear_items()
        for opt in self.challenge.options:
            button = discord.ui.Button(
                label=opt.name,
                emoji=opt.emoji,
                style=discord.ButtonStyle.secondary,
                custom_id=opt.custom_id
            )
            button.callback = self._create_callback(opt)
            self.add_item(button)

    def _create_callback(self, option: CaptchaOption) -> Callable:
        """Her buton için özel tıklama callback işleyicisini bağlar."""
        async def button_callback(interaction: discord.Interaction):
            await self._handle_selection(interaction, option)
        return button_callback

    async def _handle_selection(self, interaction: discord.Interaction, option: CaptchaOption) -> None:
        """Kullanıcının buton tıklamasını doğrular, doğru/yanlış aksiyonlarını yürütür."""
        user = interaction.user

        # 1. Yetki Kontrolü: Yalnızca hedef personel tıklayabilir
        if user.id != self.challenge.user_id:
            await interaction.response.send_message(
                embed=create_error_embed(
                    "Yetkisiz İşlem",
                    "Bu CAPTCHA doğrulaması başka bir personele aittir. Yalnızca ilgili personel yanıt verebilir."
                ),
                ephemeral=True
            )
            return

        # 2. Oturum Durumu Kontrolü (Çift tıklama önleme)
        if self.challenge.solved or self.challenge.failed:
            await interaction.response.send_message(
                embed=create_error_embed("Oturum Tamamlandı", "Bu doğrulama oturumu zaten tamamlanmıştır."),
                ephemeral=True
            )
            return

        # 3. Butonları anında devre dışı bırak
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True
                if item.custom_id == option.custom_id:
                    item.style = discord.ButtonStyle.success if option.is_correct else discord.ButtonStyle.danger

        # 4. Doğru Seçim Durumu
        if option.is_correct:
            self.challenge.solved = True
            now = datetime.now(timezone.utc)

            # Veritabanında doğrulamayı güncelle
            guild_id = self.challenge.guild_id or interaction.guild_id
            if guild_id:
                await db.update_last_verified(guild_id, user.id, now)
                logger.info(f"Kullanıcı {user.display_name} (ID: {user.id}) CAPTCHA'yı başarıyla tamamladı (Sunucu: {guild_id}).")
            else:
                # DM üzerinden yanıtlandıysa aktif mesaileri bul ve güncelle
                active_shifts = await db.get_all_active_shifts_global()
                user_shifts = [s for s in active_shifts if s["user_id"] == user.id]
                for s in user_shifts:
                    await db.update_last_verified(s["guild_id"], user.id, now)
                logger.info(f"Kullanıcı {user.display_name} (ID: {user.id}) DM üzerinden CAPTCHA'yı başarıyla tamamladı.")

            success_embed = create_captcha_success_embed(user, self.challenge)
            try:
                if interaction.message:
                    await interaction.response.edit_message(embed=success_embed, view=self)
                else:
                    await interaction.response.send_message(embed=success_embed, ephemeral=True)
            except Exception as e:
                logger.warning(f"CAPTCHA başarı mesajı düzenlenirken hata: {e}")
            self.stop()
            return

        # 5. Yanlış Seçim Durumu: Mesaiyi Ceza ile Kapat
        self.challenge.failed = True
        now = datetime.now(timezone.utc)
        guild_id = self.challenge.guild_id or interaction.guild_id

        if not guild_id:
            active_shifts = await db.get_all_active_shifts_global()
            user_shifts = [s for s in active_shifts if s["user_id"] == user.id]
            guild_id = user_shifts[0]["guild_id"] if user_shifts else None

        guild = self.bot.get_guild(guild_id) if (self.bot and guild_id) else getattr(interaction, "guild", None)

        success, result_data, msg = await db.end_shift_afk(
            guild_id=guild_id or 0,
            user_id=user.id,
            end_time=now,
            note=f"CAPTCHA Başarısız / AFK ({config.AFK_PENALTY_MINUTES} dk kesildi)"
        )

        duration_sec = result_data["duration_seconds"] if result_data else 0
        raw_duration_sec = result_data.get("raw_duration_seconds", duration_sec) if result_data else 0
        deducted_sec = result_data.get("deducted_seconds", 0) if result_data else 0

        logger.warning(
            f"Kullanıcı {user.display_name} (ID: {user.id}) CAPTCHA'da yanlış butona bastı ({option.name}). "
            f"Mesai sonlandırıldı (Ceza: {deducted_sec} sn)."
        )

        failed_embed = create_captcha_failed_embed(
            user=user,
            target_name=self.challenge.target_name,
            target_emoji=self.challenge.target_emoji,
            chosen_name=option.name,
            chosen_emoji=option.emoji,
            duration_seconds=duration_sec,
            raw_duration_seconds=raw_duration_sec,
            deducted_seconds=deducted_sec,
            penalty_minutes=config.AFK_PENALTY_MINUTES
        )

        try:
            if interaction.message:
                await interaction.response.edit_message(embed=failed_embed, view=self)
            else:
                await interaction.response.send_message(embed=failed_embed, ephemeral=True)
        except Exception as e:
            logger.warning(f"CAPTCHA hata mesajı düzenlenirken hata: {e}")

        # Denetim logunu ve panelleri güncelle
        if guild:
            log_embed = create_log_embed(
                action_type="AFK_TIMEOUT",
                user=user,
                details={
                    "⏱️ Ham Oturum Süresi": format_duration(raw_duration_sec),
                    "⚠️ Uygulanan Ceza": f"-{format_duration(deducted_sec)} ({config.AFK_PENALTY_MINUTES} dk silindi)",
                    "⌛ Kaydedilen Net Süre": format_duration(duration_sec),
                    "📌 Kapatma Nedeni": f"CAPTCHA Hatalı Seçim ({option.name}) - {config.AFK_PENALTY_MINUTES} dk ceza",
                    "🕒 Kapatılma Zamanı": f"<t:{int(now.timestamp())}:F>"
                }
            )
            await panel_manager.send_audit_log(guild, log_embed)
            await panel_manager.update_all_panels(guild)

        self.stop()

    async def on_timeout(self) -> None:
        """Zaman aşımı durumunda butonları devre dışı bırakır."""
        if not self.challenge.solved and not self.challenge.failed:
            for item in self.children:
                if isinstance(item, discord.ui.Button):
                    item.disabled = True
            if self.message:
                try:
                    await self.message.edit(view=self)
                except Exception:
                    pass
