import tomllib
from functools import lru_cache
from pathlib import Path

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@lru_cache
def _package_version() -> str:
    pyproject = Path(__file__).resolve().parents[2] / "pyproject.toml"
    with pyproject.open("rb") as f:
        return tomllib.load(f)["project"]["version"]


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/version")
def version() -> dict[str, str]:
    return {"version": _package_version()}
