from __future__ import annotations

from pathlib import Path

from core.remotion_render import (
    _progress_payload_from_remotion_event,
    build_remotion_manifest,
    motion_scene_is_ready,
    scene_has_renderable_visual,
)


def test_motion_scene_is_ready_from_template_only():
    scene = {
        "scene_type": "motion",
        "motion": {
            "template_id": "kinetic_title",
            "props": {
                "headline": "Prompts on prompts",
            },
        },
    }

    assert motion_scene_is_ready(scene) is True
    assert scene_has_renderable_visual(scene, render_backend="remotion") is True


def test_build_remotion_manifest_uses_api_media_urls_and_motion_templates(tmp_path):
    project_dir = tmp_path / "demo_project"
    (project_dir / "images").mkdir(parents=True)
    (project_dir / "audio").mkdir()
    (project_dir / "clips").mkdir()
    (project_dir / "images" / "scene_001.png").write_bytes(b"png")
    (project_dir / "clips" / "scene_002.mp4").write_bytes(b"mp4")
    (project_dir / "audio" / "scene_001.wav").write_bytes(b"wav")
    (project_dir / "audio" / "scene_002.wav").write_bytes(b"wav")
    (project_dir / "audio" / "scene_003.wav").write_bytes(b"wav")

    plan = {
        "meta": {
            "project_name": "demo_project",
            "render_profile": {"fps": 24, "render_backend": "remotion"},
        },
        "scenes": [
            {
                "uid": "scene_001",
                "id": 1,
                "scene_type": "image",
                "title": "Cover",
                "on_screen_text": ["One prompt", "Whole system"],
                "image_path": str(project_dir / "images" / "scene_001.png"),
                "audio_path": str(project_dir / "audio" / "scene_001.wav"),
            },
            {
                "uid": "scene_002",
                "id": 2,
                "scene_type": "video",
                "title": "App walkthrough",
                "video_path": str(project_dir / "clips" / "scene_002.mp4"),
                "audio_path": str(project_dir / "audio" / "scene_002.wav"),
                "video_trim_start": 1.5,
                "video_trim_end": 3.0,
                "video_playback_speed": 1.25,
            },
            {
                "uid": "scene_003",
                "id": 3,
                "scene_type": "motion",
                "title": "Prompt ladder",
                "audio_path": str(project_dir / "audio" / "scene_003.wav"),
                "motion": {
                    "template_id": "bullet_stack",
                    "props": {
                        "headline": "Prompts on prompts",
                        "bullets": ["Human prompt", "System prompt", "Agent prompt"],
                    },
                },
            },
        ],
    }

    manifest = build_remotion_manifest(
        project_dir=project_dir,
        plan=plan,
        output_path=project_dir / "demo_project.mp4",
        render_profile=plan["meta"]["render_profile"],
    )

    assert manifest["projectName"] == "demo_project"
    assert manifest["fps"] == 24
    assert len(manifest["scenes"]) == 3
    assert manifest["scenes"][0]["imageUrl"].endswith("/api/projects/demo_project/media/images/scene_001.png")
    assert manifest["scenes"][1]["videoUrl"].endswith("/api/projects/demo_project/media/clips/scene_002.mp4")
    assert manifest["scenes"][1]["trimBeforeFrames"] == 36
    assert manifest["scenes"][1]["trimAfterFrames"] == 72
    assert manifest["scenes"][2]["motion"]["templateId"] == "bullet_stack"
    assert manifest["totalDurationInFrames"] >= sum(scene["durationInFrames"] for scene in manifest["scenes"])


def test_ffmpeg_motion_scene_accepts_rendered_preview_clip(tmp_path):
    preview_path = tmp_path / "previews" / "motion_scene.mp4"
    preview_path.parent.mkdir(parents=True)
    preview_path.write_bytes(b"mp4")

    scene = {
        "scene_type": "motion",
        "preview_path": str(preview_path),
        "motion": {
            "template_id": "kinetic_title",
            "preview_path": str(preview_path),
        },
    }

    assert scene_has_renderable_visual(scene, render_backend="ffmpeg") is True


def test_progress_payload_maps_remotion_events_to_render_job_updates():
    status_payload = _progress_payload_from_remotion_event(
        {
            "type": "status",
            "stage": "render",
            "label": "Starting Remotion render",
            "detail": "codec=h264 hwaccel=required",
        }
    )
    progress_payload = _progress_payload_from_remotion_event(
        {
            "type": "progress",
            "stage": "encoding",
            "progress": 0.42,
            "renderedFrames": 120,
            "encodedFrames": 98,
        }
    )

    assert status_payload["progress_label"] == "Starting Remotion render"
    assert status_payload["progress_detail"] == "codec=h264 hwaccel=required"
    assert progress_payload["progress_label"] == "Encoding video"
    assert progress_payload["progress_detail"] == "rendered 120 frames, encoded 98"
    assert progress_payload["progress"] == 0.42
