"""Augment Code SDK: clone + focused relevance task (Phase 5 / Step 3)."""

from __future__ import annotations

import asyncio
import logging
import os
import shutil
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from auggie_sdk import Auggie
from pydantic import ValidationError
from auggie_sdk.agent import ModelType

from app.config import Settings
from app.schemas.augment import AugmentRelevanceResult
from app.services.repo_clone import shallow_clone_github_repo

log = logging.getLogger("slope.augment")

# os.environ mutation for session auth; serialize Augment runs to avoid races.
_augment_lock = asyncio.Lock()

MAX_ISSUE_CHARS = 8_000
MAX_TREE_PATHS_IN_PROMPT = 120
MAX_README_CHARS = 4_000
MAX_TICKET_ANALYSIS_JSON_CHARS = 4_000


@contextmanager
def _augment_process_env(settings: Settings) -> Iterator[None]:
    """Merge Augment-related settings into os.environ for the CLI child process."""
    updates: dict[str, str] = {}
    if settings.augment_session_auth and settings.augment_session_auth.strip():
        updates["AUGMENT_SESSION_AUTH"] = settings.augment_session_auth.strip()
    if settings.augment_api_url and settings.augment_api_url.strip():
        updates["AUGMENT_API_URL"] = settings.augment_api_url.strip()

    previous: dict[str, str | None] = {}
    try:
        for key, value in updates.items():
            previous[key] = os.environ.get(key)
            os.environ[key] = value
        yield
    finally:
        for key, old in previous.items():
            if old is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = old


def _model_for_auggie(settings: Settings) -> ModelType | None:
    m = (settings.augment_model or "").strip().lower()
    allowed: tuple[ModelType, ...] = ("haiku4.5", "sonnet4.5", "sonnet4", "gpt5")
    if m in allowed:
        return m  # type: ignore[return-value]
    if m:
        log.warning("Unknown augment_model %r; using Auggie default", settings.augment_model)
    return None


def _build_instruction(
    *,
    issue_title: str,
    issue_body: str,
    tree_paths: list[str],
    readme_excerpt: str,
    ticket_analysis_json: str | None = None,
) -> str:
    body = issue_body.strip()
    if len(body) > MAX_ISSUE_CHARS:
        body = body[: MAX_ISSUE_CHARS - 20] + "\n…[truncated]"
    paths = tree_paths[:MAX_TREE_PATHS_IN_PROMPT]
    tree_block = "\n".join(paths) if paths else "(no tree paths provided)"
    readme = readme_excerpt.strip()
    if len(readme) > MAX_README_CHARS:
        readme = readme[: MAX_README_CHARS - 20] + "\n…[truncated]"

    prior_block = ""
    ta = (ticket_analysis_json or "").strip()
    if ta:
        if len(ta) > MAX_TICKET_ANALYSIS_JSON_CHARS:
            ta = ta[: MAX_TICKET_ANALYSIS_JSON_CHARS - 30] + "\n…[truncated]"
        prior_block = f"""
## Prior LLM ticket analysis (JSON — hints only; verify in the workspace)
{ta}
"""

    return f"""You are helping an engineer onboard to a ticket in this repository.

## Issue title
{issue_title.strip() or "(no title)"}

## Issue body
{body or "(empty)"}
{prior_block}
## Repository file paths (sample from API tree; not exhaustive)
{tree_block}

## README excerpt
{readme or "(none)"}

## Task
Using only what you can verify in this workspace:
1. List the 5–10 most relevant file paths for this issue, most important first, with a one-line reason each.
2. List short notes on import/call dependencies or control flow between those files (only if you can confirm from the code).

Return JSON with:
- `relevant_files`: array of `{{"path": "...", "reason": "..."}}`.
- `dependency_notes`: either an array of short strings, or an object mapping labels to notes (e.g. `{{"routing": "..."}}`) — both are accepted."""


def run_augment_relevance_sync(
    owner: str,
    repo: str,
    pat: str,
    *,
    default_branch: str | None,
    issue_title: str,
    issue_body: str,
    tree_paths: list[str],
    readme_excerpt: str,
    settings: Settings,
    ticket_analysis_json: str | None = None,
) -> AugmentRelevanceResult:
    """
    Clone repo shallowly, run Auggie with structured return type, remove clone dir.

    Intended to be called via asyncio.to_thread under _augment_lock.
    """
    tmp_parent = tempfile.mkdtemp(prefix="slope_augment_")
    clone_root = Path(tmp_parent) / "repo"
    try:
        shallow_clone_github_repo(
            owner,
            repo,
            pat,
            clone_root,
            branch=default_branch,
            timeout_seconds=float(settings.augment_clone_timeout_seconds),
        )
    except Exception:
        shutil.rmtree(tmp_parent, ignore_errors=True)
        raise

    instruction = _build_instruction(
        issue_title=issue_title,
        issue_body=issue_body,
        tree_paths=tree_paths,
        readme_excerpt=readme_excerpt,
        ticket_analysis_json=ticket_analysis_json,
    )
    model = _model_for_auggie(settings)
    cli_args = [
        "--max-turns",
        str(settings.augment_max_cli_turns),
        "--quiet",
    ]

    try:
        with _augment_process_env(settings):
            kwargs: dict[str, Any] = {
                "workspace_root": clone_root,
                "timeout": settings.augment_timeout_seconds,
                "cli_args": cli_args,
            }
            if model is not None:
                kwargs["model"] = model
            if settings.augment_api_key and settings.augment_api_key.strip():
                kwargs["api_key"] = settings.augment_api_key.strip()
            if settings.augment_api_url and settings.augment_api_url.strip():
                kwargs["api_url"] = settings.augment_api_url.strip()

            with Auggie(**kwargs) as agent:
                # Auggie only supports dataclasses / primitives for return_type, not Pydantic models.
                raw = agent.run(
                    instruction,
                    return_type=dict,
                    timeout=settings.augment_timeout_seconds,
                )
        if not isinstance(raw, dict):
            log.warning("Augment returned non-dict structured output: %s", type(raw).__name__)
            return AugmentRelevanceResult()
        try:
            return AugmentRelevanceResult.model_validate(raw)
        except ValidationError:
            log.exception("Augment output failed Pydantic validation; using empty result")
            return AugmentRelevanceResult()
    finally:
        shutil.rmtree(tmp_parent, ignore_errors=True)


async def run_augment_relevance(
    owner: str,
    repo: str,
    pat: str,
    *,
    default_branch: str | None,
    issue_title: str,
    issue_body: str,
    tree_paths: list[str],
    readme_excerpt: str,
    settings: Settings,
    ticket_analysis_json: str | None = None,
) -> AugmentRelevanceResult | None:
    """
    Run Phase 5 relevance pass; return None if Augment is skipped or fails (logged).
    """
    async with _augment_lock:
        try:
            return await asyncio.to_thread(
                run_augment_relevance_sync,
                owner,
                repo,
                pat,
                default_branch=default_branch,
                issue_title=issue_title,
                issue_body=issue_body,
                tree_paths=tree_paths,
                readme_excerpt=readme_excerpt,
                settings=settings,
                ticket_analysis_json=ticket_analysis_json,
            )
        except Exception:
            log.exception(
                "Augment relevance failed for %s/%s (issue context present=%s)",
                owner,
                repo,
                bool(issue_title or issue_body),
            )
            return None
