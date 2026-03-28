import asyncio
import hashlib
import hmac
import json
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from httpx import ASGITransport
from starlette.testclient import TestClient

from app.main import app
from app.schemas.github_webhook import WebhookSkipReason
from app.schemas.ingestion import RepoIngestion


def _sign(body: bytes, secret: str) -> str:
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_invalid_signature(client: TestClient) -> None:
    r = client.post(
        "/github/webhook",
        content=b"{}",
        headers={
            "X-GitHub-Event": "issues",
            "X-Hub-Signature-256": "sha256=deadbeef",
            "Content-Type": "application/json",
        },
    )
    assert r.status_code == 401


def test_wrong_event_returns_200(client: TestClient) -> None:
    body = b"{}"
    r = client.post(
        "/github/webhook",
        content=body,
        headers={
            "X-GitHub-Event": "ping",
            "X-Hub-Signature-256": _sign(body, "whsec_test"),
            "Content-Type": "application/json",
        },
    )
    assert r.status_code == 200
    assert r.json()["skipped"] is True


def test_action_not_assigned(client: TestClient) -> None:
    body = json.dumps({"action": "opened"}).encode()
    r = client.post(
        "/github/webhook",
        content=body,
        headers={
            "X-GitHub-Event": "issues",
            "X-Hub-Signature-256": _sign(body, "whsec_test"),
            "Content-Type": "application/json",
        },
    )
    assert r.status_code == 200


@patch(
    "app.pipeline.webhook_jobs.augment_relevance_svc.run_augment_relevance",
    new_callable=AsyncMock,
)
@patch("app.pipeline.webhook_jobs.ingest_repository", new_callable=AsyncMock)
@patch("app.api.github_webhook.issue_comments_contain_marker", new_callable=AsyncMock)
@pytest.mark.asyncio
async def test_assigned_accepted_202(
    mock_comments: AsyncMock,
    mock_ingest: AsyncMock,
    mock_augment: AsyncMock,
) -> None:
    mock_comments.return_value = False
    mock_augment.return_value = None
    mock_ingest.return_value = RepoIngestion(
        owner="acme",
        repo="demo",
        default_branch="main",
        tree_paths=[],
        tree_truncated=False,
        readme_text=None,
        snippets=[],
    )
    payload = {
        "action": "assigned",
        "repository": {"full_name": "acme/demo", "default_branch": "main"},
        "issue": {"number": 42},
    }
    body = json.dumps(payload).encode()
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.post(
            "/github/webhook",
            content=body,
            headers={
                "X-GitHub-Event": "issues",
                "X-Hub-Signature-256": _sign(body, "whsec_test"),
                "Content-Type": "application/json",
            },
        )
        assert r.status_code == 202, r.text
        assert r.json()["issue"] == 42
        # Background pipeline runs on the same loop; give it a tick after the response.
        await asyncio.sleep(0.25)
    mock_comments.assert_awaited_once()
    mock_ingest.assert_awaited_once()
    mock_augment.assert_awaited_once()


@patch("app.pipeline.webhook_jobs.ingest_repository", new_callable=AsyncMock)
@patch("app.api.github_webhook.issue_comments_contain_marker", new_callable=AsyncMock)
def test_idempotency_skip(
    mock_comments: AsyncMock,
    mock_ingest: AsyncMock,
    client: TestClient,
) -> None:
    mock_comments.return_value = True
    payload = {
        "action": "assigned",
        "repository": {"full_name": "acme/demo"},
        "issue": {"number": 1},
    }
    body = json.dumps(payload).encode()
    r = client.post(
        "/github/webhook",
        content=body,
        headers={
            "X-GitHub-Event": "issues",
            "X-Hub-Signature-256": _sign(body, "whsec_test"),
            "Content-Type": "application/json",
        },
    )
    assert r.status_code == 200
    assert r.json()["reason"] == WebhookSkipReason.ALREADY_COMMENTED
    mock_ingest.assert_not_called()
