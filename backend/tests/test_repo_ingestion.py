import asyncio
import base64
import json

import httpx
import pytest

from app.schemas.ingestion import RepoIngestion
from app.services.repo_ingestion import ingest_repository, should_include_tree_path


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("src/index.js", True),
        ("package.json", True),
        ("node_modules/foo/bar.js", False),
        (".github/workflows/ci.yml", False),
        ("lib/__pycache__/x.pyc", False),
        ("README.md", True),
    ],
)
def test_should_include_tree_path(path: str, expected: bool) -> None:
    assert should_include_tree_path(path) is expected


def test_ingest_repository_mock_transport() -> None:
    tree_payload = {
        "truncated": False,
        "tree": [
            {"type": "blob", "path": "package.json", "mode": "100644", "sha": "a"},
            {"type": "blob", "path": "node_modules/x/y.js", "mode": "100644", "sha": "b"},
        ],
    }
    pkg_body = {"name": "demo"}
    pkg_json = {
        "type": "file",
        "encoding": "base64",
        "content": base64.b64encode(json.dumps(pkg_body).encode()).decode() + "\n",
        "size": 20,
    }

    def handler(request: httpx.Request) -> httpx.Response:
        u = str(request.url)
        if u.rstrip("/").endswith("/repos/o/r") and request.method == "GET":
            return httpx.Response(200, json={"default_branch": "main"})
        if "/repos/o/r/branches/main" in u:
            return httpx.Response(
                200,
                json={"commit": {"commit": {"tree": {"sha": "treesha"}}}},
            )
        if "/git/trees/treesha" in u:
            q = str(request.url)
            assert "recursive=1" in q
            return httpx.Response(200, json=tree_payload)
        if u.rstrip("/").endswith("/repos/o/r/readme"):
            return httpx.Response(200, text="# Hello")
        if "/contents/package.json" in u:
            return httpx.Response(200, json=pkg_json)
        return httpx.Response(500, text=f"unexpected {u}")

    transport = httpx.MockTransport(handler)

    async def run() -> RepoIngestion:
        async with httpx.AsyncClient(transport=transport) as client:
            return await ingest_repository("o", "r", "fake-pat", client=client)

    out = asyncio.run(run())
    assert out.default_branch == "main"
    assert out.tree_paths == ["package.json"]
    assert out.readme_text == "# Hello"
    assert len(out.snippets) == 1
    assert out.snippets[0].path == "package.json"


def test_ingest_default_branch_hint_skips_repo_metadata() -> None:
    """With default_branch_hint, we should not GET /repos/{owner}/{repo} (metadata only)."""
    tree_payload = {"truncated": False, "tree": []}
    requested_paths: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        from urllib.parse import urlparse

        path = urlparse(str(request.url)).path
        requested_paths.append(path)
        if path == "/repos/o/r/branches/develop":
            return httpx.Response(
                200,
                json={"commit": {"commit": {"tree": {"sha": "t1"}}}},
            )
        if path == "/repos/o/r/git/trees/t1":
            return httpx.Response(200, json=tree_payload)
        if path == "/repos/o/r/readme":
            return httpx.Response(404)
        return httpx.Response(500, text=path)

    transport = httpx.MockTransport(handler)

    async def run() -> RepoIngestion:
        async with httpx.AsyncClient(transport=transport) as client:
            return await ingest_repository(
                "o", "r", "fake-pat", default_branch_hint="develop", client=client
            )

    out = asyncio.run(run())
    assert out.default_branch == "develop"
    assert not any(p == "/repos/o/r" for p in requested_paths)
    assert "/repos/o/r/branches/develop" in requested_paths
