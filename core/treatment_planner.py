"""LLM-assisted composition treatment planning for supported Remotion families."""

from __future__ import annotations

import json
from typing import Any, Literal

from .director import (
    _ANTHROPIC_DIRECTOR_MODEL,
    _OPENAI_DIRECTOR_MODEL,
    _get_anthropic_client,
    _get_openai_client,
    _llm_call_metadata,
    load_prompt,
)
from .project_schema import normalize_brief, scene_composition_payload

_SUPPORTED_FAMILIES = {
    "static_media",
    "media_pan",
    "software_demo_focus",
    "kinetic_statements",
    "bullet_stack",
    "quote_focus",
    "three_data_stage",
    "surreal_tableau_3d",
}
_SUPPORTED_MODES = {"none", "overlay", "native"}
_SUPPORTED_TRANSITIONS = {"fade", "wipe"}


def _brief_intent_text(brief: dict[str, Any]) -> str:
    parts = [
        brief.get("video_goal"),
        brief.get("audience"),
        brief.get("source_material"),
        brief.get("must_include"),
        brief.get("must_avoid"),
        brief.get("raw_brief"),
        brief.get("visual_style"),
        brief.get("tone"),
    ]
    return "\n".join(str(value or "").strip() for value in parts if str(value or "").strip()).lower()


def _brief_requests_motion_treatment(brief: dict[str, Any]) -> bool:
    text = _brief_intent_text(brief)
    return any(
        phrase in text
        for phrase in (
            "motion",
            "animate",
            "animated",
            "3d",
            "three-dimensional",
            "camera move",
            "camera sweep",
            "orbit shot",
            "hero tableau",
            "symbolic tableau",
            "surreal stage",
            "kinetic",
        )
    )


def treatment_planning_needed(
    brief: dict[str, Any],
    scenes: list[dict[str, Any]],
) -> bool:
    normalized = normalize_brief(brief)
    if normalized.get("composition_mode") in {"hybrid", "motion_only"}:
        return True
    if normalized.get("visual_source_strategy") != "images_only":
        return True
    if normalized.get("text_render_mode") == "deterministic_overlay":
        return True
    if _brief_requests_motion_treatment(normalized):
        return True

    for scene in scenes:
        if str(scene.get("scene_type") or "").strip().lower() == "motion":
            return True
        if scene.get("transition_hint"):
            return True
        if scene.get("data_points"):
            return True
    return False


def treatment_tool_schema() -> dict[str, Any]:
    return {
        "name": "emit_treatments",
        "description": "Return treatment overrides for scenes that should receive deterministic composition changes.",
        "input_schema": {
            "type": "object",
            "properties": {
                "scenes": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "uid": {"type": "string"},
                            "family": {"type": "string"},
                            "mode": {"type": "string", "enum": sorted(_SUPPORTED_MODES)},
                            "transition_hint": {"type": "string", "enum": sorted(_SUPPORTED_TRANSITIONS)},
                            "props": {"type": "object"},
                            "data": {"type": ["object", "array"]},
                            "rationale": {"type": "string"},
                        },
                        "required": ["uid", "family", "mode", "rationale"],
                    },
                }
            },
            "required": ["scenes"],
        },
    }


def _build_treatment_user_prompt(
    brief: dict[str, Any],
    scenes: list[dict[str, Any]],
) -> str:
    normalized = normalize_brief(brief)
    payload_scenes = []
    for scene in scenes:
        composition = scene_composition_payload(scene)
        payload_scenes.append(
            {
                "uid": str(scene.get("uid") or "").strip(),
                "title": str(scene.get("title") or "").strip(),
                "scene_type": str(scene.get("scene_type") or "image").strip().lower(),
                "narration": str(scene.get("narration") or "").strip(),
                "visual_prompt": str(scene.get("visual_prompt") or "").strip(),
                "on_screen_text": [str(item).strip() for item in (scene.get("on_screen_text") or []) if str(item).strip()],
                "staging_notes": str(scene.get("staging_notes") or "").strip(),
                "data_points": [str(item).strip() for item in (scene.get("data_points") or []) if str(item).strip()],
                "transition_hint": str(scene.get("transition_hint") or "").strip().lower() or None,
                "composition": {
                    "family": str(composition.get("family") or "").strip(),
                    "mode": str(composition.get("mode") or "").strip(),
                    "rationale": str(composition.get("rationale") or "").strip(),
                },
            }
        )

    return (
        "Choose deterministic treatment overrides only for scenes that genuinely benefit from Cathode's supported motion, overlay, or 3D registry.\n\n"
        "Keep pure creative briefs image-first by default. Do not force motion unless the scene clearly asks for it.\n\n"
        f"Brief JSON:\n{json.dumps(normalized, indent=2, ensure_ascii=False)}\n\n"
        f"Scenes JSON:\n{json.dumps(payload_scenes, indent=2, ensure_ascii=False)}\n"
    )


def _extract_treatment_items(result: Any) -> list[dict[str, Any]]:
    if isinstance(result, dict) and isinstance(result.get("scenes"), list):
        return [item for item in result["scenes"] if isinstance(item, dict)]
    if isinstance(result, list):
        return [item for item in result if isinstance(item, dict)]
    raise ValueError("Could not find treatment scenes array in response")


