"""Pydantic response models for the bootstrap endpoint."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class ApiKeysStatus(BaseModel):
    openai: bool = False
    anthropic: bool = False
    replicate: bool = False
    dashscope: bool = False
    elevenlabs: bool = False


class ProvidersInfo(BaseModel):
    api_keys: ApiKeysStatus
    llm_provider: str | None
    image_providers: list[str]
    video_providers: list[str]
    render_backends: list[str]
    remotion_available: bool = False
    remotion_capabilities: dict[str, bool] = {}
    tts_providers: dict[str, str]
    tts_voice_options: dict[str, list[dict[str, str]]]
    image_edit_models: list[str]
    cost_catalog: dict[str, Any] = {}


class DefaultProfiles(BaseModel):
    brief: dict[str, Any]
    render_profile: dict[str, Any]
    image_profile: dict[str, Any]
    video_profile: dict[str, Any]
    tts_profile: dict[str, Any]


class BootstrapResponse(BaseModel):
    providers: ProvidersInfo
    defaults: DefaultProfiles
    projects: list[str]
