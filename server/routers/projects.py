"""Project list, creation, detail, and deletion endpoints."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException

from core.job_runner import list_project_jobs
from core.pipeline_service import create_project_from_brief_service
from core.project_store import annotate_plan_asset_existence, collect_project_artifacts, list_projects, load_plan
from core.runtime import PROJECTS_DIR
from server.schemas.projects import CreateProjectRequest, ProjectSummary

router = APIRouter()


def _project_asset_path(project_dir: Path, raw_path: Any) -> str | None:
    value = str(raw_path or "").strip()
    if not value:
        return None

    candidate = Path(value)
    if not candidate.is_absolute():
        normalized = value.replace("\\", "/").lstrip("/")
        marker = f"projects/{project_dir.name}/"
        index = normalized.rfind(marker)
        if index >= 0:
            normalized = normalized[index + len(marker):]
        candidate = (project_dir / normalized).resolve()
    else:
        candidate = candidate.resolve()

    project_root = project_dir.resolve()
    if not str(candidate).startswith(str(project_root)):
        return None
    if not candidate.exists() or not candidate.is_file():
        return None

    return str(candidate.relative_to(project_root)).replace("\\", "/")


@router.get("/projects", response_model=list[ProjectSummary])
async def get_projects() -> list[ProjectSummary]:
    summaries: list[ProjectSummary] = []
    for name in list_projects():
        project_dir = PROJECTS_DIR / name
        plan = load_plan(project_dir)
        if plan is None:
            continue
        meta = plan.get("meta") or {}
        video_path = _project_asset_path(project_dir, meta.get("video_path"))
        thumbnail_path = None
        for scene in plan.get("scenes", []):
            motion = scene.get("motion") if isinstance(scene.get("motion"), dict) else {}
            thumbnail_path = (
                _project_asset_path(project_dir, scene.get("image_path"))
                or _project_asset_path(project_dir, scene.get("video_path"))
                or _project_asset_path(project_dir, motion.get("preview_path"))
                or _project_asset_path(project_dir, motion.get("render_path"))
                or _project_asset_path(project_dir, scene.get("preview_path"))
            )
            if thumbnail_path:
                break
        summaries.append(
            ProjectSummary(
                name=name,
                scene_count=len(plan.get("scenes", [])),
                has_video=bool(video_path),
                video_path=video_path,
                thumbnail_path=thumbnail_path,
                image_profile=meta.get("image_profile"),
                tts_profile=meta.get("tts_profile"),
            )
        )
    return summaries


@router.post("/projects", response_model=dict[str, Any])
async def create_project(body: CreateProjectRequest) -> dict[str, Any]:
    try:
        _project_dir, plan = create_project_from_brief_service(
            project_name=body.project_name,
            brief=body.brief,
            overwrite=body.overwrite,
            provider=body.provider,
            image_profile=body.image_profile,
            video_profile=body.video_profile,
            agent_demo_profile=body.agent_demo_profile,
            tts_profile=body.tts_profile,
            render_profile=body.render_profile,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return annotate_plan_asset_existence(_project_dir, plan)


@router.get("/projects/{project}")
async def get_project_detail(project: str) -> dict[str, Any]:
    project_dir = PROJECTS_DIR / project
    if not project_dir.exists():
        raise HTTPException(status_code=404, detail=f"Project not found: {project}")
    plan = load_plan(project_dir)
    if plan is None:
        raise HTTPException(status_code=404, detail=f"No plan.json for project: {project}")
    return {
        "plan": annotate_plan_asset_existence(project_dir, plan),
        "artifacts": collect_project_artifacts(project_dir),
        "jobs": list_project_jobs(project_dir),
    }


@router.delete("/projects/{project}")
async def delete_project(project: str) -> dict[str, str]:
    project_dir = PROJECTS_DIR / project
    if not project_dir.exists():
        raise HTTPException(status_code=404, detail=f"Project not found: {project}")
    shutil.rmtree(project_dir)
    return {"status": "deleted", "project": project}
