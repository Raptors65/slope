import json
import logging
from dataclasses import dataclass
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException, Request, Response

from app.config import get_settings
from app.pipeline.webhook_jobs import run_assigned_issue_pipeline
from app.services.github_api import issue_comments_contain_marker
from app.services.github_signature import verify_github_webhook_signature
from app.tasks import spawn_background

log = logging.getLogger("slope.github.webhook")

router = APIRouter(tags=["github"])


@dataclass(frozen=True)
class AssignedIssueRef:
    owner: str
    repo: str
    issue_number: int
    default_branch: str | None = None


def _parse_assigned_issue(payload: dict[str, Any]) -> AssignedIssueRef | None:
    repo_obj = payload.get("repository") or {}
    full_name = repo_obj.get("full_name")
    if not full_name or "/" not in full_name:
        return None
    o, name = full_name.split("/", 1)
    issue = payload.get("issue") or {}
    num = issue.get("number")
    if not isinstance(num, int):
        return None
    db = repo_obj.get("default_branch")
    default_branch = db if isinstance(db, str) and db.strip() else None
    return AssignedIssueRef(
        owner=o, repo=name, issue_number=num, default_branch=default_branch
    )


@router.post("/github/webhook")
async def github_webhook(request: Request) -> Response:
    settings = get_settings()
    body = await request.body()

    if not settings.github_webhook_secret:
        log.error("GITHUB_WEBHOOK_SECRET is not set")
        raise HTTPException(status_code=503, detail="webhook secret not configured")

    sig = request.headers.get("x-hub-signature-256")
    if not verify_github_webhook_signature(
        body, sig, settings.github_webhook_secret
    ):
        raise HTTPException(status_code=401, detail="invalid signature")

    event = request.headers.get("x-github-event")
    if event != "issues":
        return Response(
            status_code=200,
            media_type="application/json",
            content=json.dumps({"skipped": True, "reason": "event_not_issues"}),
        )

    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="invalid json") from None

    if payload.get("action") != "assigned":
        return Response(
            status_code=200,
            media_type="application/json",
            content=json.dumps({"skipped": True, "reason": "action_not_assigned"}),
        )

    ref = _parse_assigned_issue(payload)
    if not ref:
        log.warning("assigned payload missing repository.full_name or issue.number")
        return Response(
            status_code=200,
            media_type="application/json",
            content=json.dumps({"skipped": True, "reason": "invalid_payload"}),
        )

    if not settings.github_pat:
        log.error("GITHUB_PAT is not set; cannot check idempotency or call GitHub API")
        raise HTTPException(status_code=503, detail="github pat not configured")

    try:
        already = await issue_comments_contain_marker(
            ref.owner, ref.repo, ref.issue_number, settings.github_pat
        )
    except httpx.HTTPStatusError as e:
        log.exception("GitHub API error listing comments: %s", e)
        raise HTTPException(
            status_code=502, detail="github api error listing comments"
        ) from e
    except httpx.RequestError as e:
        log.exception("GitHub request failed: %s", e)
        raise HTTPException(
            status_code=502, detail="github request failed"
        ) from e

    if already:
        return Response(
            status_code=200,
            media_type="application/json",
            content=json.dumps({"skipped": True, "reason": "already_commented"}),
        )

    async def _job() -> None:
        await run_assigned_issue_pipeline(
            ref.owner,
            ref.repo,
            ref.issue_number,
            default_branch=ref.default_branch,
        )

    spawn_background(_job())

    return Response(
        status_code=202,
        media_type="application/json",
        content=json.dumps(
            {
                "status": "accepted",
                "repository": f"{ref.owner}/{ref.repo}",
                "issue": ref.issue_number,
            }
        ),
    )
