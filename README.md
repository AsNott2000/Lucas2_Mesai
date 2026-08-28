# ⏱️ Lucas2 - Discord Mesai ve Vardiya Takip Botu

Lucas2 Mesai Botu; Discord sunucularında personellerin, moderatörlerin veya yetkililerin çalışma saatlerini, vardiyalarını ve aktifliklerini buton tabanlı ve rol korumalı olarak takip eden profesyonel bir Discord botudur.

---

## 🚀 Temel Özellikler

### 1. Kullanıcı Paneli (`#mesai` Kanalı)
- 🟢 **Mesai Başlat (`btn_start_shift`):** Personelin çalışma süresini başlatır. Aktif mesai varken tekrar başlatmayı engeller.
- 🔴 **Mesai Bitir (`btn_end_shift`):** Aktif mesaiyi sonlandırır, geçen süreyi (saat, dakika, saniye) hesaplar ve kullanıcıya özel özet sunar.
- 🧹 **Otomatik Kanal Temizliği:** Mesai bitiminde veya sohbete yazılan mesajlarda kanal otomatik temizlenerek ana buton paneli daima en altta ve sabit kalır (Scroll kirliliği yaşanmaz).
- 👤 **Bireysel İstatistik (`/mesaim`):** Personelin bugüne kadarki toplam oturum ve çalışma saatini gösterir.

### 2. Canlı Aktif Mesai Takibi (`#aktif-mesailer` Kanalı)
- 🟢 **Otomatik Canlı Embed:** Bu kanalda tek bir sabit mesaj yer alır.
- Herhangi bir personel mesaiye başladığında veya bitirdiğinde anında güncellenir (`message.edit`).
- Aktif görevdeki personelleri, başlangıç saatlerini ve ne kadar süredir mesaide olduklarını dinamik olarak listeler. Aktif kimse yoksa `"Şu an aktif mesaide kimse bulunmamaktadır."` bilgisini gösterir.

### 3. Genel Mesai Tablosu & İstatistik Paneli (`#mesai-tablo` Kanalı)
- 🏆 **Liderlik ve İstatistik Tablosu:** Veritabanındaki verilere dayanarak tüm personellerin toplam çalışma süresi, oturum sayısı ve son aktiflik zamanını madalyalı (🥇, 🥈, 🥉) sıralı liste olarak gösterir.
- Oturum bitimlerinde ve periyodik arka plan görevleriyle düzenli olarak güncellenir.

### 4. Otomatik Çalışma / Dinamik CAPTCHA Doğrulama Mekanizması (45 Dakikada Bir)
- ⏱️ **45 Dakikalık Güvenlik Döngüsü:** Mesai başlatan her personel için arka planda 45 dakikalık aktiflik döngüsü çalışır.
- 🧩 **Dinamik CAPTCHA Sistemi:** Süre dolduğunda bot rastgele bir hedef nesne belirler (Örn: *Trafik Lambası* 🚦, *Otobüs* 🚌, *Bisiklet* 🚲, *Motosiklet* 🏍️ vb.) ve kullanıcıya 4 seçenekli buton arayüzü sunar.
- 💬 **Kullanıcıya Özel Gönderim:** Doğrulama mesajı DM üzerinden iletilir (DM kapalıysa mesai kanalında geçici ping atar).
- ⏳ **Doğrulama ve Ceza Kuralları:**
  - **Doğru Seçim:** Kullanıcı doğru butona basarsa CAPTCHA onaylanır, zamanlayıcı sıfırlanır ve mesai kesintisiz devam eder.
  - **Yanlış Seçim veya Zaman Aşımı:** Hatalı butona basıldığında veya süre dolduğunda personelin mesaisi derhal sonlandırılır, son süre silinir, log kanalına bildirim düşülür ve canlı paneller anında güncellenir.
- 🔒 **Anti-Spam & Tek Kullanımlık Butonlar:** Her CAPTCHA oturumu benzersiz UUID ile oluşturulur, tıklandığı anda butonlar devre dışı kalır (`disabled=True`) ve başkalarının müdahalesi engellenir.

### 5. Yönetici Paneli (`#admin-settings` Kanalı)
- 🛡️ **Rol / Yetki Koruması:** Yalnızca `Administrator` veya `.env` içerisinde belirlenen yetkili role sahip üyeler erişebilir.
- 📊 **Genel Rapor Al (`btn_get_report` / `/mesai-rapor`):** Tüm personellerin toplam mesai sürelerini listeler.
- 🟢 **Anlık Aktif Mesailer (`btn_active_shifts` / `/aktif-mesailer`):** Şu anda görevde olan personelleri anlık listeler.
- 👮 **Yetkili Müdahalesi (`/mesai-bitir-yetkili`):** Açık unutulmuş mesaileri yönetici tarafından kapatır.

---

## 📂 Proje Dizin Yapısı

