from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.job_runner import (
    JOB_STATUS_FAILED,
    JOB_STATUS_PARTIAL,
    JOB_STATUS_SUCCEEDED,
    STEP_STATUS_CANCELLED,
    STEP_STATUS_FAILED,
    STEP_STATUS_PENDING,
    STEP_STATUS_RUNNING,
    STEP_STATUS_SKIPPED,
    STEP_STATUS_SUCCEEDED,
    create_job,
    cancel_job,
    cancel_step,
    create_make_video_job,
    create_rerun_stage_job,
    fail_step,
    make_job_response,
    read_job_file,
    run_job_file,
    skip_step,
    start_step,
    succeed_step,
    upsert_step,
    write_job_file,
)


def _job_payload(project_dir: Path) -> dict:
    return {
        "job_id": "job-123",
        "project_name": project_dir.name,
        "project_dir": str(project_dir),
        "requested_stage": "render",
        "status": "queued",
        "current_stage": "queued",
        "created_utc": "2026-03-06T00:00:00",
        "updated_utc": "2026-03-06T00:00:00",
        "pid": None,
        "request": {
            "kind": "make_video",
            "brief": {
                "project_name": project_dir.name,
                "source_mode": "source_text",
                "video_goal": "Explain the product",
                "audience": "Buyers",
                "source_material": "Product notes",
            },
            "run_until": "render",
        },
        "result": {},
        "error": None,
        "suggestion": "",
        "log_path": str(project_dir / ".bettube-studio" / "jobs" / "job-123.log"),
    }


def test_run_job_file_persists_success(monkeypatch, tmp_path):
    project_dir = tmp_path / "demo_project"
    project_dir.mkdir(parents=True)
    job_file = project_dir / ".bettube-studio" / "jobs" / "job-123.json"
    job_file.parent.mkdir(parents=True, exist_ok=True)
    write_job_file(job_file, _job_payload(project_dir))

    def fake_create_project_from_brief_service(**kwargs):
        plan = {
            "meta": {"project_name": kwargs["project_name"], "llm_provider": "openai"},
            "scenes": [],
        }
        (project_dir / "plan.json").write_text(json.dumps(plan))
        return project_dir, plan

    monkeypatch.setattr("core.job_runner.create_project_from_brief_service", fake_create_project_from_brief_service)
    monkeypatch.setattr(
        "core.job_runner.generate_project_assets_service",
        lambda *args, **kwargs: {
            "images_generated": 1,
            "images_skipped": 0,
            "image_failures": [],
            "audio_generated": 1,
            "audio_skipped": 0,
            "audio_failures": [],
        },
    )
    monkeypatch.setattr(
        "core.job_runner.render_project_service",
        lambda *args, **kwargs: {
            "status": "succeeded",
            "retryable": False,
            "suggestion": "",
            "video_path": str(project_dir / "demo_project.mp4"),
            "missing_visual_scenes": [],
            "missing_audio_scenes": [],
        },
    )

    result = run_job_file(job_file)
    saved = read_job_file(job_file)

    assert result["status"] == JOB_STATUS_SUCCEEDED
    assert saved["status"] == JOB_STATUS_SUCCEEDED
    assert saved["result"]["render"]["status"] == "succeeded"


def test_run_job_file_records_failure(monkeypatch, tmp_path):
    project_dir = tmp_path / "broken_project"
    project_dir.mkdir(parents=True)
    job_file = project_dir / ".bettube-studio" / "jobs" / "job-123.json"
    job_file.parent.mkdir(parents=True, exist_ok=True)
    write_job_file(job_file, _job_payload(project_dir))

    monkeypatch.setattr(
        "core.job_runner.create_project_from_brief_service",
        lambda **kwargs: (_ for _ in ()).throw(RuntimeError("boom")),
    )

    result = run_job_file(job_file)
    saved = read_job_file(job_file)

    assert result["status"] == JOB_STATUS_FAILED
    assert saved["status"] == JOB_STATUS_FAILED
    assert saved["error"]["message"] == "boom"


