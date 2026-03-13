from core.runtime import resolve_tts_profile, resolve_video_profile


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


def test_resolve_video_profile_keeps_agent_provider():
    profile = resolve_video_profile({"provider": "agent", "generation_model": ""})

    assert profile["provider"] == "agent"
