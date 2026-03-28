import json
import logging
from dataclasses import dataclass
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.pipeline.webhook_jobs import run_assigned_issue_pipeline
from app.schemas.github_webhook import (
    GitHubEventType,
    HttpErrorBody,
    IssuesWebhookAction,
    WebhookAcceptedBody,
    WebhookErrorDetail,
    WebhookSkippedBody,
    WebhookSkipReason,
)
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
    issue_title: str = ""
    issue_body: str = ""


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
    title = issue.get("title")
    body = issue.get("body")
    return AssignedIssueRef(
        owner=o,
        repo=name,
        issue_number=num,
        default_branch=default_branch,
        issue_title=str(title or ""),
        issue_body=str(body or ""),
    )


@router.post(
    "/github/webhook",
    summary="GitHub repository webhook",
    description=(
        "Receives GitHub `issues` webhooks. Only `action=assigned` may queue the "
        "onboarding pipeline. Validates `X-Hub-Signature-256` when a webhook secret is set."
    ),
    response_model=None,
    responses={
        status.HTTP_200_OK: {
            "model": WebhookSkippedBody,
            "description": "Ignored event or idempotent skip (no pipeline run).",
        },
        status.HTTP_202_ACCEPTED: {
            "model": WebhookAcceptedBody,
            "description": "Pipeline accepted; work continues asynchronously.",
        },
        status.HTTP_400_BAD_REQUEST: {
            "model": HttpErrorBody,
            "description": "Malformed JSON body.",
        },
        status.HTTP_401_UNAUTHORIZED: {
            "model": HttpErrorBody,
            "description": "Invalid or missing webhook signature.",
        },
        status.HTTP_502_BAD_GATEWAY: {
            "model": HttpErrorBody,
            "description": "Upstream GitHub API error while listing issue comments.",
        },
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "model": HttpErrorBody,
            "description": "Server missing `GITHUB_WEBHOOK_SECRET` or `GITHUB_PAT`.",
        },
    },
)
async def github_webhook(request: Request) -> JSONResponse:
    settings = get_settings()
    body = await request.body()

    if not settings.github_webhook_secret:
        log.error("GITHUB_WEBHOOK_SECRET is not set")
        raise HTTPException(
            status_code=503,
            detail=WebhookErrorDetail.WEBHOOK_SECRET_NOT_CONFIGURED,
        )

    sig = request.headers.get("x-hub-signature-256")
    if not verify_github_webhook_signature(
        body, sig, settings.github_webhook_secret
    ):
        raise HTTPException(
            status_code=401, detail=WebhookErrorDetail.INVALID_SIGNATURE
        )

    event = request.headers.get("x-github-event")
    if event != GitHubEventType.ISSUES:
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=WebhookSkippedBody(
                reason=WebhookSkipReason.EVENT_NOT_ISSUES
            ).model_dump(mode="json"),
        )

    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=400, detail=WebhookErrorDetail.INVALID_JSON
        ) from None

    if payload.get("action") != IssuesWebhookAction.ASSIGNED:
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=WebhookSkippedBody(
                reason=WebhookSkipReason.ACTION_NOT_ASSIGNED
            ).model_dump(mode="json"),
        )

    ref = _parse_assigned_issue(payload)
    if not ref:
        log.warning("assigned payload missing repository.full_name or issue.number")
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=WebhookSkippedBody(
                reason=WebhookSkipReason.INVALID_PAYLOAD
            ).model_dump(mode="json"),
        )

    if not settings.github_pat:
        log.error("GITHUB_PAT is not set; cannot check idempotency or call GitHub API")
        raise HTTPException(
            status_code=503, detail=WebhookErrorDetail.GITHUB_PAT_NOT_CONFIGURED
        )

    try:
        already = await issue_comments_contain_marker(
            ref.owner, ref.repo, ref.issue_number, settings.github_pat
        )
    except httpx.HTTPStatusError as e:
        log.exception("GitHub API error listing comments: %s", e)
        raise HTTPException(
            status_code=502,
            detail=WebhookErrorDetail.GITHUB_API_ERROR_LISTING_COMMENTS,
        ) from e
    except httpx.RequestError as e:
        log.exception("GitHub request failed: %s", e)
        raise HTTPException(
            status_code=502, detail=WebhookErrorDetail.GITHUB_REQUEST_FAILED
        ) from e

    if already:
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=WebhookSkippedBody(
                reason=WebhookSkipReason.ALREADY_COMMENTED
            ).model_dump(mode="json"),
        )

    async def _job() -> None:
        await run_assigned_issue_pipeline(
            ref.owner,
            ref.repo,
            ref.issue_number,
            default_branch=ref.default_branch,
            issue_title=ref.issue_title,
            issue_body=ref.issue_body,
        )

    spawn_background(_job())

    return JSONResponse(
        status_code=status.HTTP_202_ACCEPTED,
        content=WebhookAcceptedBody(
            repository=f"{ref.owner}/{ref.repo}",
            issue=ref.issue_number,
        ).model_dump(mode="json"),
    )
