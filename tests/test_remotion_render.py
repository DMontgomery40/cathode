from __future__ import annotations

from pathlib import Path

from core.remotion_render import build_remotion_manifest, motion_scene_is_ready, scene_has_renderable_visual


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
    assert manifest["scenes"][2]["motion"]["templateId"] == "bullet_stack"
    assert manifest["totalDurationInFrames"] >= sum(scene["durationInFrames"] for scene in manifest["scenes"])
