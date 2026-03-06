from __future__ import annotations

import json
from pathlib import Path

from core.job_runner import (
    JOB_STATUS_FAILED,
    JOB_STATUS_SUCCEEDED,
    cancel_job,
    read_job_file,
    run_job_file,
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
        "log_path": str(project_dir / ".cathode" / "jobs" / "job-123.log"),
    }


def test_run_job_file_persists_success(monkeypatch, tmp_path):
    project_dir = tmp_path / "demo_project"
    project_dir.mkdir(parents=True)
    job_file = project_dir / ".cathode" / "jobs" / "job-123.json"
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
    job_file = project_dir / ".cathode" / "jobs" / "job-123.json"
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


def test_cancel_job_returns_structured_error_for_missing_job():
    result = cancel_job("missing-job-id")

    assert result["status"] == "error"
    assert result["retryable"] is False
    assert "not found" in result["error"]["message"].lower()

