"""Workflow helpers shared by the app and batch scripts."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from .composition_planner import plan_scene_compositions
from .costs import append_actual_cost_entry
from .director import generate_storyboard_with_metadata
from .remotion_render import infer_motion_template
from .runtime import available_tts_providers
from .treatment_planner import plan_scene_treatments_with_metadata
from .project_schema import (
    backfill_plan,
    default_image_profile,
    default_render_profile,
    default_tts_profile,
    default_video_profile,
    normalize_brief,
    normalize_scene,
    sanitize_project_name,
)
from .voice_gen import DEFAULT_ELEVENLABS_VOICE, DEFAULT_VOICE, ELEVENLABS_VOICES


def _utc_now() -> str:
    return datetime.utcnow().isoformat()


def _motion_scene_defaults(scene: dict[str, Any]) -> dict[str, Any]:
    lines = [str(item).strip() for item in (scene.get("on_screen_text") or []) if str(item).strip()]
    title = str(scene.get("title") or "").strip()
    narration = str(scene.get("narration") or "").strip()
    motion = scene.get("motion") if isinstance(scene.get("motion"), dict) else {}
    props = motion.get("props") if isinstance(motion.get("props"), dict) else {}
    return {
        "template_id": str(motion.get("template_id") or "").strip() or infer_motion_template(scene),
        "props": {
            "headline": str(props.get("headline") or (lines[0] if lines else title) or "Motion beat").strip(),
            "body": str(props.get("body") or "\n".join(lines[1:3]) or narration[:180]).strip(),
            "kicker": str(props.get("kicker") or title or "Cathode").strip(),
            "bullets": props.get("bullets") if isinstance(props.get("bullets"), list) else lines[:4],
            "accent": str(props.get("accent") or "").strip(),
        },
        "render_path": motion.get("render_path"),
        "preview_path": motion.get("preview_path"),
        "rationale": str(motion.get("rationale") or "Auto-composed from a motion-only brief.").strip(),
    }


def _brief_voice_request_text(brief: dict[str, Any]) -> str:
    parts = [
        brief.get("source_material"),
        brief.get("raw_brief"),
        brief.get("video_goal"),
        brief.get("must_include"),
        brief.get("must_avoid"),
    ]
    return "\n".join(str(value or "").strip() for value in parts if str(value or "").strip()).lower()


def _brief_requests_multi_voice(brief: dict[str, Any]) -> bool:
    text = _brief_voice_request_text(brief)
    phrases = (
        "different voice",
        "different voices",
        "multiple voices",
        "all eleven labs voices",
        "all 11 labs voices",
        "seven voices",
        "7 voices",
        "voice for every section",
        "voice for each section",
        "voice for every scene",
        "voice for each scene",
    )
    return any(phrase in text for phrase in phrases)


def _brief_prefers_elevenlabs(brief: dict[str, Any]) -> bool:
    text = _brief_voice_request_text(brief)
    return any(phrase in text for phrase in ("elevenlabs", "eleven labs", "11 labs"))


def _cloud_media_prefers_elevenlabs(
    *,
    image_profile: dict[str, Any],
    video_profile: dict[str, Any],
    tts_profile: dict[str, Any],
) -> bool:
    available = available_tts_providers()
    if "elevenlabs" not in available:
        return False
    provider = str(tts_profile.get("provider") or "kokoro").strip().lower() or "kokoro"
    using_default_kokoro = provider == "kokoro" and str(tts_profile.get("voice") or "") in {"", DEFAULT_VOICE}
    if not using_default_kokoro:
        return False
    image_provider = str(image_profile.get("provider") or "manual").strip().lower()
    video_provider = str(video_profile.get("provider") or "manual").strip().lower()
    return image_provider == "replicate" or video_provider == "replicate"


def _speaker_key(value: Any) -> str:
    return " ".join(str(value or "").strip().lower().split())


def _speaker_is_narrator(value: Any) -> bool:
    normalized = _speaker_key(value)
    return normalized in {"", "narrator", "host", "speaker", "voiceover", "voice over", "bella"}


def _elevenlabs_voice_pool() -> list[str]:
    narrator_first = [DEFAULT_ELEVENLABS_VOICE]
    others = [voice for voice in ELEVENLABS_VOICES.keys() if voice != DEFAULT_ELEVENLABS_VOICE]
    return narrator_first + others


def _pick_scene_voice_plan(
    scenes: list[dict[str, Any]],
    *,
    brief: dict[str, Any],
    tts_profile: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    profile = dict(tts_profile or default_tts_profile())
    available = available_tts_providers()
    distinct_speakers = [
        key
        for key in dict.fromkeys(_speaker_key(scene.get("speaker_name")) for scene in scenes)
        if key
    ]
    multi_voice_requested = _brief_requests_multi_voice(brief) or len(distinct_speakers) > 1
    if not multi_voice_requested:
        return scenes, profile

    provider = str(profile.get("provider") or "kokoro").strip().lower() or "kokoro"
    using_default_kokoro = (
        provider == "kokoro"
        and str(profile.get("voice") or "") in {"", DEFAULT_VOICE}
    )
    if using_default_kokoro and _brief_prefers_elevenlabs(brief):
        provider = "elevenlabs"
        profile["provider"] = "elevenlabs"
        profile["voice"] = DEFAULT_ELEVENLABS_VOICE

    if provider != "elevenlabs":
        return scenes, profile

    profile.setdefault("voice", DEFAULT_ELEVENLABS_VOICE)
    profile.setdefault("model_id", default_tts_profile()["model_id"])

    voice_pool = _elevenlabs_voice_pool()
    alternate_pool = [voice for voice in voice_pool if voice != DEFAULT_ELEVENLABS_VOICE]
    speaker_voice_map: dict[str, str] = {}
    alternate_index = 0
    planned: list[dict[str, Any]] = []

    for scene in scenes:
        speaker_name = str(scene.get("speaker_name") or "").strip()
        speaker_key = _speaker_key(speaker_name)
        next_scene = dict(scene)

        if not speaker_key:
            planned.append(next_scene)
            continue

        if speaker_key not in speaker_voice_map:
            if _speaker_is_narrator(speaker_name):
                speaker_voice_map[speaker_key] = DEFAULT_ELEVENLABS_VOICE
            else:
                speaker_voice_map[speaker_key] = alternate_pool[alternate_index % len(alternate_pool)]
                alternate_index += 1

        assigned_voice = speaker_voice_map[speaker_key]
        if assigned_voice == str(profile.get("voice") or DEFAULT_ELEVENLABS_VOICE):
            next_scene["tts_override_enabled"] = False
            next_scene["tts_provider"] = None
            next_scene["tts_voice"] = None
        else:
            next_scene["tts_override_enabled"] = True
            next_scene["tts_provider"] = provider
            next_scene["tts_voice"] = assigned_voice
            next_scene["tts_speed"] = next_scene.get("tts_speed") or profile.get("speed") or 1.0
        planned.append(next_scene)

    return planned, profile


def _apply_composition_mode_to_scenes(
    scenes: list[dict[str, Any]],
    *,
    brief: dict[str, Any],
) -> list[dict[str, Any]]:
    composition_mode = str(brief.get("composition_mode") or "classic").strip().lower()
    if composition_mode != "motion_only":
        return scenes

    transformed: list[dict[str, Any]] = []
    for scene in scenes:
        item = dict(scene)
        item["scene_type"] = "motion"
        item["image_path"] = None
        item["video_path"] = None
        item["preview_path"] = None
        item["motion"] = _motion_scene_defaults(item)
        transformed.append(item)
    return transformed


def create_plan_from_brief(
    *,
    project_name: str,
    brief: dict[str, Any],
    provider: str,
    image_model: str = "qwen/qwen-image-2512",
    image_profile: dict[str, Any] | None = None,
    video_profile: dict[str, Any] | None = None,
    tts_profile: dict[str, Any] | None = None,
    render_profile: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Create a new normalized plan from a user brief."""
    normalized_brief = normalize_brief(brief)
    normalized_brief["project_name"] = sanitize_project_name(project_name)
    resolved_image_profile = dict(image_profile or default_image_profile())
    resolved_image_profile["generation_model"] = str(
        resolved_image_profile.get("generation_model") or image_model
    )
    resolved_video_profile = dict(video_profile or default_video_profile())
    resolved_tts_profile = dict(tts_profile or default_tts_profile())
    if _cloud_media_prefers_elevenlabs(
        image_profile=resolved_image_profile,
        video_profile=resolved_video_profile,
        tts_profile=resolved_tts_profile,
    ):
        resolved_tts_profile["provider"] = "elevenlabs"
        resolved_tts_profile["voice"] = DEFAULT_ELEVENLABS_VOICE

    scenes, storyboard_meta = generate_storyboard_with_metadata(normalized_brief, provider=provider)
    scenes = [normalize_scene(scene, i) for i, scene in enumerate(scenes)]
    scenes = _apply_composition_mode_to_scenes(scenes, brief=normalized_brief)
    scenes = plan_scene_compositions(scenes, brief=normalized_brief)
    scenes, treatment_meta = plan_scene_treatments_with_metadata(
        scenes,
        brief=normalized_brief,
        provider=provider,
    )
    scenes, resolved_tts_profile = _pick_scene_voice_plan(
        scenes,
        brief=normalized_brief,
        tts_profile=resolved_tts_profile,
    )

    plan = {
        "meta": {
            "project_name": normalized_brief["project_name"],
            "created_utc": _utc_now(),
            "llm_provider": provider,
            "image_model": resolved_image_profile["generation_model"],
            "image_profile": resolved_image_profile,
            "video_model": str((video_profile or default_video_profile()).get("generation_model") or ""),
            "video_profile": video_profile or default_video_profile(),
            "pipeline_mode": "generic_slides_v1",
            "brief": normalized_brief,
            "render_profile": render_profile or default_render_profile(),
            "tts_profile": resolved_tts_profile,
            # Compatibility fallback for older tooling.
            "input_text": normalized_brief.get("source_material", ""),
        },
        "scenes": scenes,
    }
    if isinstance(storyboard_meta.get("actual"), dict):
        append_actual_cost_entry(plan, storyboard_meta["actual"])
    if isinstance(storyboard_meta.get("preflight"), dict):
        plan.setdefault("meta", {}).setdefault("cost_actual", {})["llm_preflight"] = storyboard_meta["preflight"]
    if isinstance(treatment_meta.get("actual"), dict):
        append_actual_cost_entry(plan, treatment_meta["actual"])
    if isinstance(treatment_meta.get("preflight"), dict):
        plan.setdefault("meta", {}).setdefault("cost_actual", {})["llm_preflight_treatment"] = treatment_meta["preflight"]
    return backfill_plan(plan)


