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
SCENE_MANIFESTATIONS = ("authored_image", "native_remotion", "source_video")
COMPOSITION_MODES = ("auto", "classic", "motion_only", "hybrid")
EXPLICIT_COMPOSITION_MODES = ("classic", "motion_only", "hybrid")
VISUAL_SOURCE_STRATEGIES = ("images_only", "mixed_media", "video_preferred")
VIDEO_SCENE_STYLE_OPTIONS = ("auto", "cinematic", "speaking", "mixed")
TEXT_RENDER_MODES = ("visual_authored", "deterministic_overlay")
IMAGE_PROVIDERS = ("codex", "replicate", "local", "manual")
VIDEO_PROVIDERS = ("manual", "local", "replicate", "agent")
VIDEO_QUALITY_MODES = ("standard", "pro")
VIDEO_AUDIO_SOURCES = ("narration", "clip")
VIDEO_MODEL_SELECTION_MODES = ("automatic", "advanced")
VIDEO_SCENE_KINDS = ("cinematic", "speaking")
RENDER_BACKENDS = ("ffmpeg", "remotion")
RENDER_STRATEGIES = ("auto", "force_ffmpeg", "force_remotion")
AGENT_DEMO_PROFILE_KEYS = (
    "workspace_path",
    "app_url",
    "launch_command",
    "expected_url",
    "preferred_agent",
    "repo_url",
    "flow_hints",
)
_NATIVE_REMOTION_FAMILIES = {
    "bullet_stack",
    "kinetic_statements",
    "kinetic_title",
    "quote_focus",
    "software_demo_focus",
    "surreal_tableau_3d",
    "three_data_stage",
    # Clinical template compositions
    "cover_hook",
    "orientation",
    "synthesis_summary",
    "closing_cta",
    "clinical_explanation",
    "metric_improvement",
    "brain_region_focus",
    "metric_comparison",
    "timeline_progression",
    "analogy_metaphor",
}


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
        if str(resolved).startswith(str(base)):
            if resolved.exists() and resolved.is_file():
                return str(resolved)
            return None
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
        "paid_media_budget_usd": "",
        "composition_mode": "auto",
        "visual_source_strategy": "images_only",
        "video_scene_style": "auto",
        "text_render_mode": "visual_authored",
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
        "render_strategy": "auto",
        "render_backend": "ffmpeg",
        "render_backend_reason": "Classic image/video assembly has no Remotion-only requirements.",
        "text_render_mode": "visual_authored",
        "auto_compress_oversized_video": True,
        "compression_min_size_mb": 150.0,
        "compression_max_average_bitrate_mbps": 3.2,
        "compression_target_video_kbps": 2500,
        "compression_target_audio_kbps": 128,
    }


def default_image_profile() -> dict[str, Any]:
    """Default image generation/edit settings persisted in plan metadata."""
    return {
        "provider": "codex",
        "generation_model": "gpt-image-2",
        "edit_model": "gpt-image-2",
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
        "model_selection_mode": "automatic",
        "quality_mode": "standard",
        "generate_audio": True,
    }


