"""Dragon ajanı: Gemini modeli, araç döngüsü ve sohbet geçmişi yönetimi."""

from __future__ import annotations

import mimetypes
from pathlib import Path
from typing import Any, Callable, Sequence

try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None  # type: ignore
    types = None  # type: ignore

from config import settings as app_settings
from core.prompts import SYSTEM_PROMPT
from tools import registry

# UI katmanına durum bildirimleri göndermek için kullanılan geri çağırma tipi.
EventCallback = Callable[[str], None]


class AgentError(Exception):
    """Kullanıcıya gösterilebilir ajan hatası."""


class DragonAgent:
    """Gemini tabanlı, araç kullanabilen sohbet ajanı.

    Bir örnek, tek bir sohbet oturumunu temsil eder. `contents` listesi
    modelin gördüğü tam geçmişi (araç çağrıları dahil) tutar.
    `approval_requester` verilirse, riskli araçlar (ör. kabuk komutu)
    çalıştırılmadan önce kullanıcı onayı istenir.
    """

    def __init__(
        self,
        user_settings: dict[str, Any],
        approval_requester: Callable[[str], bool] | None = None,
    ) -> None:
        self.settings = user_settings
        self.approval_requester = approval_requester
        self.api_key = (user_settings.get("api_key") or "").strip()
        self.model = user_settings.get("model") or app_settings.DEFAULT_MODEL
        self.assistant_name = user_settings.get("assistant_name") or app_settings.APP_NAME

        if genai is None or types is None:
            raise AgentError(
                "google-genai paketi kurulu değil. Kurulum için: pip install google-genai"
            )

        if not self.api_key:
            raise AgentError(
                "Gemini API anahtarı tanımlı değil. Ayarlar penceresinden "
                "anahtarınızı girin."
            )

        try:
            self.client = genai.Client(api_key=self.api_key)
        except Exception as exc:  # pragma: no cover - kurulum hataları
            raise AgentError(f"Gemini istemcisi oluşturulamadı: {exc}") from exc

        self.contents: list[types.Content] = []

    # ------------------------------------------------------------------
    # Yapılandırma
    # ------------------------------------------------------------------
    def _system_prompt(self) -> str:
        custom = (self.settings.get("system_prompt") or "").strip()
        base = custom or SYSTEM_PROMPT
        return base.replace("Dragon", self.assistant_name)

    def _config(self) -> types.GenerateContentConfig:
        tool = registry.build_gemini_tool(
            web_search_enabled=bool(self.settings.get("web_search_enabled", True)),
            file_tools_enabled=bool(self.settings.get("file_tools_enabled", True)),
        )
        kwargs: dict[str, Any] = {
            "system_instruction": self._system_prompt(),
            "temperature": float(self.settings.get("temperature", 0.7)),
            "max_output_tokens": int(
                self.settings.get("max_output_tokens")
                or app_settings.DEFAULT_MAX_OUTPUT_TOKENS
            ),
        }
        if tool is not None:
            kwargs["tools"] = [tool]
        return types.GenerateContentConfig(**kwargs)

    # ------------------------------------------------------------------
    # Geçmiş yönetimi
    # ------------------------------------------------------------------
    def reset(self) -> None:
        """Konuşma geçmişini temizler."""
        self.contents = []

    def load_history(self, messages: Sequence[dict[str, Any]]) -> None:
        """Kaydedilmiş mesajlardan konuşma geçmişini yeniden kurar.

        Yalnızca metin ve görsel içeren kullanıcı/asistan turları yüklenir;
        ara araç çağrıları (saklanmıyorsa) atlanır.
        """
        self.contents = []
        for message in messages:
            role = message.get("role")
            if role not in ("user", "assistant"):
                continue
            text = message.get("text") or ""
            images = message.get("images") or []
            parts: list[types.Part] = []
            if role == "user":
                if text:
                    parts.append(types.Part.from_text(text=text))
                parts.extend(self._image_parts(images))
            else:
                if not text:
                    continue
                parts.append(types.Part.from_text(text=text))
            if parts:
                self.contents.append(types.Content(role=role, parts=parts))

    @staticmethod
    def _image_parts(paths: Sequence[str]) -> list[types.Part]:
        parts: list[types.Part] = []
        for raw in paths:
            path = Path(raw)
            if not path.exists():
                continue
            try:
                data = path.read_bytes()
            except OSError:
                continue
            mime, _ = mimetypes.guess_type(str(path))
            parts.append(
                types.Part.from_bytes(
                    data=data, mime_type=mime or "image/png"
                )
            )
        return parts

    # ------------------------------------------------------------------
    # Ana akış
    # ------------------------------------------------------------------
    def send(
        self,
        text: str,
        image_paths: Sequence[str] | None = None,
        on_event: EventCallback | None = None,
    ) -> str:
        """Kullanıcı mesajını gönderir ve asistanın yanıt metnini döndürür.

        Araç çağrıları otomatik olarak yürütülür. `on_event` verilirse her
        adımda kısa bir durum metniyle çağrılır (ör. "Web'de aranıyor...").
        """
        emit = on_event or (lambda _message: None)

        parts: list[types.Part] = []
        if text:
            parts.append(types.Part.from_text(text=text))
        parts.extend(self._image_parts(list(image_paths or [])))
        if not parts:
            raise AgentError("Gönderilecek bir içerik yok.")

        self.contents.append(types.Content(role="user", parts=parts))

        config = self._config()

        for _step in range(app_settings.MAX_TOOL_STEPS):
            emit("Dragon düşünüyor…")
            response = self._generate(config)

            candidate = response.candidates[0] if response.candidates else None
            if candidate is None or candidate.content is None:
                raise AgentError("Model boş bir yanıt döndürdü.")

            function_calls = response.function_calls or []
            if not function_calls:
                answer = response.text or ""
                self.contents.append(candidate.content)
                if not answer.strip():
                    raise AgentError("Model boş bir yanıt döndürdü.")
                return answer

            # Modelin araç çağrısını içeren turunu geçmişe ekle.
            self.contents.append(candidate.content)

            response_parts: list[types.Part] = []
            for call in function_calls:
                label = _tool_event_label(call.name or "")
                emit(label)
                result = self._run_tool_call(call.name or "", call.args)
                response_parts.append(
                    types.Part.from_function_response(
                        name=call.name or "", response={"result": result}
                    )
                )
            self.contents.append(types.Content(role="user", parts=response_parts))

        raise AgentError(
            "İstek çok fazla araç adımı gerektirdiği için durduruldu. "
            "Lütfen soruyu biraz sadeleştirin."
        )

    def _run_tool_call(self, name: str, args: dict[str, Any] | None) -> str:
        """Bir araç çağrısını (gerekirse onay isteyerek) çalıştırır."""
        if registry.requires_approval(name) and self.approval_requester is not None:
            approved = self.approval_requester(registry.describe_call(name, args))
            if not approved:
                return (
                    "Kullanıcı komutu onaylamadı; hiçbir işlem yapılmadı. "
                    "Kullanıcıya bunu bildir ve işlemi atla."
                )
        return registry.run_tool(name, args)

    def _generate(self, config: types.GenerateContentConfig) -> types.GenerateContentResponse:
        """Model çağrısını yapar ve hataları anlaşılır mesaja çevirir."""
        import threading

        result = {"resp": None, "exc": None}

        def _call():
            try:
                result["resp"] = self.client.models.generate_content(
                    model=self.model, contents=self.contents, config=config
                )
            except Exception as exc:
                result["exc"] = exc

        t = threading.Thread(target=_call, daemon=True)
        t.start()
        t.join(timeout=30)
        if t.is_alive():
            raise AgentError(
                "Model yanıt vermedi (zaman aşımı). İnternet bağlantınızı "
                "kontrol edin veya daha sonra tekrar deneyin."
            )
        if result["exc"] is not None:
            raise AgentError(_friendly_error(result["exc"])) from result["exc"]
        return result["resp"]


