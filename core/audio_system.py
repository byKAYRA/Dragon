"""Dragon ses sistemi — PyAudio tabanlı, async/await ile mikrofon girişi ve
hoparlör çıkışı, jitter buffer, SFX ve konuşma çakışması yönetimi.

Windows-only. PyAudio + asyncio.
"""

from __future__ import annotations

import asyncio
import ctypes
import os
import queue
import threading
import time
from dataclasses import dataclass
from typing import Callable, Optional

import pyaudio

# --------------------------------------------------------------------------- #
# Sabitler
# --------------------------------------------------------------------------- #
INPUT_RATE = 16000
INPUT_CHANNELS = 1
INPUT_SAMPLE_WIDTH = 2  # 16-bit
CHUNK_SIZE = 1024  # frames

OUTPUT_RATE = 24000
OUTPUT_CHANNELS = 1
OUTPUT_SAMPLE_WIDTH = 2
OUTPUT_FRAMES_PER_BUFFER = 2048

JITTER_TARGET_MS = 300
JITTER_TARGET_BYTES = int(OUTPUT_RATE * OUTPUT_SAMPLE_WIDTH * JITTER_TARGET_MS / 1000)
SILENCE_FLUSH_SEC = 0.18
MAX_BUFFER_SEC = 0.6
MAX_BUFFER_BYTES = int(OUTPUT_RATE * OUTPUT_SAMPLE_WIDTH * MAX_BUFFER_SEC)
NEW_RESPONSE_GAP_SEC = 1.0

StatusCallback = Callable[[str], None]  # "listening" | "speaking"


# --------------------------------------------------------------------------- #
# MCI (winmm) ile SFX
# --------------------------------------------------------------------------- #
class MCIPlayer:
    def __init__(self) -> None:
        self._mci = ctypes.windll.winmm
        self._aliases: set[str] = set()

    def play(self, path: str, *, loop: bool = False, alias: str = "sfx") -> None:
        escaped = path.replace("\\", "/")
        media = "waveaudio" if path.lower().endswith(".wav") else "mpegvideo"
        self._mci.mciSendStringW(f'open "{escaped}" type {media} alias {alias}', None, 0, None)
        cmd = f"play {alias}"
        if loop:
            cmd += " repeat"
        self._mci.mciSendStringW(cmd, None, 0, None)
        self._aliases.add(alias)

    def stop(self, alias: str = "sfx") -> None:
        try:
            self._mci.mciSendStringW(f"stop {alias}", None, 0, None)
            self._mci.mciSendStringW(f"close {alias}", None, 0, None)
        except Exception:
            pass
        self._aliases.discard(alias)

    def stop_all(self) -> None:
        for a in list(self._aliases):
            self.stop(a)


# --------------------------------------------------------------------------- #
# Ses girişi: mikrofon -> asyncio.Queue
# --------------------------------------------------------------------------- #
class MicInput:
    def __init__(self, loop: asyncio.AbstractEventLoop) -> None:
        self.loop = loop
        self.queue: asyncio.Queue[bytes] = asyncio.Queue()
        self._pa = pyaudio.PyAudio()
        self._stream = None
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._is_speaking = False  # kilit

    def set_speaking(self, value: bool) -> None:
        self._is_speaking = value

    def start(self) -> None:
        self._running = True
        self._stream = self._pa.open(
            format=pyaudio.paInt16,
            channels=INPUT_CHANNELS,
            rate=INPUT_RATE,
            input=True,
            frames_per_buffer=CHUNK_SIZE,
        )
        self._thread = threading.Thread(target=self._read_loop, daemon=True)
        self._thread.start()

    def _read_loop(self) -> None:
        while self._running:
            try:
                data = self._stream.read(CHUNK_SIZE, exception_on_overflow=False)
            except Exception:
                break
            if self._is_speaking:
                continue  # konuşma sırasında modele gönderme
            self.loop.call_soon_threadsafe(self.queue.put_nowait, data)

    def stop(self) -> None:
        self._running = False
        if self._stream is not None:
            try:
                self._stream.stop_stream()
                self._stream.close()
            except Exception:
                pass
        self._pa.terminate()


# --------------------------------------------------------------------------- #
# Ses çıkışı: jitter buffer + PyAudio
# --------------------------------------------------------------------------- #
@dataclass
class OutputState:
    is_speaking: bool = False


