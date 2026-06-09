"""Short-form vertical video payload builder for betTube Studio jobs."""

from __future__ import annotations

import os
from typing import Any

from .project_schema import sanitize_project_name
from .runtime import available_tts_providers

SHORT_FORM_TIERS = {"mass-native-technical", "dev-native-credible"}
SHORT_FORM_APPROACHES = {"public-reframe", "source-cutdown", "mixed-media-proof"}
CAPTION_STRATEGIES = {"word-level-highlight", "meaning-card-captions", "keyword-labels"}
PLATFORM_TARGETS = {"tiktok", "instagram-reels", "youtube-shorts"}
PLATFORM_LABELS = {
    "tiktok": "TikTok",
    "instagram-reels": "Instagram Reels",
    "youtube-shorts": "YouTube Shorts",
}
TIER_LABELS = {
    "dev-native-credible": "Technical proof",
    "mass-native-technical": "Broad technical",
}
APPROACH_LABELS = {
    "public-reframe": "Public reframe",
    "source-cutdown": "Source cutdown",
    "mixed-media-proof": "Mixed-media proof",
}
CAPTION_STRATEGY_LABELS = {
    "word-level-highlight": "Word-level highlight",
    "meaning-card-captions": "Meaning-card captions",
    "keyword-labels": "Keyword labels",
}
RUN_UNTIL_VALUES = {"storyboard", "assets", "render"}
DEFAULT_PLATFORM_TARGETS = ["tiktok", "instagram-reels", "youtube-shorts"]

DEFAULT_RUNTIME_SECONDS = 42.0
MIN_RUNTIME_SECONDS = 30.0
MAX_RUNTIME_SECONDS = 50.0
VERTICAL_WIDTH = 928
VERTICAL_HEIGHT = 1664
VERTICAL_FPS = 30

SHORT_FORM_OPTIONS = {
    "tiers": [
        {
            "value": "dev-native-credible",
            "label": "Technical proof",
            "description": "Proof-first, technically credible, inspectable visuals, and less slang.",
        },
        {
            "value": "mass-native-technical",
            "label": "Broad technical",
            "description": "Broader cold-feed energy with simple language and restrained social-native punch.",
        },
    ],
    "approaches": [
        {
            "value": "public-reframe",
            "label": "Public reframe",
            "description": "Treat the source as research input and make one cold-audience idea with fresh vertical visuals.",
        },
        {
            "value": "mixed-media-proof",
            "label": "Mixed-media proof",
            "description": "Use source footage as proof moments, surrounded by generated vertical hook/payoff visuals.",
        },
        {
            "value": "source-cutdown",
            "label": "Source cutdown",
            "description": "Use the source footage as the primary proof and isolate one standalone moment.",
        },
    ],
    "caption_strategies": [
        {
            "value": "meaning-card-captions",
            "label": "Meaning-card captions",
            "description": "Phrase-level cards that carry the idea without requiring exact word timings.",
        },
        {
            "value": "word-level-highlight",
            "label": "Word-level highlight",
            "description": "Current-word highlighting, only when final-audio word timings are available.",
        },
        {
            "value": "keyword-labels",
            "label": "Keyword labels",
            "description": "Sparse labels that emphasize proof, objects, and turns in the argument.",
        },
    ],
    "platform_targets": [
        {
            "value": "tiktok",
            "label": "TikTok",
            "description": "Biases the hook, caption density, and mobile-safe framing for a fast cold-feed watch.",
        },
        {
            "value": "instagram-reels",
            "label": "Instagram Reels",
            "description": "Biases polish, readability, and payoff clarity for Reels while keeping the same 9:16 render.",
        },
        {
            "value": "youtube-shorts",
            "label": "YouTube Shorts",
            "description": "Biases context, retention, and payoff clarity for Shorts while keeping the same 9:16 render.",
        },
    ],
    "run_until": [
        {"value": "storyboard", "label": "Storyboard", "description": "Plan only; safest first pass before spending media calls."},
        {"value": "assets", "label": "Assets", "description": "Plan plus image/video/audio generation."},
        {"value": "render", "label": "Render", "description": "Run through final MP4 assembly."},
    ],
}


def _clean(value: Any) -> str:
    return str(value or "").strip()


