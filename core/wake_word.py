"""Wake-word dinleyicisi - "Dragon" kelimesini duyunca tetiklenir.

Arka planda sürekli mikrofonu dinler. Wake-word duyulunca,
sonrasındaki konuşmayı yakalar ve on_wake(text) callback'ini çağırır.
"""

from __future__ import annotations

import threading
import time

try:
    import speech_recognition as sr
except ImportError:
    sr = None  # type: ignore

from core.voice import VoiceEngine


class WakeWordListener:
    """Arka planda sürekli mikrofonu dinler.

    Wake-word duyulunca, sonrasındaki konuşmayı yakalar
    ve on_wake(text) callback'ini çağırır.
    """

    def __init__(self, on_wake, voice_engine: VoiceEngine | None = None):
        self.on_wake = on_wake
        self.voice = voice_engine
        self.recognizer = sr.Recognizer() if sr is not None else None
        if self.recognizer is not None:
            self.recognizer.energy_threshold = 280
            self.recognizer.dynamic_energy_threshold = True
        self._thread = None
        self._running = False
        self._muted = False

    def start(self):
        if sr is None or self.recognizer is None:
            print("[WakeWord] speech_recognition modülü yüklü olmadığı için başlatılamadı.")
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        print("[WakeWord] Dinleniyor... 'Dragon' diyerek başlatın.")

    def stop(self):
        self._running = False

    @property
    def muted(self) -> bool:
        return self._muted

    @muted.setter
    def muted(self, value: bool):
        self._muted = value

    def _loop(self):
        if sr is None or self.recognizer is None:
            return
        try:
            with sr.Microphone() as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
                while self._running:
                    if self._muted:
                        time.sleep(0.2)
                        continue
                    try:
                        audio = self.recognizer.listen(
                            source, timeout=5, phrase_time_limit=4
                        )
                        try:
                            text = self.recognizer.recognize_google(
                                audio, language="tr-TR"
                            ).lower()
                        except Exception:
                            continue

                        print(f"[WakeWord] Duyuldu: {text}", flush=True)

                        # Daha esnek wake-word tespiti (farklı telaffuzlar)
                        wake_variants = ("dragon", "dragın", "dragan", "dreigon")
                        matched = None
                        for w in wake_variants:
                            if w in text:
                                matched = w
                                break
                        if matched:
                            # Wake-word sonrasındaki kısım varsa onu al
                            after = text.split(matched, 1)[-1].strip()
                            if len(after) > 3:
                                self.on_wake(after)
                            else:
                                # Sadece "Dragon" dediyse sesli yanıt ver ve dinle
                                if self.voice is not None:
                                    done_event = threading.Event()
                                    self.voice.speak_async(
                                        "Evet efendim?",
                                        on_done=done_event.set,
                                        on_error=lambda _e: done_event.set(),
                                    )
                                    done_event.wait(timeout=3.0)
                                    time.sleep(0.3)  # Kendi sesinin sönümlenmesini bekle
                                try:
                                    audio2 = self.recognizer.listen(
                                        source, timeout=6, phrase_time_limit=8
                                    )
                                    cmd = self.recognizer.recognize_google(
                                        audio2, language="tr-TR"
                                    )
                                    if cmd.strip():
                                        self.on_wake(cmd.strip())
                                except (sr.WaitTimeoutError, sr.UnknownValueError):
                                    pass
                                except Exception:
                                    pass
                    except sr.WaitTimeoutError:
                        pass
                    except Exception:
                        pass
        except Exception as exc:
            print(f"[WakeWord] Hata: {exc}")
