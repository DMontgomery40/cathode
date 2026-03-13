"""Style reference upload and analysis endpoints."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, File, HTTPException, Query, UploadFile

from core.director import analyze_style_references
from core.project_store import load_plan, save_plan
from core.runtime import PROJECTS_DIR, choose_llm_provider
from server.services.uploads import STYLE_REF_UPLOAD_SPEC, persist_upload
from server.schemas.style_refs import StyleRefsResponse

router = APIRouter()
MAX_STYLE_REFERENCE_FILES = 12


def _project_dir(project: str) -> Path:
    d = PROJECTS_DIR / project
    if not d.exists():
        raise HTTPException(status_code=404, detail=f"Project not found: {project}")
    return d


@router.post("/projects/{project}/style-refs")
async def upload_style_refs(
    project: str,
    files: list[UploadFile] = File(...),
    provider: str | None = Query(None),
) -> dict[str, Any]:
    if len(files) > MAX_STYLE_REFERENCE_FILES:
        raise HTTPException(status_code=400, detail=f"Too many style references; max is {MAX_STYLE_REFERENCE_FILES}.")

    project_dir = _project_dir(project)
    plan = load_plan(project_dir)
    if plan is None:
        raise HTTPException(status_code=404, detail=f"No plan.json for project: {project}")

    refs_dir = project_dir / "style_refs"
    refs_dir.mkdir(parents=True, exist_ok=True)

    meta = plan.setdefault("meta", {})
    brief = meta.setdefault("brief", {})
    existing_paths: list[str] = []
    for item in brief.get("style_reference_paths", []):
        if not item:
            continue
        candidate = Path(str(item))
        if not candidate.is_absolute():
            candidate = (project_dir / candidate).resolve()
        if candidate.exists():
            existing_paths.append(str(candidate))

    saved_paths = list(existing_paths)
    start_index = len(existing_paths) + 1
    for i, upload in enumerate(files, start=start_index):
        dest = await persist_upload(
            upload,
            dest_dir=refs_dir,
            stem=f"style_ref_{i:02d}",
            spec=STYLE_REF_UPLOAD_SPEC,
        )
        saved_paths.append(str(dest))

    if not saved_paths:
        raise HTTPException(status_code=400, detail="No valid style reference files were uploaded.")

    llm_provider = provider or choose_llm_provider()
    try:
        summary = analyze_style_references(saved_paths, brief, provider=llm_provider)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    brief["style_reference_summary"] = summary
    brief["style_reference_paths"] = saved_paths
    return save_plan(project_dir, plan)


@router.get("/projects/{project}/style-refs", response_model=StyleRefsResponse)
async def get_style_refs(project: str) -> StyleRefsResponse:
    project_dir = _project_dir(project)
    plan = load_plan(project_dir)
    if plan is None:
        raise HTTPException(status_code=404, detail=f"No plan.json for project: {project}")

    brief = plan.get("meta", {}).get("brief", {})
    return StyleRefsResponse(
        style_reference_paths=brief.get("style_reference_paths", []),
        style_reference_summary=brief.get("style_reference_summary", ""),
    )
