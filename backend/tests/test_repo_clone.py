from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.services.repo_clone import shallow_clone_github_repo


def test_shallow_clone_builds_expected_git_command(tmp_path: Path) -> None:
    dest = tmp_path / "repo"
    with patch("app.services.repo_clone.subprocess.run") as run:
        run.return_value = MagicMock()
        shallow_clone_github_repo(
            "acme",
            "demo",
            "ghp_secret",
            dest,
            branch="main",
            timeout_seconds=30.0,
        )
    run.assert_called_once()
    args, kwargs = run.call_args
    cmd = args[0]
    assert cmd[0] == "git"
    assert cmd[1] == "clone"
    assert cmd[2] == "--depth"
    assert cmd[3] == "1"
    assert cmd[4] == "--branch"
    assert cmd[5] == "main"
    assert cmd[6].startswith("https://x-access-token:")
    assert cmd[6].endswith("@github.com/acme/demo.git")
    assert "ghp_secret" in cmd[6]
    assert cmd[7] == str(dest)
    assert kwargs["check"] is True
    assert kwargs["timeout"] == 30.0


def test_shallow_clone_omits_branch_when_none(tmp_path: Path) -> None:
    dest = tmp_path / "r"
    with patch("app.services.repo_clone.subprocess.run") as run:
        run.return_value = MagicMock()
        shallow_clone_github_repo("a", "b", "tok", dest, branch=None)
    cmd = run.call_args.args[0]
    assert "--branch" not in cmd
