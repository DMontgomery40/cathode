"""Persisted local background jobs for Cathode pipeline runs."""

from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from .pipeline_service import (
    create_project_from_brief_service,
    generate_project_assets_service,
    prepare_project_execution_profiles,
    rebuild_storyboard_service,
    render_project_service,
)
from .agent_demo import build_agent_demo_prompt, choose_agent_cli, run_agent_demo_cli
from .project_store import collect_project_artifacts, ensure_project_dir, load_plan, save_plan
from .project_schema import normalize_agent_demo_profile
from .runtime import PROJECTS_DIR

JOB_DIR_NAME = ".cathode/jobs"
JOB_STATUS_QUEUED = "queued"
JOB_STATUS_RUNNING = "running"
JOB_STATUS_SUCCEEDED = "succeeded"
JOB_STATUS_PARTIAL = "partial_success"
JOB_STATUS_FAILED = "failed"
JOB_STATUS_CANCELLED = "cancelled"

_ACTIVE_JOB_FILE: Path | None = None


def utc_now_iso() -> str:
    """Return a UTC timestamp in ISO format."""
    return datetime.utcnow().isoformat()


def job_dir_for_project(project_dir: Path) -> Path:
    """Return the directory used for persisted job metadata."""
    path = Path(project_dir) / JOB_DIR_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def job_file_path(project_dir: Path, job_id: str) -> Path:
    """Return the JSON file path for a specific job."""
    return job_dir_for_project(project_dir) / f"{job_id}.json"


def read_job_file(job_file: Path) -> dict[str, Any]:
    """Read a job JSON file."""
    return json.loads(Path(job_file).read_text())


def write_job_file(job_file: Path, job: dict[str, Any]) -> dict[str, Any]:
    """Persist job state to disk."""
    job["updated_utc"] = utc_now_iso()
    Path(job_file).parent.mkdir(parents=True, exist_ok=True)
    Path(job_file).write_text(json.dumps(job, indent=2))
    return job


def update_job(job_file: Path, **changes: Any) -> dict[str, Any]:
    """Apply a partial update to a job file."""
    job = read_job_file(job_file)
    job.update(changes)
    return write_job_file(job_file, job)


def list_project_jobs(project_dir: Path) -> list[dict[str, Any]]:
    """List persisted jobs for a project."""
    jobs_path = job_dir_for_project(project_dir)
    jobs: list[dict[str, Any]] = []
    for path in sorted(jobs_path.glob("*.json")):
        try:
            jobs.append(read_job_file(path))
        except Exception:
            continue
    return jobs


def find_job(job_id: str, project_name: str | None = None) -> tuple[Path, dict[str, Any]] | None:
    """Find a persisted job by id, optionally scoped to one project."""
    search_roots: list[Path]
    if project_name:
        search_roots = [PROJECTS_DIR / project_name]
    else:
        search_roots = [path for path in PROJECTS_DIR.iterdir() if path.is_dir()]

    for project_dir in search_roots:
        path = job_file_path(project_dir, job_id)
        if path.exists():
            return path, read_job_file(path)
    return None


def make_job_response(job: dict[str, Any]) -> dict[str, Any]:
    """Return a compact, tool-friendly job response."""
    result = job.get("result") if isinstance(job.get("result"), dict) else {}
    request = job.get("request") if isinstance(job.get("request"), dict) else {}
    error = job.get("error") if isinstance(job.get("error"), dict) else job.get("error")
    return {
        "status": str(job.get("status") or JOB_STATUS_FAILED),
        "job_id": str(job.get("job_id") or ""),
        "project_name": str(job.get("project_name") or ""),
        "project_dir": str(job.get("project_dir") or ""),
        "kind": str(request.get("kind") or ""),
        "current_stage": str(job.get("current_stage") or "queued"),
        "retryable": bool(result.get("retryable", job.get("status") in {JOB_STATUS_FAILED, JOB_STATUS_PARTIAL})),
        "suggestion": str(result.get("suggestion") or job.get("suggestion") or ""),
        "requested_stage": str(job.get("requested_stage") or ""),
        "created_utc": str(job.get("created_utc") or ""),
        "updated_utc": str(job.get("updated_utc") or ""),
        "pid": job.get("pid"),
        "log_path": str(job.get("log_path") or ""),
        "request": request,
        "result": result,
        "error": error,
        "progress": job.get("progress"),
        "progress_kind": job.get("progress_kind"),
        "progress_label": str(job.get("progress_label") or ""),
        "progress_detail": str(job.get("progress_detail") or ""),
        "progress_scene_id": job.get("progress_scene_id"),
        "progress_scene_uid": job.get("progress_scene_uid"),
        "progress_status": str(job.get("progress_status") or ""),
    }


