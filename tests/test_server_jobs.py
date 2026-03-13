"""Integration tests for job endpoints."""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from core.job_runner import read_job_file
from server.app import create_app

_FAKE_JOB_RESPONSE: dict[str, Any] = {
    "status": "queued",
    "job_id": "test-job-123",
    "project_name": "demo",
    "project_dir": "/tmp/projects/demo",
    "current_stage": "queued",
    "retryable": False,
    "suggestion": "",
    "requested_stage": "assets",
    "pid": 12345,
    "result": {},
    "error": None,
}

_FAKE_JOB_STATUS: dict[str, Any] = {
    "status": "succeeded",
    "job_id": "test-job-123",
    "project_name": "demo",
    "project_dir": "/tmp/projects/demo",
    "kind": "rerun_stage",
    "current_stage": "done",
    "retryable": False,
    "suggestion": "",
    "requested_stage": "assets",
    "created_utc": "2026-03-12T00:00:00",
    "updated_utc": "2026-03-12T00:01:00",
    "pid": None,
    "log_path": "/tmp/projects/demo/.cathode/jobs/test-job-123.log",
    "request": {"kind": "rerun_stage", "stage": "assets"},
    "result": {},
    "error": None,
}


@pytest.fixture()
def client():
    return TestClient(create_app())


# ---------------------------------------------------------------------------
# POST /api/projects/{project}/assets
# ---------------------------------------------------------------------------


@patch("server.routers.jobs.create_rerun_stage_job", return_value=_FAKE_JOB_RESPONSE)
def test_dispatch_assets_job(mock_create, client, tmp_path):
    project_dir = tmp_path / "demo"
    project_dir.mkdir()
    with patch("server.routers.jobs.PROJECTS_DIR", tmp_path):
        resp = client.post("/api/projects/demo/assets")
    assert resp.status_code == 200
    body = resp.json()
    assert body["job_id"] == "test-job-123"
    mock_create.assert_called_once_with(project_name="demo", stage="assets")


@patch("server.routers.jobs.create_rerun_stage_job", return_value={"status": "error", "error": {"message": "not found"}})
def test_dispatch_assets_job_error(mock_create, client, tmp_path):
    project_dir = tmp_path / "demo"
    project_dir.mkdir()
    with patch("server.routers.jobs.PROJECTS_DIR", tmp_path):
        resp = client.post("/api/projects/demo/assets")
    assert resp.status_code == 400


def test_dispatch_assets_project_not_found(client, tmp_path):
    with patch("server.routers.jobs.PROJECTS_DIR", tmp_path):
        resp = client.post("/api/projects/nonexistent/assets")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# POST /api/projects/{project}/render
# ---------------------------------------------------------------------------


@patch("server.routers.jobs.create_rerun_stage_job", return_value=_FAKE_JOB_RESPONSE)
def test_dispatch_render_job(mock_create, client, tmp_path):
    project_dir = tmp_path / "demo"
    project_dir.mkdir()
    with patch("server.routers.jobs.PROJECTS_DIR", tmp_path):
        resp = client.post("/api/projects/demo/render", json={"fps": 30})
    assert resp.status_code == 200
    call_kwargs = mock_create.call_args.kwargs
    assert call_kwargs["fps"] == 30
    assert call_kwargs["stage"] == "render"


@patch("server.routers.jobs.create_rerun_stage_job", return_value=_FAKE_JOB_RESPONSE)
def test_dispatch_render_no_body(mock_create, client, tmp_path):
    project_dir = tmp_path / "demo"
    project_dir.mkdir()
    with patch("server.routers.jobs.PROJECTS_DIR", tmp_path):
        resp = client.post("/api/projects/demo/render")
    assert resp.status_code == 200


def test_dispatch_render_keeps_current_project_when_creating_real_job(client, tmp_path):
    project_dir = tmp_path / "demo"
    project_dir.mkdir()
    (project_dir / "plan.json").write_text('{"meta":{"project_name":"demo"},"scenes":[]}')

    with (
        patch("server.routers.jobs.PROJECTS_DIR", tmp_path),
        patch("core.job_runner.PROJECTS_DIR", tmp_path),
        patch("core.job_runner.load_plan", return_value={"meta": {"project_name": "demo"}, "scenes": []}),
        patch("core.job_runner.save_plan", side_effect=lambda path, plan: plan),
        patch("core.job_runner.start_job_process", side_effect=lambda job_file: read_job_file(job_file)),
    ):
        resp = client.post("/api/projects/demo/render")

    assert resp.status_code == 200
    body = resp.json()
    assert body["project_name"] == "demo"
    assert body["project_dir"] == str(project_dir)
    assert not (tmp_path / "demo__02").exists()


# ---------------------------------------------------------------------------
# POST /api/projects/{project}/agent-demo
# ---------------------------------------------------------------------------


