"""Remotion manifest building and render helpers for motion/hybrid projects."""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Callable
from urllib.parse import quote

from .project_schema import resolve_text_render_mode, scene_composition_payload, scene_requires_remotion
from .runtime import REPO_ROOT
from .video_assembly import (
    DEFAULT_FPS,
    get_media_duration,
    get_video_scene_timing,
    normalize_render_profile,
    resolve_scene_video_path,
    scene_uses_clip_audio,
)

_DEFAULT_API_BASE_URL = "http://127.0.0.1:9321"
_DEFAULT_MOTION_TEMPLATE = "kinetic_title"
_BUILTIN_TEXT_OVERLAY_FAMILIES = {"software_demo_focus"}


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
    return ["kinetic_title", "bullet_stack", "quote_focus", "kinetic_statements", "media_pan", "software_demo_focus"]


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
    composition = scene_composition_payload(scene)
    lines = [str(item).strip() for item in (scene.get("on_screen_text") or []) if str(item).strip()]
    title = str(scene.get("title") or "").strip()
    narration = str(scene.get("narration") or "").strip()
    props = (
        composition.get("props")
        if isinstance(composition.get("props"), dict)
        else motion_raw.get("props")
        if isinstance(motion_raw.get("props"), dict)
        else {}
    )

    headline = str(props.get("headline") or (lines[0] if lines else title) or "Motion beat").strip()
    body = str(props.get("body") or "\n".join(lines[1:3]) or narration[:180]).strip()
    kicker = str(props.get("kicker") or title or "Cathode").strip()
    bullets = props.get("bullets") if isinstance(props.get("bullets"), list) else lines[:4]

    return {
        "template_id": str(motion_raw.get("template_id") or composition.get("family") or "").strip() or infer_motion_template(scene),
        "props": {
            "headline": headline,
            "body": body,
            "kicker": kicker,
            "bullets": [str(item).strip() for item in bullets if str(item).strip()],
            "accent": str(props.get("accent") or "").strip(),
        },
        "render_path": motion_raw.get("render_path") or composition.get("render_path"),
        "preview_path": motion_raw.get("preview_path") or composition.get("preview_path"),
        "rationale": str(motion_raw.get("rationale") or composition.get("rationale") or "").strip(),
    }


def motion_scene_is_ready(scene: dict[str, Any]) -> bool:
    """Return whether a motion scene has enough template data to render."""
    composition = scene_composition_payload(scene)
    return bool(str(composition.get("family") or "").strip())


def scene_has_renderable_visual(
    scene: dict[str, Any],
    *,
    render_backend: str = "ffmpeg",
) -> bool:
    """Return whether the scene has the visual requirements for the chosen backend."""
    scene_type = str(scene.get("scene_type") or "image").strip().lower()
    composition = scene_composition_payload(scene)
    if scene_type == "video":
        value = resolve_scene_video_path(scene)
        return bool(value and Path(str(value)).exists())
    if scene_type == "motion" or (render_backend == "remotion" and composition.get("mode") == "native"):
        if render_backend == "remotion":
            return motion_scene_is_ready(scene)
        value = resolve_scene_video_path(scene)
        return bool(value and Path(str(value)).exists())
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
        effective_audio_duration = None if scene_uses_clip_audio(scene) else audio_duration
        timing = get_video_scene_timing(scene, audio_duration=effective_audio_duration)
        duration = float(effective_audio_duration or timing.get("effective_duration") or 5.0)
    else:
        duration = float(audio_duration or 5.0)

    return max(duration, 1.0 / max(fps, 1)), timing


