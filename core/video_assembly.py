"""Video assembly using direct ffmpeg/ffprobe orchestration."""

from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any

# Target dimensions for video output (must match image_gen.py)
TARGET_WIDTH = 1664
TARGET_HEIGHT = 928
TARGET_ASPECT_RATIO = "16:9"
DEFAULT_FPS = 24
DEFAULT_AUDIO_SAMPLE_RATE = 48000
DEFAULT_AUDIO_CHANNELS = 2
DEFAULT_AUDIO_LAYOUT = "stereo"
DEFAULT_SCENE_CODEC = "mp4"
DEFAULT_SCENE_BITRATE = "6M"

_ENCODER_CACHE: set[str] | None = None


def normalize_render_profile(render_profile: dict[str, Any] | None = None) -> dict[str, Any]:
    """Normalize and validate render profile configuration."""
    profile = {
        "version": "v1",
        "aspect_ratio": TARGET_ASPECT_RATIO,
        "width": TARGET_WIDTH,
        "height": TARGET_HEIGHT,
        "fps": DEFAULT_FPS,
        "scene_types": ["image", "video", "motion"],
        "video_encoder": "auto",
        "prefer_gpu": True,
    }
    if isinstance(render_profile, dict):
        profile.update(render_profile)

    profile["aspect_ratio"] = str(profile.get("aspect_ratio") or TARGET_ASPECT_RATIO)
    profile["width"] = int(profile.get("width") or TARGET_WIDTH)
    profile["height"] = int(profile.get("height") or TARGET_HEIGHT)
    profile["fps"] = int(profile.get("fps") or DEFAULT_FPS)
    profile["video_encoder"] = str(profile.get("video_encoder") or "auto").strip().lower() or "auto"
    profile["prefer_gpu"] = bool(profile.get("prefer_gpu", True))

    scene_types = profile.get("scene_types")
    if not isinstance(scene_types, list) or not scene_types:
        scene_types = ["image", "video", "motion"]
    profile["scene_types"] = [str(item).strip().lower() for item in scene_types if str(item).strip()]
    if not profile["scene_types"]:
        profile["scene_types"] = ["image", "video", "motion"]

    if profile["aspect_ratio"] != TARGET_ASPECT_RATIO:
        raise ValueError(f"Unsupported aspect_ratio={profile['aspect_ratio']!r}. v1 only supports 16:9.")
    if profile["width"] != TARGET_WIDTH or profile["height"] != TARGET_HEIGHT:
        raise ValueError(
            "Unsupported render resolution. v1 only supports 1664x928; "
            f"got {profile['width']}x{profile['height']}."
        )

    return profile


def _normalize_nonnegative_float(value: Any, fallback: float) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return fallback
    if parsed < 0:
        return fallback
    return parsed


def _normalize_positive_float(value: Any, fallback: float) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return fallback
    if parsed <= 0:
        return fallback
    return parsed


def _run_command(
    cmd: list[str],
    *,
    cwd: Path | None = None,
    capture: bool = False,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        check=True,
        text=True,
        capture_output=capture,
    )


def _probe_duration(path: Path) -> float | None:
    try:
        completed = _run_command(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(path),
            ],
            capture=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return None

    raw = completed.stdout.strip()
    if not raw or raw == "N/A":
        return None
    try:
        duration = float(raw)
    except ValueError:
        return None
    return duration if duration >= 0 else None


def get_media_duration(path: str | Path) -> float | None:
    """Return duration in seconds for an audio or video asset."""
    media_path = Path(path)
    if not media_path.exists():
        return None
    return _probe_duration(media_path)


