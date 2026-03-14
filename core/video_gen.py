"""Video generation adapters for env-driven backends."""

from __future__ import annotations

import base64
import json
import math
import os
import re
import shlex
import shutil
import subprocess
import sys
from contextlib import ExitStack
from pathlib import Path
from typing import Any

import requests
from replicate import Client

from .image_gen import generate_image, generate_image_local
from .rate_limiter import image_limiter
from .runtime import (
    default_local_video_generation_model,
    default_replicate_video_generation_model,
    local_video_generation_available,
)
from .video_assembly import DEFAULT_FPS, TARGET_HEIGHT, TARGET_WIDTH, get_media_duration
from .voice_gen import generate_scene_audio_result

DEFAULT_VIDEO_DURATION_SECONDS = 5.0
DEFAULT_VIDEO_TIMEOUT_SECONDS = 900
MAX_REPLICATE_VIDEO_DURATION_SECONDS = 15
DEFAULT_REPLICATE_SPEAKING_VIDEO_MODEL = "kwaivgi/kling-avatar-v2"


def _log(message: str) -> None:
    print(f"[VIDEO_GEN] {message}", file=sys.stderr, flush=True)


_replicate_client: Client | None = None


def _get_replicate_client() -> Client:
    global _replicate_client
    if _replicate_client is None:
        _replicate_client = Client(timeout=DEFAULT_VIDEO_TIMEOUT_SECONDS)
    return _replicate_client


def _local_video_command() -> str:
    return str(os.getenv("CATHODE_LOCAL_VIDEO_COMMAND") or "").strip()


def _local_video_endpoint() -> str:
    return str(os.getenv("CATHODE_LOCAL_VIDEO_ENDPOINT") or "").strip()


def _local_video_api_key() -> str:
    return str(os.getenv("CATHODE_LOCAL_VIDEO_API_KEY") or "").strip()


def _local_video_timeout_seconds() -> int:
    raw = str(os.getenv("CATHODE_LOCAL_VIDEO_TIMEOUT_SECONDS") or "").strip()
    if not raw:
        return DEFAULT_VIDEO_TIMEOUT_SECONDS
    try:
        value = int(raw)
    except ValueError:
        return DEFAULT_VIDEO_TIMEOUT_SECONDS
    return value if value > 0 else DEFAULT_VIDEO_TIMEOUT_SECONDS


def _truncate(text: str, max_chars: int = 1800) -> str:
    value = str(text or "").strip()
    if len(value) <= max_chars:
        return value
    return value[: max_chars - 3].rstrip() + "..."


def build_scene_video_prompt(
    scene: dict[str, Any],
    brief: dict[str, Any] | None = None,
    *,
    route_kind: str | None = None,
) -> str:
    """Build a grounded generation prompt for a local video backend."""
    lines: list[str] = []
    resolved_route_kind = str(route_kind or scene.get("video_scene_kind") or "").strip().lower()

    if resolved_route_kind == "speaking":
        speaker_name = str(scene.get("speaker_name") or "").strip()
        if speaker_name:
            lines.append(f"Speaking subject: {speaker_name}")
        lines.append(
            "Create a photoreal speaking-to-camera clip with one visible spokesperson delivering the message naturally."
        )
        lines.append(
            "Favor a medium or medium-close framing, realistic eye-line, subtle hand gestures, natural breathing, and believable office, studio, retail, or local-business staging."
        )

    visual_prompt = str(scene.get("visual_prompt") or "").strip()
    if visual_prompt:
        lines.append(visual_prompt)

    narration = str(scene.get("narration") or "").strip()
    if narration:
        lines.append(f"Narration context: {_truncate(narration, max_chars=600)}")

    on_screen_text = scene.get("on_screen_text")
    if isinstance(on_screen_text, list):
        words = [str(item).strip() for item in on_screen_text if str(item).strip()]
        if words:
            lines.append("On-screen text guidance: " + " | ".join(words))

    if isinstance(brief, dict):
        visual_style = str(brief.get("visual_style") or "").strip()
        tone = str(brief.get("tone") or "").strip()
        audience = str(brief.get("audience") or "").strip()
        style_reference_summary = _truncate(str(brief.get("style_reference_summary") or "").strip(), max_chars=500)

        if visual_style:
            lines.append(f"Visual style: {visual_style}")
        if tone:
            lines.append(f"Tone: {tone}")
        if audience:
            lines.append(f"Audience: {audience}")
        if style_reference_summary:
            lines.append(f"Style reference guidance: {style_reference_summary}")

    if not lines:
        title = str(scene.get("title") or "Storyboard scene").strip()
        lines.append(title)

    lines.append("Output: a 16:9 video clip suitable for direct use in a narrated explainer edit.")
    return "\n".join(lines)


