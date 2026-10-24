"""Sohbet ekranı bileşenleri: mesaj balonları ve yazıyor göstergesi."""

from __future__ import annotations

import re
from typing import Callable

import customtkinter as ctk
from PIL import Image

from ui.theme import FONT_FAMILY, MONO_FAMILY

# ```dil ... ``` bloklarını yakalar.
_CODE_FENCE = re.compile(r"```([^\n`]*)\n?(.*?)```", re.DOTALL)

MAX_IMAGE_WIDTH = 260


def split_segments(text: str) -> list[tuple]:
    """Metni ('text', içerik) ve ('code', içerik, dil) parçalarına ayırır."""
    text = text or ""
    segments: list[tuple] = []
    position = 0
    for match in _CODE_FENCE.finditer(text):
        if match.start() > position:
            segments.append(("text", text[position : match.start()]))
        lang = (match.group(1) or "").strip()
        segments.append(("code", match.group(2).rstrip("\n"), lang))
        position = match.end()
    if position < len(text):
        segments.append(("text", text[position:]))
    if not segments:
        segments.append(("text", text))
    return segments


class MessageBubble(ctk.CTkFrame):
    """Tek bir sohbet mesajını gösteren balon."""

    def __init__(
        self,
        master,
        *,
        role: str,
        text: str,
        palette: dict[str, str],
        assistant_name: str = "Dragon",
        image_paths: list[str] | None = None,
        on_copy: Callable[[str], None] | None = None,
    ) -> None:
        super().__init__(master, fg_color="transparent")
        self.columnconfigure(0, weight=1)

        self.role = role
        self.raw_text = text or ""
        self.palette = palette
        self._text_labels: list[ctk.CTkLabel] = []
        self._images: list[ctk.CTkImage] = []

        is_user = role == "user"
        bubble_color = palette["user_bubble"] if is_user else palette["assistant_bubble"]
        text_color = palette["user_text"] if is_user else palette["text"]

        bubble = ctk.CTkFrame(
            self,
            fg_color=bubble_color,
            corner_radius=14,
            border_width=0 if is_user else 1,
            border_color=palette["border"],
        )
        bubble.grid(row=0, column=0, sticky="e" if is_user else "w")

        header = ctk.CTkLabel(
            bubble,
            text=("Sen" if is_user else assistant_name),
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            text_color=palette["user_text"] if is_user else palette["accent"],
            anchor="w",
        )
        header.pack(anchor="w", padx=14, pady=(10, 0))

        for image_path in image_paths or []:
            self._add_image(bubble, image_path)

        self._add_body(bubble, text_color)

        footer = ctk.CTkFrame(bubble, fg_color="transparent")
        footer.pack(fill="x", padx=10, pady=(0, 6))
        copy_btn = ctk.CTkButton(
            footer,
            text="Kopyala",
            width=60,
            height=22,
            font=ctk.CTkFont(family=FONT_FAMILY, size=10),
            fg_color="transparent",
            hover_color=palette["surface_alt"],
            text_color=palette["user_text"] if is_user else palette["muted"],
            command=self._copy,
        )
        copy_btn.pack(side="right")
        self._on_copy = on_copy

    # ------------------------------------------------------------------
    def _add_image(self, parent, image_path: str) -> None:
        try:
            image = Image.open(image_path)
            image.thumbnail((MAX_IMAGE_WIDTH, MAX_IMAGE_WIDTH * 2))
            ctk_image = ctk.CTkImage(
                light_image=image, dark_image=image, size=image.size
            )
        except Exception:
            return
        self._images.append(ctk_image)
        label = ctk.CTkLabel(parent, image=ctk_image, text="")
        label.pack(anchor="w", padx=14, pady=(8, 0))

    def _add_body(self, parent, text_color: str) -> None:
        for segment in split_segments(self.raw_text):
            if segment[0] == "code":
                self._add_code_block(parent, segment[1], segment[2])
            else:
                content = segment[1].strip("\n")
                if not content.strip():
                    continue
                label = ctk.CTkLabel(
                    parent,
                    text=content,
                    justify="left",
                    anchor="w",
                    font=ctk.CTkFont(family=FONT_FAMILY, size=13),
                    text_color=text_color,
                    wraplength=560,
                )
                label.pack(anchor="w", padx=14, pady=(6, 0))
                self._text_labels.append(label)

    def _add_code_block(self, parent, code: str, lang: str) -> None:
        wrapper = ctk.CTkFrame(
            parent,
            fg_color=self.palette["code_bg"],
            corner_radius=8,
        )
        wrapper.pack(fill="x", padx=14, pady=(8, 4))
        if lang:
            tag = ctk.CTkLabel(
                wrapper,
                text=lang,
                font=ctk.CTkFont(family=FONT_FAMILY, size=10),
                text_color=self.palette["muted"],
                anchor="w",
            )
            tag.pack(anchor="w", padx=10, pady=(6, 0))
        code_label = ctk.CTkLabel(
            wrapper,
            text=code or " ",
            justify="left",
            anchor="w",
            font=ctk.CTkFont(family=MONO_FAMILY, size=12),
            text_color=self.palette["code_text"],
            wraplength=540,
        )
        code_label.pack(anchor="w", padx=10, pady=(4, 10))
        self._text_labels.append(code_label)

    # ------------------------------------------------------------------
    def set_wrap(self, width: int) -> None:
        """Yeniden boyutlandırmada metin sarma genişliğini günceller."""
        safe = max(240, width)
        for label in self._text_labels:
            label.configure(wraplength=safe)

    def _copy(self) -> None:
        if self._on_copy is not None:
            self._on_copy(self.raw_text)


class TypingBubble(ctk.CTkFrame):
    """Asistan yanıt hazırlarken gösterilen 'yazıyor' balonu."""

    def __init__(self, master, *, palette: dict[str, str], assistant_name: str) -> None:
        super().__init__(master, fg_color="transparent")
        self.columnconfigure(0, weight=1)
        self._palette = palette

        bubble = ctk.CTkFrame(
            self,
            fg_color=palette["assistant_bubble"],
            corner_radius=14,
            border_width=1,
            border_color=palette["border"],
        )
        bubble.grid(row=0, column=0, sticky="w")
        self._label = ctk.CTkLabel(
            bubble,
            text=f"{assistant_name} yazıyor",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13),
            text_color=palette["muted"],
            anchor="w",
        )
        self._label.pack(padx=16, pady=10)
        self._dots = 0
        self._running = True
        self._animate()

    def set_status(self, message: str) -> None:
        """Durum metnini günceller (ör. 'Web'de aranıyor…')."""
        self._status = message
        base = message.rstrip("….").strip()
        self._label.configure(text=base)

    def _animate(self) -> None:
        if not self._running:
            return
        if not hasattr(self, "_status") or not self._status:
            self._dots = (self._dots + 1) % 4
            self._label.configure(text="Yazıyor" + "." * self._dots)
        self.after(320, self._animate)

    def stop(self) -> None:
        self._running = False
