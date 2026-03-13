"""Plan and brief normalization helpers for the generic storyboard pipeline."""

from __future__ import annotations

import copy
import re
import uuid
from pathlib import Path
from typing import Any

from .demo_assets import build_footage_summary, normalize_footage_manifest

SOURCE_MODES = ("ideas_notes", "source_text", "final_script")
SCENE_TYPES = ("image", "video", "motion")
COMPOSITION_MODES = ("classic", "motion_only", "hybrid")
VISUAL_SOURCE_STRATEGIES = ("images_only", "mixed_media", "video_preferred")
IMAGE_PROVIDERS = ("replicate", "local", "manual")
VIDEO_PROVIDERS = ("manual", "local", "agent")
RENDER_BACKENDS = ("ffmpeg", "remotion")
AGENT_DEMO_PROFILE_KEYS = (
    "workspace_path",
    "app_url",
    "launch_command",
    "expected_url",
    "preferred_agent",
    "repo_url",
    "flow_hints",
)


def _normalize_project_asset_path(
    raw_path: Any,
    *,
    base_dir: str | Path | None = None,
    project_name: str | None = None,
) -> str | None:
    """Normalize asset paths that should resolve within the current project directory."""
    value = str(raw_path or "").strip()
    if not value:
        return None

    base = Path(base_dir).expanduser().resolve() if base_dir not in (None, "") else None
    if base is None:
        return value

    project_slug = sanitize_project_name(project_name or base.name)
    normalized = value.replace("\\", "/").lstrip("/")
    marker = f"projects/{project_slug}/"

    def _candidate_from_suffix(suffix: str) -> str | None:
        suffix = suffix.strip().lstrip("/")
        if not suffix:
            return None
        candidate = (base / suffix).resolve()
        if not str(candidate).startswith(str(base)):
            return None
        if candidate.exists() and candidate.is_file():
            return str(candidate)
        return None

    if normalized.startswith(marker):
        resolved = _candidate_from_suffix(normalized[len(marker):])
        return resolved

    path = Path(value).expanduser()
    if path.is_absolute():
        resolved = path.resolve()
        if str(resolved).startswith(str(base)) and resolved.exists() and resolved.is_file():
            return str(resolved)
        absolute = resolved.as_posix()
        index = absolute.rfind(f"/{marker}")
        if index >= 0:
            healed = _candidate_from_suffix(absolute[index + len(marker) + 1 :])
            return healed
        return value

    healed = _candidate_from_suffix(normalized)
    return healed


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
        "composition_mode": "classic",
        "visual_source_strategy": "images_only",
        "available_footage": "",
        "footage_manifest": [],
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
        "scene_types": ["image", "video", "motion"],
        "render_backend": "ffmpeg",
    }


def default_image_profile() -> dict[str, Any]:
    """Default image generation/edit settings persisted in plan metadata."""
    return {
        "provider": "replicate",
        "generation_model": "qwen/qwen-image-2512",
        "edit_model": "qwen/qwen-image-edit-2511",
        "dashscope_edit_n": 1,
        "dashscope_edit_seed": "",
        "dashscope_edit_negative_prompt": "",
        "dashscope_edit_prompt_extend": True,
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
        "model_id": "eleven_multilingual_v2",
        "text_normalization": "auto",
        "stability": 0.38,
        "similarity_boost": 0.8,
        "style": 0.65,
        "use_speaker_boost": True,
        "exaggeration": 0.6,
    }


def normalize_agent_demo_profile(profile: Any) -> dict[str, Any]:
    """Normalize persisted demo-target metadata for agent-driven demo runs."""
    if not isinstance(profile, dict):
        return {}

    normalized: dict[str, Any] = {}
    for key in AGENT_DEMO_PROFILE_KEYS:
        if key not in profile or profile[key] in (None, ""):
            continue
        if key == "flow_hints":
            value = profile.get(key)
            if isinstance(value, list):
                normalized[key] = [str(item).strip() for item in value if str(item).strip()]
            elif isinstance(value, str) and value.strip():
                normalized[key] = [line.strip() for line in value.splitlines() if line.strip()]
            continue
        normalized[key] = str(profile.get(key) or "").strip()

    preferred_agent = str(normalized.get("preferred_agent") or "").strip().lower()
    if preferred_agent:
        normalized["preferred_agent"] = preferred_agent

    return normalized


