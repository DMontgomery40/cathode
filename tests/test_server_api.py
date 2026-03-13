"""Integration tests for the FastAPI server layer."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from fastapi import APIRouter

from server.app import create_app


@pytest.fixture()
def client():
    app = create_app()
    return TestClient(app)


# ---------------------------------------------------------------------------
# GET /api/health
# ---------------------------------------------------------------------------


def test_health(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_health_allows_127001_frontend_origin(client):
    resp = client.options(
        "/api/health",
        headers={
            "Origin": "http://127.0.0.1:9322",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert resp.status_code == 200
    assert resp.headers["access-control-allow-origin"] == "http://127.0.0.1:9322"


def test_unhandled_exception_returns_operator_hint():
    app = create_app()
    router = APIRouter()

    @router.get("/api/_boom")
    async def _boom():
        raise RuntimeError("boom")

    app.include_router(router)
    client = TestClient(app, raise_server_exceptions=False)
    resp = client.get("/api/_boom")
    assert resp.status_code == 500
    body = resp.json()
    assert "message" in body
    assert "operatorHint" in body


# ---------------------------------------------------------------------------
# GET /api/bootstrap
# ---------------------------------------------------------------------------


_FAKE_KEYS = {
    "openai": True,
    "anthropic": False,
    "replicate": True,
    "dashscope": False,
    "elevenlabs": False,
}


@patch("server.routers.bootstrap.list_projects", return_value=["demo"])
@patch(
    "server.routers.bootstrap.available_image_edit_models",
    return_value=["qwen/qwen-image-edit-2511"],
)
@patch(
    "server.routers.bootstrap.available_video_generation_providers",
    return_value=["manual"],
)
@patch(
    "server.routers.bootstrap.available_render_backends",
    return_value=["ffmpeg", "remotion"],
)
@patch("server.routers.bootstrap.remotion_available", return_value=True)
@patch(
    "server.routers.bootstrap.available_tts_providers",
    return_value={"kokoro": "Kokoro (Local)"},
)
@patch(
    "server.routers.bootstrap.available_image_generation_providers",
    return_value=["replicate", "manual"],
)
@patch("server.routers.bootstrap.choose_llm_provider", return_value="openai")
@patch("server.routers.bootstrap.check_api_keys", return_value=_FAKE_KEYS)
def test_bootstrap_shape(
    _mock_keys,
    _mock_llm,
    _mock_img_providers,
    _mock_tts_providers,
    _mock_remotion_available,
    _mock_render_backends,
    _mock_vid_providers,
    _mock_edit_models,
    _mock_projects,
    client,
):
    resp = client.get("/api/bootstrap")
    assert resp.status_code == 200
    body = resp.json()

    # Top-level keys
    assert set(body.keys()) == {"providers", "defaults", "projects"}

    # Providers section
    providers = body["providers"]
    assert providers["api_keys"]["openai"] is True
    assert providers["api_keys"]["anthropic"] is False
    assert providers["llm_provider"] == "openai"
    assert "replicate" in providers["image_providers"]
    assert providers["video_providers"] == ["manual"]
    assert providers["render_backends"] == ["ffmpeg", "remotion"]
    assert providers["remotion_available"] is True
    assert "kokoro" in providers["tts_providers"]
    assert "kokoro" in providers["tts_voice_options"]
    assert "elevenlabs" in providers["tts_voice_options"]
    assert isinstance(providers["image_edit_models"], list)

    # Defaults section
    defaults = body["defaults"]
    for key in ("brief", "render_profile", "image_profile", "video_profile", "tts_profile"):
        assert key in defaults
    assert defaults["brief"]["project_name"] == "my_video"
    assert defaults["brief"]["composition_mode"] == "classic"
    assert defaults["render_profile"]["aspect_ratio"] == "16:9"
    assert defaults["render_profile"]["render_backend"] == "ffmpeg"
    assert defaults["tts_profile"]["provider"] == "kokoro"

    # Projects list
    assert body["projects"] == ["demo"]


# ---------------------------------------------------------------------------
# GET /api/projects
# ---------------------------------------------------------------------------


_FAKE_PLAN = {
    "meta": {
        "video_path": "/tmp/test.mp4",
        "image_profile": {"provider": "replicate"},
        "tts_profile": {"provider": "kokoro"},
    },
    "scenes": [{"id": 0}, {"id": 1}],
}


@patch("server.routers.projects.load_plan", return_value=_FAKE_PLAN)
@patch("server.routers.projects.list_projects", return_value=["project_a"])
def test_get_projects(mock_list, mock_load, client, tmp_path):
    project_dir = tmp_path / "project_a"
    project_dir.mkdir()
    (project_dir / "render.mp4").write_bytes(b"mp4")
    mock_load.return_value = {
        **_FAKE_PLAN,
        "meta": {
            **_FAKE_PLAN["meta"],
            "video_path": "projects/project_a/render.mp4",
        },
    }

    with patch("server.routers.projects.PROJECTS_DIR", tmp_path):
        resp = client.get("/api/projects")

    assert resp.status_code == 200
    body = resp.json()

    assert isinstance(body, list)
    assert len(body) == 1

    proj = body[0]
    assert proj["name"] == "project_a"
    assert proj["scene_count"] == 2
    assert proj["video_path"] == "render.mp4"
    assert proj["has_video"] is True
    assert proj["image_profile"] == {"provider": "replicate"}
    assert proj["tts_profile"] == {"provider": "kokoro"}


def test_get_projects_ignores_cross_project_thumbnail_paths(client, tmp_path):
    project_dir = tmp_path / "project_a"
    project_dir.mkdir()
    (project_dir / "images").mkdir()
    (project_dir / "images" / "scene_001.png").write_bytes(b"png")
    (tmp_path / "other_project").mkdir()
    (tmp_path / "other_project" / "images").mkdir()
    (tmp_path / "other_project" / "images" / "scene_000.png").write_bytes(b"png")

    fake_plan = {
        "meta": {"video_path": None, "image_profile": None, "tts_profile": None},
        "scenes": [
            {"image_path": str((tmp_path / "other_project" / "images" / "scene_000.png").resolve())},
            {"image_path": "projects/project_a/images/scene_001.png"},
        ],
    }

    with (
        patch("server.routers.projects.PROJECTS_DIR", tmp_path),
        patch("server.routers.projects.list_projects", return_value=["project_a"]),
        patch("server.routers.projects.load_plan", return_value=fake_plan),
    ):
        resp = client.get("/api/projects")

    assert resp.status_code == 200
    assert resp.json()[0]["thumbnail_path"] == "images/scene_001.png"
    assert resp.json()[0]["has_video"] is False


@patch("server.routers.projects.load_plan", return_value=None)
@patch("server.routers.projects.list_projects", return_value=["broken"])
def test_get_projects_skips_missing_plans(mock_list, mock_load, client):
    resp = client.get("/api/projects")
    assert resp.status_code == 200
    assert resp.json() == []


# ---------------------------------------------------------------------------
# POST /api/projects
# ---------------------------------------------------------------------------


_FAKE_CREATED_PLAN = {
    "meta": {"project_name": "new_vid", "brief": {}},
    "scenes": [{"id": 0, "title": "Scene 1"}],
}


@patch(
    "server.routers.projects.create_project_from_brief_service",
    return_value=(Path("/tmp/projects/new_vid"), _FAKE_CREATED_PLAN),
)
def test_create_project(mock_create, client):
    payload = {
        "project_name": "new_vid",
        "brief": {"source_material": "Hello world"},
    }
    resp = client.post("/api/projects", json=payload)
    assert resp.status_code == 200
    body = resp.json()
    assert body["meta"]["project_name"] == "new_vid"
    assert len(body["scenes"]) == 1

    call_kwargs = mock_create.call_args.kwargs
    assert call_kwargs["project_name"] == "new_vid"
    assert call_kwargs["brief"]["source_material"] == "Hello world"
    assert call_kwargs["overwrite"] is False


@patch(
    "server.routers.projects.create_project_from_brief_service",
    side_effect=ValueError("No LLM API keys configured."),
)
def test_create_project_missing_keys(mock_create, client):
    payload = {
        "project_name": "fail_vid",
        "brief": {"source_material": "text"},
    }
    resp = client.post("/api/projects", json=payload)
    assert resp.status_code == 400
    assert "No LLM API keys" in resp.json()["detail"]


def test_rebuild_storyboard_persists_updated_brief_and_agent_demo_profile(client, tmp_path):
    project_dir = tmp_path / "demo"
    project_dir.mkdir()
    (project_dir / "plan.json").write_text('{"meta":{"project_name":"demo","brief":{"project_name":"demo","video_goal":"old"}},"scenes":[]}')

    captured: dict[str, object] = {}

    def fake_rebuild(project_path, provider=None):
        captured["project_path"] = project_path
        captured["provider"] = provider
        return {
            "meta": {
                "project_name": "demo",
                "brief": {
                    "project_name": "demo",
                    "video_goal": "new goal",
                },
                "agent_demo_profile": {
                    "workspace_path": "/tmp/workspace",
                },
            },
            "scenes": [],
        }

    with (
        patch("server.routers.plans.PROJECTS_DIR", tmp_path),
        patch("server.routers.plans.rebuild_storyboard_service", side_effect=fake_rebuild),
    ):
        resp = client.post(
            "/api/projects/demo/storyboard",
            json={
                "brief": {
                    "project_name": "demo",
                    "source_mode": "ideas_notes",
                    "video_goal": "new goal",
                    "audience": "Hiring manager",
                    "source_material": "Prompt notes",
                    "target_length_minutes": 1.5,
                    "tone": "sharp",
                    "visual_style": "demo",
                    "must_include": "",
                    "must_avoid": "",
                    "ending_cta": "",
                    "visual_source_strategy": "mixed_media",
                },
                "agent_demo_profile": {
                    "workspace_path": "/tmp/workspace",
                },
            },
        )

    assert resp.status_code == 200
    saved_plan = json.loads((project_dir / "plan.json").read_text())
    assert saved_plan["meta"]["brief"]["video_goal"] == "new goal"
    assert saved_plan["meta"]["brief"]["composition_mode"] == "hybrid"
    assert saved_plan["meta"]["agent_demo_profile"]["workspace_path"] == "/tmp/workspace"
    assert saved_plan["meta"]["render_profile"]["render_backend"] == "remotion"
    assert captured["project_path"] == project_dir