class SpeakerOutput:
    def __init__(self, on_status: StatusCallback) -> None:
        self.on_status = on_status
        self._pa = pyaudio.PyAudio()
        self._stream = self._pa.open(
            format=pyaudio.paInt16,
            channels=OUTPUT_CHANNELS,
            rate=OUTPUT_RATE,
            output=True,
            frames_per_buffer=OUTPUT_FRAMES_PER_BUFFER,
        )
        self._queue: queue.Queue[bytes] = queue.Queue()
        self._buffer = bytearray()
        self._last_chunk_time = 0.0
        self._response_start_time = 0.0
        self._state = OutputState()
        self._lock = threading.Lock()
        self._worker = threading.Thread(target=self._play_loop, daemon=True)
        self._worker.start()

    def enqueue(self, chunk: bytes) -> None:
        now = time.monotonic()
        with self._lock:
            # yeni yanıt mı?
            if self._last_chunk_time and (now - self._last_chunk_time) > NEW_RESPONSE_GAP_SEC:
                self._buffer.clear()
                self._response_start_time = now
            self._last_chunk_time = now
            self._buffer.extend(chunk)
            # hedefe ulaştıysa veya max aşıldıysa kuyruğa aktar
            if len(self._buffer) >= JITTER_TARGET_BYTES or len(self._buffer) >= MAX_BUFFER_BYTES:
                self._flush_buffer_locked()
        # susma kontrolü ayrıca _play_loop içinde

    def _flush_buffer_locked(self) -> None:
        if self._buffer:
            self._queue.put(bytes(self._buffer))
            self._buffer.clear()

    def _play_loop(self) -> None:
        while True:
            # susma flush kontrolü
            with self._lock:
                now = time.monotonic()
                if self._buffer and self._last_chunk_time and (now - self._last_chunk_time) >= SILENCE_FLUSH_SEC:
                    self._flush_buffer_locked()
                if self._buffer and len(self._buffer) >= MAX_BUFFER_BYTES:
                    self._flush_buffer_locked()
            try:
                data = self._queue.get(timeout=0.05)
            except queue.Empty:
                # kuyruk boşaldı -> listening'e dön (geçişte)
                if self._state.is_speaking:
                    self._state.is_speaking = False
                    self.on_status("listening")
                continue
            # speaking geçişi
            if not self._state.is_speaking:
                self._state.is_speaking = True
                self.on_status("speaking")
            self._stream.write(data)

    def wait_until_done(self) -> None:
        # kuyruk ve buffer boşalana kadar bekle
        while not self._queue.empty() or self._buffer:
            time.sleep(0.05)
        # ekstra boşalma süresi
        time.sleep(0.1)

    def close(self) -> None:
        try:
            self._stream.stop_stream()
            self._stream.close()
        except Exception:
            pass
        self._pa.terminate()


# --------------------------------------------------------------------------- #
# Ana ses yöneticisi (async)
# --------------------------------------------------------------------------- #
class AudioSystem:
    def __init__(self, on_status: StatusCallback) -> None:
        self.loop = asyncio.get_event_loop()
        self.on_status = on_status
        self.mic = MicInput(self.loop)
        self.speaker = SpeakerOutput(on_status)
        self.sfx = MCIPlayer()
        self._ambient_alias = "ambient"
        self._thinking_alias = "thinking"
        self._is_speaking = False

    async def start(self) -> None:
        self.mic.start()
        # ambient HUD düşük sesle loop
        # (dosya yolu dışarıdan verilebilir; burada placeholder)
        asyncio.create_task(self._ambient_loop())

    async def _ambient_loop(self) -> None:
        # ambient dosya yolu opsiyonel; yoksa sessiz
        await asyncio.sleep(0)

    def on_speaking_start(self) -> None:
        if self._is_speaking:
            return
        self._is_speaking = True
        self.mic.set_speaking(True)
        self.sfx.stop(self._thinking_alias)
        self.sfx.stop(self._ambient_alias)
        self.on_status("speaking")

    def on_speaking_end(self) -> None:
        # kuyruk boşalana kadar bekle (arka planda)
        threading.Thread(target=self._wait_and_resume, daemon=True).start()

    def _wait_and_resume(self) -> None:
        self.speaker.wait_until_done()
        self._is_speaking = False
        self.mic.set_speaking(False)
        # ambient yeniden başlat (opsiyonel)
        self.on_status("listening")

    def play_sfx(self, path: str, *, alias: str = "sfx", loop: bool = False) -> None:
        if self._is_speaking and alias not in ("thinking",):
            return  # konuşma sırasında SFX sustur
        self.sfx.play(path, loop=loop, alias=alias)

    def stop_sfx(self, alias: str) -> None:
        self.sfx.stop(alias)

    def feed_audio(self, chunk: bytes) -> None:
        self.speaker.enqueue(chunk)

    async def mic_stream(self):
        """LLM API'sine stream edilecek async generator."""
        while True:
            data = await self.mic.queue.get()
            if self._is_speaking:
                continue
            yield data

    def close(self) -> None:
        self.mic.stop()
        self.speaker.close()
        self.sfx.stop_all()
