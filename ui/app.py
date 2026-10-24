"""Dragon masaüstü uygulaması — haber merkezi (hub) arayüzü.

Tarife göre düz (flat), koyu siyah zemin + neon mavi çerçeveler:
    * Üst ortada DRAGON + DRAGON KERNEL v1.0
    * Sol üstte Hava Durumu paneli
    * Sol altta GÜNDEM paneli
    * Ortada ses dalgası görselleştirmesi (tıklayınca dinler, yanıtı sesli okur)
    * Alt ortada metin komut çubuğu (klavyeyle komut/soru gönderme)
"""

from __future__ import annotations

import math
import queue
import threading
import tkinter as tk
from pathlib import Path
from typing import Any

import customtkinter as ctk

from config import settings as app_settings
from core import storage
from core.agent import AgentError, DragonAgent
from core.voice import VoiceEngine, VoiceError
from core.wake_word import WakeWordListener
from tools import x_trends
from ui.settings_dialog import SettingsDialog
from ui.theme import FONT_FAMILY, get_palette

TITLE_TEXT = "D R A G O N"
SUBTITLE_TEXT = "DRAGON KERNEL v1.0"
WINDOW_SIZE = "1180x800"

WEATHER = {
    "city": "İstanbul, TR",
    "state": "Parçalı Bulutlu",
    "temp": "18°C",
    "humidity": "75%",
    "wind": "10 km/h",
}

AGENDA = [
    "Teknoloji Gelişmeleri",
    "AI Modelleri Piyasaya Sürüldü",
    "Küresel Piyasalar Hareketli",
]


