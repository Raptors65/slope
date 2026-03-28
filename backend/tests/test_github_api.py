import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.constants import ONBOARDING_MAP_MARKER
from app.services.github_api import (
    fetch_issue,
    format_onboarding_map_comment_body,
    post_issue_comment,
)


@pytest.mark.asyncio
async def test_fetch_issue_parses_title_body() -> None:
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    resp.json = MagicMock(return_value={"title": "Hello", "body": "World"})

    client_instance = MagicMock()
    client_instance.get = AsyncMock(return_value=resp)

    class _CM:
        async def __aenter__(self) -> MagicMock:
            return client_instance

        async def __aexit__(self, *args: object) -> None:
            return None

    with patch("app.services.github_api.httpx.AsyncClient", return_value=_CM()):
        title, body = await fetch_issue("acme", "demo", 99, "pat-token")

    assert title == "Hello"
    assert body == "World"
    client_instance.get.assert_awaited_once()
    url = client_instance.get.await_args.args[0]
    assert "repos/acme/demo/issues/99" in url


def test_format_onboarding_map_comment_body_includes_link_and_marker() -> None:
    body = format_onboarding_map_comment_body(
        dashboard_base_url="http://localhost:3000/",
        run_id="abc-123",
    )
    assert ONBOARDING_MAP_MARKER in body
    assert "http://localhost:3000/runs/abc-123" in body
    assert "open the dashboard" in body.lower()


@pytest.mark.asyncio
async def test_post_issue_comment_posts_json_body() -> None:
    resp = MagicMock()
    resp.raise_for_status = MagicMock()

    client_instance = MagicMock()
    client_instance.post = AsyncMock(return_value=resp)

    class _CM:
        async def __aenter__(self) -> MagicMock:
            return client_instance

        async def __aexit__(self, *args: object) -> None:
            return None

    with patch("app.services.github_api.httpx.AsyncClient", return_value=_CM()):
        await post_issue_comment(
            "acme", "demo", 5, "pat", body="Hello\n\n<!-- slope:onboarding-map -->"
        )

    client_instance.post.assert_awaited_once()
    call_kw = client_instance.post.await_args.kwargs
    assert call_kw["json"] == {
        "body": "Hello\n\n<!-- slope:onboarding-map -->",
    }
    url = client_instance.post.await_args.args[0]
    assert "repos/acme/demo/issues/5/comments" in url
