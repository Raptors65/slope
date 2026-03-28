import logging

log = logging.getLogger("slope.pipeline")


async def run_assigned_issue_stub(owner: str, repo: str, issue_number: int) -> None:
    """Placeholder until ingestion + LLM + delivery are wired (Phases 3–8)."""
    log.info(
        "Pipeline stub (queued): %s/%s issue #%s — replace with real pipeline",
        owner,
        repo,
        issue_number,
    )
