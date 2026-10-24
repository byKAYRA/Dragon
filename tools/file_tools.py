"""Ajanın kullanabileceği güvenli dosya araçları.

Tüm dosya işlemleri `core.storage.workspace_path()` ile belirlenen güvenli
klasörle sınırlıdır. Bu sayede paketlenmiş uygulamayı kullanan biri, ajanın
kendi sistemindeki rastgele dosyalara erişmesini engeller.
"""

from __future__ import annotations

from pathlib import Path

from core import storage

# Tek seferde okunacak/yazılacak azami içerik uzunluğu (karakter).
MAX_READ_CHARS = 40_000
MAX_WRITE_CHARS = 200_000


class ToolError(Exception):
    """Araç çalıştırılırken oluşan, kullanıcıya gösterilebilir hata."""


def _resolve(path: str) -> Path:
    """Kullanıcı yolunu güvenli çalışma klasörüne göre çözer.

    Çalışma klasörünün dışına çıkan yolları reddeder.
    """
    root = storage.workspace_path().resolve()
    raw = (path or "").strip().strip('"').strip("'")
    if not raw:
        raise ToolError("Dosya yolu boş olamaz.")

    candidate = Path(raw)
    if not candidate.is_absolute():
        candidate = root / candidate
    candidate = candidate.resolve()

    if candidate != root and root not in candidate.parents:
        raise ToolError(
            "Güvenlik nedeniyle yalnızca çalışma klasörü içindeki dosyalara "
            f"erişilebilir: {root}"
        )
    return candidate


def read_file(path: str) -> str:
    """Çalışma klasöründeki bir metin dosyasını okur.

    Args:
        path: Çalışma klasörüne göreli (veya mutlak) dosya yolu.

    Returns:
        Dosyanın içeriği, başına bir başlık eklenerek.
    """
    target = _resolve(path)
    if not target.exists():
        raise ToolError(f"Dosya bulunamadı: {path}")
    if target.is_dir():
        raise ToolError(f"{path} bir klasör; dosya değil.")

    try:
        text = target.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        raise ToolError(f"Dosya okunamadı: {exc}") from exc

    truncated = len(text) > MAX_READ_CHARS
    if truncated:
        text = text[:MAX_READ_CHARS]

    header = f"# Dosya: {target.name}\n"
    if truncated:
        header += f"(Not: dosya çok büyük, ilk {MAX_READ_CHARS} karakter gösteriliyor.)\n"
    return header + text


def write_file(path: str, content: str) -> str:
    """Çalışma klasörüne bir metin dosyası yazar (üzerine yazar/oluşturur).

    Args:
        path: Hedef dosya yolu (çalışma klasörüne göreli).
        content: Dosyaya yazılacak metin.

    Returns:
        İşlemin sonucunu bildiren kısa bir mesaj.
    """
    target = _resolve(path)
    content = "" if content is None else str(content)
    if len(content) > MAX_WRITE_CHARS:
        raise ToolError("Yazılacak içerik izin verilen boyutu aşıyor.")

    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    except OSError as exc:
        raise ToolError(f"Dosya yazılamadı: {exc}") from exc

    return f"{target.name} kaydedildi ({len(content)} karakter)."


def list_files(path: str = ".") -> str:
    """Çalışma klasöründeki dosya ve klasörleri listeler.

    Args:
        path: Listelenecek alt klasör (varsayılan: çalışma klasörünün kökü).

    Returns:
        Her satırda bir öğe olacak şekilde liste.
    """
    target = _resolve(path)
    if not target.exists():
        raise ToolError(f"Klasör bulunamadı: {path}")
    if not target.is_dir():
        raise ToolError(f"{path} bir klasör değil.")

    entries = sorted(
        target.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())
    )
    if not entries:
        return f"{target} klasörü boş."

    lines = [f"{target} içeriği:"]
    for entry in entries[:200]:
        marker = "[klasör]" if entry.is_dir() else "[dosya] "
        size = ""
        if entry.is_file():
            try:
                size = f" ({entry.stat().st_size} bayt)"
            except OSError:
                size = ""
        lines.append(f"  {marker} {entry.name}{size}")
    return "\n".join(lines)
