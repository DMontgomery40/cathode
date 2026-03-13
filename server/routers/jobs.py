"""Job management endpoints (dispatch, status, cancel, logs)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, Body, HTTPException

from core.job_runner import (
    cancel_job,
    create_agent_demo_job,
    create_make_video_job,
    create_rerun_stage_job,
    find_job,
    get_job_status,
    list_project_jobs,
    make_job_response,
)
from core.runtime import PROJECTS_DIR
from server.schemas.jobs import AgentDemoRequest, MakeVideoRequest, RenderRequest

router = APIRouter()


def _project_dir(project: str):
    d = PROJECTS_DIR / project
    if not d.exists():
        raise HTTPException(status_code=404, detail=f"Project not found: {project}")
    return d


@router.post("/projects/{project}/assets")
async def dispatch_assets_job(project: str) -> dict[str, Any]:
    _project_dir(project)  # validate existence
    result = create_rerun_stage_job(project_name=project, stage="assets")
    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result.get("error", {}).get("message", "Failed"))
    return result


@router.post("/projects/{project}/render")
async def dispatch_render_job(
    project: str,
    body: RenderRequest | None = Body(None),
) -> dict[str, Any]:
    _project_dir(project)  # validate existence
    result = create_rerun_stage_job(
        project_name=project,
        stage="render",
        output_filename=body.output_filename if body else None,
        fps=body.fps if body else None,
    )
    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result.get("error", {}).get("message", "Failed"))
    return result


@router.post("/projects/{project}/agent-demo")
async def dispatch_agent_demo_job(
    project: str,
    body: AgentDemoRequest | None = Body(None),
) -> dict[str, Any]:
    _project_dir(project)
    result = create_agent_demo_job(
        project_name=project,
        scene_uids=body.scene_uids if body else None,
        preferred_agent=body.preferred_agent if body else None,
        workspace_path=body.workspace_path if body else None,
        app_url=body.app_url if body else None,
        launch_command=body.launch_command if body else None,
        expected_url=body.expected_url if body else None,
        run_until=body.run_until if body and body.run_until else "assets",
    )
    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result.get("error", {}).get("message", "Failed"))
    return result


@router.post("/jobs/make-video")
async def dispatch_make_video_job(body: MakeVideoRequest) -> dict[str, Any]:
    result = create_make_video_job(
        project_name=body.project_name,
        brief=body.brief,
        run_until=body.run_until or "render",
        provider=body.provider,
        image_profile=body.image_profile,
        video_profile=body.video_profile,
        agent_demo_profile=body.agent_demo_profile,
        tts_profile=body.tts_profile,
        render_profile=body.render_profile,
        overwrite=body.overwrite,
    )
    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result.get("error", {}).get("message", "Failed"))
    return result


@router.get("/projects/{project}/jobs")
async def list_jobs(project: str) -> list[dict[str, Any]]:
    project_dir = _project_dir(project)
    return [make_job_response(job) for job in list_project_jobs(project_dir)]


@router.get("/jobs/{job_id}")
async def get_job(job_id: str, project: str | None = None) -> dict[str, Any]:
    return get_job_status(job_id, project_name=project)


@router.post("/jobs/{job_id}/cancel")
async def cancel_job_endpoint(job_id: str, project: str | None = None) -> dict[str, Any]:
    return cancel_job(job_id, project_name=project)


@router.get("/projects/{project}/jobs/{job_id}/log")
async def get_project_job_log(project: str, job_id: str, tail_lines: int = 200) -> dict[str, Any]:
    _project_dir(project)
    found = find_job(job_id, project_name=project)
    if not found:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")

    _, job = found
    log_path_raw = str(job.get("log_path") or "").strip()
    if not log_path_raw:
        raise HTTPException(status_code=404, detail=f"No log file recorded for job: {job_id}")

    log_path = Path(log_path_raw)
    if not log_path.exists() or not log_path.is_file():
        raise HTTPException(status_code=404, detail=f"Log file not found for job: {job_id}")

    tail_lines = max(20, min(int(tail_lines or 200), 1000))
    lines = log_path.read_text(errors="replace").splitlines()
    return {
        "job_id": job_id,
        "project_name": project,
        "log_path": str(log_path),
        "tail_lines": tail_lines,
        "line_count": len(lines),
        "content": "\n".join(lines[-tail_lines:]),
    }
