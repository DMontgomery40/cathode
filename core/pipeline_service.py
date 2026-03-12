"""Shared headless pipeline services for app, batch, and MCP flows."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from .demo_assets import (
    apply_footage_manifest_to_scenes,
    build_footage_summary,
    copy_footage_manifest_into_project,
    normalize_footage_manifest,
)
from .director import analyze_style_references
from .image_gen import generate_scene_image
from .project_schema import default_image_profile, normalize_brief
from .project_store import copy_external_files, ensure_project_dir, load_plan, save_plan
from .runtime import choose_llm_provider, resolve_image_profile, resolve_tts_profile, resolve_video_profile
from .video_assembly import assemble_video
from .video_gen import generate_scene_video
from .voice_gen import generate_scene_audio
from .workflow import create_plan_from_brief, rebuild_plan_from_meta


def utc_now_iso() -> str:
    """Return a UTC timestamp in ISO format."""
    return datetime.utcnow().isoformat()


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
    tts_profile: dict[str, Any] | None = None,
    render_profile: dict[str, Any] | None = None,
    project_dir: Path | None = None,
) -> tuple[Path, dict[str, Any]]:
    """Create a project directory, persist style refs, and generate the initial storyboard."""
    chosen_provider = choose_llm_provider(provider)
    resolved_image_profile = resolve_image_profile(image_profile)
    resolved_video_profile = resolve_video_profile(video_profile)
    resolved_tts_profile = resolve_tts_profile(tts_profile)
    project_dir = Path(project_dir) if project_dir is not None else ensure_project_dir(project_name, overwrite=overwrite)
    if project_dir is not None:
        project_dir.mkdir(parents=True, exist_ok=True)

    normalized_brief = normalize_brief(brief)
    normalized_brief["project_name"] = project_dir.name

    requested_footage_manifest = list(normalized_brief.get("footage_manifest") or [])
    saved_style_refs = _persist_style_references(project_dir, normalized_brief.get("style_reference_paths"))
    saved_footage_manifest = _persist_footage_manifest(project_dir, normalized_brief.get("footage_manifest"))
    style_reference_summary = str(normalized_brief.get("style_reference_summary") or "").strip()
    if saved_style_refs and not style_reference_summary:
        style_reference_summary = analyze_style_references(
            [str(path) for path in saved_style_refs],
            normalized_brief,
            provider=chosen_provider,
        )
        (project_dir / "style_refs" / "style_reference_summary.txt").write_text(
            style_reference_summary,
            encoding="utf-8",
        )

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
        provider=chosen_provider,
        image_profile=resolved_image_profile,
        video_profile=resolved_video_profile,
        tts_profile=resolved_tts_profile,
        render_profile=render_profile,
    )
    plan["scenes"] = apply_footage_manifest_to_scenes(plan.get("scenes", []), saved_footage_manifest)
    plan.setdefault("meta", {})["brief"] = normalize_brief(normalized_brief, base_dir=project_dir)
    plan.setdefault("meta", {})["footage_manifest"] = saved_footage_manifest
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
    rebuilt = rebuild_plan_from_meta(plan, provider=provider)
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
    return scene_type if scene_type in {"image", "video"} else "image"


def _scene_has_primary_visual(scene: dict[str, Any]) -> bool:
    return _scene_has_video(scene) if _scene_type(scene) == "video" else _scene_has_image(scene)


def generate_project_assets_service(
    project_dir: Path,
    *,
    generate_images: bool = True,
    generate_videos: bool = True,
    generate_audio: bool = True,
    regenerate_images: bool = False,
    regenerate_videos: bool = False,
    regenerate_audio: bool = False,
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

    for scene in plan.get("scenes", []):
        scene_type = _scene_type(scene)
        has_audio = scene.get("audio_path") and Path(str(scene["audio_path"])).exists()
        if generate_audio and (regenerate_audio or not has_audio):
            try:
                path = generate_scene_audio(scene, project_dir, **tts_kwargs)
                scene["audio_path"] = str(path)
                result["audio_generated"] += 1
            except Exception as exc:  # pragma: no cover - provider/network failure
                result["audio_failures"].append(
                    {"scene_id": int(scene.get("id", 0)), "error": str(exc)}
                )
        elif generate_audio:
            result["audio_skipped"] += 1

        if scene_type == "image" and generate_images:
            has_image = _scene_has_image(scene)
            if image_provider == "manual":
                if has_image:
                    result["images_skipped"] += 1
                else:
                    result["image_failures"].append(
                        {
                            "scene_id": int(scene.get("id", 0)),
                            "error": "Image generation is configured for local/manual visuals.",
                        }
                    )
            elif regenerate_images or not has_image:
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
                except Exception as exc:  # pragma: no cover - provider/network failure
                    result["image_failures"].append(
                        {"scene_id": int(scene.get("id", 0)), "error": str(exc)}
                    )
            else:
                result["images_skipped"] += 1

        if scene_type == "video" and generate_videos:
            has_video = _scene_has_video(scene)
            if video_provider != "local":
                if has_video:
                    result["videos_skipped"] += 1
                else:
                    result["video_failures"].append(
                        {
                            "scene_id": int(scene.get("id", 0)),
                            "error": "Video generation is configured for upload/local-manual clips only.",
                        }
                    )
            elif regenerate_videos or not has_video:
                try:
                    path = generate_scene_video(
                        scene,
                        project_dir,
                        brief=brief,
                        provider=video_provider,
                        model=video_generation_model,
                    )
                    scene["video_path"] = str(path)
                    result["videos_generated"] += 1
                except Exception as exc:  # pragma: no cover - provider/runtime failure
                    result["video_failures"].append(
                        {"scene_id": int(scene.get("id", 0)), "error": str(exc)}
                    )
            else:
                result["videos_skipped"] += 1

        save_plan(project_dir, plan)

    return result


def render_project_service(
    project_dir: Path,
    *,
    output_filename: str | None = None,
    fps: int | None = None,
) -> dict[str, Any]:
    """Render a final MP4 for a project if all required assets exist."""
    plan = load_plan(project_dir)
    if not plan:
        raise ValueError(f"Missing plan.json for project: {project_dir}")

    scenes = plan.get("scenes", [])
    missing_visuals = [int(scene.get("id", 0)) for scene in scenes if not _scene_has_primary_visual(scene)]
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

    render_profile = dict(plan.get("meta", {}).get("render_profile") or {})
    if fps is not None:
        render_profile["fps"] = int(fps)
        plan.setdefault("meta", {})["render_profile"] = render_profile

    resolved_name = output_filename or f"{Path(project_dir).name}.mp4"
    video_path = assemble_video(
        scenes,
        Path(project_dir),
        output_filename=resolved_name,
        fps=int(render_profile.get("fps") or 24),
        render_profile=render_profile,
    )
    plan.setdefault("meta", {})["video_path"] = str(video_path)
    plan.setdefault("meta", {})["rendered_utc"] = utc_now_iso()
    save_plan(project_dir, plan)
    return {
        "status": "succeeded",
        "retryable": False,
        "suggestion": "",
        "missing_visual_scenes": [],
        "missing_audio_scenes": [],
        "video_path": str(video_path),
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
