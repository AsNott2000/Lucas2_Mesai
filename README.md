# ⏱️ Lucas2 - Discord Mesai ve Vardiya Takip Botu

Lucas2 Mesai Botu; Discord sunucularında personellerin, moderatörlerin veya yetkililerin çalışma saatlerini, vardiyalarını ve aktifliklerini buton tabanlı ve rol korumalı olarak takip eden profesyonel bir Discord botudur.

---

## 🚀 Temel Özellikler

1. **Kullanıcı Paneli (`#mesai` Kanalı):**
   - 🟢 **Mesai Başlat (`btn_start_shift`):** Personelin çalışma süresini başlatır. Aktif mesai varken tekrar başlatmayı engeller.
   - 🔴 **Mesai Bitir (`btn_end_shift`):** Aktif mesaiyi sonlandırır, geçen süreyi (saat, dakika, saniye) hesaplar ve kullanıcıya özel özet sunar.
   - 👤 **Bireysel İstatistik (`/mesaim`):** Personelin bugüne kadarki toplam oturum ve çalışma saatini gösterir.

2. **Yönetici Paneli (`#admin-settings` Kanalı):**
   - 🛡️ **Rol / Yetki Koruması:** Yalnızca `Administrator` veya `.env` içerisinde belirlenen yetkili rol ID'sine sahip üyeler erişebilir.
   - 📊 **Genel Rapor Al (`btn_get_report` / `/mesai-rapor`):** Tüm personellerin toplam mesai sürelerini, oturum sayılarını ve son aktiflik zamanlarını Discord Embed tablosu halinde listeler.
   - 🟢 **Anlık Aktif Mesailer (`btn_active_shifts` / `/aktif-mesailer`):** Şu anda mesaisi devam eden personelleri anlık listeler.
   - 👮 **Yetkili Müdahalesi (`/mesai-bitir-yetkili`):** Açık unutulmuş mesaileri yönetici tarafından kapatır.

3. **Kalıcı Butonlar (Persistent Views):**
   - Bot yeniden başlatılsa (restart) dahi mesajlardaki butonlar bozulmaz veya işlevsiz kalmaz.

4. **Hızlı ve Güvenilir Asenkron Veritabanı:**
   - `aiosqlite` ile asenkron SQLite veritabanı.
   - Çift tıklama ve yarış durumlarına (race condition) karşı eşzamanlılık kilidi.

---

## 📂 Proje Dizin Yapısı

```text
Lucas2_Mesai/
├── cogs/
│   ├── admin_cog.py        # Yönetici slash komutları (/kurulum-admin, /mesai-rapor vb.)
│   └── shift_cog.py        # Mesai komutları (/kurulum-mesai, /mesaim, /aktif-mesailer)
├── database/
│   ├── __init__.py
│   └── db_manager.py       # Asenkron SQLite veritabanı sürücüsü ve sorgular
├── tests/
│   ├── test_database.py    # Veritabanı ve iş mantığı testleri
│   └── test_views.py       # UI View ve Custom ID testleri
├── utils/
│   ├── formatters.py       # Zaman, süre ve Discord Embed biçimlendiricileri
│   └── permissions.py      # Yönetici ve rol yetki doğrulayıcı
├── views/
│   ├── admin_view.py       # #admin-settings kanalı kalıcı yönetim butonları
│   └── shift_view.py       # #mesai kanalı kalıcı personel butonları
├── .env.example            # Örnek ortam değişkenleri şablonu
├── .gitignore              # Git tarafından yoksayılacak dosyalar
├── bot.py                  # Bot ana sınıfı ve yaşam döngüsü
├── config.py               # Konfigürasyon yükleyici
├── main.py                 # Bot başlatıcı giriş noktası
├── requirements.txt        # Python bağımlılık listesi
└── README.md               # Detaylı kurulum ve kullanım kılavuzu
```

---

## ⚙️ Kurulum Adımları

### 1. Discord Botunu Oluşturma (Developer Portal)
1. [Discord Developer Portal](https://discord.com/developers/applications) adresine gidin ve yeni bir uygulama oluşturun.
2. **Bot** sekmesine geçin ve **Reset Token** butonuna basarak bot tokeninizi kopyalayın.
3. Aşağıdaki **Privileged Gateway Intents** seçeneklerini aktif edin:
   - ✅ **Server Members Intent**
   - ✅ **Message Content Intent**
4. **OAuth2 > URL Generator** sekmesine gidin:
   - Scopes: `bot`, `applications.commands`
   - Bot Permissions: `Administrator` (veya `Send Messages`, `Embed Links`, `Use Slash Commands`)
   - Oluşturulan link ile botu sunucunuza davet edin.

---

### 2. Proje Kurulumu ve Çalıştırma

```bash
# 1. Gerekli kütüphaneleri yükleyin:
pip install -r requirements.txt

# 2. .env dosyasını oluşturun (.env.example dosyasından kopyalayabilirsiniz):
# Windows (PowerShell):
Copy-Item .env.example .env

# 3. .env dosyasını açıp bilgilerinizi girin:
# DISCORD_TOKEN=BOT_TOKENINIZ
# GUILD_ID=SUNUCU_IDNIZ
# ADMIN_ROLE_ID=YETKILI_ROL_IDNIZ (Opsiyonel)
```

```bash
# 4. Botu başlatın:
python bot.py
# veya
python main.py
```

---

## 🛠️ Botun İlk Kurulumu (Discord Üzerinde)

1. Sunucunuzda `#mesai` metin kanalına gidin ve slash komutunu çalıştırın:
   ```text
   /kurulum-mesai
   ```
   *Bot bu kanala kalıcı "Mesai Başlat" ve "Mesai Bitir" butonlarını içeren mesajı gönderecektir.*

2. Sunucunuzda yalnızca yetkililerin gördüğü `#admin-settings` kanalına gidin ve çalıştırın:
   ```text
   /kurulum-admin
   ```
   *Bot bu kanala kalıcı "Genel Rapor Al" ve "Anlık Aktif Mesailer" butonlarını gönderecektir.*

---

## 🧪 Testleri Çalıştırma

Tüm veritabanı, hesaplama ve bileşen testlerini çalıştırmak için:
```bash
python -m unittest discover -s tests -v
```

---

## 🔒 Hata Toleransı & Güvenlik Önlemleri
- **Çakışan Mesai:** Bir personel mesaideyken yeniden "Mesai Başlat" butonuna basarsa işlem engellenir ve kaç saattir mesaide olduğu hatırlatılır.
- **Açık Mesai Olmadan Bitirme:** Açık kaydı olmayan personeller "Mesai Bitir"e basarsa nazik bir hata mesajı ile uyarılır.
- **Yetkisiz Rapor Erişimi:** Yönetici paneli ve rapor komutları, tıklayan kişinin `Administrator` veya belirlenen yetkili role sahip olup olmadığını her istekte canlı kontrol eder.
- **Gizli (Ephemeral) Yanıtlar:** Personellerin buton tıklamaları ve raporlar yalnızca ilgili kullanıcıya özel (ephemeral) olarak gösterilir, kanallarda mesaj kirliliği oluşturmaz.
