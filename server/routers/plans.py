"""Plan CRUD and storyboard rebuild endpoints."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, Body, HTTPException

from core.pipeline_service import rebuild_storyboard_service
from core.project_schema import (
    infer_composition_mode,
    normalize_agent_demo_profile,
    normalize_brief,
    remotion_explicitly_enabled,
    resolve_render_backend_details,
    resolve_render_backend,
    resolve_render_strategy,
)
from core.project_store import annotate_plan_asset_existence, load_plan, save_plan
from core.remotion_render import build_remotion_manifest
from core.runtime import PROJECTS_DIR
from server.schemas.plans import RebuildStoryboardRequest

router = APIRouter()


def _project_dir(project: str):
    d = PROJECTS_DIR / project
    if not d.exists():
        raise HTTPException(status_code=404, detail=f"Project not found: {project}")
    return d


@router.get("/projects/{project}/plan")
async def get_plan(project: str) -> dict[str, Any]:
    project_dir = _project_dir(project)
    plan = load_plan(project_dir)
    if plan is None:
        raise HTTPException(status_code=404, detail=f"No plan.json for project: {project}")
    return annotate_plan_asset_existence(project_dir, plan)


@router.put("/projects/{project}/plan")
async def put_plan(project: str, body: dict[str, Any]) -> dict[str, Any]:
    project_dir = _project_dir(project)
    return annotate_plan_asset_existence(project_dir, save_plan(project_dir, body))


@router.post("/projects/{project}/storyboard")
async def rebuild_storyboard(
    project: str,
    body: RebuildStoryboardRequest | None = Body(None),
) -> dict[str, Any]:
    project_dir = _project_dir(project)
    if body and (body.brief is not None or body.agent_demo_profile is not None):
        plan = load_plan(project_dir)
        if plan is None:
            raise HTTPException(status_code=404, detail=f"No plan.json for project: {project}")
        meta = plan.setdefault("meta", {})
        if body.brief is not None:
            meta["brief"] = normalize_brief(body.brief, base_dir=project_dir)
        if body.agent_demo_profile is not None:
            meta["agent_demo_profile"] = normalize_agent_demo_profile(body.agent_demo_profile)
        composition_mode = infer_composition_mode(
            body.brief if body and body.brief is not None else meta.get("brief"),
            agent_demo_profile=meta.get("agent_demo_profile"),
        )
        meta.setdefault("brief", {})
        meta["brief"]["composition_mode"] = composition_mode
        render_profile = dict(meta.get("render_profile") or {})
        render_profile["render_strategy"] = resolve_render_strategy(
            render_profile.get("render_strategy")
        )
        if render_profile["render_strategy"] == "auto":
            render_profile.pop("render_backend", None)
            render_profile.pop("render_backend_reason", None)
        else:
            backend, reason = resolve_render_backend_details(
                render_profile,
                composition_mode=composition_mode,
            )
            render_profile["render_backend"] = backend
            render_profile["render_backend_reason"] = reason
        meta["render_profile"] = {**render_profile}
        save_plan(project_dir, plan)
    provider = body.provider if body else None
    try:
        return annotate_plan_asset_existence(
            project_dir,
            rebuild_storyboard_service(project_dir, provider=provider),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/projects/{project}/remotion-manifest")
async def get_remotion_manifest(project: str) -> dict[str, Any]:
    project_dir = _project_dir(project)
    plan = load_plan(project_dir)
    if plan is None:
        raise HTTPException(status_code=404, detail=f"No plan.json for project: {project}")

    render_profile = plan.get("meta", {}).get("render_profile")
    if not remotion_explicitly_enabled(render_profile):
        raise HTTPException(status_code=400, detail="Remotion manifest requires render_strategy=force_remotion.")
    try:
        return build_remotion_manifest(
            project_dir=project_dir,
            plan=plan,
            output_path=Path(project_dir) / "__player_preview__.mp4",
            render_profile=render_profile if isinstance(render_profile, dict) else None,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
