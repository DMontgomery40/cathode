"""Pydantic request/response models for style reference endpoints."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class StyleRefsResponse(BaseModel):
    style_reference_paths: list[str] = []
    style_reference_summary: str = ""
