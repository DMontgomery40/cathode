"""Video assembly using MoviePy."""

from pathlib import Path
from typing import Any

from moviepy import (
    AudioFileClip,
    ImageClip,
    VideoFileClip,
    concatenate_videoclips,
)

# Target dimensions for video output (must match image_gen.py)
TARGET_WIDTH = 1664
TARGET_HEIGHT = 928


def normalize_render_profile(render_profile: dict[str, Any] | None = None) -> dict[str, Any]:
    """Normalize and validate render profile configuration."""
    profile = {
        "version": "v1",
        "aspect_ratio": "16:9",
        "width": TARGET_WIDTH,
        "height": TARGET_HEIGHT,
        "fps": 24,
        "scene_types": ["image", "video"],
    }
    if isinstance(render_profile, dict):
        profile.update(render_profile)

    profile["aspect_ratio"] = str(profile.get("aspect_ratio") or "16:9")
    profile["width"] = int(profile.get("width") or TARGET_WIDTH)
    profile["height"] = int(profile.get("height") or TARGET_HEIGHT)
    profile["fps"] = int(profile.get("fps") or 24)

    scene_types = profile.get("scene_types")
    if not isinstance(scene_types, list) or not scene_types:
        scene_types = ["image", "video"]
    profile["scene_types"] = [str(item).strip().lower() for item in scene_types if str(item).strip()]
    if not profile["scene_types"]:
        profile["scene_types"] = ["image", "video"]

    if profile["aspect_ratio"] != "16:9":
        raise ValueError(f"Unsupported aspect_ratio={profile['aspect_ratio']!r}. v1 only supports 16:9.")
    if profile["width"] != TARGET_WIDTH or profile["height"] != TARGET_HEIGHT:
        raise ValueError(
            "Unsupported render resolution. v1 only supports 1664x928; "
            f"got {profile['width']}x{profile['height']}."
        )

    return profile


def _ensure_dimensions(
    clip,
    scene_id: int = 0,
    target_width: int = TARGET_WIDTH,
    target_height: int = TARGET_HEIGHT,
):
    """
    Resize clip to target dimensions if mismatched.

    Prevents video assembly failures from dimension inconsistencies
    (e.g., edited images returning different sizes).
    """
    w, h = clip.size
    if w != target_width or h != target_height:
        print(f"  Scene {scene_id}: resizing {w}x{h} -> {target_width}x{target_height}")
        return clip.resized((target_width, target_height))
    return clip


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


def get_media_duration(path: str | Path) -> float | None:
    """Return duration in seconds for an audio or video asset."""
    media_path = Path(path)
    if not media_path.exists():
        return None

    suffix = media_path.suffix.lower()
    if suffix in {".wav", ".mp3", ".m4a", ".aac", ".flac", ".ogg"}:
        clip = AudioFileClip(str(media_path))
        try:
            return float(clip.duration or 0.0)
        finally:
            clip.close()

    clip = VideoFileClip(str(media_path))
    try:
        return float(clip.duration or 0.0)
    finally:
        clip.close()


def get_video_scene_timing(
    scene: dict[str, Any],
    *,
    source_duration: float | None = None,
    audio_duration: float | None = None,
) -> dict[str, Any]:
    """Normalize video-scene timing metadata and compute effective durations."""
    video_path = scene.get("video_path")
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


def _build_image_scene_clip(
    scene: dict[str, Any],
    *,
    scene_id: int,
    target_duration: float,
    target_width: int,
    target_height: int,
):
    image_path = scene.get("image_path")
    if not image_path or not Path(image_path).exists():
        raise ValueError(f"Scene {scene_id}: no image found at {image_path!r}")

    clip = ImageClip(str(image_path))
    clip = _ensure_dimensions(
        clip,
        scene_id,
        target_width=target_width,
        target_height=target_height,
    )
    return clip.with_duration(target_duration)


def _build_video_scene_clip(
    scene: dict[str, Any],
    *,
    scene_id: int,
    target_duration: float | None,
    target_width: int,
    target_height: int,
    fps: int,
):
    video_path = scene.get("video_path")
    if not video_path or not Path(video_path).exists():
        raise ValueError(f"Scene {scene_id}: no video clip found at {video_path!r}")

    clip = VideoFileClip(str(video_path)).without_audio()
    timing = get_video_scene_timing(scene, source_duration=float(clip.duration or 0.0), audio_duration=target_duration)

    trim_start = float(timing["trim_start"])
    trim_end = timing["trim_end"]
    source_duration = float(clip.duration or 0.0)
    if trim_start > 0 or (trim_end is not None and trim_end < source_duration):
        clip = clip.subclipped(start_time=trim_start, end_time=trim_end)

    playback_speed = float(timing["playback_speed"])
    if abs(playback_speed - 1.0) > 1e-6:
        clip = clip.with_speed_scaled(factor=playback_speed)

    clip = _ensure_dimensions(
        clip,
        scene_id,
        target_width=target_width,
        target_height=target_height,
    )

    if target_duration is None:
        return clip

    current_duration = float(clip.duration or 0.0)
    if current_duration > target_duration + 0.05:
        clip = clip.subclipped(0, target_duration)
        clip = _ensure_dimensions(
            clip,
            scene_id,
            target_width=target_width,
            target_height=target_height,
        )
        return clip

    extra = target_duration - current_duration
    if extra <= 0.05:
        return clip

    if not bool(timing["hold_last_frame"]):
        raise ValueError(
            f"Scene {scene_id}: narration is {extra:.1f}s longer than the configured video clip. "
            "Extend the clip or enable last-frame hold."
        )

    frame_t = max(current_duration - (1.0 / max(fps, 1)), 0.0)
    freeze_frame = clip.get_frame(frame_t)
    freeze_clip = ImageClip(freeze_frame).with_duration(extra)
    freeze_clip = _ensure_dimensions(
        freeze_clip,
        scene_id,
        target_width=target_width,
        target_height=target_height,
    )
    return concatenate_videoclips([clip, freeze_clip], method="compose")


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

    # Prefer the project folder name as the version base.
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


