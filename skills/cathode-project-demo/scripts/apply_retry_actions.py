#!/usr/bin/env python3
"""Apply review-driven retry actions to a capture plan."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core.demo_capture_plan import apply_retry_actions_to_capture_plan


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the next capture plan from a review report retry recommendation.")
    parser.add_argument("--capture-plan", required=True, help="Base capture plan JSON.")
    parser.add_argument("--output-json", required=True, help="Where to write the mutated retry plan.")
    parser.add_argument("--review-report", help="Optional review report JSON; uses retry_actions when --action is omitted.")
    parser.add_argument("--action", action="append", default=[], help="Explicit retry action to apply. Repeat as needed.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    plan = json.loads(Path(args.capture_plan).read_text(encoding="utf-8"))

    actions = [str(item).strip() for item in args.action if str(item).strip()]
    if not actions and args.review_report:
        report = json.loads(Path(args.review_report).read_text(encoding="utf-8"))
        actions = [str(item).strip() for item in (report.get("retry_actions") or []) if str(item).strip()]

    updated = apply_retry_actions_to_capture_plan(plan, actions)
    output_path = Path(args.output_json).expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(updated, indent=2), encoding="utf-8")
    print(json.dumps(updated, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