def media_has_audio_stream(path: str | Path) -> bool:
    """Return whether a media file contains at least one audio stream."""
    media_path = Path(path)
    if not media_path.exists():
        return False
    try:
        completed = _run_command(
            [
                "ffprobe",
                "-v",
                "error",
                "-select_streams",
                "a",
                "-show_entries",
                "stream=index",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(media_path),
            ],
            capture=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return False
    return bool(completed.stdout.strip())


def scene_uses_clip_audio(scene: dict[str, Any]) -> bool:
    """Return whether a video scene should render from the clip's embedded audio."""
    return (
        str(scene.get("scene_type") or "image").strip().lower() == "video"
        and str(scene.get("video_audio_source") or "narration").strip().lower() == "clip"
    )


def resolve_scene_video_path(scene: dict[str, Any]) -> str | None:
    """Return the playable clip path for video-like scenes."""
    scene_type = str(scene.get("scene_type") or "image").strip().lower()
    if scene_type == "motion":
        motion = scene.get("motion") if isinstance(scene.get("motion"), dict) else {}
        for candidate in (
            motion.get("render_path"),
            motion.get("preview_path"),
            scene.get("preview_path"),
        ):
            value = str(candidate or "").strip()
            if value and Path(value).exists():
                return value
        return None

    value = str(scene.get("video_path") or "").strip()
    return value or None


def get_video_scene_timing(
    scene: dict[str, Any],
    *,
    source_duration: float | None = None,
    audio_duration: float | None = None,
) -> dict[str, Any]:
    """Normalize video-scene timing metadata and compute effective durations."""
    video_path = resolve_scene_video_path(scene)
    if source_duration is None and video_path and Path(video_path).exists():
        source_duration = get_media_duration(video_path)

    trim_start = _normalize_nonnegative_float(scene.get("video_trim_start"), 0.0)
    raw_trim_end = scene.get("video_trim_end")
    trim_end = None
    if raw_trim_end not in (None, ""):
        try:
            trim_end = float(raw_trim_end)
        except (TypeError, ValueError):
            trim_end = None

    if source_duration is not None:
        source_duration = max(float(source_duration), 0.0)
        trim_start = min(trim_start, source_duration)
        if trim_end is None:
            trim_end = source_duration
        else:
            trim_end = min(max(trim_end, trim_start), source_duration)
    elif trim_end is not None:
        trim_end = max(trim_end, trim_start)

    playback_speed = _normalize_positive_float(scene.get("video_playback_speed"), 1.0)
    trimmed_duration = None
    if trim_end is not None:
        trimmed_duration = max(trim_end - trim_start, 0.0)
    elif source_duration is not None:
        trimmed_duration = max(float(source_duration) - trim_start, 0.0)

    effective_duration = None
    if trimmed_duration is not None:
        effective_duration = trimmed_duration / playback_speed if playback_speed > 0 else trimmed_duration

    hold_last_frame = bool(scene.get("video_hold_last_frame", True))
    freeze_duration = 0.0
    if audio_duration is not None and effective_duration is not None and hold_last_frame:
        freeze_duration = max(float(audio_duration) - effective_duration, 0.0)

    return {
        "trim_start": trim_start,
        "trim_end": trim_end,
        "source_duration": source_duration,
        "trimmed_duration": trimmed_duration,
        "effective_duration": effective_duration,
        "playback_speed": playback_speed,
        "hold_last_frame": hold_last_frame,
        "freeze_duration": freeze_duration,
    }


def _available_encoders() -> set[str]:
    global _ENCODER_CACHE
    if _ENCODER_CACHE is not None:
        return _ENCODER_CACHE

    try:
        completed = _run_command(["ffmpeg", "-hide_banner", "-encoders"], capture=True)
    except (FileNotFoundError, subprocess.CalledProcessError) as exc:
        raise RuntimeError("ffmpeg must be installed and available on PATH.") from exc

    encoders: set[str] = set()
    for line in completed.stdout.splitlines():
        parts = line.split()
        if len(parts) >= 2 and parts[0] and parts[0][0] in {"V", "A", "S"}:
            encoders.add(parts[1].strip())
    _ENCODER_CACHE = encoders
    return encoders


def _select_video_encoder(profile: dict[str, Any]) -> str:
    available = _available_encoders()
    explicit = str(os.getenv("CATHODE_VIDEO_ENCODER") or profile.get("video_encoder") or "auto").strip().lower()
    disable_hw = str(os.getenv("CATHODE_DISABLE_HW_ENCODER") or "").strip().lower() in {"1", "true", "yes", "on"}
    prefer_gpu = bool(profile.get("prefer_gpu", True)) and not disable_hw

    if explicit and explicit != "auto":
        if explicit not in available:
            raise ValueError(
                f"Requested video encoder {explicit!r} is not available in this ffmpeg build."
            )
        return explicit

    candidates = (
        ["h264_videotoolbox", "h264_nvenc", "h264_qsv", "h264_amf", "libx264"]
        if prefer_gpu
        else ["libx264", "h264_videotoolbox", "h264_nvenc", "h264_qsv", "h264_amf"]
    )
    for encoder in candidates:
        if encoder in available:
            return encoder
    raise RuntimeError("No supported H.264 encoder found in ffmpeg.")


def _encoder_flags(encoder: str) -> list[str]:
    if encoder == "libx264":
        return ["-c:v", "libx264", "-preset", "ultrafast", "-crf", "35"]
    if encoder == "h264_videotoolbox":
        return ["-c:v", encoder, "-allow_sw", "1", "-b:v", DEFAULT_SCENE_BITRATE, "-maxrate", "8M"]
    if encoder == "h264_nvenc":
        return ["-c:v", encoder, "-preset", "p4", "-cq", "30", "-b:v", "0"]
    if encoder == "h264_qsv":
        return ["-c:v", encoder, "-preset", "veryfast", "-global_quality", "30"]
    if encoder == "h264_amf":
        return ["-c:v", encoder, "-usage", "transcoding", "-quality", "speed", "-b:v", DEFAULT_SCENE_BITRATE]
    return ["-c:v", encoder]


def _fit_filter(target_width: int, target_height: int, fps: int) -> str:
    return (
        f"fps={fps},"
        f"scale={target_width}:{target_height}:force_original_aspect_ratio=decrease,"
        f"pad={target_width}:{target_height}:(ow-iw)/2:(oh-ih)/2:color=black,"
        "setsar=1,"
        "format=yuv420p"
    )


def _audio_filter(target_duration: float) -> str:
    return (
        f"aresample={DEFAULT_AUDIO_SAMPLE_RATE},"
        f"apad=whole_dur={target_duration:.6f},"
        f"atrim=duration={target_duration:.6f},"
        "asetpts=PTS-STARTPTS"
    )


def _tempo_audio_filters(playback_speed: float) -> list[str]:
    """Return one or more atempo filters for the requested playback speed."""
    speed = max(float(playback_speed), 0.01)
    filters: list[str] = []
    while speed > 2.0:
        filters.append("atempo=2.0")
        speed /= 2.0
    while speed < 0.5:
        filters.append("atempo=0.5")
        speed /= 0.5
    if abs(speed - 1.0) > 1e-6:
        filters.append(f"atempo={speed:.8f}")
    return filters


def _scene_target_duration(scene: dict[str, Any], default_duration: float) -> tuple[float, bool]:
    scene_type = str(scene.get("scene_type") or "image").strip().lower()
    if scene_type == "video" and scene_uses_clip_audio(scene):
        timing = get_video_scene_timing(scene)
        video_path = resolve_scene_video_path(scene)
        return (
            float(timing["effective_duration"] or default_duration),
            bool(video_path and Path(video_path).exists() and media_has_audio_stream(video_path)),
        )

    audio_path = scene.get("audio_path")
    if audio_path and Path(audio_path).exists():
        audio_duration = get_media_duration(audio_path)
        return float(audio_duration or default_duration), True

    if scene_type in {"video", "motion"}:
        timing = get_video_scene_timing(scene)
        return float(timing["effective_duration"] or default_duration), False
    return default_duration, False


def _render_image_scene(
    scene: dict[str, Any],
    *,
    output_path: Path,
    target_duration: float,
    target_width: int,
    target_height: int,
    fps: int,
    encoder: str,
) -> None:
    image_path = scene.get("image_path")
    if not image_path or not Path(image_path).exists():
        raise ValueError(f"Scene {scene.get('id', 0)}: no image found at {image_path!r}")

    audio_path = scene.get("audio_path")
    cmd = [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-loop",
        "1",
        "-framerate",
        str(fps),
        "-i",
        str(image_path),
    ]
    if audio_path and Path(audio_path).exists():
        cmd.extend(["-i", str(audio_path)])
    else:
        cmd.extend(
            [
                "-f",
                "lavfi",
                "-i",
                f"anullsrc=channel_layout={DEFAULT_AUDIO_LAYOUT}:sample_rate={DEFAULT_AUDIO_SAMPLE_RATE}",
            ]
        )

    cmd.extend(
        [
            "-map",
            "0:v:0",
            "-map",
            "1:a:0",
            "-vf",
            _fit_filter(target_width, target_height, fps),
            "-af",
            _audio_filter(target_duration),
            "-t",
            f"{target_duration:.6f}",
            *(_encoder_flags(encoder)),
            "-c:a",
            "aac",
            "-ar",
            str(DEFAULT_AUDIO_SAMPLE_RATE),
            "-ac",
            str(DEFAULT_AUDIO_CHANNELS),
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            str(output_path),
        ]
    )
    _run_command(cmd)


def _render_video_scene(
    scene: dict[str, Any],
    *,
    output_path: Path,
    target_duration: float,
    target_width: int,
    target_height: int,
    fps: int,
    encoder: str,
) -> None:
    scene_id = int(scene.get("id", 0))
    video_path = resolve_scene_video_path(scene)
    if not video_path or not Path(video_path).exists():
        raise ValueError(f"Scene {scene_id}: no playable clip found at {video_path!r}")

    source_duration = get_media_duration(video_path)
    use_clip_audio = scene_uses_clip_audio(scene)
    timing = get_video_scene_timing(
        scene,
        source_duration=source_duration,
        audio_duration=None if use_clip_audio else target_duration,
    )

    if target_duration > float(timing["effective_duration"] or 0.0) + 0.05 and not bool(timing["hold_last_frame"]):
        extra = target_duration - float(timing["effective_duration"] or 0.0)
        raise ValueError(
            f"Scene {scene_id}: narration is {extra:.1f}s longer than the configured video clip. "
            "Extend the clip or enable last-frame hold."
        )

    trim_start = float(timing["trim_start"])
    trim_end = timing["trim_end"]
    playback_speed = float(timing["playback_speed"])
    freeze_duration = max(float(timing["freeze_duration"]), 0.0)

    filter_steps: list[str] = []
    if trim_start > 0.0 or trim_end is not None:
        trim_filter = f"trim=start={trim_start:.6f}"
        if trim_end is not None:
            trim_filter += f":end={float(trim_end):.6f}"
        filter_steps.append(trim_filter)
    filter_steps.append("setpts=PTS-STARTPTS")
    if abs(playback_speed - 1.0) > 1e-6:
        filter_steps.append(f"setpts=PTS/{playback_speed:.8f}")
    filter_steps.append(_fit_filter(target_width, target_height, fps))
    if freeze_duration > 0.05:
        filter_steps.append(f"tpad=stop_mode=clone:stop_duration={freeze_duration:.6f}")
    filter_steps.append(f"trim=duration={target_duration:.6f}")
    filter_steps.append("setpts=PTS-STARTPTS")

    audio_path = scene.get("audio_path")
    use_clip_input_audio = use_clip_audio and media_has_audio_stream(video_path)
    audio_map = "0:a:0" if use_clip_input_audio else "1:a:0"
    audio_filter_steps: list[str] = []
    if use_clip_input_audio:
        if trim_start > 0.0 or trim_end is not None:
            trim_filter = f"atrim=start={trim_start:.6f}"
            if trim_end is not None:
                trim_filter += f":end={float(trim_end):.6f}"
            audio_filter_steps.append(trim_filter)
        audio_filter_steps.extend(_tempo_audio_filters(playback_speed))
    audio_filter_steps.append(_audio_filter(target_duration))

    cmd = [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(video_path),
    ]
    if not use_clip_input_audio and audio_path and Path(audio_path).exists():
        cmd.extend(["-i", str(audio_path)])
    elif not use_clip_input_audio:
        cmd.extend(
            [
                "-f",
                "lavfi",
                "-i",
                f"anullsrc=channel_layout={DEFAULT_AUDIO_LAYOUT}:sample_rate={DEFAULT_AUDIO_SAMPLE_RATE}",
            ]
        )

    cmd.extend(
        [
            "-map",
            "0:v:0",
            "-map",
            audio_map,
            "-vf",
            ",".join(filter_steps),
            "-af",
            ",".join(audio_filter_steps),
            "-t",
            f"{target_duration:.6f}",
            *(_encoder_flags(encoder)),
            "-c:a",
            "aac",
            "-ar",
            str(DEFAULT_AUDIO_SAMPLE_RATE),
            "-ac",
            str(DEFAULT_AUDIO_CHANNELS),
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            str(output_path),
        ]
    )
    _run_command(cmd)


def _render_scene_file(
    scene: dict[str, Any],
    *,
    output_path: Path,
    target_duration: float,
    target_width: int,
    target_height: int,
    fps: int,
    encoder: str,
) -> None:
    scene_type = str(scene.get("scene_type") or "image").strip().lower()
    if scene_type not in {"image", "video", "motion"}:
        raise ValueError(
            f"Scene {scene.get('id', 0)} uses unsupported scene_type={scene_type!r}. "
            "Supported scene types are 'image', 'video', and 'motion'."
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    if scene_type == "image":
        _render_image_scene(
            scene,
            output_path=output_path,
            target_duration=target_duration,
            target_width=target_width,
            target_height=target_height,
            fps=fps,
            encoder=encoder,
        )
        return

    _render_video_scene(
        scene,
        output_path=output_path,
        target_duration=target_duration,
        target_width=target_width,
        target_height=target_height,
        fps=fps,
        encoder=encoder,
    )


def _archive_existing_video(output_path: Path, project_dir: Path) -> Path | None:
    """
    If output_path exists, move it to project_dir/.v1-videos with versioned naming.

    Example:
      - .v1-videos/<project>.mp4
      - .v1-videos/<project> v2.mp4
      - .v1-videos/<project> v3.mp4
    """
    output_path = Path(output_path)
    if not output_path.exists():
        return None

    archive_dir = Path(project_dir) / ".v1-videos"
    archive_dir.mkdir(parents=True, exist_ok=True)

    base = Path(project_dir).name.split("__")[0]
    ext = output_path.suffix or ".mp4"

    dest = archive_dir / f"{base}{ext}"
    if dest.exists():
        n = 2
        while True:
            candidate = archive_dir / f"{base} v{n}{ext}"
            if not candidate.exists():
                dest = candidate
                break
            n += 1

    output_path.replace(dest)
    return dest


def _write_concat_list(paths: list[Path], concat_list_path: Path) -> None:
    lines = []
    for path in paths:
        escaped = str(path.resolve()).replace("'", "'\\''")
        lines.append(f"file '{escaped}'")
    concat_list_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _concat_scene_files(scene_paths: list[Path], *, output_path: Path) -> None:
    concat_list_path = output_path.parent / f"{output_path.stem}_concat.txt"
    _write_concat_list(scene_paths, concat_list_path)
    try:
        _run_command(
            [
                "ffmpeg",
                "-y",
                "-hide_banner",
                "-loglevel",
                "error",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(concat_list_path),
                "-c",
                "copy",
                "-movflags",
                "+faststart",
                str(output_path),
            ]
        )
    finally:
        concat_list_path.unlink(missing_ok=True)


def assemble_video(
    scenes: list[dict],
    project_dir: Path,
    output_filename: str = "final_video.mp4",
    fps: int = DEFAULT_FPS,
    default_duration: float = 5.0,
    render_profile: dict[str, Any] | None = None,
) -> Path:
    """
    Assemble scenes into a final video.

    Args:
        scenes: List of scene dictionaries with image/video and audio paths
        project_dir: Project directory containing assets
        output_filename: Name of the output video file
        fps: Frames per second for the output video (overrides render_profile["fps"] when set)
        default_duration: Duration for scenes without audio
        render_profile: Optional rendering profile metadata from plan.json

    Returns:
        Path to the assembled video
    """
    project_dir = Path(project_dir)
    output_path = project_dir / output_filename
    profile = normalize_render_profile(render_profile)
    target_width = int(profile["width"])
    target_height = int(profile["height"])
    effective_fps = int(fps or profile["fps"])
    encoder = _select_video_encoder(profile)

    archived_path = _archive_existing_video(output_path, project_dir)
    if archived_path:
        print(f"Archived previous video to: {archived_path}")
    print(f"Using ffmpeg video encoder: {encoder}")

    scene_outputs: list[Path] = []

    with tempfile.TemporaryDirectory(prefix="render_scenes_", dir=project_dir) as tmp_dir:
        tmp_root = Path(tmp_dir)
        for i, scene in enumerate(scenes):
            scene_id = int(scene.get("id", i))
            target_duration, _ = _scene_target_duration(scene, default_duration)
            if target_duration <= 0:
                print(f"Skipping scene {scene_id}: resolved non-positive duration")
                continue

            scene_output = tmp_root / f"scene_{scene_id:03d}.{DEFAULT_SCENE_CODEC}"
            try:
                _render_scene_file(
                    scene,
                    output_path=scene_output,
                    target_duration=target_duration,
                    target_width=target_width,
                    target_height=target_height,
                    fps=effective_fps,
                    encoder=encoder,
                )
            except ValueError as exc:
                print(f"Skipping scene {scene_id}: {exc}")
                continue

            if not scene_output.exists() or scene_output.stat().st_size == 0:
                raise ValueError(f"Scene {scene_id} render failed: {scene_output}")
            scene_outputs.append(scene_output)

        if not scene_outputs:
            raise ValueError("No valid scenes to assemble")

        _concat_scene_files(scene_outputs, output_path=output_path)

    if not output_path.exists() or output_path.stat().st_size == 0:
        raise ValueError(f"Video assembly failed - output not created: {output_path}")

    return output_path


def preview_scene(
    scene: dict,
    project_dir: Path,
    output_filename: str | None = None,
    fps: int = DEFAULT_FPS,
    render_profile: dict[str, Any] | None = None,
) -> Path | None:
    """
    Create a preview video for a single scene.

    Args:
        scene: Scene dictionary with image/video and audio paths
        project_dir: Project directory
        output_filename: Name of preview file (auto-generated if None)
        fps: Frames per second

    Returns:
        Path to the preview video, or None if scene has no assets
    """
    project_dir = Path(project_dir)
    scene_type = str(scene.get("scene_type") or "image").strip().lower()
    if scene_type not in {"image", "video"}:
        raise ValueError(
            f"Scene {scene.get('id', 0)} uses unsupported scene_type={scene_type!r}. "
            "Supported scene types are 'image' and 'video'."
        )

    scene_id = int(scene.get("id", 0))
    if output_filename is None:
        output_filename = f"preview_scene_{scene_id:03d}.mp4"

    if scene_type == "image":
        image_path = scene.get("image_path")
        if not image_path or not Path(image_path).exists():
            return None
    else:
        video_path = scene.get("video_path")
        if not video_path or not Path(video_path).exists():
            return None

    output_path = project_dir / "previews" / output_filename
    output_path.parent.mkdir(parents=True, exist_ok=True)

    profile = normalize_render_profile(render_profile)
    encoder = _select_video_encoder(profile)
    target_duration, _ = _scene_target_duration(scene, 5.0)

    _render_scene_file(
        scene,
        output_path=output_path,
        target_duration=target_duration,
        target_width=int(profile["width"]),
        target_height=int(profile["height"]),
        fps=int(fps or profile["fps"]),
        encoder=encoder,
    )

    if not output_path.exists() or output_path.stat().st_size == 0:
        raise ValueError(f"Preview generation failed: {output_path}")

    return output_path


def get_video_duration(scenes: list[dict]) -> float:
    """
    Calculate total video duration from scenes.

    Args:
        scenes: List of scene dictionaries

    Returns:
        Total duration in seconds
    """
    total_duration = 0.0

    for scene in scenes:
        scene_type = str(scene.get("scene_type") or "image").strip().lower()
        audio_path = scene.get("audio_path")

        if scene_type == "video" and scene_uses_clip_audio(scene):
            timing = get_video_scene_timing(scene)
            total_duration += float(timing["effective_duration"] or 5.0)
        elif audio_path and Path(audio_path).exists():
            total_duration += float(get_media_duration(audio_path) or 0.0)
        elif scene_type == "video":
            timing = get_video_scene_timing(scene)
            total_duration += float(timing["effective_duration"] or 5.0)
        else:
            total_duration += 5.0

    return total_duration
