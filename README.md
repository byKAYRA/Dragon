# 🐉 Dragon — Yapay Zeka Asistanı

Dragon, **Gemini** modeli üzerinde çalışan, **sesli ve yazılı komutlu** masaüstü bir yapay
zeka asistanıdır. Düz (flat) neon temalı arayüzüyle tek dosyalık `exe` olarak
derlenip paylaşılabilir.

## Özellikler

- 🎤 **Sesle komut** — ortadaki çembere tıklayın, konuşun veya *"Dragon"* uyandırma kelimesini kullanın.
- ⌨️ **Klavye / Metin girişi** — mikrofonunuz olmadığında veya sessiz ortamda komut çubuğuna yazıp `Enter` ile gönderin.
- 🔊 **Doğal sesli yanıt** — optimize edilmiş Türkçe sinirsel ses motoru (edge-tts / Google Cloud TTS).
- 🧠 **Gemini ajanı** — araç döngüsüyle web arama, Twitter/X trendleri, dosya okuma/yazma.
- 📋 **Haber merkezi arayüzü** — Hava Durumu ve GÜNDEM panelleri, neon visualizer.
- ⚙️ **Ayarlar** — API anahtarı, model, ses ve asistan davranışı.

## Kurulum (geliştirici)

```bash
pip install -r requirements.txt
python main.py
```

İlk açılışta API anahtarınızı ister. Anahtarı
[aistudio.google.com](https://aistudio.google.com) adresinden ücretsiz alıp
**Ayarlar** penceresine girebilir veya proje klasöründeki `.env` dosyasına
yazabilirsiniz:

```
GEMINI_API_KEY=buraya_anahtar
```

> `.env` sürüm kontrolüne dahil edilmez; exe'nin içine de gömülmez. Herkes
> kendi anahtarını kullanır.

## Testleri Çalıştırma

```bash
python -m unittest discover -s tests -v
```

## exe Olarak Derleme

```bash
pip install pyinstaller
python build.py
```

Sonuç: `dist/Dragon.exe` — tek dosya, çift tıkla çalışır.

## Nasıl Kullanılır?

1. Uygulamayı açın. API anahtarınız yoksa Ayarlar penceresi açılır.
2. Ortadaki **ses çemberine** tıklayın veya alttaki **komut çubuğuna** bir mesaj yazın.
3. Sesli konuşurken ipucu "Şimdi konuşun" olunca Türkçe konuşun (örn. *"Bugünün haberlerini özetle"*).
4. Dragon yanıtını hem ekrana yazar hem de **sesli** okur.

## Proje Yapısı

```
Dragon/
├─ main.py               # Giriş noktası
├─ build.py              # exe derleme betiği
├─ config/settings.py    # Sabitler ve varsayılanlar
├─ core/
│  ├─ agent.py           # Gemini ajanı + araç döngüsü
│  ├─ voice.py           # Sesli giriş (mikrofon) / çıkış (edge-tts)
│  ├─ wake_word.py       # "Dragon" uyandırma dinleyicisi
│  ├─ prompts.py         # Asistanın kişiliği (sistem promptu)
│  └─ storage.py         # Ayarlar, sohbetler, çalışma klasörü
├─ tests/                # Birim testleri (voice, tools, storage)
├─ tools/
│  ├─ web_search.py      # Web arama aracı
│  ├─ x_trends.py        # Canlı X (Twitter) Türkiye trendleri
│  ├─ file_tools.py      # Dosya okuma/yazma araçları
│  └─ registry.py        # Araç tanımları ve çalıştırıcı
└─ ui/
   ├─ app.py             # Haber merkezi (hub) penceresi + visualizer + komut çubuğu
   ├─ settings_dialog.py # Ayarlar penceresi
   └─ theme.py           # Neon renk paleti
```

## Verilerin Saklandığı Yer

- Geliştirme: projedeki `data/` klasörü.
- Paketlenmiş (exe): `%APPDATA%\Dragon`.

Özel bir konum için `DRAGON_DATA_DIR` ortam değişkenini kullanabilirsiniz.

## Notlar ve Sınırlar

- Ses tanıma (Google Web Speech API) ve sesli yanıt (edge-tts) **İnternet**
  gerektirir. Model istekleri de aynı şekilde İnternet üzerinden gider.
- Ses tanıma aracı için sisteminizde bir **mikrofon** bulunmalıdır (alternatif olarak metin giriş çubuğunu kullanabilirsiniz).
- Dosya araçları yalnızca ayarlarda gösterilen güvenli **çalışma klasörü**
  içinde etkindir.
