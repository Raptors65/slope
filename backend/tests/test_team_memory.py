"""Tests for Phase 6 JSON team memory."""

import pytest

from app.config import Settings
from app.schemas.llm_outputs import MapFileEntry, OnboardingMap, TicketAnalysis
from app.services.team_memory import (
    build_lesson_snapshot,
    memory_file_path,
    recall_snippets,
    remember_from_run,
)


def _settings(tmp_path) -> Settings:
    return Settings(
        openrouter_api_key=None,
        github_pat="p",
        github_webhook_secret="s",
        memory_store_path=str(tmp_path / "memory.json"),
    )


@pytest.mark.asyncio
async def test_recall_empty_store(tmp_path) -> None:
    settings = _settings(tmp_path)
    out = await recall_snippets(
        "o",
        "r",
        feature_area="auth",
        search_terms=["login"],
        settings=settings,
    )
    assert out == []


@pytest.mark.asyncio
async def test_remember_then_recall_by_keyword(tmp_path) -> None:
    settings = _settings(tmp_path)
    analysis = TicketAnalysis(
        feature_area="Middleware",
        task_type="feature",
        risk_surface="Touch request pipeline carefully.",
        suggested_search_terms=["express", "router"],
    )
    omap = OnboardingMap(
        files_to_read=[
            MapFileEntry(path="lib/router.js", summary="routing"),
        ],
        warnings=["Order matters for middleware."],
        mermaid="",
    )
    await remember_from_run(
        "acme",
        "demo",
        1,
        issue_title="Add middleware",
        analysis=analysis,
        omap=omap,
        settings=settings,
    )

    snippets = await recall_snippets(
        "acme",
        "demo",
        feature_area="HTTP Middleware stack",
        search_terms=["express"],
        settings=settings,
    )
    assert len(snippets) == 1
    assert "middleware" in snippets[0].lower()

    other_repo = await recall_snippets(
        "acme",
        "other",
        feature_area="HTTP Middleware",
        search_terms=["express"],
        settings=settings,
    )
    assert other_repo == []


def test_build_lesson_snapshot_truncates() -> None:
    long_warn = "x" * 500
    analysis = TicketAnalysis(
        feature_area="a",
        task_type="b",
        risk_surface="risk",
        suggested_search_terms=[],
    )
    omap = OnboardingMap(
        files_to_read=[],
        warnings=[long_warn],
        mermaid="",
    )
    snap = build_lesson_snapshot("T", analysis, omap, max_len=120)
    assert len(snap) <= 120


def test_memory_file_path_default_uses_backend_data(monkeypatch) -> None:
    monkeypatch.delenv("MEMORY_STORE_PATH", raising=False)
    s = Settings(github_pat="p", github_webhook_secret="s")
    p = memory_file_path(s)
    assert p.name == "memory.json"
    assert p.parent.name == "data"


@pytest.mark.asyncio
async def test_corrupt_file_recall_returns_empty(tmp_path) -> None:
    path = tmp_path / "memory.json"
    path.write_text("not json {{{", encoding="utf-8")
    settings = _settings(tmp_path)
    out = await recall_snippets(
        "o",
        "r",
        feature_area="anything",
        search_terms=["words", "here"],
        settings=settings,
    )
    assert out == []
    assert "not json" in path.read_text(encoding="utf-8")
