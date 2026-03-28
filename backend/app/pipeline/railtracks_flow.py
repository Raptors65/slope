"""Optional Railtracks-wrapped pipeline for observability (`railtracks viz`)."""

from __future__ import annotations

import logging

import railtracks as rt

from app.config import Settings, get_settings
from app.pipeline.assigned_issue_core import (
    step_augment,
    step_github_comment,
    step_ingest,
    step_memory_recall,
    step_memory_write,
    step_onboarding_map,
    step_pat,
    step_resolve_issue_text,
    step_save_run,
    step_ticket_analysis,
)
from app.pipeline.pipeline_state import SlopePipelineState

log = logging.getLogger("slope.pipeline.railtracks")


@rt.function_node
async def rt_step_pat(state: SlopePipelineState) -> None:
    await step_pat(state)


@rt.function_node
async def rt_step_ingest(state: SlopePipelineState) -> None:
    await step_ingest(state)


@rt.function_node
async def rt_step_resolve_issue_text(state: SlopePipelineState) -> None:
    await step_resolve_issue_text(state)


@rt.function_node
async def rt_step_ticket_analysis(state: SlopePipelineState) -> None:
    await step_ticket_analysis(state)


@rt.function_node
async def rt_step_augment(state: SlopePipelineState) -> None:
    await step_augment(state)


@rt.function_node
async def rt_step_memory_recall(state: SlopePipelineState) -> None:
    await step_memory_recall(state)


@rt.function_node
async def rt_step_onboarding_map(state: SlopePipelineState) -> None:
    await step_onboarding_map(state)


@rt.function_node
async def rt_step_memory_write(state: SlopePipelineState) -> None:
    await step_memory_write(state)


@rt.function_node
async def rt_step_save_run(state: SlopePipelineState) -> None:
    await step_save_run(state)


@rt.function_node
async def rt_step_github_comment(state: SlopePipelineState) -> None:
    await step_github_comment(state)


@rt.function_node
async def rt_slope_assigned_issue_entry(state: SlopePipelineState) -> None:
    await rt.call(rt_step_pat, state)
    if state.aborted:
        return
    await rt.call(rt_step_ingest, state)
    if state.aborted:
        return
    await rt.call(rt_step_resolve_issue_text, state)
    await rt.call(rt_step_ticket_analysis, state)
    await rt.call(rt_step_augment, state)
    await rt.call(rt_step_memory_recall, state)
    await rt.call(rt_step_onboarding_map, state)
    await rt.call(rt_step_memory_write, state)
    await rt.call(rt_step_save_run, state)
    if state.aborted:
        return
    await rt.call(rt_step_github_comment, state)


_SLOPE_ASSIGNED_ISSUE_FLOW = rt.Flow(
    name="slope-assigned-issue",
    entry_point=rt_slope_assigned_issue_entry,
    save_state=True,
    timeout=900.0,
)


async def run_assigned_issue_via_railtracks(
    owner: str,
    repo: str,
    issue_number: int,
    *,
    default_branch: str | None = None,
    issue_title: str = "",
    issue_body: str = "",
    settings: Settings | None = None,
) -> None:
    s = settings or get_settings()
    state = SlopePipelineState(
        owner=owner,
        repo=repo,
        issue_number=issue_number,
        default_branch=default_branch,
        issue_title=issue_title,
        issue_body=issue_body,
        settings=s,
    )
    log.info(
        "Running assigned-issue pipeline via Railtracks for %s/%s#%s",
        owner,
        repo,
        issue_number,
    )
    await _SLOPE_ASSIGNED_ISSUE_FLOW.ainvoke(state)