def estimate_scene_duration_seconds(
    scene: dict[str, Any],
    *,
    audio_path: str | Path | None = None,
) -> float:
    """Estimate scene duration when no narration audio has been generated yet."""
    if audio_path:
        actual = get_media_duration(audio_path)
        if actual and actual > 0:
            return float(actual)

    words = re.findall(r"\w+", str(scene.get("narration") or ""))
    if not words:
        return DEFAULT_VIDEO_DURATION_SECONDS

    estimated = len(words) / 2.8
    return max(2.0, min(float(estimated), 20.0))


def _response_path_candidates(payload: Any) -> list[str]:
    if isinstance(payload, str):
        return [payload]
    if not isinstance(payload, dict):
        return []
    values = []
    for key in ("output_path", "video_path", "path", "file_path"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            values.append(value.strip())
    return values


def _write_base64_video(data: str, output_path: Path) -> Path:
    raw = data.split(",", 1)[1] if "," in data and data.lstrip().startswith("data:") else data
    output_path.write_bytes(base64.b64decode(raw))
    return output_path


def _download_video(url: str, output_path: Path, *, timeout_seconds: int) -> Path:
    response = requests.get(url, timeout=(10, timeout_seconds))
    response.raise_for_status()
    output_path.write_bytes(response.content)
    return output_path


def _materialize_response(payload: Any, output_path: Path, *, timeout_seconds: int) -> Path:
    for candidate in _response_path_candidates(payload):
        source = Path(candidate)
        if source.exists():
            if source.resolve() != output_path.resolve():
                shutil.copy2(source, output_path)
            return output_path

    if isinstance(payload, dict):
        for key in ("b64_json", "base64", "video_base64"):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return _write_base64_video(value.strip(), output_path)
        url = payload.get("url")
        if isinstance(url, str) and url.strip():
            return _download_video(url.strip(), output_path, timeout_seconds=timeout_seconds)

    if isinstance(payload, str):
        source = Path(payload)
        if source.exists():
            if source.resolve() != output_path.resolve():
                shutil.copy2(source, output_path)
            return output_path

    raise ValueError(
        "Local video backend did not produce a usable clip. "
        "Write the file to CATHODE_VIDEO_OUTPUT_PATH or return JSON with output_path, url, or b64_json."
    )


def _replicate_duration_seconds(value: float) -> int:
    rounded = int(math.ceil(max(float(value), 1.0)))
    return max(1, min(rounded, MAX_REPLICATE_VIDEO_DURATION_SECONDS))


def _replicate_route_kind_for_model(model_slug: str) -> str:
    value = str(model_slug or "").strip().lower()
    if "avatar" in value:
        return "speaking"
    return "cinematic"


def resolve_replicate_video_generation_route(
    scene: dict[str, Any],
    *,
    model: str | None,
    model_selection_mode: str | None,
    generate_audio: bool,
) -> dict[str, str]:
    selection_mode = str(model_selection_mode or "automatic").strip().lower()
    explicit_model = str(model or "").strip()
    scene_kind = str(scene.get("video_scene_kind") or "").strip().lower()

    if selection_mode == "advanced" and explicit_model:
        resolved_model = explicit_model
        route_kind = _replicate_route_kind_for_model(explicit_model)
        reason = "advanced override"
    else:
        auto_prefers_speaking = bool(generate_audio) and scene_kind != "cinematic"
        if auto_prefers_speaking:
            resolved_model = DEFAULT_REPLICATE_SPEAKING_VIDEO_MODEL
            route_kind = "speaking"
            reason = "automatic speaking route"
        else:
            resolved_model = explicit_model or default_replicate_video_generation_model()
            route_kind = "cinematic"
            reason = "automatic cinematic route"

    return {
        "model": resolved_model,
        "route_kind": route_kind,
        "selection_mode": selection_mode if selection_mode in {"automatic", "advanced"} else "automatic",
        "reason": reason,
    }


def _materialize_replicate_output(output: Any, output_path: Path, *, timeout_seconds: int) -> Path:
    if isinstance(output, list) and output:
        return _materialize_replicate_output(output[0], output_path, timeout_seconds=timeout_seconds)
    if hasattr(output, "url"):
        return _download_video(str(output.url), output_path, timeout_seconds=timeout_seconds)
    if isinstance(output, str) and output.strip():
        value = output.strip()
        if value.startswith("http://") or value.startswith("https://"):
            return _download_video(value, output_path, timeout_seconds=timeout_seconds)
        source = Path(value)
        if source.exists():
            if source.resolve() != output_path.resolve():
                shutil.copy2(source, output_path)
            return output_path
    if isinstance(output, dict):
        return _materialize_response(output, output_path, timeout_seconds=timeout_seconds)
    raise ValueError(f"Replicate video generation returned an unsupported output payload: {type(output)!r}")


def _generate_reference_image_for_speaking_scene(
    scene: dict[str, Any],
    *,
    project_dir: Path,
    brief: dict[str, Any] | None,
    provider: str,
    model: str,
) -> Path:
    output_path = project_dir / "images" / f"scene_{int(scene.get('id', 0)):03d}_video_ref.png"
    prompt = build_scene_video_prompt(scene, brief, route_kind="speaking")
    if provider == "local":
        return generate_image_local(prompt, output_path, model=model, brief=brief)
    if provider == "replicate":
        return generate_image(prompt, output_path, model=model, brief=brief)
    raise ValueError(
        "Automatic speaking-video generation needs an image provider that can create a reference portrait."
    )


def _ensure_speaking_reference_image(
    scene: dict[str, Any],
    *,
    project_dir: Path,
    brief: dict[str, Any] | None,
    image_provider: str,
    image_model: str,
) -> tuple[Path, bool]:
    existing_reference = Path(str(scene.get("video_reference_image_path") or "")).expanduser() if scene.get("video_reference_image_path") else None
    if existing_reference and existing_reference.exists():
        return existing_reference, False

    existing_image = Path(str(scene.get("image_path") or "")).expanduser() if scene.get("image_path") else None
    if existing_image and existing_image.exists():
        scene["video_reference_image_path"] = str(existing_image)
        return existing_image, False

    generated = _generate_reference_image_for_speaking_scene(
        scene,
        project_dir=project_dir,
        brief=brief,
        provider=image_provider,
        model=image_model,
    )
    scene["video_reference_image_path"] = str(generated)
    return generated, True


def _ensure_speaking_audio(
    scene: dict[str, Any],
    *,
    project_dir: Path,
    tts_kwargs: dict[str, Any] | None,
) -> dict[str, Any]:
    existing_reference = Path(str(scene.get("video_reference_audio_path") or "")).expanduser() if scene.get("video_reference_audio_path") else None
    if existing_reference and existing_reference.exists():
        return {
            "path": existing_reference,
            "provider": str(tts_kwargs.get("tts_provider") or "kokoro") if isinstance(tts_kwargs, dict) else "kokoro",
            "model": str(tts_kwargs.get("openai_model_id") or tts_kwargs.get("elevenlabs_model_id") or "") if isinstance(tts_kwargs, dict) else "",
            "generated": False,
        }
    existing_audio = Path(str(scene.get("audio_path") or "")).expanduser() if scene.get("audio_path") else None
    if existing_audio and existing_audio.exists():
        scene["video_reference_audio_path"] = str(existing_audio)
        return {
            "path": existing_audio,
            "provider": str(tts_kwargs.get("tts_provider") or "kokoro") if isinstance(tts_kwargs, dict) else "kokoro",
            "model": str(tts_kwargs.get("openai_model_id") or tts_kwargs.get("elevenlabs_model_id") or "") if isinstance(tts_kwargs, dict) else "",
            "generated": False,
        }
    if not isinstance(tts_kwargs, dict) or not tts_kwargs:
        raise ValueError("Automatic speaking-video generation needs TTS settings to create dialogue audio.")
    generated = generate_scene_audio_result(scene, project_dir, **tts_kwargs)
    generated_path = Path(str(generated["path"]))
    scene["video_reference_audio_path"] = str(generated_path)
    return {
        "path": generated_path,
        "provider": str(generated.get("provider") or ""),
        "model": str(generated.get("model") or ""),
        "generated": True,
    }


def _command_env(payload: dict[str, Any]) -> dict[str, str]:
    env = os.environ.copy()
    env.update(
        {
            "CATHODE_VIDEO_PROMPT": str(payload["prompt"]),
            "CATHODE_VIDEO_OUTPUT_PATH": str(payload["output_path"]),
            "CATHODE_VIDEO_DURATION_SECONDS": str(payload["duration_seconds"]),
            "CATHODE_VIDEO_WIDTH": str(payload["width"]),
            "CATHODE_VIDEO_HEIGHT": str(payload["height"]),
            "CATHODE_VIDEO_FPS": str(payload["fps"]),
            "CATHODE_VIDEO_MODEL": str(payload.get("model") or ""),
            "CATHODE_VIDEO_SCENE_ID": str(payload["scene"].get("id", "")),
            "CATHODE_VIDEO_SCENE_TITLE": str(payload["scene"].get("title") or ""),
            "CATHODE_VIDEO_NARRATION": str(payload["scene"].get("narration") or ""),
            "CATHODE_VIDEO_REQUEST_JSON": json.dumps(payload),
        }
    )
    return env


def _run_local_video_command(payload: dict[str, Any], output_path: Path, *, timeout_seconds: int) -> Path:
    command = _local_video_command()
    if not command:
        raise ValueError("CATHODE_LOCAL_VIDEO_COMMAND is not configured.")

    _log(f"Running local video command for scene {payload['scene'].get('id', '?')}")
    completed = subprocess.run(
        shlex.split(command),
        env=_command_env(payload),
        capture_output=True,
        text=True,
        check=True,
        timeout=float(timeout_seconds),
    )

    if output_path.exists():
        return output_path

    stdout = completed.stdout.strip()
    if stdout:
        if stdout.startswith("{"):
            return _materialize_response(json.loads(stdout), output_path, timeout_seconds=timeout_seconds)
        return _materialize_response(stdout, output_path, timeout_seconds=timeout_seconds)

    raise ValueError(
        "Local video command completed without writing a clip. "
        "Write to CATHODE_VIDEO_OUTPUT_PATH or print JSON with output_path, url, or b64_json."
    )


def _request_local_video_endpoint(payload: dict[str, Any], output_path: Path, *, timeout_seconds: int) -> Path:
    endpoint = _local_video_endpoint()
    if not endpoint:
        raise ValueError("CATHODE_LOCAL_VIDEO_ENDPOINT is not configured.")

    headers = {"Content-Type": "application/json"}
    api_key = _local_video_api_key()
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    _log(f"POST {endpoint} for scene {payload['scene'].get('id', '?')}")
    response = requests.post(
        endpoint,
        headers=headers,
        json=payload,
        timeout=(10, timeout_seconds),
    )
    response.raise_for_status()

    content_type = str(response.headers.get("content-type") or "").lower()
    if "video/" in content_type or content_type.startswith("application/octet-stream"):
        output_path.write_bytes(response.content)
        return output_path

    try:
        body = response.json()
    except ValueError as exc:
        snippet = (response.text or "")[:300]
        raise ValueError(f"Local video endpoint returned unsupported content: {snippet}") from exc

    return _materialize_response(body, output_path, timeout_seconds=timeout_seconds)


def _generate_replicate_video(
    payload: dict[str, Any],
    output_path: Path,
    *,
    timeout_seconds: int,
) -> Path:
    token = str(os.getenv("REPLICATE_API_TOKEN") or "").strip()
    if not token:
        raise ValueError("REPLICATE_API_TOKEN is not configured.")

    client = _get_replicate_client()
    route_kind = str(payload.get("route_kind") or "cinematic").strip().lower()
    model_slug = str(payload.get("model") or default_replicate_video_generation_model()).strip()
    if route_kind == "speaking":
        quality_mode = str(payload.get("quality_mode") or "standard").strip().lower()
        avatar_mode = "pro" if quality_mode == "pro" else "std"
        image_path = Path(str(payload["reference_image_path"]))
        audio_path = Path(str(payload["reference_audio_path"]))
        if not image_path.exists():
            raise ValueError(f"Speaking-video generation is missing its reference image: {image_path}")
        if not audio_path.exists():
            raise ValueError(f"Speaking-video generation is missing its dialogue audio: {audio_path}")
    else:
        replicate_input = {
            "prompt": str(payload["prompt"]),
            "aspect_ratio": "16:9",
            "duration": _replicate_duration_seconds(float(payload["duration_seconds"])),
            "mode": str(payload.get("quality_mode") or "standard"),
            "generate_audio": bool(payload.get("generate_audio", True)),
        }

    _log(
        "Calling Replicate video model "
        f"{model_slug} "
        f"for scene {payload['scene'].get('id', '?')}"
    )

    def _call_replicate() -> Any:
        if route_kind == "speaking":
            with ExitStack() as stack:
                return client.run(
                    model_slug,
                    input={
                        "image": stack.enter_context(image_path.open("rb")),
                        "audio": stack.enter_context(audio_path.open("rb")),
                        "mode": avatar_mode,
                        "prompt": str(payload["prompt"]),
                    },
                )
        return client.run(
            model_slug,
            input=replicate_input,
        )

    output = image_limiter.call_with_retry(_call_replicate)
    return _materialize_replicate_output(output, output_path, timeout_seconds=timeout_seconds)


def resolve_video_generation_request(
    scene: dict[str, Any],
    *,
    brief: dict[str, Any] | None = None,
    provider: str = "local",
    model: str | None = None,
    model_selection_mode: str | None = None,
    quality_mode: str | None = None,
    generate_audio: bool | None = None,
    duration_seconds: float | None = None,
    width: int = TARGET_WIDTH,
    height: int = TARGET_HEIGHT,
    fps: int = DEFAULT_FPS,
) -> dict[str, Any]:
    """Resolve the effective video-generation request without performing it."""
    audio_path = scene.get("audio_path")
    resolved_duration = float(
        duration_seconds
        if duration_seconds is not None
        else estimate_scene_duration_seconds(scene, audio_path=audio_path)
    )
    payload = {
        "provider": str(provider or "local").strip().lower() or "local",
        "prompt": build_scene_video_prompt(scene, brief),
        "model": str(model or "").strip(),
        "model_selection_mode": str(model_selection_mode or "automatic").strip().lower() or "automatic",
        "quality_mode": str(quality_mode or "standard").strip().lower() or "standard",
        "generate_audio": bool(True if generate_audio is None else generate_audio),
        "duration_seconds": round(max(resolved_duration, 1.0), 2),
        "width": int(width),
        "height": int(height),
        "fps": int(fps),
        "scene": {
            "id": int(scene.get("id", 0)),
            "title": str(scene.get("title") or ""),
            "narration": str(scene.get("narration") or ""),
            "visual_prompt": str(scene.get("visual_prompt") or ""),
            "on_screen_text": scene.get("on_screen_text") if isinstance(scene.get("on_screen_text"), list) else [],
        },
        "brief": {
            "visual_style": str((brief or {}).get("visual_style") or ""),
            "tone": str((brief or {}).get("tone") or ""),
            "audience": str((brief or {}).get("audience") or ""),
            "style_reference_summary": str((brief or {}).get("style_reference_summary") or ""),
        },
    }
    if payload["provider"] == "replicate":
        route = resolve_replicate_video_generation_route(
            scene,
            model=payload["model"],
            model_selection_mode=payload["model_selection_mode"],
            generate_audio=bool(payload["generate_audio"]),
        )
        payload["model"] = route["model"]
        payload["route_kind"] = route["route_kind"]
        payload["route_reason"] = route["reason"]
        if payload["quality_mode"] not in {"standard", "pro"}:
            payload["quality_mode"] = "standard"
        payload["prompt"] = build_scene_video_prompt(scene, brief, route_kind=str(payload["route_kind"]))
    return payload


def generate_scene_video_result(
    scene: dict[str, Any],
    project_dir: str | Path,
    *,
    brief: dict[str, Any] | None = None,
    provider: str = "local",
    model: str | None = None,
    model_selection_mode: str | None = None,
    quality_mode: str | None = None,
    generate_audio: bool | None = None,
    image_provider: str | None = None,
    image_model: str | None = None,
    tts_kwargs: dict[str, Any] | None = None,
    duration_seconds: float | None = None,
    width: int = TARGET_WIDTH,
    height: int = TARGET_HEIGHT,
    fps: int = DEFAULT_FPS,
) -> dict[str, Any]:
    """Generate a video clip and return execution metadata."""
    project_path = Path(project_dir)
    output_path = project_path / "clips" / f"scene_{int(scene.get('id', 0)):03d}_generated.mp4"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = resolve_video_generation_request(
        scene,
        brief=brief,
        provider=provider,
        model=model,
        model_selection_mode=model_selection_mode,
        quality_mode=quality_mode,
        generate_audio=generate_audio,
        duration_seconds=duration_seconds,
        width=width,
        height=height,
        fps=fps,
    )
    payload["output_path"] = str(output_path)
    timeout_seconds = _local_video_timeout_seconds()
    result: dict[str, Any] = {
        "path": output_path,
        "provider": str(payload.get("provider") or provider or "local").strip().lower() or "local",
        "model": str(payload.get("model") or model or "").strip(),
        "route_kind": str(payload.get("route_kind") or scene.get("video_scene_kind") or "").strip().lower() or None,
        "route_reason": str(payload.get("route_reason") or "").strip() or None,
        "quality_mode": str(payload.get("quality_mode") or quality_mode or "standard").strip().lower() or "standard",
        "generate_audio": bool(payload.get("generate_audio", True)),
        "duration_seconds": float(payload.get("duration_seconds") or 0.0),
        "reference_image_generated": False,
        "reference_audio_generated": False,
        "reference_image_provider": None,
        "reference_image_model": None,
        "reference_audio_provider": None,
        "reference_audio_model": None,
    }

    if result["provider"] == "replicate":
        token = str(os.getenv("REPLICATE_API_TOKEN") or "").strip()
        if not token:
            raise ValueError("REPLICATE_API_TOKEN is not configured.")
        if payload["route_kind"] == "speaking":
            if str(scene.get("video_scene_kind") or "").strip().lower() not in {"cinematic", "speaking"}:
                scene["video_scene_kind"] = "speaking"
            reference_image, image_generated = _ensure_speaking_reference_image(
                scene,
                project_dir=project_path,
                brief=brief,
                image_provider=str(image_provider or "manual").strip().lower(),
                image_model=str(image_model or "").strip(),
            )
            reference_audio = _ensure_speaking_audio(
                scene,
                project_dir=project_path,
                tts_kwargs=tts_kwargs,
            )
            payload["reference_image_path"] = str(reference_image)
            payload["reference_audio_path"] = str(reference_audio["path"])
            result["reference_image_generated"] = image_generated
            result["reference_audio_generated"] = bool(reference_audio.get("generated"))
            result["reference_image_provider"] = str(image_provider or "manual").strip().lower() or None
            result["reference_image_model"] = str(image_model or "").strip() or None
            result["reference_audio_provider"] = str(reference_audio.get("provider") or "") or None
            result["reference_audio_model"] = str(reference_audio.get("model") or "") or None
        path = _generate_replicate_video(payload, output_path, timeout_seconds=timeout_seconds)
    elif result["provider"] == "local":
        if not local_video_generation_available():
            raise ValueError(
                "Local video generation is not configured. "
                "Set CATHODE_LOCAL_VIDEO_COMMAND or CATHODE_LOCAL_VIDEO_ENDPOINT."
            )
        payload["model"] = str(payload["model"] or default_local_video_generation_model() or "").strip()
        result["model"] = str(payload["model"] or "")
        if _local_video_command():
            path = _run_local_video_command(payload, output_path, timeout_seconds=timeout_seconds)
        else:
            path = _request_local_video_endpoint(payload, output_path, timeout_seconds=timeout_seconds)
    else:
        raise ValueError(f"Unsupported video provider: {provider}")

    if not path.exists():
        raise ValueError(f"Video generation did not create the expected output: {path}")
    result["path"] = path
    return result


def generate_scene_video(
    scene: dict[str, Any],
    project_dir: str | Path,
    *,
    brief: dict[str, Any] | None = None,
    provider: str = "local",
    model: str | None = None,
    model_selection_mode: str | None = None,
    quality_mode: str | None = None,
    generate_audio: bool | None = None,
    image_provider: str | None = None,
    image_model: str | None = None,
    tts_kwargs: dict[str, Any] | None = None,
    duration_seconds: float | None = None,
    width: int = TARGET_WIDTH,
    height: int = TARGET_HEIGHT,
    fps: int = DEFAULT_FPS,
) -> Path:
    """Generate a video clip for one storyboard scene."""
    return Path(
        generate_scene_video_result(
            scene,
            project_dir,
            brief=brief,
            provider=provider,
            model=model,
            model_selection_mode=model_selection_mode,
            quality_mode=quality_mode,
            generate_audio=generate_audio,
            image_provider=image_provider,
            image_model=image_model,
            tts_kwargs=tts_kwargs,
            duration_seconds=duration_seconds,
            width=width,
            height=height,
            fps=fps,
        )["path"]
    )
