#!/usr/bin/env python3
"""Trim, crop, and normalize raw capture clips into Cathode-ready footage."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


TARGET_WIDTH = 1664
TARGET_HEIGHT = 928
TARGET_FPS = 24


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Postprocess raw capture clips into Cathode-ready footage.")
    parser.add_argument("--capture-manifest", required=True, help="JSON file listing raw clips and optional focus boxes.")
    parser.add_argument("--output-manifest", help="Optional output path. Defaults beside the input manifest.")
    return parser.parse_args()


def _safe_float(value: Any, fallback: float | None = None) -> float | None:
    if value in (None, ""):
        return fallback
    try:
        return float(value)
    except (TypeError, ValueError):
        return fallback


def _fit_focus_box(
    focus_box: dict[str, Any] | None,
    *,
    viewport_width: int,
    viewport_height: int,
) -> tuple[int, int, int, int]:
    if not isinstance(focus_box, dict):
        return 0, 0, viewport_width, viewport_height

    x = int(_safe_float(focus_box.get("x"), 0) or 0)
    y = int(_safe_float(focus_box.get("y"), 0) or 0)
    width = max(1, int(_safe_float(focus_box.get("width"), viewport_width) or viewport_width))
    height = max(1, int(_safe_float(focus_box.get("height"), viewport_height) or viewport_height))

    desired_width = max(width + 120, int(viewport_width * 0.46))
    desired_height = int(round(desired_width * TARGET_HEIGHT / TARGET_WIDTH))
    if desired_height < height + 120:
        desired_height = height + 120
        desired_width = int(round(desired_height * TARGET_WIDTH / TARGET_HEIGHT))

    desired_width = min(viewport_width, max(2, desired_width))
    desired_height = min(viewport_height, max(2, desired_height))

    center_x = x + width / 2
    center_y = y + height / 2
    left = int(round(center_x - desired_width / 2))
    top = int(round(center_y - desired_height / 2))
    left = min(max(0, left), max(0, viewport_width - desired_width))
    top = min(max(0, top), max(0, viewport_height - desired_height))

    if desired_width % 2:
        desired_width -= 1
    if desired_height % 2:
        desired_height -= 1
    return left, top, max(2, desired_width), max(2, desired_height)


def _run_ffmpeg(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True, capture_output=True, text=True)


def _render_clip(
    *,
    source_path: Path,
    output_path: Path,
    start_seconds: float | None,
    end_seconds: float | None,
    focus_box: dict[str, Any] | None,
    viewport_width: int,
    viewport_height: int,
) -> None:
    left, top, width, height = _fit_focus_box(
        focus_box,
        viewport_width=viewport_width,
        viewport_height=viewport_height,
    )
    filters = (
        f"crop={width}:{height}:{left}:{top},"
        f"scale={TARGET_WIDTH}:{TARGET_HEIGHT}:flags=lanczos,"
        f"fps={TARGET_FPS},format=yuv420p"
    )
    cmd = ["ffmpeg", "-y"]
    if start_seconds is not None:
        cmd.extend(["-ss", f"{start_seconds:.3f}"])
    cmd.extend(["-i", str(source_path)])
    if end_seconds is not None and start_seconds is not None and end_seconds > start_seconds:
        cmd.extend(["-t", f"{max(0.0, end_seconds - start_seconds):.3f}"])
    elif end_seconds is not None:
        cmd.extend(["-to", f"{end_seconds:.3f}"])
    cmd.extend(
        [
            "-vf",
            filters,
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "23",
            "-pix_fmt",
            "yuv420p",
            "-an",
            str(output_path),
        ]
    )
    _run_ffmpeg(cmd)


def main() -> int:
    args = parse_args()
    manifest_path = Path(args.capture_manifest).expanduser().resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    clips = manifest.get("clips") if isinstance(manifest.get("clips"), list) else []
    processed_dir = Path(manifest.get("processed_dir") or manifest_path.parent / "processed").resolve()
    processed_dir.mkdir(parents=True, exist_ok=True)

    processed_entries: list[dict[str, Any]] = []
    for index, clip in enumerate(clips, start=1):
        if not isinstance(clip, dict):
            continue
        source_path = Path(str(clip.get("source_path") or clip.get("path") or "")).expanduser().resolve()
        if not source_path.exists():
            continue
        clip_id = str(clip.get("id") or f"clip_{index:02d}").strip() or f"clip_{index:02d}"
        output_path = processed_dir / f"{clip_id}.mp4"
        viewport = clip.get("viewport") if isinstance(clip.get("viewport"), dict) else {}
        viewport_width = int(viewport.get("width") or manifest.get("viewport", {}).get("width") or TARGET_WIDTH)
        viewport_height = int(viewport.get("height") or manifest.get("viewport", {}).get("height") or TARGET_HEIGHT)
        _render_clip(
            source_path=source_path,
            output_path=output_path,
            start_seconds=_safe_float(clip.get("start_seconds")),
            end_seconds=_safe_float(clip.get("end_seconds")),
            focus_box=clip.get("focus_box") if isinstance(clip.get("focus_box"), dict) else None,
            viewport_width=viewport_width,
            viewport_height=viewport_height,
        )
        processed_entries.append(
            {
                **clip,
                "path": str(output_path),
                "source_path": str(source_path),
                "kind": str(clip.get("kind") or "video_clip"),
            }
        )

    output_manifest = {
        **manifest,
        "processed_dir": str(processed_dir),
        "clips": processed_entries,
    }
    output_path = Path(args.output_manifest).expanduser().resolve() if args.output_manifest else manifest_path.parent / "processed_manifest.json"
    output_path.write_text(json.dumps(output_manifest, indent=2), encoding="utf-8")
    print(json.dumps(output_manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
