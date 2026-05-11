"""
Cathode video generator.

Pipeline:
Brief input -> director storyboard -> per-scene image + audio assets -> video render.
"""

from __future__ import annotations

import json
import os
import queue
import re
import shutil
import threading
import time
import uuid
from pathlib import Path

import streamlit as st

from core.branding import PRODUCT_NAME
from core.director import analyze_style_references, generate_storyboard, refine_narration, refine_prompt
from core.image_gen import (
    available_image_edit_models,
    canonicalize_exact_text_edit_prompt,
    default_image_edit_model,
    edit_image,
    generate_scene_image,
)
from core.pipeline_service import (
    _canonical_scene_image_path,
    create_project_from_brief_service,
    generate_project_assets_service,
    process_existing_project_service,
    replace_scene_image_preserving_identity,
    render_project_service,
    tts_kwargs_from_profile,
)
from core.project_store import (
    get_project_path as _get_project_path,
    list_projects as _list_projects,
    load_plan as _load_plan,
    save_plan as _save_plan,
)
from core.project_schema import (
    backfill_plan,
    default_image_profile,
    default_video_profile,
    normalize_brief,
    sanitize_project_name,
)
from core.runtime import (
    PROJECTS_DIR,
    available_image_generation_providers as _available_image_generation_providers_impl,
    available_video_generation_providers as _available_video_generation_providers_impl,
    available_tts_providers as _available_tts_providers_impl,
    check_api_keys as _check_api_keys_impl,
    default_local_image_generation_model as _default_local_image_generation_model_impl,
    default_replicate_video_generation_model as _default_replicate_video_generation_model_impl,
    load_repo_env,
    resolve_image_profile as _resolve_image_profile_impl,
    resolve_video_profile as _resolve_video_profile_impl,
)
from core.video_assembly import (
    assemble_video,
    get_media_duration,
    get_video_duration,
    get_video_scene_timing,
    media_has_audio_stream,
    preview_scene,
    scene_uses_clip_audio,
)
from core.video_gen import (
    DEFAULT_REPLICATE_SPEAKING_VIDEO_MODEL,
    generate_scene_video,
    resolve_replicate_video_generation_route,
)
from core.voice_gen import (
    DEFAULT_ELEVENLABS_MODEL,
    DEFAULT_ELEVENLABS_SIMILARITY_BOOST,
    DEFAULT_ELEVENLABS_SPEED,
    DEFAULT_ELEVENLABS_STABILITY,
    DEFAULT_ELEVENLABS_STYLE,
    DEFAULT_ELEVENLABS_TEXT_NORMALIZATION,
    DEFAULT_ELEVENLABS_USE_SPEAKER_BOOST,
    DEFAULT_ELEVENLABS_VOICE,
    DEFAULT_EXAGGERATION,
    DEFAULT_OPENAI_REALTIME_MODEL,
    DEFAULT_OPENAI_TTS_MODEL,
    DEFAULT_OPENAI_TTS_VOICE,
    DEFAULT_SPEED,
    DEFAULT_VOICE,
    ELEVENLABS_VOICES,
    KOKORO_VOICES,
    OPENAI_REALTIME_VOICES,
    OPENAI_TTS_VOICES,
    generate_scene_audio,
)

# Load repo-local environment variables (override shell env vars with .env file).
load_repo_env(override=True)

SOURCE_MODE_LABELS: dict[str, str] = {
    "ideas_notes": "Ideas / Notes (rough notes; AI writes the draft)",
    "source_text": "Source Text (keep facts; AI rewrites for clarity)",
    "final_script": "Final Script (already written; AI mostly splits it into scenes)",
}

SOURCE_MODE_HELP = (
    "This does not connect to a file or folder. It tells the app how much rewriting is allowed "
    "when turning the text you paste below into storyboard scenes."
)

SOURCE_MODE_UI_GUIDANCE: dict[str, dict[str, str]] = {
    "ideas_notes": {
        "when": "your input is rough bullets, notes, fragments, or a loose outline",
        "rewrite": "The app can create structure and wording, while keeping your intent and constraints.",
        "paste": "bullet points, brainstorm notes, outline fragments, meeting notes, or research scraps",
        "placeholder": (
            "Paste rough notes, bullet points, outline fragments, brainstorm text, or research scraps..."
        ),
    },
    "source_text": {
        "when": "you have source text whose facts should stay intact, but the narration can be cleaned up",
        "rewrite": "The app should preserve the factual content and key numbers while restructuring for flow.",
        "paste": "an article, transcript, memo, report excerpt, documentation, or other fact-based source text",
        "placeholder": (
            "Paste source text whose facts should be preserved: transcript, article, memo, report, docs..."
        ),
    },
    "final_script": {
        "when": "you already have a near-final script and mainly need scene splits plus matching visuals",
        "rewrite": "The app should make minimal wording changes and mostly segment your script into scenes.",
        "paste": "the script or narration you already want to use, in roughly the final wording",
        "placeholder": (
            "Paste the near-final script you want to keep mostly as written. The app will mostly split it "
            "into scenes..."
        ),
    },
}

VISUAL_SOURCE_STRATEGY_LABELS: dict[str, str] = {
    "images_only": "AI Images Only",
    "mixed_media": "Mix AI Images + Uploaded Video Clips",
    "video_preferred": "Prefer Uploaded Video Clips When It Helps",
}

VISUAL_SOURCE_STRATEGY_HELP = (
    "Choose whether this project should stay as a slide video or mix in uploaded footage. "
    "You can still change individual scenes later in Step 2."
)

VISUAL_SOURCE_STRATEGY_GUIDANCE: dict[str, str] = {
    "images_only": (
        "Best for classic narrated slide videos. The storyboard will stay image-first and the scene editor will expect still visuals by default."
    ),
    "mixed_media": (
        "Use this when you have some footage or screen recordings for key moments, but still want most scenes to behave like slides."
    ),
    "video_preferred": (
        "Use this when the story should be carried mainly by uploaded clips, demos, or recordings, with still images only where needed."
    ),
}

IMAGE_PROVIDER_LABELS: dict[str, str] = {
    "replicate": "Replicate Qwen (Cloud)",
    "local": "Local Qwen (Hugging Face)",
    "manual": "Upload / Local Assets Only",
}

VIDEO_PROVIDER_LABELS: dict[str, str] = {
    "manual": "Upload / Local Clips Only",
    "local": "Local Video Backend",
    "replicate": "Cloud Video Generation",
}

VIDEO_MODEL_SELECTION_MODE_LABELS: dict[str, str] = {
    "automatic": "Automatic",
    "advanced": "Advanced",
}

VIDEO_SCENE_KIND_LABELS: dict[str, str] = {
    "auto": "Auto",
    "cinematic": "Cinematic",
    "speaking": "Speaking",
}

BRIEF_VIDEO_SCENE_STYLE_LABELS: dict[str, str] = {
    "auto": "Auto",
    "cinematic": "Cinematic Clips",
    "speaking": "Speaking Clips",
    "mixed": "Mixed Clip Styles",
}

REPLICATE_VIDEO_MODEL_LABELS: dict[str, str] = {
    _default_replicate_video_generation_model_impl(): "Kling 3 Video",
    DEFAULT_REPLICATE_SPEAKING_VIDEO_MODEL: "Kling Avatar v2",
    "__custom__": "Custom slug",
}


def _replicate_video_model_preset(model_slug: str | None) -> str:
    value = str(model_slug or "").strip()
    if not value:
        return _default_replicate_video_generation_model_impl()
    return value if value in REPLICATE_VIDEO_MODEL_LABELS and value != "__custom__" else "__custom__"


def _replicate_video_route_summary(scene: dict | None = None) -> dict[str, str]:
    scene_payload = scene if isinstance(scene, dict) else {}
    return resolve_replicate_video_generation_route(
        scene_payload,
        model=str(st.session_state.video_generation_model or ""),
        model_selection_mode=str(st.session_state.video_model_selection_mode or "automatic"),
        generate_audio=bool(st.session_state.video_generate_audio),
    )


def check_api_keys() -> dict[str, bool]:
    """Check which API keys are configured."""
    return _check_api_keys_impl()


def _available_tts_providers(keys: dict[str, bool]) -> dict[str, str]:
    return _available_tts_providers_impl(keys)


def _available_image_generation_providers(keys: dict[str, bool]) -> list[str]:
    return _available_image_generation_providers_impl(keys)


def _available_video_generation_providers() -> list[str]:
    return _available_video_generation_providers_impl()


def get_project_path(project_name: str, overwrite: bool = False) -> Path:
    """
    Get path for a project, handling naming collisions.

    If overwrite is False and project exists, auto-increments: project__02, project__03, etc.
    If overwrite is True, returns existing path (caller should delete if needed).
    """
    return _get_project_path(project_name, overwrite=overwrite)


def load_plan(project_dir: Path) -> dict | None:
    """Load and backfill plan.json from a project directory."""
    try:
        return _load_plan(project_dir)
    except json.JSONDecodeError as e:
        st.error(f"Corrupted plan.json in {project_dir.name}: {e}")
        return None


def save_plan(project_dir: Path, plan: dict) -> None:
    """Save normalized plan.json to a project directory."""
    _save_plan(project_dir, plan)


def init_session_state():
    """Initialize Streamlit session state."""
    if "step" not in st.session_state:
        st.session_state.step = 1
    if "project_dir" not in st.session_state:
        st.session_state.project_dir = None
    if "plan" not in st.session_state:
        st.session_state.plan = None
    if "pending_profile_sync" not in st.session_state:
        st.session_state.pending_profile_sync = None
    if "tts_voice" not in st.session_state:
        st.session_state.tts_voice = DEFAULT_VOICE
    if "tts_speed" not in st.session_state:
        st.session_state.tts_speed = DEFAULT_SPEED
    if "tts_provider" not in st.session_state:
        st.session_state.tts_provider = "kokoro"  # Default to free local TTS
    if "tts_exaggeration" not in st.session_state:
        st.session_state.tts_exaggeration = DEFAULT_EXAGGERATION
    if "tts_openai_voice" not in st.session_state:
        st.session_state.tts_openai_voice = DEFAULT_OPENAI_TTS_VOICE
    if "tts_openai_model_id" not in st.session_state:
        st.session_state.tts_openai_model_id = DEFAULT_OPENAI_TTS_MODEL
    if "tts_openai_realtime_model_id" not in st.session_state:
        st.session_state.tts_openai_realtime_model_id = DEFAULT_OPENAI_REALTIME_MODEL
    if "image_provider" not in st.session_state:
        st.session_state.image_provider = default_image_profile()["provider"]
    if "image_generation_model" not in st.session_state:
        st.session_state.image_generation_model = default_image_profile()["generation_model"]
    if "video_provider" not in st.session_state:
        st.session_state.video_provider = default_video_profile()["provider"]
    if "video_generation_model" not in st.session_state:
        st.session_state.video_generation_model = default_video_profile()["generation_model"]
    if "video_model_selection_mode" not in st.session_state:
        st.session_state.video_model_selection_mode = default_video_profile()["model_selection_mode"]
    if "video_quality_mode" not in st.session_state:
        st.session_state.video_quality_mode = default_video_profile()["quality_mode"]
    if "video_generate_audio" not in st.session_state:
        st.session_state.video_generate_audio = bool(default_video_profile()["generate_audio"])

    # ElevenLabs-specific settings (kept separate from Kokoro voice/speed)
    if "tts_elevenlabs_voice" not in st.session_state:
        st.session_state.tts_elevenlabs_voice = DEFAULT_ELEVENLABS_VOICE
    if "tts_elevenlabs_speed" not in st.session_state:
        st.session_state.tts_elevenlabs_speed = float(DEFAULT_ELEVENLABS_SPEED)
    if "tts_elevenlabs_model_id" not in st.session_state:
        st.session_state.tts_elevenlabs_model_id = DEFAULT_ELEVENLABS_MODEL
    if "tts_elevenlabs_text_normalization" not in st.session_state:
        st.session_state.tts_elevenlabs_text_normalization = DEFAULT_ELEVENLABS_TEXT_NORMALIZATION
    if "tts_elevenlabs_stability" not in st.session_state:
        st.session_state.tts_elevenlabs_stability = DEFAULT_ELEVENLABS_STABILITY
    if "tts_elevenlabs_similarity_boost" not in st.session_state:
        st.session_state.tts_elevenlabs_similarity_boost = DEFAULT_ELEVENLABS_SIMILARITY_BOOST
    if "tts_elevenlabs_style" not in st.session_state:
        st.session_state.tts_elevenlabs_style = DEFAULT_ELEVENLABS_STYLE
    if "tts_elevenlabs_use_speaker_boost" not in st.session_state:
        st.session_state.tts_elevenlabs_use_speaker_boost = DEFAULT_ELEVENLABS_USE_SPEAKER_BOOST

    # Image edit model (used for per-scene "Edit Image").
    if "image_edit_model" not in st.session_state:
        st.session_state.image_edit_model = default_image_edit_model()

    # DashScope-specific image edit parameters
    if "dashscope_edit_n" not in st.session_state:
        st.session_state.dashscope_edit_n = 1
    if "dashscope_edit_seed" not in st.session_state:
        st.session_state.dashscope_edit_seed = ""  # Empty string = random
    if "dashscope_edit_negative_prompt" not in st.session_state:
        st.session_state.dashscope_edit_negative_prompt = ""
    if "dashscope_edit_prompt_extend" not in st.session_state:
        st.session_state.dashscope_edit_prompt_extend = True

    if st.session_state.pending_profile_sync:
        _sync_provider_state_from_plan(st.session_state.pending_profile_sync)
        st.session_state.pending_profile_sync = None


