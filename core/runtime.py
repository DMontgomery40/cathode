"""Runtime configuration and provider discovery helpers."""

from __future__ import annotations

import importlib.util
import os
import platform
import re
import shutil
from pathlib import Path

from .project_schema import default_image_profile, default_tts_profile, default_video_profile

REPO_ROOT = Path(__file__).resolve().parent.parent
PROJECTS_DIR = REPO_ROOT / "projects"
PROJECTS_DIR.mkdir(exist_ok=True)
_KOKORO_VOICE_PATTERN = re.compile(r"^[ab][fm]_[a-z0-9]+$")
_OPENAI_TTS_VOICES = {"alloy", "ash", "ballad", "coral", "echo", "fable", "nova", "onyx", "sage", "shimmer"}
DEFAULT_REPLICATE_VIDEO_MODEL = "kwaivgi/kling-v3-video"


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
    if keys.get("elevenlabs") and keys.get("replicate"):
        providers["elevenlabs"] = "ElevenLabs (API / Replicate fallback)"
    elif keys.get("elevenlabs"):
        providers["elevenlabs"] = "ElevenLabs (Cloud)"
    elif keys.get("replicate"):
        providers["elevenlabs"] = "ElevenLabs (Replicate)"
    if keys.get("openai"):
        providers["openai"] = "OpenAI TTS (Cloud)"
    return providers


def available_image_generation_providers(keys: dict[str, bool] | None = None) -> list[str]:
    """Return supported image-generation providers in UI preference order."""
    keys = keys or check_api_keys()
    providers = ["manual"]
    if local_image_generation_available():
        providers.insert(0, "local")
    if keys.get("replicate"):
        providers.insert(0, "replicate")
    return providers


def _module_available(module_name: str) -> bool:
    """Return whether a Python module can be imported in the current environment."""
    return importlib.util.find_spec(module_name) is not None


def _local_image_runtime_preference() -> str | None:
    """Return the configured local image runtime, or None when invalid."""
    value = str(os.getenv("CATHODE_LOCAL_IMAGE_RUNTIME") or "auto").strip().lower() or "auto"
    if value not in {"auto", "torch", "mlx"}:
        return None
    return value


def _is_apple_silicon() -> bool:
    """Return whether the current machine is Apple Silicon."""
    return platform.system() == "Darwin" and platform.machine() == "arm64"


def _mlx_local_image_backend_available() -> bool:
    """Return whether the MLX local image backend is runnable."""
    return _is_apple_silicon() and bool(shutil.which("mflux-generate-qwen"))


def _torch_local_image_backend_available() -> bool:
    """Return whether the torch local image backend is runnable."""
    return all(_module_available(module_name) for module_name in ("torch", "diffusers", "transformers"))


def _local_image_backend_runnable() -> bool:
    """Return whether the configured local image backend can actually run here."""
    runtime = _local_image_runtime_preference()
    if runtime is None:
        return False
    if runtime == "torch":
        return _torch_local_image_backend_available()
    if runtime == "mlx":
        return _mlx_local_image_backend_available()
    return _mlx_local_image_backend_available() or _torch_local_image_backend_available()


def _local_image_provider_available_for_model(model_name: str | None) -> bool:
    """Return whether a named local image model can be offered/used here."""
    return bool(str(model_name or "").strip()) and _local_image_backend_runnable()


def local_image_generation_available() -> bool:
    """Return whether a local image backend is configured."""
    return _local_image_provider_available_for_model(default_local_image_generation_model())


def default_local_image_generation_model() -> str:
    """Return the configured local image model label or repo id, if any."""
    return str(os.getenv("CATHODE_LOCAL_IMAGE_MODEL") or "").strip()


def local_video_generation_available() -> bool:
    """Return whether a local video backend is configured."""
    return bool(
        str(os.getenv("CATHODE_LOCAL_VIDEO_COMMAND") or "").strip()
        or str(os.getenv("CATHODE_LOCAL_VIDEO_ENDPOINT") or "").strip()
    )


def default_local_video_generation_model() -> str:
    """Return the configured local video model label or path, if any."""
    return str(os.getenv("CATHODE_LOCAL_VIDEO_MODEL") or "").strip()


def remotion_available() -> bool:
    """Return whether the local frontend workspace has a runnable Remotion toolchain."""
    frontend_dir = REPO_ROOT / "frontend"
    return bool(
        shutil.which("node")
        and (frontend_dir / "node_modules" / "remotion" / "package.json").exists()
        and (frontend_dir / "node_modules" / "@remotion" / "renderer" / "package.json").exists()
        and (frontend_dir / "scripts").exists()
    )