def _log_file_path(project_dir: Path, job_id: str) -> Path:
    logs_dir = job_dir_for_project(project_dir)
    return logs_dir / f"{job_id}.log"


def create_job(
    *,
    project_name: str,
    requested_stage: str,
    request: dict[str, Any],
    overwrite: bool = False,
    project_dir: Path | None = None,
) -> tuple[Path, dict[str, Any]]:
    """Create a persisted job record and reserve its project directory."""
    project_dir = Path(project_dir) if project_dir is not None else ensure_project_dir(project_name, overwrite=overwrite)
    project_dir.mkdir(parents=True, exist_ok=True)
    job_id = str(uuid4())
    job = {
        "job_id": job_id,
        "project_name": project_dir.name,
        "project_dir": str(project_dir),
        "requested_stage": requested_stage,
        "status": JOB_STATUS_QUEUED,
        "current_stage": "queued",
        "created_utc": utc_now_iso(),
        "updated_utc": utc_now_iso(),
        "pid": None,
        "request": request,
        "result": {},
        "error": None,
        "suggestion": "",
        "log_path": str(_log_file_path(project_dir, job_id)),
        "progress": 0.0,
        "progress_kind": "",
        "progress_label": "",
        "progress_detail": "",
        "progress_scene_id": None,
        "progress_scene_uid": None,
        "progress_status": "",
    }
    job_file = job_file_path(project_dir, job_id)
    write_job_file(job_file, job)
    return job_file, job


def start_job_process(job_file: Path) -> dict[str, Any]:
    """Spawn a local worker process to execute a persisted job."""
    job = read_job_file(job_file)
    log_path = Path(job["log_path"])
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_handle = log_path.open("ab")
    try:
        process = subprocess.Popen(
            [sys.executable, "-m", "core.job_runner", "--job-file", str(job_file)],
            cwd=str(Path(__file__).resolve().parent.parent),
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
    finally:
        log_handle.close()
    return update_job(job_file, pid=process.pid, status=JOB_STATUS_QUEUED)


def cancel_job(job_id: str, project_name: str | None = None) -> dict[str, Any]:
    """Terminate a running job and mark it cancelled."""
    found = find_job(job_id, project_name=project_name)
    if not found:
        return {
            "status": "error",
            "job_id": job_id,
            "project_name": project_name or "",
            "project_dir": "",
            "current_stage": "unknown",
            "retryable": False,
            "suggestion": "Check the job id and try again.",
            "requested_stage": "",
            "pid": None,
            "result": {},
            "error": {"message": f"Job not found: {job_id}"},
        }

    job_file, job = found
    pid = job.get("pid")
    if pid and str(job.get("status")) in {JOB_STATUS_QUEUED, JOB_STATUS_RUNNING}:
        try:
            os.kill(int(pid), signal.SIGTERM)
        except ProcessLookupError:
            pass

    updated = update_job(
        job_file,
        status=JOB_STATUS_CANCELLED,
        current_stage="cancelled",
        pid=None,
        suggestion="The job was cancelled.",
        result={"retryable": True, "suggestion": "Retry the job when ready."},
    )
    return make_job_response(updated)


def get_job_status(job_id: str, project_name: str | None = None) -> dict[str, Any]:
    """Return current status for a persisted job."""
    found = find_job(job_id, project_name=project_name)
    if not found:
        return {
            "status": "error",
            "job_id": job_id,
            "project_name": project_name or "",
            "project_dir": "",
            "current_stage": "unknown",
            "retryable": False,
            "suggestion": "Check the job id and try again.",
            "requested_stage": "",
            "pid": None,
            "result": {},
            "error": {"message": f"Job not found: {job_id}"},
        }
    _, job = found
    return make_job_response(job)


def _mark_running(job_file: Path, current_stage: str) -> dict[str, Any]:
    return update_job(job_file, status=JOB_STATUS_RUNNING, current_stage=current_stage)


def _update_job_progress(job_file: Path, payload: dict[str, Any]) -> dict[str, Any]:
    allowed = {
        "progress",
        "progress_kind",
        "progress_label",
        "progress_detail",
        "progress_scene_id",
        "progress_scene_uid",
        "progress_status",
    }
    changes = {key: value for key, value in payload.items() if key in allowed}
    if not changes:
        return read_job_file(job_file)
    return update_job(job_file, **changes)


def _set_signal_handlers(job_file: Path) -> None:
    global _ACTIVE_JOB_FILE
    _ACTIVE_JOB_FILE = job_file

    def _handle_signal(signum: int, _frame: Any) -> None:
        if _ACTIVE_JOB_FILE and _ACTIVE_JOB_FILE.exists():
            update_job(
                _ACTIVE_JOB_FILE,
                status=JOB_STATUS_CANCELLED,
                current_stage="cancelled",
                pid=None,
                suggestion="The job was cancelled.",
                result={"retryable": True, "suggestion": "Retry the job when ready."},
            )
        raise SystemExit(128 + signum)

    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)