def test_run_job_file_stops_after_storyboard_when_cost_estimate_is_over_budget(monkeypatch, tmp_path):
    project_dir = tmp_path / "budget_project"
    project_dir.mkdir(parents=True)
    job_file = project_dir / ".bettube-studio" / "jobs" / "job-123.json"
    job_file.parent.mkdir(parents=True, exist_ok=True)
    write_job_file(job_file, _job_payload(project_dir))

    def fake_create_project_from_brief_service(**kwargs):
        plan = {
            "meta": {
                "project_name": kwargs["project_name"],
                "llm_provider": "anthropic",
                "cost_estimate": {
                    "status": "over_budget",
                    "budget_usd": 10.0,
                    "gating_total_usd": 24.0,
                },
            },
            "scenes": [],
        }
        (project_dir / "plan.json").write_text(json.dumps(plan))
        return project_dir, plan

    monkeypatch.setattr("core.job_runner.create_project_from_brief_service", fake_create_project_from_brief_service)

    result = run_job_file(job_file)
    saved = read_job_file(job_file)

    assert result["status"] == JOB_STATUS_PARTIAL
    assert saved["status"] == JOB_STATUS_PARTIAL
    assert saved["result"]["confirmation_required"] is True
    assert saved["result"]["current_stage"] == "storyboard"


def test_cancel_job_returns_structured_error_for_missing_job():
    result = cancel_job("missing-job-id")

    assert result["status"] == "error"
    assert result["retryable"] is False
    assert "not found" in result["error"]["message"].lower()


def test_make_job_response_includes_progress_fields(tmp_path):
    project_dir = tmp_path / "demo_project"
    project_dir.mkdir()
    job = _job_payload(project_dir)
    job.update(
        progress=0.42,
        progress_kind="audio",
        progress_label="Generating audio",
        progress_detail="Scene 4 of 10 - Results",
        progress_scene_id=4,
        progress_scene_uid="scene_004",
        progress_status="running",
    )

    response = make_job_response(job)

    assert response["progress"] == 0.42
    assert response["progress_kind"] == "audio"
    assert response["progress_label"] == "Generating audio"
    assert response["progress_detail"] == "Scene 4 of 10 - Results"
    assert response["progress_scene_id"] == 4
    assert response["progress_scene_uid"] == "scene_004"
    assert response["progress_status"] == "running"


def test_create_make_video_job_keeps_demo_context_image_first_without_explicit_mixed_media(monkeypatch, tmp_path):
    project_dir = tmp_path / "demo_project"
    project_dir.mkdir()

    monkeypatch.setattr("core.job_runner.ensure_project_dir", lambda project_name, overwrite=False: project_dir)
    monkeypatch.setattr("core.job_runner.start_job_process", lambda job_file: read_job_file(job_file))

    result = create_make_video_job(
        project_name="demo_project",
        brief={
            "project_name": "demo_project",
            "source_mode": "ideas_notes",
            "video_goal": "Show the app and repo flow",
            "audience": "Hiring manager",
            "source_material": "Prompt plus job description",
        },
        agent_demo_profile={
            "workspace_path": "/tmp/workspace",
            "preferred_agent": "codex",
        },
    )

    job_file = project_dir / ".bettube-studio" / "jobs" / f"{result['job_id']}.json"
    saved = read_job_file(job_file)

    assert saved["request"]["brief"]["composition_mode"] == "classic"
    assert saved["request"]["video_profile"]["provider"] == "manual"
    assert saved["request"]["render_profile"]["render_strategy"] == "auto"
    assert "render_backend" not in saved["request"]["render_profile"]


@pytest.mark.parametrize("stage", ["storyboard", "assets", "render"])
def test_create_rerun_stage_job_stays_on_existing_project(monkeypatch, tmp_path, stage):
    project_dir = tmp_path / "demo_project"
    project_dir.mkdir(parents=True)
    (project_dir / "plan.json").write_text(json.dumps({"meta": {"project_name": "demo_project"}, "scenes": []}))

    monkeypatch.setattr("core.job_runner.PROJECTS_DIR", tmp_path)
    monkeypatch.setattr("core.job_runner.load_plan", lambda _path: {"meta": {"project_name": "demo_project"}, "scenes": []})
    monkeypatch.setattr("core.job_runner.save_plan", lambda _path, plan: plan)
    monkeypatch.setattr("core.job_runner.start_job_process", lambda job_file: read_job_file(job_file))

    result = create_rerun_stage_job(project_name="demo_project", stage=stage)

    assert result["status"] == "queued"
    assert result["project_name"] == "demo_project"
    assert result["project_dir"] == str(project_dir)
    assert result["requested_stage"] == stage
    sibling_dirs = sorted(path.name for path in tmp_path.iterdir() if path.is_dir())
    assert sibling_dirs == ["demo_project"]


