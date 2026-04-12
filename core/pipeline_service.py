"""Shared headless pipeline services for app, batch, and MCP flows."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from .agent_demo import build_agent_demo_prompt, run_agent_demo_cli, choose_agent_cli
from .costs import (
    append_actual_cost_entry,
    image_edit_entry,
    image_generation_entry,
    resolve_video_cost_context,
    tts_entry,
    video_generation_entry,
)
from .demo_assets import (
    apply_footage_manifest_to_scenes,
    build_footage_summary,
    copy_footage_manifest_into_project,
    normalize_footage_manifest,
)
from .director import analyze_style_references_with_metadata, rewrite_prompt_for_synonym_fallback_with_metadata
from .image_gen import build_exact_text_edit_prompt, edit_image, generate_scene_image
from .project_schema import (
    default_image_profile,
    has_agent_demo_context,
    infer_composition_mode,
    normalize_agent_demo_profile,
    normalize_brief,
    resolve_render_backend_details,
    resolve_render_strategy,
    resolve_render_backend,
    scene_primary_manifestation,
)
from .project_store import copy_external_files, ensure_project_dir, load_plan, save_plan
from .remotion_render import build_remotion_manifest, render_manifest_with_remotion, scene_has_renderable_visual
from .scene_review import default_scene_review_candidates, review_project_scenes
from .runtime import resolve_workflow_llm_roles, resolve_image_profile, resolve_tts_profile, resolve_video_profile
from .video_assembly import assemble_video, compress_video_if_oversized
from .video_gen import generate_scene_video_result
from .voice_gen import generate_scene_audio_result
from .workflow import create_plan_from_brief, rebuild_plan_from_meta

ReviewRunner = Callable[[str, list[str] | None], dict[str, Any]]
_MAX_EXACT_TEXT_REPAIR_ATTEMPTS = 3


def utc_now_iso() -> str:
    """Return a UTC timestamp in ISO format."""
    return datetime.utcnow().isoformat()


def prepare_project_execution_profiles(
    *,
    brief: dict[str, Any] | None,
    video_profile: dict[str, Any] | None = None,
    render_profile: dict[str, Any] | None = None,
    agent_demo_profile: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Normalize brief/demo/render inputs so GUI and MCP job creation cannot drift."""
    normalized_demo_profile = normalize_agent_demo_profile(agent_demo_profile)
    normalized_brief = normalize_brief(brief or {})
    normalized_brief["composition_mode"] = infer_composition_mode(
        brief or {},
        agent_demo_profile=normalized_demo_profile,
    )

    next_video_profile = dict(video_profile or {})
    if (
        not str(next_video_profile.get("provider") or "").strip()
        and normalized_brief["composition_mode"] == "hybrid"
        and has_agent_demo_context(normalized_demo_profile)
    ):
        next_video_profile["provider"] = "agent"

    resolved_render_profile = dict(render_profile or {})
    resolved_render_profile["render_strategy"] = resolve_render_strategy(
        resolved_render_profile.get("render_strategy")
    )
    if resolved_render_profile["render_strategy"] == "auto":
        resolved_render_profile.pop("render_backend", None)
        resolved_render_profile.pop("render_backend_reason", None)
    else:
        backend, reason = resolve_render_backend_details(
            resolved_render_profile,
            composition_mode=str(normalized_brief.get("composition_mode") or "classic"),
        )
        resolved_render_profile["render_backend"] = backend
        resolved_render_profile["render_backend_reason"] = reason
    resolved_render_profile["text_render_mode"] = str(normalized_brief.get("text_render_mode") or "visual_authored")

    return normalized_brief, resolve_video_profile(next_video_profile or None), resolved_render_profile


def tts_kwargs_from_profile(profile: dict | None) -> dict[str, Any]:
    """Build generate_scene_audio kwargs from a persisted TTS profile."""
    profile = profile if isinstance(profile, dict) else {}
    provider = str(profile.get("provider") or "kokoro")
    kwargs: dict[str, Any] = {"tts_provider": provider}

    if provider in {"kokoro", "elevenlabs"}:
        kwargs["voice"] = str(profile.get("voice") or "")
        kwargs["speed"] = float(profile.get("speed") or 1.1)
    if provider == "elevenlabs":
        if profile.get("model_id"):
            kwargs["elevenlabs_model_id"] = str(profile["model_id"])
        if profile.get("text_normalization"):
            kwargs["elevenlabs_apply_text_normalization"] = str(profile["text_normalization"])
        if profile.get("stability") is not None:
            kwargs["elevenlabs_stability"] = float(profile["stability"])
        if profile.get("similarity_boost") is not None:
            kwargs["elevenlabs_similarity_boost"] = float(profile["similarity_boost"])
        if profile.get("style") is not None:
            kwargs["elevenlabs_style"] = float(profile["style"])
        if profile.get("use_speaker_boost") is not None:
            kwargs["elevenlabs_use_speaker_boost"] = bool(profile["use_speaker_boost"])
    if provider == "chatterbox" and profile.get("exaggeration") is not None:
        kwargs["exaggeration"] = float(profile["exaggeration"])
    if provider == "openai" and profile.get("model_id"):
        kwargs["openai_model_id"] = str(profile["model_id"])
    return kwargs


def _persist_style_references(
    project_dir: Path,
    style_reference_paths: list[str | Path] | None,
) -> list[Path]:
    valid = [Path(path) for path in (style_reference_paths or []) if Path(path).exists()]
    if not valid:
        return []
    return copy_external_files(
        project_dir,
        valid,
        subdir="style_refs",
        stem_prefix="style_ref",
    )


def _persist_footage_manifest(
    project_dir: Path,
    footage_manifest: list[dict[str, Any]] | None,
) -> list[dict[str, Any]]:
    normalized = normalize_footage_manifest(footage_manifest or [])
    if not normalized:
        return []
    return copy_footage_manifest_into_project(project_dir, normalized)


