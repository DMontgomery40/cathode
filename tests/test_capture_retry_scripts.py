from __future__ import annotations

import json
import os
import shlex
import shutil
import socket
import socketserver
import subprocess
import sys
import threading
import time
from functools import partial
from http.server import BaseHTTPRequestHandler
from http.server import SimpleHTTPRequestHandler
from pathlib import Path

import pytest


FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "live_demo_app"
SKILL_SCRIPTS = Path(__file__).resolve().parent.parent / "skills" / "cathode-project-demo" / "scripts"


def _wait_for_file(file_path: Path, timeout_seconds: float = 3.0) -> None:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        if file_path.exists():
            return
        time.sleep(0.05)
    raise AssertionError(f"Timed out waiting for {file_path}")


def _process_is_running(pid: int) -> bool:
    if os.name == "posix":
        completed = subprocess.run(
            ["ps", "-o", "stat=", "-p", str(pid)],
            capture_output=True,
            text=True,
            check=False,
        )
        status = (completed.stdout or "").strip()
        if completed.returncode != 0 or not status:
            return False
        return not status.startswith("Z")
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


class _NonIdleAppHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, format, *args):  # noqa: A003
        return

    def do_GET(self):  # noqa: N802
        if self.path.startswith("/events"):
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.end_headers()
            self.wfile.write(b"data: ready\n\n")
            self.wfile.flush()
            time.sleep(5)
            return
        if self.path.startswith("/favicon.ico"):
            self.send_response(204)
            self.end_headers()
            return

        body = (
            b"<!doctype html><html><body>"
            b"<div id='app'>Live app ready</div>"
            b"<script>window.demoStream = new EventSource('/events');</script>"
            b"</body></html>"
        )
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


