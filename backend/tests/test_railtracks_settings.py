"""Railtracks killswitch (USE_RAILTRACKS / SLOPE_USE_RAILTRACKS)."""

from app.config import Settings


def test_use_railtracks_default_false(monkeypatch) -> None:
    monkeypatch.delenv("USE_RAILTRACKS", raising=False)
    monkeypatch.delenv("SLOPE_USE_RAILTRACKS", raising=False)
    # Skip `.env` so local USE_RAILTRACKS does not affect this assertion.
    s = Settings(_env_file=None)
    assert s.use_railtracks is False


def test_use_railtracks_env_use_railtracks(monkeypatch) -> None:
    monkeypatch.setenv("USE_RAILTRACKS", "1")
    monkeypatch.delenv("SLOPE_USE_RAILTRACKS", raising=False)
    assert Settings().use_railtracks is True


def test_use_railtracks_env_slope_alias(monkeypatch) -> None:
    monkeypatch.delenv("USE_RAILTRACKS", raising=False)
    monkeypatch.setenv("SLOPE_USE_RAILTRACKS", "true")
    assert Settings().use_railtracks is True


def test_use_railtracks_explicit_false(monkeypatch) -> None:
    monkeypatch.setenv("USE_RAILTRACKS", "0")
    assert Settings().use_railtracks is False