def _tts_kwargs_from_state() -> dict:
    """Build kwargs for generate_scene_audio() based on current sidebar settings."""
    return _tts_kwargs_from_profile(_tts_profile_from_state())


def _tts_kwargs_from_profile(profile: dict | None) -> dict:
    """Build kwargs for generate_scene_audio() from a persisted or session profile."""
    profile = profile if isinstance(profile, dict) else {}
    provider = str(profile.get("provider") or "kokoro")
    kwargs: dict = {"tts_provider": provider}

    if provider == "kokoro":
        kwargs.update(
            {
                "voice": str(profile.get("voice") or st.session_state.tts_voice),
                "speed": float(profile.get("speed") or st.session_state.tts_speed),
            }
        )
        return kwargs

    if provider == "elevenlabs":
        kwargs.update(
            {
                "voice": str(profile.get("voice") or st.session_state.tts_elevenlabs_voice),
                "speed": float(profile.get("speed") or st.session_state.tts_elevenlabs_speed),
                "elevenlabs_model_id": str(profile.get("model_id") or st.session_state.tts_elevenlabs_model_id),
                "elevenlabs_apply_text_normalization": str(
                    profile.get("text_normalization") or st.session_state.tts_elevenlabs_text_normalization
                ),
                "elevenlabs_stability": float(
                    profile.get("stability") if profile.get("stability") is not None else st.session_state.tts_elevenlabs_stability
                ),
                "elevenlabs_similarity_boost": float(
                    profile.get("similarity_boost")
                    if profile.get("similarity_boost") is not None
                    else st.session_state.tts_elevenlabs_similarity_boost
                ),
                "elevenlabs_style": float(
                    profile.get("style") if profile.get("style") is not None else st.session_state.tts_elevenlabs_style
                ),
                "elevenlabs_use_speaker_boost": bool(
                    profile.get("use_speaker_boost")
                    if profile.get("use_speaker_boost") is not None
                    else st.session_state.tts_elevenlabs_use_speaker_boost
                ),
            }
        )
        return kwargs

    if provider == "chatterbox":
        kwargs["exaggeration"] = float(
            profile.get("exaggeration") if profile.get("exaggeration") is not None else st.session_state.tts_exaggeration
        )
        return kwargs

    if provider == "openai":
        kwargs["voice"] = str(profile.get("voice") or st.session_state.tts_openai_voice)
        kwargs["speed"] = float(profile.get("speed") or 1.0)
        kwargs["openai_model_id"] = str(profile.get("model_id") or st.session_state.tts_openai_model_id)
        return kwargs
    if provider == "openai_realtime":
        kwargs["voice"] = str(profile.get("voice") or st.session_state.tts_openai_voice)
        kwargs["speed"] = float(profile.get("speed") or 1.0)
        kwargs["openai_model_id"] = str(profile.get("model_id") or st.session_state.tts_openai_realtime_model_id)
        return kwargs

    return kwargs


def _tts_profile_from_state() -> dict:
    """Persist user-selected TTS settings in plan metadata."""
    provider = str(st.session_state.tts_provider)
    if provider == "elevenlabs":
        return {
            "provider": "elevenlabs",
            "voice": str(st.session_state.tts_elevenlabs_voice),
            "speed": float(st.session_state.tts_elevenlabs_speed),
            "model_id": str(st.session_state.tts_elevenlabs_model_id),
            "text_normalization": str(st.session_state.tts_elevenlabs_text_normalization),
            "stability": float(st.session_state.tts_elevenlabs_stability),
            "similarity_boost": float(st.session_state.tts_elevenlabs_similarity_boost),
            "style": float(st.session_state.tts_elevenlabs_style),
            "use_speaker_boost": bool(st.session_state.tts_elevenlabs_use_speaker_boost),
        }
    if provider == "kokoro":
        return {
            "provider": "kokoro",
            "voice": str(st.session_state.tts_voice),
            "speed": float(st.session_state.tts_speed),
        }
    if provider == "chatterbox":
        return {
            "provider": "chatterbox",
            "voice": "",
            "speed": 1.0,
            "exaggeration": float(st.session_state.tts_exaggeration),
        }
    return {
        "provider": provider,
        "voice": str(st.session_state.tts_openai_voice) if provider in {"openai", "openai_realtime"} else "",
        "speed": 1.0,
        "model_id": (
            str(st.session_state.tts_openai_realtime_model_id)
            if provider == "openai_realtime"
            else str(st.session_state.tts_openai_model_id)
            if provider == "openai"
            else ""
        ),
    }


def _image_profile_from_state() -> dict:
    return _resolve_image_profile_impl(
        {
            "provider": str(st.session_state.image_provider or "manual"),
            "generation_model": str(
                st.session_state.image_generation_model or default_image_profile()["generation_model"]
            ),
            "edit_model": str(st.session_state.image_edit_model or default_image_edit_model()),
        }
    )


def _video_profile_from_state() -> dict:
    return _resolve_video_profile_impl(
        {
            "provider": str(st.session_state.video_provider or "manual"),
            "generation_model": str(st.session_state.video_generation_model or ""),
            "model_selection_mode": str(st.session_state.video_model_selection_mode or "automatic"),
            "quality_mode": str(st.session_state.video_quality_mode or "standard"),
            "generate_audio": bool(st.session_state.video_generate_audio),
        }
    )


def _sync_provider_state_from_plan(plan: dict | None) -> None:
    if not isinstance(plan, dict):
        return

    meta = plan.get("meta") if isinstance(plan.get("meta"), dict) else {}
    tts_profile = meta.get("tts_profile") if isinstance(meta.get("tts_profile"), dict) else {}
    image_profile = meta.get("image_profile") if isinstance(meta.get("image_profile"), dict) else {}
    video_profile = meta.get("video_profile") if isinstance(meta.get("video_profile"), dict) else {}

    provider = str(tts_profile.get("provider") or "kokoro")
    if provider in {"kokoro", "elevenlabs", "chatterbox", "openai", "openai_realtime"}:
        st.session_state.tts_provider = provider
    if tts_profile.get("voice"):
        voice = str(tts_profile["voice"])
        if provider == "kokoro":
            st.session_state.tts_voice = voice
        elif provider == "elevenlabs":
            st.session_state.tts_elevenlabs_voice = voice
        elif provider in {"openai", "openai_realtime"}:
            st.session_state.tts_openai_voice = voice
    if provider == "kokoro" and tts_profile.get("speed") is not None:
        st.session_state.tts_speed = float(tts_profile["speed"])
    if provider == "elevenlabs":
        if tts_profile.get("speed") is not None:
            st.session_state.tts_elevenlabs_speed = float(tts_profile["speed"])
        if tts_profile.get("model_id"):
            st.session_state.tts_elevenlabs_model_id = str(tts_profile["model_id"])
        if tts_profile.get("text_normalization"):
            st.session_state.tts_elevenlabs_text_normalization = str(tts_profile["text_normalization"])
        if tts_profile.get("stability") is not None:
            st.session_state.tts_elevenlabs_stability = float(tts_profile["stability"])
        if tts_profile.get("similarity_boost") is not None:
            st.session_state.tts_elevenlabs_similarity_boost = float(tts_profile["similarity_boost"])
        if tts_profile.get("style") is not None:
            st.session_state.tts_elevenlabs_style = float(tts_profile["style"])
        if tts_profile.get("use_speaker_boost") is not None:
            st.session_state.tts_elevenlabs_use_speaker_boost = bool(tts_profile["use_speaker_boost"])
    if provider == "chatterbox" and tts_profile.get("exaggeration") is not None:
        st.session_state.tts_exaggeration = float(tts_profile["exaggeration"])
    if provider == "openai" and tts_profile.get("model_id"):
        st.session_state.tts_openai_model_id = str(tts_profile["model_id"])
    if provider == "openai_realtime" and tts_profile.get("model_id"):
        st.session_state.tts_openai_realtime_model_id = str(tts_profile["model_id"])

    image_provider = str(image_profile.get("provider") or default_image_profile()["provider"])
    if image_provider in IMAGE_PROVIDER_LABELS:
        st.session_state.image_provider = image_provider
    image_generation_model = str(image_profile.get("generation_model") or "").strip()
    if image_provider == "local" and not image_generation_model:
        image_generation_model = _default_local_image_generation_model_impl()
    if not image_generation_model:
        image_generation_model = default_image_profile()["generation_model"]
    st.session_state.image_generation_model = image_generation_model
    st.session_state.image_edit_model = str(
        image_profile.get("edit_model") or default_image_edit_model()
    )

    video_provider = str(video_profile.get("provider") or default_video_profile()["provider"])
    if video_provider in VIDEO_PROVIDER_LABELS:
        st.session_state.video_provider = video_provider
    st.session_state.video_generation_model = str(
        video_profile.get("generation_model") or default_video_profile()["generation_model"]
    )
    st.session_state.video_model_selection_mode = str(
        video_profile.get("model_selection_mode") or default_video_profile()["model_selection_mode"]
    )
    st.session_state.video_quality_mode = str(
        video_profile.get("quality_mode") or default_video_profile()["quality_mode"]
    )
    st.session_state.video_generate_audio = bool(
        video_profile.get("generate_audio")
        if video_profile.get("generate_audio") is not None
        else default_video_profile()["generate_audio"]
    )


