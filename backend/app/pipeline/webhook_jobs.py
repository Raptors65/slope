import logging

from app.config import get_settings
from app.services.repo_ingestion import ingest_repository

log = logging.getLogger("slope.pipeline")


async def run_assigned_issue_pipeline(
    owner: str,
    repo: str,
    issue_number: int,
    *,
    default_branch: str | None = None,
) -> None:
    """Phase 3: ingest repo snapshot; later phases add LLM + issue comment."""
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
