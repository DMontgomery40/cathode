#!/usr/bin/env python3
"""
Batch rebuild Cathode projects from metadata and regenerate assets.

Usage:
    python3.10 batch_regenerate.py
    python3.10 batch_regenerate.py --projects demo_one,demo_two
    python3.10 batch_regenerate.py --dry-run
"""

from __future__ import annotations

import argparse
from pathlib import Path

from core.pipeline_service import process_existing_project_service
from core.project_store import list_projects, load_plan
from core.runtime import PROJECTS_DIR, load_repo_env

load_repo_env(override=True)


def regenerate_project(project_dir: Path, dry_run: bool = False) -> bool:
    """Rebuild one project from metadata, regenerate assets, and render a final video."""
    project_name = project_dir.name
    print(f"\n{'='*60}")
    print(f"Processing: {project_name}")
    print(f"{'='*60}")

    plan = load_plan(project_dir)
    if not plan:
        print("ERROR: Could not load plan.json")
        return False

    if dry_run:
        brief = plan.get("meta", {}).get("brief", {})
        source_mode = brief.get("source_mode") if isinstance(brief, dict) else "legacy"
        provider = plan.get("meta", {}).get("llm_provider")
        print(f"  [DRY RUN] source_mode={source_mode} provider={provider}")
        return True

    try:
        result = process_existing_project_service(
            project_dir,
            rebuild_storyboard=True,
            generate_images=True,
            generate_audio=True,
            regenerate_audio=False,
            assemble_final=True,
            output_filename=f"{project_name}.mp4",
        )
    except Exception as exc:
        print(f"ERROR: Processing failed: {exc}")
        return False

    asset_result = result.get("assets") or {}
    render_result = result.get("render") or {}

    print("\n[assets]")
    print(
        "  images: "
        f"generated={asset_result.get('images_generated', 0)} "
        f"skipped={asset_result.get('images_skipped', 0)} "
        f"failed={len(asset_result.get('image_failures', []))}"
    )
    print(
        "  clips: "
        f"generated={asset_result.get('videos_generated', 0)} "
        f"skipped={asset_result.get('videos_skipped', 0)} "
        f"failed={len(asset_result.get('video_failures', []))}"
    )
    print(
        "  audio: "
        f"generated={asset_result.get('audio_generated', 0)} "
        f"skipped={asset_result.get('audio_skipped', 0)} "
        f"failed={len(asset_result.get('audio_failures', []))}"
    )

    if render_result:
        print("\n[render]")
        print(f"  status={render_result.get('status')}")
        if render_result.get("video_path"):
            print(f"  video={render_result['video_path']}")
        if render_result.get("suggestion"):
            print(f"  note={render_result['suggestion']}")

    failed = bool(
        asset_result.get("image_failures")
        or asset_result.get("video_failures")
        or asset_result.get("audio_failures")
    )
    failed = failed or render_result.get("status") == "error"
    if render_result.get("status") == "partial_success":
        print(f"\nPARTIAL {project_name}")
        return True

    print(f"\nOK regenerated {project_name}")
    return not failed


def main() -> int:
    parser = argparse.ArgumentParser(description="Batch regenerate Cathode projects")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without doing it")
    parser.add_argument("--projects", type=str, help="Comma-separated list of project names to process")
    args = parser.parse_args()

    if args.projects:
        names = [name.strip() for name in args.projects.split(",") if name.strip()]
        projects = [PROJECTS_DIR / name for name in names if (PROJECTS_DIR / name / "plan.json").exists()]
        missing = [name for name in names if not (PROJECTS_DIR / name / "plan.json").exists()]
        if missing:
            print(f"WARNING: Skipping missing/invalid projects: {', '.join(missing)}")
    else:
        projects = [PROJECTS_DIR / name for name in list_projects()]

    if not projects:
        print("No projects with plan.json found.")
        return 1

    print(f"Found {len(projects)} project(s) to process")
    if args.dry_run:
        print("DRY RUN mode enabled")

    success_count = 0
    failed: list[str] = []
    for project_dir in projects:
        ok = regenerate_project(project_dir, dry_run=args.dry_run)
        if ok:
            success_count += 1
        else:
            failed.append(project_dir.name)

    print(f"\n{'='*60}")
    print("Summary")
    print(f"{'='*60}")
    print(f"Success: {success_count}/{len(projects)}")
    if failed:
        print(f"Failed: {len(failed)}")
        for name in failed:
            print(f"  - {name}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
