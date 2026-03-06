"""Plan and brief normalization helpers for the generic storyboard pipeline."""

from __future__ import annotations

import copy
import re
import uuid
from typing import Any

SOURCE_MODES = ("ideas_notes", "source_text", "final_script")
SCENE_TYPES = ("image", "video")
VISUAL_SOURCE_STRATEGIES = ("images_only", "mixed_media", "video_preferred")
IMAGE_PROVIDERS = ("replicate", "manual")
VIDEO_PROVIDERS = ("manual", "local")


def default_brief() -> dict[str, Any]:
    """Return the canonical brief shape for new plans."""
    return {
        "project_name": "my_video",
        "source_mode": "source_text",
        "video_goal": "",
        "audience": "",
        "source_material": "",
        "target_length_minutes": 3.0,
        "tone": "",
        "visual_style": "",
        "must_include": "",
        "must_avoid": "",
        "ending_cta": "",
        "visual_source_strategy": "images_only",
        "available_footage": "",
        "style_reference_summary": "",
        "style_reference_paths": [],
        "raw_brief": "",
    }


def default_render_profile() -> dict[str, Any]:
    """Default rendering profile for v1 (landscape slides only)."""
    return {
        "version": "v1",
        "aspect_ratio": "16:9",
        "width": 1664,
        "height": 928,
        "fps": 24,
        "scene_types": ["image", "video"],
    }


def default_image_profile() -> dict[str, Any]:
    """Default image generation/edit settings persisted in plan metadata."""
    return {
        "provider": "replicate",
        "generation_model": "qwen/qwen-image-2512",
        "edit_model": "qwen/qwen-image-edit-2511",
    }


def default_video_profile() -> dict[str, Any]:
    """Default video generation settings persisted in plan metadata."""
    return {
        "provider": "manual",
        "generation_model": "",
    }


def default_tts_profile() -> dict[str, Any]:
    """Default voice settings persisted in plan metadata."""
    return {
        "provider": "kokoro",
        "voice": "af_bella",
        "speed": 1.1,
    }


def sanitize_project_name(value: Any, fallback: str = "my_video") -> str:
    """Normalize project names to a filesystem-safe format."""
    raw = str(value or "").strip()
    if not raw:
        raw = fallback
    raw = raw.replace(" ", "_")
    cleaned = re.sub(r"[^a-zA-Z0-9_-]", "_", raw)
    return cleaned or fallback


def _normalize_float(value: Any, fallback: float) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return fallback
    if parsed <= 0:
        return fallback
    return parsed


def _normalize_nonnegative_float(value: Any, fallback: float) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return fallback
    if parsed < 0:
        return fallback
    return parsed


def _normalize_optional_nonnegative_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    if parsed < 0:
        return None
    return parsed


def normalize_brief(brief: Any) -> dict[str, Any]:
    """Normalize arbitrary brief-like input into the canonical brief schema."""
    result = default_brief()
    data = brief if isinstance(brief, dict) else {}

    for key in result:
        if key in data and data[key] is not None:
            result[key] = data[key]

    result["project_name"] = sanitize_project_name(result.get("project_name"))
    source_mode = str(result.get("source_mode") or "").strip()
    result["source_mode"] = source_mode if source_mode in SOURCE_MODES else "source_text"
    result["target_length_minutes"] = _normalize_float(result.get("target_length_minutes"), 3.0)

    for key in (
        "video_goal",
        "audience",
        "source_material",
        "tone",
        "visual_style",
        "must_include",
        "must_avoid",
        "ending_cta",
        "available_footage",
        "style_reference_summary",
        "raw_brief",
    ):
        result[key] = str(result.get(key) or "").strip()

    style_reference_paths = result.get("style_reference_paths")
    if isinstance(style_reference_paths, list):
        result["style_reference_paths"] = [
            str(item).strip()
            for item in style_reference_paths
            if item is not None and str(item).strip()
        ]
    else:
        result["style_reference_paths"] = []

    visual_source_strategy = str(result.get("visual_source_strategy") or "").strip()
    result["visual_source_strategy"] = (
        visual_source_strategy if visual_source_strategy in VISUAL_SOURCE_STRATEGIES else "images_only"
    )

    # Allow raw_brief as a direct input path when source material is intentionally empty.
    if not result["source_material"] and result["raw_brief"]:
        result["source_material"] = result["raw_brief"]

    return result


def normalize_scene(scene: Any, index: int) -> dict[str, Any]:
    """Backfill a single scene with v1 generic defaults while preserving extra keys."""
    src = copy.deepcopy(scene if isinstance(scene, dict) else {})
    out = dict(src)

    out["id"] = index
    out["uid"] = str(src.get("uid") or str(uuid.uuid4())[:8])
    out["title"] = str(src.get("title") or f"Scene {index + 1}")
    out["narration"] = str(src.get("narration") or "").strip()
    out["visual_prompt"] = str(src.get("visual_prompt") or "").strip()
    scene_type = str(src.get("scene_type") or "image").strip().lower()
    out["scene_type"] = scene_type if scene_type in SCENE_TYPES else "image"

    on_screen = src.get("on_screen_text")
    if isinstance(on_screen, list):
        out["on_screen_text"] = [str(item).strip() for item in on_screen if str(item).strip()]
    else:
        out["on_screen_text"] = []

    history = src.get("refinement_history")
    out["refinement_history"] = history if isinstance(history, list) else []
    out["image_path"] = src.get("image_path") or None
    out["video_path"] = src.get("video_path") or None
    out["video_trim_start"] = _normalize_nonnegative_float(src.get("video_trim_start"), 0.0)
    out["video_trim_end"] = _normalize_optional_nonnegative_float(src.get("video_trim_end"))
    if out["video_trim_end"] is not None and out["video_trim_end"] < out["video_trim_start"]:
        out["video_trim_end"] = out["video_trim_start"]
    out["video_playback_speed"] = _normalize_float(src.get("video_playback_speed"), 1.0)
    out["video_hold_last_frame"] = bool(src.get("video_hold_last_frame", True))
    out["audio_path"] = src.get("audio_path") or None
    if "preview_path" in src:
        out["preview_path"] = src.get("preview_path")

    return out


