"""Arayüzün renk paleti ve tipografi sabitleri.

Tema: düz (flat), koyu siyah zemin + neon mavi/mor/pembe vurgular.
"""

from __future__ import annotations

_DARK = {
    # Zeminler
    "window": "#04060d",
    "bg_alt": "#060a14",
    "sidebar": "#060a14",
    "surface": "#0a1120",
    "surface_alt": "#111a30",
    "panel": "#0a1120",
    # Sohbet balonları (gelecekte tekrar kullanılırsa)
    "assistant_bubble": "#0d1526",
    "user_bubble": "#1e5cff",
    "user_text": "#ffffff",
    # Vurgular
    "accent": "#2f7bff",
    "accent_hover": "#1d5ff0",
    "accent2": "#8b5cf6",
    "pink": "#ff5fa2",
    "ring_idle": "#2f7bff",
    "ring_a": "#4facfe",
    "ring_b": "#8b5cf6",
    # Metin
    "text": "#e8f1ff",
    "muted": "#6f86ad",
    "title": "#dceaff",
    "border": "#1e3a6e",
    "input_bg": "#0a1120",
    # Durum
    "danger": "#ff4d6d",
    "success": "#2fd07a",
    # Kod
    "code_bg": "#060b16",
    "code_text": "#7dd3fc",
}

_LIGHT = {
    "window": "#f4f7ff",
    "bg_alt": "#edf2ff",
    "sidebar": "#edf2ff",
    "surface": "#ffffff",
    "surface_alt": "#e5ecff",
    "panel": "#ffffff",
    "assistant_bubble": "#ffffff",
    "user_bubble": "#1e5cff",
    "user_text": "#ffffff",
    "accent": "#2563eb",
    "accent_hover": "#1d4ed8",
    "accent2": "#7c3aed",
    "pink": "#ec4899",
    "ring_idle": "#2563eb",
    "ring_a": "#3b82f6",
    "ring_b": "#8b5cf6",
    "text": "#0f172a",
    "muted": "#64748b",
    "title": "#0f172a",
    "border": "#c7d6f7",
    "input_bg": "#ffffff",
    "danger": "#dc2626",
    "success": "#16a34a",
    "code_bg": "#f1f5f9",
    "code_text": "#0f766e",
}

FONT_FAMILY = "Segoe UI"
MONO_FAMILY = "Consolas"


def get_palette(mode: str = "dark") -> dict[str, str]:
    """Verilen tema moduna göre renk sözlüğünü döndürür."""
    return _LIGHT.copy() if str(mode).lower() == "light" else _DARK.copy()