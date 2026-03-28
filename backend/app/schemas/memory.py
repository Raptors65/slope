"""Phase 6 — durable team memory entries (JSON file v1)."""

from pydantic import BaseModel, Field


class MemoryEntry(BaseModel):
    owner: str
    repo: str
    area: str = Field(description="Feature area / bucket from ticket analysis when stored.")
    lesson: str = Field(description="Short team note derived from a completed map run.")
    issue_number: int
    created_at: str = Field(description="ISO-8601 UTC timestamp.")
    tags: list[str] = Field(default_factory=list)


class MemoryStoreFile(BaseModel):
    version: int = 1
    entries: list[MemoryEntry] = Field(default_factory=list)
