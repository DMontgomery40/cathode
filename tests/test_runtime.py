from pathlib import Path

from core.runtime import (
    available_tts_providers,
    available_video_generation_providers,
    check_api_keys,
    load_repo_env,
    remotion_capabilities,
    resolve_tts_profile,
    resolve_video_profile,
)


def test_resolve_tts_profile_rewrites_kokoro_voice_for_elevenlabs_provider(monkeypatch):
    monkeypatch.setattr(
        "core.runtime.available_tts_providers",
        lambda keys=None: {
            "kokoro": "Kokoro (Local)",
            "elevenlabs": "ElevenLabs (Cloud)",
        },
    )

    profile = resolve_tts_profile({"provider": "elevenlabs", "voice": "af_bella"})

    assert profile["provider"] == "elevenlabs"
    assert profile["voice"] == "Bella"


def test_resolve_tts_profile_rewrites_non_kokoro_voice_for_kokoro_provider(monkeypatch):
    monkeypatch.setattr(
        "core.runtime.available_tts_providers",
        lambda keys=None: {"kokoro": "Kokoro (Local)"},
    )

    profile = resolve_tts_profile({"provider": "kokoro", "voice": "Bella"})

    assert profile["provider"] == "kokoro"
    assert profile["voice"] == "af_bella"


def test_available_tts_providers_exposes_elevenlabs_when_only_replicate_is_configured():
    providers = available_tts_providers(
        {"openai": False, "anthropic": False, "replicate": True, "dashscope": False, "elevenlabs": False}
    )

    assert providers["elevenlabs"] == "ElevenLabs (Replicate)"


def test_resolve_video_profile_keeps_agent_provider():
    profile = resolve_video_profile({"provider": "agent", "generation_model": ""})

    assert profile["provider"] == "agent"


def test_available_video_generation_providers_includes_replicate_when_configured():
    providers = available_video_generation_providers(
        {"openai": False, "anthropic": False, "replicate": True, "dashscope": False, "elevenlabs": False}
    )

    assert "replicate" in providers


def test_resolve_video_profile_defaults_replicate_model_and_audio_settings(monkeypatch):
    monkeypatch.setattr(
        "core.runtime.check_api_keys",
        lambda: {"openai": False, "anthropic": False, "replicate": True, "dashscope": False, "elevenlabs": False},
    )

    profile = resolve_video_profile({"provider": "replicate", "generation_model": "", "quality_mode": "", "generate_audio": None})

    assert profile["provider"] == "replicate"
    assert isinstance(profile["generation_model"], str)
    assert profile["generation_model"]
    assert profile["model_selection_mode"] == "automatic"
    assert profile["quality_mode"] == "standard"
    assert profile["generate_audio"] is True


def test_resolve_video_profile_normalizes_model_selection_mode(monkeypatch):
    monkeypatch.setattr(
        "core.runtime.check_api_keys",
        lambda: {"openai": False, "anthropic": False, "replicate": True, "dashscope": False, "elevenlabs": False},
    )

    profile = resolve_video_profile(
        {"provider": "replicate", "generation_model": "wan/wan-2.1", "model_selection_mode": "ADVANCED"}
    )

    assert profile["provider"] == "replicate"
    assert profile["model_selection_mode"] == "advanced"


def test_remotion_capabilities_reports_player_transitions_and_three(monkeypatch, tmp_path):
    frontend_dir = tmp_path / "frontend"
    for pkg in (
        frontend_dir / "node_modules" / "remotion" / "package.json",
        frontend_dir / "node_modules" / "@remotion" / "renderer" / "package.json",
        frontend_dir / "node_modules" / "@remotion" / "player" / "package.json",
        frontend_dir / "node_modules" / "@remotion" / "transitions" / "package.json",
        frontend_dir / "node_modules" / "@remotion" / "three" / "package.json",
        frontend_dir / "node_modules" / "three" / "package.json",
        frontend_dir / "node_modules" / "@react-three" / "fiber" / "package.json",
        frontend_dir / "node_modules" / "@react-three" / "drei" / "package.json",
    ):
        pkg.parent.mkdir(parents=True, exist_ok=True)
        pkg.write_text("{}")
    (frontend_dir / "scripts").mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr("core.runtime.REPO_ROOT", tmp_path)
    monkeypatch.setattr("core.runtime.shutil.which", lambda value: "/usr/bin/node" if value == "node" else None)

    caps = remotion_capabilities()

    assert caps["render_available"] is True
    assert caps["player_available"] is True
    assert caps["transitions_available"] is True
    assert caps["three_available"] is True


def test_load_repo_env_populates_missing_provider_keys(tmp_path, monkeypatch):
    env_path = tmp_path / ".env"
    env_path.write_text(
        "REPLICATE_API_TOKEN=rep-token\nDASHSCOPE_API_KEY=dash-token\n",
        encoding="utf-8",
    )
    monkeypatch.delenv("REPLICATE_API_TOKEN", raising=False)
    monkeypatch.delenv("DASHSCOPE_API_KEY", raising=False)

    loaded = load_repo_env(env_path=env_path)

    assert loaded == Path(env_path).resolve()
    keys = check_api_keys()
    assert keys["replicate"] is True
    assert keys["dashscope"] is True
