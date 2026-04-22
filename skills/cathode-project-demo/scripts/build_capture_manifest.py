#!/usr/bin/env python3
"""Build a live-demo capture manifest from a manually recorded desktop-use session."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import uuid
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a capture manifest from a desktop-use screen recording plus manually noted clip metadata."
    )
    parser.add_argument("--session-json", required=True, help="Prepared live-demo session manifest.")
    parser.add_argument("--raw-video-path", required=True, help="Recorded desktop or browser walkthrough video to bundle.")
    parser.add_argument(
        "--clips-json",
        required=True,
        help="JSON array or object with `clips`, including ids, labels, start/end times, screenshots, and optional focus boxes.",
    )
    parser.add_argument("--output-manifest", help="Optional output path. Defaults to the session capture manifest path.")
    parser.add_argument("--attempt-name", default="", help="Optional attempt label used in retained artifact names.")
    return parser.parse_args()


def _slugify(value: Any, fallback: str) -> str:
    text = str(value or "").strip().lower()
    text = "".join(ch if ch.isalnum() else "_" for ch in text)
    text = "_".join(part for part in text.split("_") if part)
    return text or fallback


def _load_clips(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict):
        clips = payload.get("clips")
    else:
        clips = payload
    if not isinstance(clips, list):
        raise SystemExit("clips-json must contain a JSON array or an object with a `clips` array.")
    return [item for item in clips if isinstance(item, dict)]


def _safe_float(value: Any, *, default: float | None = None) -> float | None:
    if value in (None, ""):
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _resolved_path(value: Any, *, base_dir: Path | None = None) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    path = Path(text).expanduser()
    if not path.is_absolute() and base_dir is not None:
        path = (base_dir / path).resolve()
    else:
        path = path.resolve()
    return str(path)


def _default_attempt_slug() -> str:
    return _slugify(f"desktop_capture_{uuid.uuid4().hex[:8]}", "desktop_capture")


def _bundle_artifact(
    source_path: str,
    *,
    dest_dir: Path,
    dest_stem: str,
    missing_error: str,
    fallback_suffix: str,
) -> str:
    if not source_path:
        return ""
    source = Path(source_path)
    if not source.exists() or not source.is_file():
        raise SystemExit(f"{missing_error}: {source}")
    dest = dest_dir / f"{dest_stem}{source.suffix or fallback_suffix}"
    if source.resolve() != dest.resolve():
        shutil.copy2(source, dest)
    return str(dest.resolve())


def _normalize_focus_box(value: Any) -> dict[str, int] | None:
    if not isinstance(value, dict):
        return None
    focus_box: dict[str, int] = {}
    for key in ("x", "y", "width", "height"):
        number = _safe_float(value.get(key))
        if number is None:
            return None
        focus_box[key] = int(number)
    return focus_box


def main() -> int:
    args = parse_args()
    session_path = Path(args.session_json).expanduser().resolve()
    session = json.loads(session_path.read_text(encoding="utf-8"))
    clips_json_path = Path(args.clips_json).expanduser().resolve()
    clips = _load_clips(clips_json_path)

    raw_video_source = Path(args.raw_video_path).expanduser().resolve()
    if not raw_video_source.exists():
        raise SystemExit(f"Raw capture video does not exist: {raw_video_source}")

    artifacts = session.get("artifacts") if isinstance(session.get("artifacts"), dict) else {}
    raw_dir = Path(str(artifacts.get("raw_dir") or raw_video_source.parent)).expanduser().resolve()
    screenshots_dir = Path(
        str(artifacts.get("screenshots_dir") or session_path.parent / "screenshots")
    ).expanduser().resolve()
    reports_dir = Path(str(artifacts.get("reports_dir") or raw_video_source.parent)).expanduser().resolve()
    raw_dir.mkdir(parents=True, exist_ok=True)
    screenshots_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    attempt_slug = _slugify(args.attempt_name, _default_attempt_slug()) if args.attempt_name else _default_attempt_slug()
    output_manifest_path = (
        Path(args.output_manifest).expanduser().resolve()
        if args.output_manifest
        else Path(str(artifacts.get("capture_manifest_path") or session_path.parent / "capture_manifest.json")).resolve()
    )
    raw_video_dest = raw_dir / f"{attempt_slug}{raw_video_source.suffix or '.mp4'}"
    if raw_video_source != raw_video_dest:
        shutil.copy2(raw_video_source, raw_video_dest)

    viewport = session.get("viewport") if isinstance(session.get("viewport"), dict) else {}
    step_manifest_path = reports_dir / f"{attempt_slug}_step_manifest.json"
    attempt_screenshots_dir = screenshots_dir / attempt_slug
    attempt_screenshots_dir.mkdir(parents=True, exist_ok=True)

    capture_driver = "desktop_use"
    step_entries: list[dict[str, Any]] = []
    clip_entries: list[dict[str, Any]] = []
    for index, clip in enumerate(clips, start=1):
        clip_id = _slugify(clip.get("id") or clip.get("label") or f"clip_{index:02d}", f"clip_{index:02d}")
        label = str(clip.get("label") or clip_id).strip() or clip_id
        start_seconds = _safe_float(clip.get("start_seconds"), default=0.0) or 0.0
        end_seconds = _safe_float(clip.get("end_seconds"))
        if end_seconds is not None and end_seconds < start_seconds:
            raise SystemExit(f"Clip `{clip_id}` has end_seconds before start_seconds.")

        screenshot_source_path = _resolved_path(
            clip.get("screenshot_path"),
            base_dir=clips_json_path.parent,
        )
        screenshot_path = _bundle_artifact(
            screenshot_source_path,
            dest_dir=attempt_screenshots_dir,
            dest_stem=clip_id,
            missing_error=f"Clip `{clip_id}` screenshot does not exist",
            fallback_suffix=".png",
        )
        focus_box = _normalize_focus_box(clip.get("focus_box"))
        text_excerpt = str(clip.get("text_excerpt") or "").strip()
        url = str(clip.get("url") or session.get("app_url") or session.get("expected_url") or "").strip()
        actions = clip.get("actions") if isinstance(clip.get("actions"), list) else []

        step_entry = {
            "id": str(clip.get("step_id") or clip_id),
            "label": str(clip.get("step_label") or label),
            "url": url,
            "start_seconds": start_seconds,
            "end_seconds": end_seconds if end_seconds is not None else start_seconds,
            "screenshot_path": screenshot_path,
            "focus_selector": str(clip.get("focus_selector") or "").strip(),
            "focus_box": focus_box,
            "text_excerpt": text_excerpt,
            "actions": actions,
            "capture_driver": capture_driver,
        }
        step_entries.append(step_entry)

        clip_entries.append(
            {
                **clip,
                "id": clip_id,
                "label": label,
                "notes": str(clip.get("notes") or "").strip(),
                "kind": str(clip.get("kind") or "video_clip").strip() or "video_clip",
                "review_status": str(clip.get("review_status") or "accept").strip() or "accept",
                "source_path": str(raw_video_dest),
                "start_seconds": start_seconds,
                "end_seconds": end_seconds,
                "focus_box": focus_box,
                "screenshot_path": screenshot_path,
                "url": url,
                "text_excerpt": text_excerpt,
                "viewport": viewport,
            }
        )

    step_manifest = {
        "session_id": session.get("session_id"),
        "attempt_name": attempt_slug,
        "preferred_theme": str(session.get("preferred_theme") or "dark"),
        "viewport": viewport,
        "capture_driver": capture_driver,
        "trace_path": "",
        "raw_video_path": str(raw_video_dest),
        "steps": step_entries,
    }
    step_manifest_path.write_text(json.dumps(step_manifest, indent=2), encoding="utf-8")

    capture_manifest = {
        "session_id": session.get("session_id"),
        "target_repo_path": session.get("target_repo_path"),
        "app_url": str(session.get("app_url") or session.get("expected_url") or ""),
        "preferred_theme": str(session.get("preferred_theme") or "dark"),
        "viewport": viewport,
        "capture_driver": capture_driver,
        "raw_video_path": str(raw_video_dest),
        "trace_path": "",
        "step_manifest_path": str(step_manifest_path),
        "processed_dir": str(artifacts.get("processed_dir") or output_manifest_path.parent / "processed"),
        "clips": clip_entries,
    }
    output_manifest_path.parent.mkdir(parents=True, exist_ok=True)
    output_manifest_path.write_text(json.dumps(capture_manifest, indent=2), encoding="utf-8")
    print(json.dumps(capture_manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
