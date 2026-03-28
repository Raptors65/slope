"""Phase 6 — team memory: JSON file, recall before map, append after success."""

from __future__ import annotations

import asyncio
import json
import logging
import re
from datetime import datetime, timezone
from json import JSONDecodeError
from pathlib import Path

from pydantic import ValidationError

from app.config import Settings
from app.schemas.llm_outputs import OnboardingMap, TicketAnalysis
from app.schemas.memory import MemoryEntry, MemoryStoreFile

log = logging.getLogger("slope.memory")

_lock = asyncio.Lock()

_WORD = re.compile(r"[a-zA-Z]{3,}")


def _backend_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


def memory_file_path(settings: Settings) -> Path:
    raw = (settings.memory_store_path or "").strip()
    if raw:
        return Path(raw).expanduser()
    return _backend_root() / "data" / "memory.json"


def _load_sync(path: Path) -> MemoryStoreFile:
    if not path.exists():
        return MemoryStoreFile()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return MemoryStoreFile.model_validate(data)
    except (OSError, JSONDecodeError, ValidationError) as e:
        log.warning("Failed to load memory store %s; treating as empty: %s", path, e)
        return MemoryStoreFile()


def _save_sync(path: Path, store: MemoryStoreFile) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        store.model_dump_json(indent=2),
        encoding="utf-8",
    )


def _tokenize(s: str) -> set[str]:
    return {w.lower() for w in _WORD.findall(s)}


def _score_entry(feature_area: str, search_terms: list[str], entry: MemoryEntry) -> int:
    tokens = _tokenize(feature_area) | _tokenize(" ".join(search_terms))
    if not tokens:
        return 0
    blob = _tokenize(
        f"{entry.area} {entry.lesson} {' '.join(entry.tags)}",
    )
    return len(tokens & blob)


def build_lesson_snapshot(
    issue_title: str,
    analysis: TicketAnalysis,
    omap: OnboardingMap,
    *,
    max_len: int = 800,
) -> str:
    """Compact text to store for future recall (warnings + risk + key paths)."""
    parts: list[str] = []
    if omap.warnings:
        parts.append("Warnings: " + "; ".join(omap.warnings[:6]))
    rs = (analysis.risk_surface or "").strip()
    if rs:
        parts.append(rs[:400])
    if omap.files_to_read:
        paths = ", ".join(f.path for f in omap.files_to_read[:6])
        parts.append(f"Key paths: {paths}")
    title = (issue_title or "").strip()
    if title:
        parts.insert(0, f"Issue: {title[:200]}")
    text = " | ".join(p for p in parts if p)
    return text[:max_len] if len(text) > max_len else text


async def recall_snippets(
    owner: str,
    repo: str,
    *,
    feature_area: str,
    search_terms: list[str],
    settings: Settings,
    top_k: int = 8,
) -> list[str]:
    """Return up to ``top_k`` lesson strings for this repo that overlap the area / terms."""
    path = memory_file_path(settings)
    async with _lock:
        store = _load_sync(path)

    matched: list[tuple[int, str, MemoryEntry]] = []
    for e in store.entries:
        if e.owner != owner or e.repo != repo:
            continue
        sc = _score_entry(feature_area, search_terms, e)
        if sc > 0:
            matched.append((sc, e.created_at, e))

    matched.sort(key=lambda t: t[1], reverse=True)
    matched.sort(key=lambda t: t[0], reverse=True)

    out: list[str] = []
    seen: set[str] = set()
    for _, _, e in matched:
        line = e.lesson.strip()
        if not line or line in seen:
            continue
        seen.add(line)
        out.append(line)
        if len(out) >= top_k:
            break
    return out


async def remember_from_run(
    owner: str,
    repo: str,
    issue_number: int,
    *,
    issue_title: str,
    analysis: TicketAnalysis,
    omap: OnboardingMap,
    settings: Settings,
) -> None:
    """Append one entry after a successful onboarding map (Step 6)."""
    lesson = build_lesson_snapshot(issue_title, analysis, omap)
    if not lesson.strip():
        log.debug("Skipping memory write: empty lesson snapshot")
        return

    path = memory_file_path(settings)
    entry = MemoryEntry(
        owner=owner,
        repo=repo,
        area=(analysis.feature_area or "")[:240],
        lesson=lesson,
        issue_number=issue_number,
        created_at=datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z"),
        tags=list(analysis.suggested_search_terms)[:12],
    )

    async with _lock:
        store = _load_sync(path)
        store.entries.append(entry)
        _save_sync(path, store)

    log.info(
        "Memory stored for %s/%s#%s (entries_total=%d)",
        owner,
        repo,
        issue_number,
        len(store.entries),
    )
