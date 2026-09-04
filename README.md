# 🎵 SonicTube

<div align="center">

**YouTube Video & Stüdyo Kalitesinde Müzik İndirme Uygulaması**  
*4K Video Downloader alternatifi: Hızlı, reklamsız, sınırsız ve modern masaüstü arayüzü.*

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![UI](https://img.shields.io/badge/GUI-CustomTkinter-emerald.svg)](https://customtkinter.tomschimansky.com/)
[![Engine](https://img.shields.io/badge/Engine-yt--dlp-red.svg)](https://github.com/yt-dlp/yt-dlp)
[![Audio](https://img.shields.io/badge/Audio-320kbps%20MP3%20%7C%20FLAC-purple.svg)](https://ffmpeg.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

</div>

---

## ✨ Özellikler

- 🚀 **Gerçek 320 kbps MP3:** Piyasada sesi 128 kbps'ye düşüren kalitesiz web sitelerine son! Gerçek yüksek kaliteli ses çıkışı.
- 🎨 **Otomatik Albüm Kapağı & ID3 Etiketleri:** Şarkı kapağını (thumbnail), sanatçı adını ve parça başlığını doğrudan MP3 dosyasına işler (araba teybinde, telefonda veya müzik çalarlarda kapak resmi görünür).
- 🎬 **4K & 1080p Video Desteği:** 4K (2160p), 2K (1440p), 1080p Full HD ve 720p HD çözünürlüklerinde MP4 / MKV video indirme.
- 📋 **"Bağlantıyı Yapıştır" (Tek Tık):** Panoya (clipboard) kopyalanan YouTube linkini tek tıkla algılar ve inceler.
- 📑 **Çalma Listesi (Playlist) Desteği:** Tüm çalma listesini tek seferde veya sadece seçilen videoyu indirebilme.
- 📊 **Canlı İlerleme Çubuğu:** İndirme yüzdesi, anlık hız (MB/s), kalan süre ve dosya boyutu takibi.
- 📁 **Tek Tıkla Aç / Klasörde Göster:** İndirilen dosyayı doğrudan açma veya Windows Gezgini'nde seçili halde gösterme.
- 🛡️ **Taşınabilir FFmpeg:** Sisteminizde FFmpeg kurulu olmasa bile otomatik olarak taşınabilir versiyonu indirir ve kullanır.

---

## 📸 Ekran Görüntüleri & Görünüm

SonicTube, modern koyu teması (Dark Mode) ve akıcı kart yapısıyla 4K Video Downloader arayüzünden esinlenerek tasarlanmıştır.

---

## 🛠️ Kurulum & Çalıştırma

### Kolay Başlatıcı (Önerilen - Windows)
Klasör içindeki **`SonicTube.bat`** dosyasına çift tıklamanız yeterlidir! Gerekli ortamı ve paketleri otomatik kontrol edip uygulamayı başlatır.

### Manuel Kurulum (Geliştiriciler İçin)

1. **Repoyu Klonlayın:**
   ```bash
   git clone https://github.com/EkremTezcanSaridag/SonicTube.git
   cd SonicTube
   ```

2. **Sanal Ortamı Oluşturun ve Aktif Edin:**
   ```bash
   python -m venv .venv
   # Windows:
   .venv\Scripts\activate
   ```

3. **Gerekli Paketleri Yükleyin:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Uygulamayı Başlatın:**
   ```bash
   python src/main.py
   ```

---

## ⚙️ Desteklenen Formatlar & Kaliteler

| Mod | Formatlar | Kalite Seçenekleri |
|---|---|---|
| **Müzik / Ses** | MP3, M4A, FLAC, WAV | 320 kbps (En Yüksek), 256 kbps, 192 kbps, 128 kbps |
| **Video** | MP4, MKV | 4K (2160p), 2K (1440p), 1080p (Full HD), 720p, 480p |

---

## 📝 Lisans

Bu proje [MIT Lisansı](LICENSE) altında sunulmaktadır.