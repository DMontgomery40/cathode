"""Pydantic request/response models for project endpoints."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ProjectJobCounts(BaseModel):
    total: int = 0
    queued: int = 0
    running: int = 0
    succeeded: int = 0
    partial_success: int = 0
    failed: int = 0
    cancelled: int = 0
    error: int = 0
    active: int = 0


class ProjectJobSummary(BaseModel):
    counts: ProjectJobCounts = Field(default_factory=ProjectJobCounts)
    latest_status: str | None = None
    latest_job_id: str | None = None
    latest_requested_stage: str | None = None
    latest_updated_utc: str | None = None


class ProjectSummary(BaseModel):
    name: str
    scene_count: int = 0
    has_video: bool = False
    jobs: ProjectJobSummary = Field(default_factory=ProjectJobSummary)
    video_path: str | None = None
    thumbnail_path: str | None = None
    thumbnail_version: int | None = None
    created_utc: str | None = None
    updated_utc: str | None = None
    image_profile: dict[str, Any] | None = None
    tts_profile: dict[str, Any] | None = None
    pipeline_mode: str | None = None
    short_form_format: str | None = None
    render_aspect_ratio: str | None = None


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
