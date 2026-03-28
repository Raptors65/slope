import json

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from pydantic import ValidationError

from app.config import Settings
from app.schemas.llm_outputs import OnboardingMap, TicketAnalysis
from app.services.openrouter_client import (
    OpenRouterConfigError,
    OpenRouterEmptyResponseError,
    OpenRouterRefusalError,
    chat_async,
    extract_json_substring,
    parse_model_json,
    user_message_multimodal,
)


def test_user_message_multimodal_text_only() -> None:
    m = user_message_multimodal("hello", [])
    assert m == {"role": "user", "content": "hello"}


def test_user_message_multimodal_with_images() -> None:
    m = user_message_multimodal("describe", ["https://example.com/a.png", "  ", "data:image/png;base64,xxx"])
    assert m["role"] == "user"
    assert isinstance(m["content"], list)
    assert m["content"][0] == {"type": "text", "text": "describe"}
    assert m["content"][1] == {
        "type": "image_url",
        "image_url": {"url": "https://example.com/a.png"},
    }
    assert m["content"][2]["type"] == "image_url"


def test_extract_json_substring_fence() -> None:
    raw = 'Sure.\n```json\n{"a": 1}\n```\n'
    assert extract_json_substring(raw) == '{"a": 1}'


def test_parse_model_json_ticket_analysis() -> None:
    raw = """```json
{
  "feature_area": "payments",
  "task_type": "bugfix",
  "risk_surface": "auth middleware",
  "suggested_search_terms": ["rate", "limit"],
  "image_observations": null
}
```"""
    m = parse_model_json(raw, TicketAnalysis)
    assert m.feature_area == "payments"
    assert m.suggested_search_terms == ["rate", "limit"]
    assert m.image_observations is None


def test_parse_model_json_onboarding_map() -> None:
    raw = '{"files_to_read": [{"path": "a.py", "summary": "entry"}], "warnings": ["x"], "mermaid": "graph TD; A-->B"}'
    m = parse_model_json(raw, OnboardingMap)
    assert len(m.files_to_read) == 1
    assert m.mermaid.startswith("graph TD")


def test_parse_model_json_invalid_raises() -> None:
    with pytest.raises((ValidationError, json.JSONDecodeError)):
        parse_model_json("{not json", TicketAnalysis)


@pytest.mark.asyncio
async def test_chat_async_missing_key() -> None:
    settings = Settings(
        openrouter_api_key=None,
        github_pat=None,
        github_webhook_secret=None,
    )
    with pytest.raises(OpenRouterConfigError):
        await chat_async(
            [{"role": "user", "content": "hi"}],
            settings=settings,
        )


@pytest.mark.asyncio
async def test_chat_async_success() -> None:
    settings = Settings(
        openrouter_api_key="sk-test",
        github_pat=None,
        github_webhook_secret=None,
    )
    mock_result = MagicMock()
    mock_result.choices = [
        MagicMock(
            message=MagicMock(content="  answer  ", refusal=None),
        )
    ]
    mock_client = MagicMock()
    mock_client.chat = MagicMock()
    mock_client.chat.send_async = AsyncMock(return_value=mock_result)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch("app.services.openrouter_client.OpenRouter", return_value=mock_client):
        out = await chat_async(
            [{"role": "user", "content": "hi"}],
            model="test/model",
            settings=settings,
        )
    assert out == "answer"
    mock_client.chat.send_async.assert_awaited_once()
    call_kw = mock_client.chat.send_async.await_args.kwargs
    assert call_kw["model"] == "test/model"
    assert call_kw["messages"][0]["role"] == "user"


@pytest.mark.asyncio
async def test_chat_async_refusal() -> None:
    settings = Settings(
        openrouter_api_key="sk-test",
        github_pat=None,
        github_webhook_secret=None,
    )
    mock_result = MagicMock()
    mock_result.choices = [
        MagicMock(message=MagicMock(content="", refusal="policy")),
    ]
    mock_client = MagicMock()
    mock_client.chat = MagicMock()
    mock_client.chat.send_async = AsyncMock(return_value=mock_result)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch("app.services.openrouter_client.OpenRouter", return_value=mock_client):
        with pytest.raises(OpenRouterRefusalError):
            await chat_async([{"role": "user", "content": "hi"}], settings=settings)


@pytest.mark.asyncio
async def test_chat_async_empty_choices() -> None:
    settings = Settings(
        openrouter_api_key="sk-test",
        github_pat=None,
        github_webhook_secret=None,
    )
    mock_result = MagicMock()
    mock_result.choices = []
    mock_client = MagicMock()
    mock_client.chat = MagicMock()
    mock_client.chat.send_async = AsyncMock(return_value=mock_result)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch("app.services.openrouter_client.OpenRouter", return_value=mock_client):
        with pytest.raises(OpenRouterEmptyResponseError):
            await chat_async([{"role": "user", "content": "hi"}], settings=settings)
