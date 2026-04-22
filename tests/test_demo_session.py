from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from core.demo_session import build_live_demo_session

PREPARE_SCRIPT = (
    Path(__file__).resolve().parent.parent
    / "skills"
    / "cathode-project-demo"
    / "scripts"
    / "prepare_live_demo_session.py"
)


def test_build_live_demo_session_infers_launch_and_expected_url(tmp_path):
    repo_dir = tmp_path / "fixture_repo"
    repo_dir.mkdir()
    (repo_dir / "run_all.sh").write_text("#!/usr/bin/env bash\n")
    (repo_dir / "README.md").write_text("Open http://127.0.0.1:4317 to view the app.\n")

    session = build_live_demo_session(
        target_repo_path=repo_dir,
        output_dir=tmp_path / "output",
        flow_hints=["Open the run review tab."],
    )

    assert session["launch_command"] == "./run_all.sh"
    assert session["expected_url"] == "http://127.0.0.1:4317"
    assert session["flow_hints"] == ["Open the run review tab."]
    assert Path(session["artifacts"]["session_manifest_path"]).parent.exists()
    assert session["capture_defaults"]["primary_driver"] == "desktop_use"
    assert session["capture_defaults"]["fallback_driver"] == "playwright"
    assert session["capture_defaults"]["record_trace"] is False
    assert session["capture_defaults"]["explicit_theme"] is True
    assert session["capture_defaults"]["explicit_viewport"] is True


def test_build_live_demo_session_does_not_infer_launch_when_app_url_provided(tmp_path):
    repo_dir = tmp_path / "fixture_repo"
    repo_dir.mkdir()
    (repo_dir / "run_all.sh").write_text("#!/usr/bin/env bash\n")

    session = build_live_demo_session(
        target_repo_path=repo_dir,
        output_dir=tmp_path / "output",
        app_url="http://127.0.0.1:4317",
    )

    assert session["app_url"] == "http://127.0.0.1:4317"
    assert session["expected_url"] == "http://127.0.0.1:4317"
    assert session["launch_command"] == ""


def test_build_live_demo_session_requires_expected_url_when_launching_locally(tmp_path):
    repo_dir = tmp_path / "fixture_repo"
    repo_dir.mkdir()
    (repo_dir / "run_all.sh").write_text("#!/usr/bin/env bash\n")

    with pytest.raises(ValueError, match="expected_url"):
        build_live_demo_session(
            target_repo_path=repo_dir,
            output_dir=tmp_path / "output",
            launch_command="./run_all.sh",
        )


def test_build_live_demo_session_keeps_playwright_trace_only_when_requested(tmp_path):
    repo_dir = tmp_path / "fixture_repo"
    repo_dir.mkdir()

    session = build_live_demo_session(
        target_repo_path=repo_dir,
        output_dir=tmp_path / "output",
        app_url="http://127.0.0.1:4317",
        capture_driver="playwright",
    )

    assert session["capture_defaults"]["primary_driver"] == "playwright"
    assert session["capture_defaults"]["fallback_driver"] == ""
    assert session["capture_defaults"]["record_trace"] is True


def test_prepare_live_demo_session_accepts_hyphenated_desktop_use_driver(tmp_path):
    repo_dir = tmp_path / "fixture_repo"
    repo_dir.mkdir()
    output_dir = tmp_path / "output"

    completed = subprocess.run(
        [
            "python3",
            str(PREPARE_SCRIPT),
            "--target-repo-path",
            str(repo_dir),
            "--output-dir",
            str(output_dir),
            "--app-url",
            "http://127.0.0.1:4317",
            "--capture-driver",
            "desktop-use",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    session = json.loads(completed.stdout)
    assert session["capture_defaults"]["primary_driver"] == "desktop_use"
