"""Augment result schema coercion (LLM output shapes)."""

from app.schemas.augment import AugmentRelevanceResult


def test_dependency_notes_dict_coerced_to_strings() -> None:
    r = AugmentRelevanceResult.model_validate(
        {
            "relevant_files": [{"path": "lib/express.js", "reason": "core"}],
            "dependency_notes": {
                "app_handle_flow": "lib/application.js wires router.handle()",
                "middleware_order": "See middleware init in app",
            },
        }
    )
    assert len(r.dependency_notes) == 2
    assert "app_handle_flow:" in r.dependency_notes[0]
    assert "middleware_order:" in r.dependency_notes[1]


def test_dependency_notes_list_unchanged() -> None:
    r = AugmentRelevanceResult.model_validate(
        {
            "relevant_files": [],
            "dependency_notes": ["a imports b", "c calls d"],
        }
    )
    assert r.dependency_notes == ["a imports b", "c calls d"]
