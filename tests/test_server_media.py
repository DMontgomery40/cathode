"""Integration tests for media serving, project detail/delete, settings, and style refs."""

from __future__ import annotations

import copy
from typing import Any
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from server.app import create_app
from server.services.uploads import UploadSpec


@pytest.fixture()
def client():
    return TestClient(create_app())


# ---------------------------------------------------------------------------
# GET /api/projects/{project}/media/{path}
# ---------------------------------------------------------------------------


def test_serve_media_image(client, tmp_path):
    images_dir = tmp_path / "demo" / "images"
    images_dir.mkdir(parents=True)
    img = images_dir / "scene_000.png"
    img.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)

    with patch("server.routers.media.PROJECTS_DIR", tmp_path):
        resp = client.get("/api/projects/demo/media/images/scene_000.png")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "image/png"


def test_serve_media_audio(client, tmp_path):
    audio_dir = tmp_path / "demo" / "audio"
    audio_dir.mkdir(parents=True)
    wav = audio_dir / "scene_000.wav"
    wav.write_bytes(b"RIFF" + b"\x00" * 100)

    with patch("server.routers.media.PROJECTS_DIR", tmp_path):
        resp = client.get("/api/projects/demo/media/audio/scene_000.wav")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "audio/wav"


def test_serve_media_video(client, tmp_path):
    (tmp_path / "demo").mkdir()
    mp4 = tmp_path / "demo" / "final.mp4"
    mp4.write_bytes(b"\x00\x00\x00\x20ftypmp42" + b"\x00" * 50)

    with patch("server.routers.media.PROJECTS_DIR", tmp_path):
        resp = client.get("/api/projects/demo/media/final.mp4")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "video/mp4"


def test_serve_media_404(client, tmp_path):
    (tmp_path / "demo").mkdir()
    with patch("server.routers.media.PROJECTS_DIR", tmp_path):
        resp = client.get("/api/projects/demo/media/images/nope.png")
    assert resp.status_code == 404


def test_serve_media_project_not_found(client, tmp_path):
    with patch("server.routers.media.PROJECTS_DIR", tmp_path):
        resp = client.get("/api/projects/nope/media/images/x.png")
    assert resp.status_code == 404


def test_serve_media_path_traversal_rejected(client, tmp_path):
    """Paths containing '..' are rejected with 400."""
    (tmp_path / "demo").mkdir()
    with patch("server.routers.media.PROJECTS_DIR", tmp_path):
        # The HTTP client normalizes ../.. so we test the raw path segment check
        resp = client.get("/api/projects/demo/media/images/..%2F..%2Fetc%2Fpasswd")
    # Should be 400 or 404 -- definitely not 200
    assert resp.status_code in (400, 404)


# ---------------------------------------------------------------------------
# GET /api/projects/{project} (detail)
# ---------------------------------------------------------------------------


_FAKE_PLAN = {"meta": {"project_name": "demo"}, "scenes": [{"id": 0}]}
_FAKE_ARTIFACTS = {"images": [], "audio": [], "clips": [], "videos": []}
_FAKE_JOBS: list[dict[str, Any]] = []


@patch("server.routers.projects.list_project_jobs", return_value=_FAKE_JOBS)
@patch("server.routers.projects.collect_project_artifacts", return_value=_FAKE_ARTIFACTS)
@patch("server.routers.projects.load_plan", return_value=_FAKE_PLAN)
def test_get_project_detail(mock_plan, mock_artifacts, mock_jobs, client, tmp_path):
    (tmp_path / "demo").mkdir()
    with patch("server.routers.projects.PROJECTS_DIR", tmp_path):
        resp = client.get("/api/projects/demo")
    assert resp.status_code == 200
    body = resp.json()
    assert "plan" in body
    assert "artifacts" in body
    assert "jobs" in body


def test_get_project_detail_not_found(client, tmp_path):
    with patch("server.routers.projects.PROJECTS_DIR", tmp_path):
        resp = client.get("/api/projects/nonexistent")
    assert resp.status_code == 404


@patch("server.routers.projects.load_plan", return_value=None)
def test_get_project_detail_no_plan(mock_plan, client, tmp_path):
    (tmp_path / "demo").mkdir()
    with patch("server.routers.projects.PROJECTS_DIR", tmp_path):
        resp = client.get("/api/projects/demo")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# DELETE /api/projects/{project}
# ---------------------------------------------------------------------------


def test_delete_project(client, tmp_path):
    project_dir = tmp_path / "demo"
    project_dir.mkdir()
    (project_dir / "plan.json").write_text("{}")

    with patch("server.routers.projects.PROJECTS_DIR", tmp_path):
        resp = client.delete("/api/projects/demo")
    assert resp.status_code == 200
    assert resp.json()["status"] == "deleted"
    assert not project_dir.exists()


def test_delete_project_not_found(client, tmp_path):
    with patch("server.routers.projects.PROJECTS_DIR", tmp_path):
        resp = client.delete("/api/projects/nonexistent")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# GET /api/settings/providers
# ---------------------------------------------------------------------------


_FAKE_KEYS = {"openai": True, "anthropic": False, "replicate": True, "dashscope": False, "elevenlabs": False}


@patch("server.routers.settings.available_image_edit_models", return_value=["qwen/qwen-image-edit-2511"])
@patch("server.routers.settings.available_video_generation_providers", return_value=["manual"])
@patch("server.routers.settings.available_tts_providers", return_value={"kokoro": "Kokoro (Local)"})
@patch("server.routers.settings.available_image_generation_providers", return_value=["replicate", "manual"])
@patch("server.routers.settings.choose_llm_provider", return_value="openai")
@patch("server.routers.settings.check_api_keys", return_value=_FAKE_KEYS)
def test_get_providers(
    _mock_keys,
    _mock_llm,
    _mock_img,
    _mock_tts,
    _mock_vid,
    _mock_edit,
    client,
):
    resp = client.get("/api/settings/providers")
    assert resp.status_code == 200
    body = resp.json()
    assert body["llm_provider"] == "openai"
    assert "replicate" in body["image_providers"]
    assert "kokoro" in body["tts_providers"]
    assert "elevenlabs" in body["tts_voice_options"]