@pytest.mark.skipif(shutil.which("npx") is None, reason="npx is required for capture retry script coverage")
def test_capture_retry_scripts_exercise_retry_plan_and_evaluate_actions(tmp_path):
    handler = partial(SimpleHTTPRequestHandler, directory=str(FIXTURE_DIR))
    with socketserver.TCPServer(("127.0.0.1", 0), handler) as server:
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            app_url = f"http://127.0.0.1:{server.server_address[1]}/index.html"
            bundle_dir = tmp_path / "bundle"
            subprocess.run(
                [
                    "python3",
                    str(SKILL_SCRIPTS / "prepare_live_demo_session.py"),
                    "--target-repo-path",
                    str(FIXTURE_DIR),
                    "--output-dir",
                    str(bundle_dir),
                    "--app-url",
                    app_url,
                ],
                check=True,
                capture_output=True,
                text=True,
            )

            base_plan = tmp_path / "capture_plan.json"
            base_plan.write_text(
                json.dumps(
                    {
                        "theme": "dark",
                        "retry_overrides": {
                            "pick_better_state": {
                                "steps": [
                                    {
                                        "id": "evaluate_marker",
                                        "label": "Evaluate marker",
                                        "actions": [
                                            {
                                                "type": "evaluate",
                                                "script": "() => { const marker = document.createElement('div'); marker.id = 'qc-marker'; marker.textContent = 'Evaluate worked'; marker.style.position = 'fixed'; marker.style.top = '24px'; marker.style.left = '24px'; marker.style.padding = '12px'; marker.style.zIndex = '9999'; marker.style.background = '#ffffff'; marker.style.color = '#111111'; document.body.appendChild(marker); }",
                                            }
                                        ],
                                        "focus_selector": "#qc-marker",
                                        "text_selector": "#qc-marker",
                                        "hold_ms": 400,
                                        "clip": {
                                            "id": "evaluate_marker",
                                            "label": "Evaluate marker",
                                            "notes": "Marker created via evaluate action.",
                                            "review_status": "accept",
                                        },
                                    }
                                ]
                            }
                        },
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )

            review_report = tmp_path / "review_report.json"
            review_report.write_text(
                json.dumps({"decision": "retry", "retry_actions": ["pick_better_state"]}, indent=2),
                encoding="utf-8",
            )

            retried_plan = tmp_path / "capture_plan.retry.json"
            subprocess.run(
                [
                    "python3",
                    str(SKILL_SCRIPTS / "apply_retry_actions.py"),
                    "--capture-plan",
                    str(base_plan),
                    "--review-report",
                    str(review_report),
                    "--output-json",
                    str(retried_plan),
                ],
                check=True,
                capture_output=True,
                text=True,
            )

            capture_manifest_path = bundle_dir / "capture_manifest.json"
            subprocess.run(
                [
                    "python3",
                    str(SKILL_SCRIPTS / "capture_live_demo.py"),
                    "--session-json",
                    str(bundle_dir / "session.json"),
                    "--capture-plan",
                    str(retried_plan),
                    "--output-manifest",
                    str(capture_manifest_path),
                    "--attempt-name",
                    "retry_eval",
                    "--headless",
                ],
                check=True,
                capture_output=True,
                text=True,
            )

            capture_manifest = json.loads(capture_manifest_path.read_text(encoding="utf-8"))
            step_manifest = json.loads(
                Path(capture_manifest["step_manifest_path"]).read_text(encoding="utf-8")
            )

            assert capture_manifest["clips"][0]["id"] == "evaluate_marker"
            assert "Evaluate worked" in step_manifest["steps"][0]["text_excerpt"]
            assert Path(capture_manifest["raw_video_path"]).exists()
        finally:
            server.shutdown()
            thread.join(timeout=5)


@pytest.mark.skipif(shutil.which("npx") is None, reason="npx is required for capture retry script coverage")
def test_capture_retry_scripts_preserve_step_screenshots_across_attempts(tmp_path):
    handler = partial(SimpleHTTPRequestHandler, directory=str(FIXTURE_DIR))
    with socketserver.TCPServer(("127.0.0.1", 0), handler) as server:
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            app_url = f"http://127.0.0.1:{server.server_address[1]}/index.html"
            bundle_dir = tmp_path / "bundle"
            subprocess.run(
                [
                    "python3",
                    str(SKILL_SCRIPTS / "prepare_live_demo_session.py"),
                    "--target-repo-path",
                    str(FIXTURE_DIR),
                    "--output-dir",
                    str(bundle_dir),
                    "--app-url",
                    app_url,
                ],
                check=True,
                capture_output=True,
                text=True,
            )

            capture_plan = tmp_path / "capture_plan.json"
            capture_plan.write_text(
                json.dumps(
                    {
                        "theme": "dark",
                        "steps": [
                            {
                                "id": "workspace",
                                "label": "Workspace",
                                "text_selector": "body",
                                "hold_ms": 300,
                                "clip": {
                                    "id": "workspace",
                                    "label": "Workspace",
                                    "notes": "Capture the fixture app landing state.",
                                    "review_status": "accept",
                                },
                            }
                        ],
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )

            first_manifest_path = bundle_dir / "capture_attempt_one.json"
            second_manifest_path = bundle_dir / "capture_attempt_two.json"
            for attempt_name, output_path in (
                ("attempt_one", first_manifest_path),
                ("attempt_two", second_manifest_path),
            ):
                subprocess.run(
                    [
                        "python3",
                        str(SKILL_SCRIPTS / "capture_live_demo.py"),
                        "--session-json",
                        str(bundle_dir / "session.json"),
                        "--capture-plan",
                        str(capture_plan),
                        "--output-manifest",
                        str(output_path),
                        "--attempt-name",
                        attempt_name,
                        "--headless",
                    ],
                    check=True,
                    capture_output=True,
                    text=True,
                )

            first_manifest = json.loads(first_manifest_path.read_text(encoding="utf-8"))
            second_manifest = json.loads(second_manifest_path.read_text(encoding="utf-8"))
            first_steps = json.loads(Path(first_manifest["step_manifest_path"]).read_text(encoding="utf-8"))
            second_steps = json.loads(Path(second_manifest["step_manifest_path"]).read_text(encoding="utf-8"))

            first_screenshot = Path(first_steps["steps"][0]["screenshot_path"])
            second_screenshot = Path(second_steps["steps"][0]["screenshot_path"])

            assert first_screenshot.exists()
            assert second_screenshot.exists()
            assert first_screenshot != second_screenshot
            assert first_screenshot.parent.name == "attempt_one"
            assert second_screenshot.parent.name == "attempt_two"
        finally:
            server.shutdown()
            thread.join(timeout=5)


@pytest.mark.skipif(shutil.which("npx") is None, reason="npx is required for capture retry script coverage")
def test_capture_live_demo_handles_pages_with_long_lived_network_activity(tmp_path):
    with socketserver.ThreadingTCPServer(("127.0.0.1", 0), _NonIdleAppHandler) as server:
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            app_url = f"http://127.0.0.1:{server.server_address[1]}/index.html"
            bundle_dir = tmp_path / "bundle"
            subprocess.run(
                [
                    "python3",
                    str(SKILL_SCRIPTS / "prepare_live_demo_session.py"),
                    "--target-repo-path",
                    str(FIXTURE_DIR),
                    "--output-dir",
                    str(bundle_dir),
                    "--app-url",
                    app_url,
                ],
                check=True,
                capture_output=True,
                text=True,
            )

            capture_plan = tmp_path / "capture_plan.json"
            capture_plan.write_text(
                json.dumps(
                    {
                        "steps": [
                            {
                                "id": "streaming_app",
                                "label": "Streaming app",
                                "focus_selector": "#app",
                                "text_selector": "#app",
                                "hold_ms": 200,
                                "clip": {
                                    "id": "streaming_app",
                                    "label": "Streaming app",
                                    "notes": "App keeps a long-lived event stream open.",
                                    "review_status": "accept",
                                },
                            }
                        ]
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )

            capture_manifest_path = bundle_dir / "capture_manifest.json"
            subprocess.run(
                [
                    "python3",
                    str(SKILL_SCRIPTS / "capture_live_demo.py"),
                    "--session-json",
                    str(bundle_dir / "session.json"),
                    "--capture-plan",
                    str(capture_plan),
                    "--output-manifest",
                    str(capture_manifest_path),
                    "--attempt-name",
                    "streaming_app",
                    "--timeout-seconds",
                    "3",
                    "--headless",
                ],
                check=True,
                capture_output=True,
                text=True,
            )

            capture_manifest = json.loads(capture_manifest_path.read_text(encoding="utf-8"))
            assert Path(capture_manifest["raw_video_path"]).exists()
            assert capture_manifest["clips"][0]["id"] == "streaming_app"
        finally:
            server.shutdown()
            thread.join(timeout=5)


def test_launch_target_app_cleans_up_failed_readiness_process(tmp_path):
    child_pid_path = tmp_path / "child.pid"
    child_script = tmp_path / "child_writer.py"
    child_script.write_text(
        "\n".join(
            [
                "import os",
                "import time",
                "from pathlib import Path",
                f"Path({str(child_pid_path)!r}).write_text(str(os.getpid()), encoding='utf-8')",
                "time.sleep(30)",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        unused_port = sock.getsockname()[1]

    session_path = tmp_path / "session.json"
    launch_state_path = tmp_path / "launch_state.json"
    session_path.write_text(
        json.dumps(
            {
                "target_repo_path": str(tmp_path),
                "launch_command": f"{shlex.quote(sys.executable)} {shlex.quote(str(child_script))}",
                "expected_url": f"http://127.0.0.1:{unused_port}/ready",
                "artifacts": {
                    "launch_state_path": str(launch_state_path),
                    "reports_dir": str(tmp_path / "reports"),
                },
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            "python3",
            str(SKILL_SCRIPTS / "launch_target_app.py"),
            "--session-json",
            str(session_path),
            "--timeout-seconds",
            "0.5",
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    _wait_for_file(child_pid_path)
    child_pid = int(child_pid_path.read_text(encoding="utf-8").strip())

    deadline = time.time() + 5
    while time.time() < deadline and _process_is_running(child_pid):
        time.sleep(0.1)

    if _process_is_running(child_pid):
        os.kill(child_pid, 9)
        raise AssertionError("failed launch left the spawned process running")

    assert not launch_state_path.exists()


def test_launch_target_app_requires_expected_url_for_local_launch(tmp_path):
    session_path = tmp_path / "session.json"
    launch_state_path = tmp_path / "launch_state.json"
    session_path.write_text(
        json.dumps(
            {
                "target_repo_path": str(tmp_path),
                "launch_command": f"{shlex.quote(sys.executable)} -c \"import time; time.sleep(30)\"",
                "expected_url": "",
                "artifacts": {
                    "launch_state_path": str(launch_state_path),
                    "reports_dir": str(tmp_path / "reports"),
                },
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            "python3",
            str(SKILL_SCRIPTS / "launch_target_app.py"),
            "--session-json",
            str(session_path),
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert not launch_state_path.exists()


def test_launch_target_app_stop_waits_for_process_exit(tmp_path):
    sleeper = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(30)"],
        start_new_session=True,
    )
    launch_state_path = tmp_path / "launch_state.json"
    launch_state_path.write_text(
        json.dumps({"pid": sleeper.pid}, indent=2),
        encoding="utf-8",
    )
    session_path = tmp_path / "session.json"
    session_path.write_text(
        json.dumps({"artifacts": {"launch_state_path": str(launch_state_path)}}, indent=2),
        encoding="utf-8",
    )

    try:
        result = subprocess.run(
            [
                "python3",
                str(SKILL_SCRIPTS / "launch_target_app.py"),
                "--session-json",
                str(session_path),
                "--stop",
            ],
            check=True,
            capture_output=True,
            text=True,
        )

        assert '"status": "stopped"' in result.stdout
        deadline = time.time() + 5
        while time.time() < deadline and _process_is_running(sleeper.pid):
            time.sleep(0.1)
        assert not _process_is_running(sleeper.pid)
        sleeper.wait(timeout=1)
    finally:
        if _process_is_running(sleeper.pid):
            os.kill(sleeper.pid, 9)
