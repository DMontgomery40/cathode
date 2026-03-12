"""Helpers for live-demo capture plans and retry mutations."""

from __future__ import annotations

import copy
from typing import Any


DEFAULT_VIEWPORT_EXPAND_WIDTH = 256
DEFAULT_VIEWPORT_EXPAND_HEIGHT = 144


def deep_merge_capture_plan(base: Any, override: Any) -> Any:
    """Recursively merge capture plan objects while replacing arrays."""
    if isinstance(base, dict) and isinstance(override, dict):
        merged = {key: copy.deepcopy(value) for key, value in base.items()}
        for key, value in override.items():
            if key in merged:
                merged[key] = deep_merge_capture_plan(merged[key], value)
            else:
                merged[key] = copy.deepcopy(value)
        return merged
    return copy.deepcopy(override)


def apply_retry_actions_to_capture_plan(plan: dict[str, Any], actions: list[str]) -> dict[str, Any]:
    """Apply bounded retry actions to a capture plan using generic defaults plus explicit overrides."""
    working = copy.deepcopy(plan if isinstance(plan, dict) else {})
    retry_overrides = working.get("retry_overrides") if isinstance(working.get("retry_overrides"), dict) else {}
    applied: list[str] = []

    for action in actions:
        action_name = str(action or "").strip()
        if not action_name or action_name in applied:
            continue

        if action_name == "switch_theme":
            current_theme = str(working.get("theme") or working.get("preferred_theme") or "dark").strip().lower()
            working["theme"] = "light" if current_theme == "dark" else "dark"
        elif action_name == "expand_viewport":
            viewport = working.get("viewport") if isinstance(working.get("viewport"), dict) else {}
            width = int(viewport.get("width") or 1664)
            height = int(viewport.get("height") or 928)
            working["viewport"] = {
                "width": width + DEFAULT_VIEWPORT_EXPAND_WIDTH,
                "height": height + DEFAULT_VIEWPORT_EXPAND_HEIGHT,
            }

        override = retry_overrides.get(action_name)
        if isinstance(override, dict):
            working = deep_merge_capture_plan(working, override)

        applied.append(action_name)

    working["applied_retry_actions"] = applied
    return working
