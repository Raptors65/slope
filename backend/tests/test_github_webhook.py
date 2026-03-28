import hashlib
import hmac
import json
from unittest.mock import AsyncMock, patch

import pytest
from starlette.testclient import TestClient

from app.main import app


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


@patch("app.api.github_webhook.issue_comments_contain_marker", new_callable=AsyncMock)
def test_assigned_accepted_202(mock_marker: AsyncMock, client: TestClient) -> None:
    mock_marker.return_value = False
    payload = {
        "action": "assigned",
        "repository": {"full_name": "acme/demo"},
        "issue": {"number": 42},
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
    assert r.status_code == 202, r.text
    assert r.json()["issue"] == 42
    mock_marker.assert_awaited_once()


@patch("app.api.github_webhook.issue_comments_contain_marker", new_callable=AsyncMock)
def test_idempotency_skip(mock_marker: AsyncMock, client: TestClient) -> None:
    mock_marker.return_value = True
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
    assert r.json()["reason"] == "already_commented"
