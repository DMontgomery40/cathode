import base64
import json
import wave
from pathlib import Path
from types import SimpleNamespace

import core.voice_gen as voice_gen


def _fake_audio_result(captured):
    def fake_generate_audio_result(text, output_path, **kwargs):
        output_path = Path(output_path)
        captured["text"] = text
        captured["output_path"] = output_path
        captured["kwargs"] = kwargs
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"wav")
        return {"path": output_path, "provider": kwargs["tts_provider"], "model": "test-model", "voice": kwargs["voice"]}

    return fake_generate_audio_result


def test_normalize_tts_text_does_not_special_case_brands():
    assert voice_gen._normalize_tts_text("Acme365 is massive") == "Acme365 is massive"
    assert voice_gen._normalize_tts_text("Acme365's platform") == "Acme365's platform"


def test_normalize_tts_text_spells_out_common_acronyms():
    assert voice_gen._normalize_tts_text("the word LLM matters") == "the word L.L.M. matters"
    assert voice_gen._normalize_tts_text("GraphRAG plus AI and MLOps") == "GraphRAG plus A.I. and M.L. ops"
    assert voice_gen._normalize_tts_text("MS SQL and HTTP on GCP") == "M.S. S.Q.L. and H.T.T.P. on G.C.P."


def test_generate_scene_audio_uses_project_defaults(monkeypatch, tmp_path):
    captured = {}

    monkeypatch.setattr(voice_gen, "generate_audio_result", _fake_audio_result(captured))

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

    monkeypatch.setattr(voice_gen, "generate_audio_result", _fake_audio_result(captured))
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

    monkeypatch.setattr(voice_gen, "generate_audio_result", _fake_audio_result(captured))
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

    monkeypatch.setattr(voice_gen, "generate_audio_result", _fake_audio_result(captured))
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
    monkeypatch.setattr(voice_gen, "_generate_with_replicate_elevenlabs", fail_elevenlabs)
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


def test_generate_audio_falls_back_to_replicate_hosted_elevenlabs_before_kokoro(monkeypatch, tmp_path):
    output_path = tmp_path / "audio.wav"

    def fail_elevenlabs(**kwargs):
        raise RuntimeError("401 Unauthorized")

    def fake_replicate(**kwargs):
        Path(kwargs["output_path"]).parent.mkdir(parents=True, exist_ok=True)
        Path(kwargs["output_path"]).write_bytes(b"replicate-wav")
        return Path(kwargs["output_path"])

    def fail_kokoro(*args, **kwargs):  # pragma: no cover - should not be reached
        raise AssertionError("Kokoro fallback should not run when Replicate ElevenLabs succeeds")

    monkeypatch.setattr(voice_gen, "_generate_with_elevenlabs", fail_elevenlabs)
    monkeypatch.setattr(voice_gen, "_generate_with_replicate_elevenlabs", fake_replicate)
    monkeypatch.setattr(voice_gen, "_generate_with_kokoro", fail_kokoro)

    path = voice_gen.generate_audio(
        "Hello world",
        output_path,
        voice="Bella",
        speed=1.0,
        tts_provider="elevenlabs",
    )

    assert path.exists()
    assert path.read_bytes() == b"replicate-wav"


def test_normalize_voice_for_replicate_elevenlabs_maps_curated_names():
    assert voice_gen._normalize_voice_for_replicate_elevenlabs("Bella") == "Sarah"
    assert voice_gen._normalize_voice_for_replicate_elevenlabs("Domi") == "Domi"
    assert voice_gen._normalize_voice_for_replicate_elevenlabs("Unknown Voice") == "Rachel"


def test_openai_tts_defaults_to_current_model_and_recommended_voice(monkeypatch, tmp_path):
    captured = {}

    class FakeSpeech:
        def create(self, **kwargs):
            captured.update(kwargs)

            class Response:
                def stream_to_file(self, path):
                    Path(path).write_bytes(b"mp3")

            return Response()

    class FakeClient:
        audio = SimpleNamespace(speech=FakeSpeech())

    monkeypatch.setattr(voice_gen.openai_limiter, "call_with_retry", lambda func: func())
    monkeypatch.setattr("openai.OpenAI", lambda: FakeClient())
    monkeypatch.setattr(voice_gen, "_convert_mp3_to_wav", lambda mp3_path, wav_path: Path(wav_path).write_bytes(b"wav"))

    path = voice_gen.generate_audio(
        "Hello world",
        tmp_path / "scene.wav",
        tts_provider="openai",
    )

    assert path.exists()
    assert captured["model"] == "gpt-4o-mini-tts"
    assert captured["voice"] == "marin"
    assert captured["response_format"] == "mp3"


def test_openai_realtime_voice_uses_gpt_realtime_2_websocket(monkeypatch, tmp_path):
    sent_events = []
    pcm_chunk = (0).to_bytes(2, "little", signed=True) * 240

    class FakeRealtimeConnection:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def send(self, payload):
            sent_events.append(json.loads(payload))

        def recv(self, timeout=None):
            return json.dumps(self._events.pop(0))

        _events = [
            {"type": "session.updated"},
            {"type": "response.output_audio.delta", "delta": base64.b64encode(pcm_chunk).decode("ascii")},
            {"type": "response.done"},
        ]

    captured_connect = {}

    def fake_connect(url, **kwargs):
        captured_connect["url"] = url
        captured_connect["kwargs"] = kwargs
        return FakeRealtimeConnection()

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(voice_gen.openai_limiter, "call_with_retry", lambda func: func())
    monkeypatch.setattr("websockets.sync.client.connect", fake_connect)

    result = voice_gen.generate_audio_result(
        "Read this narration.",
        tmp_path / "scene.wav",
        tts_provider="openai_realtime",
        voice="nova",
        openai_model_id="gpt-4o-mini-tts",
    )

    assert result["provider"] == "openai"
    assert result["model"] == "gpt-realtime-2"
    assert result["voice"] == "marin"
    assert "model=gpt-realtime-2" in captured_connect["url"]
    assert captured_connect["kwargs"]["additional_headers"]["Authorization"] == "Bearer test-key"
    assert sent_events[0]["type"] == "session.update"
    assert sent_events[0]["session"]["model"] == "gpt-realtime-2"
    assert sent_events[0]["session"]["audio"]["output"]["voice"] == "marin"
    assert sent_events[0]["session"]["audio"]["output"]["format"] == {"type": "audio/pcm", "rate": 24000}
    assert sent_events[1]["type"] == "conversation.item.create"
    assert sent_events[2]["response"]["output_modalities"] == ["audio"]

    with wave.open(str(result["path"]), "rb") as wav_file:
        assert wav_file.getframerate() == 24000
        assert wav_file.getnchannels() == 1
        assert wav_file.getsampwidth() == 2
        assert wav_file.readframes(240) == pcm_chunk
