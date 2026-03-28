import logging

from app.config import get_settings
from app.services import augment_relevance as augment_relevance_svc
from app.services import github_api
from app.services import onboarding_llm as onboarding_llm_svc
from app.services.repo_ingestion import ingest_repository

log = logging.getLogger("slope.pipeline")


async def run_assigned_issue_pipeline(
    owner: str,
    repo: str,
    issue_number: int,
    *,
    default_branch: str | None = None,
    issue_title: str = "",
    issue_body: str = "",
) -> None:
    """Ingest repo (Phase 3), Augment relevance on a shallow clone (Phase 5); later LLM + comment."""
    settings = get_settings()
    pat = settings.github_pat
    if not pat:
        log.error("No GITHUB_PAT; skipping pipeline for %s/%s#%s", owner, repo, issue_number)
        return

    try:
        ingestion = await ingest_repository(
            owner, repo, pat, default_branch_hint=default_branch
        )
    except Exception:
        log.exception(
            "Ingestion failed for %s/%s issue #%s", owner, repo, issue_number
        )
        return

    log.info(
        "Ingested %s/%s (issue #%s): branch=%s paths=%d tree_truncated=%s "
        "readme_chars=%d snippets=%d",
        owner,
        repo,
        issue_number,
        ingestion.default_branch,
        len(ingestion.tree_paths),
        ingestion.tree_truncated,
        len(ingestion.readme_text or ""),
        len(ingestion.snippets),
    )

    title = issue_title.strip()
    body = issue_body.strip()
    if not title and not body:
        try:
            title, body = await github_api.fetch_issue(owner, repo, issue_number, pat)
        except Exception:
            log.exception(
                "Could not fetch issue %s/%s#%s for Augment context",
                owner,
                repo,
                issue_number,
            )
            title, body = "", ""

    readme_excerpt = (ingestion.readme_text or "")[:8000]

    analysis_llm = await onboarding_llm_svc.run_ticket_analysis(
        issue_title=title,
        issue_body=body,
        tree_paths=ingestion.tree_paths,
        settings=settings,
    )
    analysis = (
        analysis_llm
        if analysis_llm is not None
        else onboarding_llm_svc.fallback_ticket_analysis(title, body)
    )
    log.info(
        "Ticket analysis %s/%s#%s: source=%s area=%s type=%s terms=%d",
        owner,
        repo,
        issue_number,
        "openrouter" if analysis_llm is not None else "fallback",
        (analysis.feature_area or "")[:120],
        analysis.task_type,
        len(analysis.suggested_search_terms),
    )
    analysis_json = analysis.model_dump_json()

    augment_result = await augment_relevance_svc.run_augment_relevance(
        owner,
        repo,
        pat,
        default_branch=ingestion.default_branch,
        issue_title=title,
        issue_body=body,
        tree_paths=ingestion.tree_paths,
        readme_excerpt=readme_excerpt,
        settings=settings,
        ticket_analysis_json=analysis_json,
    )
    if augment_result is None:
        log.warning(
            "Augment step skipped or failed for %s/%s#%s", owner, repo, issue_number
        )
    else:
        log.info(
            "Augment relevance %s/%s#%s: files=%d notes=%d",
            owner,
            repo,
            issue_number,
            len(augment_result.relevant_files),
            len(augment_result.dependency_notes),
        )
        for i, f in enumerate(augment_result.relevant_files[:10], start=1):
            log.debug("  %d. %s — %s", i, f.path, f.reason[:120])

    onboarding_map = await onboarding_llm_svc.run_onboarding_map(
        analysis=analysis,
        augment=augment_result,
        memory_snippets=[],
        issue_title=title,
        issue_body=body,
        tree_paths=ingestion.tree_paths,
        settings=settings,
    )
    if onboarding_map is None:
        log.warning(
            "Onboarding map skipped or failed for %s/%s#%s", owner, repo, issue_number
        )
    else:
        log.info(
            "Onboarding map %s/%s#%s: files=%d warnings=%d mermaid_chars=%d",
            owner,
            repo,
            issue_number,
            len(onboarding_map.files_to_read),
            len(onboarding_map.warnings),
            len(onboarding_map.mermaid or ""),
        )
