#!/usr/bin/env python3
"""Launch or stop a local target app referenced by a prepared live-demo session."""

from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Launch or stop a local demo target app.")
    parser.add_argument("--session-json", required=True, help="Path to the prepared session.json file.")
    parser.add_argument("--timeout-seconds", type=float, default=45.0, help="How long to wait for the app to become reachable.")
    parser.add_argument("--stop", action="store_true", help="Stop a previously launched app using launch_state.json.")
    return parser.parse_args()


def _wait_for_url(url: str, timeout_seconds: float) -> None:
    if not url:
        return
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2.5) as response:
                if int(getattr(response, "status", 200)) < 500:
                    return
        except (urllib.error.URLError, TimeoutError):
            time.sleep(0.5)
    raise TimeoutError(f"Timed out waiting for {url}")


def _stop_process_group(pid: int) -> None:
    try:
        if os.name == "posix":
            os.killpg(pid, signal.SIGTERM)
        else:
            os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        return


def _kill_process_group(pid: int) -> None:
    try:
        if os.name == "posix":
            os.killpg(pid, signal.SIGKILL)
        else:
            os.kill(pid, signal.SIGKILL)
    except ProcessLookupError:
        return


def _cleanup_failed_launch(process: subprocess.Popen[bytes]) -> None:
    _stop_process_group(process.pid)
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        _kill_process_group(process.pid)
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            pass


def main() -> int:
    args = parse_args()
    session_path = Path(args.session_json).expanduser().resolve()
    session = json.loads(session_path.read_text(encoding="utf-8"))
    state_path = Path(session["artifacts"]["launch_state_path"])

    if args.stop:
        if not state_path.exists():
            print(json.dumps({"status": "not_running", "launch_state_path": str(state_path)}))
            return 0
        state = json.loads(state_path.read_text(encoding="utf-8"))
        pid = int(state.get("pid") or 0)
        if pid > 0:
            _stop_process_group(pid)
        print(json.dumps({"status": "stopped", "pid": pid, "launch_state_path": str(state_path)}, indent=2))
        return 0

    launch_command = str(session.get("launch_command") or "").strip()
    expected_url = str(session.get("expected_url") or session.get("app_url") or "").strip()
    log_path = Path(session["artifacts"]["reports_dir"]) / "launch.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)

    if not launch_command:
        _wait_for_url(expected_url, args.timeout_seconds)
        state = {
            "status": "attached",
            "pid": None,
            "launch_command": "",
            "expected_url": expected_url,
            "log_path": str(log_path),
        }
        state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")
        print(json.dumps(state, indent=2))
        return 0

    with log_path.open("ab") as log_handle:
        process = subprocess.Popen(
            launch_command if os.name == "nt" else ["bash", "-lc", launch_command],
            cwd=str(Path(session["target_repo_path"])),
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            start_new_session=True,
            shell=os.name == "nt",
        )

    try:
        _wait_for_url(expected_url, args.timeout_seconds)
    except Exception:
        _cleanup_failed_launch(process)
        raise
    state = {
        "status": "running",
        "pid": process.pid,
        "launch_command": launch_command,
        "expected_url": expected_url,
        "log_path": str(log_path),
    }
    state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")
    print(json.dumps(state, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
