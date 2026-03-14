"""Bootstrap endpoint -- returns everything the frontend needs to initialize."""

from __future__ import annotations

from fastapi import APIRouter

from core.costs import frontend_cost_catalog
from core.image_gen import available_image_edit_models
from core.project_schema import (
    default_brief,
    default_image_profile,
    default_render_profile,
    default_tts_profile,
    default_video_profile,
)
from core.project_store import list_projects
from core.runtime import (
    available_image_generation_providers,
    available_render_backends,
    available_tts_providers,
    available_video_generation_providers,
    check_api_keys,
    choose_llm_provider,
    remotion_capabilities,
    remotion_available,
)
from core.voice_gen import ELEVENLABS_VOICES, KOKORO_VOICES
from server.schemas.bootstrap import (
    ApiKeysStatus,
    BootstrapResponse,
    DefaultProfiles,
    ProvidersInfo,
)

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


@router.get("/bootstrap", response_model=BootstrapResponse)
async def bootstrap() -> BootstrapResponse:
    keys = check_api_keys()
    try:
        llm_provider = choose_llm_provider()
    except ValueError:
        llm_provider = None

    return BootstrapResponse(
        providers=ProvidersInfo(
            api_keys=ApiKeysStatus(**keys),
            llm_provider=llm_provider,
            image_providers=available_image_generation_providers(keys),
            video_providers=available_video_generation_providers(keys),
            render_backends=available_render_backends(),
            remotion_available=remotion_available(),
            remotion_capabilities=remotion_capabilities(),
            tts_providers=available_tts_providers(keys),
            tts_voice_options=_tts_voice_options(),
            image_edit_models=available_image_edit_models(
                include_replicate=keys.get("replicate", False),
                include_dashscope=keys.get("dashscope", False),
            ),
            cost_catalog=frontend_cost_catalog(),
        ),
        defaults=DefaultProfiles(
            brief=default_brief(),
            render_profile=default_render_profile(),
            image_profile=default_image_profile(),
            video_profile=default_video_profile(),
            tts_profile=default_tts_profile(),
        ),
        projects=list_projects(),
    )