@patch("server.routers.jobs.create_agent_demo_job", return_value={**_FAKE_JOB_RESPONSE, "requested_stage": "agent_demo"})
def test_dispatch_agent_demo_job(mock_create, client, tmp_path):
    project_dir = tmp_path / "demo"
    project_dir.mkdir()
    with patch("server.routers.jobs.PROJECTS_DIR", tmp_path):
        resp = client.post(
            "/api/projects/demo/agent-demo",
            json={
                "scene_uids": ["abc1"],
                "preferred_agent": "codex",
                "workspace_path": "/tmp/workspace",
                "run_until": "render",
            },
        )
    assert resp.status_code == 200
    call_kwargs = mock_create.call_args.kwargs
    assert call_kwargs["project_name"] == "demo"
    assert call_kwargs["scene_uids"] == ["abc1"]
    assert call_kwargs["preferred_agent"] == "codex"
    assert call_kwargs["workspace_path"] == "/tmp/workspace"
    assert call_kwargs["run_until"] == "render"


@patch("server.routers.jobs.create_agent_demo_job", return_value={"status": "error", "error": {"message": "agent missing"}})
def test_dispatch_agent_demo_job_error(mock_create, client, tmp_path):
    project_dir = tmp_path / "demo"
    project_dir.mkdir()
    with patch("server.routers.jobs.PROJECTS_DIR", tmp_path):
        resp = client.post("/api/projects/demo/agent-demo", json={})
    assert resp.status_code == 400


@patch("server.routers.jobs.create_make_video_job", return_value={**_FAKE_JOB_RESPONSE, "requested_stage": "render"})
def test_dispatch_make_video_job(mock_create, client):
    resp = client.post(
        "/api/jobs/make-video",
        json={
            "project_name": "demo",
            "brief": {"project_name": "demo", "video_goal": "Make a demo"},
            "agent_demo_profile": {"workspace_path": "/tmp/workspace"},
            "run_until": "render",
        },
    )
    assert resp.status_code == 200
    call_kwargs = mock_create.call_args.kwargs
    assert call_kwargs["project_name"] == "demo"
    assert call_kwargs["brief"]["video_goal"] == "Make a demo"
    assert call_kwargs["agent_demo_profile"] == {"workspace_path": "/tmp/workspace"}
    assert call_kwargs["run_until"] == "render"


# ---------------------------------------------------------------------------
# GET /api/projects/{project}/jobs
# ---------------------------------------------------------------------------


@patch("server.routers.jobs.list_project_jobs", return_value=[_FAKE_JOB_STATUS])
def test_list_jobs(mock_list, client, tmp_path):
    project_dir = tmp_path / "demo"
    project_dir.mkdir()
    with patch("server.routers.jobs.PROJECTS_DIR", tmp_path):
        resp = client.get("/api/projects/demo/jobs")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["job_id"] == "test-job-123"
    assert body[0]["requested_stage"] == "assets"
    assert body[0]["request"]["stage"] == "assets"


# ---------------------------------------------------------------------------
# GET /api/jobs/{job_id}
# ---------------------------------------------------------------------------


@patch("server.routers.jobs.get_job_status", return_value=_FAKE_JOB_STATUS)
def test_get_job_status(mock_get, client):
    resp = client.get("/api/jobs/test-job-123")
    assert resp.status_code == 200
    assert resp.json()["status"] == "succeeded"
    mock_get.assert_called_once_with("test-job-123", project_name=None)


@patch("server.routers.jobs.get_job_status", return_value=_FAKE_JOB_STATUS)
def test_get_job_status_with_project(mock_get, client):
    resp = client.get("/api/jobs/test-job-123?project=demo")
    assert resp.status_code == 200
    mock_get.assert_called_once_with("test-job-123", project_name="demo")


# ---------------------------------------------------------------------------
# POST /api/jobs/{job_id}/cancel
# ---------------------------------------------------------------------------


@patch("server.routers.jobs.cancel_job", return_value={"status": "cancelled", "job_id": "test-job-123"})
def test_cancel_job(mock_cancel, client):
    resp = client.post("/api/jobs/test-job-123/cancel")
    assert resp.status_code == 200
    assert resp.json()["status"] == "cancelled"


@patch("server.routers.jobs.cancel_job", return_value={"status": "cancelled", "job_id": "test-job-123"})
def test_cancel_job_with_project(mock_cancel, client):
    resp = client.post("/api/jobs/test-job-123/cancel?project=demo")
    assert resp.status_code == 200
    mock_cancel.assert_called_once_with("test-job-123", project_name="demo")


def test_get_project_job_log(client, tmp_path):
    project_dir = tmp_path / "demo"
    project_dir.mkdir(parents=True)
    log_dir = project_dir / ".cathode" / "jobs"
    log_dir.mkdir(parents=True)
    log_path = log_dir / "test-job-123.log"
    log_path.write_text("line one\nline two\nline three\n")

    job = dict(_FAKE_JOB_STATUS)
    job["project_dir"] = str(project_dir)
    job["log_path"] = str(log_path)

    with (
        patch("server.routers.jobs.PROJECTS_DIR", tmp_path),
        patch("server.routers.jobs.find_job", return_value=(project_dir / ".cathode" / "jobs" / "test-job-123.json", job)),
    ):
        resp = client.get("/api/projects/demo/jobs/test-job-123/log?tail_lines=2")

    assert resp.status_code == 200
    body = resp.json()
    assert body["line_count"] == 3
    assert body["tail_lines"] == 20
    assert "line two" in body["content"]
    assert "line three" in body["content"]
