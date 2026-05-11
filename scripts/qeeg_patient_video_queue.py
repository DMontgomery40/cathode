#!/usr/bin/env python3.10
"""Sequential qEEG patient-video queue for Cathode.

This is an operator script for urgent qEEG portal video backfills. It creates
or refreshes Cathode projects from qEEG handoff payloads, generates GPT-image-2
still assets plus narration, and renders final MP4s one patient at a time.
"""

from __future__ import annotations

import argparse
import fcntl
import json
import os
import shutil
import subprocess
import sys
import time
import traceback
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import core.pipeline_service as pipeline_service
from core.pipeline_service import create_project_from_brief_service, process_existing_project_service
from core.project_store import load_plan, save_plan
from core.runtime import PROJECTS_DIR, codex_image_generation_available, load_repo_env

DEFAULT_PATIENTS = [
    "12-20-1975-0",
    "12-02-1985-0",
    "10-31-2008-0",
    "08-10-1989-0",
    "02-28-1978-0",
]

IMAGE_PROFILE = {
    "provider": "codex",
    "generation_model": "gpt-image-2",
    "edit_model": "gpt-image-2",
    "dashscope_edit_n": 1,
    "dashscope_edit_seed": "",
    "dashscope_edit_negative_prompt": "",
    "dashscope_edit_prompt_extend": True,
}

VIDEO_PROFILE = {
    "provider": "manual",
    "generation_model": "",
    "model_selection_mode": "automatic",
    "quality_mode": "standard",
    "generate_audio": True,
}

TTS_PROFILE = {
    "provider": "elevenlabs",
    "voice": "Bella",
    "speed": 1.1,
    "model_id": "eleven_multilingual_v2",
    "text_normalization": "auto",
    "stability": 0.38,
    "similarity_boost": 0.8,
    "style": 0.65,
    "use_speaker_boost": True,
    "exaggeration": 0.6,
}

RENDER_PROFILE = {
    "version": "v1",
    "aspect_ratio": "16:9",
    "width": 1664,
    "height": 928,
    "fps": 24,
    "scene_types": ["image"],
    "render_strategy": "force_ffmpeg",
    "render_backend": "ffmpeg",
    "render_backend_reason": "Static GPT-image-2 still-image qEEG explainer queue; no Remotion, overlays, or generated video clips.",
    "text_render_mode": "visual_authored",
    "auto_compress_oversized_video": True,
    "compression_min_size_mb": 150.0,
    "compression_max_average_bitrate_mbps": 3.2,
    "compression_target_video_kbps": 2500,
    "compression_target_audio_kbps": 128,
}

QEEG_REPO = Path(os.getenv("QEEG_ANALYSIS_REPO") or (REPO_ROOT.parent / "qEEG-analysis")).expanduser()


def utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    tmp.replace(path)


def require_locked_image_generation_lane() -> None:
    if not codex_image_generation_available():
        raise RuntimeError(
            "qEEG video queue is locked to Codex Exec + gpt-image-2 stills, but that lane is unavailable. "
            "Set OPENAI_API_KEY and ensure the `codex` CLI is on PATH before running the queue."
        )


def qeeg_portal_patient_dir(patient: str) -> Path:
    configured = (os.getenv("QEEG_PORTAL_PATIENTS_DIR") or "").strip()
    root = Path(configured).expanduser() if configured else QEEG_REPO / "data" / "portal_patients"
    return root / patient


def sync_video_to_qeeg_portal(patient: str, video_path: str | None) -> dict[str, Any]:
    if not video_path:
        return {"status": "skipped", "reason": "render did not report a video_path"}
    source = Path(video_path).expanduser()
    if not source.exists() or source.stat().st_size <= 0:
        return {"status": "skipped", "reason": f"rendered video missing or empty: {source}"}

    patient_dir = qeeg_portal_patient_dir(patient)
    patient_dir.mkdir(parents=True, exist_ok=True)
    target = patient_dir / f"{patient}.mp4"
    shutil.copy2(source, target)
    meta_path = patient_dir / f"{patient}__cathode_video.json"
    write_json_atomic(
        meta_path,
        {
            "patient_label": patient,
            "source_video_path": str(source),
            "portal_video_path": str(target),
            "synced_at": utc_now(),
            "generator": "cathode/scripts/qeeg_patient_video_queue.py",
            "image_model": IMAGE_PROFILE["generation_model"],
            "storyboard_provider": "claude_print",
            "target_minutes": 6.5,
        },
    )
    return {"status": "copied", "portal_video_path": str(target), "meta_path": str(meta_path)}


