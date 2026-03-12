from __future__ import annotations

import json
import subprocess
from pathlib import Path


SCRIPT = (
    Path(__file__).resolve().parent.parent
    / "skills"
    / "cathode-project-demo"
    / "scripts"
    / "prepare_cathode_handoff.py"
)


def test_prepare_cathode_handoff_downgrades_legibility_warnings_and_prefers_video(tmp_path):
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    (repo_dir / "README.md").write_text("# Demo\n", encoding="utf-8")

    clip_path = tmp_path / "capture.mp4"
    clip_path.write_bytes(b"mp4")

    bundle_manifest = tmp_path / "processed_manifest.json"
    bundle_manifest.write_text(
        json.dumps(
            {
                "clips": [
                    {
                        "id": "hero",
                        "path": str(clip_path),
                        "label": "Hero clip",
                        "kind": "video_clip",
                        "review_status": "accept",
                    }
                ]
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    review_report = tmp_path / "review_report.json"
    review_report.write_text(
        json.dumps(
            {
                "decision": "warn",
                "recommended_clip_id": "hero",
                "clip_assessments": [
                    {
                        "clip_id": "hero",
                        "recommended": True,
                        "notes": "Readable enough, but still too cramped.",
                        "framing": "good",
                        "legibility": "weak",
                        "theme": "good",
                        "artifact_dominance": "strong",
                        "state_quality": "good",
                        "crop_quality": "better",
                    }
                ],
                "issues": [],
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    output_json = tmp_path / "handoff.json"
    subprocess.run(
        [
            "python3",
            str(SCRIPT),
            "--bundle-manifest",
            str(bundle_manifest),
            "--review-report",
            str(review_report),
            "--target-repo-path",
            str(repo_dir),
            "--intent",
            "Create a concise demo.",
            "--audience",
            "technical buyers",
            "--output-json",
            str(output_json),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads(output_json.read_text(encoding="utf-8"))
    assert payload["visual_source_strategy"] == "video_preferred"
    assert payload["footage_manifest"][0]["review_status"] == "warn"
    assert "too cramped" in payload["footage_manifest"][0]["review_summary"]