def default_tts_profile() -> dict[str, Any]:
    """Default voice settings persisted in plan metadata."""
    return {
        "provider": "kokoro",
        "voice": "af_bella",
        "speed": 1.1,
        "model_id": "gpt-4o-mini-tts",
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
    if requested in EXPLICIT_COMPOSITION_MODES:
        return requested

    normalized_brief = normalize_brief(raw)
    has_footage_manifest = bool(normalized_brief.get("footage_manifest"))
    prefers_mixed_media = normalized_brief.get("visual_source_strategy") in {"mixed_media", "video_preferred"}
    if has_footage_manifest:
        return "hybrid"
    if has_agent_demo_context(agent_demo_profile) and prefers_mixed_media:
        return "hybrid"
    return "classic"


def _render_backend_reason_from_scenes(scenes: list[dict[str, Any]] | None) -> str | None:
    if not scenes:
        return None
    for scene in scenes:
        payload = scene_composition_payload(scene)
        title = str(scene.get("title") or "Untitled scene").strip() or "Untitled scene"
        if str(scene.get("scene_type") or "").strip().lower() == "motion":
            return f'Scene "{title}" has motion metadata, but auto render stays on classic assembly.'
        if str(payload.get("mode") or "").strip().lower() == "native":
            return f'Scene "{title}" has native composition metadata, but auto render stays on classic assembly.'
        if str(payload.get("mode") or "").strip().lower() == "overlay":
            return f'Scene "{title}" has overlay metadata, but auto render stays on classic assembly.'
        if payload.get("transition_after"):
            return f'Scene "{title}" has transition metadata, but auto render stays on classic assembly.'
    return None


def remotion_explicitly_enabled(render_profile: Any) -> bool:
    """Return whether a render profile has opted into the Remotion renderer."""
    raw = render_profile if isinstance(render_profile, dict) else {}
    if resolve_render_strategy(raw.get("render_strategy")) == "force_remotion":
        return True
    render_backend = str(raw.get("render_backend") or "").strip().lower()
    reason = str(raw.get("render_backend_reason") or "").strip().lower()
    return render_backend == "remotion" and "explicit" in reason


def resolve_render_backend_details(
    render_profile: Any,
    *,
    composition_mode: str,
    scenes: list[dict[str, Any]] | None = None,
) -> tuple[str, str]:
    raw = render_profile if isinstance(render_profile, dict) else {}
    requested_strategy = str(raw.get("render_strategy") or "").strip().lower()
    if requested_strategy == "force_ffmpeg":
        return "ffmpeg", "Classic assembly forced by render_strategy=force_ffmpeg."
    if requested_strategy == "force_remotion":
        return "remotion", "Remotion forced by render_strategy=force_remotion."

    if composition_mode == "motion_only":
        return "remotion", "Remotion selected by explicit composition_mode=motion_only."

    scene_reason = _render_backend_reason_from_scenes(scenes)
    if scene_reason:
        return "ffmpeg", scene_reason

    if composition_mode == "hybrid":
        return "ffmpeg", (
            f"Classic assembly selected for composition_mode={composition_mode}; "
            "use render_strategy=force_remotion for the native renderer."
        )

    requested = str(raw.get("render_backend") or "").strip().lower()
    if requested in RENDER_BACKENDS:
        if requested == "remotion":
            return "ffmpeg", "Classic assembly selected; render_backend=remotion requires render_strategy=force_remotion."
        return "ffmpeg", "Classic image/video assembly selected by explicit render_backend preference."

    return "ffmpeg", "Classic image/video assembly has no Remotion-only requirements."


def resolve_render_backend(
    render_profile: Any,
    *,
    composition_mode: str,
    scenes: list[dict[str, Any]] | None = None,
) -> str:
    """Choose the effective render backend for the current composition mode."""
    return resolve_render_backend_details(
        render_profile,
        composition_mode=composition_mode,
        scenes=scenes,
    )[0]


def sanitize_project_name(value: Any, fallback: str = "my_video") -> str:
    """Normalize project names to a filesystem-safe format."""
    raw = str(value or "").strip()
    if not raw:
        raw = fallback
    raw = raw.replace(" ", "_")
    cleaned = re.sub(r"[^a-zA-Z0-9_-]", "_", raw)
    return cleaned or fallback


def resolve_text_render_mode(value: Any) -> str:
    """Normalize the project-wide text rendering strategy."""
    normalized = str(value or "").strip().lower()
    return normalized if normalized in TEXT_RENDER_MODES else "visual_authored"


def resolve_render_strategy(value: Any) -> str:
    """Normalize the persisted render-strategy override."""
    normalized = str(value or "").strip().lower()
    return normalized if normalized in RENDER_STRATEGIES else "auto"


def _normalize_scene_manifestation(value: Any) -> str | None:
    normalized = str(value or "").strip().lower()
    return normalized if normalized in SCENE_MANIFESTATIONS else None


def _composition_family_implies_native_remotion(value: Any) -> bool:
    return str(value or "").strip().lower() in _NATIVE_REMOTION_FAMILIES


def _infer_scene_manifestation(
    *,
    scene_type: str,
    family: Any,
    mode: Any,
) -> str:
    if scene_type == "video":
        return "source_video"
    if str(mode or "").strip().lower() in {"native", "overlay"}:
        return "native_remotion"
    if _composition_family_implies_native_remotion(family):
        return "native_remotion"
    return "authored_image"


def default_scene_composition(scene_type: str) -> dict[str, Any]:
    normalized_type = str(scene_type or "image").strip().lower()
    if normalized_type == "motion":
        return {
            "family": "kinetic_title",
            "mode": "native",
            "manifestation": "native_remotion",
            "props": {},
            "transition_after": None,
            "data": {},
            "render_path": None,
            "preview_path": None,
            "rationale": "",
        }
    return {
        "family": "static_media",
        "mode": "none",
        "manifestation": "source_video" if normalized_type == "video" else "authored_image",
        "props": {},
        "transition_after": None,
        "data": {},
        "render_path": None,
        "preview_path": None,
        "rationale": "",
    }


def _normalize_scene_transition(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    kind = str(value.get("kind") or value.get("presentation") or "").strip().lower()
    if not kind:
        return None
    raw_duration = value.get("duration_in_frames") if "duration_in_frames" in value else value.get("durationInFrames")
    try:
        duration = max(1, int(raw_duration)) if raw_duration not in (None, "") else 20
    except (TypeError, ValueError):
        duration = 20
    return {
        "kind": kind,
        "duration_in_frames": duration,
    }


def _relative_review_asset_path(
    raw_path: Any,
    *,
    base_dir: str | Path | None = None,
    project_name: str | None = None,
) -> str | None:
    normalized = _normalize_project_asset_path(
        raw_path,
        base_dir=base_dir,
        project_name=project_name,
    )
    if normalized is None:
        value = str(raw_path or "").strip()
        return value or None
    base = Path(base_dir).expanduser().resolve() if base_dir not in (None, "") else None
    if base is None:
        return normalized
    path = Path(str(normalized)).expanduser()
    if not path.is_absolute():
        return str(path).replace("\\", "/")
    resolved = path.resolve()
    if str(resolved).startswith(str(base)):
        return str(resolved.relative_to(base)).replace("\\", "/")
    return str(resolved)


def _normalize_review_frame_refs(
    value: Any,
    *,
    base_dir: str | Path | None = None,
    project_name: str | None = None,
) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    normalized: list[dict[str, Any]] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        frame_role = str(item.get("frame_role") or "").strip()
        if not frame_role:
            continue
        try:
            timestamp = float(item.get("timestamp_seconds") or 0.0)
        except (TypeError, ValueError):
            timestamp = 0.0
        normalized_item = {
            "frame_role": frame_role,
            "path": _relative_review_asset_path(
                item.get("path"),
                base_dir=base_dir,
                project_name=project_name,
            ),
            "timestamp_seconds": max(timestamp, 0.0),
        }
        candidate_id = str(item.get("candidate_id") or "").strip()
        if candidate_id:
            normalized_item["candidate_id"] = candidate_id
        normalized.append(normalized_item)
    return normalized


def _normalize_candidate_outputs(
    value: Any,
    *,
    base_dir: str | Path | None = None,
    project_name: str | None = None,
) -> dict[str, dict[str, Any]]:
    if not isinstance(value, dict):
        return {}
    normalized: dict[str, dict[str, Any]] = {}
    for key, item in value.items():
        if not isinstance(item, dict):
            continue
        candidate_id = str(item.get("candidate_id") or key or "").strip()
        if not candidate_id:
            continue
        normalized[candidate_id] = {
            "candidate_id": candidate_id,
            "label": str(item.get("label") or candidate_id).strip() or candidate_id,
            "candidate_type": str(item.get("candidate_type") or "").strip() or None,
            "candidate_spec": copy.deepcopy(item.get("candidate_spec")),
            "source_kind": str(item.get("source_kind") or "").strip() or None,
            "source_path": _relative_review_asset_path(
                item.get("source_path"),
                base_dir=base_dir,
                project_name=project_name,
            ),
            "review_status": str(item.get("review_status") or "").strip() or None,
            "frame_refs": _normalize_review_frame_refs(
                item.get("frame_refs"),
                base_dir=base_dir,
                project_name=project_name,
            ),
        }
    return normalized


def _normalize_judge_verdict(
    value: Any,
    *,
    base_dir: str | Path | None = None,
    project_name: str | None = None,
) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    normalized = dict(value)
    normalized["trigger"] = str(value.get("trigger") or "").strip() or None
    provider = str(value.get("judge_provider") or value.get("provider") or "").strip() or None
    model = str(value.get("judge_model") or value.get("model") or "").strip() or None
    normalized["judge_provider"] = provider
    normalized["judge_model"] = model
    normalized["provider"] = provider
    normalized["model"] = model
    normalized["winner"] = str(value.get("winner") or "").strip() or None
    normalized["reasons"] = [str(item).strip() for item in (value.get("reasons") or []) if str(item).strip()]
    raw_notes = value.get("candidate_notes")
    if isinstance(raw_notes, dict):
        normalized["candidate_notes"] = {
            str(candidate_id).strip(): [str(note).strip() for note in notes if str(note).strip()]
            for candidate_id, notes in raw_notes.items()
            if str(candidate_id).strip() and isinstance(notes, list)
        }
    else:
        normalized["candidate_notes"] = {}
    raw_text_repairs = value.get("text_repairs")
    if isinstance(raw_text_repairs, list):
        normalized["text_repairs"] = [
            {
                "candidate_id": str(item.get("candidate_id") or "").strip(),
                "wrong_text": str(item.get("wrong_text") or "").strip(),
                "correct_text": str(item.get("correct_text") or "").strip(),
                "reason": str(item.get("reason") or "").strip(),
            }
            for item in raw_text_repairs
            if isinstance(item, dict)
            and str(item.get("candidate_id") or "").strip()
            and str(item.get("wrong_text") or "").strip()
            and str(item.get("correct_text") or "").strip()
        ]
    else:
        normalized["text_repairs"] = []
    normalized["frame_refs"] = _normalize_review_frame_refs(
        value.get("frame_refs"),
        base_dir=base_dir,
        project_name=project_name,
    )
    return normalized


def _normalize_composition_data_number(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed


def _normalize_composition_data_points(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    return [str(item).strip() for item in values if str(item).strip()]


def _normalize_composition_series(values: Any) -> list[dict[str, Any]]:
    if not isinstance(values, list):
        return []

    normalized: list[dict[str, Any]] = []
    for index, entry in enumerate(values):
        if not isinstance(entry, dict):
            continue
        item = copy.deepcopy(entry)
        item["id"] = str(item.get("id") or f"series_{index + 1}").strip()
        item["label"] = str(item.get("label") or "").strip()
        item["type"] = "bar" if str(item.get("type") or "").strip() == "bar" else "line"
        raw_points = item.get("points") if isinstance(item.get("points"), list) else []
        points: list[dict[str, Any]] = []
        for point in raw_points:
            if not isinstance(point, dict):
                continue
            x_value = str(point.get("x") or "").strip()
            if not x_value:
                continue
            normalized_point = copy.deepcopy(point)
            normalized_point["x"] = x_value
            normalized_point["y"] = _normalize_composition_data_number(point.get("y"))
            label = str(point.get("label") or "").strip()
            if label:
                normalized_point["label"] = label
            elif "label" in normalized_point:
                normalized_point.pop("label", None)
            points.append(normalized_point)
        item["points"] = points
        normalized.append(item)
    return normalized


def _normalize_composition_reference_bands(values: Any) -> list[dict[str, Any]]:
    if not isinstance(values, list):
        return []

    normalized: list[dict[str, Any]] = []
    for index, entry in enumerate(values):
        if not isinstance(entry, dict):
            continue
        item = copy.deepcopy(entry)
        y_min = _normalize_composition_data_number(item.get("yMin"))
        y_max = _normalize_composition_data_number(item.get("yMax"))
        if y_min is None or y_max is None:
            continue
        item["id"] = str(item.get("id") or f"reference_band_{index + 1}").strip()
        item["label"] = str(item.get("label") or "").strip() or "Reference range"
        item["yMin"] = min(y_min, y_max)
        item["yMax"] = max(y_min, y_max)
        x_range = item.get("xRange")
        if isinstance(x_range, list) and len(x_range) == 2:
            start = str(x_range[0] or "").strip()
            end = str(x_range[1] or "").strip()
            item["xRange"] = [start, end] if start and end else None
        elif "xRange" in item:
            item.pop("xRange", None)
        normalized.append(item)
    return normalized


def _normalize_composition_callouts(values: Any) -> list[dict[str, Any]]:
    if not isinstance(values, list):
        return []

    normalized: list[dict[str, Any]] = []
    for index, entry in enumerate(values):
        if not isinstance(entry, dict):
            continue
        item = copy.deepcopy(entry)
        label = str(item.get("label") or "").strip()
        if not label:
            continue
        item["id"] = str(item.get("id") or f"callout_{index + 1}").strip()
        item["label"] = label
        for key in ("x", "fromX", "toX"):
            if key in item:
                value = str(item.get(key) or "").strip()
                if value:
                    item[key] = value
                else:
                    item.pop(key, None)
        y_value = _normalize_composition_data_number(item.get("y"))
        if y_value is not None:
            item["y"] = y_value
        elif "y" in item:
            item.pop("y", None)
        normalized.append(item)
    return normalized


def _normalize_composition_data(
    value: Any,
    *,
    legacy_data_points: list[str] | None = None,
) -> dict[str, Any] | list[Any]:
    if isinstance(value, list):
        return copy.deepcopy(value)

    if isinstance(value, dict):
        normalized = copy.deepcopy(value)
        data_points = _normalize_composition_data_points(normalized.get("data_points"))
        if data_points:
            normalized["data_points"] = data_points
        elif "data_points" in normalized:
            normalized.pop("data_points", None)

        series = _normalize_composition_series(normalized.get("series"))
        if series:
            normalized["series"] = series
        elif "series" in normalized:
            normalized.pop("series", None)

        reference_bands = _normalize_composition_reference_bands(normalized.get("referenceBands"))
        if reference_bands:
            normalized["referenceBands"] = reference_bands
        elif "referenceBands" in normalized:
            normalized.pop("referenceBands", None)

        callouts = _normalize_composition_callouts(normalized.get("callouts"))
        if callouts:
            normalized["callouts"] = callouts
        elif "callouts" in normalized:
            normalized.pop("callouts", None)

        if "xAxisLabel" in normalized:
            axis = str(normalized.get("xAxisLabel") or "").strip()
            if axis:
                normalized["xAxisLabel"] = axis
            else:
                normalized.pop("xAxisLabel", None)
        if "yAxisLabel" in normalized:
            axis = str(normalized.get("yAxisLabel") or "").strip()
            if axis:
                normalized["yAxisLabel"] = axis
            else:
                normalized.pop("yAxisLabel", None)
        return normalized

    normalized_legacy = [str(item).strip() for item in (legacy_data_points or []) if str(item).strip()]
    return {"data_points": normalized_legacy} if normalized_legacy else {}


def scene_composition_payload(scene: Any) -> dict[str, Any]:
    src = scene if isinstance(scene, dict) else {}
    composition_raw = src.get("composition") if isinstance(src.get("composition"), dict) else {}
    motion_raw = src.get("motion") if isinstance(src.get("motion"), dict) else {}
    legacy_intent = src.get("composition_intent") if isinstance(src.get("composition_intent"), dict) else {}
    scene_type = str(src.get("scene_type") or "image").strip().lower()
    defaults = default_scene_composition(scene_type)
    explicit_manifestation = _normalize_scene_manifestation(composition_raw.get("manifestation"))
    allow_legacy_shape_hints = explicit_manifestation is None
    allow_legacy_motion_mirror = explicit_manifestation in {None, "native_remotion"}
    family = str(
        composition_raw.get("family")
        or (legacy_intent.get("family_hint") if allow_legacy_shape_hints else None)
        or (motion_raw.get("template_id") if allow_legacy_motion_mirror else None)
        or defaults["family"]
    ).strip() or defaults["family"]
    mode = str(
        composition_raw.get("mode")
        or (legacy_intent.get("mode_hint") if allow_legacy_shape_hints else None)
        or defaults["mode"]
    ).strip().lower() or defaults["mode"]
    if mode not in {"none", "overlay", "native"}:
        mode = defaults["mode"]

    props = (
        composition_raw.get("props")
        if isinstance(composition_raw.get("props"), dict)
        else motion_raw.get("props")
        if allow_legacy_motion_mirror and isinstance(motion_raw.get("props"), dict)
        else {}
    )
    legacy_data_points: list[str] = []
    if isinstance(src.get("data_points"), list):
        legacy_data_points = [str(item).strip() for item in src.get("data_points") if str(item).strip()]
    elif isinstance(legacy_intent.get("data_points"), list):
        legacy_data_points = [str(item).strip() for item in legacy_intent.get("data_points") if str(item).strip()]
    data = _normalize_composition_data(
        composition_raw.get("data"),
        legacy_data_points=legacy_data_points,
    )
    transition_after = _normalize_scene_transition(composition_raw.get("transition_after"))
    if transition_after is None:
        transition_hint = str(src.get("transition_hint") or legacy_intent.get("transition_after") or "").strip().lower()
        if transition_hint in {"fade", "wipe"}:
            transition_after = {"kind": transition_hint, "duration_in_frames": 20}

    manifestation = explicit_manifestation or _infer_scene_manifestation(
        scene_type=scene_type,
        family=family,
        mode=mode,
    )
    return {
        "family": family,
        "mode": mode,
        "manifestation": manifestation,
        "props": props,
        "transition_after": transition_after,
        "data": data if isinstance(data, (dict, list)) else {},
        "render_path": composition_raw.get("render_path")
        or (motion_raw.get("render_path") if allow_legacy_motion_mirror else None),
        "preview_path": composition_raw.get("preview_path")
        or (motion_raw.get("preview_path") if allow_legacy_motion_mirror else None),
        "rationale": str(
            composition_raw.get("rationale")
            or (motion_raw.get("rationale") if allow_legacy_motion_mirror else None)
            or src.get("staging_notes")
            or legacy_intent.get("motion_notes")
            or legacy_intent.get("layout")
            or ""
        ).strip(),
    }


def scene_primary_manifestation(scene: Any) -> str:
    payload = scene_composition_payload(scene)
    return str(payload.get("manifestation") or "authored_image").strip().lower() or "authored_image"


def scene_requires_remotion(scene: Any) -> bool:
    payload = scene_composition_payload(scene)
    scene_type = str((scene or {}).get("scene_type") or "image").strip().lower() if isinstance(scene, dict) else "image"
    if scene_type == "motion":
        return True
    if payload["mode"] in {"overlay", "native"}:
        return True
    return bool(payload["transition_after"])


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


def _normalize_bool(value: Any, fallback: bool) -> bool:
    if isinstance(value, bool):
        return value
    normalized = str(value or "").strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    return fallback


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
        "paid_media_budget_usd",
        "available_footage",
        "style_reference_summary",
        "raw_brief",
    ):
        result[key] = str(result.get(key) or "").strip()

    composition_mode = str(result.get("composition_mode") or "").strip()
    result["composition_mode"] = composition_mode if composition_mode in COMPOSITION_MODES else "auto"

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
    video_scene_style = str(result.get("video_scene_style") or "").strip().lower()
    result["video_scene_style"] = (
        video_scene_style if video_scene_style in VIDEO_SCENE_STYLE_OPTIONS else "auto"
    )
    result["text_render_mode"] = resolve_text_render_mode(result.get("text_render_mode"))

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
    out["staging_notes"] = str(src.get("staging_notes") or "").strip() or None
    data_points = src.get("data_points")
    if isinstance(data_points, list):
        out["data_points"] = [str(item).strip() for item in data_points if str(item).strip()]
    else:
        out["data_points"] = []
    transition_hint = str(src.get("transition_hint") or "").strip().lower()
    out["transition_hint"] = transition_hint if transition_hint in {"fade", "wipe"} else None

    history = src.get("refinement_history")
    out["refinement_history"] = history if isinstance(history, list) else []
    if src.get("speaker_name") or parsed_speaker:
        out["speaker_name"] = str(src.get("speaker_name") or parsed_speaker).strip()
    out["tts_override_enabled"] = bool(src.get("tts_override_enabled", False))
    raw_tts_provider = str(src.get("tts_provider") or "").strip().lower()
    out["tts_provider"] = raw_tts_provider or None
    raw_tts_voice = str(src.get("tts_voice") or "").strip()
    out["tts_voice"] = raw_tts_voice or None
    if src.get("tts_speed") in (None, ""):
        out["tts_speed"] = None
    else:
        out["tts_speed"] = _normalize_float(src.get("tts_speed"), 1.0)
    raw_elevenlabs_model_id = str(src.get("elevenlabs_model_id") or "").strip()
    out["elevenlabs_model_id"] = raw_elevenlabs_model_id or None
    raw_elevenlabs_text_normalization = str(src.get("elevenlabs_text_normalization") or "").strip().lower()
    out["elevenlabs_text_normalization"] = raw_elevenlabs_text_normalization or None
    if src.get("elevenlabs_stability") in (None, ""):
        out["elevenlabs_stability"] = None
    else:
        out["elevenlabs_stability"] = _normalize_float(src.get("elevenlabs_stability"), 0.38)
    if src.get("elevenlabs_similarity_boost") in (None, ""):
        out["elevenlabs_similarity_boost"] = None
    else:
        out["elevenlabs_similarity_boost"] = _normalize_float(src.get("elevenlabs_similarity_boost"), 0.8)
    if src.get("elevenlabs_style") in (None, ""):
        out["elevenlabs_style"] = None
    else:
        out["elevenlabs_style"] = _normalize_float(src.get("elevenlabs_style"), 0.65)
    if src.get("elevenlabs_use_speaker_boost") is None:
        out["elevenlabs_use_speaker_boost"] = None
    else:
        out["elevenlabs_use_speaker_boost"] = bool(src.get("elevenlabs_use_speaker_boost"))
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
    video_audio_source = str(src.get("video_audio_source") or "narration").strip().lower()
    out["video_audio_source"] = video_audio_source if video_audio_source in VIDEO_AUDIO_SOURCES else "narration"
    video_scene_kind = str(src.get("video_scene_kind") or "").strip().lower()
    if out["scene_type"] == "video":
        out["video_scene_kind"] = video_scene_kind if video_scene_kind in VIDEO_SCENE_KINDS else None
    elif "video_scene_kind" in out:
        out["video_scene_kind"] = video_scene_kind if video_scene_kind in VIDEO_SCENE_KINDS else None
    out["video_reference_image_path"] = _normalize_project_asset_path(
        src.get("video_reference_image_path"),
        base_dir=base_dir,
        project_name=project_name,
    )
    out["video_reference_audio_path"] = _normalize_project_asset_path(
        src.get("video_reference_audio_path"),
        base_dir=base_dir,
        project_name=project_name,
    )
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
    candidate_outputs = _normalize_candidate_outputs(
        src.get("candidate_outputs"),
        base_dir=base_dir,
        project_name=project_name,
    )
    if candidate_outputs:
        out["candidate_outputs"] = candidate_outputs
    elif "candidate_outputs" in out:
        out["candidate_outputs"] = {}
    judge_verdict = _normalize_judge_verdict(
        src.get("judge_verdict"),
        base_dir=base_dir,
        project_name=project_name,
    )
    if judge_verdict:
        out["judge_verdict"] = judge_verdict
    elif "judge_verdict" in out:
        out["judge_verdict"] = {}

    composition = scene_composition_payload(src)
    out["composition"] = {
        "family": composition["family"],
        "mode": composition["mode"],
        "manifestation": composition["manifestation"],
        "props": composition["props"] if isinstance(composition["props"], dict) else {},
        "transition_after": composition["transition_after"],
        "data": composition["data"],
        "render_path": _normalize_project_asset_path(
            composition.get("render_path"),
            base_dir=base_dir,
            project_name=project_name,
        ),
        "preview_path": _normalize_project_asset_path(
            composition.get("preview_path"),
            base_dir=base_dir,
            project_name=project_name,
        ),
        "rationale": str(composition.get("rationale") or "").strip(),
    }

    motion_raw = src.get("motion") if isinstance(src.get("motion"), dict) else {}
    if out["scene_type"] == "motion" or motion_raw:
        raw_template_id = str(motion_raw.get("template_id") or "").strip()
        template_id = raw_template_id or out["composition"]["family"] or ""
        if template_id in {"", "kinetic_title"} and out["composition"]["family"]:
            template_id = str(out["composition"]["family"] or "").strip()
        motion_props = motion_raw.get("props") if isinstance(motion_raw.get("props"), dict) else None
        if template_id != raw_template_id and isinstance(out["composition"]["props"], dict):
            motion_props = out["composition"]["props"]
        out["motion"] = {
            "template_id": template_id,
            "props": motion_props if isinstance(motion_props, dict) else out["composition"]["props"],
            "render_path": _normalize_project_asset_path(
                motion_raw.get("render_path") or out["composition"]["render_path"],
                base_dir=base_dir,
                project_name=project_name,
            ),
            "preview_path": _normalize_project_asset_path(
                motion_raw.get("preview_path") or out["composition"]["preview_path"],
                base_dir=base_dir,
                project_name=project_name,
            ),
            "rationale": str(motion_raw.get("rationale") or out["composition"]["rationale"] or "").strip(),
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

    raw_image_profile = meta.get("image_profile") if isinstance(meta.get("image_profile"), dict) else {}
    image_profile = _merge_with_defaults(default_image_profile(), raw_image_profile)
    if meta.get("image_provider") and "provider" not in raw_image_profile:
        image_profile["provider"] = str(meta["image_provider"])
    if meta.get("image_model") and "generation_model" not in raw_image_profile:
        image_profile["generation_model"] = str(meta["image_model"])
    provider = str(image_profile.get("provider") or default_image_profile()["provider"]).strip().lower()
    image_profile["provider"] = provider if provider in IMAGE_PROVIDERS else str(default_image_profile()["provider"])
    image_profile["generation_model"] = str(
        image_profile.get("generation_model") or default_image_profile()["generation_model"]
    ).strip()
    image_profile["edit_model"] = str(
        image_profile.get("edit_model") or default_image_profile()["edit_model"]
    ).strip()

    raw_video_profile = meta.get("video_profile") if isinstance(meta.get("video_profile"), dict) else {}
    video_profile = _merge_with_defaults(default_video_profile(), raw_video_profile)
    if meta.get("video_provider") and "provider" not in raw_video_profile:
        video_profile["provider"] = str(meta["video_provider"])
    if meta.get("video_model") and "generation_model" not in raw_video_profile:
        video_profile["generation_model"] = str(meta["video_model"])
    if meta.get("video_quality_mode") and "quality_mode" not in raw_video_profile:
        video_profile["quality_mode"] = str(meta["video_quality_mode"])
    if meta.get("video_generate_audio") is not None and "generate_audio" not in raw_video_profile:
        video_profile["generate_audio"] = bool(meta["video_generate_audio"])
    if meta.get("video_model_selection_mode") and "model_selection_mode" not in raw_video_profile:
        video_profile["model_selection_mode"] = str(meta["video_model_selection_mode"])
    video_provider = str(video_profile.get("provider") or "manual").strip().lower()
    video_profile["provider"] = video_provider if video_provider in VIDEO_PROVIDERS else "manual"
    video_profile["generation_model"] = str(video_profile.get("generation_model") or "").strip()
    selection_mode = str(video_profile.get("model_selection_mode") or "automatic").strip().lower()
    video_profile["model_selection_mode"] = (
        selection_mode if selection_mode in VIDEO_MODEL_SELECTION_MODES else "automatic"
    )
    quality_mode = str(video_profile.get("quality_mode") or "standard").strip().lower()
    video_profile["quality_mode"] = quality_mode if quality_mode in VIDEO_QUALITY_MODES else "standard"
    raw_generate_audio = video_profile.get("generate_audio")
    video_profile["generate_audio"] = True if raw_generate_audio is None else bool(raw_generate_audio)

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

    render_profile = _merge_with_defaults(default_render_profile(), raw_render_profile)
    render_profile["aspect_ratio"] = str(render_profile.get("aspect_ratio") or "16:9")
    render_profile["width"] = int(render_profile.get("width") or 1664)
    render_profile["height"] = int(render_profile.get("height") or 928)
    render_profile["fps"] = int(render_profile.get("fps") or 24)
    render_profile["render_strategy"] = resolve_render_strategy(
        raw_render_profile.get("render_strategy")
    )
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
        scenes=scenes,
    )
    render_profile["render_backend_reason"] = resolve_render_backend_details(
        raw_render_profile,
        composition_mode=str(brief.get("composition_mode") or "classic"),
        scenes=scenes,
    )[1]
    render_profile["text_render_mode"] = resolve_text_render_mode(
        raw_render_profile.get("text_render_mode") or brief.get("text_render_mode")
    )
    render_profile["auto_compress_oversized_video"] = _normalize_bool(
        render_profile.get("auto_compress_oversized_video"),
        True,
    )
    render_profile["compression_min_size_mb"] = _normalize_float(
        render_profile.get("compression_min_size_mb"),
        150.0,
    )
    render_profile["compression_max_average_bitrate_mbps"] = _normalize_float(
        render_profile.get("compression_max_average_bitrate_mbps"),
        3.2,
    )
    render_profile["compression_target_video_kbps"] = int(
        _normalize_float(render_profile.get("compression_target_video_kbps"), 2500.0)
    )
    render_profile["compression_target_audio_kbps"] = int(
        _normalize_float(render_profile.get("compression_target_audio_kbps"), 128.0)
    )
    brief["text_render_mode"] = render_profile["text_render_mode"]

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
    meta["video_model_selection_mode"] = video_profile["model_selection_mode"]
    meta["video_quality_mode"] = video_profile["quality_mode"]
    meta["video_generate_audio"] = video_profile["generate_audio"]
    meta["tts_profile"] = tts_profile

    # Keep legacy fallback for older tooling that expects input_text.
    if not input_text and brief.get("source_material"):
        meta["input_text"] = brief["source_material"]

    root["meta"] = meta
    root["scenes"] = scenes
    return root
