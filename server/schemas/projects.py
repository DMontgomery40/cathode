"""Pydantic request/response models for project endpoints."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class ProjectSummary(BaseModel):
    name: str
    scene_count: int = 0
    has_video: bool = False
    video_path: str | None = None
    thumbnail_path: str | None = None
    created_utc: str | None = None
    updated_utc: str | None = None
    image_profile: dict[str, Any] | None = None
    tts_profile: dict[str, Any] | None = None


class CreateProjectRequest(BaseModel):
    project_name: str
    brief: dict[str, Any]
    provider: str | None = None
    image_profile: dict[str, Any] | None = None
    video_profile: dict[str, Any] | None = None
    agent_demo_profile: dict[str, Any] | None = None
    tts_profile: dict[str, Any] | None = None
    render_profile: dict[str, Any] | None = None
    overwrite: bool = False
