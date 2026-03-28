"""Sequential assigned-issue pipeline (shared by direct run and Railtracks flow)."""

from __future__ import annotations

import logging

from app.config import Settings, get_settings
from app.pipeline.pipeline_state import SlopePipelineState
from app.services import augment_relevance as augment_relevance_svc
from app.services import github_api
from app.services import onboarding_llm as onboarding_llm_svc
from app.services import runs_store as runs_store_svc
from app.services import team_memory as team_memory_svc
from app.services.repo_ingestion import ingest_repository

log = logging.getLogger("slope.pipeline")


async def step_pat(state: SlopePipelineState) -> None:
    pat = state.settings.github_pat
    if not pat:
        log.error(
            "No GITHUB_PAT; skipping pipeline for %s/%s#%s",
            state.owner,
            state.repo,
            state.issue_number,
        )
        state.aborted = "no_pat"
        return
    state.pat = pat


async def step_ingest(state: SlopePipelineState) -> None:
    assert state.pat is not None
    try:
        state.ingestion = await ingest_repository(
            state.owner,
            state.repo,
            state.pat,
            default_branch_hint=state.default_branch,
        )
    except Exception:
        log.exception(
            "Ingestion failed for %s/%s issue #%s",
            state.owner,
            state.repo,
            state.issue_number,
        )
        state.aborted = "ingest_failed"
        return

    ing = state.ingestion
    log.info(
        "Ingested %s/%s (issue #%s): branch=%s paths=%d tree_truncated=%s "
        "readme_chars=%d snippets=%d",
        state.owner,
        state.repo,
        state.issue_number,
        ing.default_branch,
        len(ing.tree_paths),
        ing.tree_truncated,
        len(ing.readme_text or ""),
        len(ing.snippets),
    )


async def step_resolve_issue_text(state: SlopePipelineState) -> None:
    assert state.pat is not None and state.ingestion is not None
    title = state.issue_title.strip()
    body = state.issue_body.strip()
    if not title and not body:
        try:
            title, body = await github_api.fetch_issue(
                state.owner, state.repo, state.issue_number, state.pat
            )
        except Exception:
            log.exception(
                "Could not fetch issue %s/%s#%s for Augment context",
                state.owner,
                state.repo,
                state.issue_number,
            )
            title, body = "", ""
    state.title = title
    state.body = body


async def step_ticket_analysis(state: SlopePipelineState) -> None:
    assert state.ingestion is not None
    settings = state.settings
    analysis_llm = await onboarding_llm_svc.run_ticket_analysis(
        issue_title=state.title,
        issue_body=state.body,
        tree_paths=state.ingestion.tree_paths,
        settings=settings,
    )
    analysis = (
        analysis_llm
        if analysis_llm is not None
        else onboarding_llm_svc.fallback_ticket_analysis(state.title, state.body)
    )
    state.analysis = analysis
    state.analysis_llm_used = analysis_llm is not None
    state.analysis_json = analysis.model_dump_json()
    log.info(
        "Ticket analysis %s/%s#%s: source=%s area=%s type=%s terms=%d",
        state.owner,
        state.repo,
        state.issue_number,
        "openrouter" if analysis_llm is not None else "fallback",
        (analysis.feature_area or "")[:120],
        analysis.task_type,
        len(analysis.suggested_search_terms),
    )


async def step_augment(state: SlopePipelineState) -> None:
    assert state.pat is not None and state.ingestion is not None
    readme_excerpt = (state.ingestion.readme_text or "")[:8000]
    augment_result = await augment_relevance_svc.run_augment_relevance(
        state.owner,
        state.repo,
        state.pat,
        default_branch=state.ingestion.default_branch,
        issue_title=state.title,
        issue_body=state.body,
        tree_paths=state.ingestion.tree_paths,
        readme_excerpt=readme_excerpt,
        settings=state.settings,
        ticket_analysis_json=state.analysis_json,
    )
    state.augment_result = augment_result
    if augment_result is None:
        log.warning(
            "Augment step skipped or failed for %s/%s#%s",
            state.owner,
            state.repo,
            state.issue_number,
        )
    else:
        log.info(
            "Augment relevance %s/%s#%s: files=%d notes=%d",
            state.owner,
            state.repo,
            state.issue_number,
            len(augment_result.relevant_files),
            len(augment_result.dependency_notes),
        )
        for i, f in enumerate(augment_result.relevant_files[:10], start=1):
            log.debug("  %d. %s — %s", i, f.path, f.reason[:120])


