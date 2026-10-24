"""Ayarlar penceresi (modal)."""

from __future__ import annotations

import os
import subprocess
import sys
from typing import Any, Callable

import customtkinter as ctk

from config import settings as app_settings
from core import storage
from ui.theme import FONT_FAMILY


class SettingsDialog(ctk.CTkToplevel):
    """API anahtarı, model ve davranış ayarlarını düzenleyen pencere."""

    def __init__(
        self,
        master,
        *,
        palette: dict[str, str],
        current: dict[str, Any],
        on_save: Callable[[dict[str, Any]], None],
    ) -> None:
        super().__init__(master)
        self.palette = palette
        self.current = dict(current)
        self.on_save = on_save

        self.title("Ayarlar — Dragon")
        self.geometry("560x680")
        self.resizable(False, True)
        self.configure(fg_color=palette["window"])
        self.transient(master)
        self.grab_set()
        self._center(master)

        container = ctk.CTkScrollableFrame(self, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=20, pady=16)

        self._build_api_section(container)
        self._build_model_section(container)
        self._build_behaviour_section(container)
        self._build_workspace_section(container)

        buttons = ctk.CTkFrame(self, fg_color="transparent")
        buttons.pack(fill="x", padx=20, pady=(0, 16))
        ctk.CTkButton(
            buttons,
            text="İptal",
            width=100,
            fg_color="transparent",
            border_width=1,
            border_color=palette["border"],
            text_color=palette["text"],
            hover_color=palette["surface_alt"],
            command=self.destroy,
        ).pack(side="right", padx=(8, 0))
        ctk.CTkButton(
            buttons,
            text="Kaydet",
            width=120,
            fg_color=palette["accent"],
            hover_color=palette["accent_hover"],
            command=self._save,
        ).pack(side="right")

    # ------------------------------------------------------------------
    def _section(self, parent, title: str) -> ctk.CTkFrame:
        ctk.CTkLabel(
            parent,
            text=title,
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            text_color=self.palette["accent"],
            anchor="w",
        ).pack(fill="x", pady=(14, 6))
        frame = ctk.CTkFrame(
            parent,
            fg_color=self.palette["surface"],
            corner_radius=10,
            border_width=1,
            border_color=self.palette["border"],
        )
        frame.pack(fill="x")
        return frame

    def _build_api_section(self, parent) -> None:
        frame = self._section(parent, "API Anahtarı")
        row = ctk.CTkFrame(frame, fg_color="transparent")
        row.pack(fill="x", padx=14, pady=(12, 4))
        self.key_var = ctk.StringVar(value=self.current.get("api_key", ""))
        self.key_entry = ctk.CTkEntry(
            row,
            textvariable=self.key_var,
            show="•",
            placeholder_text="Google AI Studio API anahtarı",
            fg_color=self.palette["input_bg"],
            border_color=self.palette["border"],
        )
        self.key_entry.pack(fill="x", expand=True)
        ctk.CTkLabel(
            frame,
            text=(
                "Anahtar burada her zaman maskeli görünür ve bu cihazda şifreli "
                "saklanır; paylaşılan dosyalara ya da uygulamaya gömülmez.\n"
                "Boş bırakırsan kayıtlı anahtar korunur."
            ),
            text_color=self.palette["muted"],
            anchor="w",
            justify="left",
            wraplength=490,
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
        ).pack(fill="x", padx=14, pady=(0, 12))

    def _build_model_section(self, parent) -> None:
        frame = self._section(parent, "Model")
        inner = ctk.CTkFrame(frame, fg_color="transparent")
        inner.pack(fill="x", padx=14, pady=12)

        ctk.CTkLabel(
            inner, text="Model adı", text_color=self.palette["muted"], anchor="w"
        ).pack(fill="x")
        self.model_var = ctk.StringVar(
            value=self.current.get("model", app_settings.DEFAULT_MODEL)
        )
        ctk.CTkComboBox(
            inner,
            variable=self.model_var,
            values=app_settings.AVAILABLE_MODELS,
            fg_color=self.palette["input_bg"],
            border_color=self.palette["border"],
            button_color=self.palette["accent"],
            button_hover_color=self.palette["accent_hover"],
        ).pack(fill="x", pady=(4, 12))

        self.temp_label = ctk.CTkLabel(
            inner,
            text=f"Yaratıcılık (temperature): {self.current.get('temperature', 0.7):.1f}",
            text_color=self.palette["muted"],
            anchor="w",
        )
        self.temp_label.pack(fill="x")
        self.temp_slider = ctk.CTkSlider(
            inner,
            from_=0.0,
            to=1.5,
            number_of_steps=15,
            command=self._on_temp,
            progress_color=self.palette["accent"],
        )
        self.temp_slider.set(float(self.current.get("temperature", 0.7)))
        self.temp_slider.pack(fill="x", pady=(4, 12))

        ctk.CTkLabel(
            inner, text="Azami yanıt uzunluğu (token)", text_color=self.palette["muted"], anchor="w"
        ).pack(fill="x")
        self.tokens_var = ctk.StringVar(
            value=str(self.current.get("max_output_tokens", 8192))
        )
        ctk.CTkEntry(
            inner,
            textvariable=self.tokens_var,
            fg_color=self.palette["input_bg"],
            border_color=self.palette["border"],
        ).pack(fill="x", pady=(4, 0))

    def _build_behaviour_section(self, parent) -> None:
        frame = self._section(parent, "Davranış")
        inner = ctk.CTkFrame(frame, fg_color="transparent")
        inner.pack(fill="x", padx=14, pady=12)

        ctk.CTkLabel(
            inner, text="Asistan adı", text_color=self.palette["muted"], anchor="w"
        ).pack(fill="x")
        self.name_var = ctk.StringVar(value=self.current.get("assistant_name", "Dragon"))
        ctk.CTkEntry(
            inner,
            textvariable=self.name_var,
            fg_color=self.palette["input_bg"],
            border_color=self.palette["border"],
        ).pack(fill="x", pady=(4, 12))

        ctk.CTkLabel(
            inner, text="Ses motoru", text_color=self.palette["muted"], anchor="w"
        ).pack(fill="x")
        self.backend_var = ctk.BooleanVar(
            value=self.current.get("tts_backend", app_settings.DEFAULT_TTS_BACKEND) == "google"
        )
        ctk.CTkSwitch(
            inner,
            text="Google Cloud TTS kullan (doğal, önerilen)",
            variable=self.backend_var,
            text_color=self.palette["text"],
            progress_color=self.palette["accent"],
        ).pack(anchor="w", pady=(4, 4))
        ctk.CTkLabel(
            inner,
            text=("Kapatılırsa Microsoft Edge yedek sesi kullanılır (daha hızlı, "
                  "daha az doğal)."),
            text_color=self.palette["muted"],
            anchor="w",
            justify="left",
            wraplength=470,
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
        ).pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(
            inner, text="Google TTS anahtarı", text_color=self.palette["muted"], anchor="w"
        ).pack(fill="x")
        key_row = ctk.CTkFrame(inner, fg_color="transparent")
        key_row.pack(fill="x", pady=(4, 0))
        self.gkey_var = ctk.StringVar(value=self.current.get("google_tts_key", ""))
        self.gkey_entry = ctk.CTkEntry(
            key_row,
            textvariable=self.gkey_var,
            show="•",
            placeholder_text="AIza… (Google Cloud API anahtarı)",
            fg_color=self.palette["input_bg"],
            border_color=self.palette["border"],
        )
        self.gkey_entry.pack(side="left", fill="x", expand=True)
        ctk.CTkButton(
            key_row,
            text="🔑 Nasıl alınır",
            width=104,
            fg_color=self.palette["surface_alt"],
            hover_color=self.palette["border"],
            command=self._open_google_console,
        ).pack(side="left", padx=(8, 0))
        ctk.CTkLabel(
            inner,
            text=(
                "console.cloud.google.com → Cloud Text-to-Speech API'yi etkinleştir "
                "→ Kimlik Bilgileri → API anahtarı oluştur (maskeli saklanır).\n"
                "Boşsa Edge yedek ses kullanılır."
            ),
            text_color=self.palette["muted"],
            anchor="w",
            justify="left",
            wraplength=470,
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
        ).pack(fill="x", pady=(2, 10))

        ctk.CTkLabel(
            inner, text="Google sesi", text_color=self.palette["muted"], anchor="w"
        ).pack(fill="x")
        current_gvoice = self.current.get(
            "google_tts_voice", app_settings.DEFAULT_GOOGLE_TTS_VOICE
        )
        self.govoice_var = ctk.StringVar(value=_google_voice_label_for(current_gvoice))
        ctk.CTkOptionMenu(
            inner,
            variable=self.govoice_var,
            values=app_settings.GOOGLE_TTS_VOICES,
            fg_color=self.palette["input_bg"],
            button_color=self.palette["accent"],
            button_hover_color=self.palette["accent_hover"],
        ).pack(anchor="w", pady=(4, 10))

        self.rate_label = ctk.CTkLabel(
            inner,
            text=f"Konuşma hızı: {float(self.current.get('tts_speaking_rate', 0.92)):.2f} (JARVIS: 0.92)",
            text_color=self.palette["muted"],
            anchor="w",
        )
        self.rate_label.pack(fill="x")
        self.rate_slider = ctk.CTkSlider(
            inner,
            from_=0.7,
            to=1.4,
            number_of_steps=14,
            command=self._on_rate,
            progress_color=self.palette["accent"],
        )
        self.rate_slider.set(float(self.current.get("tts_speaking_rate", 0.92)))
        self.rate_slider.pack(fill="x", pady=(4, 10))

        self.pitch_label = ctk.CTkLabel(
            inner,
            text=f"Ses perdesi (peslik): {float(self.current.get('google_tts_pitch', -3.0)):.1f} (JARVIS: -3.0)",
            text_color=self.palette["muted"],
            anchor="w",
        )
        self.pitch_label.pack(fill="x")
        self.pitch_slider = ctk.CTkSlider(
            inner,
            from_=-10.0,
            to=5.0,
            number_of_steps=30,
            command=self._on_pitch,
            progress_color=self.palette["accent"],
        )
        self.pitch_slider.set(float(self.current.get("google_tts_pitch", -3.0)))
        self.pitch_slider.pack(fill="x", pady=(4, 4))
        ctk.CTkLabel(
            inner,
            text="Perde ne kadar negatifse ses o kadar pes/tok olur.",
            text_color=self.palette["muted"],
            anchor="w",
            justify="left",
            wraplength=470,
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
        ).pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(
            inner, text="Yedek ses (Edge)", text_color=self.palette["muted"], anchor="w"
        ).pack(fill="x")
        current_voice = self.current.get("tts_voice", app_settings.DEFAULT_TTS_VOICE)
        # Etiket listesinde arama; yoksa ilk (kalın erkek) ses.
        self.voice_var = ctk.StringVar(value=_voice_label_for(current_voice))
        ctk.CTkOptionMenu(
            inner,
            variable=self.voice_var,
            values=app_settings.TTS_VOICES,
            fg_color=self.palette["input_bg"],
            button_color=self.palette["accent"],
            button_hover_color=self.palette["accent_hover"],
        ).pack(anchor="w", pady=(4, 4))

        self.web_var = ctk.BooleanVar(value=bool(self.current.get("web_search_enabled", True)))
        self.file_var = ctk.BooleanVar(value=bool(self.current.get("file_tools_enabled", True)))
        ctk.CTkSwitch(
            inner,
            text="Web'de arama aracı",
            variable=self.web_var,
            text_color=self.palette["text"],
            progress_color=self.palette["accent"],
        ).pack(anchor="w", pady=4)
        ctk.CTkSwitch(
            inner,
            text="Dosya okuma/yazma araçları",
            variable=self.file_var,
            text_color=self.palette["text"],
            progress_color=self.palette["accent"],
        ).pack(anchor="w", pady=4)

        ctk.CTkLabel(
            inner,
            text="Sistem talimatı (asistanın kişiliği)",
            text_color=self.palette["muted"],
            anchor="w",
        ).pack(fill="x", pady=(12, 4))
        self.prompt_box = ctk.CTkTextbox(
            inner,
            height=110,
            fg_color=self.palette["input_bg"],
            border_color=self.palette["border"],
            border_width=1,
            wrap="word",
        )
        self.prompt_box.pack(fill="x")
        self.prompt_box.insert(
            "1.0",
            self.current.get("system_prompt") or _default_prompt_text(),
        )

        ctk.CTkLabel(
            inner, text="Tema", text_color=self.palette["muted"], anchor="w"
        ).pack(fill="x", pady=(12, 4))
        self.theme_var = ctk.StringVar(value=self.current.get("ui_theme", "dark"))
        ctk.CTkOptionMenu(
            inner,
            variable=self.theme_var,
            values=["dark", "light"],
            fg_color=self.palette["surface_alt"],
            button_color=self.palette["accent"],
            button_hover_color=self.palette["accent_hover"],
        ).pack(anchor="w")

    def _build_workspace_section(self, parent) -> None:
        frame = self._section(parent, "Çalışma Klasörü")
        inner = ctk.CTkFrame(frame, fg_color="transparent")
        inner.pack(fill="x", padx=14, pady=12)
        ctk.CTkLabel(
            inner,
            text="Ajanın dosya araçları yalnızca bu klasörde çalışır:",
            text_color=self.palette["muted"],
            anchor="w",
            wraplength=460,
            justify="left",
        ).pack(fill="x")
        path_text = str(storage.workspace_path())
        ctk.CTkLabel(
            inner,
            text=path_text,
            text_color=self.palette["text"],
            anchor="w",
            wraplength=460,
            justify="left",
            font=ctk.CTkFont(family="Consolas", size=11),
        ).pack(fill="x", pady=(4, 8))
        ctk.CTkButton(
            inner,
            text="Klasörü aç",
            width=110,
            fg_color=self.palette["surface_alt"],
            hover_color=self.palette["border"],
            command=lambda: self._open_path(path_text),
        ).pack(anchor="w")

    # ------------------------------------------------------------------
    def _on_temp(self, value: float) -> None:
        self.temp_label.configure(text=f"Yaratıcılık (temperature): {value:.1f}")

    def _on_rate(self, value: float) -> None:
        self.rate_label.configure(text=f"Konuşma hızı: {value:.2f} (JARVIS: 0.92)")

    def _on_pitch(self, value: float) -> None:
        self.pitch_label.configure(
            text=f"Ses perdesi (peslik): {value:.1f} (JARVIS: -3.0)"
        )

    def _open_google_console(self) -> None:
        import webbrowser

        webbrowser.open(
            "https://console.cloud.google.com/apis/library/texttospeech.googleapis.com"
        )

    def _open_path(self, path: str) -> None:
        try:
            if sys.platform == "win32":
                os.startfile(path)  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.Popen(["open", path])
            else:
                subprocess.Popen(["xdg-open", path])
        except Exception:
            pass

    def _save(self) -> None:
        result = dict(self.current)
        # Alan boş bırakılırsa mevcut anahtar korunur; aksi hâlde yenisi yazılır.
        new_key = self.key_var.get().strip()
        if new_key:
            result["api_key"] = new_key
        elif not result.get("api_key"):
            result["api_key"] = ""
        result["model"] = self.model_var.get().strip() or app_settings.DEFAULT_MODEL
        result["temperature"] = round(float(self.temp_slider.get()), 1)
        try:
            result["max_output_tokens"] = max(
                256, int(float(self.tokens_var.get()))
            )
        except (TypeError, ValueError):
            result["max_output_tokens"] = app_settings.DEFAULT_MAX_OUTPUT_TOKENS
        result["assistant_name"] = self.name_var.get().strip() or "Dragon"
        # Google anahtarı: boş bırakılırsa kayıtlı anahtar korunur.
        new_gkey = self.gkey_var.get().strip()
        if new_gkey:
            result["google_tts_key"] = new_gkey
        elif not result.get("google_tts_key"):
            result["google_tts_key"] = ""
        result["tts_backend"] = "google" if self.backend_var.get() else "edge"
        result["google_tts_voice"] = app_settings.GOOGLE_TTS_VOICE_IDS.get(
            self.govoice_var.get(), app_settings.DEFAULT_GOOGLE_TTS_VOICE
        )
        result["tts_speaking_rate"] = round(float(self.rate_slider.get()), 2)
        result["google_tts_pitch"] = round(float(self.pitch_slider.get()), 1)
        result["tts_pitch"] = app_settings.DEFAULT_TTS_PITCH
        result["tts_voice"] = app_settings.TTS_VOICE_IDS.get(
            self.voice_var.get(), app_settings.DEFAULT_TTS_VOICE
        )
        result["web_search_enabled"] = bool(self.web_var.get())
        result["file_tools_enabled"] = bool(self.file_var.get())
        prompt = self.prompt_box.get("1.0", "end").strip()
        result["system_prompt"] = "" if prompt == _default_prompt_text().strip() else prompt
        result["ui_theme"] = self.theme_var.get()

        self.on_save(result)
        self.destroy()

    def _center(self, master) -> None:
        self.update_idletasks()
        try:
            master.update_idletasks()
            x = master.winfo_rootx() + (master.winfo_width() - 560) // 2
            y = master.winfo_rooty() + (master.winfo_height() - 680) // 2
            self.geometry(f"+{max(0, x)}+{max(0, y)}")
        except Exception:
            pass


def _default_prompt_text() -> str:
    from core.prompts import SYSTEM_PROMPT

    return SYSTEM_PROMPT


def _voice_label_for(voice_id: str) -> str:
    """Ses kimliğine karşılık gelen ayarlar penceresi etiketini bulur."""
    for label, voice in app_settings.TTS_VOICE_IDS.items():
        if voice == voice_id:
            return label
    return app_settings.TTS_VOICES[0]


def _google_voice_label_for(voice_id: str) -> str:
    """Google ses kimliğine karşılık gelen etiketi bulur."""
    for label, voice in app_settings.GOOGLE_TTS_VOICE_IDS.items():
        if voice == voice_id:
            return label
    return app_settings.GOOGLE_TTS_VOICES[0]