def sync_patient_to_thrylen(patient: str) -> dict[str, Any]:
    if not (QEEG_REPO / "backend" / "portal_sync.py").exists():
        return {"status": "skipped", "reason": f"qEEG repo not found at {QEEG_REPO}"}
    qeeg_python = Path(
        os.getenv("QEEG_PYTHON")
        or (str(QEEG_REPO / ".venv" / "bin" / "python") if (QEEG_REPO / ".venv" / "bin" / "python").exists() else sys.executable)
    ).expanduser()
    completed = subprocess.run(
        [
            str(qeeg_python),
            "-m",
            "backend.portal_sync",
            "--patient-label",
            patient,
        ],
        cwd=str(QEEG_REPO),
        capture_output=True,
        text=True,
        check=False,
    )
    return {
        "status": "complete" if completed.returncode == 0 else "failed",
        "returncode": completed.returncode,
        "stdout": completed.stdout[-2000:],
        "stderr": completed.stderr[-2000:],
    }


def register_video_as_qeeg_patient_file(patient: str, video_path: str | None) -> dict[str, Any]:
    if not video_path:
        return {"status": "skipped", "reason": "render did not report a video_path"}
    register_script = QEEG_REPO / "scripts" / "register_patient_file.py"
    if not register_script.exists():
        return {"status": "skipped", "reason": f"register script not found at {register_script}"}
    qeeg_python = Path(
        os.getenv("QEEG_PYTHON")
        or (str(QEEG_REPO / ".venv" / "bin" / "python") if (QEEG_REPO / ".venv" / "bin" / "python").exists() else sys.executable)
    ).expanduser()
    completed = subprocess.run(
        [
            str(qeeg_python),
            str(register_script),
            "--patient-label",
            patient,
            "--src",
            str(Path(video_path).expanduser()),
            "--filename",
            f"{patient}.mp4",
            "--mime-type",
            "video/mp4",
        ],
        cwd=str(QEEG_REPO),
        capture_output=True,
        text=True,
        check=False,
    )
    return {
        "status": "complete" if completed.returncode == 0 else "failed",
        "returncode": completed.returncode,
        "stdout": completed.stdout[-2000:],
        "stderr": completed.stderr[-2000:],
    }


def build_brief(patient: str, project_dir: Path, *, target_minutes: float) -> dict[str, Any]:
    payload_path = project_dir / "qeeg_handoff_payload.json"
    if not payload_path.exists():
        raise FileNotFoundError(f"Missing handoff payload: {payload_path}")
    payload = read_json(payload_path)
    source_paths = [Path(p) for p in payload.get("source_paths") or []]
    source_parts: list[str] = []
    for source_path in source_paths:
        if source_path.exists():
            source_parts.append(source_path.read_text(encoding="utf-8", errors="replace"))
    source_material = "\n\n---\n\n".join(source_parts).strip()
    if not source_material:
        raise ValueError(f"Missing qEEG source material for {patient}")

    return {
        "project_name": patient,
        "source_mode": "source_text",
        "video_goal": "Create a patient-friendly qEEG explainer video from the completed qEEG Council analysis.",
        "audience": payload.get("audience") or "the patient and their family",
        "source_material": source_material,
        "target_length_minutes": target_minutes,
        "tone": "warm, clear, reassuring, clinically grounded, and not condescending",
        "visual_style": (
            "cinematic patient-friendly brain-health explainer with rich GPT-image-2 illustrations, "
            "visual-authored text only when it belongs inside the image, varied scenes, and no generic chart wallpaper"
        ),
        "must_include": (
            "Use the qEEG Council findings as source of truth. Preserve important patient-data numbers, "
            "explain them simply, include practical caveats, and keep a true 6.5-minute arc with breathing room."
        ),
        "must_avoid": (
            "Do not invent diagnoses, overstate causality, bury the patient in raw tables, use generated "
            "video clips, use Kling, use Remotion/native overlays, use Streamlit-era rendering, or repeat the same visual background across scenes."
        ),
        "ending_cta": "Continue LUMIT treatment.",
        "paid_media_budget_usd": "",
        "composition_mode": "classic",
        "visual_source_strategy": "images_only",
        "video_scene_style": "auto",
        "text_render_mode": "visual_authored",
        "available_footage": "",
        "footage_manifest": [],
        "style_reference_summary": "",
        "style_reference_paths": [],
        "raw_brief": (
            "Normal qEEG patient explainer. Exactly 6.5 minutes target. GPT-image-2 images only; no generated "
            "video clips, no Remotion, no deterministic overlays. Assemble static image scenes with narration via ffmpeg. "
            "Make it humane, visually rich, accurate, and useful for a patient and family."
        ),
    }