# ---------------------------------------------------------------------------
# Style refs
# ---------------------------------------------------------------------------


_STYLE_PLAN = {
    "meta": {
        "project_name": "demo",
        "brief": {"style_reference_summary": "", "style_reference_paths": []},
    },
    "scenes": [],
}


@patch("server.routers.style_refs.analyze_style_references", return_value="dark moody cinematic")
@patch("server.routers.style_refs.choose_llm_provider", return_value="openai")
@patch("server.routers.style_refs.save_plan", side_effect=lambda d, p: p)
@patch("server.routers.style_refs.load_plan", return_value=_STYLE_PLAN)
def test_upload_style_refs(mock_load, mock_save, mock_llm, mock_analyze, client, tmp_path):
    (tmp_path / "demo").mkdir()
    with patch("server.routers.style_refs.PROJECTS_DIR", tmp_path):
        resp = client.post(
            "/api/projects/demo/style-refs",
            files=[("files", ("ref1.png", b"fake-png", "image/png"))],
        )
    assert resp.status_code == 200
    mock_analyze.assert_called_once()


@patch("server.routers.style_refs.load_plan", return_value=_STYLE_PLAN)
def test_upload_style_refs_rejects_non_image(mock_load, client, tmp_path):
    (tmp_path / "demo").mkdir()
    with patch("server.routers.style_refs.PROJECTS_DIR", tmp_path):
        resp = client.post(
            "/api/projects/demo/style-refs",
            files=[("files", ("ref1.txt", b"nope", "text/plain"))],
        )

    assert resp.status_code == 415


@patch("server.routers.style_refs.load_plan", return_value=_STYLE_PLAN)
def test_upload_style_refs_rejects_oversize_file(mock_load, client, tmp_path):
    (tmp_path / "demo").mkdir()
    tiny_spec = UploadSpec(
        label="style reference",
        max_bytes=4,
        allowed_extensions=(".png",),
        allowed_content_types=("image/png",),
    )

    with (
        patch("server.routers.style_refs.PROJECTS_DIR", tmp_path),
        patch("server.routers.style_refs.STYLE_REF_UPLOAD_SPEC", tiny_spec),
    ):
        resp = client.post(
            "/api/projects/demo/style-refs",
            files=[("files", ("ref1.png", b"\x89PNG\r\n\x1a\n" + b"\x00" * 10, "image/png"))],
        )

    assert resp.status_code == 413


@patch("server.routers.style_refs.load_plan", return_value=_STYLE_PLAN)
def test_upload_style_refs_rejects_too_many_files(mock_load, client, tmp_path):
    (tmp_path / "demo").mkdir()
    files = [
        ("files", (f"ref{i}.png", b"fake-png", "image/png"))
        for i in range(13)
    ]
    with patch("server.routers.style_refs.PROJECTS_DIR", tmp_path):
        resp = client.post("/api/projects/demo/style-refs", files=files)

    assert resp.status_code == 400


@patch("server.routers.style_refs.load_plan", return_value=_STYLE_PLAN)
def test_upload_style_refs_rejects_non_image(mock_load, client, tmp_path):
    (tmp_path / "demo").mkdir()
    with patch("server.routers.style_refs.PROJECTS_DIR", tmp_path):
        resp = client.post(
            "/api/projects/demo/style-refs",
            files=[("files", ("notes.txt", b"not-an-image", "text/plain"))],
        )

    assert resp.status_code == 415
    assert "Unsupported style reference" in resp.json()["detail"]


@patch("server.routers.style_refs.analyze_style_references", return_value="cinematic")
@patch("server.routers.style_refs.choose_llm_provider", return_value="openai")
@patch("server.routers.style_refs.save_plan", side_effect=lambda d, p: p)
def test_upload_style_refs_appends_existing(
    mock_save,
    mock_llm,
    mock_analyze,
    client,
    tmp_path,
):
    project_dir = tmp_path / "demo"
    refs_dir = project_dir / "style_refs"
    refs_dir.mkdir(parents=True)
    existing = refs_dir / "style_ref_01.png"
    existing.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 10)
    plan = copy.deepcopy(_STYLE_PLAN)
    plan["meta"]["brief"]["style_reference_paths"] = [str(existing)]

    with (
        patch("server.routers.style_refs.PROJECTS_DIR", tmp_path),
        patch("server.routers.style_refs.load_plan", return_value=plan),
    ):
        resp = client.post(
            "/api/projects/demo/style-refs",
            files=[("files", ("ref2.png", b"fake-png", "image/png"))],
        )

    assert resp.status_code == 200
    body = resp.json()
    assert len(body["meta"]["brief"]["style_reference_paths"]) == 2


@patch("server.routers.style_refs.load_plan", return_value=_STYLE_PLAN)
def test_get_style_refs(mock_load, client, tmp_path):
    (tmp_path / "demo").mkdir()
    with patch("server.routers.style_refs.PROJECTS_DIR", tmp_path):
        resp = client.get("/api/projects/demo/style-refs")
    assert resp.status_code == 200
    body = resp.json()
    assert "style_reference_paths" in body
    assert "style_reference_summary" in body


def test_get_style_refs_project_not_found(client, tmp_path):
    with patch("server.routers.style_refs.PROJECTS_DIR", tmp_path):
        resp = client.get("/api/projects/nope/style-refs")
    assert resp.status_code == 404
