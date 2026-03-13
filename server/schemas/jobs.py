"""Pydantic request/response models for job endpoints."""

from __future__ import annotations

from pydantic import BaseModel


class RenderRequest(BaseModel):
    output_filename: str | None = None
    fps: int | None = None


class AgentDemoRequest(BaseModel):
    scene_uids: list[str] | None = None
    preferred_agent: str | None = None
    workspace_path: str | None = None
    app_url: str | None = None
    launch_command: str | None = None
    expected_url: str | None = None
    run_until: str | None = None


class MakeVideoRequest(BaseModel):
    project_name: str
    brief: dict
    provider: str | None = None
    image_profile: dict | None = None
    video_profile: dict | None = None
    agent_demo_profile: dict | None = None
    tts_profile: dict | None = None
    render_profile: dict | None = None
    overwrite: bool = False
    run_until: str | None = None
