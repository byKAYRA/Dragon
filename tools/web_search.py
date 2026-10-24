"""Web arama aracı (DuckDuckGo üzerinden, API anahtarı gerektirmez)."""

from __future__ import annotations

from typing import Any

# ddgs paketi zaman zaman ağ hataları fırlatabilir; çağıran taraf yakalar.
try:  # pragma: no cover - import ortamlara göre farklılık gösterebilir
    from ddgs import DDGS
except ImportError:
    try:
        from duckduckgo_search import DDGS  # type: ignore
    except ImportError:
        DDGS = None  # type: ignore


def web_search(query: str, max_results: int = 5) -> str:
    """DuckDuckGo üzerinden arama yapar ve okunabilir bir metin döndürür.

    Args:
        query: Aranacak ifade.
        max_results: Döndürülecek maksimum sonuç sayısı (1-10).

    Returns:
        Başlık, bağlantı ve özet içeren biçimlendirilmiş metin. Sonuç yoksa
        bunu belirten bir mesaj döner.
    """
    if DDGS is None:
        return "Web arama modülü (ddgs) kurulu değil. Kurmak için: pip install ddgs"

    query = (query or "").strip()
    if not query:
        return "Arama sorgusu boş olamaz."

    try:
        max_results = max(1, min(int(max_results), 10))
    except (TypeError, ValueError):
        max_results = 5

    try:
        with DDGS() as ddgs:
            results: list[dict[str, Any]] = list(
                ddgs.text(query, max_results=max_results)
            )
    except Exception as exc:  # ağ / zaman aşımı / ayrıştırma hataları
        return f"Web araması başarısız oldu: {exc}"

    if not results:
        return f"'{query}' için sonuç bulunamadı."

    lines: list[str] = [f"'{query}' için web arama sonuçları:"]
    for index, item in enumerate(results, start=1):
        title = (item.get("title") or "Başlıksız").strip()
        href = (item.get("href") or item.get("url") or "").strip()
        body = (item.get("body") or item.get("snippet") or "").strip()
        lines.append(f"\n[{index}] {title}\n{href}\n{body}")
    return "\n".join(lines)
