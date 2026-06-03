"""Pydantic models for short-form vertical video endpoints."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class ShortFormRequest(BaseModel):
    project_name: str
    source_material: str = ""
    source_transcript: str = ""
    footage_notes: str = ""
    audience: str = ""
    hook_promise: str = ""
    payoff: str = ""
    ending_cta: str = ""
    short_form_tier: str = "dev-native-credible"
    approach: str = "public-reframe"
    caption_strategy: str = "meaning-card-captions"
    platform_targets: list[str] | None = None
    runtime_seconds: float | None = None
    tone: str = ""
    visual_style: str = ""
    must_include: str = ""
    must_avoid: str = ""
    source_anchor_card: str = ""
    source_context_lock: str = ""
    subject: str = ""
    domain: str = ""
    setting: str = ""
    actors: str = ""
    primary_objects: str = ""
    workflow_action: str = ""
    visual_anchors: str = ""
    supported_claims: str = ""
    evidence_boundary: str = ""
    allowed_metaphors: str = ""
    forbidden_drift: str = ""
    caption_timing_source: str = ""
    caption_renderer: str = ""
    voice_direction: str = ""
    motion_intensity: str = ""
    available_footage: str = ""
    footage_manifest: list[dict[str, Any]] | None = None
    style_reference_summary: str = ""
    style_reference_paths: list[str] | None = None
    paid_media_budget_usd: str = ""
    image_profile: dict[str, Any] | None = None
    provider: str | None = None
    overwrite: bool = False
    run_until: str | None = "storyboard"