def remotion_capabilities() -> dict[str, bool]:
    """Return the locally available Remotion feature surface for the UI."""
    frontend_dir = REPO_ROOT / "frontend"
    node_modules = frontend_dir / "node_modules"
    has_node = bool(shutil.which("node"))
    return {
        "render_available": remotion_available(),
        "player_available": has_node and (node_modules / "@remotion" / "player" / "package.json").exists(),
        "transitions_available": has_node and (node_modules / "@remotion" / "transitions" / "package.json").exists(),
        "three_available": has_node
        and (node_modules / "three" / "package.json").exists()
        and (node_modules / "@react-three" / "fiber" / "package.json").exists()
        and (node_modules / "@react-three" / "drei" / "package.json").exists(),
    }


def default_replicate_video_generation_model() -> str:
    """Return the default Replicate-hosted video model slug."""
    return DEFAULT_REPLICATE_VIDEO_MODEL


def available_video_generation_providers(keys: dict[str, bool] | None = None) -> list[str]:
    """Return supported video-generation providers in UI preference order."""
    keys = keys or check_api_keys()
    providers = ["manual"]
    if keys.get("replicate"):
        providers.insert(0, "replicate")
    if local_video_generation_available():
        providers.insert(0, "local")
    return providers


def available_render_backends() -> list[str]:
    """Return supported render backends for the current local toolchain."""
    backends = ["ffmpeg"]
    if remotion_available():
        backends.append("remotion")
    return backends


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
    raw_profile = profile if isinstance(profile, dict) else {}
    if raw_profile:
        resolved.update(raw_profile)

    keys = check_api_keys()
    provider = str(resolved.get("provider") or "replicate").strip().lower()
    raw_generation_model = str(raw_profile.get("generation_model") or "").strip()
    local_model = raw_generation_model
    if not local_model or local_model == default_image_profile()["generation_model"]:
        local_model = default_local_image_generation_model()
    if provider == "replicate" and not keys.get("replicate"):
        provider = "manual"
    if provider == "local" and not _local_image_provider_available_for_model(local_model):
        provider = "manual"
    if provider not in {"replicate", "local", "manual"}:
        provider = "manual"
    resolved["provider"] = provider
    if provider == "local":
        resolved["generation_model"] = local_model
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
    voice = str(resolved.get("voice") or "").strip()
    if provider == "kokoro":
        resolved["voice"] = voice if _KOKORO_VOICE_PATTERN.match(voice) else str(default_tts_profile()["voice"])
    elif provider == "elevenlabs":
        resolved["voice"] = "Bella" if not voice or _KOKORO_VOICE_PATTERN.match(voice) else voice
    elif provider == "openai":
        resolved["voice"] = voice if voice in _OPENAI_TTS_VOICES else "nova"
    return resolved


def resolve_video_profile(profile: dict | None = None) -> dict:
    """Resolve a persisted video profile against current provider availability."""
    resolved = dict(default_video_profile())
    if isinstance(profile, dict):
        resolved.update(profile)

    keys = check_api_keys()
    provider = str(resolved.get("provider") or "manual").strip().lower()
    if provider == "local" and not local_video_generation_available():
        provider = "manual"
    if provider == "replicate" and not keys.get("replicate"):
        provider = "manual"
    if provider not in {"manual", "local", "replicate", "agent"}:
        provider = "manual"
    resolved["provider"] = provider
    generation_model = str(resolved.get("generation_model") or "").strip()
    if provider == "local":
        generation_model = generation_model or default_local_video_generation_model()
    elif provider == "replicate":
        generation_model = generation_model or default_replicate_video_generation_model()
    resolved["generation_model"] = generation_model.strip()
    selection_mode = str(resolved.get("model_selection_mode") or "automatic").strip().lower()
    resolved["model_selection_mode"] = selection_mode if selection_mode in {"automatic", "advanced"} else "automatic"
    quality_mode = str(resolved.get("quality_mode") or "standard").strip().lower()
    resolved["quality_mode"] = quality_mode if quality_mode in {"standard", "pro"} else "standard"
    raw_generate_audio = resolved.get("generate_audio")
    resolved["generate_audio"] = True if raw_generate_audio is None else bool(raw_generate_audio)
    return resolved
