"""Tests for runs JSON store."""

import pytest

from app.config import Settings
from app.schemas.llm_outputs import OnboardingMap, TicketAnalysis
from app.services.runs_store import (
    build_run_record,
    get_run,
    list_run_summaries,
    save_run,
)


def _settings(tmp_path) -> Settings:
    return Settings(
        openrouter_api_key=None,
        github_pat="p",
        github_webhook_secret="s",
        memory_store_path=str(tmp_path / "m.json"),
        runs_store_path=str(tmp_path / "runs.json"),
    )


@pytest.mark.asyncio
async def test_save_list_get_roundtrip(tmp_path) -> None:
    settings = _settings(tmp_path)
    analysis = TicketAnalysis(
        feature_area="auth",
        task_type="feature",
        risk_surface="careful",
        suggested_search_terms=["login"],
    )
    rec = build_run_record(
        owner="acme",
        repo="demo",
        issue_number=7,
        issue_title="T",
        issue_body="B",
        default_branch="main",
        analysis=analysis,
        augment_result=None,
        onboarding_map=None,
        memory_snippets=["prior"],
        image_urls=[],
    )
    rid = await save_run(rec, settings=settings)
    assert rid == rec.id

    rows = await list_run_summaries(settings=settings, limit=10)
    assert len(rows) == 1
    assert rows[0].id == rid
    assert rows[0].map_ready is False

    full = await get_run(rid, settings=settings)
    assert full is not None
    assert full.issue_number == 7
    assert full.memory_snippets == ["prior"]


@pytest.mark.asyncio
async def test_map_ready_summary(tmp_path) -> None:
    settings = _settings(tmp_path)
    analysis = TicketAnalysis(
        feature_area="a",
        task_type="b",
        risk_surface="c",
        suggested_search_terms=[],
    )
    omap = OnboardingMap(
        files_to_read=[],
        warnings=["w"],
        mermaid="graph TD;A-->B",
    )
    rec = build_run_record(
        owner="o",
        repo="r",
        issue_number=1,
        issue_title="",
        issue_body="",
        default_branch=None,
        analysis=analysis,
        augment_result=None,
        onboarding_map=omap,
        memory_snippets=[],
        image_urls=[],
    )
    await save_run(rec, settings=settings)
    rows = await list_run_summaries(settings=settings)
    assert rows[0].map_ready is True


@pytest.mark.asyncio
async def test_get_run_missing(tmp_path) -> None:
    settings = _settings(tmp_path)
    assert await get_run("does-not-exist", settings=settings) is None