def _hex_to_rgb(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    return tuple(int(value[i : i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def _rgb_to_hex(rgb: tuple[float, float, float]) -> str:
    return "#{:02x}{:02x}{:02x}".format(
        max(0, min(255, int(rgb[0]))),
        max(0, min(255, int(rgb[1]))),
        max(0, min(255, int(rgb[2]))),
    )


def _lerp_color(c1: str, c2: str, t: float) -> str:
    a, b = _hex_to_rgb(c1), _hex_to_rgb(c2)
    t = max(0.0, min(1.0, t))
    return _rgb_to_hex(tuple(a[i] + (b[i] - a[i]) * t for i in range(3)))


def _shade(color: str, factor: float) -> str:
    rgb = _hex_to_rgb(color)
    return _rgb_to_hex(tuple(c * factor for c in rgb))


class VoiceVisualizer(ctk.CTkFrame):
    """Ortadaki yuvarlak ses görselleştirme ögesi.

    Modlar: idle (bekleme), listening (dinleme), speaking (konuşma).
    Düz (flat) çizim, neon renk geçişleri, tıklanabilir.
    """

    MODE_IDLE = "idle"
    MODE_LISTENING = "listening"
    MODE_SPEAKING = "speaking"

    def __init__(
        self,
        master,
        *,
        palette: dict[str, str],
        size: int = 390,
        on_click: Any = None,
    ) -> None:
        super().__init__(master, fg_color="transparent")
        self.palette = palette
        self.size = size
        self.on_click = on_click
        self.mode = self.MODE_IDLE
        self._phase = 0.0
        self._max_bars = 48

        self.canvas = tk.Canvas(
            self,
            width=size,
            height=size,
            bg=palette["window"],
            highlightthickness=0,
            bd=0,
        )
        self.canvas.pack()
        self.canvas.bind("<Button-1>", self._clicked)
        self.after(40, self._tick)

    # ------------------------------------------------------------------
    def _clicked(self, _event) -> None:
        if self.on_click is not None:
            self.on_click()

    def set_mode(self, mode: str) -> None:
        self.mode = mode

    # ------------------------------------------------------------------
    def _tick(self) -> None:
        if self.mode == self.MODE_LISTENING:
            self._phase += 0.16
        elif self.mode == self.MODE_SPEAKING:
            self._phase += 0.06
        else:
            self._phase += 0.025
        self._paint()
        self.after(40, self._tick)

    # ------------------------------------------------------------------
    def _paint(self) -> None:
        canvas = self.canvas
        canvas.delete("all")
        cx = cy = self.size / 2
        radius = min(self.size / 2 - 20, 185)
        palette = self.palette

        if self.mode == self.MODE_LISTENING:
            self._draw_radial_bars(cx, cy, radius, big=True)
            self._draw_ring(cx, cy, radius * 1.0, palette["ring_a"], 2, dash=None)
            self._draw_core(cx, cy, radius * 0.42, "🎤")
            # Dönen neon yay
            canvas.create_arc(
                cx - radius, cy - radius, cx + radius, cy + radius,
                start=self._phase * 18 % 360, extent=72,
                style=tk.ARC, outline=palette["pink"], width=3,
            )
        elif self.mode == self.MODE_SPEAKING:
            self._draw_radial_bars(cx, cy, radius, big=False)
            self._draw_ring(cx, cy, radius * 1.0, palette["ring_b"], 2, dash=None)
            self._draw_core(cx, cy, radius * 0.42, "🎙️")
            canvas.create_arc(
                cx - radius, cy - radius, cx + radius, cy + radius,
                start=-(self._phase * 10 % 360), extent=120,
                style=tk.ARC, outline=palette["ring_a"], width=3,
            )
        else:
            self._draw_idle(cx, cy, radius, palette)

    def _draw_idle(self, cx, cy, radius, palette) -> None:
        canvas = self.canvas
        pulse = 1 + 0.06 * math.sin(self._phase * 2)

        # Düz neon görünüm: kademeli halkalar (ışıma benzeri katmanlar)
        for i, (rr, width, color) in enumerate(
            [
                (radius * pulse, 1, _shade(palette["ring_idle"], 0.35)),
                (radius * 0.99, 2, palette["ring_idle"]),
                (radius * 0.985 + 4, 1, _shade(palette["ring_idle"], 0.5)),
            ]
        ):
            canvas.create_oval(
                cx - rr, cy - rr, cx + rr, cy + rr,
                outline=color, width=width,
            )

        canvas.create_oval(
            cx - radius * 0.72, cy - radius * 0.72,
            cx + radius * 0.72, cy + radius * 0.72,
            outline=_shade(palette["ring_idle"], 0.55),
            width=1,
            dash=(3, 8),
        )
        self._draw_core(cx, cy, radius * 0.5, "🎤")

    def _draw_core(self, cx, cy, r, icon) -> None:
        canvas = self.canvas
        palette = self.palette
        canvas.create_oval(
            cx - r, cy - r, cx + r, cy + r,
            fill=palette["surface"], outline=palette["ring_idle"], width=1,
        )
        font = ("Segoe UI Emoji", max(16, int(self.size * 0.10)))
        canvas.create_text(cx, cy, text=icon, font=font, fill=palette["text"])

    def _draw_ring(self, cx, cy, radius, color, width, dash) -> None:
        self.canvas.create_oval(
            cx - radius, cy - radius, cx + radius, cy + radius,
            outline=color, width=width, dash=dash,
        )

    def _draw_radial_bars(self, cx, cy, radius, big: bool) -> None:
        """Çember etrafında neon geçişli ses çubukları."""
        canvas = self.canvas
        palette = self.palette
        n = self._max_bars
        amplitude = 26 if big else 14
        for i in range(n):
            angle = -math.pi / 2 + i * (2 * math.pi / n)
            depth = 0.5 + 0.5 * math.sin(self._phase + i * 0.55)
            inner_r = radius - (10 + depth * amplitude)
            outer_r = radius - 2
            x1 = cx + inner_r * math.cos(angle)
            y1 = cy + inner_r * math.sin(angle)
            x2 = cx + outer_r * math.cos(angle)
            y2 = cy + outer_r * math.sin(angle)

            progress = i / n
            if progress < 0.5:
                color = _lerp_color(palette["ring_a"], palette["ring_b"], progress * 2)
            else:
                color = _lerp_color(palette["ring_b"], palette["pink"], (progress - 0.5) * 2)

            width = 4 if big else 3
            canvas.create_line(
                x1, y1, x2, y2,
                fill=color, width=width,
                capstyle=tk.ROUND,
            )


class ApprovalDialog(ctk.CTkToplevel):
    """Riskli bir bilgisayar işlemi için modal onay penceresi."""

    def __init__(
        self,
        master,
        *,
        description: str,
        palette: dict[str, str],
    ) -> None:
        super().__init__(master)
        self.approved = False
        self.palette = palette

        self.title("Dragon — Onay gerekli")
        self.geometry("520x260")
        self.resizable(False, False)
        self.configure(fg_color=palette["window"])
        self.transient(master)
        self.grab_set()
        self._center(master)

        ctk.CTkLabel(
            self,
            text="Dragon bilgisayarında şu işlemi yapacak:",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13),
            text_color=palette["muted"],
        ).pack(padx=28, pady=(22, 8))

        ctk.CTkLabel(
            self,
            text=description,
            font=ctk.CTkFont(family="Consolas", size=13, weight="bold"),
            text_color=palette["title"],
            wraplength=460,
            justify="left",
        ).pack(padx=28, pady=(0, 10))

        ctk.CTkLabel(
            self,
            text="Bu komutu çalıştırmana izin veriyor musun?",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            text_color=palette["muted"],
        ).pack(pady=(0, 18))

        buttons = ctk.CTkFrame(self, fg_color="transparent")
        buttons.pack(pady=(0, 20))
        ctk.CTkButton(
            buttons,
            text="Hayır",
            width=110,
            fg_color="transparent",
            border_width=1,
            border_color=palette["border"],
            text_color=palette["text"],
            hover_color=palette["surface_alt"],
            command=lambda: self._close(False),
        ).pack(side="left", padx=(0, 12))
        ctk.CTkButton(
            buttons,
            text="Evet, Onayla",
            width=130,
            fg_color=palette["accent"],
            hover_color=palette["accent_hover"],
            command=lambda: self._close(True),
        ).pack(side="left")

        self.protocol("WM_DELETE_WINDOW", lambda: self._close(False))

    def _close(self, approved: bool) -> None:
        self.approved = approved
        self.destroy()

    def _center(self, master) -> None:
        self.update_idletasks()
        try:
            master.update_idletasks()
            x = master.winfo_rootx() + (master.winfo_width() - 520) // 2
            y = master.winfo_rooty() + (master.winfo_height() - 260) // 2
            self.geometry(f"+{max(0, x)}+{max(0, y)}")
        except Exception:
            pass


class DragonApp(ctk.CTk):
    """Uygulamanın kök penceresi."""

    def __init__(self) -> None:
        super().__init__()

        storage.ensure_dirs()
        self.settings = storage.load_settings()
        theme_mode = self.settings.get("ui_theme", "dark")
        self.palette = get_palette(theme_mode)

        ctk.set_appearance_mode("light" if theme_mode == "light" else "dark")
        ctk.set_default_color_theme("blue")

        self.title(f"{app_settings.APP_NAME} — {app_settings.APP_TAGLINE}")
        self.geometry(WINDOW_SIZE)
        self.minsize(920, 640)
        self.configure(fg_color=self.palette["window"])
        self._set_window_icon()
        self.lift()
        self.attributes("-topmost", True)
        self.after(300, lambda: self.attributes("-topmost", False))
        self.focus_force()

        self.voice = VoiceEngine(
            tts_backend=self.settings.get(
                "tts_backend", app_settings.DEFAULT_TTS_BACKEND
            ),
            google_tts_key=self.settings.get("google_tts_key", ""),
            google_tts_voice=self.settings.get(
                "google_tts_voice", app_settings.DEFAULT_GOOGLE_TTS_VOICE
            ),
            tts_speaking_rate=float(
                self.settings.get("tts_speaking_rate", 0.92)
            ),
            google_tts_pitch=float(
                self.settings.get(
                    "google_tts_pitch", app_settings.DEFAULT_GOOGLE_TTS_PITCH
                )
            ),
            tts_voice=self.settings.get("tts_voice", app_settings.DEFAULT_TTS_VOICE),
            tts_rate=self.settings.get("tts_rate", app_settings.DEFAULT_TTS_RATE),
            tts_pitch=self.settings.get(
                "tts_pitch", app_settings.DEFAULT_TTS_PITCH
            ),
        )
        self.agent: DragonAgent | None = None
        self._busy = False
        self._events: queue.Queue = queue.Queue()
        self._wake_word: WakeWordListener | None = None
        self._wake_word_enabled = False

        self._build_layout()
        self._set_status("Hazır — çembere tıklayarak konuşun veya komut yazın.")
        self._update_status_bar()

        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(80, self._pump_events)
        if not (self.settings.get("api_key") or "").strip():
            self.after(500, self._first_run)

    # ==================================================================
    # Arayüz kurulumu
    # ==================================================================
    def _set_window_icon(self) -> None:
        icon_path = Path(__file__).resolve().parents[1] / "assets" / "icon.ico"
        if not icon_path.exists():
            return
        try:
            self.iconbitmap(str(icon_path))
        except Exception:
            pass

    def _build_layout(self) -> None:
        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=1)
        self.grid_rowconfigure(2, weight=0)
        self.grid_columnconfigure(0, weight=0, minsize=320)
        self.grid_columnconfigure(1, weight=1)

        self._build_header()
        self._build_left_panel()
        self._build_center_panel()

        footer = ctk.CTkFrame(self, fg_color=self.palette["bg_alt"], corner_radius=0)
        footer.grid(row=2, column=0, columnspan=2, sticky="ew")
        self.status_label = ctk.CTkLabel(
            footer,
            text="",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color=self.palette["muted"],
            anchor="w",
        )
        self.status_label.pack(fill="x", padx=22, pady=8)

    def _build_header(self) -> None:
        header = ctk.CTkFrame(self, fg_color=self.palette["bg_alt"], corner_radius=0)
        header.grid(row=0, column=0, columnspan=2, sticky="ew")

        ctk.CTkButton(
            header,
            text="⚙",
            width=40,
            height=36,
            fg_color="transparent",
            hover_color=self.palette["surface_alt"],
            text_color=self.palette["muted"],
            font=ctk.CTkFont(size=18),
            command=self._open_settings,
        ).pack(side="right", padx=(0, 18), pady=14)

        self._wake_toggle = ctk.CTkButton(
            header,
            text="🎤 Dinleme: Kapalı",
            width=150,
            height=36,
            fg_color="transparent",
            border_width=1,
            border_color=self.palette["border"],
            text_color=self.palette["muted"],
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            command=self._toggle_wake_word,
        )
        self._wake_toggle.pack(side="right", padx=(0, 8), pady=14)

        title_box = ctk.CTkFrame(header, fg_color="transparent")
        title_box.pack(side="top", fill="x", pady=(22, 0))
        ctk.CTkLabel(
            title_box,
            text=TITLE_TEXT,
            font=ctk.CTkFont(family=FONT_FAMILY, size=40, weight="bold"),
            text_color=self.palette["title"],
        ).pack()
        ctk.CTkLabel(
            title_box,
            text=SUBTITLE_TEXT,
            font=ctk.CTkFont(family="Consolas", size=13),
            text_color=self.palette["accent"],
        ).pack(pady=(2, 18))

    def _panel(self, parent, title: str) -> ctk.CTkFrame:
        card = ctk.CTkFrame(
            parent,
            fg_color=self.palette["panel"],
            corner_radius=12,
            border_width=1,
            border_color=self.palette["border"],
        )
        ctk.CTkLabel(
            card,
            text=title,
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            text_color=self.palette["accent"],
            anchor="w",
        ).pack(anchor="w", padx=16, pady=(12, 4))
        return card

    def _build_left_panel(self) -> None:
        left = ctk.CTkFrame(self, fg_color="transparent", width=300)
        left.grid(row=1, column=0, sticky="nsw", padx=(24, 10), pady=20)
        left.grid_propagate(False)
        left.grid_columnconfigure(0, weight=1)
        left.grid_rowconfigure(1, weight=1)

        # --- Hava Durumu ---
        weather = self._panel(left, "HAVA DURUMU")
        weather.grid(row=0, column=0, sticky="ew")
        body = ctk.CTkFrame(weather, fg_color="transparent")
        body.pack(fill="x", padx=16, pady=(0, 14))

        ctk.CTkLabel(
            body, text="☁️", font=ctk.CTkFont(size=36)
        ).pack(anchor="w")
        ctk.CTkLabel(
            body,
            text=WEATHER["city"],
            font=ctk.CTkFont(family=FONT_FAMILY, size=15, weight="bold"),
            text_color=self.palette["text"],
            anchor="w",
        ).pack(fill="x", pady=(4, 0))
        ctk.CTkLabel(
            body,
            text=WEATHER["state"],
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            text_color=self.palette["muted"],
            anchor="w",
        ).pack(fill="x")

        for label, value in (
            ("Sıcaklık", WEATHER["temp"]),
            ("Nem", WEATHER["humidity"]),
            ("Rüzgar", WEATHER["wind"]),
        ):
            row = ctk.CTkFrame(body, fg_color="transparent")
            row.pack(fill="x", pady=(8, 0))
            ctk.CTkLabel(
                row,
                text=label,
                font=ctk.CTkFont(family=FONT_FAMILY, size=12),
                text_color=self.palette["muted"],
                anchor="w",
            ).pack(side="left")
            ctk.CTkLabel(
                row,
                text=value,
                font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
                text_color=self.palette["text"],
                anchor="e",
            ).pack(side="right")

        # --- Gündem / X Trendleri ---
        agenda = self._panel(left, "GÜNDEM · X TRENDLER")
        agenda.grid(row=1, column=0, sticky="new", pady=(16, 0))
        agenda_body = ctk.CTkFrame(agenda, fg_color="transparent")
        agenda_body.pack(fill="both", expand=True, padx=16, pady=(0, 14))
        self._agenda_body = agenda_body
        self._refresh_x_trends()

    def _build_center_panel(self) -> None:
        center = ctk.CTkFrame(self, fg_color="transparent")
        center.grid(row=1, column=1, sticky="nsew")

        self.visualizer = VoiceVisualizer(
            center,
            palette=self.palette,
            size=380,
            on_click=self._toggle_voice,
        )
        self.visualizer.pack(expand=True, pady=(6, 2))

        self.center_hint = ctk.CTkLabel(
            center,
            text="Konuşmak için çembere tıklayın veya komut yazın",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13),
            text_color=self.palette["muted"],
        )
        self.center_hint.pack(pady=(0, 6))

        self.voice_feedback = ctk.CTkLabel(
            center,
            text="",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13),
            text_color=self.palette["text"],
            wraplength=540,
            justify="center",
        )
        self.voice_feedback.pack(pady=(0, 12))

        # Metin Komut Girişi (Chat Input Bar)
        input_frame = ctk.CTkFrame(
            center,
            fg_color=self.palette["surface"],
            corner_radius=22,
            border_width=1,
            border_color=self.palette["border"],
            height=46,
        )
        input_frame.pack(fill="x", padx=40, pady=(0, 16))
        input_frame.pack_propagate(False)

        self.text_input = ctk.CTkEntry(
            input_frame,
            placeholder_text="Dragon'a yazın... (Örn: 'Bugün hava nasıl?', 'Spotify'ı aç')",
            placeholder_text_color=self.palette["muted"],
            font=ctk.CTkFont(family=FONT_FAMILY, size=13),
            fg_color="transparent",
            text_color=self.palette["text"],
            border_width=0,
        )
        self.text_input.pack(side="left", fill="both", expand=True, padx=(16, 8))
        self.text_input.bind("<Return>", lambda _event: self._send_text_command())

        self.send_btn = ctk.CTkButton(
            input_frame,
            text="➤",
            width=36,
            height=32,
            corner_radius=16,
            fg_color=self.palette["accent"],
            hover_color=self.palette["accent_hover"],
            text_color="#ffffff",
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self._send_text_command,
        )
        self.send_btn.pack(side="right", padx=(0, 8), pady=7)

    def _send_text_command(self) -> None:
        """Metin kutusuna girilen komutu Dragon ajanına iletir."""
        if self._busy:
            return
        text = self.text_input.get().strip()
        if not text:
            return
        if not (self.settings.get("api_key") or "").strip():
            self._open_settings()
            return

        self.text_input.delete(0, tk.END)
        self._events.put(("heard", text))
        threading.Thread(
            target=self._process_command, args=(text,), daemon=True
        ).start()

    # ==================================================================
    # Wake-word (sürekli dinleme) - diğer projeden uyarlanmış
    # ==================================================================
    def _toggle_wake_word(self) -> None:
        if self._wake_word_enabled:
            self._stop_wake_word()
        else:
            self._start_wake_word()

    def _start_wake_word(self) -> None:
        if self._wake_word is not None:
            return
        self._wake_word = WakeWordListener(
            on_wake=self._on_wake_command,
            voice_engine=self.voice,
        )
        self._wake_word.start()
        self._wake_word_enabled = True
        self._wake_toggle.configure(
            text="🎤 Dinleme: Açık",
            text_color=self.palette["accent"],
            border_color=self.palette["accent"],
        )
        self._set_status("Wake-word dinleme aktif - 'Dragon' deyin.")

    def _stop_wake_word(self) -> None:
        if self._wake_word is not None:
            self._wake_word.stop()
            self._wake_word = None
        self._wake_word_enabled = False
        self._wake_toggle.configure(
            text="🎤 Dinleme: Kapalı",
            text_color=self.palette["muted"],
            border_color=self.palette["border"],
        )
        self._set_status("Wake-word dinleme durduruldu.")

    def _on_wake_command(self, text: str) -> None:
        """Wake-word tetiklendiğinde çağrılır."""
        if self._busy:
            return
        if not (self.settings.get("api_key") or "").strip():
            return
        self._events.put(("heard", text))
        threading.Thread(
            target=self._process_command, args=(text,), daemon=True
        ).start()

    def _process_command(self, text: str) -> None:
        self._busy = True
        self.visualizer.set_mode(VoiceVisualizer.MODE_LISTENING)
        self._events.put(("tool", "Düşünüyor…"))
        try:
            agent = self._ensure_agent()
            answer = agent.send(
                text,
                on_event=lambda msg: self._events.put(("tool", msg)),
            )
            self._events.put(("answer", answer))
            self._events.put(("speaking",))

            # Konuşurken mikrofon yankısını engellemek için wake-word'ü sessize al
            if self._wake_word is not None:
                self._wake_word.muted = True

            self.voice.speak_async(
                answer,
                on_done=lambda: self._events.put(("speak_done",)),
                on_error=lambda e: self._events.put(("speak_error", str(e))),
                on_status=lambda msg: self._events.put(("tool", msg)),
            )
        except (AgentError, Exception) as exc:
            self._events.put(("error", str(exc)))
            self._busy = False
            if self._wake_word is not None:
                self._wake_word.muted = False
            self.visualizer.set_mode(VoiceVisualizer.MODE_IDLE)

    # ==================================================================
    # Ses asistanı döngüsü
    # ==================================================================
    def _toggle_voice(self) -> None:
        if self._busy:
            return
        if not (self.settings.get("api_key") or "").strip():
            self._open_settings()
            return
        # Wake-word aktifse geçici olarak durdur
        if self._wake_word_enabled:
            self._stop_wake_word()

        self._busy = True
        self.visualizer.set_mode(VoiceVisualizer.MODE_LISTENING)
        self._set_status("Dinliyorum…")
        self.voice_feedback.configure(text="")
        self.center_hint.configure(text="Şimdi konuşun — durunca algılar")

        threading.Thread(target=self._voice_roundtrip, daemon=True).start()

    def _voice_roundtrip(self) -> None:
        events = self._events
        try:
            heard = self.voice.listen()
            heard = (heard or "").strip()
            if not heard:
                events.put(("error", "Anlaşılmadı, tekrar deneyin."))
                return
            events.put(("heard", heard))

            agent = self._ensure_agent()
            answer = agent.send(
                heard,
                on_event=lambda msg: events.put(("tool", msg)),
            )
            events.put(("answer", answer))
            events.put(("speaking",))

            # Konuşurken mikrofon yankısını önlemek için wake-word'ü sessize al
            if self._wake_word is not None:
                self._wake_word.muted = True

            self.voice.speak_async(
                answer,
                on_done=lambda: events.put(("speak_done",)),
                on_error=lambda e: events.put(("speak_error", str(e))),
                on_status=lambda msg: events.put(("tool", msg)),
            )
        except VoiceError as exc:
            events.put(("error", str(exc)))
        except AgentError as exc:
            events.put(("error", str(exc)))
        except Exception as exc:  # beklenmeyen
            events.put(("error", f"Beklenmeyen hata: {exc}"))

    def _pump_events(self) -> None:
        try:
            while True:
                kind, *rest = self._events.get_nowait()
                value = rest[0] if rest else None
                if kind == "heard":
                    self.voice_feedback.configure(text=f"✨ {value}")
                    self._set_status("Yanıt hazırlanıyor…")
                elif kind == "tool":
                    self._set_status(str(value))
                elif kind == "answer":
                    preview = str(value)
                    if len(preview) > 280:
                        preview = preview[:277] + "…"
                    self.voice_feedback.configure(text=f"💬 {preview}")
                    self._set_status("Dragon yanıtlıyor…")
                elif kind == "speaking":
                    self.visualizer.set_mode(VoiceVisualizer.MODE_SPEAKING)
                    self.center_hint.configure(text="Dragon konuşuyor")
                elif kind == "approval":
                    description, reply = rest[0], rest[1]
                    self.visualizer.set_mode(VoiceVisualizer.MODE_IDLE)
                    self.center_hint.configure(text="Komut onayı bekleniyor")
                    self._set_status("⚠️ Bilgisayar işlemi için onay gerekli")
                    dialog = ApprovalDialog(
                        self,
                        description=description,
                        palette=self.palette,
                    )
                    dialog.wait_window()
                    reply.put(dialog.approved)
                    self.center_hint.configure(text="Konuşmak için çembere tıklayın veya komut yazın")
                elif kind == "speak_done":
                    self._finish_voice()
                elif kind == "speak_error":
                    self._finish_voice()
                    self._set_status(f"⚠️ Seslendirme uyarısı: {value}")
                elif kind == "error":
                    self._finish_voice(started=False)
                    self.voice_feedback.configure(text="")
                    self._set_status(f"⚠️ {value}")
        except queue.Empty:
            pass
        self.after(80, self._pump_events)

    def _finish_voice(self, *, started: bool = True) -> None:
        self._busy = False
        if self._wake_word is not None:
            self._wake_word.muted = False
        self.visualizer.set_mode(VoiceVisualizer.MODE_IDLE)
        self.center_hint.configure(text="Konuşmak için çembere tıklayın veya komut yazın")
        if started:
            self._set_status("Hazır")

    # ==================================================================
    # Ajan ve ayarlar
    # ==================================================================
    def _ensure_agent(self) -> DragonAgent:
        if self.agent is None:
            self.agent = DragonAgent(
                self.settings,
                approval_requester=self._request_approval,
            )
        return self.agent

    def _request_approval(self, description: str) -> bool:
        """Riskli bir aracı çalıştırmadan önce kullanıcı onayı ister.

        Ajan (işçi) iş parçacığında çalışır; pencere katmanı uygulama
        iş parçacığında modal bir diyalog gösterir. Sonuç kuyruktan döner.
        """
        reply: queue.Queue = queue.Queue()
        self._events.put(("approval", description, reply))
        try:
            return bool(reply.get(timeout=180))
        except queue.Empty:
            return False

    def _open_settings(self) -> None:
        SettingsDialog(
            self,
            palette=self.palette,
            current=self.settings,
            on_save=self._apply_settings,
        )

    def _apply_settings(self, new_settings: dict[str, Any]) -> None:
        self.settings = new_settings
        storage.save_settings(new_settings)
        # Model/anahtar değiştiyse ajan yeniden kurulsun.
        self.agent = None
        # Ses ayarları değiştiyse ses motorunu yenile.
        self.voice = VoiceEngine(
            tts_backend=self.settings.get(
                "tts_backend", app_settings.DEFAULT_TTS_BACKEND
            ),
            google_tts_key=self.settings.get("google_tts_key", ""),
            google_tts_voice=self.settings.get(
                "google_tts_voice", app_settings.DEFAULT_GOOGLE_TTS_VOICE
            ),
            tts_speaking_rate=float(
                self.settings.get("tts_speaking_rate", 0.92)
            ),
            google_tts_pitch=float(
                self.settings.get(
                    "google_tts_pitch", app_settings.DEFAULT_GOOGLE_TTS_PITCH
                )
            ),
            tts_voice=self.settings.get("tts_voice", app_settings.DEFAULT_TTS_VOICE),
            tts_rate=self.settings.get("tts_rate", app_settings.DEFAULT_TTS_RATE),
            tts_pitch=self.settings.get(
                "tts_pitch", app_settings.DEFAULT_TTS_PITCH
            ),
        )
        self._set_status("Ayarlar kaydedildi.")
        self._update_status_bar()

    def _first_run(self) -> None:
        self._set_status("Dragon'a hoş geldiniz! Lütfen Ayarlar penceresinden API anahtarınızı girin.")
        self._open_settings()

    # ==================================================================
    # Durum çubuğu / yaşam döngüsü
    # ==================================================================
    def _set_status(self, text: str) -> None:
        self.status_label.configure(text=text)

    def _refresh_x_trends(self) -> None:
        if not hasattr(self, "_agenda_body"):
            return
        for widget in self._agenda_body.winfo_children():
            widget.destroy()
        try:
            trends = x_trends.get_trending_topics(limit=8)
        except Exception:
            trends = []
        if not trends:
            row = ctk.CTkFrame(self._agenda_body, fg_color="transparent")
            row.pack(fill="x", pady=7)
            ctk.CTkLabel(
                row,
                text="--",
                font=ctk.CTkFont(family="Consolas", size=12, weight="bold"),
                text_color=self.palette["muted"],
                width=26,
                anchor="w",
            ).pack(side="left")
            ctk.CTkLabel(
                row,
                text="Trendler yüklenemedi",
                font=ctk.CTkFont(family=FONT_FAMILY, size=12),
                text_color=self.palette["muted"],
                anchor="w",
            ).pack(side="left", fill="x", expand=True)
            self.after(300000, self._refresh_x_trends)
            return
        for item in trends:
            row = ctk.CTkFrame(self._agenda_body, fg_color="transparent")
            row.pack(fill="x", pady=6)
            ctk.CTkLabel(
                row,
                text=f"{item['rank']:02d}",
                font=ctk.CTkFont(family="Consolas", size=12, weight="bold"),
                text_color=self.palette["ring_b"],
                width=26,
                anchor="w",
            ).pack(side="left")
            text = item["tag"]
            if item.get("count_text"):
                text = f"{item['tag']}  ({item['count_text']})"
            ctk.CTkLabel(
                row,
                text=text,
                font=ctk.CTkFont(family=FONT_FAMILY, size=12),
                text_color=self.palette["text"],
                anchor="w",
                wraplength=230,
                justify="left",
            ).pack(side="left", fill="x", expand=True)
        self.after(300000, self._refresh_x_trends)

    def _update_status_bar(self) -> None:
        model = self.settings.get("model", app_settings.DEFAULT_MODEL)
        backend = self.settings.get("tts_backend", app_settings.DEFAULT_TTS_BACKEND)
        if backend == "google":
            voice = self.settings.get(
                "google_tts_voice", app_settings.DEFAULT_GOOGLE_TTS_VOICE
            )
            voice_short = voice.replace("tr-TR-", "")
        else:
            voice = self.settings.get("tts_voice", app_settings.DEFAULT_TTS_VOICE)
            voice_short = "Edge " + voice.replace("tr-TR-", "").replace("Neural", "")
        self.status_label.configure(
            text=f"Hazır · model: {model} · ses: {voice_short} · v{app_settings.APP_VERSION}"
        )

    def _on_close(self) -> None:
        try:
            if self._wake_word is not None:
                self._wake_word.stop()
                self._wake_word = None
            storage.save_settings(self.settings)
        finally:
            self.destroy()


def run() -> None:
    """Uygulamayı başlatır."""
    app = DragonApp()
    app.mainloop()
