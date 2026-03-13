"""Integration tests for plan endpoints."""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from server.app import create_app

_FAKE_PLAN: dict[str, Any] = {
    "meta": {
        "project_name": "demo",
        "brief": {"source_material": "Hello"},
        "image_profile": {"provider": "replicate"},
        "tts_profile": {"provider": "kokoro"},
    },
    "scenes": [
        {"id": 0, "uid": "abc1", "title": "Scene 1", "narration": "Hello", "visual_prompt": "A slide"},
        {"id": 1, "uid": "def2", "title": "Scene 2", "narration": "World", "visual_prompt": "Another slide"},
    ],
}


@pytest.fixture()
def client():
    return TestClient(create_app())


# ---------------------------------------------------------------------------
# GET /api/projects/{project}/plan
# ---------------------------------------------------------------------------


@patch("server.routers.plans.load_plan", return_value=_FAKE_PLAN)
def test_get_plan(mock_load, client, tmp_path):
    (tmp_path / "demo").mkdir()
    with patch("server.routers.plans.PROJECTS_DIR", tmp_path):
        resp = client.get("/api/projects/demo/plan")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["scenes"]) == 2
    assert body["meta"]["project_name"] == "demo"


@patch("server.routers.plans.load_plan", return_value=None)
def test_get_plan_missing(mock_load, client, tmp_path):
    (tmp_path / "noplan").mkdir()
    with patch("server.routers.plans.PROJECTS_DIR", tmp_path):
        resp = client.get("/api/projects/noplan/plan")
    assert resp.status_code == 404


def test_get_plan_project_not_found(client, tmp_path):
    with patch("server.routers.plans.PROJECTS_DIR", tmp_path):
        resp = client.get("/api/projects/nonexistent/plan")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# PUT /api/projects/{project}/plan
# ---------------------------------------------------------------------------


@patch("server.routers.plans.save_plan", return_value=_FAKE_PLAN)
def test_put_plan(mock_save, client, tmp_path):
    (tmp_path / "demo").mkdir()
    with patch("server.routers.plans.PROJECTS_DIR", tmp_path):
        resp = client.put("/api/projects/demo/plan", json=_FAKE_PLAN)
    assert resp.status_code == 200
    mock_save.assert_called_once()
    assert resp.json()["meta"]["project_name"] == "demo"


# ---------------------------------------------------------------------------
# POST /api/projects/{project}/storyboard
# ---------------------------------------------------------------------------


@patch("server.routers.plans.rebuild_storyboard_service", return_value=_FAKE_PLAN)
def test_rebuild_storyboard(mock_rebuild, client, tmp_path):
    (tmp_path / "demo").mkdir()
    with patch("server.routers.plans.PROJECTS_DIR", tmp_path):
        resp = client.post("/api/projects/demo/storyboard", json={"provider": "openai"})
    assert resp.status_code == 200
    mock_rebuild.assert_called_once()
    call_kwargs = mock_rebuild.call_args.kwargs
    assert call_kwargs["provider"] == "openai"


@patch("server.routers.plans.rebuild_storyboard_service", return_value=_FAKE_PLAN)
def test_rebuild_storyboard_no_body(mock_rebuild, client, tmp_path):
    (tmp_path / "demo").mkdir()
    with patch("server.routers.plans.PROJECTS_DIR", tmp_path):
        resp = client.post("/api/projects/demo/storyboard")
    assert resp.status_code == 200


@patch(
    "server.routers.plans.rebuild_storyboard_service",
    side_effect=ValueError("Missing plan.json"),
)
def test_rebuild_storyboard_error(mock_rebuild, client, tmp_path):
    (tmp_path / "demo").mkdir()
    with patch("server.routers.plans.PROJECTS_DIR", tmp_path):
        resp = client.post("/api/projects/demo/storyboard")
    assert resp.status_code == 400
    assert "Missing plan.json" in resp.json()["detail"]