def has_agent_demo_context(profile: Any) -> bool:
    """Return whether a demo-target profile contains enough context to imply a live demo run."""
    normalized = normalize_agent_demo_profile(profile)
    return any(
        str(normalized.get(key) or "").strip()
        for key in ("workspace_path", "app_url", "launch_command", "expected_url", "repo_url")
    )


def infer_composition_mode(
    brief: Any,
    *,
    agent_demo_profile: Any = None,
) -> str:
    """Infer composition mode when the user did not explicitly choose one."""
    raw = brief if isinstance(brief, dict) else {}
    requested = str(raw.get("composition_mode") or "").strip().lower()
    if requested in COMPOSITION_MODES:
        return requested

    normalized_brief = normalize_brief(raw)
    has_footage_manifest = bool(normalized_brief.get("footage_manifest"))
    if has_agent_demo_context(agent_demo_profile) or has_footage_manifest:
        return "hybrid"
    return "classic"


def resolve_render_backend(
    render_profile: Any,
    *,
    composition_mode: str,
) -> str:
    """Choose the effective render backend for the current composition mode."""
    raw = render_profile if isinstance(render_profile, dict) else {}
    requested = str(raw.get("render_backend") or "").strip().lower()
    if requested in RENDER_BACKENDS:
        return requested
    if composition_mode in {"motion_only", "hybrid"}:
        return "remotion"
    return "ffmpeg"


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


def _clean_speaker_label(value: str) -> str:
    label = str(value or "").strip()
    label = re.sub(r"^\[|\]$", "", label)
    label = re.sub(r"\*+", "", label).strip()
    label = re.sub(r"\s*\([^)]*\)\s*$", "", label).strip()
    if not label:
        return ""
    if "narrator" in label.lower():
        return "Narrator"
    return label.title()


def _looks_like_speaker_cue(value: str, *, allow_titlecase_names: bool) -> bool:
    raw = str(value or "").strip()
    if not raw:
        return False

    cue = re.sub(r"\*+", "", raw).strip()
    inner = cue[1:-1].strip() if cue.startswith("[") and cue.endswith("]") else cue
    bare = re.sub(r"\s*\([^)]*\)\s*$", "", inner).strip()
    words = re.findall(r"[A-Za-z]+(?:['-][A-Za-z]+)?", bare)
    if not words:
        return False

    normalized = " ".join(word.lower() for word in words)
    if normalized in {"narrator", "host", "speaker", "voiceover", "voice over"}:
        return True
    if cue.startswith("[") and cue.endswith("]"):
        return True
    if "(" in cue and ")" in cue:
        return True

    if len(words) < 2:
        return False

    if all(word.isupper() for word in words):
        return True
    if allow_titlecase_names and all(word[0].isupper() and word[1:].islower() for word in words):
        return True
    return False


def _extract_speaker_and_narration(value: Any) -> tuple[str | None, str]:
    text = str(value or "").strip()
    if not text:
        return None, ""

    # First handle a standalone cue line followed by narration text.
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if len(lines) >= 2:
        cue = re.sub(r"\*+", "", lines[0]).strip().rstrip(":").strip()
        if re.fullmatch(r"\[?[A-Za-z .'\-]+(?:\s*\([^)]*\))?\]?", cue) and _looks_like_speaker_cue(
            cue,
            allow_titlecase_names=True,
        ):
            speaker = _clean_speaker_label(cue)
            body = "\n".join(lines[1:]).strip()
            if speaker and body:
                return speaker, body

    # Then handle inline prefixes like "NARRATOR (V.O.): Text".
    inline_match = re.match(
        r"^\*{0,2}\[?([A-Za-z .'\-]+(?:\s*\([^)]*\))?)\]?\*{0,2}:\s*(.+)$",
        text,
        flags=re.S,
    )
    if inline_match:
        cue = inline_match.group(1)
        if not _looks_like_speaker_cue(cue, allow_titlecase_names=False):
            return None, text
        speaker = _clean_speaker_label(cue)
        body = inline_match.group(2).strip()
        if speaker and body:
            return speaker, body

    return None, text


