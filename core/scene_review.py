"""Backend scene-review orchestration for Cathode slide visuals."""

from __future__ import annotations

import base64
import copy
import json
import os
import re
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from .composition_planner import _composition_props_from_scene, _normalize_composition_intent, _three_data_stage_data
from .image_gen import generate_scene_image
from .remotion_render import build_remotion_manifest, render_manifest_with_remotion
from .project_schema import scene_primary_manifestation
from .project_store import load_plan, save_plan
from .runtime import REPO_ROOT, check_api_keys
from .runtime import resolve_image_profile
from .video_assembly import get_media_duration

SceneJudgeRunner = Callable[[dict[str, Any], dict[str, Any]], Any]

_DEFAULT_FIRST_STABLE_FRAME_SECONDS = 0.5
_REQUIRED_FRAME_ROLES = ("first_stable_readable", "midpoint")
_IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}
_VIDEO_SUFFIXES = {".mp4", ".mov", ".m4v", ".avi", ".mkv", ".webm"}
_FRAME_ROLE_ORDER = {role: index for index, role in enumerate(_REQUIRED_FRAME_ROLES)}
_SUPPORTED_NATIVE_FALLBACK_FAMILIES = {
    "software_demo_focus",
    "kinetic_statements",
    "bullet_stack",
    "quote_focus",
    "three_data_stage",
    "surreal_tableau_3d",
    # Clinical template families (deterministic Remotion overlays)
    "cover_hook",
    "orientation",
    "clinical_explanation",
    "metric_improvement",
    "brain_region_focus",
    "metric_comparison",
    "timeline_progression",
    "analogy_metaphor",
    "synthesis_summary",
    "closing_cta",
}
_MISSING_CLAUDE_VISUAL_RUNNER_NOTE = (
    "Claude Code is discoverable, but this slice does not guess a local-image attachment "
    "contract that was not explicit in the packet or repo files."
)


def _configured_codex_model() -> str:
    return str(os.getenv("CATHODE_SCENE_JUDGE_CODEX_MODEL") or "").strip() or "local-default"


def _configured_claude_model() -> str:
    return str(os.getenv("CATHODE_SCENE_JUDGE_CLAUDE_MODEL") or "").strip() or "local-default"


def _configured_openai_model() -> str:
    return str(os.getenv("CATHODE_SCENE_JUDGE_OPENAI_MODEL") or "gpt-5.4").strip() or "gpt-5.4"


def _configured_openai_reasoning_effort() -> str:
    return str(os.getenv("CATHODE_SCENE_JUDGE_OPENAI_REASONING_EFFORT") or "xhigh").strip().lower() or "xhigh"


def scene_judge_providers() -> list[dict[str, Any]]:
    """Return scene-judge providers in the locked backend preference order."""
    keys = check_api_keys()
    codex_path = shutil.which("codex")
    claude_path = shutil.which("claude")
    openai_available = bool(keys.get("openai"))

    return [
        {
            "provider": "codex",
            "label": "local Codex",
            "available": bool(codex_path),
            "builtin_runner": bool(codex_path),
            "binary_path": codex_path,
            "model": _configured_codex_model(),
            "reasoning_effort": None,
            "reason": None if codex_path else "codex not found in PATH",
        },
        {
            "provider": "claude_code",
            "label": "local Claude Code",
            "available": bool(claude_path),
            "builtin_runner": False,
            "binary_path": claude_path,
            "model": _configured_claude_model(),
            "reasoning_effort": None,
            "reason": None if not claude_path else _MISSING_CLAUDE_VISUAL_RUNNER_NOTE,
        },
        {
            "provider": "openai_api",
            "label": f"API {_configured_openai_model()} {_configured_openai_reasoning_effort()}",
            "available": openai_available,
            "builtin_runner": openai_available,
            "binary_path": None,
            "model": _configured_openai_model(),
            "reasoning_effort": _configured_openai_reasoning_effort(),
            "reason": None if openai_available else "OPENAI_API_KEY is not configured",
        },
    ]


def choose_scene_judge_provider(
    preferred: str | None = None,
    *,
    allow_external_runner: bool = False,
) -> dict[str, Any]:
    """Choose the first usable scene-judge provider in the locked order."""
    providers = scene_judge_providers()
    normalized_preferred = str(preferred or "").strip().lower()

    if normalized_preferred:
        matched = next((provider for provider in providers if provider["provider"] == normalized_preferred), None)
        if matched is None:
            raise ValueError(f"Unknown scene-judge provider: {preferred}")
        if not matched["available"]:
            raise ValueError(matched["reason"] or f"Scene-judge provider {preferred!r} is unavailable.")
        if not matched["builtin_runner"] and not allow_external_runner:
            raise ValueError(matched["reason"] or f"Scene-judge provider {preferred!r} needs an external runner.")
        return matched

    for provider in providers:
        if not provider["available"]:
            continue
        if provider["builtin_runner"] or allow_external_runner:
            return provider

    reasons = "; ".join(
        f"{provider['provider']}: {provider['reason'] or 'unavailable'}"
        for provider in providers
    )
    raise ValueError(f"No usable scene-judge provider found. {reasons}")