def _persist_sidebar_profiles_to_plan() -> None:
    project_dir = st.session_state.project_dir
    plan = st.session_state.plan
    if not project_dir or not isinstance(plan, dict):
        return

    normalized = backfill_plan(plan)
    meta = normalized.setdefault("meta", {})
    changed = False

    tts_profile = _tts_profile_from_state()
    if meta.get("tts_profile") != tts_profile:
        meta["tts_profile"] = tts_profile
        changed = True

    image_profile = _image_profile_from_state()
    if meta.get("image_profile") != image_profile:
        meta["image_profile"] = image_profile
        meta["image_model"] = image_profile["generation_model"]
        changed = True

    video_profile = _video_profile_from_state()
    if meta.get("video_profile") != video_profile:
        meta["video_profile"] = video_profile
        meta["video_model"] = video_profile["generation_model"]
        changed = True

    if changed:
        save_plan(project_dir, normalized)
        st.session_state.plan = normalized


def get_existing_projects() -> list[str]:
    """Get list of existing project folders."""
    return sorted(_list_projects(), reverse=True)  # Most recent first


def _brief_defaults_for_form() -> dict:
    if st.session_state.plan and isinstance(st.session_state.plan.get("meta"), dict):
        brief = st.session_state.plan["meta"].get("brief")
        if isinstance(brief, dict):
            return normalize_brief(brief)
    return normalize_brief({})


def _sync_scene_on_screen_text(scene: dict, value: str) -> None:
    lines = [line.strip() for line in str(value).splitlines() if line.strip()]
    scene["on_screen_text"] = lines


def _new_blank_scene(scene_id: int) -> dict:
    return {
        "id": scene_id,
        "uid": str(uuid.uuid4())[:8],
        "title": "New Scene",
        "narration": "",
        "visual_prompt": "",
        "scene_type": "image",
        "video_scene_kind": None,
        "on_screen_text": [],
        "refinement_history": [],
        "image_path": None,
        "video_path": None,
        "video_reference_image_path": None,
        "video_trim_start": 0.0,
        "video_trim_end": None,
        "video_playback_speed": 1.0,
        "video_hold_last_frame": True,
        "video_audio_source": "narration",
        "audio_path": None,
    }


def _scene_type(scene: dict) -> str:
    scene_type = str(scene.get("scene_type") or "image").strip().lower()
    return scene_type if scene_type in {"image", "video"} else "image"


def _scene_has_image(scene: dict) -> bool:
    image_path = scene.get("image_path")
    return bool(image_path and Path(str(image_path)).exists())


def _scene_has_video(scene: dict) -> bool:
    video_path = scene.get("video_path")
    return bool(video_path and Path(str(video_path)).exists())


def _scene_has_primary_visual(scene: dict) -> bool:
    return _scene_has_video(scene) if _scene_type(scene) == "video" else _scene_has_image(scene)


def _scene_has_renderable_audio(scene: dict) -> bool:
    if _scene_has_video(scene) and scene_uses_clip_audio(scene):
        return media_has_audio_stream(scene["video_path"])
    audio_path = scene.get("audio_path")
    return bool(audio_path and Path(str(audio_path)).exists())


def _existing_style_reference_paths_from_defaults(defaults: dict) -> list[Path]:
    paths = defaults.get("style_reference_paths")
    if not isinstance(paths, list):
        return []
    valid_paths = []
    for item in paths:
        path = Path(str(item))
        if path.exists():
            valid_paths.append(path)
    return valid_paths


def _save_style_reference_images(
    *,
    project_dir: Path,
    uploaded_files: list,
    existing_paths: list[Path],
) -> list[Path]:
    """Persist uploaded or previously saved style reference images into the project."""
    style_dir = project_dir / "style_refs"
    style_dir.mkdir(parents=True, exist_ok=True)

    saved_paths: list[Path] = []
    if uploaded_files:
        for idx, uploaded in enumerate(uploaded_files, start=1):
            ext = Path(uploaded.name).suffix.lower() or ".png"
            out_path = style_dir / f"style_ref_{idx:02d}{ext}"
            out_path.write_bytes(uploaded.getvalue())
            saved_paths.append(out_path)
        return saved_paths

    for idx, src in enumerate(existing_paths, start=1):
        ext = src.suffix.lower() or ".png"
        out_path = style_dir / f"style_ref_{idx:02d}{ext}"
        out_path.write_bytes(src.read_bytes())
        saved_paths.append(out_path)
    return saved_paths


def render_sidebar():
    """Render sidebar with key status, project picker, and voice settings."""
    with st.sidebar:
        st.title(PRODUCT_NAME)

        # API Key Status
        st.subheader("API Keys")
        keys = check_api_keys()

        for service, configured in keys.items():
            icon = "OK" if configured else "MISSING"
            st.write(f"- {service}: {icon}")

        if not keys.get("replicate"):
            st.info("REPLICATE_API_TOKEN missing. AI image generation will be disabled, but uploaded/local visuals still work.")
        if not (keys.get("openai") or keys.get("anthropic")):
            st.warning("Missing LLM key (set OPENAI_API_KEY or ANTHROPIC_API_KEY).")

        st.divider()

        st.subheader("Image Settings")
        image_provider_options = _available_image_generation_providers(keys)
        if st.session_state.image_provider not in image_provider_options:
            st.session_state.image_provider = image_provider_options[0]
        st.selectbox(
            "Image Generation",
            options=image_provider_options,
            format_func=lambda value: IMAGE_PROVIDER_LABELS[value],
            key="image_provider",
            help="Choose between cloud image generation and a fully local upload-first workflow.",
        )
        if (
            st.session_state.image_provider == "local"
            and str(st.session_state.image_generation_model or "").strip()
            in {"", default_image_profile()["generation_model"]}
        ):
            st.session_state.image_generation_model = _default_local_image_generation_model_impl()
        if st.session_state.image_provider == "replicate":
            st.caption("Cloud image generation uses Qwen Image 2512 on Replicate.")
        elif st.session_state.image_provider == "local":
            model_label = str(st.session_state.image_generation_model or _default_local_image_generation_model_impl()).strip()
            if model_label:
                st.caption(f"Configured local image model: `{model_label}`")
            st.caption("Local image generation runs the configured Hugging Face Qwen model on this machine.")
        else:
            st.caption("Manual image mode skips AI generation. Upload stills or clips in Step 2 and keep the rest of the pipeline local.")

        edit_models = available_image_edit_models(
            include_openai=bool(keys.get("openai")),
            include_replicate=bool(keys.get("replicate")),
            include_dashscope=bool(keys.get("dashscope")),
        )
        if edit_models:
            if st.session_state.image_edit_model not in edit_models:
                st.session_state.image_edit_model = edit_models[0]
            st.selectbox(
                "Image Edit Backend",
                options=edit_models,
                key="image_edit_model",
                help="Used by per-scene Edit Image actions.",
            )
            st.caption(
                "Default is GPT Image 2, using local Codex execution when available and direct OpenAI API otherwise."
            )
        else:
            st.info("No AI image edit backend configured. Add OPENAI_API_KEY, REPLICATE_API_TOKEN, or DASHSCOPE_API_KEY to enable Edit Image.")

        is_dashscope_model = str(st.session_state.image_edit_model).startswith("qwen-image-edit")
        if edit_models and is_dashscope_model:
            st.caption("DashScope Parameters")
            st.session_state.dashscope_edit_n = st.slider(
                "Variants (n)",
                min_value=1,
                max_value=6,
                value=int(st.session_state.dashscope_edit_n),
                key="dashscope_n_slider",
            )
            seed_input = st.text_input(
                "Seed",
                value=str(st.session_state.dashscope_edit_seed),
                key="dashscope_seed_input",
                help="Integer 0-2147483647; empty means random.",
            )
            st.session_state.dashscope_edit_seed = seed_input.strip()
            st.session_state.dashscope_edit_prompt_extend = st.checkbox(
                "Prompt extend",
                value=bool(st.session_state.dashscope_edit_prompt_extend),
                key="dashscope_prompt_extend_checkbox",
            )
            st.session_state.dashscope_edit_negative_prompt = st.text_input(
                "Negative prompt",
                value=str(st.session_state.dashscope_edit_negative_prompt),
                key="dashscope_negative_prompt_input",
            )

        st.divider()

        st.subheader("Video Settings")
        video_provider_options = _available_video_generation_providers()
        if st.session_state.video_provider not in video_provider_options:
            st.session_state.video_provider = video_provider_options[0]
        st.selectbox(
            "Video Generation",
            options=video_provider_options,
            format_func=lambda value: VIDEO_PROVIDER_LABELS[value],
            key="video_provider",
            help="Choose between upload-only clips and a configured local video generation backend.",
        )
        resolved_video_profile = _video_profile_from_state()
        st.session_state.video_generation_model = str(resolved_video_profile.get("generation_model") or "")
        st.session_state.video_model_selection_mode = str(
            resolved_video_profile.get("model_selection_mode") or "automatic"
        )
        st.session_state.video_quality_mode = str(resolved_video_profile.get("quality_mode") or "standard")
        st.session_state.video_generate_audio = bool(resolved_video_profile.get("generate_audio", True))
        if st.session_state.video_provider == "local":
            model_label = str(st.session_state.video_generation_model or "").strip()
            if model_label:
                st.caption(f"Configured local video model: `{model_label}`")
            st.caption(
                "Local video generation is env-driven. Cathode will call the configured local command or HTTP endpoint when you generate video clips."
            )
        elif st.session_state.video_provider == "replicate":
            st.selectbox(
                "Model Selection",
                options=list(VIDEO_MODEL_SELECTION_MODE_LABELS.keys()),
                index=list(VIDEO_MODEL_SELECTION_MODE_LABELS.keys()).index(
                    str(st.session_state.video_model_selection_mode or "automatic")
                    if str(st.session_state.video_model_selection_mode or "automatic") in VIDEO_MODEL_SELECTION_MODE_LABELS
                    else "automatic"
                ),
                format_func=lambda value: VIDEO_MODEL_SELECTION_MODE_LABELS[value],
                key="video_model_selection_mode",
                help="Automatic mode picks the right cloud video model for the scene. Advanced mode lets you override it.",
            )
            if st.session_state.video_model_selection_mode == "automatic":
                st.session_state.video_generation_model = ""
                st.caption(
                    "Automatic route: Cathode uses Kling 3 Video for cinematic clips and switches to Kling Avatar v2 for speaking clips when clip audio is enabled."
                )
            else:
                current_preset = _replicate_video_model_preset(st.session_state.video_generation_model)
                selected_preset = st.selectbox(
                    "Video Model",
                    options=list(REPLICATE_VIDEO_MODEL_LABELS.keys()),
                    index=list(REPLICATE_VIDEO_MODEL_LABELS.keys()).index(current_preset),
                    format_func=lambda value: REPLICATE_VIDEO_MODEL_LABELS[value],
                    help="Choose a curated model or switch to a custom Replicate slug.",
                )
                if selected_preset == "__custom__":
                    st.text_input(
                        "Custom Video Model",
                        key="video_generation_model",
                        help="Advanced override for a custom Replicate video model slug.",
                    )
                else:
                    st.session_state.video_generation_model = selected_preset
            st.selectbox(
                "Generation quality",
                options=["standard", "pro"],
                key="video_quality_mode",
                help="Higher quality costs more but improves realism and detail.",
            )
            st.checkbox(
                "Generate clip audio",
                key="video_generate_audio",
                help="Enable when you want the generated clip to include its own voice or ambient audio.",
            )
            st.caption(
                "Cloud video generation creates scene clips directly from your shot direction. Generated clip audio can be used during render instead of a separate narration track."
            )
        else:
            st.caption("Upload video clips manually in Step 2.")

        st.divider()

        # Project selector
        st.subheader("Projects")
        existing = get_existing_projects()

        if existing:
            selected = st.selectbox(
                "Open existing project",
                options=["-- New Project --"] + existing,
                key="project_selector",
            )

            if selected != "-- New Project --":
                if st.button("Load Project", type="primary"):
                    project_dir = PROJECTS_DIR / selected
                    plan = load_plan(project_dir)
                    if plan:
                        st.session_state.project_dir = project_dir
                        st.session_state.plan = plan
                        st.session_state.pending_profile_sync = plan
                        try:
                            mp4s = sorted(
                                project_dir.glob("*.mp4"),
                                key=lambda p: p.stat().st_mtime,
                                reverse=True,
                            )
                        except Exception:
                            mp4s = []
                        if mp4s:
                            st.session_state.step = 3
                            st.session_state.render_output_name = mp4s[0].name
                        else:
                            st.session_state.step = 2
                        st.rerun()
                    else:
                        st.error("Could not load project")
        else:
            st.caption("No existing projects")

        st.divider()

        if st.session_state.project_dir:
            st.subheader("Current Project")
            st.write(f"Folder: {st.session_state.project_dir.name}")

            if st.session_state.plan:
                num_scenes = len(st.session_state.plan.get("scenes", []))
                st.write(f"Scenes: {num_scenes}")

            if st.button("Close Project"):
                st.session_state.project_dir = None
                st.session_state.plan = None
                st.session_state.step = 1
                st.rerun()

        st.divider()

        # TTS Settings
        st.subheader("Voice Settings")
        tts_providers = _available_tts_providers(keys)
        provider_keys = list(tts_providers.keys())
        current_provider = (
            st.session_state.tts_provider
            if st.session_state.tts_provider in provider_keys
            else provider_keys[0]
        )
        selected_provider = st.selectbox(
            "TTS Provider",
            options=provider_keys,
            format_func=lambda p: tts_providers[p],
            index=provider_keys.index(current_provider),
            key="tts_provider_selector",
        )
        st.session_state.tts_provider = selected_provider

        if selected_provider == "kokoro":
            voice_options = list(KOKORO_VOICES.keys())
            current_voice_idx = (
                voice_options.index(st.session_state.tts_voice)
                if st.session_state.tts_voice in voice_options
                else 0
            )
            selected_voice = st.selectbox(
                "Voice",
                options=voice_options,
                format_func=lambda v: f"{v} - {KOKORO_VOICES[v]}",
                index=current_voice_idx,
                key="kokoro_voice_selector",
            )
            st.session_state.tts_voice = selected_voice
            speed = st.slider(
                "Speed",
                min_value=0.8,
                max_value=1.5,
                value=float(st.session_state.tts_speed),
                step=0.1,
                key="kokoro_speed_slider",
            )
            st.session_state.tts_speed = speed

        elif selected_provider == "chatterbox":
            st.session_state.tts_exaggeration = st.slider(
                "Exaggeration",
                min_value=0.25,
                max_value=2.0,
                value=float(st.session_state.tts_exaggeration),
                step=0.05,
                key="chatterbox_exaggeration_slider",
                help="Higher values make Chatterbox more expressive.",
            )

        elif selected_provider == "elevenlabs":
            voice_options = list(ELEVENLABS_VOICES.keys())
            current_voice_idx = (
                voice_options.index(st.session_state.tts_elevenlabs_voice)
                if st.session_state.tts_elevenlabs_voice in voice_options
                else 0
            )
            selected_voice = st.selectbox(
                "Voice",
                options=voice_options,
                format_func=lambda v: f"{v} - {ELEVENLABS_VOICES[v][1]}",
                index=current_voice_idx,
                key="elevenlabs_voice_selector",
            )
            st.session_state.tts_elevenlabs_voice = selected_voice
            st.session_state.tts_elevenlabs_stability = st.slider(
                "Stability",
                min_value=0.0,
                max_value=1.0,
                value=float(st.session_state.tts_elevenlabs_stability),
                step=0.05,
                key="elevenlabs_stability",
            )
            st.session_state.tts_elevenlabs_similarity_boost = st.slider(
                "Similarity Boost",
                min_value=0.0,
                max_value=1.0,
                value=float(st.session_state.tts_elevenlabs_similarity_boost),
                step=0.05,
                key="elevenlabs_similarity_boost",
            )
            st.session_state.tts_elevenlabs_style = st.slider(
                "Style",
                min_value=0.0,
                max_value=1.0,
                value=float(st.session_state.tts_elevenlabs_style),
                step=0.05,
                key="elevenlabs_style",
            )
            st.session_state.tts_elevenlabs_speed = st.slider(
                "Speed",
                min_value=0.7,
                max_value=1.4,
                value=float(st.session_state.tts_elevenlabs_speed),
                step=0.05,
                key="elevenlabs_speed",
            )
            st.session_state.tts_elevenlabs_use_speaker_boost = st.checkbox(
                "Use Speaker Boost",
                value=bool(st.session_state.tts_elevenlabs_use_speaker_boost),
                key="elevenlabs_use_speaker_boost",
            )
            st.session_state.tts_elevenlabs_text_normalization = st.selectbox(
                "Text Normalization",
                options=["auto", "on", "off"],
                index=["auto", "on", "off"].index(
                    str(st.session_state.tts_elevenlabs_text_normalization)
                ),
                key="elevenlabs_text_normalization",
            )
        elif selected_provider in {"openai", "openai_realtime"}:
            voice_options = sorted(OPENAI_REALTIME_VOICES if selected_provider == "openai_realtime" else OPENAI_TTS_VOICES)
            current_voice = (
                st.session_state.tts_openai_voice
                if st.session_state.tts_openai_voice in voice_options
                else DEFAULT_OPENAI_TTS_VOICE
            )
            st.session_state.tts_openai_voice = st.selectbox(
                "Voice",
                options=voice_options,
                index=voice_options.index(current_voice),
                key=f"{selected_provider}_voice_selector",
            )
            if selected_provider == "openai":
                st.session_state.tts_openai_model_id = st.text_input(
                    "Model",
                    value=str(st.session_state.tts_openai_model_id or DEFAULT_OPENAI_TTS_MODEL),
                    key="openai_tts_model_id",
                )
            else:
                st.session_state.tts_openai_realtime_model_id = st.text_input(
                    "Model",
                    value=str(st.session_state.tts_openai_realtime_model_id or DEFAULT_OPENAI_REALTIME_MODEL),
                    key="openai_realtime_model_id",
                    help="Uses a server-side Realtime voice session and writes the returned audio into the project.",
                )

        _persist_sidebar_profiles_to_plan()

        st.divider()
        st.subheader("Steps")
        steps = ["1. Brief", "2. Scenes", "3. Render"]
        for i, step_name in enumerate(steps, 1):
            if i == st.session_state.step:
                st.write(f"-> {step_name}")
            elif i < st.session_state.step:
                st.write(f"OK {step_name}")
            else:
                st.write(f".. {step_name}")


