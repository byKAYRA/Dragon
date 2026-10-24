"""Sesli giriş/çıkış motoru.

* Giriş  : Google Web Speech API (Ücretsiz, internet gerekir, tr-TR destekli).
* Çıkış  : edge-tts ile doğal Türkçe ses; oynatma pygame (Geri düşüş: winmm).

Tüm dış bağımlılıklar isteğe bağlıdır; modül kurulu değilse anlaşılır
`VoiceError` mesajlarıyla karşılanır, uygulama çökmez.
"""

from __future__ import annotations

import asyncio
import os
import tempfile
import threading
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


class VoiceEngine:
    """Mikrofondan dinler ve metni sesli okur."""

    def __init__(
        self,
        language: str = "tr-TR",
        tts_backend: str = "google",
        google_tts_key: str = "",
        google_tts_voice: str = "tr-TR-Chirp3-HD-Charon",
        tts_speaking_rate: float = 0.92,
        google_tts_pitch: float = -3.0,
        tts_voice: str = "tr-TR-AhmetNeural",
        tts_rate: str = "-8%",
        tts_pitch: str = "-15Hz",
    ) -> None:
        self.language = language
        # TTS arka ucu: "google" (Google Cloud TTS, doğal) veya "edge" (hızlı yedek).
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
        # Daha hassas ve hızlı algılama ayarları (diğer projeden uyarlanmış)
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
        path: Path | None = None
        try:
            on_start = callbacks.get("on_start")
            if on_start is not None:
                on_start()
            path = self._make_audio(text, on_status=callbacks.get("on_status"))
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
                try:
                    path.unlink(missing_ok=True)
                except OSError:
                    pass

    def _make_audio(
        self,
        text: str,
        on_status: Callable[[str], None] | None = None,
    ) -> Path | None:
        """Konuşma sesini üretir: Google tercih, Edge yedek.

        Google anahtarı varsa önce Google Cloud TTS denenir; herhangi bir
        hata/eksiklik durumunda sessizce Edge (hızlı yedek) kullanılır.
        """
        if self.tts_backend == "google" and self.google_tts_key:
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
                return tmp
            except Exception:  # anahtar/ağ/model sorunu -> SAPI5 yedeğe düş
                try:
                    tmp.unlink(missing_ok=True)
                except OSError:
                    pass

        # Yedek 1: SAPI5 (çevrimdışı, Windows yerleşik ses - yalnızca Türkçe ses varsa)
        try:
            import win32com.client
            _spk = win32com.client.Dispatch("SAPI.SpVoice")
            if self._pick_turkish_sapi_voice(_spk) is not None:
                if on_status is not None:
                    on_status("SAPI5 sesi oluşturuluyor…")
                tmp = _temp_audio(".wav", prefix="dragon_sapi5_")
                if self._sapi5_synthesize(text, tmp):
                    return tmp
                tmp.unlink(missing_ok=True)
        except Exception:
            pass

        # Yedek 2: Edge (hızlı, internet gerektirir)
        tmp = _temp_audio(".mp3", prefix="dragon_tts_")
        try:
            asyncio.run(self._save_tts(text, tmp))
        except Exception:
            try:
                tmp.unlink(missing_ok=True)
            except OSError:
                pass
            return None
        return tmp

    def _sapi5_synthesize(self, text: str, path: Path) -> bool:
        """Windows SAPI5 ile çevrimdışı ses sentezi yapar.
        Başarılıysa True döner. Diğer projeden (Yeni Proje xx) uyarlanmıştır.
        """
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

        communicate = Communicate(
            text, voice=self.tts_voice, rate=self.tts_rate, pitch=self.tts_pitch
        )
        await communicate.save(str(path))

    def _play_audio(self, path: Path) -> None:
        """WAV/mp3'ü pygame ile çalar; pygame yoksa winmm/mci'ye düşer."""
        try:
            import pygame

            pygame.mixer.init()
            pygame.mixer.music.load(str(path))
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                threading.Event().wait(0.1)
            pygame.mixer.quit()
            return
        except Exception:
            pass

        try:  # Windows mci (winmm) geri düşüşü
            import ctypes

            mci = ctypes.windll.winmm
            escaped = str(path).replace("\\", "/")
            media_type = "waveaudio" if path.suffix.lower() == ".wav" else "mpegvideo"
            alias = "dragon_tts"
            if mci.mciSendStringW(f'open "{escaped}" type {media_type} alias {alias}', None, 0, None) == 0:
                mci.mciSendStringW(f"play {alias} wait", None, 0, None)
                mci.mciSendStringW(f"close {alias}", None, 0, None)
                return
        except Exception:
            pass

        raise VoiceError("Ses oynatılamadı (pygame yüklü değil).")


def _temp_audio(suffix: str, prefix: str = "dragon_") -> Path:
    """Geçici bir ses dosyası yolu oluşturur (boş dosya hazırlar)."""
    fd, tmp = tempfile.mkstemp(suffix=suffix, prefix=prefix)
    os.close(fd)
    return Path(tmp)