def create_project_from_brief_service(
    *,
    project_name: str,
    brief: dict[str, Any],
    overwrite: bool = False,
    provider: str | None = None,
    image_profile: dict[str, Any] | None = None,
    video_profile: dict[str, Any] | None = None,
    agent_demo_profile: dict[str, Any] | None = None,
    tts_profile: dict[str, Any] | None = None,
    render_profile: dict[str, Any] | None = None,
    project_dir: Path | None = None,
) -> tuple[Path, dict[str, Any]]:
    """Create a project directory, persist style refs, and generate the initial storyboard."""
    creative_provider, treatment_provider = resolve_workflow_llm_roles(provider)
    resolved_image_profile = resolve_image_profile(image_profile)
    normalized_brief, resolved_video_profile, resolved_render_profile = prepare_project_execution_profiles(
        brief=brief,
        video_profile=video_profile,
        render_profile=render_profile,
        agent_demo_profile=agent_demo_profile,
    )
    resolved_tts_profile = resolve_tts_profile(tts_profile)
    project_dir = Path(project_dir) if project_dir is not None else ensure_project_dir(project_name, overwrite=overwrite)
    if project_dir is not None:
        project_dir.mkdir(parents=True, exist_ok=True)
    normalized_brief["project_name"] = project_dir.name

    requested_footage_manifest = list(normalized_brief.get("footage_manifest") or [])
    saved_style_refs = _persist_style_references(project_dir, normalized_brief.get("style_reference_paths"))
    saved_footage_manifest = _persist_footage_manifest(project_dir, normalized_brief.get("footage_manifest"))
    style_reference_summary = str(normalized_brief.get("style_reference_summary") or "").strip()
    if saved_style_refs and not style_reference_summary:
        style_reference_summary, style_ref_meta = analyze_style_references_with_metadata(
            [str(path) for path in saved_style_refs],
            normalized_brief,
            provider=creative_provider,
        )
        (project_dir / "style_refs" / "style_reference_summary.txt").write_text(
            style_reference_summary,
            encoding="utf-8",
        )
    else:
        style_ref_meta = {}

    normalized_brief["style_reference_paths"] = [str(path) for path in saved_style_refs]
    normalized_brief["style_reference_summary"] = style_reference_summary
    normalized_brief["footage_manifest"] = saved_footage_manifest
    if requested_footage_manifest:
        normalized_brief["available_footage"] = build_footage_summary(saved_footage_manifest)
    elif not str(normalized_brief.get("available_footage") or "").strip() and saved_footage_manifest:
        normalized_brief["available_footage"] = build_footage_summary(saved_footage_manifest)

    plan = create_plan_from_brief(
        project_name=project_dir.name,
        brief=normalized_brief,
        provider=creative_provider,
        storyboard_provider=creative_provider,
        treatment_provider=treatment_provider,
        image_profile=resolved_image_profile,
        video_profile=resolved_video_profile,
        tts_profile=resolved_tts_profile,
        render_profile=resolved_render_profile,
    )
    plan["scenes"] = apply_footage_manifest_to_scenes(plan.get("scenes", []), saved_footage_manifest)
    if isinstance(style_ref_meta.get("actual"), dict):
        append_actual_cost_entry(plan, style_ref_meta["actual"])
    if isinstance(style_ref_meta.get("preflight"), dict):
        plan.setdefault("meta", {}).setdefault("cost_actual", {})["llm_preflight_style_refs"] = style_ref_meta["preflight"]
    plan.setdefault("meta", {})["brief"] = normalize_brief(normalized_brief, base_dir=project_dir)
    plan.setdefault("meta", {})["footage_manifest"] = saved_footage_manifest
    normalized_agent_demo_profile = normalize_agent_demo_profile(agent_demo_profile)
    if normalized_agent_demo_profile:
        plan.setdefault("meta", {})["agent_demo_profile"] = normalized_agent_demo_profile
    plan.setdefault("meta", {})["created_by"] = "cathode"
    plan = save_plan(project_dir, plan)
    return project_dir, plan


def rebuild_storyboard_service(
    project_dir: Path,
    *,
    provider: str | None = None,
) -> dict[str, Any]:
    """Rebuild storyboard scenes for an existing project using saved metadata."""
    plan = load_plan(project_dir)
    if not plan:
        raise ValueError(f"Missing plan.json for project: {project_dir}")
    creative_provider, treatment_provider = resolve_workflow_llm_roles(provider)
    rebuilt = rebuild_plan_from_meta(
        plan,
        provider=creative_provider,
        storyboard_provider=creative_provider,
        treatment_provider=treatment_provider,
    )
    footage_manifest = normalize_footage_manifest(
        rebuilt.get("meta", {}).get("footage_manifest")
        or rebuilt.get("meta", {}).get("brief", {}).get("footage_manifest")
    )
    rebuilt["scenes"] = apply_footage_manifest_to_scenes(rebuilt.get("scenes", []), footage_manifest)
    rebuilt.setdefault("meta", {})["footage_manifest"] = footage_manifest
    rebuilt.setdefault("meta", {}).setdefault("brief", {})
    rebuilt["meta"]["brief"]["footage_manifest"] = footage_manifest
    if footage_manifest:
        rebuilt["meta"]["brief"]["available_footage"] = build_footage_summary(footage_manifest)
    elif not str(rebuilt["meta"]["brief"].get("available_footage") or "").strip():
        rebuilt["meta"]["brief"]["available_footage"] = ""
    rebuilt.setdefault("meta", {})["regenerated_by"] = "cathode"
    return save_plan(project_dir, rebuilt)


def _scene_has_image(scene: dict[str, Any]) -> bool:
    image_path = scene.get("image_path")
    return bool(image_path and Path(str(image_path)).exists())


def _scene_has_video(scene: dict[str, Any]) -> bool:
    video_path = scene.get("video_path")
    return bool(video_path and Path(str(video_path)).exists())


def _scene_type(scene: dict[str, Any]) -> str:
    scene_type = str(scene.get("scene_type") or "image").strip().lower()
    return scene_type if scene_type in {"image", "video", "motion"} else "image"


def _scene_manifestation(scene: dict[str, Any]) -> str:
    return scene_primary_manifestation(scene)


def _scene_has_primary_visual(scene: dict[str, Any], *, render_backend: str = "ffmpeg") -> bool:
    return scene_has_renderable_visual(scene, render_backend=render_backend)


def _emit_asset_progress(
    progress_callback: Callable[[dict[str, Any]], None] | None,
    *,
    completed: int,
    total_work_items: int,
    total_scenes: int,
    asset_kind: str,
    scene: dict[str, Any],
    status: str,
) -> None:
    if progress_callback is None or total_work_items <= 0:
        return

    scene_id = int(scene.get("id") or 0)
    scene_title = str(scene.get("title") or "").strip()
    scene_label = f"Scene {scene_id}" if scene_id else "Scene"
    if total_scenes > 0 and scene_id:
        scene_label = f"Scene {scene_id} of {total_scenes}"
    if scene_title:
        scene_label = f"{scene_label} - {scene_title}"

    verb_map = {
        "running": {
            "image": "Generating image",
            "video": "Generating video",
            "audio": "Generating audio",
        },
        "skipped": {
            "image": "Skipping image",
            "video": "Skipping video",
            "audio": "Skipping audio",
        },
        "error": {
            "image": "Image failed",
            "video": "Video failed",
            "audio": "Audio failed",
        },
        "done": {
            "image": "Image ready",
            "video": "Video ready",
            "audio": "Audio ready",
        },
    }

    if status == "running":
        progress = min((completed + 0.35) / total_work_items, 0.99)
    else:
        progress = min((completed + 1) / total_work_items, 1.0)

    progress_callback(
        {
            "progress": progress,
            "progress_kind": asset_kind,
            "progress_label": verb_map.get(status, {}).get(asset_kind, "Generating assets"),
            "progress_detail": scene_label,
            "progress_scene_id": scene_id or None,
            "progress_scene_uid": str(scene.get("uid") or "") or None,
            "progress_status": status,
        }
        )


