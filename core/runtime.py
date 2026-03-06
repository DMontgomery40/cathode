"""Runtime configuration and provider discovery helpers."""

from __future__ import annotations

import os
from pathlib import Path

from .project_schema import default_image_profile, default_tts_profile

REPO_ROOT = Path(__file__).resolve().parent.parent
PROJECTS_DIR = REPO_ROOT / "projects"
PROJECTS_DIR.mkdir(exist_ok=True)


def check_api_keys() -> dict[str, bool]:
    """Return which external providers are configured in the current environment."""
    return {
        "openai": bool(os.getenv("OPENAI_API_KEY")),
        "anthropic": bool(os.getenv("ANTHROPIC_API_KEY")),
        "replicate": bool(os.getenv("REPLICATE_API_TOKEN")),
        "dashscope": bool(os.getenv("DASHSCOPE_API_KEY") or os.getenv("ALIBABA_API_KEY")),
        "elevenlabs": bool(os.getenv("ELEVENLABS_API_KEY")),
    }


def available_tts_providers(keys: dict[str, bool] | None = None) -> dict[str, str]:
    """Return user-facing TTS provider labels in preference order."""
    keys = keys or check_api_keys()
    providers = {"kokoro": "Kokoro (Local)"}
    if keys.get("replicate"):
        providers["chatterbox"] = "Chatterbox (Cloud / Replicate)"
    if keys.get("elevenlabs"):
        providers["elevenlabs"] = "ElevenLabs (Cloud)"
    if keys.get("openai"):
        providers["openai"] = "OpenAI TTS (Cloud)"
    return providers


def available_image_generation_providers(keys: dict[str, bool] | None = None) -> list[str]:
    """Return supported image-generation providers in UI preference order."""
    keys = keys or check_api_keys()
    providers = ["manual"]
    if keys.get("replicate"):
        providers.insert(0, "replicate")
    return providers


def choose_llm_provider(preferred: str | None = None) -> str:
    """Choose the best available storyboard LLM provider for the current environment."""
    keys = check_api_keys()
    candidate = str(preferred or "").strip().lower()
    if candidate and keys.get(candidate):
        return candidate

    for provider in ("anthropic", "openai"):
        if keys.get(provider):
            return provider
    raise ValueError("No LLM API keys configured. Set ANTHROPIC_API_KEY or OPENAI_API_KEY.")


def resolve_image_profile(profile: dict | None = None) -> dict:
    """Resolve a persisted image profile against current provider availability."""
    resolved = dict(default_image_profile())
    if isinstance(profile, dict):
        resolved.update(profile)

    keys = check_api_keys()
    provider = str(resolved.get("provider") or "replicate").strip().lower()
    if provider == "replicate" and not keys.get("replicate"):
        provider = "manual"
    if provider not in {"replicate", "manual"}:
        provider = "manual"
    resolved["provider"] = provider
    return resolved


def resolve_tts_profile(profile: dict | None = None) -> dict:
    """Resolve a persisted TTS profile against current provider availability."""
    resolved = dict(default_tts_profile())
    if isinstance(profile, dict):
        resolved.update(profile)

    available = available_tts_providers()
    provider = str(resolved.get("provider") or "kokoro").strip().lower()
    if provider not in available:
        provider = "kokoro"
    resolved["provider"] = provider
    return resolved