async def step_memory_recall(state: SlopePipelineState) -> None:
    assert state.analysis is not None
    snippets = await team_memory_svc.recall_snippets(
        state.owner,
        state.repo,
        feature_area=state.analysis.feature_area,
        search_terms=state.analysis.suggested_search_terms,
        settings=state.settings,
    )
    state.memory_snippets = snippets
    log.info(
        "Memory recall %s/%s#%s: snippets=%d",
        state.owner,
        state.repo,
        state.issue_number,
        len(snippets),
    )


async def step_onboarding_map(state: SlopePipelineState) -> None:
    assert state.analysis is not None and state.ingestion is not None
    omap = await onboarding_llm_svc.run_onboarding_map(
        analysis=state.analysis,
        augment=state.augment_result,
        memory_snippets=state.memory_snippets,
        issue_title=state.title,
        issue_body=state.body,
        tree_paths=state.ingestion.tree_paths,
        settings=state.settings,
    )
    state.onboarding_map = omap
    if omap is None:
        log.warning(
            "Onboarding map skipped or failed for %s/%s#%s",
            state.owner,
            state.repo,
            state.issue_number,
        )
    else:
        log.info(
            "Onboarding map %s/%s#%s: files=%d warnings=%d mermaid_chars=%d",
            state.owner,
            state.repo,
            state.issue_number,
            len(omap.files_to_read),
            len(omap.warnings),
            len(omap.mermaid or ""),
        )


async def step_memory_write(state: SlopePipelineState) -> None:
    if state.onboarding_map is None or state.analysis is None:
        return
    assert state.pat is not None
    try:
        await team_memory_svc.remember_from_run(
            state.owner,
            state.repo,
            state.issue_number,
            issue_title=state.title,
            analysis=state.analysis,
            omap=state.onboarding_map,
            settings=state.settings,
        )
    except Exception:
        log.exception(
            "Memory write failed for %s/%s#%s (map was produced)",
            state.owner,
            state.repo,
            state.issue_number,
        )


async def step_save_run(state: SlopePipelineState) -> None:
    assert state.analysis is not None and state.ingestion is not None
    state.image_urls = onboarding_llm_svc.image_urls_from_issue_markdown(state.body)
    run_record = runs_store_svc.build_run_record(
        owner=state.owner,
        repo=state.repo,
        issue_number=state.issue_number,
        issue_title=state.title,
        issue_body=state.body,
        default_branch=state.ingestion.default_branch,
        analysis=state.analysis,
        augment_result=state.augment_result,
        onboarding_map=state.onboarding_map,
        memory_snippets=state.memory_snippets,
        image_urls=state.image_urls,
    )
    try:
        run_id = await runs_store_svc.save_run(run_record, settings=state.settings)
        state.run_id = run_id
        log.info(
            "Saved onboarding run %s for %s/%s#%s",
            run_id,
            state.owner,
            state.repo,
            state.issue_number,
        )
    except Exception:
        log.exception(
            "Failed to persist onboarding run for %s/%s#%s",
            state.owner,
            state.repo,
            state.issue_number,
        )
        state.aborted = "save_failed"


async def step_github_comment(state: SlopePipelineState) -> None:
    if state.onboarding_map is None or state.run_id is None:
        return
    assert state.pat is not None
    comment_body = github_api.format_onboarding_map_comment_body(
        dashboard_base_url=state.settings.dashboard_base_url,
        run_id=state.run_id,
    )
    try:
        await github_api.post_issue_comment(
            state.owner,
            state.repo,
            state.issue_number,
            state.pat,
            body=comment_body,
        )
        log.info(
            "Posted onboarding map comment on %s/%s#%s (run %s)",
            state.owner,
            state.repo,
            state.issue_number,
            state.run_id,
        )
    except Exception:
        log.exception(
            "Failed to post GitHub comment for %s/%s#%s (run %s saved)",
            state.owner,
            state.repo,
            state.issue_number,
            state.run_id,
        )


async def run_pipeline_sequence(state: SlopePipelineState) -> None:
    """Run all steps in order (direct path, no Railtracks)."""
    await step_pat(state)
    if state.aborted:
        return
    await step_ingest(state)
    if state.aborted:
        return
    await step_resolve_issue_text(state)
    await step_ticket_analysis(state)
    await step_augment(state)
    await step_memory_recall(state)
    await step_onboarding_map(state)
    await step_memory_write(state)
    await step_save_run(state)
    if state.aborted:
        return
    await step_github_comment(state)


async def run_assigned_issue_pipeline_core(
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
    await run_pipeline_sequence(state)
