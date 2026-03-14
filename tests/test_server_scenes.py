"""Integration tests for scene endpoints."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from server.app import create_app
from server.services.uploads import UploadSpec

_FAKE_PLAN: dict[str, Any] = {
    "meta": {
        "project_name": "demo",
        "brief": {"source_material": "Hello"},
        "image_profile": {"provider": "replicate", "generation_model": "qwen/qwen-image-2512"},
        "tts_profile": {"provider": "kokoro", "voice": "af_bella", "speed": 1.1},
    },
    "scenes": [
        {
            "id": 0,
            "uid": "abc1",
            "title": "Scene 1",
            "narration": "Hello world",
            "visual_prompt": "A slide about hello",
            "scene_type": "image",
            "image_path": None,
            "video_path": None,
            "audio_path": None,
            "preview_path": None,
        },
    ],
}


def _fresh_plan() -> dict[str, Any]:
    return copy.deepcopy(_FAKE_PLAN)


@pytest.fixture()
def client():
    return TestClient(create_app())


# ---------------------------------------------------------------------------
# Image upload
# ---------------------------------------------------------------------------


def test_image_upload(client, tmp_path):
    (tmp_path / "demo").mkdir()

    saved_plans: list[dict] = []

    def _mock_save(d, plan):
        saved_plans.append(plan)
        return plan

    with (
        patch("server.routers.scenes.PROJECTS_DIR", tmp_path),
        patch("server.routers.scenes.load_plan", return_value=_fresh_plan()),
        patch("server.routers.scenes.save_plan", side_effect=_mock_save),
    ):
        resp = client.post(
            "/api/projects/demo/scenes/abc1/image-upload",
            files={"file": ("test.png", b"fake-png-bytes", "image/png")},
        )

    assert resp.status_code == 200
    assert saved_plans
    scene = saved_plans[0]["scenes"][0]
    assert scene["scene_type"] == "image"
    assert "image_abc1" in scene["image_path"]
    assert scene["video_path"] is None
    assert scene["preview_path"] is None
    history = saved_plans[0]["meta"]["image_action_history"]
    assert history[0]["action"] == "upload"
    assert history[0]["status"] == "succeeded"
    assert history[0]["scene_uid"] == "abc1"
    assert history[0]["request"]["filename"] == "test.png"
    assert "image_abc1" in history[0]["result"]["image_path"]


def test_image_upload_rejects_invalid_type(client, tmp_path):
    (tmp_path / "demo").mkdir()
    saved_plans: list[dict[str, Any]] = []

    with (
        patch("server.routers.scenes.PROJECTS_DIR", tmp_path),
        patch("server.routers.scenes.load_plan", return_value=_fresh_plan()),
        patch("server.routers.scenes.save_plan", side_effect=lambda d, p: saved_plans.append(copy.deepcopy(p)) or p),
    ):
        resp = client.post(
            "/api/projects/demo/scenes/abc1/image-upload",
            files={"file": ("notes.txt", b"not-an-image", "text/plain")},
        )

    assert resp.status_code == 415
    assert "Unsupported image" in resp.json()["detail"]
    history = saved_plans[0]["meta"]["image_action_history"]
    assert history[0]["action"] == "upload"
    assert history[0]["status"] == "error"
    assert history[0]["request"]["filename"] == "notes.txt"
    assert "Unsupported image" in history[0]["error"]


def test_image_upload_scene_not_found(client, tmp_path):
    (tmp_path / "demo").mkdir()

    with (
        patch("server.routers.scenes.PROJECTS_DIR", tmp_path),
        patch("server.routers.scenes.load_plan", return_value=_fresh_plan()),
    ):
        resp = client.post(
            "/api/projects/demo/scenes/nonexistent/image-upload",
            files={"file": ("test.png", b"data", "image/png")},
        )
    assert resp.status_code == 404


def test_image_upload_rejects_wrong_content_type(client, tmp_path):
    (tmp_path / "demo").mkdir()

    with (
        patch("server.routers.scenes.PROJECTS_DIR", tmp_path),
        patch("server.routers.scenes.load_plan", return_value=_fresh_plan()),
    ):
        resp = client.post(
            "/api/projects/demo/scenes/abc1/image-upload",
            files={"file": ("test.txt", b"plain-text", "text/plain")},
        )

    assert resp.status_code == 415


def test_image_upload_rejects_oversize_file(client, tmp_path):
    (tmp_path / "demo").mkdir()
    tiny_spec = UploadSpec(
        label="image",
        max_bytes=4,
        allowed_extensions=(".png",),
        allowed_content_types=("image/png",),
    )

    with (
        patch("server.routers.scenes.PROJECTS_DIR", tmp_path),
        patch("server.routers.scenes.load_plan", return_value=_fresh_plan()),
        patch("server.routers.scenes.IMAGE_UPLOAD_SPEC", tiny_spec),
    ):
        resp = client.post(
            "/api/projects/demo/scenes/abc1/image-upload",
            files={"file": ("test.png", b"\x89PNG\r\n\x1a\n" + b"\x00" * 10, "image/png")},
        )

    assert resp.status_code == 413


# ---------------------------------------------------------------------------
# Video upload
# ---------------------------------------------------------------------------


def test_video_upload(client, tmp_path):
    (tmp_path / "demo").mkdir()

    saved_plans: list[dict] = []

    def _mock_save(d, plan):
        saved_plans.append(plan)
        return plan

    with (
        patch("server.routers.scenes.PROJECTS_DIR", tmp_path),
        patch("server.routers.scenes.load_plan", return_value=_fresh_plan()),
        patch("server.routers.scenes.save_plan", side_effect=_mock_save),
    ):
        resp = client.post(
            "/api/projects/demo/scenes/abc1/video-upload",
            files={"file": ("clip.mp4", b"fake-video-bytes", "video/mp4")},
        )

    assert resp.status_code == 200
    assert saved_plans
    scene = saved_plans[0]["scenes"][0]
    assert scene["scene_type"] == "video"
    assert "clip_abc1" in scene["video_path"]
    assert scene["image_path"] is None
    assert scene["preview_path"] is None
    assert scene["video_audio_source"] == "narration"


def test_video_upload_rejects_wrong_content_type(client, tmp_path):
    (tmp_path / "demo").mkdir()

    with (
        patch("server.routers.scenes.PROJECTS_DIR", tmp_path),
        patch("server.routers.scenes.load_plan", return_value=_fresh_plan()),
    ):
        resp = client.post(
            "/api/projects/demo/scenes/abc1/video-upload",
            files={"file": ("test.png", b"fake-png-bytes", "image/png")},
        )

    assert resp.status_code == 415
    assert "Unsupported video" in resp.json()["detail"]


def test_video_upload_rejects_invalid_type(client, tmp_path):
    (tmp_path / "demo").mkdir()

    with (
        patch("server.routers.scenes.PROJECTS_DIR", tmp_path),
        patch("server.routers.scenes.load_plan", return_value=_fresh_plan()),
    ):
        resp = client.post(
            "/api/projects/demo/scenes/abc1/video-upload",
            files={"file": ("notes.txt", b"not-a-video", "text/plain")},
        )

    assert resp.status_code == 415
    assert "Unsupported video" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# Image generate
# ---------------------------------------------------------------------------


@patch("server.routers.scenes.edit_image")
def test_image_edit_uses_profile_model(mock_edit, client, tmp_path):
    project_dir = tmp_path / "demo"
    project_dir.mkdir()
    source = project_dir / "images" / "scene_000.png"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 32)

    plan = _fresh_plan()
    plan["meta"]["image_profile"] = {
        "provider": "replicate",
        "generation_model": "qwen/qwen-image-2512",
        "edit_model": "qwen/qwen-image-edit-2511",
    }
    plan["scenes"][0]["image_path"] = str(source)
    plan["scenes"][0]["preview_path"] = str(project_dir / "previews" / "existing.mp4")

    edited = project_dir / "images" / "image_abc1_edited.png"
    mock_edit.return_value = edited

    with (
        patch("server.routers.scenes.PROJECTS_DIR", tmp_path),
        patch("server.routers.scenes.load_plan", return_value=plan),
        patch("server.routers.scenes.save_plan", side_effect=lambda d, p: p),
    ):
        resp = client.post(
            "/api/projects/demo/scenes/abc1/image-edit",
            json={"feedback": "Make the image more cinematic"},
        )

    assert resp.status_code == 200
    scene = resp.json()["scenes"][0]
    assert scene["image_path"] == str(edited)
    assert scene["preview_path"] is None
    assert scene["scene_type"] == "image"
    history = resp.json()["meta"]["image_action_history"]
    assert history[0]["action"] == "edit"
    assert history[0]["status"] == "succeeded"
    assert history[0]["request"]["feedback"] == "Make the image more cinematic"
    assert history[0]["result"]["image_path"] == str(edited)
    kwargs = mock_edit.call_args.kwargs
    assert kwargs["model"] == "qwen/qwen-image-edit-2511"


def test_image_edit_requires_existing_image(client, tmp_path):
    (tmp_path / "demo").mkdir()
    saved_plans: list[dict[str, Any]] = []

    with (
        patch("server.routers.scenes.PROJECTS_DIR", tmp_path),
        patch("server.routers.scenes.load_plan", return_value=_fresh_plan()),
        patch("server.routers.scenes.save_plan", side_effect=lambda d, p: saved_plans.append(copy.deepcopy(p)) or p),
    ):
        resp = client.post(
            "/api/projects/demo/scenes/abc1/image-edit",
            json={"feedback": "Make the image more cinematic"},
        )

    assert resp.status_code == 400
    assert "must have an image" in resp.json()["detail"].lower()
    history = saved_plans[0]["meta"]["image_action_history"]
    assert history[0]["action"] == "edit"
    assert history[0]["status"] == "error"
    assert "must have an image" in history[0]["error"].lower()


@patch("server.routers.scenes.edit_image")
def test_image_edit_heals_same_project_absolute_path(mock_edit, client, tmp_path):
    project_dir = tmp_path / "demo"
    images_dir = project_dir / "images"
    images_dir.mkdir(parents=True)
    real_image = images_dir / "scene_000.png"
    real_image.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 32)

    old_root = Path("/tmp/old_checkout/projects/demo")
    raw_plan = {
        "meta": {
            "project_name": "demo",
            "image_profile": {
                "provider": "replicate",
                "generation_model": "qwen/qwen-image-2512",
                "edit_model": "qwen/qwen-image-edit-2511",
            },
        },
        "scenes": [
            {
                "uid": "abc1",
                "title": "Scene 1",
                "narration": "Hello world",
                "visual_prompt": "A slide about hello",
                "scene_type": "image",
                "image_path": str(old_root / "images" / "scene_000.png"),
            }
        ],
    }
    (project_dir / "plan.json").write_text(json.dumps(raw_plan))

    edited = images_dir / "image_abc1_edited.png"
    edited.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 32)
    mock_edit.return_value = edited

    with patch("server.routers.scenes.PROJECTS_DIR", tmp_path):
        resp = client.post(
            "/api/projects/demo/scenes/abc1/image-edit",
            json={"feedback": "Make the image more cinematic"},
        )

    assert resp.status_code == 200
    scene = resp.json()["scenes"][0]
    assert scene["image_path"] == str(edited.resolve())
    assert mock_edit.call_args.args[1] == str(real_image.resolve())


@patch("server.routers.scenes.generate_scene_image")
def test_image_generate(mock_gen, client, tmp_path):
    (tmp_path / "demo").mkdir()
    mock_gen.return_value = tmp_path / "demo" / "images" / "scene_000.png"
    plan = _fresh_plan()
    plan["scenes"][0]["scene_type"] = "video"
    plan["scenes"][0]["video_path"] = "projects/demo/clips/existing.mp4"
    plan["scenes"][0]["preview_path"] = "projects/demo/previews/existing.mp4"

    with (
        patch("server.routers.scenes.PROJECTS_DIR", tmp_path),
        patch("server.routers.scenes.load_plan", return_value=plan),
        patch("server.routers.scenes.save_plan", side_effect=lambda d, p: p),
        patch(
            "server.routers.scenes.resolve_image_profile",
            return_value={"provider": "replicate", "generation_model": "qwen/qwen-image-2512"},
        ),
    ):
        resp = client.post("/api/projects/demo/scenes/abc1/image-generate", json={})

    assert resp.status_code == 200
    mock_gen.assert_called_once()
    body = resp.json()
    scene = body["scenes"][0]
    assert scene["scene_type"] == "image"
    assert scene["video_path"] is None
    assert scene["preview_path"] is None
    history = body["meta"]["image_action_history"]
    assert history[0]["action"] == "generate"
    assert history[0]["status"] == "succeeded"
    assert history[0]["request"] == {"provider": "replicate", "model": "qwen/qwen-image-2512"}


@patch(
    "server.routers.scenes.generate_scene_image",
    side_effect=ValueError("No visual_prompt"),
)
def test_image_generate_error(mock_gen, client, tmp_path):
    (tmp_path / "demo").mkdir()
    saved_plans: list[dict[str, Any]] = []

    with (
        patch("server.routers.scenes.PROJECTS_DIR", tmp_path),
        patch("server.routers.scenes.load_plan", return_value=_fresh_plan()),
        patch("server.routers.scenes.save_plan", side_effect=lambda d, p: saved_plans.append(copy.deepcopy(p)) or p),
        patch(
            "server.routers.scenes.resolve_image_profile",
            return_value={"provider": "replicate", "generation_model": "m"},
        ),
    ):
        resp = client.post("/api/projects/demo/scenes/abc1/image-generate", json={})

    assert resp.status_code == 400
    history = saved_plans[0]["meta"]["image_action_history"]
    assert history[0]["action"] == "generate"
    assert history[0]["status"] == "error"
    assert history[0]["request"] == {"provider": "replicate", "model": "m"}
    assert history[0]["error"] == "No visual_prompt"


# ---------------------------------------------------------------------------
# Video generate
# ---------------------------------------------------------------------------


@patch("server.routers.scenes.generate_scene_video_result")
def test_video_generate(mock_gen, client, tmp_path):
    project_dir = tmp_path / "demo"
    project_dir.mkdir()
    mock_gen.return_value = {
        "path": project_dir / "clips" / "scene_000.mp4",
        "provider": "local",
        "model": "wan/wan-2.1",
        "generate_audio": False,
        "quality_mode": "standard",
        "duration_seconds": 5.0,
    }
    plan = _fresh_plan()
    plan["scenes"][0]["image_path"] = "projects/demo/images/existing.png"
    plan["scenes"][0]["preview_path"] = "projects/demo/previews/existing.mp4"

    with (
        patch("server.routers.scenes.PROJECTS_DIR", tmp_path),
        patch("server.routers.scenes.load_plan", return_value=plan),
        patch("server.routers.scenes.save_plan", side_effect=lambda d, p: p),
        patch(
            "server.routers.scenes.resolve_video_profile",
            return_value={
                "provider": "local",
                "generation_model": "wan/wan-2.1",
                "model_selection_mode": "automatic",
            },
        ),
    ):
        resp = client.post("/api/projects/demo/scenes/abc1/video-generate", json={})

    assert resp.status_code == 200
    mock_gen.assert_called_once()
    scene = resp.json()["scenes"][0]
    assert scene["scene_type"] == "video"
    assert scene["image_path"] is None
    assert scene["preview_path"] is None
    assert scene["video_path"] == str(project_dir / "clips" / "scene_000.mp4")
    assert scene["video_audio_source"] == "narration"


@patch("server.routers.scenes.generate_scene_video_result")
def test_video_generate_replicate_defaults_scene_to_clip_audio(mock_gen, client, tmp_path):
    project_dir = tmp_path / "demo"
    project_dir.mkdir()
    mock_gen.return_value = {
        "path": project_dir / "clips" / "scene_000.mp4",
        "provider": "replicate",
        "model": "kwaivgi/kling-avatar-v2",
        "generate_audio": True,
        "quality_mode": "standard",
        "duration_seconds": 5.0,
    }

    with (
        patch("server.routers.scenes.PROJECTS_DIR", tmp_path),
        patch("server.routers.scenes.load_plan", return_value=_fresh_plan()),
        patch("server.routers.scenes.save_plan", side_effect=lambda d, p: p),
        patch(
            "server.routers.scenes.resolve_video_profile",
            return_value={
                "provider": "replicate",
                "generation_model": "wan/wan-2.1",
                "model_selection_mode": "automatic",
                "quality_mode": "standard",
                "generate_audio": True,
            },
        ),
    ):
        resp = client.post("/api/projects/demo/scenes/abc1/video-generate", json={})

    assert resp.status_code == 200
    kwargs = mock_gen.call_args.kwargs
    assert kwargs["provider"] == "replicate"
    assert kwargs["model"] == "wan/wan-2.1"
    assert kwargs["model_selection_mode"] == "automatic"
    assert kwargs["quality_mode"] == "standard"
    assert kwargs["generate_audio"] is True
    scene = resp.json()["scenes"][0]
    assert scene["video_audio_source"] == "clip"
    assert scene["audio_path"] is None


@patch("server.routers.scenes.generate_scene_video_result")
def test_video_generate_accepts_model_selection_mode_override(mock_gen, client, tmp_path):
    project_dir = tmp_path / "demo"
    project_dir.mkdir()
    mock_gen.return_value = {
        "path": project_dir / "clips" / "scene_000.mp4",
        "provider": "replicate",
        "model": "wan/wan-2.1",
        "generate_audio": True,
        "quality_mode": "standard",
        "duration_seconds": 5.0,
    }

    with (
        patch("server.routers.scenes.PROJECTS_DIR", tmp_path),
        patch("server.routers.scenes.load_plan", return_value=_fresh_plan()),
        patch("server.routers.scenes.save_plan", side_effect=lambda d, p: p),
        patch(
            "server.routers.scenes.resolve_video_profile",
            return_value={
                "provider": "replicate",
                "generation_model": "",
                "model_selection_mode": "automatic",
                "quality_mode": "standard",
                "generate_audio": True,
            },
        ),
    ):
        resp = client.post(
            "/api/projects/demo/scenes/abc1/video-generate",
            json={"model_selection_mode": "advanced", "model": "wan/wan-2.1"},
        )

    assert resp.status_code == 200
    kwargs = mock_gen.call_args.kwargs
    assert kwargs["model_selection_mode"] == "advanced"
    assert kwargs["model"] == "wan/wan-2.1"


@patch(
    "server.routers.scenes.generate_scene_video_result",
    side_effect=ValueError("Local video generation is not configured."),
)
def test_video_generate_error(mock_gen, client, tmp_path):
    (tmp_path / "demo").mkdir()

    with (
        patch("server.routers.scenes.PROJECTS_DIR", tmp_path),
        patch("server.routers.scenes.load_plan", return_value=_fresh_plan()),
        patch(
            "server.routers.scenes.resolve_video_profile",
            return_value={"provider": "manual", "generation_model": ""},
        ),
    ):
        resp = client.post("/api/projects/demo/scenes/abc1/video-generate", json={})

    assert resp.status_code == 400
    assert "Local video generation is not configured." in resp.json()["detail"]


# ---------------------------------------------------------------------------
# Audio generate
# ---------------------------------------------------------------------------


@patch("server.routers.scenes.generate_scene_audio_result")
def test_audio_generate(mock_gen, client, tmp_path):
    (tmp_path / "demo").mkdir()
    mock_gen.return_value = {
        "path": tmp_path / "demo" / "audio" / "scene_000.wav",
        "provider": "kokoro",
        "model": "kokoro-local",
    }

    with (
        patch("server.routers.scenes.PROJECTS_DIR", tmp_path),
        patch("server.routers.scenes.load_plan", return_value=_fresh_plan()),
        patch("server.routers.scenes.save_plan", side_effect=lambda d, p: p),
        patch(
            "server.routers.scenes.resolve_tts_profile",
            return_value={"provider": "kokoro", "voice": "af_bella", "speed": 1.1},
        ),
    ):
        resp = client.post(
            "/api/projects/demo/scenes/abc1/audio-generate",
            json={"tts_provider": "kokoro"},
        )

    assert resp.status_code == 200
    mock_gen.assert_called_once()


@patch("server.routers.scenes.build_remotion_manifest", return_value={"scenes": [{"uid": "abc1"}], "fps": 24})
def test_scene_remotion_manifest_endpoint(mock_manifest, client, tmp_path):
    (tmp_path / "demo").mkdir()

    with (
        patch("server.routers.scenes.PROJECTS_DIR", tmp_path),
        patch("server.routers.scenes.load_plan", return_value=_fresh_plan()),
    ):
        resp = client.get("/api/projects/demo/scenes/abc1/remotion-manifest")

    assert resp.status_code == 200
    assert resp.json()["fps"] == 24
    mock_manifest.assert_called_once()


# ---------------------------------------------------------------------------
# Prompt refine
# ---------------------------------------------------------------------------


@patch("server.routers.scenes.refine_prompt_with_metadata", return_value=("improved prompt", {"actual": None, "preflight": None}))
@patch("server.routers.scenes.choose_llm_provider", return_value="openai")
def test_prompt_refine(mock_llm, mock_refine, client, tmp_path):
    (tmp_path / "demo").mkdir()
    saved_plans: list[dict] = []

    with (
        patch("server.routers.scenes.PROJECTS_DIR", tmp_path),
        patch("server.routers.scenes.load_plan", return_value=_fresh_plan()),
        patch("server.routers.scenes.save_plan", side_effect=lambda d, p: saved_plans.append(copy.deepcopy(p)) or p),
    ):
        resp = client.post(
            "/api/projects/demo/scenes/abc1/prompt-refine",
            json={"feedback": "make it brighter"},
        )

    assert resp.status_code == 200
    assert saved_plans
    assert saved_plans[0]["scenes"][0]["visual_prompt"] == "improved prompt"
    assert resp.json()["scenes"][0]["visual_prompt"] == "improved prompt"


def test_prompt_refine_missing_feedback(client, tmp_path):
    (tmp_path / "demo").mkdir()

    with patch("server.routers.scenes.PROJECTS_DIR", tmp_path):
        resp = client.post(
            "/api/projects/demo/scenes/abc1/prompt-refine",
            json={},
        )
    assert resp.status_code == 422  # validation error


# ---------------------------------------------------------------------------
# Narration refine
# ---------------------------------------------------------------------------


@patch("server.routers.scenes.refine_narration_with_metadata", return_value=("improved narration", {"actual": None, "preflight": None}))
@patch("server.routers.scenes.choose_llm_provider", return_value="openai")
def test_narration_refine(mock_llm, mock_refine, client, tmp_path):
    (tmp_path / "demo").mkdir()
    saved_plans: list[dict] = []

    with (
        patch("server.routers.scenes.PROJECTS_DIR", tmp_path),
        patch("server.routers.scenes.load_plan", return_value=_fresh_plan()),
        patch("server.routers.scenes.save_plan", side_effect=lambda d, p: saved_plans.append(copy.deepcopy(p)) or p),
    ):
        resp = client.post(
            "/api/projects/demo/scenes/abc1/narration-refine",
            json={"feedback": "shorter please"},
        )

    assert resp.status_code == 200
    assert saved_plans
    assert saved_plans[0]["scenes"][0]["narration"] == "improved narration"
    assert resp.json()["scenes"][0]["narration"] == "improved narration"


# ---------------------------------------------------------------------------
# Preview
# ---------------------------------------------------------------------------


@patch(
    "server.routers.scenes.preview_scene",
    return_value=Path("/tmp/previews/preview_scene_000.mp4"),
)
def test_preview_scene(mock_preview, client, tmp_path):
    (tmp_path / "demo").mkdir()

    with (
        patch("server.routers.scenes.PROJECTS_DIR", tmp_path),
        patch("server.routers.scenes.load_plan", return_value=_fresh_plan()),
        patch("server.routers.scenes.save_plan", side_effect=lambda d, p: p),
    ):
        resp = client.post("/api/projects/demo/scenes/abc1/preview")

    assert resp.status_code == 200
    mock_preview.assert_called_once()


@patch(
    "server.routers.scenes.render_manifest_with_remotion",
    return_value=Path("/tmp/previews/preview_motion_scene.mp4"),
)
@patch(
    "server.routers.scenes.build_remotion_manifest",
    return_value={"outputPath": "/tmp/previews/preview_motion_scene.mp4"},
)
def test_motion_preview_runs_in_threadpool(mock_manifest, mock_render, client, tmp_path):
    (tmp_path / "demo").mkdir()
    plan = _fresh_plan()
    plan["meta"]["render_profile"] = {"render_backend": "remotion"}
    plan["scenes"][0]["scene_type"] = "motion"
    plan["scenes"][0]["motion"] = {
        "template_id": "kinetic_title",
        "props": {"headline": "Prompts on prompts"},
    }
    plan["scenes"][0]["composition"] = {
        "family": "kinetic_title",
        "mode": "native",
        "props": {"headline": "Prompts on prompts"},
    }

    captured: dict[str, object] = {}

    async def fake_run_in_threadpool(func, **kwargs):
        captured["func_name"] = getattr(func, "__name__", "")
        return func(**kwargs)

    with (
        patch("server.routers.scenes.PROJECTS_DIR", tmp_path),
        patch("server.routers.scenes.load_plan", return_value=plan),
        patch("server.routers.scenes.run_in_threadpool", side_effect=fake_run_in_threadpool),
        patch("server.routers.scenes.save_plan", side_effect=lambda d, p: p),
    ):
        resp = client.post("/api/projects/demo/scenes/abc1/preview")

    assert resp.status_code == 200
    assert captured["func_name"] == "_render_preview_asset"
    saved_scene = resp.json()["scenes"][0]
    assert saved_scene["preview_path"] == "/tmp/previews/preview_motion_scene.mp4"
    assert saved_scene["motion"]["preview_path"] == "/tmp/previews/preview_motion_scene.mp4"
    assert saved_scene["composition"]["preview_path"] == "/tmp/previews/preview_motion_scene.mp4"


def test_preview_project_not_found(client, tmp_path):
    with patch("server.routers.scenes.PROJECTS_DIR", tmp_path):
        resp = client.post("/api/projects/nope/scenes/abc1/preview")
    assert resp.status_code == 404
