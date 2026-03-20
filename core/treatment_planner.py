"""LLM-assisted composition treatment planning for supported Remotion families."""

from __future__ import annotations

import json
from typing import Any, Literal

from .composition_planner import (
    _brief_prefers_authored_clinical_stills,
    _composition_props_from_scene,
    _normalize_composition_intent,
    _normalized_data_points,
    _surreal_tableau_requested,
    _three_data_stage_data,
)
from .director import (
    _ANTHROPIC_DIRECTOR_MODEL,
    _OPENAI_DIRECTOR_MODEL,
    _get_anthropic_client,
    _get_openai_client,
    _llm_call_metadata,
    load_prompt,
)
from .project_schema import normalize_brief

_SUPPORTED_FAMILIES = {
    "kinetic_statements",
    "bullet_stack",
    "quote_focus",
    "three_data_stage",
    "surreal_tableau_3d",
}
_SUPPORTED_MODES = {"native"}
_SUPPORTED_TRANSITIONS = {"fade", "wipe"}
_ALLOWED_FAMILY_PROP_KEYS = {
    "bullet_stack": frozenset(),
    "kinetic_statements": frozenset(),
    "quote_focus": frozenset(),
    "surreal_tableau_3d": frozenset(
        {
            "layoutVariant",
            "heroObject",
            "secondaryObject",
            "orbitingObject",
            "orbitCount",
            "environmentBackdrop",
            "ambientDetails",
            "paletteWords",
            "cameraMove",
            "copyTreatment",
        }
    ),
    "three_data_stage": frozenset(
        {
            "layoutVariant",
            "emphasis",
            "palette",
        }
    ),
}


def _normalize_explicit_transition(transition: Any) -> dict[str, Any] | None:
    if not isinstance(transition, dict):
        return None
    kind = str(transition.get("kind") or "").strip().lower()
    if kind not in _SUPPORTED_TRANSITIONS:
        return None
    try:
        duration = int(transition.get("duration_in_frames") or 20)
    except (TypeError, ValueError):
        duration = 20
    if duration <= 0:
        duration = 20
    return {
        "kind": kind,
        "duration_in_frames": duration,
    }


def _explicit_scene_composition(scene: dict[str, Any]) -> dict[str, Any]:
    composition = scene.get("composition") if isinstance(scene.get("composition"), dict) else {}
    props = composition.get("props") if isinstance(composition.get("props"), dict) else {}
    data = composition.get("data") if isinstance(composition.get("data"), (dict, list)) else {}
    return {
        "family": str(composition.get("family") or "").strip(),
        "mode": str(composition.get("mode") or "").strip().lower(),
        "props": props,
        "transition_after": _normalize_explicit_transition(composition.get("transition_after")),
        "data": data,
        "render_path": composition.get("render_path"),
        "preview_path": composition.get("preview_path"),
        "rationale": str(composition.get("rationale") or "").strip(),
    }


def _scene_is_native_remotion(scene: dict[str, Any]) -> bool:
    return _explicit_scene_composition(scene).get("mode") == "native"