def _slugify_token(value: Any, *, fallback: str) -> str:
    candidate = re.sub(r"[^A-Za-z0-9._-]+", "_", str(value or "").strip()).strip("._-")
    return candidate or fallback


def _path_kind(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in _IMAGE_SUFFIXES:
        return "image"
    if suffix in _VIDEO_SUFFIXES:
        return "video"
    raise ValueError(f"Unsupported scene-review source type: {path}")


def _project_relative_path(project_dir: Path, path: Path) -> str:
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(project_dir.resolve())).replace("\\", "/")
    except ValueError:
        return str(resolved)


def _ensure_timestamp(value: Any, *, fallback: float) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return fallback
    return max(0.0, parsed)


def _guess_image_media_type(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in {".jpg", ".jpeg"}:
        return "image/jpeg"
    if suffix == ".webp":
        return "image/webp"
    return "image/png"


def _data_url_for_image(path: str | Path) -> str:
    image_path = Path(path)
    media_type = _guess_image_media_type(image_path)
    encoded = base64.b64encode(image_path.read_bytes()).decode("utf-8")
    return f"data:{media_type};base64,{encoded}"


def _extract_video_frame(source_path: Path, output_path: Path, timestamp_seconds: float) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-ss",
            f"{timestamp_seconds:.3f}",
            "-i",
            str(source_path),
            "-frames:v",
            "1",
            "-q:v",
            "2",
            str(output_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )


def _normalize_explicit_frame_refs(
    project_dir: Path,
    candidate_id: str,
    frame_refs: list[Any],
) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    seen_roles: set[str] = set()
    for item in frame_refs:
        if not isinstance(item, dict):
            continue
        frame_role = str(item.get("frame_role") or item.get("kind") or "").strip().lower()
        if frame_role not in _REQUIRED_FRAME_ROLES:
            continue
        path_value = str(item.get("path") or "").strip()
        if not path_value:
            continue
        path = Path(path_value).expanduser()
        if not path.is_absolute():
            path = (project_dir / path).resolve()
        if not path.exists():
            raise ValueError(f"Explicit review frame does not exist: {path}")
        seen_roles.add(frame_role)
        normalized.append(
            {
                "candidate_id": candidate_id,
                "frame_role": frame_role,
                "absolute_path": str(path.resolve()),
                "path": _project_relative_path(project_dir, path),
                "timestamp_seconds": _ensure_timestamp(item.get("timestamp_seconds"), fallback=0.0),
            }
        )

    missing_roles = [role for role in _REQUIRED_FRAME_ROLES if role not in seen_roles]
    if missing_roles:
        raise ValueError(
            f"Candidate {candidate_id!r} is missing required review frames: {', '.join(missing_roles)}"
        )
    normalized.sort(key=lambda item: _FRAME_ROLE_ORDER[item["frame_role"]])
    return normalized


def default_scene_review_candidates(scene: dict[str, Any]) -> list[dict[str, Any]]:
    """Return the default review candidate for a scene from its current persisted assets.

    Native-remotion scenes that haven't been rendered yet have no visual
    source to review -- return an empty list instead of raising so callers
    can skip them gracefully.
    """
    composition = scene.get("composition") if isinstance(scene.get("composition"), dict) else {}
    motion = scene.get("motion") if isinstance(scene.get("motion"), dict) else {}

    path_candidates = [
        ("motion_render", motion.get("render_path")),
        ("composition_render", composition.get("render_path")),
        ("scene_preview", scene.get("preview_path")),
        ("motion_preview", motion.get("preview_path")),
        ("composition_preview", composition.get("preview_path")),
        ("scene_video", scene.get("video_path")),
        ("scene_image", scene.get("image_path")),
    ]
    for _, raw_path in path_candidates:
        value = str(raw_path or "").strip()
        if not value:
            continue
        source_path = Path(value).expanduser()
        if source_path.exists():
            return [
                {
                    "candidate_id": "primary",
                    "label": "Primary candidate",
                    "candidate_type": scene_primary_manifestation(scene),
                    "source_path": str(source_path.resolve()),
                }
            ]
    if scene_primary_manifestation(scene) == "native_remotion":
        return []
    raise ValueError(
        f"Scene {scene.get('uid') or scene.get('id') or '(unknown)'} has no reviewable visual source."
    )


def _manifestation_plan(scene: dict[str, Any]) -> dict[str, Any]:
    raw = scene.get("manifestation_plan")
    return raw if isinstance(raw, dict) else {}


def _fallback_path(scene: dict[str, Any]) -> str | None:
    value = str(_manifestation_plan(scene).get("fallback_path") or "").strip().lower()
    if value in {"authored_image", "native_remotion", "source_video"}:
        return value
    return None


def _primary_candidate_from_scene(scene: dict[str, Any]) -> dict[str, Any]:
    primary = default_scene_review_candidates(scene)[0]
    candidate_type = scene_primary_manifestation(scene)
    return {
        **primary,
        "candidate_id": candidate_type,
        "label": f"{candidate_type} candidate",
        "candidate_type": candidate_type,
        "candidate_spec": _manifestation_plan(scene) or None,
    }


def _native_fallback_family(scene: dict[str, Any]) -> str | None:
    plan = _manifestation_plan(scene)
    hinted = str(plan.get("native_family_hint") or "").strip()
    if hinted in _SUPPORTED_NATIVE_FALLBACK_FAMILIES:
        return hinted
    composition = scene.get("composition") if isinstance(scene.get("composition"), dict) else {}
    current_family = str(composition.get("family") or "").strip()
    if current_family in _SUPPORTED_NATIVE_FALLBACK_FAMILIES:
        return current_family
    return None


def _native_candidate_scene(scene: dict[str, Any]) -> dict[str, Any]:
    family = _native_fallback_family(scene)
    if not family:
        raise ValueError(
            f"Scene {scene.get('uid') or scene.get('id') or '(unknown)'} requested native_remotion fallback without a supported native family hint."
        )

    candidate_scene = copy.deepcopy(scene)
    plan = _manifestation_plan(candidate_scene)
    native_build_prompt = str(plan.get("native_build_prompt") or "").strip()
    staging_notes = str(candidate_scene.get("staging_notes") or "").strip()
    if native_build_prompt:
        candidate_scene["staging_notes"] = " ".join(part for part in (staging_notes, native_build_prompt) if part).strip()
    intent = _normalize_composition_intent(candidate_scene)
    props = _composition_props_from_scene(candidate_scene, intent, family)
    current_composition = candidate_scene.get("composition") if isinstance(candidate_scene.get("composition"), dict) else {}
    current_data = current_composition.get("data") if isinstance(current_composition.get("data"), (dict, list)) else {}
    data = _three_data_stage_data(candidate_scene, intent, current_data, props) if family == "three_data_stage" else current_data
    rationale = native_build_prompt or str(current_composition.get("rationale") or candidate_scene.get("staging_notes") or "").strip()
    candidate_scene["scene_type"] = "motion"
    candidate_scene["composition"] = {
        "family": family,
        "mode": "native",
        "manifestation": "native_remotion",
        "props": props,
        "transition_after": None,
        "data": data if isinstance(data, (dict, list)) else {},
        "render_path": None,
        "preview_path": None,
        "rationale": rationale,
    }
    candidate_scene["motion"] = {
        "template_id": family,
        "props": props,
        "render_path": None,
        "preview_path": None,
        "rationale": rationale,
    }
    candidate_scene["preview_path"] = None
    return candidate_scene


def _render_native_fallback_candidate(
    project_dir: Path,
    plan: dict[str, Any],
    scene: dict[str, Any],
    *,
    review_root: Path,
) -> dict[str, Any]:
    scene_uid = _slugify_token(scene.get("uid") or scene.get("id"), fallback="scene")
    candidate_dir = review_root / "generated_candidates" / scene_uid / "native_remotion"
    candidate_dir.mkdir(parents=True, exist_ok=True)
    output_path = candidate_dir / "native_remotion_preview.mp4"

    candidate_plan = copy.deepcopy(plan)
    candidate_scenes = candidate_plan.get("scenes") if isinstance(candidate_plan.get("scenes"), list) else []
    target_uid = str(scene.get("uid") or "").strip()
    for index, candidate in enumerate(candidate_scenes):
        if str(candidate.get("uid") or "").strip() == target_uid:
            candidate_scenes[index] = _native_candidate_scene(scene)
            break
    else:
        raise ValueError(f"Scene {target_uid!r} not found while building native fallback candidate.")

    manifest = build_remotion_manifest(
        project_dir=project_dir,
        plan=candidate_plan,
        output_path=output_path,
        render_profile=candidate_plan.get("meta", {}).get("render_profile"),
        preview_scene_uid=target_uid,
    )
    preview_path = render_manifest_with_remotion(manifest, output_path=output_path)
    return {
        "candidate_id": "native_remotion",
        "label": "native_remotion candidate",
        "candidate_type": "native_remotion",
        "candidate_spec": {
            "scene_type": "motion",
            "composition": copy.deepcopy(candidate_plan["scenes"][0]["composition"]),
            "motion": copy.deepcopy(candidate_plan["scenes"][0].get("motion")),
        },
        "source_path": str(Path(preview_path).resolve()),
        "first_stable_timestamp_seconds": _DEFAULT_FIRST_STABLE_FRAME_SECONDS,
    }


def _render_authored_image_fallback_candidate(
    project_dir: Path,
    plan: dict[str, Any],
    scene: dict[str, Any],
    *,
    review_root: Path,
) -> dict[str, Any]:
    scene_uid = _slugify_token(scene.get("uid") or scene.get("id"), fallback="scene")
    candidate_dir = review_root / "generated_candidates" / scene_uid / "authored_image"
    candidate_dir.mkdir(parents=True, exist_ok=True)
    review_project_dir = candidate_dir / "project"
    review_project_dir.mkdir(parents=True, exist_ok=True)
    image_profile = resolve_image_profile(plan.get("meta", {}).get("image_profile"))
    provider = str(image_profile.get("provider") or "manual").strip().lower()
    if provider == "manual":
        raise ValueError(
            f"Scene {scene.get('uid') or scene.get('id') or '(unknown)'} requested authored_image fallback but image generation is configured for manual visuals."
        )
    model = str(image_profile.get("generation_model") or "").strip()
    output_path = generate_scene_image(
        scene,
        review_project_dir,
        brief=plan.get("meta", {}).get("brief"),
        provider=provider,
        model=model,
    )
    return {
        "candidate_id": "authored_image",
        "label": "authored_image candidate",
        "candidate_type": "authored_image",
        "candidate_spec": {
            "scene_type": "image",
            "visual_prompt": str(scene.get("visual_prompt") or "").strip(),
            "on_screen_text": [str(item).strip() for item in (scene.get("on_screen_text") or []) if str(item).strip()],
            "composition": {
                "family": "static_media",
                "mode": "none",
                "manifestation": "authored_image",
            },
        },
        "source_path": str(Path(output_path).resolve()),
    }


def auto_scene_review_candidates(
    project_dir: str | Path,
    plan: dict[str, Any],
    scene: dict[str, Any],
    *,
    review_root: str | Path | None = None,
) -> list[dict[str, Any]] | None:
    project_dir = Path(project_dir).expanduser().resolve()
    review_root_path = Path(review_root).expanduser().resolve() if review_root else project_dir / ".cathode" / "scene_review" / "adhoc"
    fallback = _fallback_path(scene)
    if not fallback:
        return None

    primary = scene_primary_manifestation(scene)
    if fallback == primary:
        return None

    primary_defaults = default_scene_review_candidates(scene)
    if not primary_defaults:
        return None  # primary path has no reviewable visual yet (e.g. native_remotion not rendered)

    candidates = [_primary_candidate_from_scene(scene)]
    try:
        if fallback == "native_remotion":
            candidates.append(_render_native_fallback_candidate(project_dir, plan, scene, review_root=review_root_path))
        elif fallback == "authored_image":
            candidates.append(_render_authored_image_fallback_candidate(project_dir, plan, scene, review_root=review_root_path))
    except (ValueError, FileNotFoundError):
        pass  # fallback not viable for this scene's family; proceed with primary only
    return candidates


def prepare_scene_review_candidates(
    project_dir: str | Path,
    scene: dict[str, Any],
    *,
    candidates: list[dict[str, Any]] | None = None,
    review_root: str | Path | None = None,
    first_stable_frame_seconds: float = _DEFAULT_FIRST_STABLE_FRAME_SECONDS,
) -> list[dict[str, Any]]:
    """Resolve or extract the frame refs that power vision-only scene review."""
    project_dir = Path(project_dir).expanduser().resolve()
    scene_uid = _slugify_token(scene.get("uid") or scene.get("id"), fallback="scene")
    resolved_candidates = candidates if isinstance(candidates, list) and candidates else default_scene_review_candidates(scene)
    frames_root = Path(review_root).expanduser().resolve() if review_root else project_dir / ".cathode" / "scene_review" / "adhoc"

    prepared: list[dict[str, Any]] = []
    for index, candidate in enumerate(resolved_candidates, start=1):
        if not isinstance(candidate, dict):
            raise ValueError(f"Scene review candidate #{index} must be a dict.")
        candidate_id = _slugify_token(candidate.get("candidate_id") or f"candidate_{index}", fallback=f"candidate_{index}")
        label = str(candidate.get("label") or candidate_id).strip() or candidate_id
        explicit_frames = candidate.get("frame_refs")
        if isinstance(explicit_frames, list) and explicit_frames:
            frame_refs = _normalize_explicit_frame_refs(project_dir, candidate_id, explicit_frames)
            absolute_source_path = Path(frame_refs[0]["absolute_path"])
            source_kind = "image"
            source_path_display = frame_refs[0]["path"]
        else:
            path_value = str(
                candidate.get("source_path")
                or candidate.get("rendered_path")
                or candidate.get("render_path")
                or candidate.get("preview_path")
                or candidate.get("video_path")
                or candidate.get("image_path")
                or ""
            ).strip()
            if not path_value:
                raise ValueError(f"Scene review candidate {candidate_id!r} is missing a source path.")
            source_path = Path(path_value).expanduser()
            if not source_path.is_absolute():
                source_path = (project_dir / source_path).resolve()
            if not source_path.exists():
                raise ValueError(f"Scene review candidate source does not exist: {source_path}")

            absolute_source_path = source_path.resolve()
            source_path_display = _project_relative_path(project_dir, absolute_source_path)
            source_kind = _path_kind(absolute_source_path)
            if source_kind == "image":
                frame_refs = [
                    {
                        "candidate_id": candidate_id,
                        "frame_role": "first_stable_readable",
                        "absolute_path": str(absolute_source_path),
                        "path": source_path_display,
                        "timestamp_seconds": 0.0,
                    },
                    {
                        "candidate_id": candidate_id,
                        "frame_role": "midpoint",
                        "absolute_path": str(absolute_source_path),
                        "path": source_path_display,
                        "timestamp_seconds": 0.0,
                    },
                ]
            else:
                duration_seconds = float(get_media_duration(absolute_source_path) or 0.0)
                midpoint_seconds = _ensure_timestamp(
                    candidate.get("midpoint_timestamp_seconds"),
                    fallback=duration_seconds / 2.0 if duration_seconds > 0 else 0.0,
                )
                stable_seconds = _ensure_timestamp(
                    candidate.get("first_stable_timestamp_seconds"),
                    fallback=min(max(0.0, first_stable_frame_seconds), midpoint_seconds),
                )
                midpoint_seconds = max(midpoint_seconds, stable_seconds)
                candidate_dir = frames_root / scene_uid / candidate_id
                first_frame_path = candidate_dir / "first_stable_readable.jpg"
                midpoint_frame_path = candidate_dir / "midpoint.jpg"
                _extract_video_frame(absolute_source_path, first_frame_path, stable_seconds)
                _extract_video_frame(absolute_source_path, midpoint_frame_path, midpoint_seconds)
                frame_refs = [
                    {
                        "candidate_id": candidate_id,
                        "frame_role": "first_stable_readable",
                        "absolute_path": str(first_frame_path.resolve()),
                        "path": _project_relative_path(project_dir, first_frame_path),
                        "timestamp_seconds": stable_seconds,
                    },
                    {
                        "candidate_id": candidate_id,
                        "frame_role": "midpoint",
                        "absolute_path": str(midpoint_frame_path.resolve()),
                        "path": _project_relative_path(project_dir, midpoint_frame_path),
                        "timestamp_seconds": midpoint_seconds,
                    },
                ]

        prepared.append(
            {
                "candidate_id": candidate_id,
                "label": label,
                "candidate_type": str(
                    candidate.get("candidate_type")
                    or candidate.get("manifestation")
                    or candidate.get("type")
                    or ("authored_image" if source_kind == "image" else "source_video")
                ).strip()
                or ("authored_image" if source_kind == "image" else "source_video"),
                "candidate_spec": candidate.get("candidate_spec")
                or candidate.get("spec")
                or candidate.get("prompt")
                or candidate.get("manifestation_plan"),
                "source_kind": source_kind,
                "source_path": source_path_display,
                "absolute_source_path": str(absolute_source_path),
                "frame_refs": frame_refs,
            }
        )

    return prepared


def _build_scene_review_prompt(
    *,
    scene: dict[str, Any],
    prepared_candidates: list[dict[str, Any]],
    trigger: str,
) -> str:
    review_mode = "dual-path comparison" if len(prepared_candidates) > 1 else "single-candidate review"
    lines: list[str] = [
        "You are Cathode's backend visual scene judge.",
        "This is a vision-only review over rendered slide images.",
        "Do not use OCR, do not transcribe visible slide text, and do not invent hidden content.",
        "Judge each candidate by actually looking at the attached images.",
        "Inspect every candidate's first stable readable frame and midpoint frame before deciding.",
        "",
        f"Trigger: {trigger}",
        f"Review mode: {review_mode}",
        f"Scene uid: {scene.get('uid') or ''}",
        f"Scene type: {scene.get('scene_type') or 'image'}",
        f"Scene title: {str(scene.get('title') or '').strip()}",
        f"Narration intent: {str(scene.get('narration') or '').strip()}",
        f"Visual prompt intent: {str(scene.get('visual_prompt') or '').strip()}",
    ]
    on_screen_text = scene.get("on_screen_text") if isinstance(scene.get("on_screen_text"), list) else []
    if on_screen_text:
        lines.append("Authored on-screen text targets:")
        lines.extend(f"- {str(item).strip()}" for item in on_screen_text if str(item).strip())
    else:
        lines.append("Authored on-screen text targets: (none)")

    lines.extend(["", "Candidates and required frame refs:"])
    for candidate in prepared_candidates:
        lines.append(f"- {candidate['candidate_id']}: {candidate['label']}")
        for frame in candidate["frame_refs"]:
            lines.append(
                f"  - {frame['frame_role']}: {frame['path']} @ {frame['timestamp_seconds']:.3f}s"
            )

    candidate_ids = ", ".join(candidate["candidate_id"] for candidate in prepared_candidates)
    lines.extend(
        [
            "",
            "Return JSON only with this shape:",
            "{",
            '  "winner": "<one of the candidate ids>",',
            '  "reasons": ["short reason", "..."],',
            '  "candidate_notes": {',
            '    "<candidate id>": ["short note", "..."]',
            "  },",
            '  "text_repairs": [',
            '    {"candidate_id": "<candidate id>", "wrong_text": "<visible text>", "correct_text": "<intended correction>", "reason": "<why the direct edit is safe>"}',
            "  ]",
            "}",
            f"Winner must be one of: {candidate_ids}.",
            "Only include text_repairs when a direct exact text edit is safe and high-confidence.",
            "Use text_repairs only for clearly wrong visible words or labels that should be changed literally.",
        ]
    )
    return "\n".join(lines)


def build_scene_review_request(
    scene: dict[str, Any],
    *,
    prepared_candidates: list[dict[str, Any]],
    trigger: str,
) -> dict[str, Any]:
    """Build the provider-facing scene-review request payload."""
    attachments: list[dict[str, Any]] = []
    for candidate in prepared_candidates:
        for frame in candidate["frame_refs"]:
            attachments.append(
                {
                    "candidate_id": candidate["candidate_id"],
                    "candidate_label": candidate["label"],
                    "frame_role": frame["frame_role"],
                    "absolute_path": frame["absolute_path"],
                    "path": frame["path"],
                    "timestamp_seconds": frame["timestamp_seconds"],
                }
            )

    scene_payload = {
        "uid": str(scene.get("uid") or "").strip(),
        "id": scene.get("id"),
        "scene_type": str(scene.get("scene_type") or "image").strip().lower(),
        "title": str(scene.get("title") or "").strip(),
        "narration": str(scene.get("narration") or "").strip(),
        "visual_prompt": str(scene.get("visual_prompt") or "").strip(),
        "on_screen_text": [
            str(item).strip()
            for item in (scene.get("on_screen_text") or [])
            if str(item).strip()
        ],
    }
    return {
        "trigger": str(trigger or "").strip() or "scene_review",
        "review_mode": "compare" if len(prepared_candidates) > 1 else "single",
        "scene": scene_payload,
        "candidates": [
            {
                "candidate_id": candidate["candidate_id"],
                "label": candidate["label"],
                "source_kind": candidate["source_kind"],
                "source_path": candidate["source_path"],
                "frame_refs": [
                    {
                        "candidate_id": frame["candidate_id"],
                        "frame_role": frame["frame_role"],
                        "path": frame["path"],
                        "timestamp_seconds": frame["timestamp_seconds"],
                    }
                    for frame in candidate["frame_refs"]
                ],
            }
            for candidate in prepared_candidates
        ],
        "attachments": attachments,
        "prompt": _build_scene_review_prompt(
            scene=scene_payload,
            prepared_candidates=prepared_candidates,
            trigger=str(trigger or "").strip() or "scene_review",
        ),
    }


def _normalize_string_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if value is None:
        return []
    normalized = str(value).strip()
    return [normalized] if normalized else []


def normalize_scene_judge_response(
    response: Any,
    *,
    candidate_ids: list[str],
) -> dict[str, Any]:
    """Normalize a provider response into stable judge-verdict fields."""
    raw = json.loads(response) if isinstance(response, str) else response
    if not isinstance(raw, dict):
        raise ValueError("Scene judge response must be a JSON object.")

    winner = str(
        raw.get("winner")
        or raw.get("selected_candidate")
        or raw.get("preferred_candidate")
        or ""
    ).strip()
    if winner not in candidate_ids:
        if len(candidate_ids) == 1:
            winner = candidate_ids[0]
        else:
            raise ValueError(f"Scene judge winner must be one of {candidate_ids}, got {winner!r}")

    reasons = _normalize_string_list(raw.get("reasons") or raw.get("winner_reasons") or raw.get("summary"))
    candidate_notes = {candidate_id: [] for candidate_id in candidate_ids}

    raw_candidate_notes = raw.get("candidate_notes") or raw.get("per_candidate_notes")
    if isinstance(raw_candidate_notes, dict):
        for candidate_id in candidate_ids:
            candidate_notes[candidate_id] = _normalize_string_list(raw_candidate_notes.get(candidate_id))
    elif isinstance(raw_candidate_notes, list):
        for item in raw_candidate_notes:
            if not isinstance(item, dict):
                continue
            candidate_id = str(item.get("candidate_id") or item.get("candidate") or "").strip()
            if candidate_id not in candidate_notes:
                continue
            candidate_notes[candidate_id] = _normalize_string_list(
                item.get("notes") or item.get("reasons") or item.get("note")
            )

    text_repairs: list[dict[str, str]] = []
    raw_text_repairs = raw.get("text_repairs")
    if isinstance(raw_text_repairs, list):
        for item in raw_text_repairs:
            if not isinstance(item, dict):
                continue
            candidate_id = str(item.get("candidate_id") or "").strip()
            wrong_text = str(item.get("wrong_text") or "").strip()
            correct_text = str(item.get("correct_text") or "").strip()
            reason = str(item.get("reason") or "").strip()
            if candidate_id not in candidate_ids or not wrong_text or not correct_text:
                continue
            text_repairs.append(
                {
                    "candidate_id": candidate_id,
                    "wrong_text": wrong_text,
                    "correct_text": correct_text,
                    "reason": reason,
                }
            )

    return {
        "winner": winner,
        "reasons": reasons,
        "candidate_notes": candidate_notes,
        "text_repairs": text_repairs,
    }


def _persisted_frame_refs(prepared_candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    for candidate in prepared_candidates:
        for frame in candidate["frame_refs"]:
            refs.append(
                {
                    "candidate_id": candidate["candidate_id"],
                    "frame_role": frame["frame_role"],
                    "path": frame["path"],
                    "timestamp_seconds": frame["timestamp_seconds"],
                }
            )
    refs.sort(key=lambda item: (item["candidate_id"], _FRAME_ROLE_ORDER[item["frame_role"]]))
    return refs


def build_scene_judge_verdict(
    *,
    provider: dict[str, Any],
    request: dict[str, Any],
    response: Any,
    prepared_candidates: list[dict[str, Any]],
) -> dict[str, Any]:
    """Build the persisted scene judge_verdict payload."""
    normalized = normalize_scene_judge_response(
        response,
        candidate_ids=[candidate["candidate_id"] for candidate in prepared_candidates],
    )
    return {
        "trigger": request["trigger"],
        "judge_provider": provider["provider"],
        "judge_model": provider["model"],
        "provider": provider["provider"],
        "model": provider["model"],
        "winner": normalized["winner"],
        "reasons": normalized["reasons"],
        "candidate_notes": normalized["candidate_notes"],
        "text_repairs": normalized["text_repairs"],
        "frame_refs": _persisted_frame_refs(prepared_candidates),
    }


def _persisted_candidate_outputs(
    prepared_candidates: list[dict[str, Any]],
    *,
    winner: str,
) -> dict[str, dict[str, Any]]:
    outputs: dict[str, dict[str, Any]] = {}
    for candidate in prepared_candidates:
        candidate_id = str(candidate["candidate_id"])
        outputs[candidate_id] = {
            "candidate_id": candidate_id,
            "label": str(candidate["label"]),
            "candidate_type": str(candidate.get("candidate_type") or "").strip() or None,
            "candidate_spec": candidate.get("candidate_spec"),
            "source_kind": str(candidate["source_kind"]),
            "source_path": str(candidate["source_path"]),
            "review_status": "winner" if candidate_id == winner else "rejected",
            "frame_refs": [
                {
                    "frame_role": frame["frame_role"],
                    "path": frame["path"],
                    "timestamp_seconds": frame["timestamp_seconds"],
                }
                for frame in candidate["frame_refs"]
            ],
        }
    return outputs


def _scene_review_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["winner", "reasons", "candidate_notes", "text_repairs"],
        "properties": {
            "winner": {"type": "string"},
            "reasons": {"type": "array", "items": {"type": "string"}},
            "candidate_notes": {
                "type": "object",
                "additionalProperties": {
                    "type": "array",
                    "items": {"type": "string"},
                },
            },
            "text_repairs": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["candidate_id", "wrong_text", "correct_text", "reason"],
                    "properties": {
                        "candidate_id": {"type": "string"},
                        "wrong_text": {"type": "string"},
                        "correct_text": {"type": "string"},
                        "reason": {"type": "string"},
                    },
                },
            },
        },
    }


