"""Shallow git clone for Augment workspace (Phase 5)."""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path
from urllib.parse import quote

log = logging.getLogger("slope.clone")

GITHUB_HOST = "github.com"


def shallow_clone_github_repo(
    owner: str,
    repo: str,
    pat: str,
    dest: Path,
    *,
    branch: str | None = None,
    timeout_seconds: float = 180.0,
) -> None:
    """
    `git clone --depth 1` into `dest` (empty directory) using HTTPS + PAT.

    Raises subprocess.CalledProcessError on clone failure.
    """
    dest.parent.mkdir(parents=True, exist_ok=True)
    token = quote(pat, safe="")
    url = f"https://x-access-token:{token}@{GITHUB_HOST}/{owner}/{repo}.git"
    cmd: list[str] = ["git", "clone", "--depth", "1"]
    if branch and branch.strip():
        cmd.extend(["--branch", branch.strip()])
    cmd.extend([url, str(dest)])

    log.info("Cloning %s/%s (depth=1%s)", owner, repo, f", branch={branch}" if branch else "")
    try:
        subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
    except subprocess.CalledProcessError as e:
        err = (e.stderr or e.stdout or "").strip()
        log.error(
            "git clone failed for %s/%s (exit=%s): %s",
            owner,
            repo,
            e.returncode,
            err[:500],
        )
        raise
