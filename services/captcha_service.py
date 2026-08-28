import random
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Dict, Optional

@dataclass
class CaptchaOption:
    """Tek bir CAPTCHA buton seçeneğini temsil eden veri yapısı."""
    name: str
    emoji: str
    is_correct: bool
    custom_id: str

@dataclass
class CaptchaChallenge:
    """Tek bir CAPTCHA doğrulama oturumunu temsil eden veri yapısı."""
    session_id: str
    user_id: int
    guild_id: Optional[int]
    target_name: str
    target_emoji: str
    options: List[CaptchaOption]
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    timeout_seconds: int = 60
    solved: bool = False
    failed: bool = False

# Doğrulama için kullanılacak zengin nesne ve emoji kategorileri
CAPTCHA_ITEMS_POOL: List[Dict[str, str]] = [
    {"name": "Trafik Lambası", "emoji": "🚦"},
    {"name": "Otobüs", "emoji": "🚌"},
    {"name": "Bisiklet", "emoji": "🚲"},
    {"name": "Yaya Geçidi", "emoji": "🚶"},
    {"name": "Motosiklet", "emoji": "🏍️"},
    {"name": "Yangın Musluğu", "emoji": "🧯"},
    {"name": "Araba", "emoji": "🚗"},
    {"name": "Helikopter", "emoji": "🚁"},
    {"name": "Uçak", "emoji": "✈️"},
    {"name": "Gemi", "emoji": "🚢"},
    {"name": "Tren", "emoji": "🚆"},
    {"name": "Ağaç", "emoji": "🌳"},
    {"name": "Köpek", "emoji": "🐕"},
    {"name": "Kedi", "emoji": "🐱"},
    {"name": "Güneş", "emoji": "☀️"},
    {"name": "Yıldız", "emoji": "⭐"},
    {"name": "Telefon", "emoji": "📱"},
    {"name": "Bilgisayar", "emoji": "💻"},
    {"name": "Kitap", "emoji": "📚"},
    {"name": "Kahve", "emoji": "☕"},
    {"name": "Pizza", "emoji": "🍕"},
    {"name": "Elma", "emoji": "🍎"},
    {"name": "Müzik Notası", "emoji": "🎵"},
    {"name": "Anahtar", "emoji": "🔑"},
    {"name": "Saat", "emoji": "⏰"},
    {"name": "Kamera", "emoji": "📷"},
]

def generate_captcha_challenge(
    user_id: int,
    guild_id: Optional[int] = None,
    option_count: int = 4,
    timeout_seconds: int = 60
) -> CaptchaChallenge:
    """
    Rastgele hedef nesne ve yanıltıcı şıklardan oluşan dinamik bir CAPTCHA oturumu üretir.
    
    :param user_id: Doğrulama yapılacak personelin Discord ID'si
    :param guild_id: Mesainin ait olduğu sunucu ID'si
    :param option_count: Toplam gösterilecek buton sayısı (varsayılan 4)
    :param timeout_seconds: Yanıt verilmesi gereken süre (saniye)
    :return: CaptchaChallenge nesnesi
    """
    session_id = uuid.uuid4().hex[:12]
    option_count = max(3, min(option_count, len(CAPTCHA_ITEMS_POOL)))
    
    # 1. Doğru hedef nesneyi seç
    target = random.choice(CAPTCHA_ITEMS_POOL)
    
    # 2. Yanıltıcı şıkları seç (hedef nesne hariç)
    other_items = [item for item in CAPTCHA_ITEMS_POOL if item["name"] != target["name"]]
    distractors = random.sample(other_items, option_count - 1)
    
    # 3. Seçenekleri birleştir ve karıştır
    selected_raw = [
        {"name": target["name"], "emoji": target["emoji"], "is_correct": True}
    ] + [
        {"name": d["name"], "emoji": d["emoji"], "is_correct": False} for d in distractors
    ]
    random.shuffle(selected_raw)
    
    # 4. CaptchaOption nesnelerini benzersiz custom_id ile oluştur
    options: List[CaptchaOption] = []
    for idx, opt in enumerate(selected_raw):
        correct_tag = "1" if opt["is_correct"] else "0"
        opt_custom_id = f"cpt_{session_id}_{idx}_{correct_tag}"
        options.append(
            CaptchaOption(
                name=opt["name"],
                emoji=opt["emoji"],
                is_correct=opt["is_correct"],
                custom_id=opt_custom_id
            )
        )
        
    return CaptchaChallenge(
        session_id=session_id,
        user_id=user_id,
        guild_id=guild_id,
        target_name=target["name"],
        target_emoji=target["emoji"],
        options=options,
        timeout_seconds=timeout_seconds
    )
