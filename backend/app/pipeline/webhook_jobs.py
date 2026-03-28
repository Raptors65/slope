import logging

from app.config import get_settings
from app.pipeline.assigned_issue_core import run_assigned_issue_pipeline_core

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
    """Ingest → analysis → Augment → memory → map → persist → GitHub comment."""
    settings = get_settings()
    if settings.use_railtracks:
        from app.pipeline.railtracks_flow import run_assigned_issue_via_railtracks

        await run_assigned_issue_via_railtracks(
            owner,
            repo,
            issue_number,
            default_branch=default_branch,
            issue_title=issue_title,
            issue_body=issue_body,
            settings=settings,
        )
        return

    await run_assigned_issue_pipeline_core(
        owner,
        repo,
        issue_number,
        default_branch=default_branch,
        issue_title=issue_title,
        issue_body=issue_body,
        settings=settings,
    )
