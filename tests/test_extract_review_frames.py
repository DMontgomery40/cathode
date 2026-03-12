from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest


SCRIPT = Path(__file__).resolve().parent.parent / "skills" / "cathode-project-demo" / "scripts" / "extract_review_frames.py"


@pytest.mark.skipif(shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None, reason="ffmpeg and ffprobe are required")
def test_extract_review_frames_builds_review_image_manifest(tmp_path):
    source_video = tmp_path / "source.mp4"
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "testsrc=size=640x360:rate=24:duration=3",
            "-pix_fmt",
            "yuv420p",
            str(source_video),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    bundle_manifest = tmp_path / "bundle.json"
    bundle_manifest.write_text(
        json.dumps(
            {
                "clips": [
                    {
                        "id": "hero_clip",
                        "path": str(source_video),
                        "label": "Hero clip",
                        "kind": "video_clip",
                    }
                ]
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    output_dir = tmp_path / "review_frames"
    subprocess.run(
        [
            "python3",
            str(SCRIPT),
            "--bundle-manifest",
            str(bundle_manifest),
            "--output-dir",
            str(output_dir),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    review_manifest = json.loads((output_dir / "review_frames.json").read_text(encoding="utf-8"))
    assert review_manifest["items"][0]["clip_id"] == "hero_clip"
    assert len(review_manifest["items"][0]["frame_paths"]) == 3
    assert all(Path(path).exists() for path in review_manifest["items"][0]["frame_paths"])
