# Python 3.11 hafif (slim) imajını temel alıyoruz
FROM python:3.11-slim

# Python konsol çıktılarını anlık olarak görebilmek ve bytecode (.pyc) üretimini kapatmak için
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    TZ=Europe/Istanbul

# Zaman dilimi ve gerekli sistem paketlerini yükle
RUN apt-get update && apt-get install -y --no-install-recommends \
    tzdata \
    && ln -fs /usr/share/zoneinfo/$TZ /etc/localtime \
    && dpkg-reconfigure --frontend noninteractive tzdata \
    && rm -rf /var/lib/apt/lists/*

# Çalışma dizinini ayarla
WORKDIR /app

# Önce bağımlılıkları kopyala ve yükle (Docker cache optimizasyonu)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Proje dosyalarını kopyala
COPY . .

# SQLite veritabanı klasörünü oluştur
RUN mkdir -p /app/data

# Botu başlat
CMD ["python", "main.py"]
