"""Remotion manifest building and render helpers for motion/hybrid projects."""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any
from urllib.parse import quote

from .runtime import REPO_ROOT
from .video_assembly import DEFAULT_FPS, get_media_duration, get_video_scene_timing, normalize_render_profile

_DEFAULT_API_BASE_URL = "http://127.0.0.1:9321"
_DEFAULT_MOTION_TEMPLATE = "kinetic_title"


def _api_base_url() -> str:
    return str(os.getenv("CATHODE_API_BASE_URL") or _DEFAULT_API_BASE_URL).rstrip("/")


def _relative_project_media_path(project_name: str, project_dir: Path, raw_path: Any) -> str | None:
    value = str(raw_path or "").strip()
    if not value:
        return None

    normalized = value.replace("\\", "/").lstrip("/")
    markers = [f"projects/{project_name}/", f"/projects/{project_name}/"]
    for marker in markers:
        index = normalized.rfind(marker)
        if index >= 0:
            return normalized[index + len(marker) :]

    path = Path(value).expanduser()
    if path.is_absolute():
        resolved = path.resolve()
        project_root = project_dir.resolve()
        if str(resolved).startswith(str(project_root)):
            return str(resolved.relative_to(project_root)).replace("\\", "/")
        return None

    if normalized.startswith("projects/"):
        return None
    return normalized


def project_media_url(project_name: str, project_dir: Path, raw_path: Any) -> str | None:
    relative_path = _relative_project_media_path(project_name, project_dir, raw_path)
    if not relative_path:
        return None
    encoded = "/".join(quote(part) for part in relative_path.split("/") if part)
    return f"{_api_base_url()}/api/projects/{quote(project_name)}/media/{encoded}"


def motion_template_options() -> list[str]:
    """Return the supported motion template ids used in the Remotion layer."""
    return ["kinetic_title", "bullet_stack", "quote_focus"]


def infer_motion_template(scene: dict[str, Any]) -> str:
    """Pick a simple template based on the scene content."""
    lines = [str(item).strip() for item in (scene.get("on_screen_text") or []) if str(item).strip()]
    narration = str(scene.get("narration") or "").strip()
    if len(lines) >= 3:
        return "bullet_stack"
    if narration and len(narration.split()) >= 18:
        return "quote_focus"
    return _DEFAULT_MOTION_TEMPLATE


def scene_motion_payload(scene: dict[str, Any]) -> dict[str, Any]:
    """Return normalized motion-scene metadata with default props."""
    motion_raw = scene.get("motion") if isinstance(scene.get("motion"), dict) else {}
    lines = [str(item).strip() for item in (scene.get("on_screen_text") or []) if str(item).strip()]
    title = str(scene.get("title") or "").strip()
    narration = str(scene.get("narration") or "").strip()
    props = motion_raw.get("props") if isinstance(motion_raw.get("props"), dict) else {}

    headline = str(props.get("headline") or (lines[0] if lines else title) or "Motion beat").strip()
    body = str(props.get("body") or "\n".join(lines[1:3]) or narration[:180]).strip()
    kicker = str(props.get("kicker") or title or "Cathode").strip()
    bullets = props.get("bullets") if isinstance(props.get("bullets"), list) else lines[:4]

    return {
        "template_id": str(motion_raw.get("template_id") or "").strip() or infer_motion_template(scene),
        "props": {
            "headline": headline,
            "body": body,
            "kicker": kicker,
            "bullets": [str(item).strip() for item in bullets if str(item).strip()],
            "accent": str(props.get("accent") or "").strip(),
        },
        "render_path": motion_raw.get("render_path"),
        "preview_path": motion_raw.get("preview_path"),
        "rationale": str(motion_raw.get("rationale") or "").strip(),
    }


def motion_scene_is_ready(scene: dict[str, Any]) -> bool:
    """Return whether a motion scene has enough template data to render."""
    motion = scene_motion_payload(scene)
    return bool(motion["template_id"])


def scene_has_renderable_visual(
    scene: dict[str, Any],
    *,
    render_backend: str = "ffmpeg",
) -> bool:
    """Return whether the scene has the visual requirements for the chosen backend."""
    scene_type = str(scene.get("scene_type") or "image").strip().lower()
    if scene_type == "video":
        value = scene.get("video_path")
        return bool(value and Path(str(value)).exists())
    if scene_type == "motion":
        if render_backend == "remotion":
            return motion_scene_is_ready(scene)
        motion = scene_motion_payload(scene)
        render_path = motion.get("render_path")
        return bool(render_path and Path(str(render_path)).exists())
    value = scene.get("image_path")
    return bool(value and Path(str(value)).exists())