# ---------------------------------------------------------------------------
# Phase B: JobStep contract tests
# ---------------------------------------------------------------------------


def test_make_job_response_includes_steps_key_empty_by_default(tmp_path):
    """make_job_response must always include a 'steps' key that is a list."""
    project_dir = tmp_path / "demo_project"
    project_dir.mkdir()
    job = _job_payload(project_dir)
    # A freshly-constructed payload has no 'steps' key; make_job_response should
    # default to an empty list so callers never have to handle a missing key.
    response = make_job_response(job)
    assert "steps" in response
    assert isinstance(response["steps"], list)
    assert response["steps"] == []


def test_make_job_response_propagates_steps_list(tmp_path):
    """make_job_response passes the existing steps list through unchanged."""
    project_dir = tmp_path / "demo_project"
    project_dir.mkdir()
    job = _job_payload(project_dir)
    sample_step = {
        "id": "job_created",
        "label": "Job created",
        "category": "setup",
        "status": STEP_STATUS_PENDING,
        "detail": None,
        "error": None,
        "hint": None,
        "scene_id": None,
        "scene_uid": None,
        "artifact_path": None,
        "created_utc": "2026-03-06T00:00:00",
        "started_utc": None,
        "completed_utc": None,
        "duration_ms": None,
    }
    job["steps"] = [sample_step]
    response = make_job_response(job)
    assert isinstance(response["steps"], list)
    assert len(response["steps"]) == 1
    assert response["steps"][0]["id"] == "job_created"
    assert response["steps"][0]["status"] == STEP_STATUS_PENDING


def test_create_job_persists_seed_steps(tmp_path):
    project_dir = tmp_path / "seed_project"

    job_file, job = create_job(
        project_name=project_dir.name,
        requested_stage="render",
        request={"kind": "make_video"},
        project_dir=project_dir,
    )

    saved = read_job_file(job_file)
    step_ids = [step["id"] for step in saved["steps"]]
    assert step_ids == ["job_created", "worker_started"]
    assert job["steps"][0]["status"] == STEP_STATUS_SUCCEEDED
    assert saved["steps"][0]["status"] == STEP_STATUS_SUCCEEDED
    assert saved["steps"][1]["status"] == STEP_STATUS_RUNNING


def test_upsert_step_creates_pending_step_on_new_job(tmp_path):
    """upsert_step creates a step dict with status 'pending' when the step does not exist."""
    project_dir = tmp_path / "step_project"
    project_dir.mkdir(parents=True)
    job_file = project_dir / ".bettube-studio" / "jobs" / "job-001.json"
    job_file.parent.mkdir(parents=True, exist_ok=True)
    write_job_file(job_file, _job_payload(project_dir))

    upsert_step(job_file, step_id="storyboard", label="Storyboard", category="storyboard")

    saved = read_job_file(job_file)
    steps = saved.get("steps", [])
    assert len(steps) == 1
    step = steps[0]
    assert step["id"] == "storyboard"
    assert step["label"] == "Storyboard"
    assert step["category"] == "storyboard"
    assert step["status"] == STEP_STATUS_PENDING


def test_upsert_step_updates_existing_step_without_duplicating(tmp_path):
    """Calling upsert_step twice with the same step_id updates in place."""
    project_dir = tmp_path / "step_project"
    project_dir.mkdir(parents=True)
    job_file = project_dir / ".bettube-studio" / "jobs" / "job-001.json"
    job_file.parent.mkdir(parents=True, exist_ok=True)
    write_job_file(job_file, _job_payload(project_dir))

    upsert_step(job_file, step_id="render", label="Render", category="render")
    upsert_step(job_file, step_id="render", label="Render (updated)", category="render", detail="pass 2")

    saved = read_job_file(job_file)
    steps = saved.get("steps", [])
    assert len(steps) == 1
    assert steps[0]["label"] == "Render (updated)"
    assert steps[0]["detail"] == "pass 2"


