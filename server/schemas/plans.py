"""Pydantic request/response models for plan endpoints."""

from __future__ import annotations

from pydantic import BaseModel


class RebuildStoryboardRequest(BaseModel):
    provider: str | None = None
    brief: dict | None = None
    agent_demo_profile: dict | None = None
