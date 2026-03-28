"""Phase 3: fetch default branch, tree, README, and capped config snippets via GitHub API."""

from __future__ import annotations

import base64
import logging
from typing import Any
from urllib.parse import quote

import httpx

from app.schemas.ingestion import FileSnippet, RepoIngestion
from app.services.github_api import _headers

log = logging.getLogger("slope.ingestion")

GITHUB_API = "https://api.github.com"

# Tree caps (large monorepos)
MAX_TREE_PATHS = 500
IGNORE_PATH_PREFIXES = (
    "node_modules/",
    ".git/",
    "dist/",
    "build/",
    "__pycache__/",
    ".venv/",
    "vendor/",
    ".github/",
    "coverage/",
    "htmlcov/",
    ".next/",
    "target/",
)
IGNORE_BASENAMES = frozenset({".DS_Store", ".gitignore"})

README_MAX_CHARS = 12_000
SNIPPET_MAX_BYTES = 12_288
MAX_SNIPPET_FILES = 12

CONFIG_BASENAMES = frozenset(
    {
        "package.json",
        "pyproject.toml",
        "Dockerfile",
        "Cargo.toml",
        "go.mod",
        "tsconfig.json",
        "Makefile",
        "requirements.txt",
        "composer.json",
        "build.gradle",
        "pom.xml",
    }
)


def should_include_tree_path(path: str) -> bool:
    if not path or path in IGNORE_BASENAMES:
        return False
    base = path.rsplit("/", 1)[-1]
    if base in IGNORE_BASENAMES:
        return False
    if "__pycache__" in path.split("/"):
        return False
    for prefix in IGNORE_PATH_PREFIXES:
        if path == prefix.rstrip("/") or path.startswith(prefix):
            return False
    return True


def _encode_content_path(path: str) -> str:
    return "/".join(quote(seg, safe="") for seg in path.split("/"))


def _select_config_paths(tree_paths: list[str], limit: int) -> list[str]:
    matches = [
        p for p in tree_paths if p.split("/")[-1] in CONFIG_BASENAMES
    ]
    matches.sort(key=lambda p: (len(p.split("/")), p))
    return matches[:limit]


async def _get_json(
    client: httpx.AsyncClient,
    url: str,
    pat: str,
    *,
    params: dict[str, Any] | None = None,
    extra_headers: dict[str, str] | None = None,
) -> Any:
    h = {**_headers(pat), **(extra_headers or {})}
    r = await client.get(url, headers=h, params=params)
    r.raise_for_status()
    return r.json()


async def _fetch_repo_default_branch(
    client: httpx.AsyncClient, owner: str, repo: str, pat: str
) -> str:
    data = await _get_json(
        client, f"{GITHUB_API}/repos/{owner}/{repo}", pat
    )
    branch = data.get("default_branch")
    if not isinstance(branch, str) or not branch:
        raise ValueError("repository response missing default_branch")
    return branch


async def _fetch_tree_sha_for_branch(
    client: httpx.AsyncClient,
    owner: str,
    repo: str,
    branch: str,
    pat: str,
) -> str:
    data = await _get_json(
        client,
        f"{GITHUB_API}/repos/{owner}/{repo}/branches/{quote(branch, safe='')}",
        pat,
    )
    commit = data.get("commit") or {}
    inner = commit.get("commit") or {}
    tree = inner.get("tree") or {}
    sha = tree.get("sha")
    if not isinstance(sha, str):
        raise ValueError(f"could not resolve tree sha for branch {branch!r}")
    return sha


async def _fetch_recursive_tree_paths(
    client: httpx.AsyncClient,
    owner: str,
    repo: str,
    tree_sha: str,
    pat: str,
) -> tuple[list[str], bool]:
    data = await _get_json(
        client,
        f"{GITHUB_API}/repos/{owner}/{repo}/git/trees/{tree_sha}",
        pat,
        params={"recursive": "1"},
    )
    truncated = bool(data.get("truncated"))
    paths: list[str] = []
    for item in data.get("tree") or []:
        if item.get("type") != "blob":
            continue
        p = item.get("path")
        if isinstance(p, str) and should_include_tree_path(p):
            paths.append(p)
    paths.sort()
    if len(paths) > MAX_TREE_PATHS:
        paths = paths[:MAX_TREE_PATHS]
        truncated = True
    return paths, truncated


