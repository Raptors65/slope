from unittest.mock import MagicMock, patch

from app.config import Settings
from app.schemas.augment import AugmentRelevanceResult
from app.services.augment_relevance import run_augment_relevance_sync


def test_run_augment_relevance_sync_uses_auggie_and_cleans_tmp() -> None:
    settings = Settings(
        openrouter_api_key=None,
        github_pat=None,
        github_webhook_secret=None,
        augment_model="haiku4.5",
        augment_timeout_seconds=60,
        augment_max_cli_turns=3,
        augment_clone_timeout_seconds=60,
    )
    fake_dict = {
        "relevant_files": [{"path": "app/main.py", "reason": "entrypoint"}],
        "dependency_notes": ["a imports b"],
    }
    fake_result = AugmentRelevanceResult.model_validate(fake_dict)

    mock_agent = MagicMock()
    mock_agent.__enter__ = MagicMock(return_value=mock_agent)
    mock_agent.__exit__ = MagicMock(return_value=None)
    mock_agent.run = MagicMock(return_value=fake_dict)

    with (
        patch(
            "app.services.augment_relevance.tempfile.mkdtemp",
            return_value="/tmp/slope_augment_test",
        ),
        patch("app.services.augment_relevance.shutil.rmtree") as mock_rmtree,
        patch(
            "app.services.augment_relevance.shallow_clone_github_repo"
        ) as mock_clone,
        patch("app.services.augment_relevance.Auggie", return_value=mock_agent),
    ):
        out = run_augment_relevance_sync(
            "o",
            "r",
            "pat",
            default_branch="main",
            issue_title="Fix bug",
            issue_body="Details",
            tree_paths=["a.py", "b.py"],
            readme_excerpt="# Hi",
            settings=settings,
            ticket_analysis_json='{"task_type":"bugfix"}',
        )

    assert out == fake_result
    mock_clone.assert_called_once()
    clone_kw = mock_clone.call_args.kwargs
    assert clone_kw["branch"] == "main"
    mock_agent.run.assert_called_once()
    instr = mock_agent.run.call_args[0][0]
    assert "Prior LLM ticket analysis" in instr
    assert mock_agent.run.call_args.kwargs.get("return_type") is dict
    assert mock_rmtree.call_count >= 1
