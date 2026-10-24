"""Uygulama ayarları ve varsayılan değerler.

Bu modül hem kod içi varsayılanları hem de kullanıcının kaydettiği
ayarların yükleneceği yolu tanımlar. Gerçek ayar yükleme/kaydetme işini
`core.storage` yapar; burada sadece sabitler bulunur.
"""

import os

from dotenv import load_dotenv

# .env dosyasını (varsa) yükle. Bu dosya sürüm kontrolüne dahil edilmez.
load_dotenv()

# --- Uygulama kimliği ---------------------------------------------------
APP_NAME = "Dragon"
APP_VERSION = "1.0.0"
APP_TAGLINE = "Yapay Zeka Asistanı"

# --- Varsayılan model ayarları -----------------------------------------
DEFAULT_MODEL = "gemini-3.5-flash"

# Arayüzde sunulacak hazır modeller. Kullanıcı ayrıca kendi model adını
# yazabilir, bu yüzden liste dışına çıkmasına izin verilir.
AVAILABLE_MODELS = [
    "gemini-3.5-flash",
    "gemini-3.5-flash-lite",
    "gemini-3.8-flash",
]

DEFAULT_TEMPERATURE = 0.7
DEFAULT_MAX_OUTPUT_TOKENS = 8192

# --- Ses ayarları ------------------------------------------------------
# Varsayılan arka uç: Google Cloud TTS (doğal sinirsel Türkçe sesler).
# "edge" seçilirse hızlı yedek (Microsoft Edge neural) kullanılır.
# JARVIS ayarı: tok, sakin, derin erkek sesi (yavaş + pes).
DEFAULT_TTS_BACKEND = "google"

DEFAULT_GOOGLE_TTS_VOICE = "tr-TR-Chirp3-HD-Charon"
DEFAULT_TTS_SPEAKING_RATE = 0.92
DEFAULT_GOOGLE_TTS_PITCH = -3.0

# Ayarlar penceresinde sunulacak Google Türkçe sesleri (ad -> ses kimliği).
GOOGLE_TTS_VOICES = [
    "tr-TR-Chirp3-HD-Charon (JARVIS - tok erkek)",
    "tr-TR-Neural2-D (Erkek)",
    "tr-TR-Neural2-A (Erkek)",
    "tr-TR-Chirp3-HD-Leda (Kadın)",
    "tr-TR-Neural2-C (Kadın)",
]
GOOGLE_TTS_VOICE_IDS = {
    "tr-TR-Chirp3-HD-Charon (JARVIS - tok erkek)": "tr-TR-Chirp3-HD-Charon",
    "tr-TR-Neural2-D (Erkek)": "tr-TR-Neural2-D",
    "tr-TR-Neural2-A (Erkek)": "tr-TR-Neural2-A",
    "tr-TR-Chirp3-HD-Leda (Kadın)": "tr-TR-Chirp3-HD-Leda",
    "tr-TR-Neural2-C (Kadın)": "tr-TR-Neural2-C",
    # Eski etiketle kayıtlı ayarlar için geriye dönük uyumluluk:
    "tr-TR-Chirp3-HD-Charon (Erkek - en doğal)": "tr-TR-Chirp3-HD-Charon",
}

# Edge yedek sesleri (Google kullanılamazsa/hızlı modda kullanılır).
# JARVIS: Ahmet en tok erkek sesi, rate yavaş, pitch pes.
DEFAULT_TTS_VOICE = "tr-TR-AhmetNeural"
DEFAULT_TTS_RATE = "-8%"
DEFAULT_TTS_PITCH = "-15Hz"

# Ayarlar penceresinde sunulacak yedek (Edge) sesler (ad -> edge-tts ses kimliği).
TTS_VOICES = [
    "tr-TR-AhmetNeural (JARVIS - tok erkek)",
    "tr-TR-EmelNeural (Kadın)",
]
TTS_VOICE_IDS = {
    "tr-TR-AhmetNeural (JARVIS - tok erkek)": "tr-TR-AhmetNeural",
    "tr-TR-EmelNeural (Kadın)": "tr-TR-EmelNeural",
    # Eski etiketle kayıtlı ayarlar için geriye dönük uyumluluk:
    "tr-TR-AhmetNeural (Erkek - kalın)": "tr-TR-AhmetNeural",
}

# Bir istek içinde en fazla kaç kez araç çalıştırılabileceği (sonsuz döngüye
# karşı koruma).
MAX_TOOL_STEPS = 8

# --- Ortamdan gelen gizli anahtar --------------------------------------
ENV_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()

# Kullanıcı ayarları dosyasını (ve sohbetleri) başka bir yere taşımak
# isterse bu ortam değişkenini kullanabilir.
ENV_DATA_DIR = "DRAGON_DATA_DIR"
