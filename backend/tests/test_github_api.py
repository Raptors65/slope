import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.github_api import fetch_issue


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