def rebuild_plan_from_meta(
    plan: dict[str, Any],
    *,
    provider: str | None = None,
) -> dict[str, Any]:
    """
    Regenerate storyboard scenes from `meta.brief` (or legacy `meta.input_text`).

    Existing scene assets are intentionally reset because scene count/order/content
    may change after rebuild.
    """
    normalized = backfill_plan(plan)
    meta = dict(normalized.get("meta", {}))

    chosen_provider = (provider or meta.get("llm_provider") or "openai").strip()
    source = meta.get("brief") if isinstance(meta.get("brief"), dict) else None
    if not source:
        source = str(meta.get("input_text") or "")

    next_tts_profile = dict(meta.get("tts_profile") or default_tts_profile())
    if _cloud_media_prefers_elevenlabs(
        image_profile=dict(meta.get("image_profile") or default_image_profile()),
        video_profile=dict(meta.get("video_profile") or default_video_profile()),
        tts_profile=next_tts_profile,
    ):
        next_tts_profile["provider"] = "elevenlabs"
        next_tts_profile["voice"] = DEFAULT_ELEVENLABS_VOICE

    scenes, storyboard_meta = generate_storyboard_with_metadata(source, provider=chosen_provider)
    normalized_scenes = []
    for i, scene in enumerate(scenes):
        item = normalize_scene(scene, i)
        item["image_path"] = None
        item["audio_path"] = None
        item["preview_path"] = None
        normalized_scenes.append(item)
    normalized_scenes = _apply_composition_mode_to_scenes(normalized_scenes, brief=meta.get("brief") or {})
    normalized_scenes = plan_scene_compositions(normalized_scenes, brief=meta.get("brief") or {})
    normalized_scenes, treatment_meta = plan_scene_treatments_with_metadata(
        normalized_scenes,
        brief=meta.get("brief") or {},
        provider=chosen_provider,
    )
    normalized_scenes, next_tts_profile = _pick_scene_voice_plan(
        normalized_scenes,
        brief=meta.get("brief") or {},
        tts_profile=next_tts_profile,
    )

    meta["llm_provider"] = chosen_provider
    meta["regenerated_utc"] = _utc_now()
    meta["tts_profile"] = next_tts_profile
    if isinstance(storyboard_meta.get("actual"), dict):
        actual = meta.get("cost_actual") if isinstance(meta.get("cost_actual"), dict) else {}
        entries = actual.get("entries") if isinstance(actual.get("entries"), list) else []
        actual["entries"] = [*entries, storyboard_meta["actual"]]
        if isinstance(storyboard_meta.get("preflight"), dict):
            actual["llm_preflight"] = storyboard_meta["preflight"]
        meta["cost_actual"] = actual
    if isinstance(treatment_meta.get("actual"), dict):
        actual = meta.get("cost_actual") if isinstance(meta.get("cost_actual"), dict) else {}
        entries = actual.get("entries") if isinstance(actual.get("entries"), list) else []
        actual["entries"] = [*entries, treatment_meta["actual"]]
        if isinstance(treatment_meta.get("preflight"), dict):
            actual["llm_preflight_treatment"] = treatment_meta["preflight"]
        meta["cost_actual"] = actual
    normalized["meta"] = meta
    normalized["scenes"] = normalized_scenes
    return backfill_plan(normalized)