def _parse_scene_judge_json_output(raw_output: str) -> dict[str, Any]:
    text = str(raw_output or "").strip()
    if not text:
        raise RuntimeError("Codex scene judge returned an empty last message.")

    def _parse_candidate(candidate_text: str) -> dict[str, Any] | None:
        try:
            payload = json.loads(candidate_text)
        except json.JSONDecodeError:
            return None
        return payload if isinstance(payload, dict) else None

    parsed = _parse_candidate(text)
    if parsed is not None:
        return parsed

    fenced_blocks = re.findall(r"```(?:json)?\s*([\s\S]*?)```", text, flags=re.IGNORECASE)
    for block in fenced_blocks:
        parsed = _parse_candidate(block.strip())
        if parsed is not None:
            return parsed

    decoder = json.JSONDecoder()
    required_keys = set(_scene_review_schema()["required"])
    best_match: dict[str, Any] | None = None
    best_score = -1

    for match in re.finditer(r"\{", text):
        try:
            candidate, _ = decoder.raw_decode(text[match.start():])
        except json.JSONDecodeError:
            continue
        if not isinstance(candidate, dict):
            continue
        score = sum(1 for key in required_keys if key in candidate)
        if score > best_score:
            best_match = candidate
            best_score = score
        if score == len(required_keys):
            return candidate

    if best_match is not None:
        return best_match

    raise RuntimeError(f"Codex scene judge returned invalid JSON: {text[:500]}")


