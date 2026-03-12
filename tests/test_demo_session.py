from __future__ import annotations

from pathlib import Path

from core.demo_session import build_live_demo_session


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
