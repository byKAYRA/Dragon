"""Dragon'u tek dosyalık Windows uygulaması (exe) olarak derler.

Kullanım:
    python build.py

Sonuç:  dist/Dragon.exe  (çift tıklandığında arayüz açılır)

Not: exe'yi paylaştığın kişiler kendi Gemini API anahtarlarını ilk açılışta
Ayarlar penceresinden girer. Anahtar exe'nin içine gömülmez.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def main() -> int:
    # PyInstaller kurulu mu?
    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        print("PyInstaller bulunamadı. Kurmak için: pip install pyinstaller")
        return 1

    for folder in ("build", "dist"):
        target = ROOT / folder
        if target.exists():
            shutil.rmtree(target, ignore_errors=True)

    args = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--windowed",
        "--onefile",
        "--name",
        "Dragon",
        # Uygulama ikonu
        "--icon",
        str(ROOT / "assets" / "icon.ico"),
        # customtkinter, tema ve font dosyalarını pakete dahil et.
        "--collect-all",
        "customtkinter",
        "--collect-all",
        "ddgs",
        # google-genai modüllerini güvence altına al.
        "--collect-submodules",
        "google.genai",
        # Ses kütüphaneleri (pyaudio & pygame yerel eklentileri dahil).
        "--collect-binaries",
        "pyaudio",
        "--collect-binaries",
        "pygame",
        "--collect-all",
        "edge_tts",
        # Kalıntıları hariç tutarak boyutu küçült
        "--exclude-module",
        "librosa",
        "--exclude-module",
        "scipy",
        "--exclude-module",
        "scipy.signal",
        "--exclude-module",
        "scipy.fftpack",
        "--exclude-module",
        "scipy.interpolate",
        "--exclude-module",
        "matplotlib",
        "--exclude-module",
        "matplotlib.pyplot",
        "--exclude-module",
        "numba",
        "--exclude-module",
        "pandas",
        "--exclude-module",
        "sklearn",
        "--exclude-module",
        "skimage",
        "--exclude-module",
        "torchaudio",
        "--exclude-module",
        "torch",
        "--exclude-module",
        "torchvision",
        "--exclude-module",
        "transformers",
        # Ses seviyesi kontrolü (pycaw + comtypes) — set_volume aracı için.
        "--collect-all",
        "pycaw",
        "--collect-all",
        "comtypes",
        # Pillow'un Tk entegrasyonu.
        "--hidden-import",
        "PIL._tkinter_finder",
        # Temiz bir çalıştırma için ana dosya.
        str(ROOT / "main.py"),
    ]

    print("PyInstaller çalıştırılıyor...\n")
    result = subprocess.run(args, cwd=ROOT)
    if result.returncode != 0:
        print("\nDerleme başarısız oldu.")
        return result.returncode

    exe = ROOT / "dist" / "Dragon.exe"
    print(f"\nTamamlandı: {exe}")
    print("Bu dosyayı paylaşabilirsin.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