def _run_codex_scene_judge(provider: dict[str, Any], request: dict[str, Any]) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="cathode-scene-review-") as tmp_dir:
        tmp_root = Path(tmp_dir)
        output_path = tmp_root / "scene_review_output.json"
        codex_binary = str(provider.get("binary_path") or "codex").strip() or "codex"

        command = [
            codex_binary,
            "exec",
            "--dangerously-bypass-approvals-and-sandbox",
            "--skip-git-repo-check",
            "--color",
            "never",
            "-C",
            str(REPO_ROOT),
            "-o",
            str(output_path),
        ]
        model = str(provider.get("model") or "").strip()
        if model and model != "local-default":
            command.extend(["-m", model])
        for attachment in request["attachments"]:
            command.extend(["-i", str(attachment["absolute_path"])])

        completed = subprocess.run(
            command,
            input=f"{request['prompt']}\n\nReturn a single valid JSON object only. Do not add commentary.",
            text=True,
            capture_output=True,
            check=False,
        )
        if completed.returncode != 0:
            message = completed.stderr.strip() or completed.stdout.strip() or "Codex scene judge failed."
            raise RuntimeError(message)
        if not output_path.exists():
            raise RuntimeError("Codex scene judge did not write a structured response.")
        raw_output = output_path.read_text(encoding="utf-8")
        return _parse_scene_judge_json_output(raw_output)


