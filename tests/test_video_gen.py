from __future__ import annotations

import shlex
import sys
from pathlib import Path

from core.runtime import available_video_generation_providers, resolve_video_profile
from core.video_gen import (
    build_scene_video_prompt,
    estimate_scene_duration_seconds,
    generate_scene_video,
    resolve_replicate_video_generation_route,
)


def test_resolve_video_profile_falls_back_without_local_backend(monkeypatch):
    monkeypatch.delenv("CATHODE_LOCAL_VIDEO_COMMAND", raising=False)
    monkeypatch.delenv("CATHODE_LOCAL_VIDEO_ENDPOINT", raising=False)
    monkeypatch.delenv("REPLICATE_API_TOKEN", raising=False)

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


def test_resolve_replicate_video_generation_route_prefers_speaking_when_clip_audio_is_enabled(monkeypatch):
    resolved = resolve_replicate_video_generation_route(
        {},
        model=None,
        model_selection_mode="automatic",
        generate_audio=True,
    )

    assert isinstance(resolved["model"], str)
    assert resolved["model"]
    assert resolved["route_kind"] == "speaking"


def test_resolve_replicate_video_generation_route_allows_scene_kind_to_force_cinematic(monkeypatch):
    resolved = resolve_replicate_video_generation_route(
        {"video_scene_kind": "cinematic"},
        model=None,
        model_selection_mode="automatic",
        generate_audio=True,
    )

    assert isinstance(resolved["model"], str)
    assert resolved["model"]
    assert resolved["route_kind"] == "cinematic"


def test_generate_scene_video_uses_replicate_backend_and_caps_duration(monkeypatch, tmp_path):
    captured: dict[str, object] = {}

    class _FakeClient:
        def run(self, model: str, input: dict[str, object]) -> str:
            captured["model"] = model
            captured["input"] = input
            return "https://example.com/generated.mp4"

    monkeypatch.setenv("REPLICATE_API_TOKEN", "test-token")
    monkeypatch.setattr("core.video_gen._get_replicate_client", lambda: _FakeClient())
    monkeypatch.setattr("core.video_gen.image_limiter.call_with_retry", lambda fn: fn())

    def _fake_download(url: str, output_path: Path, timeout_seconds: int) -> Path:
        output_path.write_bytes(b"replicate-mp4")
        return output_path

    monkeypatch.setattr("core.video_gen._download_video", _fake_download)

    path = generate_scene_video(
        {
            "id": 7,
            "title": "Scene 8",
            "narration": "One two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen twenty.",
            "visual_prompt": "A charismatic spokesperson in a bright dealership showroom.",
            "video_scene_kind": "cinematic",
            "on_screen_text": [],
        },
        tmp_path,
        provider="replicate",
        quality_mode="standard",
        generate_audio=True,
        duration_seconds=18.4,
    )

    assert path.exists()
    assert path.read_bytes() == b"replicate-mp4"
    assert isinstance(captured["model"], str)
    assert captured["model"]
    replicate_input = captured["input"]
    assert isinstance(replicate_input, dict)
    assert replicate_input["aspect_ratio"] == "16:9"
    assert replicate_input["duration"] == 15
    assert replicate_input["mode"] == "standard"
    assert replicate_input["generate_audio"] is True
    assert "dealership showroom" in str(replicate_input["prompt"])


def test_generate_scene_video_uses_speaking_route_when_clip_audio_is_enabled(monkeypatch, tmp_path):
    captured: dict[str, object] = {}

    class _FakeClient:
        def run(self, model: str, input: dict[str, object]) -> str:
            captured["model"] = model
            captured["input"] = input
            return "https://example.com/avatar.mp4"

    image_path = tmp_path / "images" / "speaker.png"
    image_path.parent.mkdir(parents=True, exist_ok=True)
    image_path.write_bytes(b"fake-image")
    audio_path = tmp_path / "audio" / "speaker.wav"
    audio_path.parent.mkdir(parents=True, exist_ok=True)
    audio_path.write_bytes(b"fake-audio")

    monkeypatch.setenv("REPLICATE_API_TOKEN", "test-token")
    monkeypatch.setattr("core.video_gen._get_replicate_client", lambda: _FakeClient())
    monkeypatch.setattr("core.video_gen.image_limiter.call_with_retry", lambda fn: fn())

    def _fake_download(url: str, output_path: Path, timeout_seconds: int) -> Path:
        output_path.write_bytes(b"avatar-mp4")
        return output_path

    monkeypatch.setattr("core.video_gen._download_video", _fake_download)

    path = generate_scene_video(
        {
            "id": 2,
            "title": "Scene 3",
            "narration": "Come visit our showroom this weekend.",
            "visual_prompt": "A welcoming dealership owner speaks directly to camera.",
            "image_path": str(image_path),
            "audio_path": str(audio_path),
            "on_screen_text": [],
        },
        tmp_path,
        provider="replicate",
        model_selection_mode="automatic",
        quality_mode="standard",
        generate_audio=True,
        image_provider="manual",
    )

    assert path.exists()
    assert path.read_bytes() == b"avatar-mp4"
    assert isinstance(captured["model"], str)
    assert captured["model"]
    replicate_input = captured["input"]
    assert isinstance(replicate_input, dict)
    assert replicate_input["mode"] == "std"
    assert "audio" in replicate_input
    assert "image" in replicate_input


def test_generate_scene_video_requires_replicate_token_for_cloud_provider(monkeypatch, tmp_path):
    monkeypatch.delenv("REPLICATE_API_TOKEN", raising=False)

    try:
        generate_scene_video(
            {
                "id": 0,
                "title": "Scene 1",
                "narration": "Short narration for the clip.",
                "visual_prompt": "A clean dashboard animation.",
                "on_screen_text": [],
            },
            tmp_path,
            provider="replicate",
        )
    except ValueError as exc:
        assert "REPLICATE_API_TOKEN" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("Expected replicate generation to require a token")
