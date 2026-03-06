"""Local video generation adapters for env-driven backends."""

from __future__ import annotations

import base64
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import requests

from .runtime import default_local_video_generation_model, local_video_generation_available
from .video_assembly import DEFAULT_FPS, TARGET_HEIGHT, TARGET_WIDTH, get_media_duration

DEFAULT_VIDEO_DURATION_SECONDS = 5.0
DEFAULT_VIDEO_TIMEOUT_SECONDS = 900


def _log(message: str) -> None:
    print(f"[VIDEO_GEN] {message}", file=sys.stderr, flush=True)


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


def build_scene_video_prompt(scene: dict[str, Any], brief: dict[str, Any] | None = None) -> str:
    """Build a grounded generation prompt for a local video backend."""
    lines: list[str] = []

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


def generate_scene_video(
    scene: dict[str, Any],
    project_dir: str | Path,
    *,
    brief: dict[str, Any] | None = None,
    provider: str = "local",
    model: str | None = None,
    duration_seconds: float | None = None,
    width: int = TARGET_WIDTH,
    height: int = TARGET_HEIGHT,
    fps: int = DEFAULT_FPS,
) -> Path:
    """Generate a local video clip for one storyboard scene."""
    if provider != "local":
        raise ValueError(f"Unsupported video provider: {provider}")
    if not local_video_generation_available():
        raise ValueError(
            "Local video generation is not configured. "
            "Set CATHODE_LOCAL_VIDEO_COMMAND or CATHODE_LOCAL_VIDEO_ENDPOINT."
        )

    project_path = Path(project_dir)
    output_path = project_path / "clips" / f"scene_{int(scene.get('id', 0)):03d}_generated.mp4"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    audio_path = scene.get("audio_path")
    resolved_duration = float(
        duration_seconds
        if duration_seconds is not None
        else estimate_scene_duration_seconds(scene, audio_path=audio_path)
    )
    resolved_model = str(model or default_local_video_generation_model() or "").strip()

    payload = {
        "prompt": build_scene_video_prompt(scene, brief),
        "model": resolved_model,
        "output_path": str(output_path),
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
    timeout_seconds = _local_video_timeout_seconds()

    if _local_video_command():
        path = _run_local_video_command(payload, output_path, timeout_seconds=timeout_seconds)
    else:
        path = _request_local_video_endpoint(payload, output_path, timeout_seconds=timeout_seconds)

    if not path.exists():
        raise ValueError(f"Local video generation did not create the expected output: {path}")
    return path
