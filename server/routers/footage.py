"""Footage upload endpoints for project-level demo clips and stills."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, File, HTTPException, UploadFile

from core.demo_assets import build_footage_summary, normalize_footage_manifest
from core.project_store import load_plan, save_plan
from core.runtime import PROJECTS_DIR
from server.services.uploads import IMAGE_UPLOAD_SPEC, VIDEO_UPLOAD_SPEC, persist_upload

router = APIRouter()
MAX_FOOTAGE_FILES = 24
_VIDEO_SUFFIXES = set(VIDEO_UPLOAD_SPEC.allowed_extensions)
_IMAGE_SUFFIXES = set(IMAGE_UPLOAD_SPEC.allowed_extensions)


def _project_dir(project: str) -> Path:
    path = PROJECTS_DIR / project
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Project not found: {project}")
    return path


def _choose_upload_spec(upload: UploadFile):
    suffix = Path(upload.filename or "").suffix.lower()
    content_type = (upload.content_type or "").split(";")[0].strip().lower()
    if suffix in _VIDEO_SUFFIXES or content_type in VIDEO_UPLOAD_SPEC.allowed_content_types:
        return VIDEO_UPLOAD_SPEC, "video_clip"
    if suffix in _IMAGE_SUFFIXES or content_type in IMAGE_UPLOAD_SPEC.allowed_content_types:
        return IMAGE_UPLOAD_SPEC, "image_still"
    raise HTTPException(
        status_code=415,
        detail="Unsupported footage type. Upload a video clip or image still.",
    )


@router.post("/projects/{project}/footage")
async def upload_footage(project: str, files: list[UploadFile] = File(...)) -> dict[str, Any]:
    if len(files) > MAX_FOOTAGE_FILES:
        raise HTTPException(status_code=400, detail=f"Too many footage files; max is {MAX_FOOTAGE_FILES}.")

    project_dir = _project_dir(project)
    plan = load_plan(project_dir)
    if plan is None:
        raise HTTPException(status_code=404, detail=f"No plan.json for project: {project}")

    brief = plan.setdefault("meta", {}).setdefault("brief", {})
    existing_manifest = normalize_footage_manifest(
        brief.get("footage_manifest") or plan.get("meta", {}).get("footage_manifest") or [],
        base_dir=project_dir,
    )
    manifest: list[dict[str, Any]] = list(existing_manifest)

    next_index = len(existing_manifest) + 1
    clips_dir = project_dir / "clips"
    clips_dir.mkdir(parents=True, exist_ok=True)

    for offset, upload in enumerate(files, start=next_index):
        spec, kind = _choose_upload_spec(upload)
        stem = f"footage_{offset:02d}"
        dest = await persist_upload(
            upload,
            dest_dir=clips_dir,
            stem=stem,
            spec=spec,
        )
        manifest.append(
            {
                "id": stem,
                "label": Path(upload.filename or stem).stem.replace("_", " ").strip() or stem,
                "path": str(dest),
                "kind": kind,
                "review_status": "accept",
            }
        )

    normalized = normalize_footage_manifest(manifest, base_dir=project_dir)
    brief["footage_manifest"] = normalized
    brief["available_footage"] = build_footage_summary(normalized)
    plan.setdefault("meta", {})["footage_manifest"] = normalized
    return save_plan(project_dir, plan)
