"""Short-form vertical video endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from core.job_runner import create_make_video_job
from core.short_form import RUN_UNTIL_VALUES, build_short_form_payload, short_form_options
from server.schemas.short_form import ShortFormRequest

router = APIRouter()


@router.get("/short-form/options")
async def get_short_form_options() -> dict[str, Any]:
    """Return backend-owned option metadata for the short-form surface."""
    return short_form_options()


@router.post("/short-form/preview")
async def preview_short_form_payload(body: ShortFormRequest) -> dict[str, Any]:
    """Return the betTube Studio job payload that the short-form surface will launch."""
    return build_short_form_payload(body.model_dump())


@router.post("/short-form/jobs")
async def dispatch_short_form_job(body: ShortFormRequest) -> dict[str, Any]:
    raw_run_until = str(body.run_until or "storyboard").strip().lower().replace("_", "-").replace(" ", "-")
    if raw_run_until not in RUN_UNTIL_VALUES:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "run_until must be storyboard, assets, or render",
                "operatorHint": "Choose one of the supported short-form run depths before launching the job.",
            },
        )

    payload = build_short_form_payload(body.model_dump())
    run_until = str(payload.get("run_until") or body.run_until or "storyboard")

    result = create_make_video_job(
        project_name=str(payload["project_name"]),
        brief=payload["brief"],
        run_until=run_until,
        provider=body.provider,
        image_profile=payload.get("image_profile"),
        video_profile=payload["video_profile"],
        tts_profile=payload["tts_profile"],
        render_profile=payload["render_profile"],
        overwrite=body.overwrite,
    )
    if result.get("status") == "error":
        error = result.get("error") if isinstance(result.get("error"), dict) else {}
        raise HTTPException(
            status_code=400,
            detail={
                "message": error.get("message") or "Short-form job failed before it could start.",
                "operatorHint": "Preview the payload, check the project name and configured providers, then retry.",
            },
        )
    return result
