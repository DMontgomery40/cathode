"""Normalize storyboard scenes into reusable composition families."""

from __future__ import annotations

from typing import Any

from .project_schema import scene_composition_payload
from .remotion_render import infer_motion_template

_SOFTWARE_DEMO_HINTS = (
    "dashboard",
    "screen",
    "screenshot",
    "ui",
    "interface",
    "browser",
    "workspace",
    "console",
    "panel",
    "inspector",
    "timeline",
    "form",
    "modal",
    "save endpoint",
    "right panel",
)

_FAMILY_HINTS = {
    "static_media",
    "media_pan",
    "software_demo_focus",
    "kinetic_statements",
    "three_data_stage",
    "surreal_tableau_3d",
}
_MODE_HINTS = {"none", "overlay", "native"}
_TRANSITION_HINTS = {"fade", "wipe"}
_NATIVE_MOTION_HINTS = (
    "motion",
    "animated",
    "animation",
    "kinetic",
    "title card",
    "text-led",
    "text led",
    "statement",
    "quote",
    "roadmap",
    "step",
    "process",
    "comparison",
    "ranked",
    "ranking",
    "callout",
    "reveal",
)
_QUOTE_HINTS = ("quote", "testimonial", "testimony", "founder note", "customer quote")
_BULLET_HINTS = ("roadmap", "step", "steps", "process", "sequence", "checklist", "workflow")
_DATA_HINTS = ("ranked", "ranking", "compare", "comparison", "top 3", "top three", "podium", "data stage")


def _scene_text(scene: dict[str, Any]) -> str:
    parts = [
        scene.get("title"),
        scene.get("visual_prompt"),
        scene.get("narration"),
        " ".join(str(item) for item in (scene.get("on_screen_text") or []) if str(item).strip()),
    ]
    return "\n".join(str(value or "").strip() for value in parts if str(value or "").strip()).lower()


def _normalize_composition_intent(scene: dict[str, Any]) -> dict[str, Any]:
    raw = scene.get("composition_intent") if isinstance(scene.get("composition_intent"), dict) else {}
    family_hint = str(raw.get("family_hint") or "").strip()
    mode_hint = str(raw.get("mode_hint") or "").strip().lower()
    layout = str(raw.get("layout") or "").strip()
    motion_notes = str(raw.get("motion_notes") or "").strip()
    transition_after = str(raw.get("transition_after") or "").strip().lower()
    data_points_raw = raw.get("data_points")
    data_points = (
        [str(item).strip() for item in data_points_raw if str(item).strip()]
        if isinstance(data_points_raw, list)
        else []
    )
    return {
        "family_hint": family_hint if family_hint in _FAMILY_HINTS else "",
        "mode_hint": mode_hint if mode_hint in _MODE_HINTS else "",
        "layout": layout,
        "motion_notes": motion_notes,
        "transition_after": transition_after,
        "data_points": data_points,
    }


def _normalized_transition_hint(scene: dict[str, Any], intent: dict[str, Any]) -> str:
    hint = str(scene.get("transition_hint") or "").strip().lower()
    if hint in _TRANSITION_HINTS:
        return hint
    return str(intent.get("transition_after") or "").strip().lower()


def _normalized_data_points(scene: dict[str, Any], intent: dict[str, Any]) -> list[str]:
    raw = scene.get("data_points")
    if isinstance(raw, list):
        normalized = [str(item).strip() for item in raw if str(item).strip()]
        if normalized:
            return normalized
    return intent["data_points"]


def _staging_notes(scene: dict[str, Any], intent: dict[str, Any]) -> str:
    notes = str(scene.get("staging_notes") or "").strip()
    if notes:
        return notes
    return " ".join(part for part in (intent.get("layout"), intent.get("motion_notes")) if str(part or "").strip()).strip()


def _director_scene_text(scene: dict[str, Any], intent: dict[str, Any]) -> str:
    notes = _staging_notes(scene, intent)
    parts = [
        _scene_text(scene),
        notes,
        " ".join(_normalized_data_points(scene, intent)),
        str(scene.get("transition_hint") or "").strip(),
    ]
    return "\n".join(part for part in parts if part).lower()


def _native_motion_requested(scene: dict[str, Any], intent: dict[str, Any]) -> bool:
    scene_type = str(scene.get("scene_type") or "").strip().lower()
    if scene_type == "motion":
        return True
    if intent["mode_hint"] == "native":
        return True
    if _normalized_data_points(scene, intent):
        return True
    notes = _staging_notes(scene, intent).lower()
    if not notes:
        return False
    return any(hint in notes for hint in _NATIVE_MOTION_HINTS)


