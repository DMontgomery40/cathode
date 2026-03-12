#!/usr/bin/env python3
"""Extract review frames from processed clips or a final rendered demo video."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extract representative review frames for a spawned QC sub-agent.")
    parser.add_argument("--bundle-manifest", help="Processed bundle manifest JSON.")
    parser.add_argument("--video-path", help="Optional final rendered MP4 to review.")
    parser.add_argument("--output-dir", required=True, help="Directory where extracted JPEG frames should be written.")
    parser.add_argument("--frames-per-clip", type=int, default=3, help="Representative frames to extract per clip. Default: 3")
    parser.add_argument("--output-json", help="Optional JSON manifest path. Defaults to <output-dir>/review_frames.json")
    return parser.parse_args()


def _probe_duration_seconds(path: Path) -> float:
    completed = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    try:
        return max(0.0, float(completed.stdout.strip()))
    except ValueError:
        return 0.0


def _frame_times(duration_seconds: float, frame_count: int) -> list[float]:
    if duration_seconds <= 0 or frame_count <= 1:
        return [0.0]
    if frame_count == 2:
        return [max(0.0, duration_seconds * 0.2), max(0.0, duration_seconds * 0.8)]
    if frame_count == 3:
        return [
            max(0.0, duration_seconds * 0.15),
            max(0.0, duration_seconds * 0.5),
            max(0.0, duration_seconds * 0.85),
        ]
    step = duration_seconds / (frame_count + 1)
    return [step * (index + 1) for index in range(frame_count)]


def _extract_frame(source_path: Path, output_path: Path, timestamp_seconds: float) -> None:
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


def _bundle_items(bundle_manifest: dict) -> list[dict]:
    clips = bundle_manifest.get("clips") if isinstance(bundle_manifest.get("clips"), list) else []
    items: list[dict] = []
    for clip in clips:
        if not isinstance(clip, dict):
            continue
        path_value = str(clip.get("path") or clip.get("source_path") or "").strip()
        if not path_value:
            continue
        items.append(
            {
                "clip_id": str(clip.get("id") or Path(path_value).stem).strip() or Path(path_value).stem,
                "label": str(clip.get("label") or Path(path_value).stem).strip() or Path(path_value).stem,
                "path": path_value,
                "kind": str(clip.get("kind") or "video_clip"),
            }
        )
    return items


def main() -> int:
    args = parse_args()
    output_dir = Path(args.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    items: list[dict] = []
    if args.bundle_manifest:
        bundle_manifest = json.loads(Path(args.bundle_manifest).read_text(encoding="utf-8"))
        items.extend(_bundle_items(bundle_manifest))
    if args.video_path:
        items.append(
            {
                "clip_id": "final_render",
                "label": "Final render",
                "path": str(Path(args.video_path).expanduser().resolve()),
                "kind": "final_video",
            }
        )

    extracted: list[dict] = []
    for item in items:
        source_path = Path(item["path"]).expanduser().resolve()
        if not source_path.exists():
            continue
        clip_dir = output_dir / item["clip_id"]
        duration_seconds = _probe_duration_seconds(source_path)
        frame_paths: list[str] = []
        for index, timestamp in enumerate(_frame_times(duration_seconds, max(1, args.frames_per_clip)), start=1):
            frame_path = clip_dir / f"frame_{index:02d}.jpg"
            _extract_frame(source_path, frame_path, timestamp)
            frame_paths.append(str(frame_path))
        extracted.append(
            {
                "clip_id": item["clip_id"],
                "label": item["label"],
                "kind": item["kind"],
                "source_path": str(source_path),
                "duration_seconds": duration_seconds,
                "frame_paths": frame_paths,
            }
        )

    payload = {"items": extracted}
    output_json = (
        Path(args.output_json).expanduser().resolve()
        if args.output_json
        else output_dir / "review_frames.json"
    )
    output_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
