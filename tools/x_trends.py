"""
X (Twitter) Türkiye trendleri çekici - Dragon entegrasyonu
Diğer projeden uyarlanmıştır (trends24.in)
"""

from __future__ import annotations

import re
import threading
import time
import urllib.parse
from typing import Any

import requests


REQUEST_TIMEOUT = 12
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.8",
}

COUNTRY = "turkey"
_CACHE: dict[str, tuple[float, list[dict[str, Any]]]] = {}
_CACHE_TTL = 300.0
_lock = threading.Lock()

_OL_RE = re.compile(r"<ol class=trend-card__list>(.*?)</ol>", re.S)
_LI_RE = re.compile(r"<li[^>]*>(.*?)</li>", re.S)
_NAME_RE = re.compile(r"class=trend-link>(.*?)</a>", re.S)
_HREF_RE = re.compile(r'href="([^"]+)"')
_COUNT_RE = re.compile(r"class=tweet-count[^>]*>(.*?)</span>", re.S)
_TAG_RE = re.compile(r"<[^>]+>")


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", _TAG_RE.sub("", text or "")).strip()


def _parse_count(raw: str) -> int | None:
    raw = _clean(raw)
    if not raw:
        return None
    m = re.match(r"([\d.,]+)\s*([KMB]?)", raw, re.IGNORECASE)
    if not m:
        return None
    try:
        value = float(m.group(1).replace(".", "").replace(",", "."))
    except ValueError:
        return None
    factor = {"k": 1_000, "m": 1_000_000, "b": 1_000_000_000}.get(m.group(2).lower(), 1)
    return int(value * factor)


def _format_count(value: int | None) -> str:
    if not value:
        return ""
    if value >= 1_000_000:
        return f"{value / 1_000_000:.1f}M".replace(".0M", "M")
    if value >= 1_000:
        return f"{value / 1_000:.1f}K".replace(".0K", "K")
    return str(value)


def _parse(html: str, limit: int) -> list[dict[str, Any]]:
    match = _OL_RE.search(html)
    if not match:
        return []

    items: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw in _LI_RE.findall(match.group(1)):
        name_match = _NAME_RE.search(raw)
        if not name_match:
            continue
        tag = _clean(name_match.group(1))
        if not tag or tag.lower() in seen:
            continue
        seen.add(tag.lower())

        href_match = _HREF_RE.search(raw)
        link = href_match.group(1) if href_match else ""

        count_match = _COUNT_RE.search(raw)
        count = _parse_count(count_match.group(1)) if count_match else None

        items.append({
            "tag": tag,
            "rank": len(items) + 1,
            "count": count,
            "count_text": _format_count(count),
            "link": link,
            "is_tag": tag.startswith("#"),
        })
        if len(items) >= 60:
            break

    hashtags = [i for i in items if i["is_tag"]]
    others = [i for i in items if not i["is_tag"]]
    merged = hashtags + others
    for i, item in enumerate(merged):
        item["rank"] = i + 1
    return merged[:max(1, limit)]


def get_trending_topics(limit: int = 8, force: bool = False) -> list[dict[str, Any]]:
    slug = COUNTRY
    now = time.time()
    if not force:
        with _lock:
            hit = _CACHE.get(slug)
        if hit and now - hit[0] < _CACHE_TTL:
            return list(hit[1])[:limit]

    url = f"https://trends24.in/{slug}/"
    try:
        response = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        response.encoding = "utf-8"
        parsed = _parse(response.text, limit)
    except Exception:
        with _lock:
            hit = _CACHE.get(slug)
        if hit:
            return list(hit[1])[:limit]
        return []

    if parsed:
        with _lock:
            _CACHE[slug] = (now, list(parsed))
    return parsed


def search_url(tag: str) -> str:
    return "https://x.com/search?q=" + urllib.parse.quote(tag)
