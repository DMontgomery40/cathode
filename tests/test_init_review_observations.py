from __future__ import annotations

import json
import subprocess
from pathlib import Path


SCRIPT = (
    Path(__file__).resolve().parent.parent
    / "skills"
    / "cathode-project-demo"
    / "scripts"
    / "init_review_observations.py"
)


def test_init_review_observations_creates_parent_editable_template(tmp_path):
    bundle_manifest = tmp_path / "processed_manifest.json"
    bundle_manifest.write_text(
        json.dumps(
            {
                "clips": [
                    {"id": "run_review", "label": "Run review overlay", "kind": "video_clip"},
                    {"id": "final_render", "label": "Final render", "kind": "final_video"},
                ]
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    review_frames_manifest = tmp_path / "review_frames.json"
    review_frames_manifest.write_text(
        json.dumps(
            {
                "items": [
                    {
                        "clip_id": "run_review",
                        "label": "Run review overlay",
                        "kind": "video_clip",
                        "frame_paths": ["/tmp/run_review/frame_01.jpg"],
                    }
                ]
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    output_path = tmp_path / "reports" / "review_observations.template.json"
    subprocess.run(
        [
            "python3",
            str(SCRIPT),
            "--bundle-manifest",
            str(bundle_manifest),
            "--review-frames-manifest",
            str(review_frames_manifest),
            "--raw-review-path",
            str(tmp_path / "reports" / "subagent_qc_raw.md"),
            "--output-json",
            str(output_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["decision"] == "retry"
    assert payload["raw_feedback_path"].endswith("subagent_qc_raw.md")
    assert payload["clip_assessments"][0]["clip_id"] == "run_review"
    assert payload["clip_assessments"][0]["reference_frames"] == ["/tmp/run_review/frame_01.jpg"]