def render_step_1():
    """Step 1: Input project brief and generate storyboard."""
    st.header("Step 1: Build Project Brief")

    defaults = _brief_defaults_for_form()

    project_name = st.text_input(
        "Project Name",
        value=defaults["project_name"],
        help="Project folder name on disk. This becomes the folder under projects/ where plan.json, images, audio, and the final video are stored.",
    )
    project_name = sanitize_project_name(project_name)

    existing_path = PROJECTS_DIR / project_name
    if existing_path.exists():
        overwrite = st.checkbox(
            f"Overwrite existing project '{project_name}'",
            value=False,
            help="If unchecked, a new folder with incremented name will be created",
        )
    else:
        overwrite = False

    keys = check_api_keys()
    available_providers = [p for p in ["anthropic", "openai"] if keys.get(p)]
    if not available_providers:
        st.error("No LLM API keys configured. Set OPENAI_API_KEY or ANTHROPIC_API_KEY.")
        return

    provider = st.selectbox(
        "LLM Provider",
        options=available_providers,
        help="Which AI model should write the first storyboard draft from your brief and pasted text.",
    )

    st.subheader("Brief")
    st.caption(
        "Set the outcome, source mode, and clip preferences here. The director uses this brief to plan the storyboard, scene types, and generated-video beats before the rest of the pipeline runs."
    )
    source_mode = st.selectbox(
        "How should the app use the text you paste below?",
        options=list(SOURCE_MODE_LABELS.keys()),
        format_func=lambda m: SOURCE_MODE_LABELS[m],
        index=list(SOURCE_MODE_LABELS.keys()).index(defaults["source_mode"]),
        help=SOURCE_MODE_HELP,
    )
    mode_guidance = SOURCE_MODE_UI_GUIDANCE[source_mode]
    st.info(
        "\n".join(
            [
                f"Use this when: {mode_guidance['when']}.",
                f"Rewriting behavior: {mode_guidance['rewrite']}",
                f"What to paste into Source Material: {mode_guidance['paste']}.",
            ]
        )
    )

    visual_source_strategy = st.selectbox(
        "What should scenes use for visuals?",
        options=list(VISUAL_SOURCE_STRATEGY_LABELS.keys()),
        format_func=lambda value: VISUAL_SOURCE_STRATEGY_LABELS[value],
        index=list(VISUAL_SOURCE_STRATEGY_LABELS.keys()).index(defaults["visual_source_strategy"]),
        help=VISUAL_SOURCE_STRATEGY_HELP,
    )
    st.caption(VISUAL_SOURCE_STRATEGY_GUIDANCE[visual_source_strategy])

    video_scene_style = st.selectbox(
        "How should generated video scenes behave?",
        options=list(BRIEF_VIDEO_SCENE_STYLE_LABELS.keys()),
        format_func=lambda value: BRIEF_VIDEO_SCENE_STYLE_LABELS[value],
        index=list(BRIEF_VIDEO_SCENE_STYLE_LABELS.keys()).index(
            str(defaults.get("video_scene_style") or "auto")
            if str(defaults.get("video_scene_style") or "auto") in BRIEF_VIDEO_SCENE_STYLE_LABELS
            else "auto"
        ),
        help="Use this to steer whether the director should plan generated video scenes as cinematic motion, speaking clips, or let Cathode decide beat by beat.",
    )
    st.caption(
        "This setting steers the director and the automatic video route. You can still change individual scenes later."
    )

    existing_style_reference_paths = _existing_style_reference_paths_from_defaults(defaults)
    style_reference_uploads = st.file_uploader(
        "Style Reference Images (optional)",
        type=["png", "jpg", "jpeg", "webp", "bmp"],
        accept_multiple_files=True,
        help=(
            "Upload one or more reference images when you want the AI to match a specific vibe, finish, palette, composition style, or overall art direction. "
            "The app will analyze them and turn them into a reusable style brief for the whole project."
        ),
    )
    st.caption(
        "If you upload style references, the app will analyze them before storyboard generation and use the resulting style brief across the whole pipeline."
    )
    if existing_style_reference_paths:
        st.caption("Saved style references for this project:")
        st.image([str(path) for path in existing_style_reference_paths], width=180)
    existing_style_summary = str(defaults.get("style_reference_summary") or "").strip()
    if existing_style_summary:
        with st.expander("Current Style Reference Summary"):
            st.write(existing_style_summary)

    col_a, col_b = st.columns(2)
    with col_a:
        video_goal = st.text_input(
            "Video Goal",
            value=defaults["video_goal"],
            help="What should the finished video accomplish for the viewer or the business? Example: explain a feature, train a team, pitch an idea, summarize a report.",
        )
        audience = st.text_input(
            "Audience",
            value=defaults["audience"],
            help="Who is this video for? Example: new customers, executives, internal team, investors, hiring managers.",
        )
        target_length_minutes = st.number_input(
            "Target Length (minutes)",
            min_value=0.5,
            max_value=20.0,
            value=float(defaults["target_length_minutes"]),
            step=0.5,
            help="Approximate final runtime. The app uses this to size scene count and narration length.",
        )
        tone = st.text_input(
            "Tone",
            value=defaults["tone"],
            help="How the narration should sound. Examples: calm, energetic, premium, direct, playful, urgent.",
        )
    with col_b:
        visual_style = st.text_input(
            "Visual Style",
            value=defaults["visual_style"],
            help="How the visuals should feel. Examples: cinematic infographic, minimalist, product demo, editorial, case-study, bold motion-graphic style.",
        )
        must_include = st.text_area(
            "Must Include",
            value=defaults["must_include"],
            height=80,
            help="Facts, phrases, sections, visuals, or calls to action that must appear somewhere in the storyboard.",
        )
        must_avoid = st.text_area(
            "Must Avoid",
            value=defaults["must_avoid"],
            height=80,
            help="Things the app should avoid in wording, framing, tone, visuals, or claims.",
        )
        ending_cta = st.text_input(
            "Ending CTA",
            value=defaults["ending_cta"],
            help="Optional closing call to action for the last scene. Example: book a demo, approve rollout, visit the site, contact sales.",
        )

    source_material = st.text_area(
        "Source Material (paste text here)",
        height=240,
        value=defaults["source_material"],
        placeholder=mode_guidance["placeholder"],
        help="This is the main input. Paste the text you want the app to turn into scenes here. It is not a file picker or directory selector.",
    )
    available_footage = st.text_area(
        "Available Footage / Clip Notes (optional)",
        height=110,
        value=defaults["available_footage"],
        placeholder="Optional. Describe any recordings or clips you already have or can capture: product demo, onboarding flow, dashboard alert moment, gameplay clip, speaker clip, etc.",
        help="Optional. Describe any video footage you want the storyboard to plan around. This helps the app decide when a scene should be a video clip instead of an image slide.",
    )
    raw_brief = st.text_area(
        "Optional Extra Instructions (freeform)",
        height=130,
        value=defaults["raw_brief"],
        placeholder="Optional extra instructions for the AI, such as structure preferences, emphasis, or constraints not already covered above...",
        help="Optional. Use this for extra guidance about how to shape the storyboard, not for the main source text itself. Leave blank if the fields above are enough.",
    )

    can_generate = bool(source_material.strip() or raw_brief.strip())
    if st.button("Generate Storyboard", type="primary", disabled=not can_generate):
        with st.spinner("Generating storyboard..."):
            try:
                project_dir = get_project_path(project_name, overwrite=overwrite)
                if overwrite and project_dir.exists():
                    shutil.rmtree(project_dir)
                project_dir.mkdir(parents=True, exist_ok=True)

                uploaded_style_files = list(style_reference_uploads or [])
                saved_style_reference_paths = _save_style_reference_images(
                    project_dir=project_dir,
                    uploaded_files=uploaded_style_files,
                    existing_paths=existing_style_reference_paths,
                )

                draft_brief = normalize_brief(
                    {
                        "project_name": project_dir.name,
                        "source_mode": source_mode,
                        "video_goal": video_goal,
                        "audience": audience,
                        "source_material": source_material,
                        "target_length_minutes": float(target_length_minutes),
                        "tone": tone,
                        "visual_style": visual_style,
                        "must_include": must_include,
                        "must_avoid": must_avoid,
                        "ending_cta": ending_cta,
                        "visual_source_strategy": visual_source_strategy,
                        "video_scene_style": video_scene_style,
                        "available_footage": available_footage,
                        "style_reference_paths": [str(path) for path in saved_style_reference_paths],
                        "raw_brief": raw_brief,
                    }
                )

                _, plan = create_project_from_brief_service(
                    project_name=project_dir.name,
                    project_dir=project_dir,
                    brief={
                        **draft_brief,
                        "style_reference_paths": [str(path) for path in saved_style_reference_paths],
                    },
                    provider=provider,
                    image_profile=_image_profile_from_state(),
                    video_profile=_video_profile_from_state(),
                    tts_profile=_tts_profile_from_state(),
                )
                st.session_state.project_dir = project_dir
                st.session_state.plan = plan
                st.session_state.pending_profile_sync = plan
                st.session_state.step = 2
                st.rerun()
            except Exception as e:
                st.error(f"Error generating storyboard: {e}")


