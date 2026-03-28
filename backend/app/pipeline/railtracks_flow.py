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


# Railtracks may pass deep copies into each node, so in-place mutations on one call are not
# visible to the next. Return `state` from every step and assign `state = await rt.call(...)`.


@rt.function_node
async def rt_step_pat(state: SlopePipelineState) -> SlopePipelineState:
    await step_pat(state)
    return state


@rt.function_node
async def rt_step_ingest(state: SlopePipelineState) -> SlopePipelineState:
    await step_ingest(state)
    return state


@rt.function_node
async def rt_step_resolve_issue_text(state: SlopePipelineState) -> SlopePipelineState:
    await step_resolve_issue_text(state)
    return state


@rt.function_node
async def rt_step_ticket_analysis(state: SlopePipelineState) -> SlopePipelineState:
    await step_ticket_analysis(state)
    return state


@rt.function_node
async def rt_step_augment(state: SlopePipelineState) -> SlopePipelineState:
    await step_augment(state)
    return state


@rt.function_node
async def rt_step_memory_recall(state: SlopePipelineState) -> SlopePipelineState:
    await step_memory_recall(state)
    return state


@rt.function_node
async def rt_step_onboarding_map(state: SlopePipelineState) -> SlopePipelineState:
    await step_onboarding_map(state)
    return state


@rt.function_node
async def rt_step_memory_write(state: SlopePipelineState) -> SlopePipelineState:
    await step_memory_write(state)
    return state


@rt.function_node
async def rt_step_save_run(state: SlopePipelineState) -> SlopePipelineState:
    await step_save_run(state)
    return state


@rt.function_node
async def rt_step_github_comment(state: SlopePipelineState) -> SlopePipelineState:
    await step_github_comment(state)
    return state


@rt.function_node
async def rt_slope_assigned_issue_entry(state: SlopePipelineState) -> None:
    state = await rt.call(rt_step_pat, state)
    if state.aborted:
        return
    state = await rt.call(rt_step_ingest, state)
    if state.aborted:
        return
    state = await rt.call(rt_step_resolve_issue_text, state)
    state = await rt.call(rt_step_ticket_analysis, state)
    state = await rt.call(rt_step_augment, state)
    state = await rt.call(rt_step_memory_recall, state)
    state = await rt.call(rt_step_onboarding_map, state)
    state = await rt.call(rt_step_memory_write, state)
    state = await rt.call(rt_step_save_run, state)
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