def _finish_job(job_file: Path, *, status: str, result: dict[str, Any], error: dict[str, Any] | None = None) -> dict[str, Any]:
    return update_job(
        job_file,
        status=status,
        current_stage="done" if status == JOB_STATUS_SUCCEEDED else result.get("current_stage", "done"),
        pid=None,
        result=result,
        error=error,
        suggestion=str(result.get("suggestion") or ""),
        progress=1.0 if status in {JOB_STATUS_SUCCEEDED, JOB_STATUS_PARTIAL} else read_job_file(job_file).get("progress", 0.0),
        progress_kind="assets" if result.get("current_stage") == "assets" else result.get("current_stage", ""),
        progress_status="done" if status in {JOB_STATUS_SUCCEEDED, JOB_STATUS_PARTIAL} else "",
    )


def _run_make_video_job(job_file: Path, job: dict[str, Any]) -> dict[str, Any]:
    request = dict(job.get("request") or {})
    project_dir = Path(job["project_dir"])
    brief = dict(request.get("brief") or {})
    provider = request.get("provider")
    image_profile = request.get("image_profile")
    video_profile = request.get("video_profile")
    agent_demo_profile = request.get("agent_demo_profile")
    tts_profile = request.get("tts_profile")
    render_profile = request.get("render_profile")
    run_until = str(request.get("run_until") or "render")

    _mark_running(job_file, "storyboard")
    project_dir, plan = create_project_from_brief_service(
        project_name=project_dir.name,
        project_dir=project_dir,
        brief=brief,
        overwrite=False,
        provider=provider,
        image_profile=image_profile,
        video_profile=video_profile,
        agent_demo_profile=agent_demo_profile,
        tts_profile=tts_profile,
        render_profile=render_profile,
    )

    result: dict[str, Any] = {
        "retryable": False,
        "suggestion": "",
        "current_stage": "storyboard",
        "plan_path": str(project_dir / "plan.json"),
        "artifacts": collect_project_artifacts(project_dir),
    }

    if run_until in {"assets", "render"}:
        _mark_running(job_file, "assets")
        assets_result = generate_project_assets_service(
            project_dir,
            regenerate_images=bool(request.get("regenerate_images")),
            regenerate_videos=bool(request.get("regenerate_videos")),
            regenerate_audio=bool(request.get("regenerate_audio")),
            progress_callback=lambda payload: _update_job_progress(job_file, payload),
        )
        result["current_stage"] = "assets"
        result["assets"] = assets_result

        if (
            assets_result.get("image_failures")
            or assets_result.get("video_failures")
            or assets_result.get("audio_failures")
        ):
            result["retryable"] = True
            result["suggestion"] = "Review missing providers or failed scenes, then rerun the assets stage."

    if run_until == "render":
        _mark_running(job_file, "render")
        render_result = render_project_service(
            project_dir,
            output_filename=request.get("output_filename"),
            fps=request.get("fps"),
        )
        result["current_stage"] = "render"
        result["render"] = render_result
        result["video_path"] = render_result.get("video_path")
        result["retryable"] = bool(render_result.get("retryable")) or result["retryable"]
        if render_result.get("suggestion"):
            result["suggestion"] = str(render_result["suggestion"])

    result["artifacts"] = collect_project_artifacts(project_dir)
    result["plan_path"] = str(project_dir / "plan.json")

    if run_until == "render" and result.get("render", {}).get("status") == "partial_success":
        status = JOB_STATUS_PARTIAL
    elif (
        result.get("assets", {}).get("image_failures")
        or result.get("assets", {}).get("video_failures")
        or result.get("assets", {}).get("audio_failures")
    ):
        status = JOB_STATUS_PARTIAL
    else:
        status = JOB_STATUS_SUCCEEDED
    return _finish_job(job_file, status=status, result=result)


