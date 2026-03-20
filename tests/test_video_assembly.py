from __future__ import annotations

import subprocess
import wave
from pathlib import Path

from core.video_assembly import (
    assemble_video,
    compress_video_if_oversized,
    get_media_duration,
    get_video_scene_timing,
)


def _write_silent_wav(path: Path, duration_seconds: float, sample_rate: int = 16000) -> None:
    frame_count = int(duration_seconds * sample_rate)
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(b"\x00\x00" * frame_count)


def _write_color_video(path: Path, duration_seconds: float, size: tuple[int, int] = (640, 360)) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-f",
            "lavfi",
            "-i",
            f"color=c=0C2040:s={size[0]}x{size[1]}:d={duration_seconds}:r=24",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            str(path),
        ],
        check=True,
    )


def _write_color_video_with_audio(path: Path, duration_seconds: float, size: tuple[int, int] = (640, 360)) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-f",
            "lavfi",
            "-i",
            f"color=c=0C2040:s={size[0]}x{size[1]}:d={duration_seconds}:r=24",
            "-f",
            "lavfi",
            "-i",
            f"sine=frequency=440:duration={duration_seconds}",
            "-c:v",
            "libx264",
            "-c:a",
            "aac",
            "-pix_fmt",
            "yuv420p",
            str(path),
        ],
        check=True,
    )


def test_get_video_scene_timing_reports_effective_and_freeze_duration():
    scene = {
        "video_trim_start": 2.0,
        "video_trim_end": 8.0,
        "video_playback_speed": 2.0,
        "video_hold_last_frame": True,
    }

    timing = get_video_scene_timing(scene, source_duration=12.0, audio_duration=5.0)

    assert timing["trim_start"] == 2.0
    assert timing["trim_end"] == 8.0
    assert timing["trimmed_duration"] == 6.0
    assert timing["effective_duration"] == 3.0
    assert timing["freeze_duration"] == 2.0


def test_assemble_video_supports_video_scene_with_last_frame_hold(tmp_path):
    project_dir = tmp_path / "video_project"
    video_path = project_dir / "clips" / "scene_000.mp4"
    audio_path = project_dir / "audio" / "scene_000.wav"

    _write_color_video(video_path, duration_seconds=1.0)
    _write_silent_wav(audio_path, duration_seconds=1.6)

    output_path = assemble_video(
        [
            {
                "id": 0,
                "scene_type": "video",
                "video_path": str(video_path),
                "video_trim_start": 0.0,
                "video_trim_end": None,
                "video_playback_speed": 1.0,
                "video_hold_last_frame": True,
                "audio_path": str(audio_path),
            }
        ],
        project_dir,
        output_filename="final.mp4",
        fps=24,
    )

    output_duration = get_media_duration(output_path)

    assert output_path.exists()
    assert output_duration is not None
    assert 1.45 <= output_duration <= 1.85


def test_assemble_video_prefers_clip_audio_when_requested(tmp_path):
    project_dir = tmp_path / "clip_audio_project"
    video_path = project_dir / "clips" / "scene_000.mp4"
    audio_path = project_dir / "audio" / "scene_000.wav"

    _write_color_video_with_audio(video_path, duration_seconds=1.0)
    _write_silent_wav(audio_path, duration_seconds=1.8)

    output_path = assemble_video(
        [
            {
                "id": 0,
                "scene_type": "video",
                "video_path": str(video_path),
                "video_audio_source": "clip",
                "video_trim_start": 0.0,
                "video_trim_end": None,
                "video_playback_speed": 1.0,
                "video_hold_last_frame": True,
                "audio_path": str(audio_path),
            }
        ],
        project_dir,
        output_filename="clip-audio.mp4",
        fps=24,
    )

    output_duration = get_media_duration(output_path)

    assert output_path.exists()
    assert output_duration is not None
    assert 0.85 <= output_duration <= 1.15


def test_compress_video_if_oversized_reencodes_large_outputs(tmp_path):
    project_dir = tmp_path / "compress_project"
    video_path = project_dir / "clips" / "scene_000.mp4"
    audio_path = project_dir / "audio" / "scene_000.wav"

    _write_color_video(video_path, duration_seconds=2.4, size=(1280, 720))
    _write_silent_wav(audio_path, duration_seconds=2.4)

    output_path = assemble_video(
        [
            {
                "id": 0,
                "scene_type": "video",
                "video_path": str(video_path),
                "video_trim_start": 0.0,
                "video_trim_end": None,
                "video_playback_speed": 1.0,
                "video_hold_last_frame": True,
                "audio_path": str(audio_path),
            }
        ],
        project_dir,
        output_filename="final.mp4",
        fps=24,
        render_profile={"auto_compress_oversized_video": False},
    )
    original_size = output_path.stat().st_size

    compression = compress_video_if_oversized(
        output_path,
        render_profile={
            "compression_min_size_mb": 0.001,
            "compression_max_average_bitrate_mbps": 0.01,
            "compression_target_video_kbps": 220,
            "compression_target_audio_kbps": 64,
        },
    )

    assert compression["compressed"] is True
    assert compression["reason"] == "compressed"
    assert output_path.exists()
    assert output_path.stat().st_size < original_size
    assert compression["final_size_bytes"] == output_path.stat().st_size
    output_duration = get_media_duration(output_path)
    assert output_duration is not None
    assert 2.1 <= output_duration <= 2.7


def test_compress_video_if_oversized_skips_reasonable_outputs(tmp_path):
    project_dir = tmp_path / "skip_compress_project"
    video_path = project_dir / "clips" / "scene_000.mp4"
    audio_path = project_dir / "audio" / "scene_000.wav"

    _write_color_video(video_path, duration_seconds=1.0)
    _write_silent_wav(audio_path, duration_seconds=1.0)

    output_path = assemble_video(
        [
            {
                "id": 0,
                "scene_type": "video",
                "video_path": str(video_path),
                "video_trim_start": 0.0,
                "video_trim_end": None,
                "video_playback_speed": 1.0,
                "video_hold_last_frame": True,
                "audio_path": str(audio_path),
            }
        ],
        project_dir,
        output_filename="final.mp4",
        fps=24,
        render_profile={"auto_compress_oversized_video": False},
    )
    original_size = output_path.stat().st_size

    compression = compress_video_if_oversized(
        output_path,
        render_profile={
            "compression_min_size_mb": 500.0,
            "compression_max_average_bitrate_mbps": 100.0,
        },
    )

    assert compression["compressed"] is False
    assert compression["reason"] == "below_size_threshold"
    assert output_path.exists()
    assert output_path.stat().st_size == original_size
