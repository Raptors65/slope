"""Structured LLM outputs (ticket analysis, onboarding map) for Phase 4+ pipeline."""

from pydantic import BaseModel, Field


class TicketAnalysis(BaseModel):
    """Step 2 — ticket understanding from issue text, tree summary, optional images."""

    feature_area: str = Field(description="Product or code area this ticket belongs to.")
    task_type: str = Field(
        description="Kind of work, e.g. bugfix, feature, refactor, docs, test."
    )
    risk_surface: str = Field(
        description="What could break or what to be careful about at a high level."
    )
    suggested_search_terms: list[str] = Field(
        default_factory=list,
        description="Extra keywords for codebase / memory lookup.",
    )
    image_observations: str | None = Field(
        default=None,
        description="If images were provided: what they show and how it relates to the ticket.",
    )


class MapFileEntry(BaseModel):
    path: str
    summary: str = Field(description="One line: why this file matters for the ticket.")


class OnboardingMap(BaseModel):
    """Step 5 — dashboard payload: reading order, warnings, Mermaid graph."""

    files_to_read: list[MapFileEntry] = Field(
        default_factory=list,
        description="Files in the order the engineer should read them.",
    )
    warnings: list[str] = Field(
        default_factory=list,
        description='"Watch out" bullets derived from memory + analysis.',
    )
    mermaid: str = Field(
        default="",
        description="Mermaid flowchart; file nodes should use repo-relative path labels (quoted if needed).",
    )