def _run_rerun_stage_job(job_file: Path, job: dict[str, Any]) -> dict[str, Any]:
    request = dict(job.get("request") or {})
    project_dir = Path(job["project_dir"])
    stage = str(request.get("stage") or "render")
    force = bool(request.get("force"))

    result: dict[str, Any] = {
        "retryable": False,
        "suggestion": "",
        "current_stage": stage,
        "artifacts": collect_project_artifacts(project_dir),
    }

    if stage == "storyboard":
        _mark_running(job_file, "storyboard")
        plan = rebuild_storyboard_service(project_dir, provider=request.get("provider"))
        result["plan_path"] = str(project_dir / "plan.json")
        result["scene_count"] = len(plan.get("scenes", []))
    elif stage == "assets":
        _mark_running(job_file, "assets")
        assets_result = generate_project_assets_service(
            project_dir,
            regenerate_images=force,
            regenerate_videos=force,
            regenerate_audio=force,
            progress_callback=lambda payload: _update_job_progress(job_file, payload),
        )
        result["assets"] = assets_result
        if (
            assets_result.get("image_failures")
            or assets_result.get("video_failures")
            or assets_result.get("audio_failures")
        ):
            result["retryable"] = True
            result["suggestion"] = "Review failed scenes or provider configuration, then rerun assets."
    elif stage == "render":
        _mark_running(job_file, "render")
        render_result = render_project_service(
            project_dir,
            output_filename=request.get("output_filename"),
            fps=request.get("fps"),
        )
        result["render"] = render_result
        result["video_path"] = render_result.get("video_path")
        result["retryable"] = bool(render_result.get("retryable"))
        result["suggestion"] = str(render_result.get("suggestion") or "")
    else:
        return _finish_job(
            job_file,
            status=JOB_STATUS_FAILED,
            result={"retryable": False, "suggestion": "Use storyboard, assets, or render."},
            error={"message": f"Unsupported rerun stage: {stage}"},
        )

    result["artifacts"] = collect_project_artifacts(project_dir)
    status = JOB_STATUS_SUCCEEDED
    if (
        stage == "assets"
        and (
            result.get("assets", {}).get("image_failures")
            or result.get("assets", {}).get("video_failures")
            or result.get("assets", {}).get("audio_failures")
        )
    ):
        status = JOB_STATUS_PARTIAL
    if stage == "render" and result.get("render", {}).get("status") == "partial_success":
        status = JOB_STATUS_PARTIAL
    return _finish_job(job_file, status=status, result=result)