def _scene_duration_seconds(scene: dict[str, Any], fps: int) -> tuple[float, dict[str, Any]]:
    audio_duration = None
    audio_path = scene.get("audio_path")
    if audio_path and Path(str(audio_path)).exists():
        audio_duration = float(get_media_duration(audio_path) or 0.0) or None

    scene_type = str(scene.get("scene_type") or "image").strip().lower()
    timing: dict[str, Any] = {}
    if scene_type == "video":
        timing = get_video_scene_timing(scene, audio_duration=audio_duration)
        duration = float(audio_duration or timing.get("effective_duration") or 5.0)
    else:
        duration = float(audio_duration or 5.0)

    return max(duration, 1.0 / max(fps, 1)), timing


def build_remotion_manifest(
    *,
    project_dir: Path,
    plan: dict[str, Any],
    output_path: Path,
    render_profile: dict[str, Any] | None = None,
    preview_scene_uid: str | None = None,
) -> dict[str, Any]:
    """Build the normalized manifest consumed by the Remotion renderer."""
    project_dir = Path(project_dir)
    profile = normalize_render_profile(render_profile)
    fps = int(profile.get("fps") or DEFAULT_FPS)
    project_name = str(plan.get("meta", {}).get("project_name") or project_dir.name)
    scenes_raw = list(plan.get("scenes", []))
    scenes: list[dict[str, Any]] = []

    for scene in scenes_raw:
        uid = str(scene.get("uid") or "")
        if preview_scene_uid and uid != preview_scene_uid:
            continue

        duration_seconds, timing = _scene_duration_seconds(scene, fps)
        duration_in_frames = max(1, round(duration_seconds * fps))
        motion = scene_motion_payload(scene)
        source_duration = timing.get("source_duration")
        trim_end = timing.get("trim_end")
        source_frames = round(float(source_duration) * fps) if source_duration is not None else None
        trim_end_frames = round(float(trim_end) * fps) if trim_end is not None else None
        trim_after_frames = 0
        if source_frames is not None and trim_end_frames is not None:
            trim_after_frames = max(source_frames - trim_end_frames, 0)

        play_frames = duration_in_frames
        hold_frames = 0
        if timing:
            hold_frames = max(0, round(float(timing.get("freeze_duration") or 0.0) * fps))
            play_frames = max(1, duration_in_frames - hold_frames)

        scenes.append(
            {
                "uid": uid,
                "sceneType": str(scene.get("scene_type") or "image").strip().lower(),
                "title": str(scene.get("title") or "").strip(),
                "narration": str(scene.get("narration") or "").strip(),
                "onScreenText": [
                    str(item).strip()
                    for item in (scene.get("on_screen_text") or [])
                    if str(item).strip()
                ],
                "durationInFrames": duration_in_frames,
                "audioUrl": project_media_url(project_name, project_dir, scene.get("audio_path")),
                "imageUrl": project_media_url(project_name, project_dir, scene.get("image_path")),
                "videoUrl": project_media_url(project_name, project_dir, scene.get("video_path")),
                "previewUrl": project_media_url(project_name, project_dir, scene.get("preview_path")),
                "trimBeforeFrames": round(float(timing.get("trim_start") or 0.0) * fps),
                "trimAfterFrames": trim_after_frames,
                "playbackRate": float(timing.get("playback_speed") or 1.0),
                "holdFrames": hold_frames,
                "playFrames": play_frames,
                "motion": {
                    "templateId": motion["template_id"],
                    "props": motion["props"],
                    "rationale": motion["rationale"],
                },
            }
        )

    if not scenes:
        raise ValueError("No renderable scenes were included in the Remotion manifest.")

    return {
        "projectName": project_name,
        "width": int(profile.get("width") or 1664),
        "height": int(profile.get("height") or 928),
        "fps": fps,
        "totalDurationInFrames": sum(int(scene["durationInFrames"]) for scene in scenes),
        "outputPath": str(output_path),
        "scenes": scenes,
    }


def render_manifest_with_remotion(manifest: dict[str, Any], *, output_path: Path) -> Path:
    """Render a manifest to MP4 via the frontend Remotion bundle."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    scripts_dir = REPO_ROOT / "frontend" / "scripts"
    script_path = scripts_dir / "render-remotion.mjs"
    if not script_path.exists():
        raise ValueError(f"Missing Remotion render script: {script_path}")

    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as handle:
        json.dump(manifest, handle, indent=2)
        manifest_path = Path(handle.name)

    try:
        completed = subprocess.run(
            ["node", str(script_path), str(manifest_path), str(output_path)],
            cwd=str(REPO_ROOT / "frontend"),
            text=True,
            capture_output=True,
            check=False,
        )
    finally:
        manifest_path.unlink(missing_ok=True)

    if completed.returncode != 0:
        stderr = completed.stderr.strip() or completed.stdout.strip() or "Unknown Remotion render failure."
        raise RuntimeError(stderr)

    if not output_path.exists() or output_path.stat().st_size == 0:
        raise RuntimeError(f"Remotion render failed to create output: {output_path}")

    return output_path