def normalize_brief(
    brief: Any,
    *,
    base_dir: str | Path | None = None,
) -> dict[str, Any]:
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

    composition_mode = str(result.get("composition_mode") or "").strip()
    result["composition_mode"] = composition_mode if composition_mode in COMPOSITION_MODES else "classic"

    style_reference_paths = result.get("style_reference_paths")
    if isinstance(style_reference_paths, list):
        resolved_paths: list[str] = []
        base = Path(base_dir).expanduser().resolve() if base_dir not in (None, "") else None
        for item in style_reference_paths:
            if item is None or not str(item).strip():
                continue
            path = Path(str(item).strip()).expanduser()
            if path.is_absolute():
                resolved_paths.append(str(path.resolve()))
            elif base is not None:
                resolved_paths.append(str((base / path).resolve()))
            else:
                resolved_paths.append(str(path))
        result["style_reference_paths"] = resolved_paths
    else:
        result["style_reference_paths"] = []

    result["footage_manifest"] = normalize_footage_manifest(
        result.get("footage_manifest"),
        base_dir=base_dir,
    )

    visual_source_strategy = str(result.get("visual_source_strategy") or "").strip()
    result["visual_source_strategy"] = (
        visual_source_strategy if visual_source_strategy in VISUAL_SOURCE_STRATEGIES else "images_only"
    )

    # Allow raw_brief as a direct input path when source material is intentionally empty.
    if not result["source_material"] and result["raw_brief"]:
        result["source_material"] = result["raw_brief"]

    return result


def normalize_scene(
    scene: Any,
    index: int,
    *,
    base_dir: str | Path | None = None,
    project_name: str | None = None,
) -> dict[str, Any]:
    """Backfill a single scene with v1 generic defaults while preserving extra keys."""
    src = copy.deepcopy(scene if isinstance(scene, dict) else {})
    out = dict(src)

    out["id"] = index
    out["uid"] = str(src.get("uid") or str(uuid.uuid4())[:8])
    out["title"] = str(src.get("title") or f"Scene {index + 1}")
    parsed_speaker, cleaned_narration = _extract_speaker_and_narration(src.get("narration") or "")
    out["narration"] = cleaned_narration
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
    if src.get("speaker_name") or parsed_speaker:
        out["speaker_name"] = str(src.get("speaker_name") or parsed_speaker).strip()
    out["image_path"] = _normalize_project_asset_path(
        src.get("image_path"),
        base_dir=base_dir,
        project_name=project_name,
    )
    out["video_path"] = _normalize_project_asset_path(
        src.get("video_path"),
        base_dir=base_dir,
        project_name=project_name,
    )
    out["video_trim_start"] = _normalize_nonnegative_float(src.get("video_trim_start"), 0.0)
    out["video_trim_end"] = _normalize_optional_nonnegative_float(src.get("video_trim_end"))
    if out["video_trim_end"] is not None and out["video_trim_end"] < out["video_trim_start"]:
        out["video_trim_end"] = out["video_trim_start"]
    out["video_playback_speed"] = _normalize_float(src.get("video_playback_speed"), 1.0)
    out["video_hold_last_frame"] = bool(src.get("video_hold_last_frame", True))
    out["audio_path"] = _normalize_project_asset_path(
        src.get("audio_path"),
        base_dir=base_dir,
        project_name=project_name,
    )
    if "preview_path" in src:
        out["preview_path"] = _normalize_project_asset_path(
            src.get("preview_path"),
            base_dir=base_dir,
            project_name=project_name,
        )

    motion_raw = src.get("motion") if isinstance(src.get("motion"), dict) else {}
    if out["scene_type"] == "motion" or motion_raw:
        out["motion"] = {
            "template_id": str(motion_raw.get("template_id") or "").strip(),
            "props": motion_raw.get("props") if isinstance(motion_raw.get("props"), dict) else {},
            "render_path": _normalize_project_asset_path(
                motion_raw.get("render_path"),
                base_dir=base_dir,
                project_name=project_name,
            ),
            "preview_path": _normalize_project_asset_path(
                motion_raw.get("preview_path"),
                base_dir=base_dir,
                project_name=project_name,
            ),
            "rationale": str(motion_raw.get("rationale") or "").strip(),
        }
    elif "motion" in out:
        out["motion"] = None

    return out


