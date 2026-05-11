"""Per-scene operation endpoints (upload, generate, refine, preview)."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Body, HTTPException, UploadFile
from starlette.concurrency import run_in_threadpool

from core.costs import append_actual_cost_entry, image_edit_entry, image_generation_entry, tts_entry, video_generation_entry
from core.director import refine_narration_with_metadata, refine_prompt_with_metadata
from core.image_gen import canonicalize_exact_text_edit_prompt, edit_image, generate_scene_image
from core.project_store import annotate_plan_asset_existence, load_plan, save_plan
from core.project_schema import remotion_explicitly_enabled
from core.remotion_render import build_remotion_manifest, render_manifest_with_remotion
from core.runtime import PROJECTS_DIR, choose_llm_provider, resolve_image_profile, resolve_tts_profile, resolve_video_profile
from core.video_gen import generate_scene_video_result
from core.video_assembly import preview_scene
from core.voice_gen import generate_scene_audio_result
from core.pipeline_service import (
    _canonical_scene_image_path,
    replace_scene_image_preserving_identity,
    tts_kwargs_from_profile,
)
from server.services.uploads import IMAGE_UPLOAD_SPEC, VIDEO_UPLOAD_SPEC, persist_upload
from server.schemas.scenes import (
    AudioGenerateRequest,
    ImageEditRequest,
    ImageGenerateRequest,
    NarrationRefineRequest,
    PromptRefineRequest,
    VideoGenerateRequest,
)

router = APIRouter()
IMAGE_ACTION_HISTORY_LIMIT = 20


def _project_dir(project: str) -> Path:
    d = PROJECTS_DIR / project
    if not d.exists():
        raise HTTPException(status_code=404, detail=f"Project not found: {project}")
    return d


def _load_plan_or_404(project_dir: Path) -> dict[str, Any]:
    plan = load_plan(project_dir)
    if plan is None:
        raise HTTPException(status_code=404, detail=f"No plan.json in {project_dir.name}")
    return plan


def _present_plan(project_dir: Path, plan: dict[str, Any]) -> dict[str, Any]:
    return annotate_plan_asset_existence(project_dir, plan)


def _find_scene(plan: dict[str, Any], scene_uid: str) -> tuple[int, dict[str, Any]]:
    for i, s in enumerate(plan.get("scenes", [])):
        if s.get("uid") == scene_uid:
            return i, s
    raise HTTPException(status_code=404, detail=f"Scene not found: {scene_uid}")


def _error_message(detail: Any) -> str:
    if isinstance(detail, dict):
        message = str(detail.get("message") or "").strip()
        if message:
            return message
    return str(detail or "Request failed.").strip()


def _render_preview_asset(
    *,
    scene: dict[str, Any],
    scene_uid: str,
    project_dir: Path,
    plan: dict[str, Any],
    render_profile: dict[str, Any],
) -> tuple[Path | None, dict[str, Any] | None]:
    if str(scene.get("scene_type") or "image").strip().lower() == "motion":
        if not remotion_explicitly_enabled(render_profile):
            raise HTTPException(
                status_code=400,
                detail="Motion preview requires render_strategy=force_remotion.",
            )
        output_path = project_dir / "previews" / f"preview_{scene_uid}.mp4"
        manifest = build_remotion_manifest(
            project_dir=project_dir,
            plan=plan,
            output_path=output_path,
            render_profile=render_profile,
            preview_scene_uid=scene_uid,
        )
        preview_path = render_manifest_with_remotion(manifest, output_path=output_path)
        motion = scene.get("motion") if isinstance(scene.get("motion"), dict) else {}
        motion["preview_path"] = str(preview_path)
        composition = scene.get("composition") if isinstance(scene.get("composition"), dict) else {}
        composition["preview_path"] = str(preview_path)
        scene["composition"] = composition
        return preview_path, motion

    return preview_scene(scene, project_dir, render_profile=render_profile), None


def _record_image_action(
    plan: dict[str, Any],
    *,
    scene: dict[str, Any],
    scene_index: int,
    action: str,
    status: str,
    request: dict[str, Any],
    result: dict[str, Any] | None = None,
    error: str | None = None,
) -> None:
    meta = plan.get("meta")
    if not isinstance(meta, dict):
        meta = {}
        plan["meta"] = meta

    raw_history = meta.get("image_action_history")
    history = [item for item in raw_history if isinstance(item, dict)] if isinstance(raw_history, list) else []
    scene_title = str(scene.get("title") or "").strip() or f"Scene {scene_index + 1}"
    entry = {
        "action": action,
        "status": status,
        "scene_uid": str(scene.get("uid") or ""),
        "scene_index": scene_index + 1,
        "scene_title": scene_title,
        "request": request,
        "result": result or {},
        "error": error or None,
        "happened_at": datetime.now(timezone.utc).isoformat(),
    }
    meta["image_action_history"] = [entry, *history][:IMAGE_ACTION_HISTORY_LIMIT]


def _save_failed_image_action(
    project_dir: Path,
    plan: dict[str, Any],
    *,
    scene: dict[str, Any],
    scene_index: int,
    action: str,
    request: dict[str, Any],
    error: str,
) -> None:
    _record_image_action(
        plan,
        scene=scene,
        scene_index=scene_index,
        action=action,
        status="error",
        request=request,
        error=error,
    )
    save_plan(project_dir, plan)


# ---- File upload endpoints ------------------------------------------------


@router.post("/projects/{project}/scenes/{scene_uid}/image-upload")
async def upload_scene_image(project: str, scene_uid: str, file: UploadFile) -> dict[str, Any]:
    project_dir = _project_dir(project)
    plan = _load_plan_or_404(project_dir)
    idx, scene = _find_scene(plan, scene_uid)
    request_payload = {
        "filename": str(file.filename or "").strip(),
        "content_type": str(file.content_type or "").strip() or "unknown",
        "size": file.size,
    }

    try:
        dest = await persist_upload(
            file,
            dest_dir=project_dir / "images",
            stem=f"image_{scene_uid}",
            spec=IMAGE_UPLOAD_SPEC,
        )
    except HTTPException as exc:
        _save_failed_image_action(
            project_dir,
            plan,
            scene=scene,
            scene_index=idx,
            action="upload",
            request=request_payload,
            error=_error_message(exc.detail),
        )
        raise
    except Exception as exc:
        _save_failed_image_action(
            project_dir,
            plan,
            scene=scene,
            scene_index=idx,
            action="upload",
            request=request_payload,
            error=str(exc),
        )
        raise

    scene["image_path"] = str(dest)
    scene["video_path"] = None
    scene["preview_path"] = None
    scene["scene_type"] = "image"
    plan["scenes"][idx] = scene
    _record_image_action(
        plan,
        scene=scene,
        scene_index=idx,
        action="upload",
        status="succeeded",
        request=request_payload,
        result={
            "image_path": str(dest),
            "scene_type": "image",
        },
    )
    return _present_plan(project_dir, save_plan(project_dir, plan))


@router.post("/projects/{project}/scenes/{scene_uid}/video-upload")
async def upload_scene_video(project: str, scene_uid: str, file: UploadFile) -> dict[str, Any]:
    project_dir = _project_dir(project)
    plan = _load_plan_or_404(project_dir)
    idx, scene = _find_scene(plan, scene_uid)

    dest = await persist_upload(
        file,
        dest_dir=project_dir / "clips",
        stem=f"clip_{scene_uid}",
        spec=VIDEO_UPLOAD_SPEC,
    )

    scene["video_path"] = str(dest)
    scene["image_path"] = None
    scene["preview_path"] = None
    scene["scene_type"] = "video"
    scene["video_audio_source"] = "narration"
    plan["scenes"][idx] = scene
    return _present_plan(project_dir, save_plan(project_dir, plan))


# ---- Generation endpoints -------------------------------------------------


@router.post("/projects/{project}/scenes/{scene_uid}/image-generate")
async def generate_image_for_scene(
    project: str,
    scene_uid: str,
    body: ImageGenerateRequest | None = Body(None),
) -> dict[str, Any]:
    project_dir = _project_dir(project)
    plan = _load_plan_or_404(project_dir)
    idx, scene = _find_scene(plan, scene_uid)
    meta = plan.get("meta", {})
    brief = meta.get("brief", {})
    composition = scene.get("composition") if isinstance(scene.get("composition"), dict) else {}
    scene_type = str(scene.get("scene_type") or "image").strip().lower()
    composition_mode = str(composition.get("mode") or "").strip().lower()
    render_profile = meta.get("render_profile") if isinstance(meta.get("render_profile"), dict) else {}
    if remotion_explicitly_enabled(render_profile) and (scene_type == "motion" or composition_mode == "native"):
        raise HTTPException(
            status_code=400,
            detail=(
                "This scene is on Cathode's native renderer path. "
                "Use Generate Motion Preview or Render Video instead of Generate Image."
            ),
        )

    image_profile = resolve_image_profile(meta.get("image_profile"))
    provider = (body.provider if body and body.provider else None) or image_profile["provider"]
    model = (body.model if body and body.model else None) or image_profile["generation_model"]
    request_payload = {
        "provider": provider,
        "model": model,
    }

    try:
        path = generate_scene_image(scene, project_dir, brief=brief, provider=provider, model=model)
    except Exception as exc:
        message = str(exc)
        _save_failed_image_action(
            project_dir,
            plan,
            scene=scene,
            scene_index=idx,
            action="generate",
            request=request_payload,
            error=message,
        )
        raise HTTPException(status_code=400, detail=message)

    scene["image_path"] = str(path)
    scene["video_path"] = None
    scene["preview_path"] = None
    scene["scene_type"] = "image"
    plan["scenes"][idx] = scene
    _record_image_action(
        plan,
        scene=scene,
        scene_index=idx,
        action="generate",
        status="succeeded",
        request=request_payload,
        result={
            "image_path": str(path),
            "scene_type": "image",
        },
    )
    return _present_plan(project_dir, save_plan(project_dir, plan))


@router.post("/projects/{project}/scenes/{scene_uid}/video-generate")
async def generate_video_for_scene(
    project: str,
    scene_uid: str,
    body: VideoGenerateRequest | None = Body(None),
) -> dict[str, Any]:
    project_dir = _project_dir(project)
    plan = _load_plan_or_404(project_dir)
    idx, scene = _find_scene(plan, scene_uid)
    meta = plan.get("meta", {})
    brief = meta.get("brief", {})

    image_profile = resolve_image_profile(meta.get("image_profile"))
    video_profile = resolve_video_profile(meta.get("video_profile"))
    tts_profile = resolve_tts_profile(meta.get("tts_profile"))
    tts_kwargs = tts_kwargs_from_profile(tts_profile)
    provider = (body.provider if body and body.provider else None) or video_profile["provider"]
    model = (body.model if body and body.model else None) or video_profile["generation_model"]
    model_selection_mode = (
        (body.model_selection_mode if body and body.model_selection_mode else None)
        or video_profile.get("model_selection_mode")
    )
    quality_mode = (body.quality_mode if body and body.quality_mode else None) or video_profile.get("quality_mode")
    generate_audio = body.generate_audio if body and body.generate_audio is not None else video_profile.get("generate_audio")

    try:
        video_result = generate_scene_video_result(
            scene,
            project_dir,
            brief=brief,
            provider=provider,
            model=model,
            model_selection_mode=str(model_selection_mode or "automatic"),
            quality_mode=str(quality_mode or "standard"),
            generate_audio=bool(True if generate_audio is None else generate_audio),
            image_provider=str(image_profile.get("provider") or "manual"),
            image_model=str(image_profile.get("generation_model") or ""),
            tts_kwargs=tts_kwargs,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    path = Path(str(video_result["path"]))
    scene["video_path"] = str(path)
    scene["image_path"] = None
    scene["preview_path"] = None
    scene["scene_type"] = "video"
    uses_clip_audio = bool(video_result.get("provider") == "replicate" and video_result.get("generate_audio"))
    scene["video_audio_source"] = "clip" if uses_clip_audio else "narration"
    if uses_clip_audio:
        scene["audio_path"] = None
    plan["scenes"][idx] = scene
    append_actual_cost_entry(
        plan,
        video_generation_entry(
            scene=scene,
            provider=str(video_result.get("provider") or provider or video_profile["provider"]),
            model=str(video_result.get("model") or model or video_profile["generation_model"]),
            model_selection_mode=str(model_selection_mode or video_profile.get("model_selection_mode") or "automatic"),
            quality_mode=str(video_result.get("quality_mode") or quality_mode or video_profile.get("quality_mode") or "standard"),
            generate_audio=bool(video_result.get("generate_audio")),
            estimated=False,
            operation="scene_video_generate",
            duration_seconds=float(video_result.get("duration_seconds") or 0.0),
        ),
    )
    if video_result.get("reference_image_generated"):
        append_actual_cost_entry(
            plan,
            image_generation_entry(
                scene=scene,
                provider=str(image_profile.get("provider") or "manual"),
                model=str(image_profile.get("generation_model") or ""),
                estimated=False,
                operation="video_reference_image",
            ),
        )
    if video_result.get("reference_audio_generated"):
        append_actual_cost_entry(
            plan,
            tts_entry(
                scene=scene,
                provider=str(video_result.get("reference_audio_provider") or tts_kwargs.get("tts_provider") or "kokoro"),
                model=str(video_result.get("reference_audio_model") or tts_kwargs.get("openai_model_id") or tts_kwargs.get("elevenlabs_model_id") or ""),
                estimated=False,
                operation="video_reference_audio",
                purpose="reference_audio",
                text=str(scene.get("narration") or ""),
            ),
        )
    return _present_plan(project_dir, save_plan(project_dir, plan))


@router.post("/projects/{project}/scenes/{scene_uid}/image-edit")
async def edit_image_for_scene(
    project: str,
    scene_uid: str,
    body: ImageEditRequest,
) -> dict[str, Any]:
    project_dir = _project_dir(project)
    plan = _load_plan_or_404(project_dir)
    idx, scene = _find_scene(plan, scene_uid)
    meta = plan.get("meta", {})
    image_profile = resolve_image_profile(meta.get("image_profile"))

    image_path = scene.get("image_path")
    if not image_path or not Path(str(image_path)).exists():
        message = "Scene must have an image before it can be edited."
        _save_failed_image_action(
            project_dir,
            plan,
            scene=scene,
            scene_index=idx,
            action="edit",
            request={"feedback": body.feedback.strip()},
            error=message,
        )
        raise HTTPException(status_code=400, detail=message)

    feedback = body.feedback.strip()
    if not feedback:
        message = "Edit instructions are required."
        _save_failed_image_action(
            project_dir,
            plan,
            scene=scene,
            scene_index=idx,
            action="edit",
            request={"feedback": feedback},
            error=message,
        )
        raise HTTPException(status_code=400, detail=message)

    exact_text_edit_prompt = canonicalize_exact_text_edit_prompt(feedback)
    feedback = exact_text_edit_prompt or feedback
    model = str(body.model or image_profile.get("edit_model") or "").strip()
    if not model:
        message = "No image editor is configured for this project."
        _save_failed_image_action(
            project_dir,
            plan,
            scene=scene,
            scene_index=idx,
            action="edit",
            request={"feedback": feedback, "model": model},
            error=message,
        )
        raise HTTPException(status_code=400, detail=message)

    canonical_image_path = _canonical_scene_image_path(project_dir, scene)
    edited_path = (
        canonical_image_path.with_name(f".{canonical_image_path.stem}_edited{canonical_image_path.suffix}")
        if canonical_image_path is not None
        else project_dir / "images" / f"image_{scene_uid}_edited.png"
    )
    edit_kwargs: dict[str, Any] = {"model": model}
    if model.startswith("qwen-image-edit"):
        edit_kwargs["n"] = int(image_profile.get("dashscope_edit_n") or 1)
        edit_kwargs["prompt_extend"] = bool(image_profile.get("dashscope_edit_prompt_extend", True))
        negative_prompt = str(image_profile.get("dashscope_edit_negative_prompt") or "").strip()
        edit_kwargs["negative_prompt"] = negative_prompt if negative_prompt else " "
        seed_raw = str(image_profile.get("dashscope_edit_seed") or "").strip()
        if seed_raw.isdigit():
            edit_kwargs["seed"] = int(seed_raw)
        if exact_text_edit_prompt:
            edit_kwargs["n"] = 1
            edit_kwargs["prompt_extend"] = False
            edit_kwargs["negative_prompt"] = " "
    request_payload = {
        "feedback": feedback,
        "model": model,
        "dashscope_edit_n": edit_kwargs.get("n"),
        "dashscope_edit_seed": edit_kwargs.get("seed"),
        "dashscope_edit_negative_prompt": edit_kwargs.get("negative_prompt"),
        "dashscope_edit_prompt_extend": edit_kwargs.get("prompt_extend"),
    }

    try:
        output_path = edit_image(
            feedback,
            image_path,
            edited_path,
            **edit_kwargs,
        )
    except Exception as exc:
        message = str(exc)
        _save_failed_image_action(
            project_dir,
            plan,
            scene=scene,
            scene_index=idx,
            action="edit",
            request=request_payload,
            error=message,
        )
        raise HTTPException(status_code=400, detail=message)

    preserved_image_path = replace_scene_image_preserving_identity(project_dir, scene, output_path)
    scene["image_path"] = str(preserved_image_path or output_path)
    scene["video_path"] = None
    scene["preview_path"] = None
    scene["scene_type"] = "image"
    plan["scenes"][idx] = scene
    append_actual_cost_entry(
        plan,
        image_edit_entry(
            scene=scene,
            provider=(
                "dashscope"
                if model.startswith("qwen-image-edit")
                else "openai"
                if model.startswith("gpt-image")
                else "replicate"
            ),
            model=model,
            estimated=False,
            operation="scene_image_edit",
        ),
    )
    _record_image_action(
        plan,
        scene=scene,
        scene_index=idx,
        action="edit",
        status="succeeded",
        request=request_payload,
        result={
            "image_path": scene["image_path"],
            "scene_type": "image",
        },
    )
    return _present_plan(project_dir, save_plan(project_dir, plan))


@router.post("/projects/{project}/scenes/{scene_uid}/audio-generate")
async def generate_audio_for_scene(
    project: str,
    scene_uid: str,
    body: AudioGenerateRequest | None = Body(None),
) -> dict[str, Any]:
    project_dir = _project_dir(project)
    plan = _load_plan_or_404(project_dir)
    idx, scene = _find_scene(plan, scene_uid)
    meta = plan.get("meta", {})

    tts_profile = resolve_tts_profile(meta.get("tts_profile"))
    tts_kwargs = tts_kwargs_from_profile(tts_profile)
    if body:
        if body.tts_provider:
            tts_kwargs["tts_provider"] = body.tts_provider
        if body.voice:
            tts_kwargs["voice"] = body.voice
        if body.speed is not None:
            tts_kwargs["speed"] = body.speed

    try:
        audio_result = generate_scene_audio_result(scene, project_dir, **tts_kwargs)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    path = Path(str(audio_result["path"]))
    scene["audio_path"] = str(path)
    plan["scenes"][idx] = scene
    append_actual_cost_entry(
        plan,
        tts_entry(
            scene=scene,
            provider=str(audio_result.get("provider") or tts_kwargs.get("tts_provider") or "kokoro"),
            model=str(audio_result.get("model") or tts_kwargs.get("openai_model_id") or tts_kwargs.get("elevenlabs_model_id") or ""),
            estimated=False,
            operation="scene_audio_generate",
            purpose="narration",
            text=str(scene.get("narration") or ""),
        ),
    )
    return _present_plan(project_dir, save_plan(project_dir, plan))


@router.get("/projects/{project}/scenes/{scene_uid}/remotion-manifest")
async def get_scene_remotion_manifest(project: str, scene_uid: str) -> dict[str, Any]:
    project_dir = _project_dir(project)
    plan = _load_plan_or_404(project_dir)
    _find_scene(plan, scene_uid)
    render_profile = plan.get("meta", {}).get("render_profile")

    try:
        return build_remotion_manifest(
            project_dir=project_dir,
            plan=plan,
            output_path=project_dir / "previews" / f"preview_{scene_uid}.mp4",
            render_profile=render_profile if isinstance(render_profile, dict) else None,
            preview_scene_uid=scene_uid,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


# ---- Refinement endpoints -------------------------------------------------


@router.post("/projects/{project}/scenes/{scene_uid}/prompt-refine")
async def refine_scene_prompt(
    project: str,
    scene_uid: str,
    body: PromptRefineRequest,
) -> dict[str, Any]:
    project_dir = _project_dir(project)
    plan = _load_plan_or_404(project_dir)
    idx, scene = _find_scene(plan, scene_uid)

    provider = body.provider or choose_llm_provider()
    try:
        refined, llm_meta = refine_prompt_with_metadata(
            original_prompt=scene.get("visual_prompt", ""),
            feedback=body.feedback,
            narration=scene.get("narration", ""),
            provider=provider,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    scene["visual_prompt"] = refined
    plan["scenes"][idx] = scene
    if isinstance(llm_meta.get("actual"), dict):
        append_actual_cost_entry(plan, llm_meta["actual"])
    if isinstance(llm_meta.get("preflight"), dict):
        plan.setdefault("meta", {}).setdefault("cost_actual", {})["llm_preflight_refine_prompt"] = llm_meta["preflight"]
    return _present_plan(project_dir, save_plan(project_dir, plan))


@router.post("/projects/{project}/scenes/{scene_uid}/narration-refine")
async def refine_scene_narration(
    project: str,
    scene_uid: str,
    body: NarrationRefineRequest,
) -> dict[str, Any]:
    project_dir = _project_dir(project)
    plan = _load_plan_or_404(project_dir)
    idx, scene = _find_scene(plan, scene_uid)

    provider = body.provider or choose_llm_provider()
    try:
        refined, llm_meta = refine_narration_with_metadata(
            original_narration=scene.get("narration", ""),
            feedback=body.feedback,
            provider=provider,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    scene["narration"] = refined
    plan["scenes"][idx] = scene
    if isinstance(llm_meta.get("actual"), dict):
        append_actual_cost_entry(plan, llm_meta["actual"])
    if isinstance(llm_meta.get("preflight"), dict):
        plan.setdefault("meta", {}).setdefault("cost_actual", {})["llm_preflight_refine_narration"] = llm_meta["preflight"]
    return _present_plan(project_dir, save_plan(project_dir, plan))


# ---- Preview endpoint ------------------------------------------------------


@router.post("/projects/{project}/scenes/{scene_uid}/preview")
async def preview_scene_endpoint(project: str, scene_uid: str) -> dict[str, Any]:
    project_dir = _project_dir(project)
    plan = _load_plan_or_404(project_dir)
    idx, scene = _find_scene(plan, scene_uid)
    render_profile = plan.get("meta", {}).get("render_profile") if isinstance(plan.get("meta", {}).get("render_profile"), dict) else {}

    try:
        preview_path, motion = await run_in_threadpool(
            _render_preview_asset,
            scene=scene,
            scene_uid=scene_uid,
            project_dir=project_dir,
            plan=plan,
            render_profile=render_profile,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    if motion is not None:
        scene["motion"] = motion
    if preview_path:
        scene["preview_path"] = str(preview_path)
        plan["scenes"][idx] = scene
    return _present_plan(project_dir, save_plan(project_dir, plan))
