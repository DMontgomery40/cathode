"""Provider configuration endpoint."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from core.image_gen import available_image_edit_models
from core.runtime import (
    available_image_generation_providers,
    available_tts_providers,
    available_video_generation_providers,
    check_api_keys,
    choose_llm_provider,
)
from core.voice_gen import ELEVENLABS_VOICES, KOKORO_VOICES

router = APIRouter()


def _tts_voice_options() -> dict[str, list[dict[str, str]]]:
    return {
        "kokoro": [
            {"value": voice_id, "label": voice_id, "description": description}
            for voice_id, description in KOKORO_VOICES.items()
        ],
        "elevenlabs": [
            {"value": name, "label": name, "description": description}
            for name, (_voice_id, description) in ELEVENLABS_VOICES.items()
        ],
        "openai": [
            {"value": voice, "label": voice, "description": "OpenAI TTS voice"}
            for voice in ("alloy", "ash", "ballad", "coral", "echo", "fable", "nova", "onyx", "sage", "shimmer")
        ],
        "chatterbox": [],
    }


@router.get("/settings/providers")
async def get_providers() -> dict[str, Any]:
    keys = check_api_keys()
    try:
        llm_provider = choose_llm_provider()
    except ValueError:
        llm_provider = "none"

    return {
        "api_keys": keys,
        "llm_provider": llm_provider,
        "image_providers": available_image_generation_providers(keys),
        "video_providers": available_video_generation_providers(),
        "tts_providers": available_tts_providers(keys),
        "tts_voice_options": _tts_voice_options(),
        "image_edit_models": available_image_edit_models(
            include_replicate=keys.get("replicate", False),
            include_dashscope=keys.get("dashscope", False),
        ),
    }
