"""Thin async wrapper around the official OpenRouter Python SDK."""

from __future__ import annotations

import json
import re
from collections.abc import Sequence
from typing import Any, TypeVar

from openrouter import OpenRouter
from openrouter.components import ChatMessagesTypedDict
from openrouter.types import UNSET

from app.config import Settings, get_settings

T = TypeVar("T")


class OpenRouterConfigError(RuntimeError):
    """Missing API key or invalid configuration."""


class OpenRouterEmptyResponseError(RuntimeError):
    """Completion returned no usable assistant text."""


class OpenRouterRefusalError(RuntimeError):
    """Model refused the request."""


_JSON_FENCE = re.compile(r"```(?:json)?\s*([\s\S]*?)```", re.IGNORECASE)


def user_message_multimodal(text: str, image_urls: Sequence[str]) -> ChatMessagesTypedDict:
    """Build a user message with text plus `image_url` parts (URLs or data: URIs)."""
    urls = [u.strip() for u in image_urls if u.strip()]
    if not urls:
        return {"role": "user", "content": text}
    parts: list[dict[str, Any]] = [{"type": "text", "text": text}]
    for url in urls:
        parts.append({"type": "image_url", "image_url": {"url": url}})
    return {"role": "user", "content": parts}


def extract_json_substring(raw: str) -> str:
    """Strip optional ```json fences; return inner JSON or the whole string trimmed."""
    text = raw.strip()
    m = _JSON_FENCE.search(text)
    if m:
        return m.group(1).strip()
    return text


def parse_model_json(raw: str, model: type[T]) -> T:
    """Parse assistant output into a Pydantic model (JSON object)."""
    blob = extract_json_substring(raw)
    return model.model_validate(json.loads(blob))


def _assistant_text_from_choice(choice: Any) -> str:
    msg = choice.message
    refusal = getattr(msg, "refusal", None)
    if refusal is not None and refusal is not UNSET:
        rs = str(refusal).strip()
        if rs:
            raise OpenRouterRefusalError(rs)
    content = msg.content
    if content is None or content is UNSET:
        return ""
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        chunks: list[str] = []
        for item in content:
            if isinstance(item, dict):
                if item.get("type") == "text":
                    chunks.append(str(item.get("text", "")))
            else:
                t = getattr(item, "type", None)
                if t == "text":
                    chunks.append(str(getattr(item, "text", "") or ""))
        return "".join(chunks).strip()
    return str(content).strip()


async def chat_async(
    messages: list[ChatMessagesTypedDict],
    *,
    model: str | None = None,
    temperature: float | None = 1.0,
    settings: Settings | None = None,
) -> str:
    """
    Send chat completion; return assistant message text.

    Raises OpenRouterConfigError if API key is missing, OpenRouterRefusalError on refusal,
    OpenRouterEmptyResponseError if content is empty.
    """
    cfg = settings or get_settings()
    if not cfg.openrouter_api_key:
        raise OpenRouterConfigError("OPENROUTER_API_KEY is not set")

    use_model = model or cfg.openrouter_model
    kwargs: dict[str, Any] = {
        "model": use_model,
        "messages": messages,
    }
    if temperature is not None:
        kwargs["temperature"] = temperature
    if cfg.openrouter_http_referer:
        kwargs["http_referer"] = cfg.openrouter_http_referer
    if cfg.openrouter_app_title:
        kwargs["x_open_router_title"] = cfg.openrouter_app_title

    async with OpenRouter(api_key=cfg.openrouter_api_key) as client:
        result = await client.chat.send_async(**kwargs)

    if not result.choices:
        raise OpenRouterEmptyResponseError("OpenRouter returned no choices")
    text = _assistant_text_from_choice(result.choices[0])
    if not text:
        raise OpenRouterEmptyResponseError("OpenRouter returned empty message content")
    return text