def _tool_event_label(name: str) -> str:
    labels = {
        "web_search": "Web'de aranıyor…",
        "get_trending_topics": "Gündem ve trendler alınıyor…",
        "read_file": "Dosya okunuyor…",
        "write_file": "Dosya yazılıyor…",
        "list_files": "Klasör listeleniyor…",
        "get_current_datetime": "Tarih alınıyor…",
        "open_application": "Uygulama açılıyor…",
        "open_website": "Site açılıyor…",
        "get_weather": "Hava durumu sorgulanıyor…",
        "set_volume": "Ses seviyesi ayarlanıyor…",
        "run_shell_command": "Komut çalıştırılıyor…",
    }
    return labels.get(name, f"Araç çalıştırılıyor: {name}…")


def _friendly_error(exc: Exception) -> str:
    """Ham SDK hatasını kullanıcı dostu bir mesaja dönüştürür."""
    text = str(exc)
    lowered = text.lower()
    if "api key" in lowered or "api_key" in lowered or "unauthenticated" in lowered:
        return "API anahtarı geçersiz görünüyor. Ayarlardan kontrol edin."
    if "quota" in lowered or "rate limit" in lowered or "429" in text:
        return "İstek kotası aşıldı veya çok hızlı istek gönderildi. Biraz bekleyin."
    if ("not found" in lowered or "not_found" in lowered or "404" in text) and "model" in lowered:
        return (
            "Seçili model artık kullanılamıyor. Ayarlardan güncel bir model "
            "seçin (örn. gemini-3.8-flash)."
        )
    if "timeout" in lowered or "timed out" in lowered:
        return "Bağlantı zaman aşımına uğradı. İnternet bağlantınızı kontrol edin."
    if "network" in lowered or "connection" in lowered:
        return "Ağ hatası: İnternet bağlantınızı kontrol edin."
    if "503" in text or "service unavailable" in lowered or "unavailable" in lowered:
        return "Gemini servisi şu an kullanılamıyor. Biraz bekleyip tekrar deneyin."
    if "500" in text or "internal" in lowered:
        return "Gemini sunucusunda geçici bir hata oluştu. Tekrar deneyin."
    return f"Model hatası: {text}"
