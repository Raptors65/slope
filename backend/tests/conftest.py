import pytest

from app.config import get_settings


@pytest.fixture(autouse=True)
def github_webhook_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GITHUB_WEBHOOK_SECRET", "whsec_test")
    monkeypatch.setenv("GITHUB_PAT", "pat_test")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