def _scene_text_layer_kind(
    scene: dict[str, Any],
    *,
    text_render_mode: str,
    composition: dict[str, Any],
) -> str:
    scene_type = str(scene.get("scene_type") or "image").strip().lower()
    family = str(composition.get("family") or "").strip()
    mode = str(composition.get("mode") or "none").strip().lower()
    lines = [str(item).strip() for item in (scene.get("on_screen_text") or []) if str(item).strip()]
    if scene_type != "motion" and family in _BUILTIN_TEXT_OVERLAY_FAMILIES:
        props = composition.get("props") if isinstance(composition.get("props"), dict) else {}
        headline = str(props.get("headline") or "").strip()
        if lines or headline:
            return family
    if scene_type == "motion" or not lines:
        return "none"

    if mode == "overlay":
        return "captions"
    if text_render_mode == "deterministic_overlay" and scene_type == "image":
        return "captions"
    return "none"


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
    brief = plan.get("meta", {}).get("brief") if isinstance(plan.get("meta", {}).get("brief"), dict) else {}
    text_render_mode = resolve_text_render_mode(
        profile.get("text_render_mode") or brief.get("text_render_mode")
    )
    scenes_raw = list(plan.get("scenes", []))
    scenes: list[dict[str, Any]] = []

    for scene in scenes_raw:
        uid = str(scene.get("uid") or "")
        if preview_scene_uid and uid != preview_scene_uid:
            continue

        duration_seconds, timing = _scene_duration_seconds(scene, fps)
        duration_in_frames = max(1, round(duration_seconds * fps))
        motion = scene_motion_payload(scene)
        composition = scene_composition_payload(scene)
        video_audio_source = "clip" if scene_uses_clip_audio(scene) else "narration"
        trim_end = timing.get("trim_end")
        trim_end_frames = round(float(trim_end) * fps) if trim_end is not None else None
        trim_before_frames = round(float(timing.get("trim_start") or 0.0) * fps)
        trim_after_frame = None
        if trim_end_frames is not None:
            trim_after_frame = max(trim_end_frames, trim_before_frames + 1)

        play_frames = duration_in_frames
        hold_frames = 0
        if timing:
            hold_frames = max(0, round(float(timing.get("freeze_duration") or 0.0) * fps))
            play_frames = max(1, duration_in_frames - hold_frames)
        transition_after = (
            {
                "kind": str(composition["transition_after"].get("kind") or "").strip(),
                "durationInFrames": int(composition["transition_after"].get("duration_in_frames") or 20),
            }
            if isinstance(composition.get("transition_after"), dict)
            else None
        )
        transition_duration_in_frames = int(transition_after["durationInFrames"]) if transition_after else 0

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
                "sequenceDurationInFrames": duration_in_frames + transition_duration_in_frames,
                "audioUrl": None if video_audio_source == "clip" else project_media_url(project_name, project_dir, scene.get("audio_path")),
                "imageUrl": project_media_url(project_name, project_dir, scene.get("image_path")),
                "videoUrl": project_media_url(project_name, project_dir, scene.get("video_path")),
                "previewUrl": project_media_url(project_name, project_dir, scene.get("preview_path")),
                "videoAudioSource": video_audio_source,
                "trimBeforeFrames": trim_before_frames,
                "trimAfterFrames": trim_after_frame,
                "playbackRate": float(timing.get("playback_speed") or 1.0),
                "holdFrames": hold_frames,
                "playFrames": play_frames,
                "requiresRemotion": scene_requires_remotion(scene),
                "textLayerKind": _scene_text_layer_kind(
                    scene,
                    text_render_mode=text_render_mode,
                    composition=composition,
                ),
                "composition": {
                    "family": str(composition.get("family") or "").strip(),
                    "mode": str(composition.get("mode") or "none").strip(),
                    "props": composition.get("props") if isinstance(composition.get("props"), dict) else {},
                    "transitionAfter": transition_after,
                    "data": composition.get("data"),
                    "rationale": composition.get("rationale"),
                },
                "motion": {
                    "templateId": str(motion["template_id"] or composition.get("family") or "").strip(),
                    "props": motion["props"] if isinstance(motion["props"], dict) else composition.get("props"),
                    "rationale": motion["rationale"] or composition.get("rationale"),
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
        "textRenderMode": text_render_mode,
        "totalDurationInFrames": sum(int(scene["durationInFrames"]) for scene in scenes),
        "outputPath": str(output_path),
        "scenes": scenes,
    }


def _progress_payload_from_remotion_event(event: dict[str, Any]) -> dict[str, Any] | None:
    event_type = str(event.get("type") or "").strip().lower()
    if event_type == "status":
        return {
            "progress": 0.02,
            "progress_kind": "render",
            "progress_label": str(event.get("label") or "Preparing render"),
            "progress_detail": str(event.get("detail") or ""),
            "progress_status": str(event.get("stage") or "preparing"),
        }

    if event_type == "progress":
        stage = str(event.get("stage") or "").strip().lower() or "render"
        progress = float(event.get("progress") or 0.0)
        if stage == "encoding":
            label = "Encoding video"
        elif stage == "muxing":
            label = "Muxing audio and video"
        else:
            label = "Rendering frames"
        detail = f"rendered {int(event.get('renderedFrames') or 0)} frames, encoded {int(event.get('encodedFrames') or 0)}"
        return {
            "progress": max(0.02, min(progress, 0.99)),
            "progress_kind": "render",
            "progress_label": label,
            "progress_detail": detail,
            "progress_status": stage,
        }

    if event_type == "done":
        return {
            "progress": 1.0,
            "progress_kind": "render",
            "progress_label": str(event.get("label") or "Render complete"),
            "progress_detail": str(event.get("detail") or ""),
            "progress_status": "done",
        }

    return None


def render_manifest_with_remotion(
    manifest: dict[str, Any],
    *,
    output_path: Path,
    progress_callback: Callable[[dict[str, Any]], None] | None = None,
) -> Path:
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
        process = subprocess.Popen(
            ["node", str(script_path), str(manifest_path), str(output_path)],
            cwd=str(REPO_ROOT / "frontend"),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        output_lines: list[str] = []
        assert process.stdout is not None
        for raw_line in process.stdout:
            line = raw_line.rstrip()
            if not line:
                continue
            output_lines.append(line)
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                event = None
            if event is not None and progress_callback is not None:
                payload = _progress_payload_from_remotion_event(event)
                if payload:
                    progress_callback(payload)
            print(line, flush=True)
        return_code = process.wait()
    finally:
        manifest_path.unlink(missing_ok=True)

    if return_code != 0:
        stderr = "\n".join(output_lines).strip() or "Unknown Remotion render failure."
        raise RuntimeError(stderr)

    if not output_path.exists() or output_path.stat().st_size == 0:
        raise RuntimeError(f"Remotion render failed to create output: {output_path}")

    return output_path
