"""Pydantic request/response models for scene endpoints."""

from __future__ import annotations

from pydantic import BaseModel


class ImageGenerateRequest(BaseModel):
    provider: str | None = None
    model: str | None = None


class VideoGenerateRequest(BaseModel):
    provider: str | None = None
    model: str | None = None


class ImageEditRequest(BaseModel):
    feedback: str
    model: str | None = None


class AudioGenerateRequest(BaseModel):
    tts_provider: str | None = None
    voice: str | None = None
    speed: float | None = None


class PromptRefineRequest(BaseModel):
    feedback: str
    provider: str | None = None


class NarrationRefineRequest(BaseModel):
    feedback: str
    provider: str | None = None
