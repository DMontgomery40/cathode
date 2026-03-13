from pathlib import Path

import core.voice_gen as voice_gen


def test_normalize_tts_text_does_not_special_case_brands():
    assert voice_gen._normalize_tts_text("Acme365 is massive") == "Acme365 is massive"
    assert voice_gen._normalize_tts_text("Acme365's platform") == "Acme365's platform"


def test_normalize_tts_text_spells_out_common_acronyms():
    assert voice_gen._normalize_tts_text("the word LLM matters") == "the word L.L.M. matters"
    assert voice_gen._normalize_tts_text("GraphRAG plus AI and MLOps") == "GraphRAG plus A.I. and M.L. ops"
    assert voice_gen._normalize_tts_text("MS SQL and HTTP on GCP") == "M.S. S.Q.L. and H.T.T.P. on G.C.P."


def test_generate_scene_audio_uses_project_defaults(monkeypatch, tmp_path):
    captured = {}

    def fake_generate_audio(text, output_path, **kwargs):
        captured["text"] = text
        captured["output_path"] = Path(output_path)
        captured["kwargs"] = kwargs
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(output_path).write_bytes(b"wav")
        return Path(output_path)

    monkeypatch.setattr(voice_gen, "generate_audio", fake_generate_audio)

    path = voice_gen.generate_scene_audio(
        {"id": 0, "narration": "Hello world."},
        tmp_path,
        tts_provider="kokoro",
        voice="af_bella",
        speed=1.1,
    )

    assert path.exists()
    assert captured["kwargs"]["tts_provider"] == "kokoro"
    assert captured["kwargs"]["voice"] == "af_bella"


def test_generate_scene_audio_honors_scene_voice_override(monkeypatch, tmp_path):
    captured = {}

    def fake_generate_audio(text, output_path, **kwargs):
        captured["text"] = text
        captured["output_path"] = Path(output_path)
        captured["kwargs"] = kwargs
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(output_path).write_bytes(b"wav")
        return Path(output_path)

    monkeypatch.setattr(voice_gen, "generate_audio", fake_generate_audio)
    monkeypatch.setattr(
        voice_gen,
        "available_tts_providers",
        lambda keys=None: {
            "kokoro": "Kokoro (Local)",
            "elevenlabs": "ElevenLabs (Cloud)",
        },
    )

    path = voice_gen.generate_scene_audio(
        {
            "id": 1,
            "narration": "Alan Reed speaks here.",
            "tts_override_enabled": True,
            "tts_provider": "elevenlabs",
            "tts_voice": "Bella",
            "tts_speed": 0.95,
            "elevenlabs_model_id": "eleven_multilingual_v2",
        },
        tmp_path,
        tts_provider="kokoro",
        voice="af_bella",
        speed=1.1,
    )

    assert path.exists()
    assert captured["kwargs"]["tts_provider"] == "elevenlabs"
    assert captured["kwargs"]["voice"] == "Bella"
    assert captured["kwargs"]["speed"] == 0.95


def test_generate_scene_audio_falls_back_when_scene_override_provider_is_unavailable(monkeypatch, tmp_path):
    captured = {}

    def fake_generate_audio(text, output_path, **kwargs):
        captured["text"] = text
        captured["output_path"] = Path(output_path)
        captured["kwargs"] = kwargs
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(output_path).write_bytes(b"wav")
        return Path(output_path)

    monkeypatch.setattr(voice_gen, "generate_audio", fake_generate_audio)
    monkeypatch.setattr(voice_gen, "available_tts_providers", lambda keys=None: {"kokoro": "Kokoro (Local)"})

    path = voice_gen.generate_scene_audio(
        {
            "id": 2,
            "narration": "Fallback to the project default voice.",
            "tts_override_enabled": True,
            "tts_provider": "elevenlabs",
            "tts_voice": "Bella",
            "tts_speed": 0.95,
        },
        tmp_path,
        tts_provider="kokoro",
        voice="af_bella",
        speed=1.1,
    )

    assert path.exists()
    assert captured["kwargs"]["tts_provider"] == "kokoro"
    assert captured["kwargs"]["voice"] == "af_bella"
    assert captured["kwargs"]["speed"] == 1.1


def test_generate_scene_audio_normalizes_voice_when_base_provider_falls_back_to_kokoro(monkeypatch, tmp_path):
    captured = {}

    def fake_generate_audio(text, output_path, **kwargs):
        captured["text"] = text
        captured["output_path"] = Path(output_path)
        captured["kwargs"] = kwargs
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(output_path).write_bytes(b"wav")
        return Path(output_path)

    monkeypatch.setattr(voice_gen, "generate_audio", fake_generate_audio)
    monkeypatch.setattr(voice_gen, "available_tts_providers", lambda keys=None: {"kokoro": "Kokoro (Local)"})

    path = voice_gen.generate_scene_audio(
        {"id": 3, "narration": "Use the local fallback voice."},
        tmp_path,
        tts_provider="elevenlabs",
        voice="Bella",
        speed=1.0,
    )

    assert path.exists()
    assert captured["kwargs"]["tts_provider"] == "kokoro"
    assert captured["kwargs"]["voice"] == "af_bella"


def test_generate_audio_falls_back_to_kokoro_when_elevenlabs_fails(monkeypatch, tmp_path):
    output_path = tmp_path / "audio.wav"

    def fail_elevenlabs(**kwargs):
        raise RuntimeError("401 Unauthorized")

    def fake_kokoro(text, output_path_arg, voice, speed):
        Path(output_path_arg).parent.mkdir(parents=True, exist_ok=True)
        Path(output_path_arg).write_bytes(b"wav")
        return Path(output_path_arg)

    monkeypatch.setattr(voice_gen, "_generate_with_elevenlabs", fail_elevenlabs)
    monkeypatch.setattr(voice_gen, "_generate_with_kokoro", fake_kokoro)

    path = voice_gen.generate_audio(
        "Hello world",
        output_path,
        voice="Bella",
        speed=1.0,
        tts_provider="elevenlabs",
    )

    assert path.exists()
    assert path.read_bytes() == b"wav"
