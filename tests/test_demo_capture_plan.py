from __future__ import annotations

from core.demo_capture_plan import apply_retry_actions_to_capture_plan


def test_apply_retry_actions_flips_theme_and_expands_viewport():
    updated = apply_retry_actions_to_capture_plan(
        {
            "theme": "dark",
            "viewport": {"width": 1664, "height": 928},
        },
        ["switch_theme", "expand_viewport"],
    )

    assert updated["theme"] == "light"
    assert updated["viewport"] == {"width": 1920, "height": 1072}
    assert updated["applied_retry_actions"] == ["switch_theme", "expand_viewport"]


def test_apply_retry_actions_merges_explicit_retry_overrides():
    updated = apply_retry_actions_to_capture_plan(
        {
            "theme": "dark",
            "viewport": {"width": 1664, "height": 928},
            "retry_overrides": {
                "pick_better_state": {
                    "steps": [
                        {
                            "id": "run_review",
                            "focus_selector": "#hero-run-review",
                        }
                    ]
                }
            },
        },
        ["pick_better_state"],
    )

    assert updated["steps"][0]["focus_selector"] == "#hero-run-review"
    assert updated["applied_retry_actions"] == ["pick_better_state"]
