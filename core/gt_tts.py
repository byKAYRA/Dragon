"""Google Cloud Text-to-Speech motoru — doğal Türkçe sinirsel sesler.

Google'ın REST uç noktasını (`textsynthesize`) doğrudan standart `urllib`
ile çağırır; ağır `grpcio`/`protobuf` bağımlılığı gerekmez. Bu sayede
paketlenen exe boyutu küçük kalır.

Kimlik doğrulama bir Google Cloud API anahtarıyla yapılır (Ayarlar'da
girilir). Gemini/AI Studio anahtarı bu hizmetle çalışmaz; kullanıcı
console.cloud.google.com'dan "Cloud Text-to-Speech API"yi açıp bir API
anahtarı oluşturmalıdır.
"""

from __future__ import annotations

import base64
import json
import struct
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

REST_URL = "https://texttospeech.googleapis.com/v1/text:synthesize"
SAMPLE_RATE = 24000


class GoogleTTSError(Exception):
    """Kullanıcıya gösterilebilir Google TTS hatası."""


def synthesize(
    text: str,
    out_wav: Path,
    *,
    voice: str,
    api_key: str,
    speaking_rate: float = 0.92,
    pitch: float = -3.0,
) -> bool:
    """Metni Google TTS ile sentezler ve WAV olarak `out_wav` içine yazar.

    Returns:
        Çıktı oluştuysa True.
    """
    text = (text or "").strip()
    if not text:
        raise GoogleTTSError("Seslendirilecek metin boş.")
    if len(text.encode("utf-8")) > 4800:
        text = text[:1600]

    api_key = (api_key or "").strip()
    if not api_key:
        raise GoogleTTSError("Google TTS API anahtarı tanımlı değil.")

    payload = {
        "input": {"text": text},
        "voice": {"languageCode": "tr-TR", "name": voice},
        "audioConfig": {
            "audioEncoding": "LINEAR16",
            "sampleRateHertz": SAMPLE_RATE,
            "speakingRate": float(speaking_rate),
            "pitch": float(pitch),
        },
    }
    url = f"{REST_URL}?key={urllib.parse.quote(api_key)}"
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=25) as response:
            body = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:400]
        raise GoogleTTSError(_friendly_http_error(exc.code, detail)) from exc
    except Exception as exc:  # ağ / DNS / zaman aşımı
        raise GoogleTTSError(f"Google TTS'e ulaşılamadı: {exc}") from exc

    audio_b64 = body.get("audioContent") or ""
    if not audio_b64:
        raise GoogleTTSError("Google TTS boş ses döndürdü (kota/ağ?).")
    pcm = base64.b64decode(audio_b64)
    _write_wav(Path(out_wav), pcm)
    return Path(out_wav).exists() and Path(out_wav).stat().st_size > 0


def _write_wav(path: Path, pcm: bytes) -> None:
    """Ham LINEAR16 PCM'i geçerli bir WAV dosyasına çevirir."""
    frame_size = SAMPLE_RATE * 2  # mono * 2 byte
    riff_size = 36 + len(pcm)
    header = b""
    header += b"RIFF" + struct.pack("<I", riff_size) + b"WAVE"
    header += b"fmt " + struct.pack("<IHHIIHH", 16, 1, 1, SAMPLE_RATE, frame_size, 2, 16)
    header += b"data" + struct.pack("<I", len(pcm))
    path.write_bytes(header + pcm)


def _friendly_http_error(code: int, detail: str) -> str:
    lowered = detail.lower()
    if code == 403 and ("api key" in lowered or "permission" in lowered):
        return (
            "Google TTS anahtarı reddedildi. Cloud Text-to-Speech API'yi "
            "console.cloud.google.com üzerinden açıp doğru anahtarı girin."
        )
    if code == 404:
        return "Seçili Google sesi bulunamadı; Ayarlar'dan başka bir ses seçin."
    return f"Google TTS isteği başarısız ({code}): {detail[:200]}"