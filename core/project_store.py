"""Project storage and local artifact helpers."""

from __future__ import annotations

import copy
import json
import shutil
from pathlib import Path
from typing import Any

from .costs import refresh_plan_costs
from .project_schema import backfill_plan, sanitize_project_name
from .runtime import PROJECTS_DIR
from .video_assembly import media_has_audio_stream


def get_project_path(project_name: str, overwrite: bool = False) -> Path:
    """Return a project path, incrementing the folder name unless overwrite is requested."""
    clean_name = sanitize_project_name(project_name)
    base_path = PROJECTS_DIR / clean_name
    if overwrite or not base_path.exists():
        return base_path

    counter = 2
    while True:
        candidate = PROJECTS_DIR / f"{clean_name}__{counter:02d}"
        if not candidate.exists():
            return candidate
        counter += 1


def ensure_project_dir(project_name: str, overwrite: bool = False) -> Path:
    """Create and return the project directory."""
    project_dir = get_project_path(project_name, overwrite=overwrite)
    if overwrite and project_dir.exists():
        shutil.rmtree(project_dir)
    project_dir.mkdir(parents=True, exist_ok=True)
    return project_dir


def load_plan(project_dir: Path) -> dict[str, Any] | None:
    """Load and normalize a project's plan.json."""
    plan_path = Path(project_dir) / "plan.json"
    if not plan_path.exists():
        return None

    raw = json.loads(plan_path.read_text())
    plan = backfill_plan(raw, base_dir=project_dir)
    plan = refresh_plan_costs(plan)
    if plan != raw:
        plan_path.write_text(json.dumps(plan, indent=2))
    return plan


def save_plan(project_dir: Path, plan: dict[str, Any]) -> dict[str, Any]:
    """Normalize and persist a project's plan.json."""
    project_dir = Path(project_dir)
    project_dir.mkdir(parents=True, exist_ok=True)
    normalized = backfill_plan(plan, base_dir=project_dir)
    normalized = refresh_plan_costs(normalized)
    (project_dir / "plan.json").write_text(json.dumps(normalized, indent=2))
    return normalized


def _resolve_asset_path(project_dir: Path, raw_path: Any) -> Path | None:
    value = str(raw_path or "").strip()
    if not value:
        return None

    normalized = value.replace("\\", "/").lstrip("/")
    marker = f"projects/{project_dir.name}/"
    index = normalized.rfind(marker)
    if index >= 0:
        suffix = normalized[index + len(marker) :].lstrip("/")
        if not suffix:
            return None
        return (project_dir / suffix).resolve()

    path = Path(value).expanduser()
    if path.is_absolute():
        return path.resolve()

    return (project_dir / normalized).resolve()


def asset_path_exists(project_dir: Path, raw_path: Any) -> bool:
    """Return whether a persisted asset path currently resolves to a readable file."""
    resolved = _resolve_asset_path(Path(project_dir), raw_path)
    return bool(resolved and resolved.exists() and resolved.is_file())


def annotate_plan_asset_existence(project_dir: Path, plan: dict[str, Any]) -> dict[str, Any]:
    """Attach non-persisted asset existence hints used by the API/UI."""
    annotated = copy.deepcopy(plan if isinstance(plan, dict) else {})
    project_dir = Path(project_dir)

    meta = annotated.get("meta")
    if not isinstance(meta, dict):
        meta = {}
        annotated["meta"] = meta
    meta["video_exists"] = asset_path_exists(project_dir, meta.get("video_path"))

    scenes = annotated.get("scenes")
    if not isinstance(scenes, list):
        annotated["scenes"] = []
        return annotated

    for scene in scenes:
        if not isinstance(scene, dict):
            continue
        scene["image_exists"] = asset_path_exists(project_dir, scene.get("image_path"))
        scene["video_exists"] = asset_path_exists(project_dir, scene.get("video_path"))
        scene["video_audio_exists"] = bool(
            scene["video_exists"] and media_has_audio_stream(_resolve_asset_path(project_dir, scene.get("video_path")) or "")
        )
        scene["audio_exists"] = asset_path_exists(project_dir, scene.get("audio_path"))
        scene["preview_exists"] = asset_path_exists(project_dir, scene.get("preview_path"))
        composition = scene.get("composition")
        if isinstance(composition, dict):
            composition["render_exists"] = asset_path_exists(project_dir, composition.get("render_path"))
            composition["preview_exists"] = asset_path_exists(project_dir, composition.get("preview_path"))
        motion = scene.get("motion")
        if isinstance(motion, dict):
            motion["render_exists"] = asset_path_exists(project_dir, motion.get("render_path"))
            motion["preview_exists"] = asset_path_exists(project_dir, motion.get("preview_path"))

    return annotated


def list_projects() -> list[str]:
    """List all projects that currently contain a plan.json."""
    names: list[str] = []
    for path in sorted(PROJECTS_DIR.iterdir()):
        if path.is_dir() and (path / "plan.json").exists():
            names.append(path.name)
    return names


def copy_external_files(
    project_dir: Path,
    source_paths: list[str | Path],
    *,
    subdir: str,
    stem_prefix: str,
) -> list[Path]:
    """Copy external files into the project under a stable local naming scheme."""
    output_dir = Path(project_dir) / subdir
    output_dir.mkdir(parents=True, exist_ok=True)

    copied: list[Path] = []
    for index, source in enumerate(source_paths, start=1):
        src = Path(source)
        if not src.exists() or not src.is_file():
            continue
        suffix = src.suffix.lower() or ".bin"
        dest = output_dir / f"{stem_prefix}_{index:02d}{suffix}"
        if src.resolve() != dest.resolve():
            dest.write_bytes(src.read_bytes())
        copied.append(dest)
    return copied


def collect_project_artifacts(project_dir: Path) -> dict[str, Any]:
    """Return a compact inventory of files generated for a project."""
    root = Path(project_dir)

    def _files(name: str) -> list[str]:
        folder = root / name
        if not folder.exists():
            return []
        return sorted(str(path) for path in folder.iterdir() if path.is_file())

    mp4_files = sorted(str(path) for path in root.glob("*.mp4") if path.is_file())
    jobs_dir = root / ".cathode" / "jobs"
    job_files = sorted(str(path) for path in jobs_dir.glob("*.json")) if jobs_dir.exists() else []
    return {
        "project_dir": str(root),
        "plan_path": str(root / "plan.json"),
        "images": _files("images"),
        "clips": _files("clips"),
        "audio": _files("audio"),
        "previews": _files("previews"),
        "style_refs": _files("style_refs"),
        "videos": mp4_files,
        "jobs": job_files,
    }