def project_has_render(project_dir: Path, patient: str) -> bool:
    video_path = project_dir / f"{patient}.mp4"
    if video_path.exists() and video_path.stat().st_size > 0:
        return True
    plan = load_plan(project_dir)
    if not plan:
        return False
    candidate = str((plan.get("meta") or {}).get("video_path") or "")
    return bool(candidate and Path(candidate).exists() and Path(candidate).stat().st_size > 0)


def plan_needs_storyboard_refresh(project_dir: Path, *, minimum_target_minutes: float) -> bool:
    plan = load_plan(project_dir)
    if not plan:
        return True
    brief = (plan.get("meta") or {}).get("brief") or {}
    try:
        target_minutes = float(brief.get("target_length_minutes") or 0)
    except (TypeError, ValueError):
        target_minutes = 0
    if target_minutes < minimum_target_minutes:
        return True
    image_profile = (plan.get("meta") or {}).get("image_profile") or {}
    if str(image_profile.get("provider") or "") != IMAGE_PROFILE["provider"]:
        return True
    if str(image_profile.get("generation_model") or "") != IMAGE_PROFILE["generation_model"]:
        return True
    if str((plan.get("meta") or {}).get("creative_llm_provider") or "") != "claude_print":
        return True
    video_profile = (plan.get("meta") or {}).get("video_profile") or {}
    if str(video_profile.get("provider") or "") != "manual":
        return True
    return False


def force_static_image_plan(plan: dict[str, Any]) -> dict[str, Any]:
    """Clamp generated storyboards to still-image ffmpeg scenes for the qEEG queue."""
    for scene in plan.get("scenes") or []:
        if not isinstance(scene, dict):
            continue
        scene["scene_type"] = "image"
        scene["video_path"] = None
        scene["motion"] = None
        scene["composition"] = {
            "family": "",
            "mode": "none",
            "props": {},
            "transition_after": None,
            "data": {},
            "rationale": "qEEG queue is locked to GPT-image-2 stills plus ffmpeg assembly.",
        }
        manifestation = scene.get("manifestation_plan")
        if not isinstance(manifestation, dict):
            manifestation = {}
        manifestation["primary_path"] = "authored_image"
        manifestation["fallback_path"] = "authored_image"
        manifestation["native_family_hint"] = ""
        manifestation["native_build_prompt"] = ""
        scene["manifestation_plan"] = manifestation
    meta = plan.setdefault("meta", {})
    render_profile = meta.setdefault("render_profile", {})
    render_profile.update(RENDER_PROFILE)
    meta["image_profile"] = IMAGE_PROFILE
    meta["video_profile"] = VIDEO_PROFILE
    meta["creative_llm_provider"] = "claude_print"
    return plan


