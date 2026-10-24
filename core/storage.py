"""Yerel veri depolama katmanı.

Sorumluluklar:
    * Uygulama veri klasörünü belirlemek (geliştirme ve paketlenmiş hâli).
    * Kullanıcı ayarlarını `settings.json` içinde saklamak.
    * Sohbetleri `chats/` altında ayrı JSON dosyaları olarak saklamak.
    * Ajanın dosya araçlarını kullandığı güvenli `workspace/` klasörünü yönetmek.

Hiçbir ağ çağrısı yapmaz; tamamen yereldir.
"""

from __future__ import annotations

import json
import os
import shutil
import sys
import time
import uuid
from pathlib import Path
from typing import Any

from config.settings import (
    DEFAULT_GOOGLE_TTS_PITCH,
    DEFAULT_GOOGLE_TTS_VOICE,
    DEFAULT_MODEL,
    DEFAULT_TTS_BACKEND,
    DEFAULT_TTS_PITCH,
    DEFAULT_TTS_RATE,
    DEFAULT_TTS_SPEAKING_RATE,
    DEFAULT_TTS_VOICE,
    ENV_API_KEY,
    ENV_DATA_DIR,
)


def project_root() -> Path:
    """Projenin kök klasörünü döndürür (bu dosya `core/` içinde)."""
    return Path(__file__).resolve().parents[1]


def _default_data_dir() -> Path:
    """Veri klasörünü seçer.

    Öncelik sırası:
        1. `DRAGON_DATA_DIR` ortam değişkeni.
        2. Paketlenmiş (exe) çalışma -> `%APPDATA%/Dragon`.
        3. Geliştirme çalışması -> projedeki `data/` klasörü.
    """
    override = os.environ.get(ENV_DATA_DIR, "").strip()
    if override:
        return Path(override).expanduser().resolve()

    if getattr(sys, "frozen", False):
        if sys.platform == "win32":
            base = os.environ.get("APPDATA") or os.path.expanduser("~")
        else:
            base = os.environ.get("XDG_DATA_HOME") or os.path.join(
                os.path.expanduser("~"), ".local", "share"
            )
        return Path(base) / "Dragon"

    return project_root() / "data"


DATA_DIR = _default_data_dir()
CHATS_DIR = DATA_DIR / "chats"
MEDIA_DIR = DATA_DIR / "media"
WORKSPACE_DIR = DATA_DIR / "workspace"
SETTINGS_FILE = DATA_DIR / "settings.json"
EXPORT_DIR = DATA_DIR / "exports"


def ensure_dirs() -> None:
    """Gerekli tüm klasörleri oluşturur."""
    for path in (DATA_DIR, CHATS_DIR, MEDIA_DIR, WORKSPACE_DIR, EXPORT_DIR):
        path.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Ayarlar
# ---------------------------------------------------------------------------

DEFAULT_SETTINGS: dict[str, Any] = {
    "api_key": "",
    "model": DEFAULT_MODEL,
    "temperature": 0.7,
    "max_output_tokens": 8192,
    "system_prompt": "",  # boşsa core.prompts.SYSTEM_PROMPT kullanılır
    "assistant_name": "Dragon",
    "web_search_enabled": True,
    "file_tools_enabled": True,
    "ui_theme": "dark",
    "font_scale": 1.0,
    "tts_backend": DEFAULT_TTS_BACKEND,
    "google_tts_key": "",
    "google_tts_voice": DEFAULT_GOOGLE_TTS_VOICE,
    "tts_speaking_rate": DEFAULT_TTS_SPEAKING_RATE,
    "google_tts_pitch": DEFAULT_GOOGLE_TTS_PITCH,
    "tts_voice": DEFAULT_TTS_VOICE,
    "tts_rate": DEFAULT_TTS_RATE,
    "tts_pitch": DEFAULT_TTS_PITCH,
}

# ---------------------------------------------------------------------------
# API anahtarını dosyada gizleme
# ---------------------------------------------------------------------------
# Gerçek bir şifreleme değildir; yalnızca düz metin görünmeyi engeller.
# Anahtar uygulama arayüzünde maskeli gösterilir ve exe'ye gömülmez.
_KEY_PREFIX = "drn1:"
_XOR = 0x5A
# Düz metin saklanmaması gereken ayar anahtarları.
_SECRET_KEYS = ("api_key", "google_tts_key")


def _obfuscate(key: str) -> str:
    import base64

    data = bytes(b ^ _XOR for b in key.encode("utf-8"))
    return _KEY_PREFIX + base64.urlsafe_b64encode(data).decode("ascii")


def _deobfuscate(value: str) -> str:
    import base64

    if not value.startswith(_KEY_PREFIX):
        return value
    try:
        raw = base64.urlsafe_b64decode(value[len(_KEY_PREFIX) :].encode("ascii"))
        return bytes(b ^ _XOR for b in raw).decode("utf-8")
    except Exception:
        return ""


