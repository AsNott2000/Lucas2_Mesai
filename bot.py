import sys
import logging
import asyncio
import discord
from discord.ext import commands

from config import config
from database import db
from views.shift_view import ShiftView
from views.admin_view import AdminView

# Loglama Yapılandırması
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("Lucas2MesaiBot")

class Lucas2MesaiBot(commands.Bot):
    """Lucas2 Mesai ve Vardiya Takip Bot Sınıfı."""

    def __init__(self):
        intents = discord.Intents.default()
        intents.guilds = True
        intents.members = True
        intents.message_content = True

        super().__init__(
            command_prefix="!",
            intents=intents,
            help_command=None
        )

    async def setup_hook(self) -> None:
        """Bot başlatılırken veritabanını hazırlar, cog'ları ve kalıcı view'leri yükler."""
        logger.info("Veritabanı başlatılıyor...")
        await db.init_db()
        logger.info(f"Veritabanı hazır: {config.DATABASE_PATH}")

        # Kalıcı (Persistent) View bileşenlerini kaydet
        # Bu işlem sayesinde bot yeniden başlatılsa bile eski butonlar çalışmaya devam eder
        self.add_view(ShiftView())
        self.add_view(AdminView())
        logger.info("Kalıcı View bileşenleri (ShiftView, AdminView) başarıyla kaydedildi.")

        # Cog modüllerini yükle
        cogs = ["cogs.shift_cog", "cogs.admin_cog"]
        for cog in cogs:
            try:
                await self.load_extension(cog)
                logger.info(f"Modül yüklendi: {cog}")
            except Exception as e:
                logger.error(f"Modül yüklenirken hata oluştu ({cog}): {e}", exc_info=True)

        # Slash komutlarını senkronize et
        try:
            if config.GUILD_ID:
                guild_obj = discord.Object(id=config.GUILD_ID)
                self.tree.copy_global_to(guild=guild_obj)
                synced = await self.tree.sync(guild=guild_obj)
                logger.info(f"Guild ({config.GUILD_ID}) için {len(synced)} slash komutu anında senkronize edildi.")
            else:
                synced = await self.tree.sync()
                logger.info(f"Global olarak {len(synced)} slash komutu senkronize edildi.")
        except Exception as e:
            logger.error(f"Slash komutları senkronize edilirken hata: {e}", exc_info=True)

    async def on_ready(self):
        """Bot Discord ağına bağlandığında tetiklenir."""
        logger.info("=" * 50)
        logger.info(f"Bot Başarıyla Giriş Yaptı: {self.user} (ID: {self.user.id})")
        logger.info(f"Bağlı Sunucu Sayısı: {len(self.guilds)}")
        logger.info(f"Gecikme (Ping): {round(self.latency * 1000, 2)}ms")
        logger.info("=" * 50)

        # Durum mesajı ayarla
        activity = discord.Activity(
            type=discord.ActivityType.watching,
            name="Personel Mesailerini ⏱️"
        )
        await self.change_presence(status=discord.Status.online, activity=activity)

    async def on_command_error(self, ctx: commands.Context, error: Exception):
        """Genel komut hata yakalayıcı."""
        logger.error(f"Komut Hatası ({ctx.command}): {error}", exc_info=True)

def main():
    """Botu başlatan ana fonksiyon."""
    config.validate()

    if not config.DISCORD_TOKEN or config.DISCORD_TOKEN == "YOUR_BOT_TOKEN_HERE":
        logger.critical("HATA: Lütfen .env dosyasını oluşturun ve geçerli bir DISCORD_TOKEN tanımlayın!")
        logger.info("Örnek dosya için .env.example dosyasını inceleyebilirsiniz.")
        sys.exit(1)

    bot = Lucas2MesaiBot()
    try:
        bot.run(config.DISCORD_TOKEN)
    except discord.LoginFailure:
        logger.critical("HATA: Geçersiz Discord Bot Tokeni! Lütfen .env dosyanızı kontrol ediniz.")
    except Exception as e:
        logger.critical(f"Bot çalışırken beklenmeyen bir hata oluştu: {e}", exc_info=True)

if __name__ == "__main__":
    main()