def render_step_2():
    """Step 2: Edit scenes and generate assets."""
    st.header("Step 2: Edit Scenes")
    st.info(
        "Each scene can be either an Image Slide or a Video Clip. Image scenes use a generated or uploaded still. "
        "Video scenes use an uploaded or generated clip, optional trim/speed settings, and either clip audio or narration during preview/render."
    )

    plan = st.session_state.plan
    project_dir = st.session_state.project_dir
    scenes = plan["scenes"]
    brief = plan.get("meta", {}).get("brief", {})
    image_profile = plan.get("meta", {}).get("image_profile", {})
    image_provider = str(image_profile.get("provider") or "replicate")
    image_generation_model = str(
        image_profile.get("generation_model") or default_image_profile()["generation_model"]
    )
    image_generation_enabled = image_provider in {"replicate", "local"}
    video_profile = plan.get("meta", {}).get("video_profile", {})
    video_provider = str(video_profile.get("provider") or "manual")
    video_generation_model = str(video_profile.get("generation_model") or "")
    video_model_selection_mode = str(video_profile.get("model_selection_mode") or "automatic")
    video_quality_mode = str(video_profile.get("quality_mode") or "standard")
    video_generate_audio = bool(video_profile.get("generate_audio", True))
    video_generation_enabled = video_provider in {"local", "replicate"}
    tts_profile = plan.get("meta", {}).get("tts_profile", {})
    tts_kwargs = tts_kwargs_from_profile(tts_profile)

    if st.button("<- Back to Brief"):
        st.session_state.step = 1
        st.rerun()

    st.divider()

    if st.button("+ Add Scene at Beginning", key="add_scene_start"):
        scenes.insert(0, _new_blank_scene(0))
        for idx, s in enumerate(scenes):
            s["id"] = idx
        save_plan(project_dir, plan)
        st.rerun()

    for i, scene in enumerate(scenes):
        scene_id = scene.get("id", i)
        if "uid" not in scene:
            scene["uid"] = str(uuid.uuid4())[:8]
            save_plan(project_dir, plan)
        scene_uid = scene["uid"]

        with st.expander(f"Scene {scene_id + 1}: {scene['title']}", expanded=i == 0):
            mgmt_col1, mgmt_col2, mgmt_col3 = st.columns([1, 1, 5])
            with mgmt_col1:
                if st.button("Delete", key=f"delete_{scene_uid}", type="secondary"):
                    if len(scenes) > 1:
                        scenes.remove(scene)
                        for idx, s in enumerate(scenes):
                            s["id"] = idx
                        save_plan(project_dir, plan)
                        st.rerun()
                    else:
                        st.warning("Cannot delete the only scene.")
            with mgmt_col2:
                if st.button("Add After", key=f"add_after_{scene_uid}", type="secondary"):
                    scenes.insert(i + 1, _new_blank_scene(scene_id + 1))
                    for idx, s in enumerate(scenes):
                        s["id"] = idx
                    save_plan(project_dir, plan)
                    st.rerun()

            current_scene_type = _scene_type(scene)
            selected_scene_type = st.selectbox(
                "Scene Type",
                options=["image", "video"],
                index=["image", "video"].index(current_scene_type),
                key=f"scene_type_{scene_uid}",
                format_func=lambda value: "Image Slide" if value == "image" else "Video Clip",
                help="Image scenes use a still image. Video scenes use an uploaded or locally generated clip with trim/speed controls and narration-aligned timing.",
            )
            if selected_scene_type != current_scene_type:
                scene["scene_type"] = selected_scene_type
                save_plan(project_dir, plan)
                st.rerun()

            scene_type = selected_scene_type
            st.caption(
                "Image scenes generate or upload a still. Video scenes upload or generate a clip and optionally trim it to the narration."
            )
            st.divider()

            col1, col2 = st.columns([1, 1])
            with col1:
                new_title = st.text_input("Title", value=scene.get("title", ""), key=f"title_{scene_uid}")
                if new_title != scene.get("title", ""):
                    scene["title"] = new_title
                    save_plan(project_dir, plan)

                new_narration = st.text_area(
                    "Narration",
                    value=scene.get("narration", ""),
                    height=120,
                    key=f"narration_{scene_uid}",
                    help="Voiceover text for this scene. Narration length is the timing source of truth during preview and final render.",
                )
                if new_narration != scene.get("narration", ""):
                    scene["narration"] = new_narration
                    save_plan(project_dir, plan)

                narration_feedback = st.text_input(
                    "Refine narration",
                    key=f"narration_feedback_{scene_uid}",
                    placeholder="e.g., tighter and punchier",
                )
                if st.button("Refine Narration", key=f"refine_narration_{scene_uid}"):
                    if narration_feedback.strip():
                        with st.spinner("Refining narration..."):
                            try:
                                provider = plan["meta"]["llm_provider"]
                                refined = refine_narration(
                                    scene.get("narration", ""),
                                    narration_feedback,
                                    provider=provider,
                                )
                                if refined and refined.strip():
                                    scene["narration"] = refined.strip()
                                    save_plan(project_dir, plan)
                                    st.rerun()
                                else:
                                    st.error("Refinement returned empty result.")
                            except Exception as e:
                                st.error(f"Error: {e}")
                    else:
                        st.warning("Enter feedback first.")

                st.divider()

                prompt_label = "Visual Prompt" if scene_type == "image" else "Clip Notes / Shot Direction"
                prompt_help = (
                    "Describe the still image you want to generate for this scene."
                    if scene_type == "image"
                    else "Describe the clip moment you want. Cathode uses this for planning and, when local video generation is enabled, as part of the generation prompt."
                )
                new_prompt = st.text_area(
                    prompt_label,
                    value=scene.get("visual_prompt", ""),
                    height=120,
                    key=f"visual_prompt_{scene_uid}",
                    help=prompt_help,
                )
                if new_prompt != scene.get("visual_prompt", ""):
                    scene["visual_prompt"] = new_prompt
                    save_plan(project_dir, plan)

                on_screen_value = "\n".join(scene.get("on_screen_text", []))
                new_on_screen_value = st.text_area(
                    "On-screen Text (one per line)",
                    value=on_screen_value,
                    height=100,
                    key=f"onscreen_{scene_uid}",
                    help="Planning note for exact words that should appear in the visual. This does not add text overlays automatically; it guides image generation and scene intent.",
                )
                if new_on_screen_value != on_screen_value:
                    _sync_scene_on_screen_text(scene, new_on_screen_value)
                    save_plan(project_dir, plan)

                refinement = st.text_input(
                    "Refine visual prompt" if scene_type == "image" else "Refine clip notes",
                    key=f"refinement_{scene_uid}",
                    placeholder=(
                        "e.g., clearer typography and warmer colors"
                        if scene_type == "image"
                        else "e.g., focus on the exact moment where the anomaly first becomes obvious"
                    ),
                    help=(
                        "For image scenes, this same instruction can either refine the prompt text or directly edit the existing image."
                        if scene_type == "image"
                        else "Use this note to tighten the clip direction before you upload, generate, or trim footage."
                    ),
                )

                col_a, col_b = st.columns(2)
                with col_a:
                    if st.button(
                        "Refine Prompt" if scene_type == "image" else "Refine Notes",
                        key=f"refine_prompt_{scene_uid}",
                    ):
                        if refinement.strip():
                            with st.spinner("Refining prompt..."):
                                try:
                                    provider = plan["meta"]["llm_provider"]
                                    refined = refine_prompt(
                                        scene.get("visual_prompt", ""),
                                        refinement,
                                        narration=scene.get("narration", ""),
                                        provider=provider,
                                    )
                                    if refined and refined.strip():
                                        scene["visual_prompt"] = refined.strip()
                                        save_plan(project_dir, plan)
                                        st.rerun()
                                    else:
                                        st.error("Refinement returned empty result.")
                                except Exception as e:
                                    st.error(f"Error: {e}")
                        else:
                            st.warning("Enter feedback first.")

                with col_b:
                    has_image = _scene_has_image(scene)
                    if scene_type == "image":
                        if st.button(
                            "Edit Image",
                            key=f"edit_image_{scene_uid}",
                            disabled=not has_image,
                        ):
                            if not refinement.strip():
                                st.warning("Enter edit instructions first.")
                            elif has_image:
                                with st.spinner("Editing image..."):
                                    try:
                                        feedback = canonicalize_exact_text_edit_prompt(refinement) or refinement
                                        canonical_image_path = _canonical_scene_image_path(project_dir, scene)
                                        edited_path = (
                                            canonical_image_path.with_name(
                                                f".{canonical_image_path.stem}_edited{canonical_image_path.suffix}"
                                            )
                                            if canonical_image_path is not None
                                            else project_dir / "images" / f"scene_{scene_id:03d}_edited.png"
                                        )
                                        edit_kwargs: dict = {"model": st.session_state.image_edit_model}
                                        if str(st.session_state.image_edit_model).startswith("qwen-image-edit"):
                                            edit_kwargs["n"] = int(st.session_state.dashscope_edit_n)
                                            edit_kwargs["prompt_extend"] = bool(
                                                st.session_state.dashscope_edit_prompt_extend
                                            )
                                            neg = str(st.session_state.dashscope_edit_negative_prompt).strip()
                                            edit_kwargs["negative_prompt"] = neg if neg else " "
                                            seed_str = str(st.session_state.dashscope_edit_seed).strip()
                                            if seed_str.isdigit():
                                                edit_kwargs["seed"] = int(seed_str)
                                            if feedback != refinement:
                                                edit_kwargs["n"] = 1
                                                edit_kwargs["prompt_extend"] = False
                                                edit_kwargs["negative_prompt"] = " "
                                        edit_image(
                                            feedback,
                                            scene["image_path"],
                                            edited_path,
                                            **edit_kwargs,
                                        )
                                        replace_scene_image_preserving_identity(project_dir, scene, edited_path)
                                        scene["video_path"] = None
                                        scene["scene_type"] = "image"
                                        scene["preview_path"] = None
                                        save_plan(project_dir, plan)
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"Error: {e}")

            with col2:
                if scene_type == "image":
                    st.subheader("Image")
                    uploaded = st.file_uploader(
                        "Upload / Replace Image",
                        type=["png", "jpg", "jpeg", "webp", "bmp"],
                        key=f"upload_image_{scene_uid}",
                        help="Use this when you already have the exact still image you want instead of generating one.",
                    )
                    if uploaded is not None:
                        if st.button("Use Uploaded Image", key=f"use_upload_{scene_uid}"):
                            try:
                                ext = Path(uploaded.name).suffix.lower() or ".png"
                                upload_path = project_dir / "images" / f"scene_{scene_id:03d}_upload{ext}"
                                upload_path.parent.mkdir(parents=True, exist_ok=True)
                                upload_path.write_bytes(uploaded.getvalue())
                                scene["image_path"] = str(upload_path)
                                save_plan(project_dir, plan)
                                st.rerun()
                            except Exception as e:
                                st.error(f"Upload failed: {e}")

                    if _scene_has_image(scene):
                        st.image(scene["image_path"], width="stretch")
                        if st.button(
                            "Regenerate Image",
                            key=f"regen_image_{scene_uid}",
                            disabled=not image_generation_enabled,
                        ):
                            with st.spinner("Generating image..."):
                                try:
                                    path = generate_scene_image(
                                        scene,
                                        project_dir,
                                        brief=brief,
                                        provider=image_provider,
                                        model=image_generation_model,
                                    )
                                    scene["image_path"] = str(path)
                                    save_plan(project_dir, plan)
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Error: {e}")
                    else:
                        st.info("No image generated yet.")
                        if st.button(
                            "Generate Image",
                            key=f"gen_image_{scene_uid}",
                            type="primary",
                            disabled=not image_generation_enabled,
                        ):
                            with st.spinner("Generating image..."):
                                try:
                                    path = generate_scene_image(
                                        scene,
                                        project_dir,
                                        brief=brief,
                                        provider=image_provider,
                                        model=image_generation_model,
                                    )
                                    scene["image_path"] = str(path)
                                    save_plan(project_dir, plan)
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Error: {e}")
                        if image_provider == "manual":
                            st.caption("Image generation is set to manual mode. Upload a still image instead.")
                else:
                    st.subheader("Video Clip")
                    current_video_scene_kind = str(scene.get("video_scene_kind") or "").strip().lower()
                    if current_video_scene_kind not in {"cinematic", "speaking"}:
                        current_video_scene_kind = "auto"
                    selected_video_scene_kind = st.selectbox(
                        "Generated Clip Style",
                        options=list(VIDEO_SCENE_KIND_LABELS.keys()),
                        index=list(VIDEO_SCENE_KIND_LABELS.keys()).index(current_video_scene_kind),
                        format_func=lambda value: VIDEO_SCENE_KIND_LABELS[value],
                        key=f"video_scene_kind_{scene_uid}",
                        help="Auto lets Cathode decide from the brief plus clip-audio setting. Cinematic keeps the motion lane. Speaking prefers the talking-avatar lane.",
                    )
                    normalized_video_scene_kind = None if selected_video_scene_kind == "auto" else selected_video_scene_kind
                    if normalized_video_scene_kind != scene.get("video_scene_kind"):
                        scene["video_scene_kind"] = normalized_video_scene_kind
                        save_plan(project_dir, plan)
                        st.rerun()

                    if video_provider == "replicate":
                        route_preview = _replicate_video_route_summary(scene)
                        st.caption(
                            f"Resolved model: `{route_preview['model']}` ({route_preview['reason']})."
                        )
                    uploaded_video = st.file_uploader(
                        "Upload / Replace Video Clip",
                        type=["mp4", "mov", "m4v", "webm", "mkv"],
                        key=f"upload_video_{scene_uid}",
                        help="Upload the exact footage for this scene. The renderer will trim it, speed it up if requested, and sync it to narration timing.",
                    )
                    if uploaded_video is not None:
                        if st.button("Use Uploaded Video Clip", key=f"use_upload_video_{scene_uid}"):
                            try:
                                ext = Path(uploaded_video.name).suffix.lower() or ".mp4"
                                upload_path = project_dir / "clips" / f"scene_{scene_id:03d}_upload{ext}"
                                upload_path.parent.mkdir(parents=True, exist_ok=True)
                                upload_path.write_bytes(uploaded_video.getvalue())
                                scene["video_path"] = str(upload_path)
                                scene["video_audio_source"] = "narration"
                                save_plan(project_dir, plan)
                                st.rerun()
                            except Exception as e:
                                st.error(f"Upload failed: {e}")

                    if st.button(
                        "Regenerate Video Clip" if _scene_has_video(scene) else "Generate Video Clip",
                        key=f"gen_video_{scene_uid}",
                        disabled=not video_generation_enabled,
                        type="primary" if not _scene_has_video(scene) else "secondary",
                    ):
                        with st.spinner("Generating video clip..."):
                            try:
                                path = generate_scene_video(
                                    scene,
                                    project_dir,
                                    brief=brief,
                                    provider=video_provider,
                                    model=video_generation_model,
                                    model_selection_mode=video_model_selection_mode,
                                    quality_mode=video_quality_mode,
                                    generate_audio=video_generate_audio,
                                    image_provider=image_provider,
                                    image_model=image_generation_model,
                                    tts_kwargs=tts_kwargs,
                                )
                                scene["video_path"] = str(path)
                                scene["video_audio_source"] = (
                                    "clip" if video_provider == "replicate" and video_generate_audio else "narration"
                                )
                                save_plan(project_dir, plan)
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error: {e}")

                    if video_generation_enabled:
                        if video_provider == "local":
                            st.caption(
                                "Local video generation uses the clip notes plus scene narration context. Generate audio first if you want exact duration matching."
                            )
                        else:
                            st.caption(
                                "Cloud video generation creates a full scene clip from your shot direction. Automatic mode switches between cinematic and speaking models for you. Use Scene Audio Source to choose whether render follows the clip's audio or a separate narration track."
                            )
                    else:
                        st.caption(
                            "Video generation is set to upload-only mode. Switch the sidebar Video Generation dropdown to a configured generation backend to create clips here."
                        )

                    audio_source_options = {
                        "narration": "Narration track",
                        "clip": "Clip audio",
                    }
                    current_audio_source = str(scene.get("video_audio_source") or "narration")
                    if current_audio_source not in audio_source_options:
                        current_audio_source = "narration"
                    selected_audio_source = st.selectbox(
                        "Scene Audio Source",
                        options=list(audio_source_options.keys()),
                        index=list(audio_source_options.keys()).index(current_audio_source),
                        format_func=lambda value: audio_source_options[value],
                        key=f"video_audio_source_{scene_uid}",
                        help="Narration uses the scene audio track. Clip audio uses the video's embedded sound during preview and final render.",
                    )
                    if selected_audio_source != current_audio_source:
                        scene["video_audio_source"] = selected_audio_source
                        save_plan(project_dir, plan)
                        st.rerun()

                    if _scene_has_video(scene):
                        st.video(scene["video_path"])
                    else:
                        st.info("No video clip generated or uploaded yet.")

                    source_duration = (
                        get_media_duration(scene["video_path"]) if _scene_has_video(scene) else None
                    )
                    clip_cols = st.columns(2)
                    with clip_cols[0]:
                        clip_start = st.number_input(
                            "Clip Start (seconds)",
                            min_value=0.0,
                            value=float(scene.get("video_trim_start") or 0.0),
                            step=0.25,
                            key=f"video_trim_start_{scene_uid}",
                            help="Start time inside the uploaded clip before playback-speed adjustment.",
                        )
                    with clip_cols[1]:
                        clip_speed = st.number_input(
                            "Playback Speed",
                            min_value=0.25,
                            max_value=4.0,
                            value=float(scene.get("video_playback_speed") or 1.0),
                            step=0.05,
                            key=f"video_speed_{scene_uid}",
                            help="Values above 1.0 speed the clip up. The renderer trims after speed changes so the final segment matches narration.",
                        )

                    if clip_start != float(scene.get("video_trim_start") or 0.0):
                        scene["video_trim_start"] = float(clip_start)
                        save_plan(project_dir, plan)
                    if clip_speed != float(scene.get("video_playback_speed") or 1.0):
                        scene["video_playback_speed"] = float(clip_speed)
                        save_plan(project_dir, plan)

                    use_to_end_default = scene.get("video_trim_end") in (None, "")
                    use_to_end = st.checkbox(
                        "Use clip until source ends",
                        value=use_to_end_default,
                        key=f"video_use_to_end_{scene_uid}",
                        help="Leave enabled to use everything from Clip Start to the end of the uploaded clip.",
                    )
                    if use_to_end:
                        if scene.get("video_trim_end") is not None:
                            scene["video_trim_end"] = None
                            save_plan(project_dir, plan)
                    else:
                        end_fallback = (
                            float(scene.get("video_trim_end"))
                            if scene.get("video_trim_end") not in (None, "")
                            else max(float(scene.get("video_trim_start") or 0.0) + 1.0, 1.0)
                        )
                        clip_end = st.number_input(
                            "Clip End (seconds)",
                            min_value=0.0,
                            value=end_fallback,
                            step=0.25,
                            key=f"video_trim_end_{scene_uid}",
                            help="End time inside the uploaded clip before playback-speed adjustment.",
                        )
                        if clip_end != float(scene.get("video_trim_end") or end_fallback):
                            scene["video_trim_end"] = float(clip_end)
                            save_plan(project_dir, plan)

                    hold_last_frame = st.checkbox(
                        "Freeze last frame if narration is longer",
                        value=bool(scene.get("video_hold_last_frame", True)),
                        key=f"video_hold_last_frame_{scene_uid}",
                        help="If narration outlasts the usable clip, hold on the final frame instead of failing render.",
                    )
                    if hold_last_frame != bool(scene.get("video_hold_last_frame", True)):
                        scene["video_hold_last_frame"] = hold_last_frame
                        save_plan(project_dir, plan)

                    uses_clip_audio = scene_uses_clip_audio(scene)
                    narration_duration = (
                        get_media_duration(scene["audio_path"])
                        if scene.get("audio_path") and Path(scene["audio_path"]).exists()
                        else None
                    )
                    audio_duration = None if uses_clip_audio else narration_duration
                    timing = get_video_scene_timing(
                        scene,
                        source_duration=source_duration,
                        audio_duration=audio_duration,
                    )
                    if source_duration is not None:
                        st.caption(f"Source clip duration: {source_duration:.1f}s")
                    if timing["effective_duration"] is not None:
                        st.caption(
                            f"Usable clip after trim/speed: {float(timing['effective_duration']):.1f}s"
                        )
                    if uses_clip_audio:
                        if _scene_has_video(scene):
                            if media_has_audio_stream(scene["video_path"]):
                                st.caption("Render will use the clip's embedded audio for this scene.")
                            else:
                                st.warning("This clip does not currently have an embedded audio track. Switch Scene Audio Source to narration or regenerate the clip with audio.")
                    elif audio_duration is not None:
                        st.caption(f"Narration duration: {audio_duration:.1f}s")
                        freeze_duration = float(timing["freeze_duration"] or 0.0)
                        if freeze_duration > 5.0:
                            st.warning(
                                f"Narration is {freeze_duration:.1f}s longer than the clip. Render will freeze the last frame for a noticeable stretch."
                            )
                        elif freeze_duration > 0.05:
                            st.info(
                                f"Narration is {freeze_duration:.1f}s longer than the clip. Render will hold the final frame to stay in sync."
                            )
                        elif timing["effective_duration"] is not None and float(timing["effective_duration"]) > audio_duration + 0.05:
                            st.info("The clip is longer than the narration. Render will trim the clip to the narration length.")

                    if _scene_has_video(scene) and audio_duration is not None:
                        if st.button("Fit Clip Length to Narration", key=f"fit_clip_to_audio_{scene_uid}"):
                            available_duration = float(source_duration or 0.0)
                            target_end = float(scene.get("video_trim_start") or 0.0) + (
                                float(audio_duration) * float(scene.get("video_playback_speed") or 1.0)
                            )
                            if available_duration and target_end <= available_duration + 0.05:
                                scene["video_trim_end"] = round(target_end, 3)
                                save_plan(project_dir, plan)
                                st.rerun()
                            else:
                                st.warning(
                                    "There is not enough source footage after the chosen start time to fully cover the narration. Upload a longer clip, move the start earlier, or keep last-frame hold enabled."
                                )

                st.subheader("Audio")
                if scene.get("scene_type") == "video" and scene_uses_clip_audio(scene):
                    st.caption(
                        "This scene is currently set to use the clip's embedded audio during render. Generate narration only if you want to switch the scene back to a separate audio track."
                    )
                else:
                    st.caption(
                        "Narration drives final timing. For video scenes using narration audio, the clip is trimmed or held against this track."
                    )
                speaker_name = st.text_input(
                    "Speaker / Character (optional)",
                    value=str(scene.get("speaker_name") or ""),
                    key=f"speaker_name_{scene_uid}",
                    help="Useful for documentaries with a narrator plus interview recreations or other characters.",
                )
                if speaker_name != str(scene.get("speaker_name") or ""):
                    scene["speaker_name"] = speaker_name.strip()
                    save_plan(project_dir, plan)

                override_enabled = st.checkbox(
                    "Override project narrator for this scene",
                    value=bool(scene.get("tts_override_enabled")),
                    key=f"tts_override_enabled_{scene_uid}",
                    help="Use a different provider or voice for this scene only.",
                )
                if override_enabled != bool(scene.get("tts_override_enabled")):
                    scene["tts_override_enabled"] = bool(override_enabled)
                    save_plan(project_dir, plan)

                if override_enabled:
                    scene_tts_providers = _available_tts_providers(check_api_keys())
                    scene_provider_keys = list(scene_tts_providers.keys())
                    default_scene_provider = str(scene.get("tts_provider") or st.session_state.tts_provider)
                    if default_scene_provider not in scene_provider_keys:
                        default_scene_provider = scene_provider_keys[0]
                    selected_scene_provider = st.selectbox(
                        "Scene TTS Provider",
                        options=scene_provider_keys,
                        index=scene_provider_keys.index(default_scene_provider),
                        format_func=lambda p: scene_tts_providers[p],
                        key=f"scene_tts_provider_{scene_uid}",
                    )
                    if selected_scene_provider != str(scene.get("tts_provider") or ""):
                        scene["tts_provider"] = selected_scene_provider
                        save_plan(project_dir, plan)

                    if selected_scene_provider == "kokoro":
                        voice_options = list(KOKORO_VOICES.keys())
                        default_voice = str(scene.get("tts_voice") or st.session_state.tts_voice)
                        if default_voice not in voice_options:
                            default_voice = voice_options[0]
                        selected_scene_voice = st.selectbox(
                            "Scene Voice",
                            options=voice_options,
                            index=voice_options.index(default_voice),
                            format_func=lambda v: f"{v} - {KOKORO_VOICES[v]}",
                            key=f"scene_kokoro_voice_{scene_uid}",
                        )
                    elif selected_scene_provider == "elevenlabs":
                        selected_scene_voice = st.text_input(
                            "Scene Voice / Voice ID",
                            value=str(scene.get("tts_voice") or st.session_state.tts_elevenlabs_voice),
                            key=f"scene_elevenlabs_voice_{scene_uid}",
                            help="Use a curated name like Bella or a raw ElevenLabs voice ID from your account.",
                        )
                    else:
                        selected_scene_voice = st.text_input(
                            "Scene Voice",
                            value=str(scene.get("tts_voice") or ""),
                            key=f"scene_generic_voice_{scene_uid}",
                        )
                    if selected_scene_voice != str(scene.get("tts_voice") or ""):
                        scene["tts_voice"] = str(selected_scene_voice).strip()
                        save_plan(project_dir, plan)

                    scene_speed_default = (
                        float(scene.get("tts_speed"))
                        if scene.get("tts_speed") is not None
                        else (
                            float(st.session_state.tts_elevenlabs_speed)
                            if selected_scene_provider == "elevenlabs"
                            else float(st.session_state.tts_speed)
                        )
                    )
                    selected_scene_speed = st.slider(
                        "Scene Voice Speed",
                        min_value=0.7,
                        max_value=1.4,
                        value=float(scene_speed_default),
                        step=0.05,
                        key=f"scene_tts_speed_{scene_uid}",
                    )
                    if float(selected_scene_speed) != float(scene.get("tts_speed") or scene_speed_default):
                        scene["tts_speed"] = float(selected_scene_speed)
                        save_plan(project_dir, plan)

                if scene.get("audio_path") and Path(scene["audio_path"]).exists():
                    st.audio(scene["audio_path"])
                    if st.button("Regenerate Audio", key=f"regen_audio_{scene_uid}"):
                        with st.spinner("Generating audio..."):
                            try:
                                path = generate_scene_audio(scene, project_dir, **_tts_kwargs_from_state())
                                scene["audio_path"] = str(path)
                                save_plan(project_dir, plan)
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error: {e}")
                else:
                    st.info("No audio generated yet.")
                    if st.button("Generate Audio", key=f"gen_audio_{scene_uid}", type="primary"):
                        with st.spinner("Generating audio..."):
                            try:
                                path = generate_scene_audio(scene, project_dir, **_tts_kwargs_from_state())
                                scene["audio_path"] = str(path)
                                save_plan(project_dir, plan)
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error: {e}")

                has_visual = _scene_has_primary_visual(scene)
                has_audio = _scene_has_renderable_audio(scene)
                if has_visual and has_audio:
                    st.divider()
                    st.subheader("Preview")
                    existing_preview = scene.get("preview_path")
                    if existing_preview and Path(existing_preview).exists():
                        st.video(existing_preview)
                    if st.button(
                        "Generate Preview" if not existing_preview else "Regenerate Preview",
                        key=f"preview_{scene_uid}",
                    ):
                        with st.spinner("Rendering preview..."):
                            try:
                                preview_path = preview_scene(
                                    scene,
                                    project_dir,
                                    render_profile=plan.get("meta", {}).get("render_profile"),
                                )
                                if preview_path:
                                    scene["preview_path"] = str(preview_path)
                                    save_plan(project_dir, plan)
                                    st.rerun()
                            except Exception as e:
                                st.error(f"Error: {e}")

    st.divider()
    st.subheader("Batch Generation")
    st.caption(
        "Image batch actions skip video scenes automatically. Video batch actions only run for video scenes. Audio batch actions still run for every scene."
    )

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if st.button("Generate Missing Images", key="batch_gen_images", disabled=not image_generation_enabled):
            result = generate_project_assets_service(
                project_dir,
                generate_images=True,
                generate_videos=False,
                generate_audio=False,
                regenerate_images=False,
            )
            st.session_state.plan = load_plan(project_dir)
            failed_scenes = result.get("image_failures", [])
            generated = int(result.get("images_generated") or 0)
            skipped = int(result.get("images_skipped") or 0)
            if failed_scenes:
                st.error(
                    f"Images complete: generated {generated}, skipped {skipped}, failed {len(failed_scenes)}."
                )
            else:
                st.success(f"Images complete: generated {generated}, skipped {skipped}.")
        if not image_generation_enabled:
            st.caption("Batch image generation is disabled in local/manual image mode.")

    with col2:
        a, b = st.columns(2)
        gen_missing_video = a.button(
            "Generate Missing Video Clips",
            key="batch_gen_videos",
            disabled=not video_generation_enabled,
        )
        regen_all_video = b.button(
            "Regenerate All Video Clips",
            key="batch_regen_videos",
            disabled=not video_generation_enabled,
        )
        if gen_missing_video or regen_all_video:
            current_plan = backfill_plan(plan)
            current_plan.setdefault("meta", {})["video_profile"] = _video_profile_from_state()
            save_plan(project_dir, current_plan)
            result = generate_project_assets_service(
                project_dir,
                generate_images=False,
                generate_videos=True,
                generate_audio=False,
                regenerate_videos=regen_all_video,
            )
            st.session_state.plan = load_plan(project_dir)
            failed_scenes = result.get("video_failures", [])
            generated = int(result.get("videos_generated") or 0)
            skipped = int(result.get("videos_skipped") or 0)
            if failed_scenes:
                st.error(
                    f"Video clips complete: generated {generated}, skipped {skipped}, failed {len(failed_scenes)}."
                )
            else:
                st.success(f"Video clips complete: generated {generated}, skipped {skipped}.")
        if not video_generation_enabled:
            st.caption("Batch video generation is disabled in upload-only video mode.")

    with col3:
        a, b = st.columns(2)
        gen_missing = a.button("Generate Missing Audio", key="batch_gen_audio")
        regen_all = b.button("Regenerate All Audio", key="batch_regen_audio")
        if gen_missing or regen_all:
            current_plan = backfill_plan(plan)
            current_plan.setdefault("meta", {})["tts_profile"] = _tts_profile_from_state()
            save_plan(project_dir, current_plan)
            result = generate_project_assets_service(
                project_dir,
                generate_images=False,
                generate_videos=False,
                generate_audio=True,
                regenerate_audio=regen_all,
            )
            st.session_state.plan = load_plan(project_dir)
            failed_scenes = result.get("audio_failures", [])
            generated = int(result.get("audio_generated") or 0)
            skipped = int(result.get("audio_skipped") or 0)
            if failed_scenes:
                st.error(
                    f"Audio complete: generated {generated}, skipped {skipped}, failed {len(failed_scenes)}."
                )
            else:
                st.success(f"Audio complete: generated {generated}, skipped {skipped}.")

    with col4:
        if st.button("Go to Render ->", type="primary"):
            st.session_state.step = 3
            st.rerun()

        all_visuals = all(_scene_has_primary_visual(scene) for scene in scenes)
        all_audio = all(_scene_has_renderable_audio(scene) for scene in scenes)
        if not all_visuals:
            st.caption("Missing image or video clip")
        if not all_audio:
            st.caption("Missing audio")

    st.divider()
    st.subheader("Regenerate Everything")
    st.caption("Regenerates all AI images and all audio in parallel. Local video clips have their own batch actions above.")

    if st.button("Regenerate Everything (Images + Audio)", type="primary", key="regen_everything_parallel"):
        tts_kwargs = _tts_kwargs_from_state()
        total = len(scenes)
        if total == 0:
            st.warning("No scenes found.")
            return

        img_col, aud_col = st.columns(2)
        with img_col:
            st.markdown("**Images**")
            img_status = st.empty()
            img_progress = st.progress(0.0)
        with aud_col:
            st.markdown("**Audio**")
            aud_status = st.empty()
            aud_progress = st.progress(0.0)

        overall = st.empty()
        q: queue.Queue = queue.Queue()
        lock = threading.Lock()

        img_failed: list[tuple[int, str]] = []
        aud_failed: list[tuple[int, str]] = []

        def _regen_images() -> None:
            try:
                for i, scene in enumerate(scenes):
                    sid = int(scene.get("id", i))
                    if _scene_type(scene) != "image":
                        q.put(("image_skip", i + 1, total, sid))
                        continue
                    try:
                        path = generate_scene_image(scene, project_dir, brief=brief)
                        with lock:
                            scene["image_path"] = str(path)
                            save_plan(project_dir, plan)
                        q.put(("image_ok", i + 1, total, sid))
                    except Exception as e:
                        q.put(("image_err", i + 1, total, sid, str(e)))
            finally:
                q.put(("image_done",))

        def _regen_audio() -> None:
            try:
                for i, scene in enumerate(scenes):
                    sid = int(scene.get("id", i))
                    try:
                        path = generate_scene_audio(scene, project_dir, **tts_kwargs)
                        with lock:
                            scene["audio_path"] = str(path)
                            save_plan(project_dir, plan)
                        q.put(("audio_ok", i + 1, total, sid))
                    except Exception as e:
                        q.put(("audio_err", i + 1, total, sid, str(e)))
            finally:
                q.put(("audio_done",))

        t_img = threading.Thread(target=_regen_images, daemon=True)
        t_aud = threading.Thread(target=_regen_audio, daemon=True)
        t_img.start()
        t_aud.start()

        overall.info("Running... (images + audio in parallel)")
        img_finished = False
        aud_finished = False
        while not (img_finished and aud_finished):
            try:
                evt = q.get(timeout=0.2)
            except Exception:
                evt = None
            if not evt:
                continue
            kind = evt[0]
            if kind == "image_ok":
                _, n, tot, sid = evt
                img_progress.progress(n / tot)
                img_status.text(f"Scene {sid}: {n}/{tot}")
            elif kind == "image_skip":
                _, n, tot, sid = evt
                img_progress.progress(n / tot)
                img_status.text(f"Scene {sid}: {n}/{tot} (video scene skipped)")
            elif kind == "image_err":
                _, n, tot, sid, msg = evt
                img_progress.progress(n / tot)
                img_status.text(f"Scene {sid}: {n}/{tot} (error)")
                img_failed.append((sid, msg))
            elif kind == "image_done":
                img_finished = True
                img_progress.progress(1.0)
                img_status.text("Done.")
            elif kind == "audio_ok":
                _, n, tot, sid = evt
                aud_progress.progress(n / tot)
                aud_status.text(f"Scene {sid}: {n}/{tot}")
            elif kind == "audio_err":
                _, n, tot, sid, msg = evt
                aud_progress.progress(n / tot)
                aud_status.text(f"Scene {sid}: {n}/{tot} (error)")
                aud_failed.append((sid, msg))
            elif kind == "audio_done":
                aud_finished = True
                aud_progress.progress(1.0)
                aud_status.text("Done.")

        t_img.join(timeout=0.1)
        t_aud.join(timeout=0.1)

        if img_failed or aud_failed:
            overall.error(
                f"Complete with errors. Image failures: {len(img_failed)}. Audio failures: {len(aud_failed)}."
            )
        else:
            overall.success("Regeneration complete.")