def _clean_lines(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return [line.strip() for line in str(value or "").splitlines() if line.strip()]


def _short_form_tts_profile(data: dict[str, Any]) -> dict[str, Any]:
    profile = data.get("tts_profile") if isinstance(data.get("tts_profile"), dict) else None
    if profile:
        return {**profile, "speed": float(profile.get("speed") or 1.0)}

    if "openai" in available_tts_providers():
        return {
            "provider": "openai",
            "voice": os.getenv("BETTUBE_STUDIO_OPENAI_TTS_VOICE") or "marin",
            "model_id": os.getenv("BETTUBE_STUDIO_OPENAI_TTS_MODEL") or "gpt-4o-mini-tts",
            "speed": 1.0,
        }

    return {
        "speed": 1.0,
    }


def _slug_choice(value: Any, allowed: set[str], fallback: str) -> str:
    normalized = _clean(value).lower().replace("_", "-").replace(" ", "-")
    return normalized if normalized in allowed else fallback


def _runtime_seconds(value: Any) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        parsed = DEFAULT_RUNTIME_SECONDS
    return min(max(parsed, MIN_RUNTIME_SECONDS), MAX_RUNTIME_SECONDS)


def _platforms(value: Any) -> list[str]:
    values = _clean_lines(value)
    normalized = [
        item.lower().replace("_", "-").replace(" ", "-")
        for item in values
        if item.lower().replace("_", "-").replace(" ", "-") in PLATFORM_TARGETS
    ]
    return normalized or list(DEFAULT_PLATFORM_TARGETS)


def short_form_options() -> dict[str, Any]:
    """Return option metadata used by both API clients and the React surface."""
    return {
        **SHORT_FORM_OPTIONS,
        "defaults": {
            "short_form_tier": "dev-native-credible",
            "approach": "public-reframe",
            "caption_strategy": "meaning-card-captions",
            "platform_targets": list(DEFAULT_PLATFORM_TARGETS),
            "runtime_seconds": DEFAULT_RUNTIME_SECONDS,
            "run_until": "storyboard",
            "render_profile": {
                "aspect_ratio": "9:16",
                "width": VERTICAL_WIDTH,
                "height": VERTICAL_HEIGHT,
                "fps": VERTICAL_FPS,
            },
        },
    }


def _source_anchor_card(data: dict[str, Any]) -> str:
    explicit = _clean(data.get("source_anchor_card"))
    if explicit:
        return explicit

    fields = [
        ("Subject", data.get("subject")),
        ("Domain", data.get("domain")),
        ("Setting", data.get("setting")),
        ("Actors/users", data.get("actors")),
        ("Primary objects", data.get("primary_objects")),
        ("Workflow/action", data.get("workflow_action")),
        ("Visual anchors", data.get("visual_anchors")),
        ("Supported claims", data.get("supported_claims")),
        ("Evidence boundary", data.get("evidence_boundary")),
        ("Allowed metaphors", data.get("allowed_metaphors")),
        ("Forbidden drift", data.get("forbidden_drift")),
    ]
    return "\n".join(f"{label}: {_clean(value)}" for label, value in fields if _clean(value))


def _source_context_lock(anchor_card: str, data: dict[str, Any]) -> str:
    explicit = _clean(data.get("source_context_lock"))
    if explicit:
        return explicit
    if anchor_card:
        return anchor_card
    return (
        "Preserve the source domain, setting, actors, primary objects, workflow, and claims. "
        "Reject visual drift into unrelated products, industries, user roles, platforms, or outcomes."
    )


def _source_material_block(data: dict[str, Any], *, anchor_card: str) -> str:
    lines: list[str] = []
    source_material = _clean(data.get("source_material"))
    transcript = _clean(data.get("source_transcript"))
    footage_notes = _clean(data.get("footage_notes"))
    if source_material:
        lines.extend(["Source material:", source_material])
    if transcript:
        lines.extend(["", "Source transcript excerpt:", transcript])
    if footage_notes:
        lines.extend(["", "Footage notes:", footage_notes])
    if anchor_card:
        lines.extend(["", "Source anchor card:", anchor_card])
    return "\n".join(lines).strip()


def _brief_text(
    data: dict[str, Any],
    *,
    runtime_seconds: float,
    tier: str,
    approach: str,
    caption_strategy: str,
    platform_targets: list[str],
) -> str:
    hook = _clean(data.get("hook_promise"))
    payoff = _clean(data.get("payoff"))
    audience = _clean(data.get("audience")) or "cold scrolling viewers"
    cta = _clean(data.get("ending_cta")) or "follow for the full breakdown"
    source_video_role = {
        "public-reframe": "optional proof/reference only, not the visual spine",
        "source-cutdown": "primary proof material; cut to one standalone moment",
        "mixed-media-proof": "proof anchor mixed with fresh generated vertical visuals",
    }[approach]
    platform_labels = ", ".join(PLATFORM_LABELS.get(platform, platform) for platform in platform_targets)
    return "\n".join(
        [
            f"Create a {int(round(runtime_seconds))}-second vertical short-form video.",
            "It must be hook-first, fast-paced, caption-led, and built around one clear payoff.",
            "The first 1-3 seconds must create a concrete reason to keep watching.",
            "Use 3-5 beats with visible pattern changes every 3-5 seconds.",
            f"Short-form tier: {TIER_LABELS.get(tier, tier)}.",
            f"Short-form approach: {APPROACH_LABELS.get(approach, approach.replace('-', ' '))}.",
            f"Platform targets: {platform_labels}.",
            f"Source footage role: {source_video_role}.",
            f"Hook promise: {hook or 'a concrete result, contradiction, mistake, or proof moment'}",
            f"Audience: {audience}",
            f"Payoff: {payoff or 'the viewer understands the one useful idea before the CTA'}",
            f"Caption strategy: {CAPTION_STRATEGY_LABELS.get(caption_strategy, caption_strategy.replace('-', ' '))}.",
            f"CTA: {cta}",
        ]
    )


def _approach_source_role(approach: str) -> str:
    return {
        "public-reframe": "Source material informs the idea; generated vertical visuals carry the short unless footage is proof.",
        "source-cutdown": "Source footage is the spine; the director should isolate one standalone proof moment.",
        "mixed-media-proof": "Source footage supplies proof moments; generated vertical visuals supply hook, context, and payoff.",
    }[approach]


def _payload_preview(
    *,
    project_name: str,
    runtime_seconds: float,
    tier: str,
    approach: str,
    caption_strategy: str,
    platform_targets: list[str],
    run_until: str,
    anchor_card: str,
    render_profile: dict[str, Any],
) -> dict[str, Any]:
    return {
        "project_name": project_name,
        "format": "vertical_short",
        "frame": f"{render_profile['aspect_ratio']} {render_profile['width']}x{render_profile['height']} @ {render_profile['fps']}fps",
        "runtime_seconds": runtime_seconds,
        "tier": TIER_LABELS.get(tier, tier),
        "approach": APPROACH_LABELS.get(approach, approach),
        "caption_strategy": CAPTION_STRATEGY_LABELS.get(caption_strategy, caption_strategy),
        "platform_targets": platform_targets,
        "run_until": run_until,
        "source_role": _approach_source_role(approach),
        "has_source_anchor": bool(anchor_card),
        "pipeline": [
            "brief",
            "storyboard",
            "asset plan",
            "assets" if run_until in {"assets", "render"} else "storyboard only",
            "render" if run_until == "render" else "render later",
        ],
        "beat_shape": [
            {"range": "0-3s", "job": "hook promise"},
            {"range": "3-30s", "job": "3-5 proof or meaning beats with visible resets"},
            {"range": f"before {int(round(runtime_seconds))}s", "job": "payoff before CTA"},
        ],
        "guardrails": [
            "one main idea",
            "source-loyal visual direction",
            "caption-safe mobile framing",
            "no current-word captions without final-audio word timings",
        ],
    }


def build_short_form_payload(data: dict[str, Any]) -> dict[str, Any]:
    """Return the canonical betTube Studio request bundle for a vertical short."""
    project_name = sanitize_project_name(data.get("project_name"), fallback="vertical_short")
    runtime_seconds = _runtime_seconds(data.get("runtime_seconds"))
    tier = _slug_choice(data.get("short_form_tier"), SHORT_FORM_TIERS, "dev-native-credible")
    approach = _slug_choice(data.get("approach"), SHORT_FORM_APPROACHES, "public-reframe")
    caption_strategy = _slug_choice(
        data.get("caption_strategy"),
        CAPTION_STRATEGIES,
        "meaning-card-captions",
    )
    platform_targets = _platforms(data.get("platform_targets"))
    anchor_card = _source_anchor_card(data)
    source_context_lock = _source_context_lock(anchor_card, data)
    source_material = _source_material_block(data, anchor_card=anchor_card)
    target_minutes = round(runtime_seconds / 60.0, 3)
    hook = _clean(data.get("hook_promise"))
    payoff = _clean(data.get("payoff"))
    cta = _clean(data.get("ending_cta")) or "follow for the full breakdown"
    audience = _clean(data.get("audience")) or "cold scrolling viewers"
    caption_timing_source = (
        _clean(data.get("caption_timing_source"))
        or "Align captions from final narration audio after edits; do not use approximate timings for current-word highlights."
    )
    caption_renderer = (
        _clean(data.get("caption_renderer"))
        or "Use Remotion captions from word timestamps when available; otherwise burn in phrase/meaning cards."
    )

    short_form_intent = _brief_text(
        data,
        runtime_seconds=runtime_seconds,
        tier=tier,
        approach=approach,
        caption_strategy=caption_strategy,
        platform_targets=platform_targets,
    )
    must_include_parts = [
        "A first-3-second hook.",
        "3-5 short-form beats.",
        "Caption-safe mobile framing.",
        "A payoff before the CTA.",
        _clean(data.get("must_include")),
    ]
    must_avoid_parts = [
        "Generic intro.",
        "Broad full-topic summary.",
        "Deceptive clickbait.",
        "More than one main idea.",
        "Merely compressing a long source video unless source-cutdown is explicitly chosen.",
        "Generated visuals drifting away from the source context.",
        "Current-word captions without accurate word timing.",
        _clean(data.get("must_avoid")),
    ]
    visual_source_strategy = "mixed_media" if approach in {"source-cutdown", "mixed-media-proof"} else "images_only"
    video_scene_style = "mixed" if visual_source_strategy == "mixed_media" else "auto"
    run_until = _slug_choice(data.get("run_until"), RUN_UNTIL_VALUES, "storyboard")

    brief = {
        "project_name": project_name,
        "source_mode": "source_text" if source_material else "ideas_notes",
        "video_goal": short_form_intent,
        "audience": audience,
        "source_material": source_material or short_form_intent,
        "target_length_minutes": target_minutes,
        "tone": _clean(data.get("tone")) or "fast, clear, confident, social-native, and not forced",
        "visual_style": _clean(data.get("visual_style"))
        or "9:16 vertical short-form, tight mobile-safe framing, kinetic captions, fast visual resets, source-loyal visuals",
        "must_include": "\n".join(part for part in must_include_parts if part),
        "must_avoid": "\n".join(part for part in must_avoid_parts if part),
        "ending_cta": cta,
        "paid_media_budget_usd": _clean(data.get("paid_media_budget_usd")),
        "composition_mode": "classic",
        "visual_source_strategy": visual_source_strategy,
        "video_scene_style": video_scene_style,
        "text_render_mode": "visual_authored",
        "available_footage": _clean(data.get("available_footage")),
        "footage_manifest": data.get("footage_manifest") if isinstance(data.get("footage_manifest"), list) else [],
        "style_reference_summary": _clean(data.get("style_reference_summary")),
        "style_reference_paths": data.get("style_reference_paths") if isinstance(data.get("style_reference_paths"), list) else [],
        "raw_brief": "\n\n".join(part for part in [short_form_intent, source_material] if part),
        "short_form_format": "vertical_short",
        "short_form_tier": tier,
        "short_form_approach": approach,
        "short_form_duration_seconds": runtime_seconds,
        "platform_targets": platform_targets,
        "hook_promise": hook,
        "payoff": payoff,
        "source_anchor_card": anchor_card,
        "source_context_lock": source_context_lock,
        "caption_strategy": caption_strategy,
        "caption_timing_source": caption_timing_source,
        "caption_renderer": caption_renderer,
        "voice_direction": _clean(data.get("voice_direction"))
        or "naturally fast presenter, clear consonants, no chipmunk pitch, no exaggerated influencer cadence",
        "motion_intensity": _clean(data.get("motion_intensity"))
        or ("high but purposeful" if tier == "mass-native-technical" else "medium-high and inspectable"),
    }

    render_profile = {
        "version": "v1",
        "aspect_ratio": "9:16",
        "width": VERTICAL_WIDTH,
        "height": VERTICAL_HEIGHT,
        "fps": VERTICAL_FPS,
        "scene_types": ["image", "video", "motion"],
        "render_strategy": "force_ffmpeg",
        "render_backend": "ffmpeg",
        "render_backend_reason": "Vertical short-form surface explicitly requested 9:16 ffmpeg assembly.",
        "text_render_mode": "visual_authored",
        "auto_compress_oversized_video": True,
        "compression_min_size_mb": 75.0,
        "compression_max_average_bitrate_mbps": 3.2,
        "compression_target_video_kbps": 2500,
        "compression_target_audio_kbps": 128,
    }
    video_profile = {
        "provider": "manual",
        "generation_model": "",
        "model_selection_mode": "automatic",
        "quality_mode": "standard",
        "generate_audio": True,
    }
    tts_profile = _short_form_tts_profile(data)
    image_profile = data.get("image_profile") if isinstance(data.get("image_profile"), dict) else None
    preview = _payload_preview(
        project_name=project_name,
        runtime_seconds=runtime_seconds,
        tier=tier,
        approach=approach,
        caption_strategy=caption_strategy,
        platform_targets=platform_targets,
        run_until=run_until,
        anchor_card=anchor_card,
        render_profile=render_profile,
    )

    return {
        "project_name": project_name,
        "brief": brief,
        "render_profile": render_profile,
        "video_profile": video_profile,
        "tts_profile": tts_profile,
        "image_profile": image_profile,
        "runtime_seconds": runtime_seconds,
        "run_until": run_until,
        "preview": preview,
    }