def _merge_with_defaults(defaults: dict[str, Any], value: Any) -> dict[str, Any]:
    merged = dict(defaults)
    if isinstance(value, dict):
        for key, current in value.items():
            merged[key] = current
    return merged


def backfill_plan(plan: Any) -> dict[str, Any]:
    """
    Normalize an existing plan to the v1 generic schema.

    This is intentionally non-destructive for unknown keys and supports legacy
    plans that only contain `meta.input_text`.
    """
    root = copy.deepcopy(plan if isinstance(plan, dict) else {})
    meta = root.get("meta") if isinstance(root.get("meta"), dict) else {}
    meta = dict(meta)

    inferred_project_name = sanitize_project_name(meta.get("project_name") or "my_video")

    brief = normalize_brief(meta.get("brief"))
    brief["project_name"] = inferred_project_name

    input_text = str(meta.get("input_text") or "").strip()
    if not brief.get("source_material") and input_text:
        brief["source_mode"] = "source_text"
        brief["source_material"] = input_text

    render_profile = _merge_with_defaults(default_render_profile(), meta.get("render_profile"))
    render_profile["aspect_ratio"] = str(render_profile.get("aspect_ratio") or "16:9")
    render_profile["width"] = int(render_profile.get("width") or 1664)
    render_profile["height"] = int(render_profile.get("height") or 928)
    render_profile["fps"] = int(render_profile.get("fps") or 24)
    if not isinstance(render_profile.get("scene_types"), list):
        render_profile["scene_types"] = ["image"]

    raw_image_profile = meta.get("image_profile") if isinstance(meta.get("image_profile"), dict) else {}
    image_profile = _merge_with_defaults(default_image_profile(), raw_image_profile)
    if meta.get("image_provider") and "provider" not in raw_image_profile:
        image_profile["provider"] = str(meta["image_provider"])
    if meta.get("image_model") and "generation_model" not in raw_image_profile:
        image_profile["generation_model"] = str(meta["image_model"])
    provider = str(image_profile.get("provider") or "replicate").strip().lower()
    image_profile["provider"] = provider if provider in IMAGE_PROVIDERS else "replicate"
    image_profile["generation_model"] = str(image_profile.get("generation_model") or "qwen/qwen-image-2512").strip()
    image_profile["edit_model"] = str(image_profile.get("edit_model") or "qwen/qwen-image-edit-2511").strip()

    raw_video_profile = meta.get("video_profile") if isinstance(meta.get("video_profile"), dict) else {}
    video_profile = _merge_with_defaults(default_video_profile(), raw_video_profile)
    if meta.get("video_provider") and "provider" not in raw_video_profile:
        video_profile["provider"] = str(meta["video_provider"])
    if meta.get("video_model") and "generation_model" not in raw_video_profile:
        video_profile["generation_model"] = str(meta["video_model"])
    video_provider = str(video_profile.get("provider") or "manual").strip().lower()
    video_profile["provider"] = video_provider if video_provider in VIDEO_PROVIDERS else "manual"
    video_profile["generation_model"] = str(video_profile.get("generation_model") or "").strip()

    tts_profile = _merge_with_defaults(default_tts_profile(), meta.get("tts_profile"))

    # Compatibility with prior flat metadata keys.
    if meta.get("tts_provider") and not tts_profile.get("provider"):
        tts_profile["provider"] = str(meta["tts_provider"])
    if meta.get("tts_voice") and not tts_profile.get("voice"):
        tts_profile["voice"] = str(meta["tts_voice"])
    if meta.get("tts_speed") and not tts_profile.get("speed"):
        tts_profile["speed"] = _normalize_float(meta["tts_speed"], 1.1)
    tts_profile["provider"] = str(tts_profile.get("provider") or "kokoro")
    tts_profile["voice"] = str(tts_profile.get("voice") or "af_bella")
    tts_profile["speed"] = _normalize_float(tts_profile.get("speed"), 1.1)

    scenes_raw = root.get("scenes") if isinstance(root.get("scenes"), list) else []
    scenes = [normalize_scene(scene, index=i) for i, scene in enumerate(scenes_raw)]

    meta["project_name"] = inferred_project_name
    meta["brief"] = brief
    meta["pipeline_mode"] = str(meta.get("pipeline_mode") or "generic_slides_v1")
    meta["render_profile"] = render_profile
    meta["image_profile"] = image_profile
    meta["image_model"] = image_profile["generation_model"]
    meta["video_profile"] = video_profile
    meta["video_model"] = video_profile["generation_model"]
    meta["tts_profile"] = tts_profile

    # Keep legacy fallback for older tooling that expects input_text.
    if not input_text and brief.get("source_material"):
        meta["input_text"] = brief["source_material"]

    root["meta"] = meta
    root["scenes"] = scenes
    return root