def _run_openai_scene_judge(provider: dict[str, Any], request: dict[str, Any]) -> dict[str, Any]:
    import openai

    client = openai.OpenAI()
    content: list[dict[str, Any]] = [{"type": "input_text", "text": request["prompt"]}]
    for attachment in request["attachments"]:
        content.append(
            {
                "type": "input_text",
                "text": (
                    f"Candidate {attachment['candidate_id']} ({attachment['candidate_label']}) "
                    f"- {attachment['frame_role']} @ {attachment['timestamp_seconds']:.3f}s"
                ),
            }
        )
        content.append(
            {
                "type": "input_image",
                "image_url": _data_url_for_image(attachment["absolute_path"]),
            }
        )

    kwargs: dict[str, Any] = {
        "model": provider["model"],
        "input": [{"role": "user", "content": content}],
        "text": {"format": {"type": "json_object"}},
    }
    reasoning_effort = str(provider.get("reasoning_effort") or "").strip().lower()
    if reasoning_effort:
        kwargs["reasoning"] = {"effort": reasoning_effort}
    response = client.responses.create(**kwargs)
    return json.loads(response.output_text)


def run_scene_judge(provider: dict[str, Any], request: dict[str, Any]) -> Any:
    """Run a scene judge with a built-in provider implementation."""
    provider_name = str(provider.get("provider") or "").strip().lower()
    if provider_name == "codex":
        return _run_codex_scene_judge(provider, request)
    if provider_name == "openai_api":
        return _run_openai_scene_judge(provider, request)
    raise NotImplementedError(provider.get("reason") or f"No built-in runner for {provider_name}")


