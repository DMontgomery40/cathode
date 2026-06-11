"""Integration tests for the FastAPI server layer."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
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


def test_unhandled_exception_returns_operator_hint(monkeypatch, tmp_path):
    # Point the SPA mount at an empty dir so its catch-all route does not
    # shadow the test route registered after create_app().
    monkeypatch.setenv("BETTUBE_STUDIO_FRONTEND_DIST", str(tmp_path))
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
@patch(
    "server.routers.bootstrap.remotion_capabilities",
    return_value={
        "render_available": True,
        "player_available": True,
        "transitions_available": True,
        "three_available": True,
    },
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
    _mock_remotion_capabilities,
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
    assert providers["remotion_capabilities"]["player_available"] is True
    assert providers["remotion_capabilities"]["three_available"] is True
    assert "kokoro" in providers["tts_providers"]
    assert "kokoro" in providers["tts_voice_options"]
    assert "elevenlabs" in providers["tts_voice_options"]
    assert isinstance(providers["image_edit_models"], list)
    assert providers["cost_catalog"]["version"]
    assert isinstance(providers["cost_catalog"]["entries"], list)

    # Defaults section
    defaults = body["defaults"]
    for key in ("brief", "render_profile", "image_profile", "video_profile", "tts_profile"):
        assert key in defaults
    assert defaults["brief"]["project_name"] == "my_video"
    assert defaults["brief"]["composition_mode"] == "auto"
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
    (project_dir / "plan.json").write_text("{}", encoding="utf-8")
    (project_dir / "render.mp4").write_bytes(b"mp4")
    mock_load.return_value = {
        **_FAKE_PLAN,
        "meta": {
            **_FAKE_PLAN["meta"],
            "video_path": "projects/project_a/render.mp4",
            "created_utc": "2026-03-14T10:00:00Z",
            "rendered_utc": "2026-03-14T12:30:00Z",
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
    assert proj["created_utc"] == "2026-03-14T10:00:00Z"
    assert proj["updated_utc"] == "2026-03-14T12:30:00Z"
    assert proj["image_profile"] == {"provider": "replicate"}
    assert proj["tts_profile"] == {"provider": "kokoro"}
    assert proj["jobs"]["counts"]["total"] == 0
    assert proj["jobs"]["counts"]["active"] == 0
    assert proj["jobs"]["latest_status"] is None


@patch("server.routers.projects.load_plan")
@patch("server.routers.projects.list_projects", return_value=["project_a"])
def test_get_projects_exposes_real_job_summary(mock_list, mock_load, client, tmp_path):
    project_dir = tmp_path / "project_a"
    jobs_dir = project_dir / ".bettube-studio" / "jobs"
    jobs_dir.mkdir(parents=True)
    (project_dir / "plan.json").write_text("{}", encoding="utf-8")
    (jobs_dir / "old.json").write_text(
        json.dumps(
            {
                "job_id": "old",
                "status": "succeeded",
                "requested_stage": "assets",
                "created_utc": "2026-03-14T10:00:00",
                "updated_utc": "2026-03-14T10:05:00",
            },
        ),
        encoding="utf-8",
    )
    (jobs_dir / "new.json").write_text(
        json.dumps(
            {
                "job_id": "new",
                "status": "failed",
                "requested_stage": "render",
                "created_utc": "2026-03-14T11:00:00",
                "updated_utc": "2026-03-14T11:05:00",
            },
        ),
        encoding="utf-8",
    )
    mock_load.return_value = {
        "meta": {"video_path": None, "image_profile": None, "tts_profile": None},
        "scenes": [{"id": 0}],
    }

    with patch("server.routers.projects.PROJECTS_DIR", tmp_path):
        resp = client.get("/api/projects")

    assert resp.status_code == 200
    jobs = resp.json()[0]["jobs"]
    assert jobs["counts"]["total"] == 2
    assert jobs["counts"]["succeeded"] == 1
    assert jobs["counts"]["failed"] == 1
    assert jobs["counts"]["active"] == 0
    assert jobs["latest_status"] == "failed"
    assert jobs["latest_job_id"] == "new"
    assert jobs["latest_requested_stage"] == "render"


@patch("server.routers.projects.load_plan")
@patch("server.routers.projects.list_projects", return_value=["short_project"])
def test_get_projects_exposes_short_form_mode_metadata(mock_list, mock_load, client, tmp_path):
    project_dir = tmp_path / "short_project"
    project_dir.mkdir()
    (project_dir / "plan.json").write_text("{}", encoding="utf-8")
    mock_load.return_value = {
        "meta": {
            "pipeline_mode": "short_form_vertical_v1",
            "brief": {"short_form_format": "vertical_short"},
            "render_profile": {"aspect_ratio": "9:16"},
        },
        "scenes": [],
    }

    with patch("server.routers.projects.PROJECTS_DIR", tmp_path):
        resp = client.get("/api/projects")

    assert resp.status_code == 200
    proj = resp.json()[0]
    assert proj["pipeline_mode"] == "short_form_vertical_v1"
    assert proj["short_form_format"] == "vertical_short"
    assert proj["render_aspect_ratio"] == "9:16"


def test_get_projects_falls_back_to_plan_timestamp_when_meta_dates_missing(client, tmp_path):
    project_dir = tmp_path / "project_a"
    project_dir.mkdir()
    plan_path = project_dir / "plan.json"
    plan_path.write_text("{}", encoding="utf-8")
    fallback_time = datetime(2026, 3, 9, 15, 45, tzinfo=timezone.utc).timestamp()
    os.utime(plan_path, (fallback_time, fallback_time))

    fake_plan = {
        "meta": {"video_path": None, "image_profile": None, "tts_profile": None},
        "scenes": [],
    }

    with (
        patch("server.routers.projects.PROJECTS_DIR", tmp_path),
        patch("server.routers.projects.list_projects", return_value=["project_a"]),
        patch("server.routers.projects.load_plan", return_value=fake_plan),
    ):
        resp = client.get("/api/projects")

    assert resp.status_code == 200
    assert resp.json()[0]["created_utc"] == "2026-03-09T15:45:00Z"
    assert resp.json()[0]["updated_utc"] == "2026-03-09T15:45:00Z"


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


def test_get_projects_includes_job_only_directories(client, tmp_path):
    project_dir = tmp_path / "job_only_project"
    jobs_dir = project_dir / ".bettube-studio" / "jobs"
    jobs_dir.mkdir(parents=True)
    (jobs_dir / "active.json").write_text(
        json.dumps(
            {
                "job_id": "active",
                "project_name": "job_only_project",
                "status": "running",
                "requested_stage": "render",
                "created_utc": "2026-06-09T20:00:00",
                "updated_utc": "2026-06-09T20:01:00",
            }
        ),
        encoding="utf-8",
    )

    with (
        patch("server.routers.projects.PROJECTS_DIR", tmp_path),
        patch("server.routers.projects.list_projects", return_value=[]),
    ):
        resp = client.get("/api/projects")

    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    project = body[0]
    assert project["name"] == "job_only_project"
    assert project["scene_count"] == 0
    assert project["jobs"]["counts"]["running"] == 1
    assert project["jobs"]["counts"]["active"] == 1
    assert project["jobs"]["latest_status"] == "running"
    assert project["created_utc"] == "2026-06-09T20:01:00Z"


@patch("server.routers.projects.load_plan", return_value=None)
@patch("server.routers.projects.list_projects", return_value=["broken"])
def test_get_projects_keeps_missing_plan_project_as_empty(mock_list, mock_load, client, tmp_path):
    (tmp_path / "broken").mkdir()
    with patch("server.routers.projects.PROJECTS_DIR", tmp_path):
        resp = client.get("/api/projects")
    assert resp.status_code == 200
    assert resp.json()[0]["name"] == "broken"
    assert resp.json()[0]["jobs"]["counts"]["total"] == 0


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
    assert saved_plan["meta"]["render_profile"]["render_backend"] == "ffmpeg"


@patch("server.routers.plans.build_remotion_manifest", return_value={"scenes": [], "fps": 24})
def test_get_project_remotion_manifest(mock_manifest, client, tmp_path):
    (tmp_path / "demo").mkdir()

    with (
        patch("server.routers.plans.PROJECTS_DIR", tmp_path),
        patch(
            "server.routers.plans.load_plan",
            return_value={
                "meta": {
                    "render_profile": {
                        "render_strategy": "force_remotion",
                        "render_backend": "remotion",
                    },
                },
                "scenes": [],
            },
        ),
    ):
        resp = client.get("/api/projects/demo/remotion-manifest")

    assert resp.status_code == 200
    assert resp.json()["fps"] == 24
    mock_manifest.assert_called_once()

def test_cors_origins_env_override(monkeypatch):
    from server.app import _cors_origins

    monkeypatch.delenv("BETTUBE_STUDIO_CORS_ORIGINS", raising=False)
    defaults = _cors_origins()
    assert "http://127.0.0.1:9322" in defaults

    monkeypatch.setenv(
        "BETTUBE_STUDIO_CORS_ORIGINS",
        "https://studio.example.com, https://tools.example.com/",
    )
    assert _cors_origins() == ["https://studio.example.com", "https://tools.example.com"]


def test_cors_env_origin_is_honored_by_app(monkeypatch):
    monkeypatch.setenv("BETTUBE_STUDIO_CORS_ORIGINS", "https://studio.example.com")
    app = create_app()
    client = TestClient(app)
    resp = client.options(
        "/api/health",
        headers={
            "Origin": "https://studio.example.com",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert resp.status_code == 200
    assert resp.headers["access-control-allow-origin"] == "https://studio.example.com"

    disallowed = client.options(
        "/api/health",
        headers={
            "Origin": "https://evil.example.com",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert "access-control-allow-origin" not in disallowed.headers

def test_project_asset_path_remaps_foreign_absolute_paths(tmp_path):
    """Plans written on another machine persist absolute paths; anything with a
    projects/<name>/ segment must remap into the local project directory."""
    from server.routers.projects import _project_asset_path

    project_dir = tmp_path / "projects" / "demo_project"
    (project_dir / "images").mkdir(parents=True)
    asset = project_dir / "images" / "scene_000.png"
    asset.write_bytes(b"png")

    foreign = "/Users/somebody-else/old-repo/projects/demo_project/images/scene_000.png"
    assert _project_asset_path(project_dir, foreign) == "images/scene_000.png"

    # Absolute paths with no project marker stay rejected (no path escape).
    assert _project_asset_path(project_dir, "/etc/passwd") is None
    # Missing files stay rejected even when the marker matches.
    missing = "/elsewhere/projects/demo_project/images/missing.png"
    assert _project_asset_path(project_dir, missing) is None


def test_get_projects_thumbnail_prefers_stills_then_falls_back_to_video(tmp_path):
    from server.routers import projects as projects_router

    project_dir = tmp_path / "video_only"
    (project_dir / "clips").mkdir(parents=True)
    clip = project_dir / "clips" / "scene_001.mp4"
    clip.write_bytes(b"mp4")
    render = project_dir / "final.mp4"
    render.write_bytes(b"mp4")
    (project_dir / "plan.json").write_text("{}", encoding="utf-8")

    plan = {
        "meta": {"video_path": str(render)},
        "scenes": [
            {"id": 0, "image_path": None, "video_path": str(clip)},
            {"id": 1, "image_path": None},
        ],
    }

    with (
        patch.object(projects_router, "PROJECTS_DIR", tmp_path),
        patch.object(projects_router, "list_projects", return_value=["video_only"]),
        patch.object(projects_router, "load_plan", return_value=plan),
    ):
        app = create_app()
        client = TestClient(app)
        resp = client.get("/api/projects")

    assert resp.status_code == 200
    body = resp.json()[0]
    # No stills anywhere -> first scene clip becomes the thumbnail.
    assert body["thumbnail_path"] == "clips/scene_001.mp4"
    assert body["has_video"] is True
