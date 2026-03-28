"""Structured output from Augment (Auggie) relevance pass — Step 3."""

from typing import Any

from pydantic import BaseModel, Field, field_validator


class AugmentRelevantFile(BaseModel):
    path: str = Field(description="Repo-relative path the engineer should inspect.")
    reason: str = Field(description="One line: why this file matters for the ticket.")


class AugmentRelevanceResult(BaseModel):
    """Result of the focused codebase task (return_type for Auggie.run)."""

    relevant_files: list[AugmentRelevantFile] = Field(
        default_factory=list,
        description="5–10 most relevant files for this issue, most important first.",
    )
    dependency_notes: list[str] = Field(
        default_factory=list,
        description="Verified import/call relationships or flow between modules.",
    )

    @field_validator("dependency_notes", mode="before")
    @classmethod
    def _coerce_dependency_notes(cls, v: Any) -> list[str]:
        """Models often emit a mapping (label → note) instead of a list of strings."""
        if v is None:
            return []
        if isinstance(v, list):
            return [str(x).strip() for x in v if str(x).strip()]
        if isinstance(v, dict):
            out: list[str] = []
            for key, val in v.items():
                ks, vs = str(key).strip(), str(val).strip()
                if not vs:
                    continue
                out.append(f"{ks}: {vs}" if ks else vs)
            return out
        s = str(v).strip()
        return [s] if s else []
