"""Phase 7: OpenRouter ticket analysis (Step 2) and onboarding map (Step 5)."""

from __future__ import annotations

import json
import logging
import re
from pydantic import ValidationError

from app.config import Settings
from app.schemas.augment import AugmentRelevanceResult
from app.schemas.llm_outputs import OnboardingMap, TicketAnalysis
from app.services.openrouter_client import (
    OpenRouterConfigError,
    OpenRouterEmptyResponseError,
    chat_async,
    parse_model_json,
    user_message_multimodal,
)

log = logging.getLogger("slope.onboarding_llm")

_SYSTEM_JSON = (
    "You are a precise assistant. Respond with a single JSON object only — "
    "no markdown code fences, no prose before or after."
)

_MARKDOWN_IMG = re.compile(r"!\[[^\]]*\]\(\s*(https?://[^)\s]+)\s*\)")
_RAW_USER_IMG = re.compile(
    r"https://user-images\.githubusercontent\.com/[^\s\)\"'<>]+", re.I
)

MAX_TREE_FOR_ANALYSIS = 80
MAX_TREE_FOR_MAP = 100
MAX_BODY_IN_PROMPT = 12_000


def image_urls_from_issue_markdown(body: str, *, max_images: int = 8) -> list[str]:
    """Collect likely image URLs from GitHub issue body (markdown + user-images hosts)."""
    seen: set[str] = set()
    out: list[str] = []
    for m in _MARKDOWN_IMG.finditer(body or ""):
        u = m.group(1).strip()
        if u and u not in seen:
            seen.add(u)
            out.append(u)
            if len(out) >= max_images:
                return out
    for m in _RAW_USER_IMG.finditer(body or ""):
        u = m.group(0).rstrip(").,]")
        if u and u not in seen:
            seen.add(u)
            out.append(u)
            if len(out) >= max_images:
                break
    return out


def fallback_ticket_analysis(issue_title: str, issue_body: str) -> TicketAnalysis:
    """Static safe defaults when OpenRouter is unavailable or analysis JSON fails.

    ``issue_title`` / ``issue_body`` are accepted for a stable call shape and for
    future light heuristics (search terms, coarse task_type); not used yet.
    """
    return TicketAnalysis(
        feature_area="general",
        task_type="unknown",
        risk_surface="Review the issue, tests, and related modules before changing behavior.",
        suggested_search_terms=[],
        image_observations=None,
    )


async def _chat_json_model[T](
    messages: list,
    model: type[T],
    *,
    settings: Settings,
    temperature: float,
    repair_user_hint: str,
) -> T | None:
    try:
        raw = await chat_async(messages, temperature=temperature, settings=settings)
    except (OpenRouterConfigError, OpenRouterEmptyResponseError) as e:
        log.warning("OpenRouter call failed: %s", e)
        return None
    except Exception:
        log.exception("OpenRouter request failed")
        return None

    try:
        return parse_model_json(raw, model)
    except (json.JSONDecodeError, ValidationError) as e:
        log.warning("First JSON parse failed (%s); attempting repair pass", e)
        try:
            repair_msg = (
                f"{repair_user_hint}\n\n"
                f"Previous output was invalid JSON for the schema. Error: {e}\n\n"
                f"Broken output (fix and reply with ONLY corrected JSON):\n{raw[:6000]}"
            )
            raw2 = await chat_async(
                [
                    {"role": "system", "content": _SYSTEM_JSON},
                    {"role": "user", "content": repair_msg},
                ],
                temperature=0.1,
                settings=settings,
            )
            return parse_model_json(raw2, model)
        except Exception:
            log.exception("JSON repair pass failed")
            return None