def review_project_scenes(
    project_dir: str | Path,
    *,
    trigger: str,
    scene_candidates: dict[str, list[dict[str, Any]]] | None = None,
    scene_uids: list[str] | None = None,
    preferred_provider: str | None = None,
    judge_runner: SceneJudgeRunner | None = None,
    review_root: str | Path | None = None,
) -> dict[str, Any]:
    """Review every scene in a project deck and persist per-scene judge_verdict metadata."""
    project_dir = Path(project_dir).expanduser().resolve()
    plan = load_plan(project_dir)
    if not plan:
        raise ValueError(f"Could not load plan.json for project: {project_dir}")

    scenes = plan.get("scenes") if isinstance(plan.get("scenes"), list) else []
    if isinstance(scene_uids, list) and scene_uids:
        allowed = {str(uid).strip() for uid in scene_uids if str(uid).strip()}
        scenes = [scene for scene in scenes if str(scene.get("uid") or "").strip() in allowed]
    if not scenes:
        raise ValueError("Scene review requires at least one scene.")

    provider = choose_scene_judge_provider(
        preferred_provider,
        allow_external_runner=judge_runner is not None,
    )
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = (
        Path(review_root).expanduser().resolve()
        if review_root
        else project_dir / ".cathode" / "scene_review" / run_id
    )
    frames_root = run_dir / "frames"
    prepared_by_uid: dict[str, list[dict[str, Any]]] = {}

    for scene in scenes:
        scene_uid = str(scene.get("uid") or "").strip()
        candidate_overrides = None
        if isinstance(scene_candidates, dict):
            candidate_overrides = scene_candidates.get(scene_uid)
        if candidate_overrides is None:
            candidate_overrides = auto_scene_review_candidates(
                project_dir,
                plan,
                scene,
                review_root=run_dir,
            )
        prepared_by_uid[scene_uid] = prepare_scene_review_candidates(
            project_dir,
            scene,
            candidates=candidate_overrides,
            review_root=frames_root,
        )

    scene_results: list[dict[str, Any]] = []
    for scene in scenes:
        scene_uid = str(scene.get("uid") or "").strip()
        prepared_candidates = prepared_by_uid[scene_uid]
        if not prepared_candidates:
            continue  # no visual source to review (e.g. native_remotion not yet rendered)
        request = build_scene_review_request(
            scene,
            prepared_candidates=prepared_candidates,
            trigger=trigger,
        )
        scene_dir = run_dir / "scenes" / _slugify_token(scene_uid, fallback="scene")
        scene_dir.mkdir(parents=True, exist_ok=True)
        (scene_dir / "request.json").write_text(json.dumps(request, indent=2), encoding="utf-8")

        raw_response = judge_runner(provider, request) if judge_runner is not None else run_scene_judge(provider, request)
        if isinstance(raw_response, str):
            try:
                raw_payload: Any = json.loads(raw_response)
            except json.JSONDecodeError:
                raw_payload = {"raw": raw_response}
        else:
            raw_payload = raw_response
        (scene_dir / "response.json").write_text(json.dumps(raw_payload, indent=2), encoding="utf-8")

        verdict = build_scene_judge_verdict(
            provider=provider,
            request=request,
            response=raw_response,
            prepared_candidates=prepared_candidates,
        )
        scene["candidate_outputs"] = _persisted_candidate_outputs(
            prepared_candidates,
            winner=verdict["winner"],
        )
        scene["judge_verdict"] = verdict
        scene_results.append(
            {
                "scene_uid": scene_uid,
                "winner": verdict["winner"],
                "frame_ref_count": len(verdict["frame_refs"]),
            }
        )

    save_plan(project_dir, plan)
    return {
        "provider": provider["provider"],
        "model": provider["model"],
        "scene_count": len(scene_results),
        "review_dir": str(run_dir),
        "scenes": scene_results,
    }
