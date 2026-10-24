"""Uygulama ayarları ve varsayılan değerler.

Bu modül hem kod içi varsayılanları hem de kullanıcının kaydettiği
ayarların yükleneceği yolu tanımlar. Gerçek ayar yükleme/kaydetme işini
`core.storage` yapar; burada sadece sabitler bulunur.
"""

import os

try:
    from dotenv import load_dotenv

    # .env dosyasını (varsa) yükle. Bu dosya sürüm kontrolüne dahil edilmez.
    load_dotenv()
except ImportError:
    pass

# --- Uygulama kimliği ---------------------------------------------------
APP_NAME = "Dragon"
APP_VERSION = "1.0.0"
APP_TAGLINE = "Yapay Zeka Asistanı"

# --- Varsayılan model ayarları -----------------------------------------
DEFAULT_MODEL = "gemini-2.5-flash"

# Arayüzde sunulacak hazır modeller. Kullanıcı ayrıca kendi model adını
# yazabilir, bu yüzden liste dışına çıkmasına izin verilir.
AVAILABLE_MODELS = [
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-3.5-flash-lite",
    "gemini-3.5-flash",
]

DEFAULT_TEMPERATURE = 0.7
DEFAULT_MAX_OUTPUT_TOKENS = 8192

# --- Ses ayarları ------------------------------------------------------
# Varsayılan arka uç: "edge" (Microsoft Edge neural, ücretsiz, hızlı, anahtar gerektirmez).
# Kullanıcı isterse ayarlardan Google Cloud TTS anahtarı girip geçiş yapabilir.
DEFAULT_TTS_BACKEND = "edge"

DEFAULT_GOOGLE_TTS_VOICE = "tr-TR-Neural2-C"
DEFAULT_TTS_SPEAKING_RATE = 1.0
DEFAULT_GOOGLE_TTS_PITCH = 0.0

# Ayarlar penceresinde sunulacak Google Türkçe sesleri (ad -> ses kimliği).
GOOGLE_TTS_VOICES = [
    "tr-TR-Neural2-C (Kadın - Akıcı)",
    "tr-TR-Neural2-D (Erkek - Doğal)",
    "tr-TR-Neural2-A (Kadın)",
    "tr-TR-Chirp3-HD-Charon (Erkek)",
    "tr-TR-Chirp3-HD-Leda (Kadın)",
]
GOOGLE_TTS_VOICE_IDS = {
    "tr-TR-Neural2-C (Kadın - Akıcı)": "tr-TR-Neural2-C",
    "tr-TR-Neural2-D (Erkek - Doğal)": "tr-TR-Neural2-D",
    "tr-TR-Neural2-A (Kadın)": "tr-TR-Neural2-A",
    "tr-TR-Chirp3-HD-Charon (Erkek)": "tr-TR-Chirp3-HD-Charon",
    "tr-TR-Chirp3-HD-Leda (Kadın)": "tr-TR-Chirp3-HD-Leda",
    # Eski etiketler için geriye dönük uyumluluk:
    "tr-TR-Chirp3-HD-Charon (JARVIS - tok erkek)": "tr-TR-Chirp3-HD-Charon",
    "tr-TR-Chirp3-HD-Charon (Erkek - en doğal)": "tr-TR-Chirp3-HD-Charon",
    "tr-TR-Neural2-C (Kadın)": "tr-TR-Neural2-C",
}

# Edge sesleri (ücretsiz, yüksek kaliteli sinirsel Türkçe sesler)
DEFAULT_TTS_VOICE = "tr-TR-EmelNeural"
DEFAULT_TTS_RATE = "+0%"
DEFAULT_TTS_PITCH = "+0Hz"

# Ayarlar penceresinde sunulacak Edge sesleri (ad -> edge-tts ses kimliği).
TTS_VOICES = [
    "tr-TR-EmelNeural (Doğal Türkçe - Kadın)",
    "tr-TR-AhmetNeural (Erkek)",
]
TTS_VOICE_IDS = {
    "tr-TR-EmelNeural (Doğal Türkçe - Kadın)": "tr-TR-EmelNeural",
    "tr-TR-AhmetNeural (Erkek)": "tr-TR-AhmetNeural",
    # Eski etiketler için geriye dönük uyumluluk:
    "tr-TR-EmelNeural (Kadın)": "tr-TR-EmelNeural",
    "tr-TR-AhmetNeural (JARVIS - tok erkek)": "tr-TR-AhmetNeural",
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
