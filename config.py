import os
from pathlib import Path
from dataclasses import dataclass
from typing import Optional
from dotenv import load_dotenv

# .env dosyasını çalışma alanından yükle
load_dotenv()

@dataclass(frozen=True)
class Config:
    """Uygulama genelinde kullanılan konfigürasyon değişkenleri."""
    DISCORD_TOKEN: str = os.getenv("DISCORD_TOKEN", "")
    GUILD_ID: Optional[int] = int(os.getenv("GUILD_ID")) if os.getenv("GUILD_ID") and os.getenv("GUILD_ID").isdigit() else None
    ADMIN_ROLE_ID: Optional[int] = int(os.getenv("ADMIN_ROLE_ID")) if os.getenv("ADMIN_ROLE_ID") and os.getenv("ADMIN_ROLE_ID").isdigit() else None
    MESAI_CHANNEL_ID: Optional[int] = int(os.getenv("MESAI_CHANNEL_ID")) if os.getenv("MESAI_CHANNEL_ID") and os.getenv("MESAI_CHANNEL_ID").isdigit() else None
    ADMIN_CHANNEL_ID: Optional[int] = int(os.getenv("ADMIN_CHANNEL_ID")) if os.getenv("ADMIN_CHANNEL_ID") and os.getenv("ADMIN_CHANNEL_ID").isdigit() else None
    AKTIF_MESAILER_CHANNEL_ID: Optional[int] = int(os.getenv("AKTIF_MESAILER_CHANNEL_ID")) if os.getenv("AKTIF_MESAILER_CHANNEL_ID") and os.getenv("AKTIF_MESAILER_CHANNEL_ID").isdigit() else None
    MESAI_TABLO_CHANNEL_ID: Optional[int] = int(os.getenv("MESAI_TABLO_CHANNEL_ID")) if os.getenv("MESAI_TABLO_CHANNEL_ID") and os.getenv("MESAI_TABLO_CHANNEL_ID").isdigit() else None
    LOG_CHANNEL_ID: Optional[int] = int(os.getenv("LOG_CHANNEL_ID")) if os.getenv("LOG_CHANNEL_ID") and os.getenv("LOG_CHANNEL_ID").isdigit() else None
    AFK_CHECK_INTERVAL_MINUTES: int = int(os.getenv("AFK_CHECK_INTERVAL_MINUTES", "45"))
    AFK_TIMEOUT_MINUTES: int = int(os.getenv("AFK_TIMEOUT_MINUTES", "15"))
    AFK_PENALTY_MINUTES: int = int(os.getenv("AFK_PENALTY_MINUTES", "61"))
    DATABASE_PATH: str = os.getenv("DATABASE_PATH", "data/mesai.db")
    TIMEZONE: str = os.getenv("TIMEZONE", "Europe/Istanbul")

    def validate(self) -> None:
        """Kritik konfigürasyonların varlığını doğrular."""
        if not self.DISCORD_TOKEN or self.DISCORD_TOKEN == "YOUR_BOT_TOKEN_HERE":
            print("[UYARI] DISCORD_TOKEN .env dosyasında tanımlı değil veya varsayılan değerde!")

        # Veritabanı dizinini hazırla
        db_dir = Path(self.DATABASE_PATH).parent
        db_dir.mkdir(parents=True, exist_ok=True)

# Singleton config örneği
config = Config()
