from pydantic import BaseModel, Field


class FileSnippet(BaseModel):
    path: str
    content: str = Field(description="UTF-8 text, possibly truncated")
    size_bytes: int = Field(description="Decoded byte length before truncation")


class RepoIngestion(BaseModel):
    owner: str
    repo: str
    default_branch: str
    tree_paths: list[str] = Field(default_factory=list)
    tree_truncated: bool = False
    readme_text: str | None = None
    snippets: list[FileSnippet] = Field(default_factory=list)