def _motion_family_from_scene(scene: dict[str, Any], intent: dict[str, Any]) -> str:
    if intent["family_hint"]:
        return intent["family_hint"]
    if _normalized_data_points(scene, intent) and any(hint in _director_scene_text(scene, intent) for hint in _DATA_HINTS):
        return "three_data_stage"
    text = _director_scene_text(scene, intent)
    if any(hint in text for hint in _QUOTE_HINTS):
        return "quote_focus"
    if any(hint in text for hint in _BULLET_HINTS):
        return "bullet_stack"
    template = infer_motion_template(scene)
    if template == "three_data_stage":
        return "three_data_stage"
    if template == "quote_focus":
        return "quote_focus"
    if template == "bullet_stack":
        return "bullet_stack"
    return "kinetic_statements"


def _composition_props_from_scene(scene: dict[str, Any], intent: dict[str, Any], family: str) -> dict[str, Any]:
    lines = [str(item).strip() for item in (scene.get("on_screen_text") or []) if str(item).strip()]
    title = str(scene.get("title") or "").strip()
    narration = str(scene.get("narration") or "").strip()
    staging_notes = _staging_notes(scene, intent)
    headline = lines[0] if lines else title
    body = " ".join(lines[1:3]).strip() if len(lines) > 1 else narration[:180].strip()
    props: dict[str, Any] = {}
    if family in {"media_pan", "software_demo_focus", "kinetic_statements", "bullet_stack", "quote_focus", "surreal_tableau_3d"}:
        props["headline"] = headline
        if body:
            props["body"] = body
    if family in {"kinetic_statements", "bullet_stack"}:
        props["kicker"] = title or "Cathode"
        if lines[:4]:
            props["bullets"] = lines[:4]
        elif title:
            props["bullets"] = [title]
    if family == "quote_focus":
        props["kicker"] = title or "Cathode"
    if family == "surreal_tableau_3d":
        props["leftSubject"] = lines[0] if lines else title or "Hero form"
        props["rightSubject"] = lines[1] if len(lines) > 1 else "Counterpoint"
        props["environment"] = staging_notes or "dreamlike cinematic void"
    if staging_notes:
        props["layout"] = staging_notes
        props["motion_notes"] = staging_notes
    return props


def _default_mode_for_family(scene: dict[str, Any], family: str, current_mode: str) -> str:
    scene_type = str(scene.get("scene_type") or "").strip().lower()
    if scene_type == "motion":
        return "native"
    if family in {"kinetic_statements", "bullet_stack", "quote_focus", "three_data_stage", "surreal_tableau_3d"}:
        return "native"
    if family == "software_demo_focus":
        return "overlay"
    return current_mode or "none"


def _family_for_scene(scene: dict[str, Any], current_family: str) -> str:
    intent = _normalize_composition_intent(scene)
    if intent["family_hint"]:
        return intent["family_hint"]

    scene_type = str(scene.get("scene_type") or "image").strip().lower()
    if scene_type == "motion":
        if current_family and current_family not in {"static_media", "kinetic_title"}:
            return current_family
        return _motion_family_from_scene(scene, intent)
    if current_family and current_family != "static_media":
        return current_family
    if scene_type == "video":
        text = _director_scene_text(scene, intent)
        if any(hint in text for hint in _SOFTWARE_DEMO_HINTS):
            return "software_demo_focus"
        return "static_media"
    if scene_type == "image":
        text = _director_scene_text(scene, intent)
        if any(hint in text for hint in _SOFTWARE_DEMO_HINTS):
            return "software_demo_focus"
        if _native_motion_requested(scene, intent):
            return _motion_family_from_scene(scene, intent)
        return "media_pan"
    return current_family or "static_media"


def plan_scene_compositions(
    scenes: list[dict[str, Any]],
    *,
    brief: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Populate stable composition families without forcing a new render path yet."""
    _ = brief
    planned: list[dict[str, Any]] = []

    for scene in scenes:
        current = scene_composition_payload(scene)
        intent = _normalize_composition_intent(scene)
        next_scene = dict(scene)
        family = _family_for_scene(next_scene, str(current.get("family") or "").strip())
        mode = intent["mode_hint"] or _default_mode_for_family(
            next_scene,
            family,
            str(current.get("mode") or "none"),
        )
        if mode not in _MODE_HINTS:
            mode = _default_mode_for_family(next_scene, family, "none")
        transition_after = current.get("transition_after")
        transition_hint = _normalized_transition_hint(next_scene, intent)
        if transition_hint in _TRANSITION_HINTS:
            transition_after = {"kind": transition_hint, "duration_in_frames": 20}
        data = current.get("data")
        data_points = _normalized_data_points(next_scene, intent)
        if data_points:
            data = {"data_points": data_points}
        next_scene["composition"] = {
            "family": family,
            "mode": mode,
            "props": _composition_props_from_scene(next_scene, intent, family) or (current.get("props") if isinstance(current.get("props"), dict) else {}),
            "transition_after": transition_after,
            "data": data,
            "render_path": current.get("render_path"),
            "preview_path": current.get("preview_path"),
            "rationale": str(
                current.get("rationale")
                or _staging_notes(next_scene, intent)
                or ""
            ).strip(),
        }
        planned.append(next_scene)

    return planned