def _merge_with_defaults(defaults: dict[str, Any], value: Any) -> dict[str, Any]:
    merged = dict(defaults)
    if isinstance(value, dict):
        for key, current in value.items():
            merged[key] = current
    return merged


def backfill_plan(
    plan: Any,
    *,
    base_dir: str | Path | None = None,
) -> dict[str, Any]:
    """
    Normalize an existing plan to the v1 generic schema.

    This is intentionally non-destructive for unknown keys and supports legacy
    plans that only contain `meta.input_text`.
    """
    root = copy.deepcopy(plan if isinstance(plan, dict) else {})
    meta = root.get("meta") if isinstance(root.get("meta"), dict) else {}
    meta = dict(meta)

    inferred_project_name = sanitize_project_name(meta.get("project_name") or "my_video")

    brief = normalize_brief(meta.get("brief"), base_dir=base_dir)
    brief["project_name"] = inferred_project_name
    if meta.get("footage_manifest") and not brief.get("footage_manifest"):
        brief["footage_manifest"] = normalize_footage_manifest(
            meta.get("footage_manifest"),
            base_dir=base_dir,
        )
    if brief.get("footage_manifest") and not brief.get("available_footage"):
        brief["available_footage"] = build_footage_summary(brief["footage_manifest"])

    input_text = str(meta.get("input_text") or "").strip()
    if not brief.get("source_material") and input_text:
        brief["source_mode"] = "source_text"
        brief["source_material"] = input_text

    raw_render_profile = meta.get("render_profile") if isinstance(meta.get("render_profile"), dict) else {}
    render_profile = _merge_with_defaults(default_render_profile(), raw_render_profile)
    render_profile["aspect_ratio"] = str(render_profile.get("aspect_ratio") or "16:9")
    render_profile["width"] = int(render_profile.get("width") or 1664)
    render_profile["height"] = int(render_profile.get("height") or 928)
    render_profile["fps"] = int(render_profile.get("fps") or 24)
    if not isinstance(render_profile.get("scene_types"), list):
        render_profile["scene_types"] = ["image", "video", "motion"]
    else:
        normalized_scene_types = [
            str(scene_type).strip().lower()
            for scene_type in render_profile["scene_types"]
            if str(scene_type).strip().lower() in SCENE_TYPES
        ]
        render_profile["scene_types"] = normalized_scene_types or ["image", "video", "motion"]
    render_profile["render_backend"] = resolve_render_backend(
        raw_render_profile,
        composition_mode=str(brief.get("composition_mode") or "classic"),
    )

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
    scenes = [
        normalize_scene(scene, index=i, base_dir=base_dir, project_name=inferred_project_name)
        for i, scene in enumerate(scenes_raw)
    ]

    meta["video_path"] = _normalize_project_asset_path(
        meta.get("video_path"),
        base_dir=base_dir,
        project_name=inferred_project_name,
    )

    meta["project_name"] = inferred_project_name
    meta["brief"] = brief
    meta["footage_manifest"] = brief.get("footage_manifest", [])
    if isinstance(meta.get("agent_demo_profile"), dict):
        meta["agent_demo_profile"] = normalize_agent_demo_profile(meta["agent_demo_profile"])
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