async def _fetch_readme_text(
    client: httpx.AsyncClient, owner: str, repo: str, pat: str
) -> str | None:
    r = await client.get(
        f"{GITHUB_API}/repos/{owner}/{repo}/readme",
        headers={
            **_headers(pat),
            "Accept": "application/vnd.github.raw",
        },
        follow_redirects=True,
    )
    if r.status_code == 404:
        return None
    r.raise_for_status()
    text = r.text
    if len(text) > README_MAX_CHARS:
        return text[:README_MAX_CHARS] + "\n…"
    return text


async def _fetch_file_snippet(
    client: httpx.AsyncClient,
    owner: str,
    repo: str,
    path: str,
    ref: str,
    pat: str,
) -> FileSnippet | None:
    enc = _encode_content_path(path)
    r = await client.get(
        f"{GITHUB_API}/repos/{owner}/{repo}/contents/{enc}",
        headers=_headers(pat),
        params={"ref": ref},
    )
    if r.status_code == 404:
        return None
    r.raise_for_status()
    data = r.json()
    if isinstance(data, list):
        return None
    if data.get("type") != "file":
        return None
    raw_b64 = data.get("content")
    if not isinstance(raw_b64, str):
        return None
    raw = base64.b64decode(raw_b64.replace("\n", ""))
    size_bytes = len(raw)
    text = raw.decode("utf-8", errors="replace")
    if len(text.encode("utf-8")) > SNIPPET_MAX_BYTES:
        # truncate by bytes approximately via UTF-8 prefix
        cut = raw[:SNIPPET_MAX_BYTES].decode("utf-8", errors="ignore")
        text = cut + "\n…"
    return FileSnippet(path=path, content=text, size_bytes=size_bytes)


async def ingest_repository(
    owner: str,
    repo: str,
    pat: str,
    *,
    default_branch_hint: str | None = None,
    client: httpx.AsyncClient | None = None,
) -> RepoIngestion:
    """
    Build a compact snapshot for LLM prompts: branch, capped tree paths, README, config snippets.
    """
    close_client = False
    if client is None:
        client = httpx.AsyncClient(timeout=60.0)
        close_client = True

    try:
        if default_branch_hint and default_branch_hint.strip():
            branch = default_branch_hint.strip()
        else:
            branch = await _fetch_repo_default_branch(client, owner, repo, pat)

        tree_sha = await _fetch_tree_sha_for_branch(
            client, owner, repo, branch, pat
        )
        tree_paths, tree_truncated = await _fetch_recursive_tree_paths(
            client, owner, repo, tree_sha, pat
        )

        readme_text: str | None = None
        try:
            readme_text = await _fetch_readme_text(client, owner, repo, pat)
        except httpx.HTTPStatusError as e:
            if e.response.status_code != 404:
                raise
            log.debug("No README for %s/%s", owner, repo)

        snippets: list[FileSnippet] = []
        for rel in _select_config_paths(tree_paths, MAX_SNIPPET_FILES):
            try:
                snip = await _fetch_file_snippet(
                    client, owner, repo, rel, branch, pat
                )
                if snip:
                    snippets.append(snip)
            except httpx.HTTPStatusError as e:
                log.warning("Skip snippet %s: HTTP %s", rel, e.response.status_code)

        return RepoIngestion(
            owner=owner,
            repo=repo,
            default_branch=branch,
            tree_paths=tree_paths,
            tree_truncated=tree_truncated,
            readme_text=readme_text,
            snippets=snippets,
        )
    finally:
        if close_client:
            await client.aclose()