def _run_agent_demo_job(job_file: Path, job: dict[str, Any]) -> dict[str, Any]:
    request = dict(job.get("request") or {})
    project_dir = Path(job["project_dir"])
    project_name = str(job.get("project_name") or project_dir.name)
    preferred_agent = str(request.get("preferred_agent") or "").strip().lower() or None
    scene_uids = [
        str(value).strip()
        for value in (request.get("scene_uids") or [])
        if str(value).strip()
    ]
    workspace_path = str(request.get("workspace_path") or "").strip() or None
    app_url = str(request.get("app_url") or "").strip() or None
    launch_command = str(request.get("launch_command") or "").strip() or None
    expected_url = str(request.get("expected_url") or "").strip() or None
    run_until = str(request.get("run_until") or "assets").strip().lower() or "assets"

    selected_agent = choose_agent_cli(preferred_agent)
    if not selected_agent:
        return _finish_job(
            job_file,
            status=JOB_STATUS_FAILED,
            result={"retryable": False, "suggestion": "Install Codex CLI or Claude Code to use Agent Demo."},
            error={"message": "No supported agent CLI is installed. Expected `codex` or `claude` in PATH."},
        )

    agent_name, agent_path = selected_agent
    artifacts_dir = project_dir / ".cathode" / "agent_demo" / str(job.get("job_id") or "latest")
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    prompt_path = artifacts_dir / "prompt.txt"

    update_job(
        job_file,
        status=JOB_STATUS_RUNNING,
        current_stage="agent_demo",
        progress_kind="agent_demo",
        progress_label="Preparing agent demo prompt",
        progress_detail=f"{project_name}: {len(scene_uids) if scene_uids else 'all'} video scene target(s)",
        progress_status="building_prompt",
    )
    prompt = build_agent_demo_prompt(
        project_dir=project_dir,
        scene_uids=scene_uids or None,
        workspace_path=workspace_path,
        app_url=app_url,
        launch_command=launch_command,
        expected_url=expected_url,
        run_until=run_until,
    )

    update_job(
        job_file,
        status=JOB_STATUS_RUNNING,
        current_stage="agent_demo",
        progress_kind="agent_demo",
        progress_label=f"Running {agent_name} agent demo",
        progress_detail=f"Workspace: {workspace_path or project_dir}",
        progress_status="running_agent",
        result={
            "agent": agent_name,
            "agent_path": agent_path,
            "prompt_path": str(prompt_path),
            "artifacts_dir": str(artifacts_dir),
            "scene_uids": scene_uids,
        },
    )

    run_agent_demo_cli(
        agent_name=agent_name,
        prompt=prompt,
        prompt_path=prompt_path,
        project_dir=project_dir,
        workspace_path=workspace_path,
    )

    refreshed_plan = load_plan(project_dir)
    scene_count = len(refreshed_plan.get("scenes", [])) if isinstance(refreshed_plan, dict) else 0
    result = {
        "retryable": False,
        "suggestion": "",
        "current_stage": "agent_demo",
        "agent": agent_name,
        "prompt_path": str(prompt_path),
        "artifacts_dir": str(artifacts_dir),
        "scene_uids": scene_uids,
        "scene_count": scene_count,
        "run_until": run_until,
        "artifacts": collect_project_artifacts(project_dir),
    }
    return _finish_job(job_file, status=JOB_STATUS_SUCCEEDED, result=result)


def run_job_file(job_file: Path) -> dict[str, Any]:
    """Execute a persisted job in the current process."""
    _set_signal_handlers(job_file)
    job = read_job_file(job_file)
    request = dict(job.get("request") or {})
    kind = str(request.get("kind") or "make_video")
    try:
        if kind == "make_video":
            return _run_make_video_job(job_file, job)
        if kind == "rerun_stage":
            return _run_rerun_stage_job(job_file, job)
        if kind == "agent_demo":
            return _run_agent_demo_job(job_file, job)
        return _finish_job(
            job_file,
            status=JOB_STATUS_FAILED,
            result={"retryable": False, "suggestion": "Use a supported Cathode job type."},
            error={"message": f"Unsupported job kind: {kind}"},
        )
    except Exception as exc:  # pragma: no cover - surfaced in job metadata
        return _finish_job(
            job_file,
            status=JOB_STATUS_FAILED,
            result={"retryable": True, "suggestion": "Inspect the job log and retry after fixing the input or environment."},
            error={"message": str(exc)},
        )


def create_make_video_job(
    *,
    project_name: str,
    brief: dict[str, Any],
    run_until: str = "render",
    provider: str | None = None,
    image_profile: dict[str, Any] | None = None,
    video_profile: dict[str, Any] | None = None,
    agent_demo_profile: dict[str, Any] | None = None,
    tts_profile: dict[str, Any] | None = None,
    render_profile: dict[str, Any] | None = None,
    overwrite: bool = False,
    output_filename: str | None = None,
    fps: int | None = None,
) -> dict[str, Any]:
    """Create and start a background make-video job."""
    normalized_brief, normalized_video_profile, normalized_render_profile = prepare_project_execution_profiles(
        brief=brief,
        video_profile=video_profile,
        render_profile=render_profile,
        agent_demo_profile=agent_demo_profile,
    )
    normalized_agent_demo_profile = normalize_agent_demo_profile(agent_demo_profile)
    job_file, _ = create_job(
        project_name=project_name,
        requested_stage=run_until,
        overwrite=overwrite,
        request={
            "kind": "make_video",
            "brief": normalized_brief,
            "provider": provider,
            "image_profile": image_profile,
            "video_profile": normalized_video_profile,
            "agent_demo_profile": normalized_agent_demo_profile or None,
            "tts_profile": tts_profile,
            "render_profile": normalized_render_profile,
            "run_until": run_until,
            "output_filename": output_filename,
            "fps": fps,
        },
    )
    job = start_job_process(job_file)
    return make_job_response(job)