async def run_ticket_analysis(
    *,
    issue_title: str,
    issue_body: str,
    tree_paths: list[str],
    settings: Settings,
) -> TicketAnalysis | None:
    """Step 2 — classify the ticket; optional vision URLs from issue body."""
    if not settings.openrouter_api_key:
        log.warning("Skipping ticket analysis: OPENROUTER_API_KEY not set")
        return None

    body = (issue_body or "").strip()
    if len(body) > MAX_BODY_IN_PROMPT:
        body = body[: MAX_BODY_IN_PROMPT - 20] + "\n…[truncated]"

    paths = tree_paths[:MAX_TREE_FOR_ANALYSIS]
    tree_block = "\n".join(paths) if paths else "(no paths)"

    text = f"""Analyze this GitHub issue for an engineer onboarding to the repo.

## Title
{issue_title.strip() or "(empty)"}

## Body
{body or "(empty)"}

## Sample repository paths (from API tree; not exhaustive)
{tree_block}

Return JSON with exactly these keys:
- "feature_area": string — product or code area
- "task_type": string — e.g. bugfix, feature, refactor, docs, test
- "risk_surface": string — what could break or needs care
- "suggested_search_terms": array of strings — extra keywords for search
- "image_observations": string or null — if images are attached, what they show; else null

JSON only."""

    image_urls = image_urls_from_issue_markdown(issue_body)
    user_msg = user_message_multimodal(text, image_urls)
    messages: list = [
        {"role": "system", "content": _SYSTEM_JSON},
        user_msg,
    ]

    return await _chat_json_model(
        messages,
        TicketAnalysis,
        settings=settings,
        temperature=0.2,
        repair_user_hint="The schema is TicketAnalysis: feature_area, task_type, risk_surface, suggested_search_terms, image_observations.",
    )


async def run_onboarding_map(
    *,
    analysis: TicketAnalysis,
    augment: AugmentRelevanceResult | None,
    memory_snippets: list[str],
    issue_title: str,
    issue_body: str,
    tree_paths: list[str],
    settings: Settings,
) -> OnboardingMap | None:
    """Step 5 — dashboard-oriented map (files, warnings, mermaid)."""
    if not settings.openrouter_api_key:
        log.warning("Skipping onboarding map: OPENROUTER_API_KEY not set")
        return None

    body = (issue_body or "").strip()
    if len(body) > MAX_BODY_IN_PROMPT:
        body = body[: MAX_BODY_IN_PROMPT - 20] + "\n…[truncated]"

    tree_block = "\n".join(tree_paths[:MAX_TREE_FOR_MAP]) if tree_paths else "(no paths)"
    analysis_json = analysis.model_dump_json()
    augment_json = (
        augment.model_dump_json()
        if augment is not None
        else '{"relevant_files":[],"dependency_notes":[]}'
    )
    memory_block = (
        "\n".join(f"- {s}" for s in memory_snippets)
        if memory_snippets
        else "(no team memory entries yet)"
    )

    user_text = f"""Build an onboarding map for this issue. Output JSON only for the dashboard.

## Issue title
{issue_title.strip() or "(empty)"}

## Issue body (may be truncated)
{body or "(empty)"}

## Ticket analysis (JSON)
{analysis_json}

## Augment / codebase relevance (JSON from a repo-aware agent)
{augment_json}

## Team memory hints
{memory_block}

## Sample tree paths
{tree_block}

Return JSON with exactly:
- "files_to_read": array of {{"path": "repo-relative path", "summary": "one line why read this file, order matters"}}
- "warnings": array of short strings — gotchas, ordering, deprecated areas
- "mermaid": string — a valid Mermaid flowchart (e.g. graph TD or flowchart LR). **Labels with parentheses must be double-quoted**, e.g. `A["app.handle()"]` not `A[app.handle()]` (unquoted parens break the parser). Same for diamond nodes with special characters when needed. Can be empty string if not applicable.

JSON only."""

    messages = [
        {"role": "system", "content": _SYSTEM_JSON},
        {"role": "user", "content": user_text},
    ]

    return await _chat_json_model(
        messages,
        OnboardingMap,
        settings=settings,
        temperature=0.3,
        repair_user_hint="The schema is OnboardingMap: files_to_read (array of path+summary), warnings (array of strings), mermaid (string).",
    )