def run_queue(args: argparse.Namespace) -> int:
    load_repo_env(override=True)
    require_locked_image_generation_lane()
    if args.skip_scene_review:
        def _skip_review(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
            return {
                "status": "skipped",
                "reason": "Skipped by qEEG unattended video queue; run qEEG QC/publish before portal release.",
                "results": [],
                "summary": {"total": 0, "passed": 0, "failed": 0},
            }

        pipeline_service.review_project_scenes = _skip_review

    patients = args.patients or DEFAULT_PATIENTS
    status_path = Path(args.status_path).expanduser().resolve()
    status: dict[str, Any] = {
        "started_at": utc_now(),
        "patients": patients,
        "target_minutes": args.target_minutes,
        "items": {},
    }
    write_json_atomic(status_path, status)

    failures = 0
    for index, patient in enumerate(patients, start=1):
        project_dir = PROJECTS_DIR / patient
        item: dict[str, Any] = {
            "patient": patient,
            "position": index,
            "project_dir": str(project_dir),
            "started_at": utc_now(),
            "status": "started",
        }
        status["items"][patient] = item
        write_json_atomic(status_path, status)
        print(f"\n=== [{index}/{len(patients)}] {patient}: start ===", flush=True)
        try:
            if args.skip_completed and project_has_render(project_dir, patient):
                item["status"] = "skipped_existing_render"
                item["video_path"] = str(project_dir / f"{patient}.mp4")
                item["completed_at"] = utc_now()
                write_json_atomic(status_path, status)
                print(f"[{patient}] skipped existing render", flush=True)
                continue

            if args.rebuild_storyboard or plan_needs_storyboard_refresh(
                project_dir,
                minimum_target_minutes=args.minimum_existing_target_minutes,
            ):
                brief = build_brief(patient, project_dir, target_minutes=args.target_minutes)
                project_dir, plan = create_project_from_brief_service(
                    project_name=patient,
                    project_dir=project_dir,
                    overwrite=True,
                    provider="claude_print",
                    brief=brief,
                    image_profile=IMAGE_PROFILE,
                    video_profile=VIDEO_PROFILE,
                    tts_profile=TTS_PROFILE,
                    render_profile=RENDER_PROFILE,
                )
                plan = save_plan(project_dir, force_static_image_plan(plan))
                item["storyboard_saved_at"] = utc_now()
                item["scene_count"] = len(plan.get("scenes") or [])
                write_json_atomic(status_path, status)
                print(f"[{patient}] storyboard saved: {item['scene_count']} scenes", flush=True)

            result = process_existing_project_service(
                project_dir,
                rebuild_storyboard=False,
                generate_images=True,
                generate_videos=False,
                generate_audio=True,
                regenerate_videos=False,
                regenerate_audio=False,
                assemble_final=True,
                fps=24,
                output_filename=f"{patient}.mp4",
            )
            item["result"] = result
            render = result.get("render") or {}
            item["video_path"] = render.get("video_path")
            item["status"] = "complete" if render.get("status") == "succeeded" else "needs_attention"
            if item["status"] == "complete":
                item["portal_video"] = sync_video_to_qeeg_portal(patient, item.get("video_path"))
                item["patient_file"] = register_video_as_qeeg_patient_file(patient, item.get("video_path"))
                item["thrylen_sync"] = sync_patient_to_thrylen(patient)
            item["completed_at"] = utc_now()
            if item["status"] != "complete":
                failures += 1
            write_json_atomic(status_path, status)
            print(f"[{patient}] render={json.dumps(render, default=str)[:2000]}", flush=True)
            print(f"=== [{index}/{len(patients)}] {patient}: {item['status']} ===", flush=True)
        except Exception as exc:
            failures += 1
            item["status"] = "failed"
            item["error"] = str(exc)
            item["traceback"] = traceback.format_exc()
            item["failed_at"] = utc_now()
            write_json_atomic(status_path, status)
            print(f"[{patient}] FAILED: {exc}", flush=True)
            traceback.print_exc()
            if not args.continue_on_error:
                break

    status["finished_at"] = utc_now()
    write_json_atomic(status_path, status)
    print(f"\nQueue status written to {status_path}", flush=True)
    return 1 if failures else 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run sequential qEEG patient video backfills through Cathode.")
    parser.add_argument("--patients", nargs="*", default=None, help="Patient labels to process in order.")
    parser.add_argument("--target-minutes", type=float, default=6.5)
    parser.add_argument("--status-path", default=str(PROJECTS_DIR / "qeeg_video_queue_2026-04-17.json"))
    parser.add_argument("--lock-path", default=str(PROJECTS_DIR / ".qeeg_video_queue.lock"))
    parser.add_argument("--rebuild-storyboard", action="store_true")
    parser.add_argument("--skip-completed", action="store_true")
    parser.add_argument("--continue-on-error", action="store_true")
    parser.add_argument("--minimum-existing-target-minutes", type=float, default=5.5)
    parser.add_argument(
        "--skip-scene-review",
        action="store_true",
        help="Skip Cathode's local per-scene agent review during unattended generation.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    lock_path = Path(args.lock_path).expanduser().resolve()
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("w", encoding="utf-8") as lock_file:
        try:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print(f"Another qEEG video queue is already running: {lock_path}", file=sys.stderr)
            return 2
        lock_file.write(f"pid={os.getpid()} started_at={utc_now()}\n")
        lock_file.flush()
        return run_queue(args)


if __name__ == "__main__":
    raise SystemExit(main())