def render_step_3():
    """Step 3: Render final video and download."""
    st.header("Step 3: Render Video")

    plan = st.session_state.plan
    project_dir = st.session_state.project_dir
    scenes = plan["scenes"]
    render_profile = plan.get("meta", {}).get("render_profile", {})

    if st.button("<- Back to Scenes"):
        st.session_state.step = 2
        st.rerun()

    st.divider()
    duration = get_video_duration(scenes)
    st.write(f"Scenes: {len(scenes)}")
    st.write(f"Estimated Duration: {duration:.1f} seconds ({duration/60:.1f} minutes)")
    st.caption(
        "Render uses narration length as the timing source of truth. Image scenes hold for the narration duration; video scenes trim to narration length or freeze on the last frame if they run short."
    )
    st.divider()

    st.subheader("Render Settings")
    col1, col2 = st.columns(2)
    with col1:
        fps = st.selectbox(
            "Frame Rate",
            [24, 30, 60],
            index=[24, 30, 60].index(int(render_profile.get("fps", 24)))
            if int(render_profile.get("fps", 24)) in [24, 30, 60]
            else 0,
            key="render_fps",
        )
    with col2:
        output_name = st.text_input("Output Filename", "final_video.mp4", key="render_output_name")

    video_path = project_dir / output_name
    if st.button("Render Video", type="primary"):
        with st.spinner("Rendering video..."):
            try:
                plan["meta"]["render_profile"] = {**render_profile, "fps": int(fps)}
                save_plan(project_dir, plan)
                render_result = render_project_service(
                    project_dir,
                    output_filename=output_name,
                    fps=int(fps),
                )
                if render_result.get("status") == "succeeded":
                    st.success("Video rendered successfully.")
                    st.session_state.plan = load_plan(project_dir)
                    st.rerun()
                else:
                    st.warning(str(render_result.get("suggestion") or "Render completed partially."))
            except Exception as e:
                st.error(f"Error rendering video: {e}")

    if video_path.exists():
        st.divider()
        st.subheader("Download")
        st.video(str(video_path))
        with open(video_path, "rb") as f:
            st.download_button(
                "Download Video",
                data=f,
                file_name=output_name,
                mime="video/mp4",
                type="primary",
            )


