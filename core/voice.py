"""Sesli giriş/çıkış motoru.

* Giriş  : Google Web Speech API (Ücretsiz, internet gerekir, tr-TR destekli).
* Çıkış  : edge-tts ile doğal Türkçe ses; oynatma pygame (Geri düşüş: winmm).

Tüm dış bağımlılıklar isteğe bağlıdır; modül kurulu değilse anlaşılır
`VoiceError` mesajlarıyla karşılanır, uygulama çökmez.
"""

from __future__ import annotations

import asyncio
import os
import re
import tempfile
import threading
import time
import uuid
from pathlib import Path
from typing import Callable

# pygame "Hello from the pygame community" baskısını sustur.
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

# Yerel bağımlılıkların durumu.
try:
    import speech_recognition as sr
    import pyaudio  # type: ignore

    SPEECH_AVAILABLE = True
except Exception:  # pragma: no cover
    try:
        import speech_recognition as sr  # type: ignore
        SPEECH_AVAILABLE = True
    except Exception:
        sr = None  # type: ignore
        SPEECH_AVAILABLE = False


class VoiceError(Exception):
    """Kullanıcıya gösterilebilir ses motoru hatası."""


def clean_text_for_speech(text: str) -> str:
    """Metni sesli okuma (TTS) için optimize eder ve temizler.

    Markdown biçimlendirmelerini, kod bloklarını, linkleri, emojileri ve
    aşırı uzun metinleri ayıklayarak kulağa doğal gelen Türkçe konuşma metni üretir.
    """
    if not text:
        return ""

    # 1. Kod bloklarını temizle veya konuşma dostu ifadeye çevir
    cleaned = re.sub(
        r"```[^\n`]*\n.*?```",
        " İlgili kod bloğunu ekrana yansıttım efendim. ",
        text,
        flags=re.DOTALL,
    )

    # 2. Satır içi kodlar: `komut` -> komut
    cleaned = re.sub(r"`([^`]+)`", r"\1", cleaned)

    # 3. Web bağlantıları
    cleaned = re.sub(r"https?://\S+", "bağlantı adresi", cleaned)

    # 4. Markdown başlıkları (# Başlık -> Başlık)
    cleaned = re.sub(r"^\s*#+\s*", "", cleaned, flags=re.MULTILINE)

    # 5. Kalın, italik ve üstü çizili (*, **, _, __, ~~)
    cleaned = re.sub(r"\*\*([^*]+)\*\*", r"\1", cleaned)
    cleaned = re.sub(r"\*([^*]+)\*", r"\1", cleaned)
    cleaned = re.sub(r"__([^_]+)__", r"\1", cleaned)
    cleaned = re.sub(r"_([^_]+)_", r"\1", cleaned)
    cleaned = re.sub(r"~~([^~]+)~~", r"\1", cleaned)

    # 6. Liste imleri (- madde, * madde, 1. madde)
    cleaned = re.sub(r"^\s*[-*•]\s+", "", cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r"^\s*\d+\.\s+", "", cleaned, flags=re.MULTILINE)

    # 7. Tablo dikey çizgileri
    cleaned = cleaned.replace("|", " ")

    # 8. Emojileri temizle
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"
        "\U0001F300-\U0001F5FF"
        "\U0001F680-\U0001F6FF"
        "\U0001F1E0-\U0001F1FF"
        "\U00002702-\U000027B0"
        "\U000024C2-\U0001F251"
        "\U0001F900-\U0001F9FF"
        "\U0001FA70-\U0001FAFF"
        "]+",
        flags=re.UNICODE,
    )
    cleaned = emoji_pattern.sub("", cleaned)

    # 9. Fazla boşlukları ve satır sonlarını temizle
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    # 10. Çok uzun yanıtları konuşma için sınırla (ilk 600 karakter civarı)
    if len(cleaned) > 600:
        cutoff = cleaned[:600]
        last_punct = max(cutoff.rfind("."), cutoff.rfind("!"), cutoff.rfind("?"))
        if last_punct > 250:
            cleaned = cutoff[: last_punct + 1] + " Devamını ekrandan okuyabilirsiniz efendim."
        else:
            cleaned = cutoff + "… Devamını ekrandan okuyabilirsiniz efendim."

    return cleaned


