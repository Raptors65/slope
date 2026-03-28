"""Tests for Phase 7 OpenRouter ticket analysis and onboarding map."""

from unittest.mock import AsyncMock, patch

import pytest

from app.config import Settings
from app.schemas.llm_outputs import OnboardingMap
from app.services.onboarding_llm import (
    fallback_ticket_analysis,
    image_urls_from_issue_markdown,
    run_onboarding_map,
    run_ticket_analysis,
)


def test_image_urls_from_markdown_and_raw() -> None:
    body = """See ![s](https://user-images.githubusercontent.com/1/2.png) and
    also https://user-images.githubusercontent.com/u/v.jpg end."""
    urls = image_urls_from_issue_markdown(body)
    assert "https://user-images.githubusercontent.com/1/2.png" in urls
    assert any("user-images.githubusercontent.com/u/v.jpg" in u for u in urls)


def test_fallback_ticket_analysis_shape() -> None:
    t = fallback_ticket_analysis("T", "B")
    assert t.task_type == "unknown"
    assert isinstance(t.suggested_search_terms, list)


@pytest.mark.asyncio
async def test_run_ticket_analysis_skips_without_api_key() -> None:
    settings = Settings(
        openrouter_api_key=None,
        github_pat=None,
        github_webhook_secret=None,
    )
    out = await run_ticket_analysis(
        issue_title="x",
        issue_body="y",
        tree_paths=[],
        settings=settings,
    )
    assert out is None


@pytest.mark.asyncio
async def test_run_ticket_analysis_parses_json() -> None:
    settings = Settings(
        openrouter_api_key="sk-test",
        github_pat=None,
        github_webhook_secret=None,
    )
    payload = {
        "feature_area": "auth",
        "task_type": "bugfix",
        "risk_surface": "sessions",
        "suggested_search_terms": ["login"],
        "image_observations": None,
    }
    with patch(
        "app.services.onboarding_llm.chat_async",
        new_callable=AsyncMock,
        return_value='{"feature_area": "auth", "task_type": "bugfix", '
        '"risk_surface": "sessions", "suggested_search_terms": ["login"], '
        '"image_observations": null}',
    ):
        out = await run_ticket_analysis(
            issue_title="Login broken",
            issue_body="Cannot sign in",
            tree_paths=["app/auth.py"],
            settings=settings,
        )
    assert out is not None
    assert out.feature_area == payload["feature_area"]


@pytest.mark.asyncio
async def test_run_onboarding_map_skips_without_api_key() -> None:
    settings = Settings(
        openrouter_api_key=None,
        github_pat=None,
        github_webhook_secret=None,
    )
    analysis = fallback_ticket_analysis("", "")
    out = await run_onboarding_map(
        analysis=analysis,
        augment=None,
        memory_snippets=[],
        issue_title="t",
        issue_body="b",
        tree_paths=[],
        settings=settings,
    )
    assert out is None


@pytest.mark.asyncio
async def test_run_onboarding_map_parses_json() -> None:
    settings = Settings(
        openrouter_api_key="sk-test",
        github_pat=None,
        github_webhook_secret=None,
    )
    raw_map = (
        '{"files_to_read": [{"path": "a.py", "summary": "entry"}], '
        '"warnings": ["careful"], "mermaid": "graph TD; A-->B"}'
    )
    with patch(
        "app.services.onboarding_llm.chat_async",
        new_callable=AsyncMock,
        return_value=raw_map,
    ):
        out = await run_onboarding_map(
            analysis=fallback_ticket_analysis("T", "B"),
            augment=None,
            memory_snippets=[],
            issue_title="T",
            issue_body="B",
            tree_paths=["a.py"],
            settings=settings,
        )
    assert isinstance(out, OnboardingMap)
    assert len(out.files_to_read) == 1
    assert out.files_to_read[0].path == "a.py"
    assert "A-->B" in out.mermaid
