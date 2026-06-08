#!/usr/bin/env python3
"""Build a structured review report from reviewer observations."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core.demo_review import build_review_report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Combine reviewer observations with deterministic retry rules.")
    parser.add_argument("--bundle-manifest", required=True, help="Capture bundle manifest or processed manifest JSON.")
    parser.add_argument("--observations-json", required=True, help="Structured reviewer observations JSON.")
    parser.add_argument("--output-json", required=True, help="Where to write the final review report JSON.")
    parser.add_argument(
        "--raw-review-path",
        default="",
        help="Optional path to the saved plain-language spawned sub-agent feedback.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    bundle_manifest = json.loads(Path(args.bundle_manifest).read_text(encoding="utf-8"))
    observations = json.loads(Path(args.observations_json).read_text(encoding="utf-8"))
    report = build_review_report(bundle_manifest, observations)
    raw_review_path = str(args.raw_review_path or observations.get("raw_feedback_path") or "").strip()
    if raw_review_path:
        report["raw_review_path"] = str(Path(raw_review_path).expanduser().resolve())
    output_path = Path(args.output_json).expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