class VoiceEngine:
    """Mikrofondan dinler ve metni sesli okur."""

    def __init__(
        self,
        language: str = "tr-TR",
        tts_backend: str = "edge",
        google_tts_key: str = "",
        google_tts_voice: str = "tr-TR-Neural2-C",
        tts_speaking_rate: float = 1.0,
        google_tts_pitch: float = 0.0,
        tts_voice: str = "tr-TR-EmelNeural",
        tts_rate: str = "+0%",
        tts_pitch: str = "+0Hz",
    ) -> None:
        self.language = language
        # TTS arka ucu: "edge" (ücretsiz, doğal Türkçe sesler) veya "google" (Google Cloud TTS).
        self.tts_backend = tts_backend
        self.google_tts_key = google_tts_key
        self.google_tts_voice = google_tts_voice
        self.tts_speaking_rate = tts_speaking_rate
        self.google_tts_pitch = google_tts_pitch
        self.tts_voice = tts_voice
        self.tts_rate = tts_rate
        self.tts_pitch = tts_pitch
        self._speak_lock = threading.Lock()

    # ------------------------------------------------------------------
    # Giriş: mikrofon
    # ------------------------------------------------------------------
    def listen(self, timeout: float = 1.2, phrase_time_limit: float = 3.0) -> str:
        """Mikrofondan bir konuşmayı kaydedip metne çevirir.

        Raises:
            VoiceError: Modül yok, mikrofon yok veya anlayamama durumunda.
        """
        if not SPEECH_AVAILABLE or sr is None:
            raise VoiceError(
                "Ses tanıma modülü yüklü değil. Kurulum için: "
                "pip install SpeechRecognition pyaudio"
            )

        try:
            import pyaudio  # type: ignore
        except Exception:
            raise VoiceError(
                "PyAudio bulunamadı. Mikrofon girişi kullanılamıyor. "
                "Sesli komut yerine metin girişi kullanın veya PyAudio yükleyin."
            )

        recognizer = sr.Recognizer()
        recognizer.energy_threshold = 280
        recognizer.dynamic_energy_threshold = True
        recognizer.pause_threshold = 0.32
        recognizer.non_speaking_duration = 0.22
        recognizer.phrase_threshold = 0.18
        try:
            recognizer.operation_timeout = 2
        except Exception:
            pass
        try:
            with sr.Microphone() as source:
                try:
                    recognizer.adjust_for_ambient_noise(source, duration=0.01)
                except Exception:
                    pass
                audio = recognizer.listen(
                    source,
                    timeout=timeout,
                    phrase_time_limit=phrase_time_limit,
                )
        except OSError as exc:
            raise VoiceError("Mikrofona erişilemedi. Giriş aygıtı bağlı mı?") from exc
        except sr.WaitTimeoutError:
            raise VoiceError("Dinleme zaman aşımı. Tekrar deneyin.") from None
        except Exception as exc:  # ses aygıtı sürücü sorunları
            raise VoiceError(f"Mikrofon hatası: {exc}") from exc

        try:
            return recognizer.recognize_google(audio, language=self.language, show_all=False)
        except sr.UnknownValueError:
            raise VoiceError("Sizi anlayamadım. Lütfen tekrar söyleyin.") from None
        except sr.RequestError as exc:
            raise VoiceError(
                "Ses tanıma servisine ulaşılamadı (İnternet gerekli)."
            ) from exc

    # ------------------------------------------------------------------
    # Çıkış: konuşma
    # ------------------------------------------------------------------
    def speak_async(
        self,
        text: str,
        *,
        on_start: Callable[[], None] | None = None,
        on_done: Callable[[], None] | None = None,
        on_error: Callable[[Exception], None] | None = None,
        on_status: Callable[[str], None] | None = None,
    ) -> None:
        """Metni arka plan iş parçacığında sesli okur (bloklamaz).

        `on_status`, sentez adımlarında (ör. "Google sesi oluşturuluyor…")
        kısa durum metinleriyle çağrılır.
        """
        threading.Thread(
            target=self._speak_job,
            args=(text,),
            kwargs={
                "on_start": on_start,
                "on_done": on_done,
                "on_error": on_error,
                "on_status": on_status,
            },
            daemon=True,
        ).start()

    def _speak_job(self, text: str, **callbacks) -> None:
        cleaned_text = clean_text_for_speech(text)
        if not cleaned_text:
            done = callbacks.get("on_done")
            if done is not None:
                done()
            return

        path: Path | None = None
        try:
            on_start = callbacks.get("on_start")
            if on_start is not None:
                on_start()
            path = self._make_audio(cleaned_text, on_status=callbacks.get("on_status"))
            if path is not None:
                self._play_audio(path)
            done = callbacks.get("on_done")
            if done is not None:
                done()
        except Exception as exc:  # tts üretimi veya oynatma hatası
            err = callbacks.get("on_error")
            if err is not None:
                err(exc)
        finally:
            if path is not None:
                time.sleep(0.05)
                try:
                    path.unlink(missing_ok=True)
                except OSError:
                    pass

    def _make_audio(
        self,
        text: str,
        on_status: Callable[[str], None] | None = None,
    ) -> Path | None:
        """Konuşma sesini üretir: Google (anahtar varsa), Edge (doğal Türkçe), SAPI5 (çevrimdışı)."""
        # 1. Google Cloud TTS (eğer google seçili ve api_key tanımlıysa)
        if self.tts_backend == "google" and bool(self.google_tts_key and self.google_tts_key.strip()):
            tmp = _temp_audio(".wav", prefix="dragon_google_")
            try:
                if on_status is not None:
                    on_status("Google sesi oluşturuluyor…")
                from core import gt_tts

                gt_tts.synthesize(
                    text,
                    tmp,
                    voice=self.google_tts_voice,
                    api_key=self.google_tts_key,
                    speaking_rate=self.tts_speaking_rate,
                    pitch=self.google_tts_pitch,
                )
                if tmp.exists() and tmp.stat().st_size > 0:
                    return tmp
            except Exception:  # anahtar/ağ/model sorunu -> Edge yedeğe geç
                try:
                    tmp.unlink(missing_ok=True)
                except OSError:
                    pass

        # 2. Edge-TTS (Doğal Türkçe sinirsel ses; Microsoft Edge altyapısı, ücretsiz)
        tmp = _temp_audio(".mp3", prefix="dragon_tts_")
        try:
            if on_status is not None:
                on_status("Ses sentezleniyor…")
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(self._save_tts(text, tmp))
            finally:
                loop.close()

            if tmp.exists() and tmp.stat().st_size > 0:
                return tmp
        except Exception:
            try:
                tmp.unlink(missing_ok=True)
            except OSError:
                pass

        # 3. SAPI5 (Windows yerleşik ses motoru - Çevrimdışı son çare)
        try:
            if on_status is not None:
                on_status("SAPI5 sesi oluşturuluyor…")
            tmp = _temp_audio(".wav", prefix="dragon_sapi5_")
            if self._sapi5_synthesize(text, tmp):
                return tmp
            tmp.unlink(missing_ok=True)
        except Exception:
            pass

        return None

    def _sapi5_synthesize(self, text: str, path: Path) -> bool:
        """Windows SAPI5 ile çevrimdışı ses sentezi yapar."""
        try:
            import win32com.client
        except ImportError:
            return False

        try:
            from comtypes import CoInitialize, CoUninitialize
            CoInitialize()
            initialized = True
        except Exception:
            initialized = False

        try:
            speaker = win32com.client.Dispatch("SAPI.SpVoice")
            voice = self._pick_turkish_sapi_voice(speaker)
            if voice is not None:
                speaker.Voice = voice
            file_stream = win32com.client.Dispatch("SAPI.SpFileStream")
            file_stream.Open(str(path), 3)  # 3 = SSFMCreateForWrite
            speaker.AudioOutputStream = file_stream
            speaker.Speak(text)
            file_stream.Close()
            return path.exists() and path.stat().st_size > 0
        except Exception:
            return False
        finally:
            if initialized:
                try:
                    CoUninitialize()
                except Exception:
                    pass

    def _pick_turkish_sapi_voice(self, speaker):
        """Kayıtlı SAPI sesleri içinde Türkçe olanı bulur; yoksa None."""
        hints = ("turkish", "türkçe", "turkce", "tolga", "tr-tr", "tr_tr")
        try:
            voices = speaker.GetVoices()
            for index in range(voices.Count):
                try:
                    item = voices.Item(index)
                    description = str(item.GetDescription()).lower()
                except Exception:
                    continue
                if any(hint in description for hint in hints):
                    return item
        except Exception:
            pass
        return None

    async def _save_tts(self, text: str, path: Path) -> None:
        from edge_tts import Communicate  # yalnızca kullanımda içe aktar

        voice = self.tts_voice or "tr-TR-EmelNeural"
        rate = self.tts_rate or "+0%"
        pitch = self.tts_pitch or "+0Hz"

        # -15Hz / -8% gibi sunucu tarafından reddedilen veya robotik yapan aşırı pes tonları düzelt
        if pitch in ("-15Hz", "-10Hz", "-5Hz"):
            pitch = "+0Hz"
        if rate in ("-8%", "-5%"):
            rate = "+0%"

        try:
            communicate = Communicate(
                text, voice=voice, rate=rate, pitch=pitch
            )
            await communicate.save(str(path))
            if path.exists() and path.stat().st_size > 0:
                return
        except Exception:
            # Seçili ses (örn. AhmetNeural) sunucu hatası verirse güvenilir doğal ses Emel'e düş
            if voice != "tr-TR-EmelNeural":
                communicate = Communicate(
                    text, voice="tr-TR-EmelNeural", rate="+0%", pitch="+0Hz"
                )
                await communicate.save(str(path))
                if path.exists() and path.stat().st_size > 0:
                    return
            raise

    def _play_audio(self, path: Path) -> None:
        """WAV/mp3'ü pygame ile çalar; pygame yoksa winmm/mci'ye düşer."""
        # 1. Pygame dene
        try:
            import pygame

            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=24000, buffer=512)
            pygame.mixer.music.load(str(path))
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                threading.Event().wait(0.04)
            pygame.mixer.music.stop()
            try:
                pygame.mixer.music.unload()
            except Exception:
                pass
            return
        except Exception:
            pass

        # 2. Windows MCI (winmm) geri düşüşü
        try:
            import ctypes

            mci = ctypes.windll.winmm
            escaped = str(path.resolve()).replace("\\", "/")
            media_type = "waveaudio" if path.suffix.lower() == ".wav" else "mpegvideo"
            alias = f"drg_{uuid.uuid4().hex[:6]}"
            if mci.mciSendStringW(f'open "{escaped}" type {media_type} alias {alias}', None, 0, None) == 0:
                mci.mciSendStringW(f"play {alias} wait", None, 0, None)
                mci.mciSendStringW(f"close {alias}", None, 0, None)
                return
        except Exception:
            pass

        raise VoiceError("Ses oynatılamadı. Ses sürücüsü veya oynatıcı bulunamadı.")


def _temp_audio(suffix: str, prefix: str = "dragon_") -> Path:
    """Geçici bir ses dosyası yolu oluşturur (boş dosya hazırlar)."""
    fd, tmp = tempfile.mkstemp(suffix=suffix, prefix=prefix)
    os.close(fd)
    return Path(tmp)
