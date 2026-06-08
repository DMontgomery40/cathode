#!/usr/bin/env python3
"""Prepare a deterministic live-demo capture session bundle."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core.demo_session import (
    DEFAULT_VIEWPORT_HEIGHT,
    DEFAULT_VIEWPORT_WIDTH,
    SUPPORTED_CAPTURE_DRIVERS,
    build_live_demo_session,
)


def _capture_driver_arg(value: str) -> str:
    normalized = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
    if normalized not in SUPPORTED_CAPTURE_DRIVERS:
        options = ", ".join(sorted(SUPPORTED_CAPTURE_DRIVERS))
        raise argparse.ArgumentTypeError(f"capture driver must normalize to one of: {options}")
    return normalized


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare a live demo capture session bundle.")
    parser.add_argument("--target-repo-path", required=True, help="Local repository or app workspace to demo.")
    parser.add_argument("--output-dir", required=True, help="Bundle directory used for capture artifacts and reports.")
    parser.add_argument("--app-url", help="Already-running app URL, when no local launch is needed.")
    parser.add_argument("--launch-command", help="Explicit command used to launch the target app locally.")
    parser.add_argument("--expected-url", help="Expected local URL that indicates the app is ready.")
    parser.add_argument("--preferred-theme", default="dark", help="Explicit starting theme: light or dark.")
    parser.add_argument(
        "--capture-driver",
        default="desktop_use",
        type=_capture_driver_arg,
        help="Preferred live-capture driver. Default: desktop_use",
    )
    parser.add_argument("--viewport-width", type=int, default=DEFAULT_VIEWPORT_WIDTH)
    parser.add_argument("--viewport-height", type=int, default=DEFAULT_VIEWPORT_HEIGHT)
    parser.add_argument("--flow-hint", action="append", default=[], help="Optional note about the flow to capture.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    session = build_live_demo_session(
        target_repo_path=args.target_repo_path,
        output_dir=args.output_dir,
        app_url=args.app_url,
        launch_command=args.launch_command,
        expected_url=args.expected_url,
        preferred_theme=args.preferred_theme,
        capture_driver=args.capture_driver,
        flow_hints=args.flow_hint,
        viewport_width=args.viewport_width,
        viewport_height=args.viewport_height,
    )
    session_path = Path(session["artifacts"]["session_manifest_path"])
    session_path.write_text(json.dumps(session, indent=2), encoding="utf-8")
    print(json.dumps(session, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