def render_batch_queue():
    """Render the batch processing queue tab."""
    st.header("Batch Processing Queue")
    st.info("Queue multiple projects for unattended rebuild and asset generation.")

    available_projects = get_existing_projects()
    if not available_projects:
        st.warning("No existing projects found.")
        return

    selected = st.multiselect(
        "Select projects to process",
        available_projects,
        help="Choose projects to process in sequence.",
    )
    if not selected:
        st.caption("Select at least one project.")
        return

    st.divider()
    st.subheader("Processing Options")
    col1, col2 = st.columns(2)
    with col1:
        rebuild_storyboards = st.checkbox(
            "Rebuild storyboard from plan metadata (meta.brief or legacy input_text)",
            value=False,
        )
        generate_images = st.checkbox("Generate missing images", value=True)
        generate_videos = st.checkbox("Generate missing video clips", value=True)
        generate_audio = st.checkbox("Generate missing audio", value=True)
    with col2:
        regenerate_audio = st.checkbox("Regenerate all audio", value=False)
        assemble_videos = st.checkbox("Assemble final videos", value=True)
        delay_between = st.slider("Delay between projects (sec)", min_value=2, max_value=60, value=10)

    if st.button("Start Batch Processing", type="primary"):
        batch_progress = st.progress(0.0)
        batch_status = st.empty()
        results = []

        for i, project_name in enumerate(selected):
            batch_status.text(f"Processing {project_name} ({i + 1}/{len(selected)})")
            project_dir = PROJECTS_DIR / project_name
            project_result = {
                "name": project_name,
                "rebuild": False,
                "images": 0,
                "clips": 0,
                "audio": 0,
                "video": False,
                "errors": [],
            }

            if not load_plan(project_dir):
                project_result["errors"].append("Could not load plan.json")
                results.append(project_result)
                continue

            try:
                shared_result = process_existing_project_service(
                    project_dir,
                    rebuild_storyboard=rebuild_storyboards,
                    generate_images=generate_images,
                    generate_videos=generate_videos,
                    generate_audio=generate_audio,
                    regenerate_audio=regenerate_audio,
                    assemble_final=assemble_videos,
                )
                project_result["rebuild"] = rebuild_storyboards
                assets = shared_result.get("assets") or {}
                render = shared_result.get("render") or {}
                project_result["images"] = int(assets.get("images_generated") or 0)
                project_result["clips"] = int(assets.get("videos_generated") or 0)
                project_result["audio"] = int(assets.get("audio_generated") or 0)
                project_result["video"] = render.get("status") == "succeeded"
                for failure in assets.get("image_failures", []):
                    project_result["errors"].append(
                        f"Image scene {failure.get('scene_id')}: {failure.get('error')}"
                    )
                for failure in assets.get("video_failures", []):
                    project_result["errors"].append(
                        f"Video scene {failure.get('scene_id')}: {failure.get('error')}"
                    )
                for failure in assets.get("audio_failures", []):
                    project_result["errors"].append(
                        f"Audio scene {failure.get('scene_id')}: {failure.get('error')}"
                    )
                if render.get("status") == "partial_success":
                    project_result["errors"].append(str(render.get("suggestion") or "Render completed partially."))
                elif render.get("status") == "error":
                    project_result["errors"].append(str(render.get("suggestion") or "Video assembly failed."))
            except Exception as e:
                project_result["errors"].append(f"Batch processing failed: {e}")

            results.append(project_result)
            batch_progress.progress((i + 1) / len(selected))

            if i < len(selected) - 1:
                batch_status.text(f"Waiting {delay_between}s before next project...")
                time.sleep(delay_between)

        batch_status.empty()
        st.success("Batch processing complete.")
        st.subheader("Results Summary")
        for r in results:
            status_icon = "FAIL" if r["errors"] else "OK"
            st.write(
                f"{status_icon} {r['name']}: rebuild={r['rebuild']} "
                f"images={r['images']} clips={r['clips']} audio={r['audio']} video={r['video']}"
            )
            if r["errors"]:
                for err in r["errors"]:
                    st.caption(f"- {err}")


def main():
    """Main Streamlit app."""
    st.set_page_config(
        page_title=PRODUCT_NAME,
        page_icon="🎬",
        layout="wide",
    )

    init_session_state()
    render_sidebar()

    tab1, tab2 = st.tabs(["Project Workflow", "Batch Queue"])
    with tab1:
        if st.session_state.step == 1:
            render_step_1()
        elif st.session_state.step == 2:
            render_step_2()
        elif st.session_state.step == 3:
            render_step_3()
    with tab2:
        render_batch_queue()


if __name__ == "__main__":
    main()