def _eligible_treatment_scenes(scenes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [scene for scene in scenes if _scene_is_native_remotion(scene)]


def treatment_planning_needed(
    brief: dict[str, Any],
    scenes: list[dict[str, Any]],
) -> bool:
    del brief
    return any(_scene_is_native_remotion(scene) for scene in scenes)


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
        composition = _explicit_scene_composition(scene)
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
                "composition": {
                    "family": str(composition.get("family") or "").strip(),
                    "mode": str(composition.get("mode") or "").strip(),
                    "transition_after": composition.get("transition_after"),
                    "rationale": str(composition.get("rationale") or "").strip(),
                },
            }
        )

    return (
        "Choose deterministic treatment overrides only for scenes that are already in Cathode's native Remotion branch.\n\n"
        "Do not change manifestation branch, mode, scene copy, visual prompts, narration, staging facts, or raw data. Only refine native family choice, semantic props, structured data that already exists in the source scene, and rationale.\n\n"
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
        validated.append(
            {
                "uid": uid,
                "family": family,
                "mode": mode,
                "transition_hint": transition_hint if transition_hint in _SUPPORTED_TRANSITIONS else None,
                "props": props,
                "rationale": str(item.get("rationale") or "").strip(),
            }
        )
    return validated


def _semantic_override_props(family: str, props: Any) -> dict[str, Any]:
    if not isinstance(props, dict):
        return {}
    allowed_keys = _ALLOWED_FAMILY_PROP_KEYS.get(family, frozenset())
    return {key: value for key, value in props.items() if key in allowed_keys}


def _merged_props(
    scene: dict[str, Any],
    current: dict[str, Any],
    family: str,
    override_props: Any,
) -> dict[str, Any]:
    intent = _normalize_composition_intent(scene)
    base_props = _composition_props_from_scene(scene, intent, family)
    current_family = str(current.get("family") or "").strip()
    current_props = current.get("props") if isinstance(current.get("props"), dict) else {}
    if current_family == family:
        merged = dict(base_props)
        merged.update(current_props)
    else:
        merged = dict(base_props)
    merged.update(_semantic_override_props(family, override_props))
    return merged


def _merged_data(
    scene: dict[str, Any],
    current: dict[str, Any],
    family: str,
    props: dict[str, Any],
) -> Any:
    current_family = str(current.get("family") or "").strip()
    current_data = current.get("data") if family == current_family else {}
    if family == "three_data_stage":
        intent = _normalize_composition_intent(scene)
        return _three_data_stage_data(scene, intent, current_data, props)
    return current_data if isinstance(current_data, (dict, list)) else {}


def _synchronized_legacy_motion(scene: dict[str, Any], composition: dict[str, Any]) -> dict[str, Any]:
    motion = scene.get("motion")
    if not isinstance(motion, dict):
        return scene
    next_scene = dict(scene)
    next_motion = dict(motion)
    next_motion["template_id"] = composition["family"]
    next_motion["props"] = composition["props"]
    next_motion["rationale"] = composition["rationale"]
    next_motion["render_path"] = composition.get("render_path")
    next_motion["preview_path"] = composition.get("preview_path")
    next_scene["motion"] = next_motion
    return next_scene


def _clean_legacy_transition_hints(scene: dict[str, Any], transition_after: dict[str, Any] | None) -> dict[str, Any]:
    next_scene = dict(scene)
    next_scene["transition_hint"] = transition_after["kind"] if transition_after else None
    composition_intent = next_scene.get("composition_intent")
    if isinstance(composition_intent, dict) and "transition_after" in composition_intent:
        cleaned_intent = dict(composition_intent)
        cleaned_intent.pop("transition_after", None)
        next_scene["composition_intent"] = cleaned_intent
    return next_scene


def _merge_treatment_overrides(
    scenes: list[dict[str, Any]],
    overrides: list[dict[str, Any]],
    *,
    brief: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    by_uid = {item["uid"]: item for item in overrides}
    merged: list[dict[str, Any]] = []
    suppress_transitions = _brief_prefers_authored_clinical_stills(brief)
    for scene in scenes:
        uid = str(scene.get("uid") or "").strip()
        override = by_uid.get(uid)
        if not override or not _scene_is_native_remotion(scene):
            merged.append(scene)
            continue

        current = _explicit_scene_composition(scene)
        current_family = str(current.get("family") or "").strip()
        override_family = str(override.get("family") or "").strip()
        if override_family not in _SUPPORTED_FAMILIES:
            merged.append(scene)
            continue

        intent = _normalize_composition_intent(scene)
        data_points = _normalized_data_points(scene, intent)
        if override_family == "three_data_stage" and not data_points and current_family != "three_data_stage":
            merged.append(scene)
            continue
        if current_family == "three_data_stage" and override_family != "three_data_stage" and data_points:
            merged.append(scene)
            continue
        if override_family == "surreal_tableau_3d" and not _surreal_tableau_requested(scene, intent):
            merged.append(scene)
            continue
        if (
            current_family == "surreal_tableau_3d"
            and override_family != "surreal_tableau_3d"
            and _surreal_tableau_requested(scene, intent)
        ):
            merged.append(scene)
            continue

        transition_after = None if suppress_transitions else current.get("transition_after")
        next_scene = _clean_legacy_transition_hints(scene, transition_after)
        next_props = _merged_props(scene, current, override_family, override.get("props"))
        next_composition = {
            "family": override_family,
            "mode": "native",
            "props": next_props,
            "transition_after": transition_after,
            "data": _merged_data(scene, current, override_family, next_props),
            "render_path": current.get("render_path"),
            "preview_path": current.get("preview_path"),
            "rationale": override["rationale"] or str(current.get("rationale") or "").strip(),
        }
        next_scene["composition"] = next_composition
        next_scene = _synchronized_legacy_motion(next_scene, next_composition)
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
    eligible_scenes = _eligible_treatment_scenes(scenes)
    if not eligible_scenes or not treatment_planning_needed(normalized_brief, scenes):
        return scenes, {}

    system_prompt = load_prompt("treatment_planner_system")
    user_prompt = _build_treatment_user_prompt(normalized_brief, eligible_scenes)

    if provider == "openai":
        overrides, response = _plan_with_openai(system_prompt, user_prompt)
        return _merge_treatment_overrides(scenes, overrides, brief=normalized_brief), _llm_call_metadata(
            provider="openai",
            model=_OPENAI_DIRECTOR_MODEL,
            operation="treatment_planning",
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response=response,
        )
    if provider == "anthropic":
        overrides, response = _plan_with_anthropic(system_prompt, user_prompt)
        return _merge_treatment_overrides(scenes, overrides, brief=normalized_brief), _llm_call_metadata(
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
