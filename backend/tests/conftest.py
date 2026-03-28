import pytest

from app.config import get_settings


@pytest.fixture(autouse=True)
def github_webhook_env(
    monkeypatch: pytest.MonkeyPatch, tmp_path_factory: pytest.TempPathFactory
) -> None:
    monkeypatch.setenv("GITHUB_WEBHOOK_SECRET", "whsec_test")
    monkeypatch.setenv("GITHUB_PAT", "pat_test")
    mem = tmp_path_factory.mktemp("memory") / "memory.json"
    monkeypatch.setenv("MEMORY_STORE_PATH", str(mem))
    runs = tmp_path_factory.mktemp("runs") / "runs.json"
    monkeypatch.setenv("RUNS_STORE_PATH", str(runs))
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
