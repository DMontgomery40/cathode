#!/usr/bin/env python3
"""Run the packaged Playwright-backed live capture workflow."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Capture a live demo walkthrough with Playwright and emit a capture bundle manifest.")
    parser.add_argument("--session-json", required=True, help="Prepared session manifest from prepare_live_demo_session.py.")
    parser.add_argument("--capture-plan", required=True, help="Capture plan JSON describing the real browser walkthrough.")
    parser.add_argument("--output-manifest", help="Optional path for the capture manifest JSON.")
    parser.add_argument("--attempt-name", default="", help="Optional attempt label used in retained artifact names.")
    parser.add_argument("--headless", action="store_true", help="Run the browser headlessly. Useful for tests and CI.")
    parser.add_argument("--timeout-seconds", type=float, default=30.0, help="Per-action timeout in seconds.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if shutil.which("npx") is None:
        raise SystemExit("npx is required to run the packaged Playwright capture workflow.")

    script_path = Path(__file__).with_name("capture_live_demo.mjs")
    command = [
        "npx",
        "--yes",
        "--package",
        "playwright",
        "node",
        str(script_path),
        "--session-json",
        str(Path(args.session_json).expanduser().resolve()),
        "--capture-plan",
        str(Path(args.capture_plan).expanduser().resolve()),
        "--timeout-seconds",
        str(args.timeout_seconds),
    ]
    if args.output_manifest:
        command.extend(["--output-manifest", str(Path(args.output_manifest).expanduser().resolve())])
    if args.attempt_name:
        command.extend(["--attempt-name", args.attempt_name])
    if args.headless:
        command.append("--headless")

    env = os.environ.copy()
    subprocess.run(command, check=True, env=env)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
