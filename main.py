"""Dragon — masaüstü yapay zeka asistanı. Giriş noktası.

Bu dosya çalıştırıldığında (veya paketlenmiş exe açıldığında) arayüz başlar.
"""

from __future__ import annotations

import sys
import traceback


def main() -> int:
    try:
        from ui.app import run
    except Exception:  # bağımlılık eksikse anlaşılır mesaj ver
        traceback.print_exc()
        _show_startup_error()
        return 1

    try:
        run()
    except Exception:
        traceback.print_exc()
        _show_startup_error()
        return 1
    return 0


def _show_startup_error() -> None:
    """Arayüz açılamadığında kullanıcıya bilgi verir (konsol yoksa)."""
    message = (
        "Dragon başlatılamadı.\n\n"
        "Gerekli paketler eksik olabilir. Kurmak için:\n"
        "    pip install -r requirements.txt\n\n"
        "Ayrıntılar için konsol çıktısına bakın."
    )
    try:
        import tkinter as tk
        from tkinter import messagebox

        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("Dragon", message)
        root.destroy()
    except Exception:
        print(message, file=sys.stderr)


if __name__ == "__main__":
    raise SystemExit(main())