def assemble_video(
    scenes: list[dict],
    project_dir: Path,
    output_filename: str = "final_video.mp4",
    fps: int = 24,
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

    archived_path = _archive_existing_video(output_path, project_dir)
    if archived_path:
        print(f"Archived previous video to: {archived_path}")

    clips = []
    audio_clips = []  # Track for cleanup

    try:
        for i, scene in enumerate(scenes):
            scene_id = int(scene.get("id", i))
            scene_type = str(scene.get("scene_type") or "image").strip().lower()
            if scene_type not in {"image", "video"}:
                raise ValueError(
                    f"Scene {scene_id} uses unsupported scene_type={scene_type!r}. "
                    "Supported scene types are 'image' and 'video'."
                )

            audio_path = scene.get("audio_path")
            if audio_path and Path(audio_path).exists():
                audio_clip = AudioFileClip(str(audio_path))
                audio_clips.append(audio_clip)
                target_duration = float(audio_clip.duration or default_duration)
            else:
                audio_clip = None
                if scene_type == "video":
                    timing = get_video_scene_timing(scene)
                    target_duration = float(timing["effective_duration"] or default_duration)
                else:
                    target_duration = default_duration

            try:
                if scene_type == "image":
                    visual_clip = _build_image_scene_clip(
                        scene,
                        scene_id=scene_id,
                        target_duration=target_duration,
                        target_width=target_width,
                        target_height=target_height,
                    )
                else:
                    visual_clip = _build_video_scene_clip(
                        scene,
                        scene_id=scene_id,
                        target_duration=target_duration,
                        target_width=target_width,
                        target_height=target_height,
                        fps=effective_fps,
                    )
            except ValueError as exc:
                print(f"Skipping scene {scene_id}: {exc}")
                continue

            if audio_clip is not None:
                visual_clip = visual_clip.with_audio(audio_clip)

            clips.append(visual_clip)

        if not clips:
            raise ValueError("No valid scenes to assemble")

        # Concatenate all clips (hard cuts, no transitions)
        final_video = concatenate_videoclips(clips, method="compose")

        # Write output video using CPU encoder (faster for slideshow content)
        final_video.write_videofile(
            str(output_path),
            fps=effective_fps,
            codec="libx264",
            audio_codec="aac",
            temp_audiofile=str(project_dir / "temp_audio.m4a"),
            remove_temp=True,
            logger="bar",
            ffmpeg_params=[
                "-preset", "ultrafast",
                "-crf", "35",
                "-pix_fmt", "yuv420p",
                "-movflags", "+faststart",
            ],
        )

    finally:
        for clip in clips:
            clip.close()
        for audio_clip in audio_clips:
            audio_clip.close()
        if "final_video" in locals():
            final_video.close()

    if not output_path.exists() or output_path.stat().st_size == 0:
        raise ValueError(f"Video assembly failed - output not created: {output_path}")

    return output_path


def preview_scene(
    scene: dict,
    project_dir: Path,
    output_filename: str | None = None,
    fps: int = 24,
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

    output_path = project_dir / "previews" / output_filename
    output_path.parent.mkdir(parents=True, exist_ok=True)

    visual_clip = None
    audio_clip = None
    profile = normalize_render_profile(render_profile)

    try:
        audio_path = scene.get("audio_path")
        if audio_path and Path(audio_path).exists():
            audio_clip = AudioFileClip(str(audio_path))
            target_duration = float(audio_clip.duration or 5.0)
        else:
            audio_clip = None
            if scene_type == "video":
                timing = get_video_scene_timing(scene)
                target_duration = float(timing["effective_duration"] or 5.0)
            else:
                target_duration = 5.0

        if scene_type == "image":
            image_path = scene.get("image_path")
            if not image_path or not Path(image_path).exists():
                return None
            visual_clip = _build_image_scene_clip(
                scene,
                scene_id=scene_id,
                target_duration=target_duration,
                target_width=int(profile["width"]),
                target_height=int(profile["height"]),
            )
        else:
            video_path = scene.get("video_path")
            if not video_path or not Path(video_path).exists():
                return None
            visual_clip = _build_video_scene_clip(
                scene,
                scene_id=scene_id,
                target_duration=target_duration,
                target_width=int(profile["width"]),
                target_height=int(profile["height"]),
                fps=int(fps or profile["fps"]),
            )

        if audio_clip is not None:
            visual_clip = visual_clip.with_audio(audio_clip)

        visual_clip.write_videofile(
            str(output_path),
            fps=int(fps or profile["fps"]),
            codec="libx264",
            audio_codec="aac",
            ffmpeg_params=[
                "-preset", "ultrafast",
                "-crf", "35",
                "-pix_fmt", "yuv420p",
                "-movflags", "+faststart",
            ],
            logger=None,
        )

    finally:
        if visual_clip:
            visual_clip.close()
        if audio_clip:
            audio_clip.close()

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

        if audio_path and Path(audio_path).exists():
            audio_clip = AudioFileClip(str(audio_path))
            try:
                total_duration += audio_clip.duration
            finally:
                audio_clip.close()
        elif scene_type == "video":
            timing = get_video_scene_timing(scene)
            total_duration += float(timing["effective_duration"] or 5.0)
        else:
            total_duration += 5.0

    return total_duration