def _looks_like_placeholder(key: str) -> bool:
    """Örnek/yer tutucu gibi görünen anahtarları gerçek anahtar sayma."""
    lowered = key.strip().lower()
    markers = ("buraya", "your_", "your-", "xxx", "example", "placeholder", "anahtarin", "anahtar")
    return any(marker in lowered for marker in markers)


def load_settings() -> dict[str, Any]:
    """Kayıtlı ayarları varsayılanlarla birleştirerek döndürür."""
    ensure_dirs()
    data: dict[str, Any] = dict(DEFAULT_SETTINGS)
    if SETTINGS_FILE.exists():
        try:
            stored = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
            if isinstance(stored, dict):
                data.update(stored)
        except (json.JSONDecodeError, OSError):
            pass
    # Kayıtlı gizli anahtarları çöz (eski düz metinler de kabul edilir).
    for skey in _SECRET_KEYS:
        stored = data.get(skey) or ""
        if stored.startswith(_KEY_PREFIX):
            data[skey] = _deobfuscate(stored)
        else:
            data[skey] = stored

    # Kayıtlı Gemini anahtarı yoksa .env'deki anahtara düş.
    if not data.get("api_key") and ENV_API_KEY:
        data["api_key"] = ENV_API_KEY
    # Yer tutucu görünümlü anahtarlar boş kabul edilir (ilk açılış penceresi açılır).
    for skey in _SECRET_KEYS:
        if _looks_like_placeholder(str(data.get(skey, ""))):
            data[skey] = ""
    return data


def save_settings(settings: dict[str, Any]) -> None:
    """Ayarları diske yazar (gizli anahtarlar düz metin saklanmaz)."""
    ensure_dirs()
    to_store = dict(settings)
    for skey in _SECRET_KEYS:
        value = to_store.get(skey) or ""
        if value and not value.startswith(_KEY_PREFIX) and not _looks_like_placeholder(value):
            to_store[skey] = _obfuscate(value)
    tmp = SETTINGS_FILE.with_suffix(".json.tmp")
    tmp.write_text(
        json.dumps(to_store, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    tmp.replace(SETTINGS_FILE)


# ---------------------------------------------------------------------------
# Sohbetler
# ---------------------------------------------------------------------------

def _chat_path(chat_id: str) -> Path:
    safe = "".join(c for c in chat_id if c.isalnum() or c in "-_")
    return CHATS_DIR / f"{safe}.json"


def new_chat(name: str = "Yeni sohbet") -> dict[str, Any]:
    """Bellekte yeni bir sohbet sözlüğü oluşturur (diske yazmaz)."""
    now = time.time()
    return {
        "id": uuid.uuid4().hex[:12],
        "title": name,
        "created": now,
        "updated": now,
        "messages": [],
    }


def save_chat(chat: dict[str, Any]) -> None:
    """Sohbeti diske yazar, `updated` alanını günceller."""
    ensure_dirs()
    chat["updated"] = time.time()
    path = _chat_path(chat["id"])
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(chat, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def load_chat(chat_id: str) -> dict[str, Any] | None:
    """Kayıtlı bir sohbeti okur, yoksa None döndürür."""
    path = _chat_path(chat_id)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def delete_chat(chat_id: str) -> None:
    """Sohbeti ve ona ait medyayı siler."""
    path = _chat_path(chat_id)
    if path.exists():
        path.unlink()
    media = MEDIA_DIR / chat_id
    if media.exists():
        shutil.rmtree(media, ignore_errors=True)


def list_chats() -> list[dict[str, Any]]:
    """Kayıtlı sohbetlerin özet listesini (en yeni önce) döndürür."""
    ensure_dirs()
    items: list[dict[str, Any]] = []
    for path in CHATS_DIR.glob("*.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        items.append(
            {
                "id": data.get("id", path.stem),
                "title": data.get("title", "Sohbet"),
                "updated": data.get("updated", 0),
                "count": len(data.get("messages", [])),
            }
        )
    items.sort(key=lambda item: item["updated"], reverse=True)
    return items


# ---------------------------------------------------------------------------
# Medya (görseller)
# ---------------------------------------------------------------------------

def store_image(chat_id: str, source_path: str | os.PathLike[str]) -> str:
    """Kullanıcının seçtiği görseli sohbet klasörüne kopyalar.

    Görselin kalıcı olmasını sağlar ve yeni yolunu döndürür.
    """
    ensure_dirs()
    src = Path(source_path)
    target_dir = MEDIA_DIR / chat_id
    target_dir.mkdir(parents=True, exist_ok=True)
    ext = src.suffix.lower() or ".png"
    target = target_dir / f"{uuid.uuid4().hex[:10]}{ext}"
    shutil.copy2(src, target)
    return str(target)


def workspace_path() -> Path:
    """Dosya araçlarının kullanacağı güvenli çalışma klasörü."""
    ensure_dirs()
    return WORKSPACE_DIR
