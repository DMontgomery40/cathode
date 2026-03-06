"""Workflow helpers shared by the app and batch scripts."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from .director import generate_storyboard
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


def _utc_now() -> str:
    return datetime.utcnow().isoformat()


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

    scenes = generate_storyboard(normalized_brief, provider=provider)
    scenes = [normalize_scene(scene, i) for i, scene in enumerate(scenes)]

    resolved_image_profile = dict(image_profile or default_image_profile())
    resolved_image_profile["generation_model"] = str(
        resolved_image_profile.get("generation_model") or image_model
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
            "tts_profile": tts_profile or default_tts_profile(),
            # Compatibility fallback for older tooling.
            "input_text": normalized_brief.get("source_material", ""),
        },
        "scenes": scenes,
    }
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

    scenes = generate_storyboard(source, provider=chosen_provider)
    normalized_scenes = []
    for i, scene in enumerate(scenes):
        item = normalize_scene(scene, i)
        item["image_path"] = None
        item["audio_path"] = None
        item["preview_path"] = None
        normalized_scenes.append(item)

    meta["llm_provider"] = chosen_provider
    meta["regenerated_utc"] = _utc_now()
    normalized["meta"] = meta
    normalized["scenes"] = normalized_scenes
    return backfill_plan(normalized)
