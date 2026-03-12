#!/usr/bin/env python3
"""Turn a reviewed capture bundle into a Cathode make_video payload."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core.demo_assets import build_footage_summary, normalize_footage_manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare a Cathode make_video payload from a reviewed capture bundle.")
    parser.add_argument("--bundle-manifest", required=True, help="Processed capture bundle manifest JSON.")
    parser.add_argument("--review-report", required=True, help="Final review report JSON.")
    parser.add_argument("--target-repo-path", required=True, help="Repo or workspace path to inspect for source context.")
    parser.add_argument("--intent", required=True, help="Demo goal passed through to Cathode make_video.")
    parser.add_argument("--audience", required=True, help="Audience for the final video.")
    parser.add_argument("--target-length-minutes", type=float, default=1.5)
    parser.add_argument("--tone", default="clear, technical, grounded")
    parser.add_argument("--visual-style", default="clean editorial product demo")
    parser.add_argument("--ending-cta", default="")
    parser.add_argument("--must-include", default="")
    parser.add_argument("--source-path", action="append", default=[], help="High-signal source file to pass through to Cathode.")
    parser.add_argument("--output-json", required=True, help="Where to write the final Cathode payload JSON.")
    return parser.parse_args()


def _default_source_paths(repo_path: Path) -> list[str]:
    candidates = [
        repo_path / "README.md",
        repo_path / "docs" / "getting-started.md",
        repo_path / "docs" / "workflows.md",
        repo_path / "package.json",
        repo_path / "pyproject.toml",
    ]
    return [str(path.resolve()) for path in candidates if path.exists() and path.is_file()][:4]


def _assessment_requires_warn(assessment: dict | None) -> bool:
    if not isinstance(assessment, dict):
        return False
    if str(assessment.get("state_quality") or "").strip().lower() == "weak":
        return True
    if str(assessment.get("framing") or "").strip().lower() in {"weak", "poor"}:
        return True
    if str(assessment.get("legibility") or "").strip().lower() in {"weak", "poor"}:
        return True
    if str(assessment.get("theme") or "").strip().lower() in {"wrong", "mixed"}:
        return True
    if str(assessment.get("artifact_dominance") or "").strip().lower() in {"weak", "mixed"}:
        return True
    if str(assessment.get("crop_quality") or "").strip().lower() == "worse":
        return True
    return False


def _visual_source_strategy_for_reviewed_clips(clips: list[dict]) -> str:
    if not clips:
        return "images_only"
    kinds = {str(item.get("kind") or "").strip().lower() for item in clips}
    if kinds and kinds <= {"video_clip", "final_video"}:
        return "video_preferred"
    return "mixed_media"


def _safe_priority(value: object) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def main() -> int:
    args = parse_args()
    bundle_manifest = json.loads(Path(args.bundle_manifest).read_text(encoding="utf-8"))
    review_report = json.loads(Path(args.review_report).read_text(encoding="utf-8"))
    repo_path = Path(args.target_repo_path).expanduser().resolve()

    clips = normalize_footage_manifest(bundle_manifest.get("clips") or [])
    assessments = {
        str(item.get("clip_id") or ""): item
        for item in review_report.get("clip_assessments") or []
        if isinstance(item, dict) and str(item.get("clip_id") or "").strip()
    }

    selected: list[dict] = []
    for clip in clips:
        assessment = assessments.get(str(clip["id"]))
        if _assessment_requires_warn(assessment):
            clip["review_status"] = "warn"
            if not clip.get("review_summary"):
                clip["review_summary"] = str(assessment.get("notes") or "Capture is usable but not ideal as a hero state.")
        selected.append(clip)

    ordered = sorted(
        selected,
        key=lambda item: (
            0 if str(item.get("id")) == str(review_report.get("recommended_clip_id") or "") else 1,
            0 if str(item.get("review_status") or "accept") == "accept" else 1,
            _safe_priority(item.get("priority")),
        ),
    )

    source_paths = [str(Path(path).expanduser().resolve()) for path in args.source_path if Path(path).exists()]
    if not source_paths:
        source_paths = _default_source_paths(repo_path)

    must_avoid = ""
    if any(str(item.get("review_status") or "") == "warn" for item in ordered):
        must_avoid = "Do not center clips marked warn as the hero proof moment unless the narration clearly caveats them."

    payload = {
        "intent": args.intent,
        "workspace_path": str(repo_path),
        "source_paths": source_paths,
        "audience": args.audience,
        "target_length_minutes": args.target_length_minutes,
        "tone": args.tone,
        "visual_style": args.visual_style,
        "visual_source_strategy": _visual_source_strategy_for_reviewed_clips(ordered),
        "footage_manifest": ordered,
        "available_footage": build_footage_summary(ordered),
        "ending_cta": args.ending_cta,
        "must_include": args.must_include,
        "must_avoid": must_avoid,
        "run_until": "render",
        "ready_for_handoff": str(review_report.get("decision") or "") in {"accept", "warn"},
        "review_decision": str(review_report.get("decision") or ""),
    }
    output_path = Path(args.output_json).expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
