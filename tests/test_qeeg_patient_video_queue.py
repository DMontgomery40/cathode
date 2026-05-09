from __future__ import annotations

import json
import subprocess

from scripts import qeeg_patient_video_queue as queue


def test_qeeg_queue_brief_locks_gpt_image2_static_ffmpeg(tmp_path):
    project_dir = tmp_path / "05-13-1947-0"
    project_dir.mkdir()
    source_path = project_dir / "qeeg_council_source.md"
    source_path.write_text("# Council\nStage 4 consolidation", encoding="utf-8")
    (project_dir / "qeeg_handoff_payload.json").write_text(
        json.dumps({"source_paths": [str(source_path)], "audience": "patient"}),
        encoding="utf-8",
    )

    brief = queue.build_brief("05-13-1947-0", project_dir, target_minutes=6.5)

    assert queue.IMAGE_PROFILE["provider"] == "codex"
    assert queue.IMAGE_PROFILE["generation_model"] == "gpt-image-2"
    assert queue.RENDER_PROFILE["render_backend"] == "ffmpeg"
    assert queue.RENDER_PROFILE["scene_types"] == ["image"]
    assert brief["target_length_minutes"] == 6.5
    assert brief["visual_source_strategy"] == "images_only"
    assert "no Remotion" in brief["raw_brief"]


def test_qeeg_queue_refreshes_older_image_or_story_provider(monkeypatch, tmp_path):
    project_dir = tmp_path / "05-13-1947-0"
    plan = {
        "meta": {
            "brief": {"target_length_minutes": 6.5},
            "creative_llm_provider": "anthropic",
            "image_profile": {"provider": "replicate", "generation_model": "qwen/qwen-image-2512"},
            "video_profile": {"provider": "manual"},
        },
        "scenes": [],
    }
    monkeypatch.setattr(queue, "load_plan", lambda _project_dir: plan)

    assert queue.plan_needs_storyboard_refresh(project_dir, minimum_target_minutes=6.5) is True


def test_qeeg_queue_fails_closed_when_codex_image_lane_unavailable(monkeypatch):
    monkeypatch.setattr(queue, "codex_image_generation_available", lambda: False)

    try:
        queue.require_locked_image_generation_lane()
    except RuntimeError as exc:
        assert "Codex Exec + gpt-image-2" in str(exc)
        assert "OPENAI_API_KEY" in str(exc)
    else:
        raise AssertionError("qEEG queue did not fail closed when Codex image generation was unavailable")


def test_force_static_image_plan_removes_video_and_native_render_paths():
    plan = {
        "meta": {},
        "scenes": [
            {
                "scene_type": "motion",
                "video_path": "clips/scene-1.mp4",
                "manifestation_plan": {
                    "primary_path": "native_remotion",
                    "fallback_path": "source_video",
                    "native_family_hint": "three_data_stage",
                    "native_build_prompt": "make an overlay",
                },
            }
        ],
    }

    clamped = queue.force_static_image_plan(plan)
    scene = clamped["scenes"][0]

    assert scene["scene_type"] == "image"
    assert scene["video_path"] is None
    assert scene["motion"] is None
    assert scene["composition"]["mode"] == "none"
    assert scene["manifestation_plan"]["primary_path"] == "authored_image"
    assert scene["manifestation_plan"]["fallback_path"] == "authored_image"
    assert clamped["meta"]["render_profile"]["render_backend"] == "ffmpeg"
    assert clamped["meta"]["image_profile"]["generation_model"] == "gpt-image-2"


def test_sync_video_to_qeeg_portal_copies_mp4_and_meta(monkeypatch, tmp_path):
    qeeq_repo = tmp_path / "qEEG-analysis"
    monkeypatch.setattr(queue, "QEEG_REPO", qeeq_repo)
    source = tmp_path / "render.mp4"
    source.write_bytes(b"mp4")

    result = queue.sync_video_to_qeeg_portal("05-13-1947-0", str(source))

    target = qeeq_repo / "data" / "portal_patients" / "05-13-1947-0" / "05-13-1947-0.mp4"
    meta = qeeq_repo / "data" / "portal_patients" / "05-13-1947-0" / "05-13-1947-0__cathode_video.json"
    assert result["status"] == "copied"
    assert target.read_bytes() == b"mp4"
    assert json.loads(meta.read_text(encoding="utf-8"))["image_model"] == "gpt-image-2"


def test_sync_patient_to_thrylen_uses_qeeg_portal_sync(monkeypatch, tmp_path):
    qeeq_repo = tmp_path / "qEEG-analysis"
    (qeeq_repo / "backend").mkdir(parents=True)
    (qeeq_repo / "backend" / "portal_sync.py").write_text("", encoding="utf-8")
    python_path = qeeq_repo / ".venv" / "bin" / "python"
    python_path.parent.mkdir(parents=True)
    python_path.write_text("", encoding="utf-8")
    monkeypatch.setattr(queue, "QEEG_REPO", qeeq_repo)
    captured = {}

    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        captured["kwargs"] = kwargs
        return subprocess.CompletedProcess(cmd, 0, stdout="ok", stderr="")

    monkeypatch.setattr(queue.subprocess, "run", fake_run)

    result = queue.sync_patient_to_thrylen("05-13-1947-0")

    assert result["status"] == "complete"
    assert captured["cmd"][1:4] == ["-m", "backend.portal_sync", "--patient-label"]
    assert captured["cmd"][4] == "05-13-1947-0"
    assert captured["kwargs"]["cwd"] == str(qeeq_repo)


def test_register_video_as_qeeg_patient_file_uses_qeeg_helper(monkeypatch, tmp_path):
    qeeq_repo = tmp_path / "qEEG-analysis"
    register_script = qeeq_repo / "scripts" / "register_patient_file.py"
    register_script.parent.mkdir(parents=True)
    register_script.write_text("", encoding="utf-8")
    python_path = qeeq_repo / ".venv" / "bin" / "python"
    python_path.parent.mkdir(parents=True)
    python_path.write_text("", encoding="utf-8")
    video = tmp_path / "render.mp4"
    video.write_bytes(b"mp4")
    monkeypatch.setattr(queue, "QEEG_REPO", qeeq_repo)
    captured = {}

    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        captured["kwargs"] = kwargs
        return subprocess.CompletedProcess(cmd, 0, stdout="ok", stderr="")

    monkeypatch.setattr(queue.subprocess, "run", fake_run)

    result = queue.register_video_as_qeeg_patient_file("05-13-1947-0", str(video))

    assert result["status"] == "complete"
    assert captured["cmd"][1] == str(register_script)
    assert captured["cmd"][2:4] == ["--patient-label", "05-13-1947-0"]
    assert captured["cmd"][4:6] == ["--src", str(video)]
    assert captured["cmd"][6:10] == ["--filename", "05-13-1947-0.mp4", "--mime-type", "video/mp4"]
    assert captured["kwargs"]["cwd"] == str(qeeq_repo)