def _validate_treatment_items(result: Any) -> list[dict[str, Any]]:
    validated: list[dict[str, Any]] = []
    for item in _extract_treatment_items(result):
        uid = str(item.get("uid") or "").strip()
        family = str(item.get("family") or "").strip()
        mode = str(item.get("mode") or "").strip().lower()
        if not uid or family not in _SUPPORTED_FAMILIES or mode not in _SUPPORTED_MODES:
            continue

        transition_hint = str(item.get("transition_hint") or "").strip().lower()
        props = item.get("props") if isinstance(item.get("props"), dict) else {}
        data = item.get("data") if isinstance(item.get("data"), (dict, list)) else {}
        validated.append(
            {
                "uid": uid,
                "family": family,
                "mode": mode,
                "transition_hint": transition_hint if transition_hint in _SUPPORTED_TRANSITIONS else None,
                "props": props,
                "data": data,
                "rationale": str(item.get("rationale") or "").strip(),
            }
        )
    return validated


def _merge_treatment_overrides(
    scenes: list[dict[str, Any]],
    overrides: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    by_uid = {item["uid"]: item for item in overrides}
    merged: list[dict[str, Any]] = []
    for scene in scenes:
        uid = str(scene.get("uid") or "").strip()
        override = by_uid.get(uid)
        if not override:
            merged.append(scene)
            continue

        current = scene_composition_payload(scene)
        transition_after = current.get("transition_after")
        if override.get("transition_hint"):
            transition_after = {
                "kind": override["transition_hint"],
                "duration_in_frames": 20,
            }

        next_scene = dict(scene)
        next_scene["composition"] = {
            "family": override["family"],
            "mode": override["mode"],
            "props": override["props"] if isinstance(override["props"], dict) else current.get("props") or {},
            "transition_after": transition_after,
            "data": override["data"] if isinstance(override["data"], (dict, list)) else current.get("data") or {},
            "render_path": current.get("render_path"),
            "preview_path": current.get("preview_path"),
            "rationale": override["rationale"] or str(current.get("rationale") or "").strip(),
        }
        merged.append(next_scene)
    return merged


def _plan_with_openai(system_prompt: str, user_prompt: str) -> tuple[list[dict[str, Any]], Any]:
    client = _get_openai_client()
    response = client.responses.create(
        model=_OPENAI_DIRECTOR_MODEL,
        instructions=system_prompt,
        input=user_prompt,
        text={"format": {"type": "json_object"}},
        temperature=0.2,
    )
    parsed = json.loads(response.output_text)
    return _validate_treatment_items(parsed), response


def _anthropic_tool_input(content: list[Any]) -> Any:
    for block in content:
        block_type = getattr(block, "type", None)
        if block_type is None and isinstance(block, dict):
            block_type = block.get("type")
        block_name = getattr(block, "name", None)
        if block_name is None and isinstance(block, dict):
            block_name = block.get("name")
        if block_type == "tool_use" and block_name == "emit_treatments":
            if isinstance(block, dict):
                return block.get("input")
            return getattr(block, "input", None)
    return None


def _plan_with_anthropic(system_prompt: str, user_prompt: str) -> tuple[list[dict[str, Any]], Any]:
    client = _get_anthropic_client()
    response = client.messages.create(
        model=_ANTHROPIC_DIRECTOR_MODEL,
        max_tokens=4000,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
        tools=[treatment_tool_schema()],
        tool_choice={"type": "tool", "name": "emit_treatments"},
    )
    tool_input = _anthropic_tool_input(response.content)
    if not tool_input:
        raise ValueError("No structured treatment tool output from Anthropic")
    return _validate_treatment_items(tool_input), response


def plan_scene_treatments_with_metadata(
    scenes: list[dict[str, Any]],
    *,
    brief: dict[str, Any] | None = None,
    provider: Literal["openai", "anthropic"] = "openai",
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    normalized_brief = normalize_brief(brief or {})
    if not treatment_planning_needed(normalized_brief, scenes):
        return scenes, {}

    system_prompt = load_prompt("treatment_planner_system")
    user_prompt = _build_treatment_user_prompt(normalized_brief, scenes)

    if provider == "openai":
        overrides, response = _plan_with_openai(system_prompt, user_prompt)
        return _merge_treatment_overrides(scenes, overrides), _llm_call_metadata(
            provider="openai",
            model=_OPENAI_DIRECTOR_MODEL,
            operation="treatment_planning",
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response=response,
        )
    if provider == "anthropic":
        overrides, response = _plan_with_anthropic(system_prompt, user_prompt)
        return _merge_treatment_overrides(scenes, overrides), _llm_call_metadata(
            provider="anthropic",
            model=_ANTHROPIC_DIRECTOR_MODEL,
            operation="treatment_planning",
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response=response,
        )
    raise ValueError(f"Unknown provider: {provider}")


def plan_scene_treatments(
    scenes: list[dict[str, Any]],
    *,
    brief: dict[str, Any] | None = None,
    provider: Literal["openai", "anthropic"] = "openai",
) -> list[dict[str, Any]]:
    return plan_scene_treatments_with_metadata(
        scenes,
        brief=brief,
        provider=provider,
    )[0]
