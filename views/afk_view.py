import logging
import discord
from datetime import datetime, timezone
from database import db
from utils.formatters import create_afk_verified_embed, create_error_embed

logger = logging.getLogger("Lucas2MesaiBot.AFKView")

class AFKVerificationView(discord.ui.View):
    """
    AFK aktiflik doğrulama bildirimi için kalıcı (Persistent) buton view'i.
    Bot yeniden başlatılsa dahi timeout=None ve sabit custom_id sayesinde çalışır.
    """

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Buradayım / Mesaiyi Doğrula",
        style=discord.ButtonStyle.success,
        emoji="✅",
        custom_id="btn_afk_verify"
    )
    async def verify_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Kullanıcının aktiflik doğrulama butonuna tıklama aksiyonu."""
        user = interaction.user
        guild_id = interaction.guild_id

        # 1. Guild ID belirlenmesi (DM veya Sunucu)
        if not guild_id:
            # DM üzerinden tıklanmışsa kullanıcının aktif mesailerini global olarak bul
            active_shifts = await db.get_all_active_shifts_global()
            user_shifts = [s for s in active_shifts if s["user_id"] == user.id]
            if not user_shifts:
                await interaction.response.send_message(
                    embed=create_error_embed("Aktif Mesai Yok", "Şu anda devam eden aktif bir mesainiz bulunmuyor."),
                    ephemeral=True
                )
                return
            
            # Bulunan aktif mesai(ler) için doğrulamayı güncelle
            for s in user_shifts:
                await db.update_last_verified(s["guild_id"], user.id)
                logger.info(f"Kullanıcı {user.display_name} (ID: {user.id}) DM üzerinden mesai doğruladı (Guild: {s['guild_id']}).")
        else:
            active = await db.get_active_shift(guild_id, user.id)
            if not active:
                await interaction.response.send_message(
                    embed=create_error_embed("Aktif Mesai Yok", "Şu anda bu sunucuda devam eden aktif bir mesainiz bulunmuyor."),
                    ephemeral=True
                )
                return

            await db.update_last_verified(guild_id, user.id)
            logger.info(f"Kullanıcı {user.display_name} (ID: {user.id}) sunucuda mesai doğruladı (Guild: {guild_id}).")

        # Butonu devre dışı bırak ve mesajı onayla
        verified_embed = create_afk_verified_embed(user)
        self.verify_button.disabled = True
        self.verify_button.style = discord.ButtonStyle.secondary
        self.verify_button.label = "Doğrulandı ✅"

        try:
            if interaction.message:
                await interaction.response.edit_message(embed=verified_embed, view=self)
            else:
                await interaction.response.send_message(embed=verified_embed, ephemeral=True)
        except Exception as e:
            logger.warning(f"Doğrulama mesajı düzenlenirken hata: {e}")
            await interaction.response.send_message(embed=verified_embed, ephemeral=True)