def _primary_only_scene_review_candidates(
    plan: dict[str, Any],
    *,
    scene_uids: list[str] | None = None,
) -> dict[str, list[dict[str, Any]]]:
    candidates: dict[str, list[dict[str, Any]]] = {}
    scenes = plan.get("scenes", []) if isinstance(plan.get("scenes"), list) else []
    allowed = {str(uid).strip() for uid in (scene_uids or []) if str(uid).strip()}
    for scene in scenes:
        if not isinstance(scene, dict):
            continue
        scene_uid = str(scene.get("uid") or "").strip()
        if not scene_uid or (allowed and scene_uid not in allowed):
            continue
        try:
            scene_candidates = default_scene_review_candidates(scene)
        except Exception:
            continue
        if scene_candidates:
            candidates[scene_uid] = scene_candidates
    return candidates


def _resolve_project_path(project_dir: Path, raw_path: Any) -> Path | None:
    value = str(raw_path or "").strip()
    if not value:
        return None
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = Path(project_dir) / path
    return path.resolve()


def _path_is_within(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _canonical_scene_image_path(project_dir: Path, scene: dict[str, Any]) -> Path | None:
    if scene_primary_manifestation(scene) != "authored_image":
        return None
    try:
        scene_id = int(scene.get("id"))
    except (TypeError, ValueError):
        return None
    return (Path(project_dir) / "images" / f"scene_{scene_id:03d}.png").resolve()


def clear_scene_review_metadata(scene: dict[str, Any]) -> bool:
    changed = False
    for key in ("judge_verdict", "candidate_outputs"):
        if key in scene:
            scene.pop(key, None)
            changed = True
    return changed


def _review_metadata_uses_noncanonical_image(project_dir: Path, scene: dict[str, Any]) -> bool:
    canonical_path = _canonical_scene_image_path(project_dir, scene)
    if canonical_path is None:
        return False

    verdict = scene.get("judge_verdict") if isinstance(scene.get("judge_verdict"), dict) else {}
    for frame_ref in verdict.get("frame_refs", []) if isinstance(verdict.get("frame_refs"), list) else []:
        if not isinstance(frame_ref, dict):
            continue
        frame_path = _resolve_project_path(project_dir, frame_ref.get("path"))
        if frame_path is not None and frame_path != canonical_path:
            return True

    candidate_outputs = scene.get("candidate_outputs") if isinstance(scene.get("candidate_outputs"), dict) else {}
    for candidate_payload in candidate_outputs.values():
        if not isinstance(candidate_payload, dict):
            continue
        candidate_path = _resolve_project_path(project_dir, candidate_payload.get("source_path"))
        if candidate_path is not None and candidate_path != canonical_path:
            return True
        for frame_ref in candidate_payload.get("frame_refs", []) if isinstance(candidate_payload.get("frame_refs"), list) else []:
            if not isinstance(frame_ref, dict):
                continue
            frame_path = _resolve_project_path(project_dir, frame_ref.get("path"))
            if frame_path is not None and frame_path != canonical_path:
                return True
    return False


def _cleanup_scene_derivative_images(project_dir: Path, scene: dict[str, Any], *, keep_paths: set[Path] | None = None) -> None:
    scene_uid = str(scene.get("uid") or "").strip()
    if not scene_uid:
        return
    images_dir = (Path(project_dir) / "images").resolve()
    keep = {path.resolve() for path in (keep_paths or set())}
    for suffix in ("edited", "textfix"):
        candidate = images_dir / f"image_{scene_uid}_{suffix}.png"
        if not candidate.exists() or candidate.resolve() in keep:
            continue
        try:
            candidate.unlink()
        except OSError:
            continue


def replace_scene_image_preserving_identity(
    project_dir: Path,
    scene: dict[str, Any],
    source_path: str | Path | None = None,
    *,
    clear_review_metadata: bool = True,
) -> Path | None:
    project_dir = Path(project_dir).resolve()
    images_dir = (project_dir / "images").resolve()
    canonical_path = _canonical_scene_image_path(project_dir, scene)
    if canonical_path is None:
        resolved_path = _resolve_project_path(project_dir, source_path if source_path is not None else scene.get("image_path"))
        if resolved_path is not None:
            scene["image_path"] = str(resolved_path)
        return resolved_path

    canonical_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_source = _resolve_project_path(project_dir, source_path if source_path is not None else scene.get("image_path"))

    if resolved_source is not None and resolved_source.exists():
        if resolved_source != canonical_path:
            resolved_source.replace(canonical_path)
    elif not canonical_path.exists():
        return None

    scene["image_path"] = str(canonical_path)
    if clear_review_metadata:
        clear_scene_review_metadata(scene)
    _cleanup_scene_derivative_images(project_dir, scene, keep_paths={canonical_path})
    if resolved_source is not None and resolved_source != canonical_path and resolved_source.exists():
        if _path_is_within(resolved_source, images_dir):
            try:
                resolved_source.unlink()
            except OSError:
                pass
    return canonical_path


def normalize_authored_image_scene_identities(
    project_dir: Path,
    current_plan: dict[str, Any],
    *,
    scene_uids: list[str] | None = None,
) -> tuple[dict[str, Any], bool]:
    changed = False
    allowed = {str(uid).strip() for uid in (scene_uids or []) if str(uid).strip()}
    scenes_local = current_plan.get("scenes", []) if isinstance(current_plan.get("scenes"), list) else []
    for idx, scene in enumerate(scenes_local):
        if not isinstance(scene, dict):
            continue
        scene_uid = str(scene.get("uid") or "").strip()
        if allowed and scene_uid not in allowed:
            continue
        canonical_path = _canonical_scene_image_path(project_dir, scene)
        if canonical_path is None:
            continue
        resolved_path = _resolve_project_path(project_dir, scene.get("image_path"))
        review_reset_needed = _review_metadata_uses_noncanonical_image(project_dir, scene)
        if resolved_path is not None and resolved_path.exists() and resolved_path != canonical_path:
            replace_scene_image_preserving_identity(
                project_dir,
                scene,
                resolved_path,
                clear_review_metadata=True,
            )
            changed = True
        else:
            if canonical_path.exists() and str(scene.get("image_path") or "") != str(canonical_path):
                scene["image_path"] = str(canonical_path)
                changed = True
            if review_reset_needed and clear_scene_review_metadata(scene):
                changed = True
            _cleanup_scene_derivative_images(project_dir, scene, keep_paths={canonical_path})
        scenes_local[idx] = scene
    return current_plan, changed


def _scene_by_uid(current_plan: dict[str, Any], scene_uid: str) -> dict[str, Any] | None:
    scenes_local = current_plan.get("scenes", []) if isinstance(current_plan.get("scenes"), list) else []
    for scene in scenes_local:
        if not isinstance(scene, dict):
            continue
        if str(scene.get("uid") or "").strip() == scene_uid:
            return scene
    return None


def _upsert_scene(current_plan: dict[str, Any], updated_scene: dict[str, Any]) -> None:
    scenes_local = current_plan.get("scenes", []) if isinstance(current_plan.get("scenes"), list) else []
    scene_uid = str(updated_scene.get("uid") or "").strip()
    for idx, scene in enumerate(scenes_local):
        if not isinstance(scene, dict):
            continue
        if str(scene.get("uid") or "").strip() == scene_uid:
            scenes_local[idx] = updated_scene
            return


def _winning_text_repairs(scene: dict[str, Any]) -> list[dict[str, str]]:
    manifestation_plan = scene.get("manifestation_plan") if isinstance(scene.get("manifestation_plan"), dict) else {}
    if not manifestation_plan.get("text_expected"):
        return []
    if scene_primary_manifestation(scene) != "authored_image":
        return []
    verdict = scene.get("judge_verdict") if isinstance(scene.get("judge_verdict"), dict) else {}
    winner = str(verdict.get("winner") or "primary").strip() or "primary"
    candidate_outputs = scene.get("candidate_outputs") if isinstance(scene.get("candidate_outputs"), dict) else {}
    winner_payload = candidate_outputs.get(winner) if isinstance(candidate_outputs.get(winner), dict) else {}
    if winner_payload and str(winner_payload.get("candidate_type") or "").strip() not in {"", "authored_image"}:
        return []
    repairs = verdict.get("text_repairs") if isinstance(verdict.get("text_repairs"), list) else []
    return [
        item
        for item in repairs
        if isinstance(item, dict)
        and str(item.get("candidate_id") or "").strip() == winner
        and str(item.get("wrong_text") or "").strip()
        and str(item.get("correct_text") or "").strip()
    ]


def _image_edit_kwargs(image_profile: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    model = str(image_profile.get("edit_model") or "").strip()
    kwargs: dict[str, Any] = {"model": model}
    if model.startswith("qwen-image-edit"):
        kwargs["n"] = 1
        kwargs["prompt_extend"] = False
        kwargs["negative_prompt"] = " "
        seed_raw = str(image_profile.get("dashscope_edit_seed") or "").strip()
        if seed_raw.isdigit():
            kwargs["seed"] = int(seed_raw)
    return model, kwargs


def _attempt_text_repairs(
    project_dir: Path,
    current_plan: dict[str, Any],
    *,
    image_provider: str,
    image_generation_model: str,
    image_profile: dict[str, Any],
    review_runner: ReviewRunner,
    exact_review_trigger: str,
    synonym_review_trigger: str,
) -> tuple[dict[str, Any], bool]:
    changed = False
    scenes_local = current_plan.get("scenes", []) if isinstance(current_plan.get("scenes"), list) else []
    edit_model, edit_kwargs = _image_edit_kwargs(image_profile)
    for scene in scenes_local:
        repairs = _winning_text_repairs(scene)
        if not repairs or not scene.get("image_path"):
            continue
        scene_uid = str(scene.get("uid") or scene.get("id") or "scene").strip() or "scene"
        seen_repairs: set[tuple[str, str]] = set()
        exact_attempts = 0

        while exact_attempts < _MAX_EXACT_TEXT_REPAIR_ATTEMPTS:
            refreshed_scene = _scene_by_uid(current_plan, scene_uid) or scene
            repairs = _winning_text_repairs(refreshed_scene)
            if not repairs or not refreshed_scene.get("image_path"):
                break
            repair = repairs[0]
            repair_key = (repair["wrong_text"], repair["correct_text"])
            if repair_key in seen_repairs:
                break
            seen_repairs.add(repair_key)
            exact_attempts += 1

            exact_prompt = build_exact_text_edit_prompt(
                repair["wrong_text"],
                repair["correct_text"],
            )
            canonical_path = _canonical_scene_image_path(project_dir, refreshed_scene)
            if canonical_path is None:
                break
            edited_path = canonical_path.with_name(f".{canonical_path.stem}_textfix{canonical_path.suffix}")
            output_path = edit_image(
                exact_prompt,
                refreshed_scene["image_path"],
                edited_path,
                **edit_kwargs,
            )
            replace_scene_image_preserving_identity(project_dir, refreshed_scene, output_path)
            append_actual_cost_entry(
                current_plan,
                image_edit_entry(
                    scene=refreshed_scene,
                    provider="dashscope" if edit_model.startswith("qwen-image-edit") else "replicate",
                    model=edit_model,
                    estimated=False,
                    operation="render_text_repair",
                ),
            )
            _upsert_scene(current_plan, refreshed_scene)
            changed = True
            save_plan(project_dir, current_plan)
            review_runner(exact_review_trigger, [scene_uid])
            current_plan = load_plan(project_dir) or current_plan

        refreshed_scene = _scene_by_uid(current_plan, scene_uid) or scene
        repairs_after_edit = _winning_text_repairs(refreshed_scene)
        text_critical = bool(
            isinstance(refreshed_scene.get("manifestation_plan"), dict)
            and refreshed_scene["manifestation_plan"].get("text_critical")
        )
        if not repairs_after_edit or text_critical:
            continue

        synonym_payload, synonym_meta = rewrite_prompt_for_synonym_fallback_with_metadata(
            original_prompt=str(refreshed_scene.get("visual_prompt") or ""),
            on_screen_text=refreshed_scene.get("on_screen_text") if isinstance(refreshed_scene.get("on_screen_text"), list) else [],
            wrong_text=repairs_after_edit[0]["wrong_text"],
            correct_text=repairs_after_edit[0]["correct_text"],
            narration=str(refreshed_scene.get("narration") or ""),
            provider="anthropic",
        )
        refreshed_scene["visual_prompt"] = synonym_payload["rewritten_prompt"]
        refreshed_scene["on_screen_text"] = synonym_payload["rewritten_on_screen_text"]
        regenerated_path = generate_scene_image(
            refreshed_scene,
            Path(project_dir),
            brief=current_plan.get("meta", {}).get("brief"),
            provider=image_provider,
            model=image_generation_model,
        )
        replace_scene_image_preserving_identity(project_dir, refreshed_scene, regenerated_path)
        append_actual_cost_entry(
            current_plan,
            image_generation_entry(
                scene=refreshed_scene,
                provider=image_provider,
                model=image_generation_model,
                estimated=False,
                operation="synonym_regenerate",
            ),
        )
        if isinstance(synonym_meta.get("actual"), dict):
            append_actual_cost_entry(current_plan, synonym_meta["actual"])
        _upsert_scene(current_plan, refreshed_scene)
        changed = True
        save_plan(project_dir, current_plan)
        review_runner(synonym_review_trigger, [scene_uid])
        current_plan = load_plan(project_dir) or current_plan
    return current_plan, changed


def generate_project_assets_service(
    project_dir: Path,
    *,
    generate_images: bool = True,
    generate_videos: bool = True,
    generate_audio: bool = True,
    regenerate_images: bool = False,
    regenerate_videos: bool = False,
    regenerate_audio: bool = False,
    progress_callback: Callable[[dict[str, Any]], None] | None = None,
) -> dict[str, Any]:
    """Generate image and audio assets for a project, preserving existing files by default."""
    plan = load_plan(project_dir)
    if not plan:
        raise ValueError(f"Missing plan.json for project: {project_dir}")

    meta = plan.get("meta", {})
    brief = meta.get("brief", {})
    image_profile = resolve_image_profile(meta.get("image_profile"))
    image_provider = str(image_profile.get("provider") or "manual")
    image_generation_model = str(
        image_profile.get("generation_model") or default_image_profile()["generation_model"]
    )
    video_profile = resolve_video_profile(meta.get("video_profile"))
    video_provider = str(video_profile.get("provider") or "manual")
    video_generation_model = str(video_profile.get("generation_model") or "")
    video_model_selection_mode = str(video_profile.get("model_selection_mode") or "automatic")
    video_quality_mode = str(video_profile.get("quality_mode") or "standard")
    video_generate_audio = True if video_profile.get("generate_audio") is None else bool(video_profile.get("generate_audio"))
    agent_demo_profile = meta.get("agent_demo_profile") if isinstance(meta.get("agent_demo_profile"), dict) else {}
    tts_profile = resolve_tts_profile(meta.get("tts_profile"))
    tts_kwargs = tts_kwargs_from_profile(tts_profile)

    result = {
        "images_generated": 0,
        "images_skipped": 0,
        "image_failures": [],
        "videos_generated": 0,
        "videos_skipped": 0,
        "video_failures": [],
        "audio_generated": 0,
        "audio_skipped": 0,
        "audio_failures": [],
    }

    scenes = list(plan.get("scenes", []))
    total_scenes = len(scenes)
    total_work_items = 0
    if generate_audio:
        total_work_items += total_scenes
    if generate_images:
        total_work_items += sum(1 for scene in scenes if _scene_manifestation(scene) == "authored_image")
    if generate_videos:
        total_work_items += sum(1 for scene in scenes if _scene_manifestation(scene) == "source_video")
    completed_work_items = 0

    for scene in scenes:
        manifestation = _scene_manifestation(scene)
        video_cost_context = (
            resolve_video_cost_context(
                scene=scene,
                provider=video_provider,
                model=video_generation_model,
                model_selection_mode=video_model_selection_mode,
                quality_mode=video_quality_mode,
                generate_audio=video_generate_audio,
            )
            if manifestation == "source_video"
            else None
        )
        clip_audio_expected = bool(video_cost_context and video_cost_context.get("uses_clip_audio"))
        has_audio = scene.get("audio_path") and Path(str(scene["audio_path"])).exists()
        if generate_audio and clip_audio_expected:
            scene["video_audio_source"] = "clip"
            scene["audio_path"] = None
            result["audio_skipped"] += 1
            _emit_asset_progress(
                progress_callback,
                completed=completed_work_items,
                total_work_items=total_work_items,
                total_scenes=total_scenes,
                asset_kind="audio",
                scene=scene,
                status="skipped",
            )
            completed_work_items += 1
        elif generate_audio and (regenerate_audio or not has_audio):
            _emit_asset_progress(
                progress_callback,
                completed=completed_work_items,
                total_work_items=total_work_items,
                total_scenes=total_scenes,
                asset_kind="audio",
                scene=scene,
                status="running",
            )
            try:
                audio_result = generate_scene_audio_result(scene, project_dir, **tts_kwargs)
                path = Path(str(audio_result["path"]))
                scene["audio_path"] = str(path)
                result["audio_generated"] += 1
                cost_entry = tts_entry(
                    scene=scene,
                    provider=str(audio_result.get("provider") or tts_kwargs.get("tts_provider") or "kokoro"),
                    model=str(audio_result.get("model") or tts_kwargs.get("openai_model_id") or tts_kwargs.get("elevenlabs_model_id") or ""),
                    estimated=False,
                    operation="asset_pass",
                    purpose="narration",
                    text=str(scene.get("narration") or ""),
                )
                append_actual_cost_entry(plan, cost_entry)
                _emit_asset_progress(
                    progress_callback,
                    completed=completed_work_items,
                    total_work_items=total_work_items,
                    total_scenes=total_scenes,
                    asset_kind="audio",
                    scene=scene,
                    status="done",
                )
            except Exception as exc:  # pragma: no cover - provider/network failure
                result["audio_failures"].append(
                    {"scene_id": int(scene.get("id", 0)), "error": str(exc)}
                )
                _emit_asset_progress(
                    progress_callback,
                    completed=completed_work_items,
                    total_work_items=total_work_items,
                    total_scenes=total_scenes,
                    asset_kind="audio",
                    scene=scene,
                    status="error",
                )
            completed_work_items += 1
        elif generate_audio:
            result["audio_skipped"] += 1
            _emit_asset_progress(
                progress_callback,
                completed=completed_work_items,
                total_work_items=total_work_items,
                total_scenes=total_scenes,
                asset_kind="audio",
                scene=scene,
                status="skipped",
            )
            completed_work_items += 1

        if manifestation == "authored_image" and generate_images:
            has_image = _scene_has_image(scene)
            if image_provider == "manual":
                if has_image:
                    result["images_skipped"] += 1
                    _emit_asset_progress(
                        progress_callback,
                        completed=completed_work_items,
                        total_work_items=total_work_items,
                        total_scenes=total_scenes,
                        asset_kind="image",
                        scene=scene,
                        status="skipped",
                    )
                else:
                    result["image_failures"].append(
                        {
                            "scene_id": int(scene.get("id", 0)),
                            "error": "Image generation is configured for local/manual visuals.",
                        }
                    )
                    _emit_asset_progress(
                        progress_callback,
                        completed=completed_work_items,
                        total_work_items=total_work_items,
                        total_scenes=total_scenes,
                        asset_kind="image",
                        scene=scene,
                        status="error",
                    )
                completed_work_items += 1
            elif regenerate_images or not has_image:
                _emit_asset_progress(
                    progress_callback,
                    completed=completed_work_items,
                    total_work_items=total_work_items,
                    total_scenes=total_scenes,
                    asset_kind="image",
                    scene=scene,
                    status="running",
                )
                try:
                    path = generate_scene_image(
                        scene,
                        project_dir,
                        brief=brief,
                        provider=image_provider,
                        model=image_generation_model,
                    )
                    scene["image_path"] = str(path)
                    result["images_generated"] += 1
                    append_actual_cost_entry(
                        plan,
                        image_generation_entry(
                            scene=scene,
                            provider=image_provider,
                            model=image_generation_model,
                            estimated=False,
                            operation="asset_pass",
                        ),
                    )
                    _emit_asset_progress(
                        progress_callback,
                        completed=completed_work_items,
                        total_work_items=total_work_items,
                        total_scenes=total_scenes,
                        asset_kind="image",
                        scene=scene,
                        status="done",
                    )
                except Exception as exc:  # pragma: no cover - provider/network failure
                    result["image_failures"].append(
                        {"scene_id": int(scene.get("id", 0)), "error": str(exc)}
                    )
                    _emit_asset_progress(
                        progress_callback,
                        completed=completed_work_items,
                        total_work_items=total_work_items,
                        total_scenes=total_scenes,
                        asset_kind="image",
                        scene=scene,
                        status="error",
                    )
                completed_work_items += 1
            else:
                result["images_skipped"] += 1
                _emit_asset_progress(
                    progress_callback,
                    completed=completed_work_items,
                    total_work_items=total_work_items,
                    total_scenes=total_scenes,
                    asset_kind="image",
                    scene=scene,
                    status="skipped",
                    )
                completed_work_items += 1

        if manifestation == "source_video" and generate_videos:
            has_video = _scene_has_video(scene)
            if video_provider == "agent" and (regenerate_videos or not has_video):
                _emit_asset_progress(
                    progress_callback,
                    completed=completed_work_items,
                    total_work_items=total_work_items,
                    total_scenes=total_scenes,
                    asset_kind="video",
                    scene=scene,
                    status="running",
                )
                try:
                    selected_agent = choose_agent_cli(str(agent_demo_profile.get("preferred_agent") or "").strip() or None)
                    if not selected_agent:
                        raise ValueError("Agent demo requested, but neither `codex` nor `claude` is installed.")
                    agent_name, _ = selected_agent
                    prompt = build_agent_demo_prompt(
                        project_dir=project_dir,
                        scene_uids=[str(scene.get("uid") or "")],
                        workspace_path=str(agent_demo_profile.get("workspace_path") or "").strip() or None,
                        app_url=str(agent_demo_profile.get("app_url") or "").strip() or None,
                        launch_command=str(agent_demo_profile.get("launch_command") or "").strip() or None,
                        expected_url=str(agent_demo_profile.get("expected_url") or "").strip() or None,
                        run_until="assets",
                    )
                    prompt_path = project_dir / ".cathode" / "agent_demo" / "asset_pass" / f"{scene.get('uid') or scene.get('id')}.prompt.txt"
                    run_agent_demo_cli(
                        agent_name=agent_name,
                        prompt=prompt,
                        prompt_path=prompt_path,
                        project_dir=project_dir,
                        workspace_path=str(agent_demo_profile.get("workspace_path") or "").strip() or None,
                    )
                    refreshed = load_plan(project_dir)
                    if not refreshed:
                        raise ValueError("Agent demo finished without leaving a readable plan.json behind.")
                    refreshed_scene = next(
                        (candidate for candidate in refreshed.get("scenes", []) if str(candidate.get("uid") or "") == str(scene.get("uid") or "")),
                        None,
                    )
                    if not refreshed_scene or not _scene_has_video(refreshed_scene):
                        raise ValueError("Agent demo finished, but the target scene still has no video clip.")
                    plan = refreshed
                    scenes = list(plan.get("scenes", []))
                    result["videos_generated"] += 1
                    _emit_asset_progress(
                        progress_callback,
                        completed=completed_work_items,
                        total_work_items=total_work_items,
                        total_scenes=total_scenes,
                        asset_kind="video",
                        scene=refreshed_scene,
                        status="done",
                    )
                except Exception as exc:  # pragma: no cover - external agent/runtime failure
                    result["video_failures"].append(
                        {"scene_id": int(scene.get("id", 0)), "error": str(exc)}
                    )
                    _emit_asset_progress(
                        progress_callback,
                        completed=completed_work_items,
                        total_work_items=total_work_items,
                        total_scenes=total_scenes,
                        asset_kind="video",
                        scene=scene,
                        status="error",
                    )
                completed_work_items += 1
            elif video_provider not in {"local", "replicate"}:
                if has_video:
                    result["videos_skipped"] += 1
                    _emit_asset_progress(
                        progress_callback,
                        completed=completed_work_items,
                        total_work_items=total_work_items,
                        total_scenes=total_scenes,
                        asset_kind="video",
                        scene=scene,
                        status="skipped",
                    )
                else:
                    result["video_failures"].append(
                        {
                            "scene_id": int(scene.get("id", 0)),
                            "error": "Video generation is configured for upload-only clips, local backends, or supported cloud providers only.",
                        }
                    )
                    _emit_asset_progress(
                        progress_callback,
                        completed=completed_work_items,
                        total_work_items=total_work_items,
                        total_scenes=total_scenes,
                        asset_kind="video",
                        scene=scene,
                        status="error",
                    )
                completed_work_items += 1
            elif regenerate_videos or not has_video:
                _emit_asset_progress(
                    progress_callback,
                    completed=completed_work_items,
                    total_work_items=total_work_items,
                    total_scenes=total_scenes,
                    asset_kind="video",
                    scene=scene,
                    status="running",
                )
                try:
                    video_result = generate_scene_video_result(
                        scene,
                        project_dir,
                        brief=brief,
                        provider=video_provider,
                        model=video_generation_model,
                        model_selection_mode=video_model_selection_mode,
                        quality_mode=video_quality_mode,
                        generate_audio=video_generate_audio,
                        image_provider=image_provider,
                        image_model=image_generation_model,
                        tts_kwargs=tts_kwargs,
                    )
                    path = Path(str(video_result["path"]))
                    scene["video_path"] = str(path)
                    uses_clip_audio = bool(video_result.get("provider") == "replicate" and video_result.get("generate_audio"))
                    scene["video_audio_source"] = "clip" if uses_clip_audio else "narration"
                    if uses_clip_audio:
                        scene["audio_path"] = None
                    result["videos_generated"] += 1
                    append_actual_cost_entry(
                        plan,
                        video_generation_entry(
                            scene=scene,
                            provider=str(video_result.get("provider") or video_provider),
                            model=str(video_result.get("model") or video_generation_model),
                            model_selection_mode=video_model_selection_mode,
                            quality_mode=str(video_result.get("quality_mode") or video_quality_mode),
                            generate_audio=bool(video_result.get("generate_audio")),
                            estimated=False,
                            operation="asset_pass",
                            duration_seconds=float(video_result.get("duration_seconds") or 0.0),
                        ),
                    )
                    if video_result.get("reference_image_generated"):
                        append_actual_cost_entry(
                            plan,
                            image_generation_entry(
                                scene=scene,
                                provider=image_provider,
                                model=image_generation_model,
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
                    _emit_asset_progress(
                        progress_callback,
                        completed=completed_work_items,
                        total_work_items=total_work_items,
                        total_scenes=total_scenes,
                        asset_kind="video",
                        scene=scene,
                        status="done",
                    )
                except Exception as exc:  # pragma: no cover - provider/runtime failure
                    result["video_failures"].append(
                        {"scene_id": int(scene.get("id", 0)), "error": str(exc)}
                    )
                    _emit_asset_progress(
                        progress_callback,
                        completed=completed_work_items,
                        total_work_items=total_work_items,
                        total_scenes=total_scenes,
                        asset_kind="video",
                        scene=scene,
                        status="error",
                    )
                completed_work_items += 1
            else:
                result["videos_skipped"] += 1
                _emit_asset_progress(
                    progress_callback,
                    completed=completed_work_items,
                    total_work_items=total_work_items,
                    total_scenes=total_scenes,
                    asset_kind="video",
                    scene=scene,
                    status="skipped",
                )
                completed_work_items += 1

        save_plan(project_dir, plan)

    scene_review = None
    plan, normalized_before_review = normalize_authored_image_scene_identities(project_dir, plan)
    if normalized_before_review:
        save_plan(project_dir, plan)
        plan = load_plan(project_dir) or plan
    primary_review_candidates = _primary_only_scene_review_candidates(plan)
    if primary_review_candidates:
        def _run_asset_review(trigger: str, scene_uids: list[str] | None = None) -> dict[str, Any]:
            refreshed_plan = load_plan(project_dir) or plan
            refreshed_plan, normalized = normalize_authored_image_scene_identities(
                project_dir,
                refreshed_plan,
                scene_uids=scene_uids,
            )
            if normalized:
                save_plan(project_dir, refreshed_plan)
                refreshed_plan = load_plan(project_dir) or refreshed_plan
            refreshed_candidates = _primary_only_scene_review_candidates(refreshed_plan, scene_uids=scene_uids)
            if not refreshed_candidates:
                raise ValueError("No reviewable primary-visual scenes were available for asset review.")
            return review_project_scenes(
                project_dir,
                trigger=trigger,
                scene_candidates=refreshed_candidates,
                scene_uids=scene_uids,
            )

        try:
            scene_review = _run_asset_review("post_asset_generation_review")
            plan = load_plan(project_dir) or plan
            plan, repairs_applied = _attempt_text_repairs(
                project_dir,
                plan,
                image_provider=image_provider,
                image_generation_model=image_generation_model,
                image_profile=image_profile,
                review_runner=_run_asset_review,
                exact_review_trigger="post_asset_exact_text_edit_review",
                synonym_review_trigger="post_asset_synonym_regenerate_review",
            )
            if repairs_applied:
                scene_review = _run_asset_review("post_asset_review_after_repairs")
                plan = load_plan(project_dir) or plan
            result["scene_review"] = scene_review
            unresolved_text_repairs = [
                str(scene.get("uid") or scene.get("id") or "")
                for scene in plan.get("scenes", [])
                if isinstance(scene, dict) and _winning_text_repairs(scene)
            ]
            if unresolved_text_repairs:
                result["text_review_failures"] = unresolved_text_repairs
        except Exception as exc:
            result["scene_review_error"] = str(exc)

    if progress_callback is not None:
        progress_callback(
            {
                "progress": 1.0,
                "progress_kind": "assets",
                "progress_label": "Asset pass complete",
                "progress_detail": f"{total_scenes} scene{'s' if total_scenes != 1 else ''} checked",
                "progress_scene_id": None,
                "progress_scene_uid": None,
                "progress_status": "done",
            }
        )

    return result


def render_project_service(
    project_dir: Path,
    *,
    output_filename: str | None = None,
    fps: int | None = None,
    progress_callback: Callable[[dict[str, Any]], None] | None = None,
) -> dict[str, Any]:
    """Render a final MP4 for a project if all required assets exist."""
    plan = load_plan(project_dir)
    if not plan:
        raise ValueError(f"Missing plan.json for project: {project_dir}")
    plan, normalized_before_render = normalize_authored_image_scene_identities(project_dir, plan)
    if normalized_before_render:
        save_plan(project_dir, plan)
        plan = load_plan(project_dir) or plan

    scenes = plan.get("scenes", [])
    render_profile = dict(plan.get("meta", {}).get("render_profile") or {})
    if fps is not None:
        render_profile["fps"] = int(fps)
        plan.setdefault("meta", {})["render_profile"] = render_profile

    render_backend = str(render_profile.get("render_backend") or "ffmpeg").strip().lower() or "ffmpeg"
    missing_visuals = [
        int(scene.get("id", 0))
        for scene in scenes
        if not _scene_has_primary_visual(scene, render_backend=render_backend)
    ]
    missing_audio = [
        int(scene.get("id", 0))
        for scene in scenes
        if not (scene.get("audio_path") and Path(str(scene["audio_path"])).exists())
    ]
    if missing_visuals or missing_audio:
        return {
            "status": "partial_success",
            "retryable": True,
            "suggestion": "Generate missing assets or upload required clips before rendering.",
            "missing_visual_scenes": missing_visuals,
            "missing_audio_scenes": missing_audio,
            "video_path": None,
        }

    resolved_name = output_filename or f"{Path(project_dir).name}.mp4"
    if progress_callback is not None:
        progress_callback(
            {
                "progress": 0.01,
                "progress_kind": "render",
                "progress_label": "Preparing render",
                "progress_detail": f"backend={render_backend}",
                "progress_status": "preparing",
            }
        )
    image_profile = resolve_image_profile(plan.get("meta", {}).get("image_profile"))
    image_provider = str(image_profile.get("provider") or "manual")
    image_generation_model = str(
        image_profile.get("generation_model") or default_image_profile()["generation_model"]
    )

    def _render_video(current_plan: dict[str, Any]) -> tuple[Path, dict[str, Any]]:
        if render_backend == "remotion":
            output_path = Path(project_dir) / resolved_name
            manifest = build_remotion_manifest(
                project_dir=Path(project_dir),
                plan=current_plan,
                output_path=output_path,
                render_profile=render_profile,
            )
            rendered_path = render_manifest_with_remotion(
                manifest,
                output_path=output_path,
                progress_callback=progress_callback,
            )
        else:
            rendered_path = assemble_video(
                current_plan.get("scenes", []),
                Path(project_dir),
                output_filename=resolved_name,
                fps=int(render_profile.get("fps") or 24),
                render_profile=render_profile,
            )
        return rendered_path, compress_video_if_oversized(
            rendered_path,
            render_profile=render_profile,
            progress_callback=progress_callback,
        )

    def _run_review(trigger: str, scene_uids: list[str] | None = None) -> dict[str, Any]:
        refreshed_plan = load_plan(project_dir) or plan
        refreshed_plan, normalized = normalize_authored_image_scene_identities(
            project_dir,
            refreshed_plan,
            scene_uids=scene_uids,
        )
        if normalized:
            save_plan(project_dir, refreshed_plan)
            refreshed_plan = load_plan(project_dir) or refreshed_plan
        return review_project_scenes(
            project_dir,
            trigger=trigger,
            scene_uids=scene_uids,
        )

    def _run_review_for_scenes(trigger: str, scene_uids: list[str]) -> dict[str, Any]:
        return _run_review(trigger, scene_uids)

    def _scene_requests_fallback(scene: dict[str, Any]) -> bool:
        manifestation_plan = scene.get("manifestation_plan") if isinstance(scene.get("manifestation_plan"), dict) else {}
        fallback_path = str(manifestation_plan.get("fallback_path") or "").strip().lower()
        if not fallback_path:
            return False
        primary = scene_primary_manifestation(scene)
        if primary == "native_remotion":
            return False
        return fallback_path != primary

    def _resolve_project_path(raw_path: Any) -> str | None:
        value = str(raw_path or "").strip()
        if not value:
            return None
        path = Path(value).expanduser()
        if path.is_absolute():
            return str(path.resolve())
        return str((Path(project_dir) / value).resolve())

    def _apply_pre_render_candidate_winners(current_plan: dict[str, Any]) -> tuple[dict[str, Any], bool]:
        changed = False
        for scene in current_plan.get("scenes", []):
            if not isinstance(scene, dict):
                continue
            verdict = scene.get("judge_verdict") if isinstance(scene.get("judge_verdict"), dict) else {}
            winner = str(verdict.get("winner") or "").strip()
            candidate_outputs = scene.get("candidate_outputs") if isinstance(scene.get("candidate_outputs"), dict) else {}
            winner_payload = candidate_outputs.get(winner) if winner and isinstance(candidate_outputs.get(winner), dict) else None
            if not winner_payload:
                continue
            candidate_type = str(winner_payload.get("candidate_type") or "").strip().lower()
            if not candidate_type or candidate_type == scene_primary_manifestation(scene):
                continue

            candidate_spec = winner_payload.get("candidate_spec") if isinstance(winner_payload.get("candidate_spec"), dict) else {}
            if candidate_type == "native_remotion":
                composition = candidate_spec.get("composition") if isinstance(candidate_spec.get("composition"), dict) else {}
                motion = candidate_spec.get("motion") if isinstance(candidate_spec.get("motion"), dict) else {}
                if not composition:
                    continue
                scene["scene_type"] = "motion"
                scene["composition"] = composition
                scene["motion"] = motion or {
                    "template_id": str(composition.get("family") or "").strip(),
                    "props": composition.get("props") if isinstance(composition.get("props"), dict) else {},
                    "rationale": str(composition.get("rationale") or "").strip(),
                    "render_path": composition.get("render_path"),
                    "preview_path": composition.get("preview_path"),
                }
                scene["image_path"] = None
                preview_source = _resolve_project_path(winner_payload.get("source_path"))
                if preview_source:
                    scene["preview_path"] = preview_source
                    scene["composition"]["preview_path"] = preview_source
                    if isinstance(scene.get("motion"), dict):
                        scene["motion"]["preview_path"] = preview_source
                changed = True
                continue

            if candidate_type == "authored_image":
                scene["scene_type"] = "image"
                scene["video_path"] = None
                scene["preview_path"] = None
                source_path = _resolve_project_path(winner_payload.get("source_path"))
                if source_path:
                    scene["image_path"] = source_path
                composition = scene.get("composition") if isinstance(scene.get("composition"), dict) else {}
                composition["family"] = "static_media"
                composition["mode"] = "none"
                composition["manifestation"] = "authored_image"
                composition["transition_after"] = None
                scene["composition"] = composition
                changed = True
                continue

            if candidate_type == "source_video":
                scene["scene_type"] = "video"
                scene["image_path"] = None
                source_path = _resolve_project_path(winner_payload.get("source_path"))
                if source_path:
                    scene["video_path"] = source_path
                composition = scene.get("composition") if isinstance(scene.get("composition"), dict) else {}
                composition["manifestation"] = "source_video"
                scene["composition"] = composition
                changed = True
        return current_plan, changed

    candidate_scene_uids = [
        str(scene.get("uid") or "").strip()
        for scene in plan.get("scenes", [])
        if isinstance(scene, dict) and _scene_requests_fallback(scene)
    ]
    if candidate_scene_uids:
        try:
            _run_review_for_scenes("pre_render_candidate_selection", candidate_scene_uids)
        except Exception as exc:
            return {
                "status": "partial_success",
                "retryable": True,
                "suggestion": "Mandatory pre-render candidate selection failed. Resolve the scene review runner or the fallback candidate generation error before publishing.",
                "missing_visual_scenes": [],
                "missing_audio_scenes": [],
                "video_path": None,
                "scene_review_error": str(exc),
            }
        plan = load_plan(project_dir) or plan
        plan, winners_applied = _apply_pre_render_candidate_winners(plan)
        if winners_applied:
            save_plan(project_dir, plan)
            plan = load_plan(project_dir) or plan

    video_path, compression_result = _render_video(plan)
    plan.setdefault("meta", {})["video_path"] = str(video_path)
    plan.setdefault("meta", {})["rendered_utc"] = utc_now_iso()
    plan.setdefault("meta", {})["video_compression"] = compression_result
    save_plan(project_dir, plan)
    try:
        scene_review = _run_review("post_render_review")
    except Exception as exc:
        if progress_callback is not None:
            progress_callback(
                {
                    "progress": 1.0,
                    "progress_kind": "render",
                    "progress_label": "Render complete, scene review failed",
                    "progress_detail": str(exc),
                    "progress_status": "error",
                }
            )
        return {
            "status": "partial_success",
            "retryable": True,
            "suggestion": "Final render completed, but mandatory slide-by-slide scene review failed. Resolve the review runner and retry review before publishing.",
            "missing_visual_scenes": [],
            "missing_audio_scenes": [],
            "video_path": str(video_path),
            "compression": compression_result,
            "scene_review_error": str(exc),
        }
    plan = load_plan(project_dir) or plan
    plan, repairs_applied = _attempt_text_repairs(
        project_dir,
        plan,
        image_provider=image_provider,
        image_generation_model=image_generation_model,
        image_profile=image_profile,
        review_runner=_run_review,
        exact_review_trigger="post_exact_text_edit_review",
        synonym_review_trigger="post_synonym_regenerate_review",
    )
    if repairs_applied:
        video_path, compression_result = _render_video(plan)
        plan.setdefault("meta", {})["video_path"] = str(video_path)
        plan.setdefault("meta", {})["rendered_utc"] = utc_now_iso()
        plan.setdefault("meta", {})["video_compression"] = compression_result
        save_plan(project_dir, plan)
        scene_review = _run_review("post_render_review_after_repairs")
    if progress_callback is not None:
        progress_callback(
            {
                "progress": 1.0,
                "progress_kind": "render",
                "progress_label": "Render complete",
                "progress_detail": str(video_path),
                "progress_status": "done",
            }
        )
    latest_plan = load_plan(project_dir) or plan
    unresolved_text_repairs = [
        str(scene.get("uid") or scene.get("id") or "")
        for scene in latest_plan.get("scenes", [])
        if isinstance(scene, dict) and _winning_text_repairs(scene)
    ]
    if unresolved_text_repairs:
        return {
            "status": "partial_success",
            "retryable": True,
            "suggestion": "Render completed, but some authored-image scenes still failed mandatory text review after exact edit and synonym regeneration.",
            "missing_visual_scenes": [],
            "missing_audio_scenes": [],
            "video_path": str(video_path),
            "compression": compression_result,
            "scene_review": scene_review,
            "text_review_failures": unresolved_text_repairs,
        }
    return {
        "status": "succeeded",
        "retryable": False,
        "suggestion": "",
        "missing_visual_scenes": [],
        "missing_audio_scenes": [],
        "video_path": str(video_path),
        "compression": compression_result,
        "scene_review": scene_review,
    }


def process_existing_project_service(
    project_dir: Path,
    *,
    rebuild_storyboard: bool = False,
    generate_images: bool = True,
    generate_videos: bool = True,
    generate_audio: bool = True,
    regenerate_videos: bool = False,
    regenerate_audio: bool = False,
    assemble_final: bool = True,
    fps: int | None = None,
    output_filename: str | None = None,
) -> dict[str, Any]:
    """Shared non-UI batch processing path for an existing project."""
    if rebuild_storyboard:
        rebuild_storyboard_service(project_dir)

    result: dict[str, Any] = {"assets": None, "render": None}
    if generate_images or generate_videos or generate_audio or regenerate_videos or regenerate_audio:
        result["assets"] = generate_project_assets_service(
            project_dir,
            generate_images=generate_images,
            generate_videos=generate_videos,
            generate_audio=generate_audio or regenerate_audio,
            regenerate_images=False,
            regenerate_videos=regenerate_videos,
            regenerate_audio=regenerate_audio,
        )
    if assemble_final:
        result["render"] = render_project_service(
            project_dir,
            output_filename=output_filename,
            fps=fps,
        )
    return result
