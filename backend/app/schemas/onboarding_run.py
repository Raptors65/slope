"""Persisted onboarding pipeline run (Phase 8 / Phase 9 API)."""

from typing import Any

from pydantic import BaseModel, Field


class OnboardingRunRecord(BaseModel):
    """Full run payload for storage and `GET /runs/{id}`."""

    id: str
    created_at: str = Field(description="ISO-8601 UTC timestamp.")
    owner: str
    repo: str
    issue_number: int
    issue_title: str = ""
    issue_body: str = ""
    default_branch: str | None = None
    ticket_analysis: dict[str, Any]
    augment: dict[str, Any] | None = None
    onboarding_map: dict[str, Any] | None = None
    memory_snippets: list[str] = Field(default_factory=list)
    image_urls: list[str] = Field(default_factory=list)


class OnboardingRunSummary(BaseModel):
    """Row for `GET /runs`."""

    id: str
    created_at: str
    owner: str
    repo: str
    issue_number: int
    issue_title: str = ""
    map_ready: bool = Field(
        description="True when an onboarding map was produced (comment posted only in that case)."
    )