def create_rerun_stage_job(
    *,
    project_name: str,
    stage: str,
    force: bool = False,
    provider: str | None = None,
    output_filename: str | None = None,
    fps: int | None = None,
) -> dict[str, Any]:
    """Create and start a background rerun-stage job for an existing project."""
    project_dir = PROJECTS_DIR / project_name
    if not project_dir.exists() or not (project_dir / "plan.json").exists():
        return {
            "status": "error",
            "job_id": "",
            "project_name": project_name,
            "project_dir": str(project_dir),
            "current_stage": "unknown",
            "retryable": False,
            "suggestion": "Create the project first or choose an existing one.",
            "requested_stage": stage,
            "pid": None,
            "result": {},
            "error": {"message": f"Project not found: {project_name}"},
        }

    plan = load_plan(project_dir)
    if not plan:
        return {
            "status": "error",
            "job_id": "",
            "project_name": project_name,
            "project_dir": str(project_dir),
            "current_stage": "unknown",
            "retryable": False,
            "suggestion": "Repair the project's plan.json before retrying.",
            "requested_stage": stage,
            "pid": None,
            "result": {},
            "error": {"message": f"Could not load plan.json for project: {project_name}"},
        }
    save_plan(project_dir, plan)

    job_file, _ = create_job(
        project_name=project_name,
        requested_stage=stage,
        overwrite=False,
        project_dir=project_dir,
        request={
            "kind": "rerun_stage",
            "stage": stage,
            "force": force,
            "provider": provider,
            "output_filename": output_filename,
            "fps": fps,
        },
    )
    job = start_job_process(job_file)
    return make_job_response(job)


def create_agent_demo_job(
    *,
    project_name: str,
    scene_uids: list[str] | None = None,
    preferred_agent: str | None = None,
    workspace_path: str | None = None,
    app_url: str | None = None,
    launch_command: str | None = None,
    expected_url: str | None = None,
    run_until: str = "assets",
) -> dict[str, Any]:
    """Create and start an agent-driven demo workflow job for an existing project."""
    project_dir = PROJECTS_DIR / project_name
    if not project_dir.exists() or not (project_dir / "plan.json").exists():
        return {
            "status": "error",
            "job_id": "",
            "project_name": project_name,
            "project_dir": str(project_dir),
            "current_stage": "unknown",
            "retryable": False,
            "suggestion": "Create the project first or choose an existing one.",
            "requested_stage": "agent_demo",
            "pid": None,
            "result": {},
            "error": {"message": f"Project not found: {project_name}"},
        }

    plan = load_plan(project_dir)
    if not plan:
        return {
            "status": "error",
            "job_id": "",
            "project_name": project_name,
            "project_dir": str(project_dir),
            "current_stage": "unknown",
            "retryable": False,
            "suggestion": "Repair the project's plan.json before retrying.",
            "requested_stage": "agent_demo",
            "pid": None,
            "result": {},
            "error": {"message": f"Could not load plan.json for project: {project_name}"},
        }
    save_plan(project_dir, plan)

    normalized_scene_uids = [str(uid).strip() for uid in (scene_uids or []) if str(uid).strip()]
    job_file, _ = create_job(
        project_name=project_name,
        requested_stage="agent_demo",
        overwrite=False,
        project_dir=project_dir,
        request={
            "kind": "agent_demo",
            "scene_uids": normalized_scene_uids,
            "preferred_agent": preferred_agent,
            "workspace_path": workspace_path,
            "app_url": app_url,
            "launch_command": launch_command,
            "expected_url": expected_url,
            "run_until": run_until,
        },
    )
    job = start_job_process(job_file)
    return make_job_response(job)


def main() -> None:
    """CLI entrypoint for worker subprocesses."""
    parser = argparse.ArgumentParser(description="Run a persisted Cathode background job.")
    parser.add_argument("--job-file", required=True, help="Path to the persisted job JSON file.")
    args = parser.parse_args()
    run_job_file(Path(args.job_file))


if __name__ == "__main__":
    main()
