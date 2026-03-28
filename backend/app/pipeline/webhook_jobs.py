import logging

from app.config import get_settings
from app.services import augment_relevance as augment_relevance_svc
from app.services import github_api
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
