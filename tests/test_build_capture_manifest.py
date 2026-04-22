from __future__ import annotations

import json
import subprocess
from pathlib import Path


SCRIPT = (
    Path(__file__).resolve().parent.parent
    / "skills"
    / "cathode-project-demo"
    / "scripts"
    / "build_capture_manifest.py"
)


def test_build_capture_manifest_bundles_manual_desktop_capture(tmp_path):
    bundle_dir = tmp_path / "bundle"
    raw_dir = bundle_dir / "raw"
    screenshots_dir = bundle_dir / "screenshots"
    reports_dir = bundle_dir / "reports"
    raw_dir.mkdir(parents=True)
    screenshots_dir.mkdir(parents=True)
    reports_dir.mkdir(parents=True)

    session_json = bundle_dir / "session.json"
    session_json.write_text(
        json.dumps(
            {
                "session_id": "rondo_demo_1234abcd",
                "target_repo_path": str(tmp_path / "repo"),
                "app_url": "http://127.0.0.1:4173",
                "preferred_theme": "dark",
                "viewport": {"width": 1664, "height": 928},
                "artifacts": {
                    "raw_dir": str(raw_dir),
                    "screenshots_dir": str(screenshots_dir),
                    "reports_dir": str(reports_dir),
                    "processed_dir": str(bundle_dir / "processed"),
                    "capture_manifest_path": str(bundle_dir / "capture_manifest.json"),
                },
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    raw_video = tmp_path / "desktop_run.mp4"
    raw_video.write_bytes(b"not-a-real-video-but-good-enough-for-manifest-tests")
    screenshot = tmp_path / "hero.png"
    screenshot.write_bytes(b"png")

    clips_json = tmp_path / "clips.json"
    clips_json.write_text(
        json.dumps(
            {
                "clips": [
                    {
                        "id": "hero_flow",
                        "label": "Hero flow",
                        "start_seconds": 1.25,
                        "end_seconds": 7.5,
                        "screenshot_path": screenshot.name,
                        "text_excerpt": "Rondo workspace with possession map visible.",
                        "notes": "Best hero proof moment from the desktop-use pass.",
                        "focus_box": {"x": 120, "y": 80, "width": 900, "height": 620},
                    }
                ]
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    output_manifest = bundle_dir / "desktop_capture_manifest.json"
    subprocess.run(
        [
            "python3",
            str(SCRIPT),
            "--session-json",
            str(session_json),
            "--raw-video-path",
            str(raw_video),
            "--clips-json",
            str(clips_json),
            "--output-manifest",
            str(output_manifest),
            "--attempt-name",
            "desktop_attempt",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    manifest = json.loads(output_manifest.read_text(encoding="utf-8"))
    step_manifest = json.loads(Path(manifest["step_manifest_path"]).read_text(encoding="utf-8"))

    copied_raw_video = Path(manifest["raw_video_path"])
    assert copied_raw_video.exists()
    assert copied_raw_video.parent == raw_dir
    assert manifest["capture_driver"] == "desktop_use"
    assert manifest["clips"][0]["id"] == "hero_flow"
    assert manifest["clips"][0]["source_path"] == str(copied_raw_video)
    copied_screenshot = Path(manifest["clips"][0]["screenshot_path"])
    assert copied_screenshot.exists()
    assert copied_screenshot.parent == screenshots_dir / "desktop_attempt"
    assert manifest["trace_path"] == ""
    assert step_manifest["capture_driver"] == "desktop_use"
    assert Path(step_manifest["steps"][0]["screenshot_path"]) == copied_screenshot
    assert step_manifest["steps"][0]["text_excerpt"].startswith("Rondo workspace")


def test_build_capture_manifest_uses_unique_default_attempt_names(tmp_path):
    bundle_dir = tmp_path / "bundle"
    raw_dir = bundle_dir / "raw"
    screenshots_dir = bundle_dir / "screenshots"
    reports_dir = bundle_dir / "reports"
    raw_dir.mkdir(parents=True)
    screenshots_dir.mkdir(parents=True)
    reports_dir.mkdir(parents=True)

    session_json = bundle_dir / "session.json"
    session_json.write_text(
        json.dumps(
            {
                "session_id": "rondo_demo_1234abcd",
                "target_repo_path": str(tmp_path / "repo"),
                "app_url": "http://127.0.0.1:4173",
                "preferred_theme": "dark",
                "viewport": {"width": 1664, "height": 928},
                "artifacts": {
                    "raw_dir": str(raw_dir),
                    "screenshots_dir": str(screenshots_dir),
                    "reports_dir": str(reports_dir),
                    "processed_dir": str(bundle_dir / "processed"),
                    "capture_manifest_path": str(bundle_dir / "capture_manifest.json"),
                },
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    raw_video = tmp_path / "desktop_run.mp4"
    raw_video.write_bytes(b"not-a-real-video-but-good-enough-for-manifest-tests")
    screenshot = tmp_path / "hero.png"
    screenshot.write_bytes(b"png")
    clips_json = tmp_path / "clips.json"
    clips_json.write_text(
        json.dumps(
            {
                "clips": [
                    {
                        "id": "hero_flow",
                        "label": "Hero flow",
                        "start_seconds": 1.25,
                        "end_seconds": 7.5,
                        "screenshot_path": screenshot.name,
                    }
                ]
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    manifest_paths = [bundle_dir / "capture_first.json", bundle_dir / "capture_second.json"]
    manifests = []
    for output_manifest in manifest_paths:
        subprocess.run(
            [
                "python3",
                str(SCRIPT),
                "--session-json",
                str(session_json),
                "--raw-video-path",
                str(raw_video),
                "--clips-json",
                str(clips_json),
                "--output-manifest",
                str(output_manifest),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        manifests.append(json.loads(output_manifest.read_text(encoding="utf-8")))

    first_manifest, second_manifest = manifests
    assert first_manifest["raw_video_path"] != second_manifest["raw_video_path"]
    assert first_manifest["step_manifest_path"] != second_manifest["step_manifest_path"]
    assert first_manifest["clips"][0]["screenshot_path"] != second_manifest["clips"][0]["screenshot_path"]
    assert Path(first_manifest["raw_video_path"]).exists()
    assert Path(second_manifest["raw_video_path"]).exists()
    assert Path(first_manifest["step_manifest_path"]).exists()
    assert Path(second_manifest["step_manifest_path"]).exists()
