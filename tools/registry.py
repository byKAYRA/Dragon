"""Araçların kaydı, şema tanımları ve çalıştırıcısı.

`DragonAgent` bu modüldeki tanımları modele bildirir ve model bir araç
çağırdığında `run_tool` üzerinden çalıştırır.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Callable

try:
    from google.genai import types
except ImportError:
    types = None  # type: ignore

from tools import file_tools, system_tools, web_search, x_trends


def _format_trends(limit: int = 8) -> str:
    """X trendlerini model için okunabilir metne dönüştürür."""
    topics = x_trends.get_trending_topics(limit=limit)
    if not topics:
        return "Şu anda Türkiye X (Twitter) trend verileri alınamadı."
    lines = ["Türkiye X (Twitter) Gündem Trendleri:"]
    for item in topics:
        count = f" ({item['count_text']})" if item.get("count_text") else ""
        lines.append(f"{item['rank']}. {item['tag']}{count}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Araç tanımları
# ---------------------------------------------------------------------------

# Her araç: ad, açıklama, Gemini şeması, çalıştırılacak fonksiyon.
# `needs_approval: True` olan araçlar çalıştırılmadan önce kullanıcı onayı ister.
TOOL_SPECS: list[dict[str, Any]] = [
    {
        "name": "web_search",
        "description": (
            "Güncel bilgi, haber, fiyat veya doğrulanması gereken gerçekler için "
            "web'de arama yapar. Kullanıcı güncel bir konuyu sorduğunda kullan."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Aranacak anahtar kelimeler.",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Döndürülecek sonuç sayısı (1-10).",
                },
            },
            "required": ["query"],
        },
        "function": web_search.web_search,
    },
    {
        "name": "get_trending_topics",
        "description": (
            "Türkiye'de X (Twitter) üzerinde anlık en çok konuşulan trend "
            "başlıklarını (gündemi) döndürür. Kullanıcı 'gündemde ne var', "
            "'trendler neler' dediğinde kullan."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Döndürülecek trend sayısı (1-10, varsayılan 8).",
                }
            },
            "required": [],
        },
        "function": lambda limit=8: _format_trends(limit),
    },
    {
        "name": "read_file",
        "description": (
            "Çalışma klasöründeki bir metin dosyasını okur. Kullanıcı bir "
            "dosyadan bahsettiğinde ve içeriğini bilmiyorsan kullan."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Çalışma klasörüne göreli dosya yolu.",
                }
            },
            "required": ["path"],
        },
        "function": file_tools.read_file,
    },
    {
        "name": "write_file",
        "description": (
            "Çalışma klasörüne bir metin dosyası yazar veya var olanın üzerine "
            "yazar. Kullanıcı dosya oluşturmayı/düzenlemeyi istediğinde kullan."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Hedef dosya yolu (çalışma klasörüne göreli).",
                },
                "content": {
                    "type": "string",
                    "description": "Dosyaya yazılacak tam metin.",
                },
            },
            "required": ["path", "content"],
        },
        "function": file_tools.write_file,
    },
    {
        "name": "list_files",
        "description": "Çalışma klasöründeki dosya ve klasörleri listeler.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Listelenecek alt klasör (varsayılan '.').",
                }
            },
            "required": [],
        },
        "function": file_tools.list_files,
    },
    {
        "name": "get_current_datetime",
        "description": "Güncel tarih ve saati döndürür.",
        "parameters": {"type": "object", "properties": {}, "required": []},
        "function": lambda: datetime.now().strftime("%d.%m.%Y %H:%M (%A)"),
    },
    {
        "name": "open_application",
        "description": (
            "Kullanıcının bilgisayarındaki bir uygulamayı açar. Kullanıcı "
            "'not defterini aç', 'chrome'u başlat', 'spotify'ı çalıştır' gibi "
            "bir uygulama istediğinde kullan."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "app_name": {
                    "type": "string",
                    "description": "Açılacak uygulamanın adı.",
                }
            },
            "required": ["app_name"],
        },
        "function": system_tools.open_application,
    },
    {
        "name": "open_website",
        "description": (
            "Varsayılan tarayıcıda bir web sitesini açar. Kullanıcı bir "
            "adresi, web sitesini veya sayfasını açmak istediğinde kullan."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "Açılacak sitenin adresi (ör. 'github.com').",
                }
            },
            "required": ["url"],
        },
        "function": system_tools.open_website,
    },
    {
        "name": "get_weather",
        "description": "Bir şehrin güncel hava durumunu döndürür (sıcaklık, durum, nem, rüzgar).",
        "parameters": {
            "type": "object",
            "properties": {
                "city": {
                    "type": "string",
                    "description": "Şehir adı, varsayılan İstanbul.",
                }
            },
            "required": [],
        },
        "function": system_tools.get_weather,
    },
    {
        "name": "set_volume",
        "description": "Sistemin ana ses seviyesini 0-100 arasında ayarlar.",
        "parameters": {
            "type": "object",
            "properties": {
                "level": {
                    "type": "integer",
                    "description": "Hedef ses seviyesi (0-100).",
                }
            },
            "required": ["level"],
        },
        "function": system_tools.set_volume,
    },
    {
        "name": "run_shell_command",
        "description": (
            "Windows üzerinde bir kabuk komutu (veya program) çalıştırır. "
            "Yalnızca kullanıcının açıkça istediği komutlar için kullan; "
            "komut çalıştırılmadan önce kullanıcı onayı istenir."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "Çalıştırılacak komut metni.",
                }
            },
            "required": ["command"],
        },
        "function": system_tools.run_shell_command,
        "needs_approval": True,
    },
]

_SPEC_BY_NAME: dict[str, dict[str, Any]] = {spec["name"]: spec for spec in TOOL_SPECS}


def _enabled_specs(
    *, web_search_enabled: bool = True, file_tools_enabled: bool = True
) -> list[dict[str, Any]]:
    """Kullanıcı ayarlarına göre etkin araçları süzer."""
    file_tool_names = {"read_file", "write_file", "list_files"}
    enabled: list[dict[str, Any]] = []
    for spec in TOOL_SPECS:
        if spec["name"] == "web_search" and not web_search_enabled:
            continue
        if spec["name"] in file_tool_names and not file_tools_enabled:
            continue
        enabled.append(spec)
    return enabled


def build_gemini_tool(
    *, web_search_enabled: bool = True, file_tools_enabled: bool = True
) -> Any | None:
    """Etkin araçlardan modele verilecek `types.Tool` nesnesini üretir."""
    if types is None:
        return None

    specs = _enabled_specs(
        web_search_enabled=web_search_enabled,
        file_tools_enabled=file_tools_enabled,
    )
    if not specs:
        return None

    declarations = [
        types.FunctionDeclaration(
            name=spec["name"],
            description=spec["description"],
            parameters=spec["parameters"],
        )
        for spec in specs
    ]
    return types.Tool(function_declarations=declarations)


def tool_info(name: str) -> dict[str, Any] | None:
    """Bir aracın kaydını (spec) döndürür, yoksa None."""
    return _SPEC_BY_NAME.get(name)


def requires_approval(name: str) -> bool:
    """Bir aracın kullanıcı onayı gerektirip gerektirmediğini söyler."""
    spec = _SPEC_BY_NAME.get(name)
    return bool(spec and spec.get("needs_approval"))


def describe_call(name: str, args: dict[str, Any] | None) -> str:
    """Bir araç çağrısını kullanıcıya gösterilecek metne çevirir."""
    args = args or {}
    labels = {
        "run_shell_command": "Şu komut çalıştırılacak:\n$ {command}",
        "open_application": "Uygulama açılacak: {app_name}",
        "open_website": "Site açılacak: {url}",
        "get_weather": "Hava durumu sorgulanacak: {city}",
        "get_trending_topics": "X (Twitter) trendleri sorgulanacak",
        "set_volume": "Ses seviyesi değiştirilecek: %{level}",
        "web_search": "Web araması yapılacak: {query}",
    }
    template = labels.get(name)
    if template:
        try:
            return template.format(**args)
        except Exception:
            return template
    return f"Araç: {name} ({args})"


def run_tool(name: str, args: dict[str, Any] | None) -> str:
    """Bir aracı adıyla çalıştırır ve sonucu metne çevirir.

    Hatalar yakalanır ve modele anlamlı bir hata mesajı döndürülür; böylece
    ajan hatayı kullanıcıya açıklayabilir veya farklı bir yol deneyebilir.
    """
    spec = _SPEC_BY_NAME.get(name)
    if spec is None:
        return f"Hata: '{name}' adında bir araç yok."

    func: Callable[..., Any] = spec["function"]
    args = args or {}
    try:
        result = func(**args)
    except TypeError as exc:  # eksik/fazla parametre
        return f"Hata: araç parametreleri geçersiz ({exc})."
    except file_tools.ToolError as exc:
        return f"Hata: {exc}"
    except Exception as exc:  # araç içi beklenmeyen hata
        return f"Hata: araç çalıştırılamadı ({exc})."

    return str(result)