def test_start_step_transitions_pending_to_running(tmp_path):
    """start_step sets status to 'running' and populates started_utc."""
    project_dir = tmp_path / "step_project"
    project_dir.mkdir(parents=True)
    job_file = project_dir / ".bettube-studio" / "jobs" / "job-001.json"
    job_file.parent.mkdir(parents=True, exist_ok=True)
    write_job_file(job_file, _job_payload(project_dir))

    upsert_step(job_file, step_id="render", label="Render", category="render")
    start_step(job_file, step_id="render")

    saved = read_job_file(job_file)
    step = next(s for s in saved["steps"] if s["id"] == "render")
    assert step["status"] == STEP_STATUS_RUNNING
    assert step["started_utc"] is not None


def test_succeed_step_completes_lifecycle_with_timestamps_and_duration(tmp_path):
    """upsert->start->succeed sets succeeded status, both timestamps, and a non-negative duration_ms."""
    project_dir = tmp_path / "step_project"
    project_dir.mkdir(parents=True)
    job_file = project_dir / ".bettube-studio" / "jobs" / "job-001.json"
    job_file.parent.mkdir(parents=True, exist_ok=True)
    write_job_file(job_file, _job_payload(project_dir))

    upsert_step(job_file, step_id="compress", label="Compress", category="compress")
    start_step(job_file, step_id="compress")
    succeed_step(job_file, step_id="compress")

    saved = read_job_file(job_file)
    step = next(s for s in saved["steps"] if s["id"] == "compress")
    assert step["status"] == STEP_STATUS_SUCCEEDED
    assert step["started_utc"] is not None
    assert step["completed_utc"] is not None
    assert isinstance(step["duration_ms"], (int, float))
    assert step["duration_ms"] >= 0


def test_fail_step_records_error_and_terminal_status(tmp_path):
    """fail_step sets status to 'failed' and stores the error message."""
    project_dir = tmp_path / "step_project"
    project_dir.mkdir(parents=True)
    job_file = project_dir / ".bettube-studio" / "jobs" / "job-001.json"
    job_file.parent.mkdir(parents=True, exist_ok=True)
    write_job_file(job_file, _job_payload(project_dir))

    upsert_step(job_file, step_id="assets", label="Assets", category="assets")
    start_step(job_file, step_id="assets")
    fail_step(job_file, step_id="assets", error="Provider returned 429")

    saved = read_job_file(job_file)
    step = next(s for s in saved["steps"] if s["id"] == "assets")
    assert step["status"] == STEP_STATUS_FAILED
    assert "Provider returned 429" in (step.get("error") or "")


def test_skip_step_marks_step_as_skipped(tmp_path):
    """skip_step sets status to 'skipped' without requiring start_step first."""
    project_dir = tmp_path / "step_project"
    project_dir.mkdir(parents=True)
    job_file = project_dir / ".bettube-studio" / "jobs" / "job-001.json"
    job_file.parent.mkdir(parents=True, exist_ok=True)
    write_job_file(job_file, _job_payload(project_dir))

    upsert_step(job_file, step_id="budget_gate", label="Budget gate", category="budget")
    skip_step(job_file, step_id="budget_gate", detail="No budget cap configured")

    saved = read_job_file(job_file)
    step = next(s for s in saved["steps"] if s["id"] == "budget_gate")
    assert step["status"] == STEP_STATUS_SKIPPED


def test_cancel_step_transitions_running_step_to_cancelled(tmp_path):
    """cancel_step transitions a running step to 'cancelled'."""
    project_dir = tmp_path / "step_project"
    project_dir.mkdir(parents=True)
    job_file = project_dir / ".bettube-studio" / "jobs" / "job-001.json"
    job_file.parent.mkdir(parents=True, exist_ok=True)
    write_job_file(job_file, _job_payload(project_dir))

    upsert_step(job_file, step_id="render", label="Render", category="render")
    start_step(job_file, step_id="render")
    cancel_step(job_file, step_id="render")

    saved = read_job_file(job_file)
    step = next(s for s in saved["steps"] if s["id"] == "render")
    assert step["status"] == STEP_STATUS_CANCELLED