```text
Lucas2_Mesai/
├── cogs/
│   ├── admin_cog.py        # Yönetici slash komutları (/kurulum-hepsi, /kurulum-aktif-mesailer vb.)
│   ├── shift_cog.py        # Mesai komutları (/kurulum-mesai, /mesaim, /aktif-mesailer)
│   └── tracker_cog.py      # Arka plan AFK kontrolü ve canlı panellerin senkronizasyon döngüsü
├── database/
│   ├── __init__.py
│   └── db_manager.py       # Asenkron SQLite veritabanı sürücüsü, migrasyonlar ve ayarlar
├── services/
│   ├── __init__.py
│   └── panel_manager.py    # Canlı embed güncelleme, kanal temizleme ve log servisi
├── tests/
│   ├── test_database.py    # Veritabanı ve AFK iş mantığı testleri
│   ├── test_tracker.py     # Canlı paneller ve takip testleri
│   └── test_views.py       # UI View ve Custom ID testleri
├── utils/
│   ├── formatters.py       # Zaman, süre ve Discord Embed biçimlendiricileri
│   └── permissions.py      # Yönetici ve rol yetki doğrulayıcı
├── views/
│   ├── admin_view.py       # #admin-settings kanalı kalıcı yönetim butonları
│   ├── afk_view.py         # 45 dakikalık AFK doğrulama kalıcı butonu
│   └── shift_view.py       # #mesai kanalı kalıcı personel butonları
├── .env                    # Ortam değişkenleri ve kanal ayarları
├── .gitignore              # Git tarafından yoksayılacak dosyalar
├── bot.py                  # Bot ana sınıfı ve yaşam döngüsü
├── config.py               # Konfigürasyon yükleyici
├── main.py                 # Bot başlatıcı giriş noktası
├── requirements.txt        # Python bağımlılık listesi
└── README.md               # Detaylı kurulum ve kullanım kılavuzu
```

---

## 🛠️ Discord Slash Kurulum Komutları

| Komut | Açıklama |
| :--- | :--- |
| `/kurulum-hepsi` | **Tek tıkla tüm kanalları (`#mesai`, `#aktif-mesailer`, `#mesai-tablo`, `#admin-settings`, `#mesai-log`) ve panelleri otomatik kurar.** |
| `/kurulum-mesai [kanal]` | `#mesai` kanalına ana Mesai Başlat/Bitir panelini kurar ve eski mesajları temizler. |
| `/kurulum-aktif-mesailer [kanal]` | `#aktif-mesailer` kanalına canlı otomatik güncellenen aktif mesai listesi panelini kurar. |
| `/kurulum-mesai-tablo [kanal]` | `#mesai-tablo` kanalına genel sıralama ve istatistik panelini kurar. |
| `/kurulum-admin [kanal]` | `#admin-settings` kanalına yönetici kontrol panelini kurar. |
| `/mesai-temizle [kanal]` | Belirtilen mesai kanalını ana panel hariç temizler. |
| `/mesaim` | Personelin kendi aktif durumunu ve toplam mesai saatini gösterir. |
| `/aktif-mesailer` | Anlık görevdeki tüm personelleri listeler. |
| `/mesai-rapor` | Sunucu geneli tüm mesai istatistiklerini raporlar. |
| `/mesai-bitir-yetkili [üye]` | Açık unutulmuş bir mesaiyi yönetici olarak sonlandırır. |

---

## 🧪 Testleri Çalıştırma

Tüm veritabanı, AFK doğrulama, canlı panel ve bileşen testlerini çalıştırmak için:
```bash
python -m unittest discover -s tests -v
```

---

## 🔒 Kalıcılık ve Güvenlik
- **Yeniden Başlatma Dayanıklılığı:** Panel mesaj ID'leri `settings` tablosunda, personellerin son doğrulama zamanları `last_verified_at` olarak SQLite'ta saklanır. Bot yeniden başlatıldığında paneller ve zamanlayıcılar kaldığı yerden devam eder.
- **Çakışan Mesai Koruması:** Aktif mesaisi olan personeller ikinci bir mesai açamaz.
- **AFK Otomatik Kapatma:** Doğrulama yapmayan üyelerin mesaileri haksız süre birikimini önlemek adına otomatik sonlandırılır.
- **Açık Mesai Olmadan Bitirme:** Açık kaydı olmayan personeller "Mesai Bitir"e basarsa nazik bir hata mesajı ile uyarılır.
- **Yetkisiz Rapor Erişimi:** Yönetici paneli ve rapor komutları, tıklayan kişinin `Administrator` veya belirlenen yetkili role sahip olup olmadığını her istekte canlı kontrol eder.
- **Gizli (Ephemeral) Yanıtlar:** Personellerin buton tıklamaları ve raporlar yalnızca ilgili kullanıcıya özel (ephemeral) olarak gösterilir, kanallarda mesaj kirliliği oluşturmaz.

