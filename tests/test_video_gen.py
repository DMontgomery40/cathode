from __future__ import annotations

import shlex
import sys

from core.runtime import available_video_generation_providers, resolve_video_profile
from core.video_gen import build_scene_video_prompt, estimate_scene_duration_seconds, generate_scene_video


def test_resolve_video_profile_falls_back_without_local_backend(monkeypatch):
    monkeypatch.delenv("CATHODE_LOCAL_VIDEO_COMMAND", raising=False)
    monkeypatch.delenv("CATHODE_LOCAL_VIDEO_ENDPOINT", raising=False)

    resolved = resolve_video_profile({"provider": "local", "generation_model": "/models/demo"})

    assert resolved["provider"] == "manual"
    assert available_video_generation_providers() == ["manual"]


def test_build_scene_video_prompt_includes_scene_and_brief_context():
    prompt = build_scene_video_prompt(
        {
            "title": "Intro",
            "narration": "Explain how the product works.",
            "visual_prompt": "Slow camera push across the product UI.",
            "on_screen_text": ["Fast setup", "Local render"],
        },
        {
            "visual_style": "clean editorial demo",
            "tone": "confident",
            "audience": "technical buyers",
        },
    )

    assert "Slow camera push across the product UI." in prompt
    assert "Narration context" in prompt
    assert "On-screen text guidance: Fast setup | Local render" in prompt
    assert "Visual style: clean editorial demo" in prompt


def test_estimate_scene_duration_seconds_uses_narration_length():
    scene = {"narration": "one two three four five six seven eight nine ten eleven twelve thirteen fourteen"}

    duration = estimate_scene_duration_seconds(scene)

    assert duration == 5.0


def test_generate_scene_video_uses_local_command_backend(monkeypatch, tmp_path):
    script = (
        "import os; "
        "from pathlib import Path; "
        "Path(os.environ['CATHODE_VIDEO_OUTPUT_PATH']).write_bytes(b'fake-mp4-bytes')"
    )
    monkeypatch.setenv("CATHODE_LOCAL_VIDEO_COMMAND", shlex.join([sys.executable, "-c", script]))
    monkeypatch.delenv("CATHODE_LOCAL_VIDEO_ENDPOINT", raising=False)
    monkeypatch.setenv("CATHODE_LOCAL_VIDEO_MODEL", "/models/local-video")

    path = generate_scene_video(
        {
            "id": 0,
            "title": "Scene 1",
            "narration": "Short narration for the clip.",
            "visual_prompt": "A clean dashboard animation.",
            "on_screen_text": [],
        },
        tmp_path,
        brief={"visual_style": "editorial demo"},
    )

    assert path.exists()
    assert path.name == "scene_000_generated.mp4"
    assert path.read_bytes() == b"fake-mp4-bytes"
