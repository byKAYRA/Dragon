"""Bilgisayar kontrol araçları: uygulama açma, site, hava durumu, ses, komut.

Güvenlik: `run_shell_command` risklidir ve `registry` tarafından
"onay gerektirir" olarak işaretlenir; ajan bu aracı ancak kullanıcının
onayından sonra çalıştırır. Diğer araçlar doğrudan çalışabilir.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import urllib.parse
import urllib.request
import webbrowser
from pathlib import Path
from typing import Any

MAX_OUTPUT_CHARS = 2500


class ToolError(Exception):
    """Kullanıcıya gösterilebilir sistem aracı hatası."""


# ---------------------------------------------------------------------------
# Uygulama bilinen adı -> komut eşlemesi
# ---------------------------------------------------------------------------
APP_ALIASES: dict[str, str] = {
    "notepad": "notepad.exe",
    "not defteri": "notepad.exe",
    "hesap makinesi": "calc.exe",
    "calculator": "calc.exe",
    "paint": "mspaint.exe",
    "boya": "mspaint.exe",
    "dosya gezgini": "explorer.exe",
    "explorer": "explorer.exe",
    "chrome": "chrome",
    "google chrome": "chrome",
    "tarayıcı": "chrome",
    "internet tarayıcı": "edge",
    "edge": "msedge",
    "microsoft edge": "msedge",
    "spotify": "spotify",
    "discord": "discord",
    "steam": "steam",
    "visual studio code": "code",
    "vscode": "code",
    "kod editörü": "code",
    "komut istemi": "cmd",
    "cmd": "cmd",
    "terminal": "wt",
    "powershell": "powershell",
    "müzik": "spotify",
    "youtube": "https://www.youtube.com",
}

_START_MENU_DIRS: list[Path] = []
_appdata = os.environ.get("APPDATA", "")
if _appdata:
    _START_MENU_DIRS.append(Path(_appdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs")
_START_MENU_DIRS.append(Path("C:/ProgramData/Microsoft/Windows/Start Menu/Programs"))


def _find_application(name: str) -> str | None:
    """Bir uygulamayı PATH veya Başlat Menüsü kısayollarında arar."""
    target = APP_ALIASES.get(name.strip().lower(), name.strip())

    # Site macerası: alias bir URL ise direkt onu döndür.
    if target.startswith("http"):
        return target

    # 1) PATH içinde exe.
    exe = shutil.which(target) or shutil.which(target + ".exe")
    if exe:
        return exe

    # 2) Başlat Menüsü kısayollarını tara.
    lowered = name.strip().lower()
    for base in _START_MENU_DIRS:
        if not base.exists():
            continue
        try:
            for entry in base.rglob("*"):
                if not entry.is_file():
                    continue
                if entry.suffix.lower() not in (".lnk", ".url", ".exe"):
                    continue
                if lowered in entry.stem.lower():
                    return str(entry)
        except OSError:
            continue
    return None


# ---------------------------------------------------------------------------
# Araçlar
# ---------------------------------------------------------------------------
def open_application(app_name: str) -> str:
    """Bilgisayardaki bir uygulamayı açar.

    Args:
        app_name: Uygulamanın bilinen adı (ör. "notepad", "chrome", "spotify").

    Returns:
        İşlem sonucunu bildiren metin.
    """
    target = _find_application(app_name)
    if target is None:
        raise ToolError(f"'{app_name}' adında bir uygulama bulunamadı.")

    try:
        if target.startswith("http"):
            webbrowser.open(target)
        elif target.lower().endswith((".lnk", ".url")):
            os.startfile(target)  # type: ignore[attr-defined]
        else:
            subprocess.Popen([target], close_fds=True)
    except Exception as exc:
        raise ToolError(f"Uygulama açılamadı: {exc}") from exc

    return f"'{app_name}' açılıyor."


def open_website(url: str) -> str:
    """Varsayılan tarayıcıda bir web sitesini açar.

    Args:
        url: Açılacak adres (örn. "github.com"). Şema yoksa https eklenir.

    Returns:
        İşlem sonucunu bildiren metin.
    """
    url = (url or "").strip()
    if not url:
        raise ToolError("Site adresi boş olamaz.")
    if " " in url or "." not in url:
        raise ToolError(f"'{url}' geçerli bir adrese benzemiyor.")
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    try:
        webbrowser.open(url)
    except Exception as exc:
        raise ToolError(f"Site açılamadı: {exc}") from exc
    return f"{url} tarayıcıda açılıyor."


def get_weather(city: str = "İstanbul") -> str:
    """Bir şehrin güncel hava durumunu wttr.in'den alır.

    Args:
        city: Şehir adı (varsayılan İstanbul).

    Returns:
        Sıcaklık, durum, nem, rüzgar bilgisini içeren metin.
    """
    city = (city or "").strip() or "İstanbul"
    try:
        query = urllib.parse.quote(city)
        url = f"https://wttr.in/{query}?format=j1&lang=tr"
        with urllib.request.urlopen(url, timeout=10) as response:
            data: dict[str, Any] = json.loads(response.read().decode("utf-8"))
        current = data["current_condition"][0]
    except Exception as exc:
        raise ToolError(f"Hava durumu alınamadı: {exc}") from exc

    description = _weather_desc(current)
    temp = current.get("temp_C", "?")
    humidity = current.get("humidity", "?")
    wind = current.get("windspeedKmph", "?")
    return (
        f"{city} için güncel hava durumu: {description}, "
        f"Sıcaklık: {temp}°C, Nem: {humidity}%, Rüzgar: {wind} km/s."
    )


def _weather_desc(current: dict[str, Any]) -> str:
    for key in ("lang_tr", "weatherDesc"):
        items = current.get(key)
        if isinstance(items, list) and items:
            value = items[0].get("value")
            if value:
                return value
    return current.get("weatherDesc", "?")


def set_volume(level: int) -> str:
    """Sistem ses seviyesini ayarlar (0-100).

    Args:
        level: 0-100 arası hedef ses seviyesi.

    Returns:
        Yeni ses seviyesini bildiren metin.
    """
    try:
        level = max(0, min(100, int(level)))
    except (TypeError, ValueError):
        raise ToolError("Ses seviyesi 0-100 arasında bir sayı olmalı.")

    try:
        _set_volume_pycaw(level)
    except Exception:
        try:
            _set_volume_keys(level)
        except Exception as exc:
            raise ToolError(f"Ses seviyesi ayarlanamadı: {exc}") from exc
    return f"Ses seviyesi %{level} olarak ayarlandı."


def _set_volume_pycaw(level: int) -> None:
    from pycaw.pycaw import AudioUtilities  # ağır import, yalnızca gerektiğinde

    speakers = AudioUtilities.GetSpeakers()
    speakers.volume_percent = float(level)


def _set_volume_keys(level: int) -> None:
    """pycaw yoksa ses tuşlarıyla yaklaşık ayar (geri düşüş)."""
    import ctypes

    VK_VOLUME_DOWN = 0xAE
    VK_VOLUME_UP = 0xAF
    user32 = ctypes.windll.user32
    # %10 mertebesinde tahmini adım (kesin değildir).
    steps = 4 if level >= 50 else 3
    for _ in range(steps):
        user32.keybd_event(VK_VOLUME_UP, 0, 0, 0)
        user32.keybd_event(VK_VOLUME_UP, 0, 2, 0)


def run_shell_command(command: str) -> str:
    """Bir kabuk komutunu çalıştırır (yalnızca kullanıcı onayıyla).

    Args:
        command: Çalıştırılacak komut.

    Returns:
        Komutun çıktısı (çıktı/büyükse kısaltılır).
    """
    command = (command or "").strip()
    if not command:
        raise ToolError("Komut boş olamaz.")

    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            errors="replace",
            timeout=30,
        )
    except subprocess.TimeoutExpired:
        return "Komut 30 saniye içinde bitmedi ve durduruldu."
    except Exception as exc:
        raise ToolError(f"Komut çalıştırılamadı: {exc}") from exc

    output = (result.stdout or "") + (("\n" + result.stderr) if result.stderr else "")
    output = output.strip() or "(çıktı yok)"
    if len(output) > MAX_OUTPUT_CHARS:
        output = output[:MAX_OUTPUT_CHARS] + "\n… (çıktı kısaltıldı)"
    return f"Çıkış kodu: {result.returncode}\n{output}"