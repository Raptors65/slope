"""Request/response shapes for the GitHub webhook (OpenAPI + runtime)."""

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class WebhookSkipReason(StrEnum):
    """Machine-readable reason when the webhook is acknowledged but no pipeline runs."""

    EVENT_NOT_ISSUES = "event_not_issues"
    ACTION_NOT_ASSIGNED = "action_not_assigned"
    INVALID_PAYLOAD = "invalid_payload"
    ALREADY_COMMENTED = "already_commented"


class WebhookAcceptedStatus(StrEnum):
    ACCEPTED = "accepted"


class WebhookErrorDetail(StrEnum):
    """Stable `detail` strings for HTTP errors from this route (matches response body)."""

    WEBHOOK_SECRET_NOT_CONFIGURED = "webhook secret not configured"
    INVALID_SIGNATURE = "invalid signature"
    INVALID_JSON = "invalid json"
    GITHUB_PAT_NOT_CONFIGURED = "github pat not configured"
    GITHUB_API_ERROR_LISTING_COMMENTS = "github api error listing comments"
    GITHUB_REQUEST_FAILED = "github request failed"


class GitHubEventType(StrEnum):
    """Subset of `X-GitHub-Event` values this handler cares about."""

    ISSUES = "issues"


class IssuesWebhookAction(StrEnum):
    """Subset of `action` on `issues` webhooks we branch on."""

    ASSIGNED = "assigned"


class WebhookSkippedBody(BaseModel):
    """GitHub call acknowledged but no pipeline run (wrong event, idempotency, etc.)."""

    skipped: Literal[True] = True
    reason: WebhookSkipReason = Field(
        description="Why the event was skipped (stable API contract)."
    )


class WebhookAcceptedBody(BaseModel):
    """Pipeline queued for asynchronous processing."""

    status: WebhookAcceptedStatus = WebhookAcceptedStatus.ACCEPTED
    repository: str = Field(description='Repository full name "owner/repo".')
    issue: int = Field(description="Issue number on that repository.")

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "status": WebhookAcceptedStatus.ACCEPTED.value,
                    "repository": "octocat/Hello-World",
                    "issue": 42,
                }
            ]
        }
    )


class HttpErrorBody(BaseModel):
    """Standard FastAPI / Starlette HTTP error payload for this route."""

    detail: WebhookErrorDetail
