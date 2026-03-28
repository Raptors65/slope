"""Mutable state for the assigned-issue onboarding pipeline (sequential + Railtracks)."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.config import Settings
from app.schemas.augment import AugmentRelevanceResult
from app.schemas.ingestion import RepoIngestion
from app.schemas.llm_outputs import OnboardingMap, TicketAnalysis


@dataclass
class SlopePipelineState:
    owner: str
    repo: str
    issue_number: int
    default_branch: str | None
    issue_title: str
    issue_body: str
    settings: Settings

    aborted: str | None = None
    pat: str | None = None
    ingestion: RepoIngestion | None = None
    title: str = ""
    body: str = ""
    analysis: TicketAnalysis | None = None
    analysis_llm_used: bool = False
    analysis_json: str = ""
    augment_result: AugmentRelevanceResult | None = None
    memory_snippets: list[str] = field(default_factory=list)
    onboarding_map: OnboardingMap | None = None
    image_urls: list[str] = field(default_factory=list)
    run_id: str | None = None
