"""HTTP tests for GET /runs (Phase 9 minimal)."""

import asyncio

import pytest
from starlette.testclient import TestClient

from app.main import app
from app.schemas.llm_outputs import TicketAnalysis
from app.services.runs_store import build_run_record, save_run


@pytest.fixture
def http_client() -> TestClient:
    return TestClient(app)


def test_list_runs_empty(http_client: TestClient) -> None:
    r = http_client.get("/runs")
    assert r.status_code == 200
    assert r.json() == []


def test_get_run_404(http_client: TestClient) -> None:
    r = http_client.get("/runs/00000000-0000-0000-0000-000000000000")
    assert r.status_code == 404


def test_runs_api_after_save(http_client: TestClient) -> None:
    from app.config import get_settings

    settings = get_settings()
    analysis = TicketAnalysis(
        feature_area="x",
        task_type="y",
        risk_surface="z",
        suggested_search_terms=[],
    )
    rec = build_run_record(
        owner="u",
        repo="v",
        issue_number=3,
        issue_title="api",
        issue_body="body",
        default_branch="main",
        analysis=analysis,
        augment_result=None,
        onboarding_map=None,
        memory_snippets=[],
        image_urls=[],
    )
    run_id = asyncio.run(save_run(rec, settings=settings))

    listed = http_client.get("/runs").json()
    assert len(listed) >= 1
    assert any(row["id"] == run_id for row in listed)

    detail = http_client.get(f"/runs/{run_id}")
    assert detail.status_code == 200
    assert detail.json()["issue_number"] == 3
    assert detail.json()["issue_title"] == "api"
