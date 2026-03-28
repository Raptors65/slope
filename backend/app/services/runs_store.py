"""Append-only JSON store for onboarding runs (Phase 8 / 9)."""

from __future__ import annotations

import asyncio
import json
import uuid
from datetime import datetime, timezone
from json import JSONDecodeError
import logging
from pathlib import Path

from pydantic import BaseModel, Field, ValidationError

from app.config import Settings
from app.schemas.augment import AugmentRelevanceResult
from app.schemas.llm_outputs import OnboardingMap, TicketAnalysis
from app.schemas.onboarding_run import OnboardingRunRecord, OnboardingRunSummary

MAX_RUNS_RETAINED = 200
MAX_ISSUE_BODY_CHARS = 24_000

_lock = asyncio.Lock()
log = logging.getLogger("slope.runs")


class _RunsFile(BaseModel):
    version: int = 1
    runs: list[OnboardingRunRecord] = Field(default_factory=list)


def _backend_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


def runs_file_path(settings: Settings) -> Path:
    raw = (settings.runs_store_path or "").strip()
    if raw:
        return Path(raw).expanduser()
    return _backend_root() / "data" / "runs.json"


def _load_sync(path: Path) -> _RunsFile:
    if not path.exists():
        return _RunsFile()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return _RunsFile.model_validate(data)
    except (OSError, JSONDecodeError, ValidationError) as e:
        log.warning("Failed to load runs store %s; starting fresh: %s", path, e)
        return _RunsFile()


def _save_sync(path: Path, store: _RunsFile) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(store.model_dump_json(indent=2), encoding="utf-8")


def build_run_record(
    *,
    owner: str,
    repo: str,
    issue_number: int,
    issue_title: str,
    issue_body: str,
    default_branch: str | None,
    analysis: TicketAnalysis,
    augment_result: AugmentRelevanceResult | None,
    onboarding_map: OnboardingMap | None,
    memory_snippets: list[str],
    image_urls: list[str],
) -> OnboardingRunRecord:
    body = issue_body.strip()
    if len(body) > MAX_ISSUE_BODY_CHARS:
        body = body[: MAX_ISSUE_BODY_CHARS - 20] + "\n…[truncated]"
    rid = str(uuid.uuid4())
    created = (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )
    return OnboardingRunRecord(
        id=rid,
        created_at=created,
        owner=owner,
        repo=repo,
        issue_number=issue_number,
        issue_title=issue_title.strip()[:500],
        issue_body=body,
        default_branch=default_branch,
        ticket_analysis=analysis.model_dump(mode="json"),
        augment=augment_result.model_dump(mode="json") if augment_result else None,
        onboarding_map=onboarding_map.model_dump(mode="json") if onboarding_map else None,
        memory_snippets=list(memory_snippets),
        image_urls=list(image_urls),
    )


async def save_run(record: OnboardingRunRecord, *, settings: Settings) -> str:
    """Prepend run, cap list size. Returns run id."""
    path = runs_file_path(settings)
    async with _lock:
        store = _load_sync(path)
        store.runs.insert(0, record)
        if len(store.runs) > MAX_RUNS_RETAINED:
            store.runs = store.runs[:MAX_RUNS_RETAINED]
        _save_sync(path, store)
    return record.id


async def list_run_summaries(
    *, settings: Settings, limit: int = 50
) -> list[OnboardingRunSummary]:
    path = runs_file_path(settings)
    async with _lock:
        store = _load_sync(path)
    out: list[OnboardingRunSummary] = []
    for r in store.runs[: max(1, min(limit, 200))]:
        out.append(
            OnboardingRunSummary(
                id=r.id,
                created_at=r.created_at,
                owner=r.owner,
                repo=r.repo,
                issue_number=r.issue_number,
                issue_title=r.issue_title,
                map_ready=r.onboarding_map is not None,
            )
        )
    return out


async def get_run(run_id: str, *, settings: Settings) -> OnboardingRunRecord | None:
    path = runs_file_path(settings)
    async with _lock:
        store = _load_sync(path)
    for r in store.runs:
        if r.id == run_id:
            return r
    return None
