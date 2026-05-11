from pathlib import Path
import base64
import shlex
import sys
import types

import core.image_gen as image_gen
import core.runtime as runtime
from core.image_gen import (
    DASHSCOPE_IMAGE_EDIT_MODELS,
    DEFAULT_CODEX_IMAGE_MODEL,
    DEFAULT_OPENAI_IMAGE_EDIT_MODEL,
    DEFAULT_REPLICATE_IMAGE_EDIT_MODEL,
    available_image_edit_models,
    build_exact_text_edit_prompt,
    canonicalize_exact_text_edit_prompt,
    default_image_edit_model,
    edit_image,
    edit_image_codex_exec,
    generate_image_codex_exec,
    generate_image_local,
    generate_scene_image,
)
from core.runtime import available_image_generation_providers, resolve_image_profile


def test_default_image_edit_model_prefers_openai_when_configured(monkeypatch):
    monkeypatch.delenv("IMAGE_EDIT_PROVIDER", raising=False)
    monkeypatch.delenv("IMAGE_EDIT_MODEL", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("REPLICATE_API_TOKEN", "rep-token")
    monkeypatch.setenv("DASHSCOPE_API_KEY", "test-key")
    monkeypatch.delenv("ALIBABA_API_KEY", raising=False)

    assert default_image_edit_model() == DEFAULT_OPENAI_IMAGE_EDIT_MODEL


def test_default_image_edit_model_falls_back_to_replicate_without_openai(monkeypatch):
    monkeypatch.delenv("IMAGE_EDIT_PROVIDER", raising=False)
    monkeypatch.delenv("IMAGE_EDIT_MODEL", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("REPLICATE_API_TOKEN", "rep-token")
    monkeypatch.setenv("DASHSCOPE_API_KEY", "test-key")
    monkeypatch.delenv("ALIBABA_API_KEY", raising=False)

    assert default_image_edit_model() == DEFAULT_REPLICATE_IMAGE_EDIT_MODEL


def test_default_image_edit_model_respects_explicit_dashscope_provider(monkeypatch):
    monkeypatch.setenv("IMAGE_EDIT_PROVIDER", "dashscope")
    monkeypatch.delenv("IMAGE_EDIT_MODEL", raising=False)

    assert default_image_edit_model() == DASHSCOPE_IMAGE_EDIT_MODELS[0]


def test_available_image_edit_models_orders_public_default_first():
    assert available_image_edit_models(include_openai=True, include_replicate=True, include_dashscope=False) == [
        DEFAULT_OPENAI_IMAGE_EDIT_MODEL,
        DEFAULT_REPLICATE_IMAGE_EDIT_MODEL
    ]
    assert available_image_edit_models(include_openai=True, include_replicate=True, include_dashscope=True) == [
        DEFAULT_OPENAI_IMAGE_EDIT_MODEL,
        DEFAULT_REPLICATE_IMAGE_EDIT_MODEL,
        *DASHSCOPE_IMAGE_EDIT_MODELS,
    ]
    assert available_image_edit_models(include_openai=False, include_replicate=False, include_dashscope=True) == [
        *DASHSCOPE_IMAGE_EDIT_MODELS
    ]


def test_available_image_generation_providers_includes_local_when_configured(monkeypatch):
    monkeypatch.delenv("REPLICATE_API_TOKEN", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("CATHODE_LOCAL_IMAGE_MODEL", "Qwen/Qwen-Image-2512")
    monkeypatch.setattr(runtime, "_local_image_backend_runnable", lambda: True)
    monkeypatch.setattr(runtime.shutil, "which", lambda value: None)

    assert available_image_generation_providers() == ["local", "manual"]


def test_available_image_generation_providers_hides_local_when_backend_not_runnable(monkeypatch):
    monkeypatch.delenv("REPLICATE_API_TOKEN", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("CATHODE_LOCAL_IMAGE_MODEL", "Qwen/Qwen-Image-2512")
    monkeypatch.setattr(runtime, "_local_image_backend_runnable", lambda: False)
    monkeypatch.setattr(runtime.shutil, "which", lambda value: None)

    assert available_image_generation_providers() == ["manual"]


def test_available_image_generation_providers_prefers_codex_when_openai_and_cli_are_available(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.delenv("REPLICATE_API_TOKEN", raising=False)
    monkeypatch.delenv("CATHODE_LOCAL_IMAGE_MODEL", raising=False)
    monkeypatch.setattr(runtime, "_local_image_backend_runnable", lambda: False)
    monkeypatch.setattr(runtime.shutil, "which", lambda value: "/usr/local/bin/codex" if value == "codex" else None)

    assert available_image_generation_providers() == ["codex", "manual"]


def test_resolve_image_profile_keeps_explicit_local_model_when_backend_is_runnable(monkeypatch):
    monkeypatch.delenv("REPLICATE_API_TOKEN", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("CATHODE_LOCAL_IMAGE_MODEL", raising=False)
    monkeypatch.setattr(runtime, "_local_image_backend_runnable", lambda: True)
    monkeypatch.setattr(runtime.shutil, "which", lambda value: None)

    resolved = resolve_image_profile(
        {"provider": "local", "generation_model": "Qwen/Qwen-Image-2512"}
    )

    assert resolved["provider"] == "local"
    assert resolved["generation_model"] == "Qwen/Qwen-Image-2512"


def test_resolve_image_profile_falls_back_when_local_backend_is_not_runnable(monkeypatch):
    monkeypatch.delenv("REPLICATE_API_TOKEN", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("CATHODE_LOCAL_IMAGE_MODEL", raising=False)
    monkeypatch.setattr(runtime, "_local_image_backend_runnable", lambda: False)
    monkeypatch.setattr(runtime.shutil, "which", lambda value: None)

    resolved = resolve_image_profile(
        {"provider": "local", "generation_model": "Qwen/Qwen-Image-2512"}
    )

    assert resolved["provider"] == "manual"


def test_resolve_image_profile_prefers_codex_defaults_when_available(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.delenv("REPLICATE_API_TOKEN", raising=False)
    monkeypatch.delenv("CATHODE_LOCAL_IMAGE_MODEL", raising=False)
    monkeypatch.setattr(runtime, "_local_image_backend_runnable", lambda: False)
    monkeypatch.setattr(runtime.shutil, "which", lambda value: "/usr/local/bin/codex" if value == "codex" else None)

    resolved = resolve_image_profile()

    assert resolved["provider"] == "codex"
    assert resolved["generation_model"] == "gpt-image-2"


def test_resolve_image_profile_falls_back_from_codex_to_replicate(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("REPLICATE_API_TOKEN", "rep-token")
    monkeypatch.delenv("CATHODE_LOCAL_IMAGE_MODEL", raising=False)
    monkeypatch.setattr(runtime, "_local_image_backend_runnable", lambda: False)
    monkeypatch.setattr(runtime.shutil, "which", lambda value: None)

    resolved = resolve_image_profile({"provider": "codex", "generation_model": "gpt-image-2"})

    assert resolved["provider"] == "replicate"
    assert resolved["generation_model"] == "qwen/qwen-image-2512"


def test_generate_scene_image_uses_local_backend(monkeypatch, tmp_path):
    captured: dict[str, str] = {}

    def fake_generate_image_local(prompt, output_path, model, apply_style=True, seed=None, brief=None):
        captured["prompt"] = prompt
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(output_path).write_bytes(b"fake-local-image")
        return Path(output_path)

    monkeypatch.setattr(image_gen, "generate_image_local", fake_generate_image_local)

    result = generate_scene_image(
        {"id": 0, "visual_prompt": "A clean product still."},
        tmp_path,
        provider="local",
        model="Qwen/Qwen-Image-2512",
    )

    assert result.exists()
    assert result.read_bytes() == b"fake-local-image"
    assert captured["prompt"] == "A clean product still."


def test_generate_scene_image_uses_codex_backend(monkeypatch, tmp_path):
    captured: dict[str, str] = {}

    def fake_generate_image_codex_exec(prompt, output_path, model, apply_style=True, seed=None, brief=None):
        captured["prompt"] = prompt
        captured["model"] = model
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(output_path).write_bytes(b"fake-codex-image")
        return Path(output_path)

    monkeypatch.setattr(image_gen, "generate_image_codex_exec", fake_generate_image_codex_exec)

    result = generate_scene_image(
        {"id": 0, "visual_prompt": "A precise editorial still."},
        tmp_path,
        provider="codex",
        model=DEFAULT_CODEX_IMAGE_MODEL,
    )

    assert result.exists()
    assert result.read_bytes() == b"fake-codex-image"
    assert captured["prompt"] == "A precise editorial still."
    assert captured["model"] == DEFAULT_CODEX_IMAGE_MODEL


def test_generate_image_codex_exec_runs_helper_through_local_codex(monkeypatch, tmp_path):
    output_path = tmp_path / "scene.png"
    seen: dict[str, object] = {}
    helper_python = "/opt/cathode python/bin/python3"

    def fake_run(command, *, input, text, capture_output, check):
        seen["command"] = command
        seen["input"] = input
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"fake-codex-image")
        result_path = Path(command[command.index("-o") + 1])
        result_path.write_text(
            '{"status":"succeeded","provider":"codex","model":"gpt-image-2","output_path":"' + str(output_path) + '"}',
            encoding="utf-8",
        )
        return image_gen.subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr(image_gen.shutil, "which", lambda value: "/usr/local/bin/codex" if value == "codex" else None)
    monkeypatch.setattr(image_gen.sys, "executable", helper_python)
    monkeypatch.setattr(image_gen.subprocess, "run", fake_run)

    result = generate_image_codex_exec(
        "A cinematic still of a product reveal.",
        output_path,
        model="gpt-image-2",
    )

    command = seen["command"]
    assert isinstance(command, list)
    assert command[:2] == ["/usr/local/bin/codex", "exec"]
    assert "--ephemeral" in command
    assert "-o" in command
    assert str(seen["input"]).splitlines()[3].startswith(shlex.quote(helper_python))
    assert "generate_openai_image.py" in str(seen["input"])
    assert "--model gpt-image-2" in str(seen["input"])
    assert result == output_path


def test_edit_image_codex_exec_runs_helper_through_local_codex(monkeypatch, tmp_path):
    input_path = tmp_path / "input.png"
    output_path = tmp_path / "scene.png"
    input_path.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 32)
    seen: dict[str, object] = {}
    helper_python = "/opt/cathode python/bin/python3"

    def fake_run(command, *, input, text, capture_output, check):
        seen["command"] = command
        seen["input"] = input
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"fake-codex-edited-image")
        result_path = Path(command[command.index("-o") + 1])
        result_path.write_text(
            '{"status":"succeeded","provider":"codex","model":"gpt-image-2","output_path":"' + str(output_path) + '"}',
            encoding="utf-8",
        )
        return image_gen.subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr(image_gen.shutil, "which", lambda value: "/usr/local/bin/codex" if value == "codex" else None)
    monkeypatch.setattr(image_gen.sys, "executable", helper_python)
    monkeypatch.setattr(image_gen.subprocess, "run", fake_run)

    result = edit_image_codex_exec(
        "update the visible treatment name to LUMIT",
        input_path,
        output_path,
        model="gpt-image-2",
    )

    command = seen["command"]
    assert isinstance(command, list)
    assert command[:2] == ["/usr/local/bin/codex", "exec"]
    assert "--ephemeral" in command
    assert str(seen["input"]).splitlines()[3].startswith(shlex.quote(helper_python))
    assert "edit_openai_image.py" in str(seen["input"])
    assert "--input-image" in str(seen["input"])
    assert "--model gpt-image-2" in str(seen["input"])
    assert result == output_path


def test_edit_image_gpt_image_prefers_codex_when_available(monkeypatch, tmp_path):
    input_path = tmp_path / "input.png"
    output_path = tmp_path / "edited.png"
    input_path.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 32)
    captured: dict[str, object] = {}

    def fake_codex(prompt, input_image_path, output_path_arg, model):
        captured["prompt"] = prompt
        captured["input_image_path"] = input_image_path
        captured["model"] = model
        Path(output_path_arg).write_bytes(b"codex-edited")
        return Path(output_path_arg)

    monkeypatch.setattr(image_gen.shutil, "which", lambda value: "/usr/local/bin/codex" if value == "codex" else None)
    monkeypatch.setattr(image_gen, "edit_image_codex_exec", fake_codex)

    result = edit_image("make it warmer", input_path, output_path, model="gpt-image-2")

    assert result == output_path
    assert captured["model"] == "gpt-image-2"
    assert captured["prompt"] == "make it warmer"


def test_edit_image_gpt_image_falls_back_to_openai_api_without_codex(monkeypatch, tmp_path):
    input_path = tmp_path / "input.png"
    output_path = tmp_path / "edited.png"
    input_path.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 32)
    captured: dict[str, object] = {}

    class FakeImages:
        def edit(self, **kwargs):
            captured.update(kwargs)
            return types.SimpleNamespace(
                data=[
                    types.SimpleNamespace(
                        b64_json=base64.b64encode(b"openai-edited").decode("ascii")
                    )
                ]
            )

    class FakeClient:
        images = FakeImages()

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(image_gen.shutil, "which", lambda value: None)
    monkeypatch.setitem(sys.modules, "openai", types.SimpleNamespace(OpenAI=lambda: FakeClient()))
    monkeypatch.setattr(image_gen.image_limiter, "call_with_retry", lambda callback: callback())

    result = edit_image("make it warmer", input_path, output_path, model="gpt-image-2")

    assert result == output_path
    assert output_path.read_bytes() == b"openai-edited"
    assert captured["model"] == "gpt-image-2"
    assert captured["size"] == image_gen.TARGET_SIZE_OPENAI
    assert captured["output_format"] == "png"


def test_edit_image_gpt_image_falls_back_to_openai_api_when_codex_fails(monkeypatch, tmp_path):
    input_path = tmp_path / "input.png"
    output_path = tmp_path / "edited.png"
    input_path.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 32)
    captured: dict[str, object] = {}

    class FakeImages:
        def edit(self, **kwargs):
            captured.update(kwargs)
            return types.SimpleNamespace(
                data=[
                    types.SimpleNamespace(
                        b64_json=base64.b64encode(b"openai-edited").decode("ascii")
                    )
                ]
            )

    class FakeClient:
        images = FakeImages()

    def fail_codex(*args, **kwargs):
        raise RuntimeError("codex auth unavailable")

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(image_gen.shutil, "which", lambda value: "/usr/local/bin/codex" if value == "codex" else None)
    monkeypatch.setattr(image_gen, "edit_image_codex_exec", fail_codex)
    monkeypatch.setitem(sys.modules, "openai", types.SimpleNamespace(OpenAI=lambda: FakeClient()))
    monkeypatch.setattr(image_gen.image_limiter, "call_with_retry", lambda callback: callback())

    result = edit_image("make it warmer", input_path, output_path, model="gpt-image-2")

    assert result == output_path
    assert output_path.read_bytes() == b"openai-edited"
    assert captured["model"] == "gpt-image-2"


def test_generate_scene_image_preserves_raw_prompt_for_authored_image_scene(monkeypatch, tmp_path):
    captured: dict[str, str] = {}

    def fake_generate_image_local(prompt, output_path, model, apply_style=True, seed=None, brief=None):
        captured["prompt"] = prompt
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(output_path).write_bytes(b"fake-local-image")
        return Path(output_path)

    monkeypatch.setattr(image_gen, "generate_image_local", fake_generate_image_local)

    generate_scene_image(
        {
            "id": 3,
            "scene_type": "authored_image",
            "visual_prompt": '  Deep navy background with waveform panels labeled "Session 1" and "Session 3".  ',
            "composition": {
                "family": "three_data_stage",
                "mode": "overlay",
            },
        },
        tmp_path,
        provider="local",
        model="Qwen/Qwen-Image-2512",
    )

    assert captured["prompt"] == '  Deep navy background with waveform panels labeled "Session 1" and "Session 3".  '


def test_generate_scene_image_preserves_authored_prompt_for_ordinary_slides(monkeypatch, tmp_path):
    captured: dict[str, str] = {}

    def fake_generate_image_local(prompt, output_path, model, apply_style=True, seed=None, brief=None):
        captured["prompt"] = prompt
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(output_path).write_bytes(b"fake-local-image")
        return Path(output_path)

    monkeypatch.setattr(image_gen, "generate_image_local", fake_generate_image_local)

    generate_scene_image(
        {
            "id": 1,
            "visual_prompt": "Warm illustrated scene with three circular icons.",
            "composition": {"family": "static_media", "mode": "none"},
            "on_screen_text": ["Three Snapshots, Seven Weeks"],
        },
        tmp_path,
        provider="local",
        model="Qwen/Qwen-Image-2512",
    )

    prompt = captured["prompt"]
    assert prompt == "Warm illustrated scene with three circular icons."


def test_generate_image_passes_raw_prompt_without_style_suffix(monkeypatch, tmp_path):
    captured: dict[str, str] = {}

    class FakeClient:
        def run(self, model, input):
            captured["model"] = model
            captured["prompt"] = input["prompt"]
            return "https://example.com/image.png"

    class FakeResponse:
        status_code = 200
        content = b"fake-image"

        def raise_for_status(self):
            return None

    monkeypatch.setattr(image_gen, "_get_replicate_client", lambda: FakeClient())
    monkeypatch.setattr(image_gen.image_limiter, "call_with_retry", lambda fn: fn())
    monkeypatch.setattr(image_gen.requests, "get", lambda url, timeout: FakeResponse())
    monkeypatch.setattr(image_gen, "_ensure_png", lambda path: path)

    result = image_gen.generate_image(
        "Anthropic-authored prompt",
        tmp_path / "scene.png",
        brief={"visual_style": "cinematic illustration", "tone": "warm"},
    )

    assert result.exists()
    assert result.read_bytes() == b"fake-image"
    assert captured["model"] == image_gen.DEFAULT_IMAGE_MODEL
    assert captured["prompt"] == "Anthropic-authored prompt"


def test_generate_image_local_passes_raw_prompt_without_style_suffix(monkeypatch, tmp_path):
    captured: dict[str, object] = {}

    def fake_generate_local_image(*, prompt, output_path, model, width, height, seed):
        captured["prompt"] = prompt
        captured["model"] = model
        captured["width"] = width
        captured["height"] = height
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(output_path).write_bytes(b"fake-local-image")
        return Path(output_path)

    monkeypatch.setattr(image_gen, "generate_local_image", fake_generate_local_image)

    result = generate_image_local(
        "Anthropic-authored prompt",
        tmp_path / "scene.png",
        brief={"visual_style": "cinematic illustration", "tone": "warm"},
    )

    assert result.exists()
    assert result.read_bytes() == b"fake-local-image"
    assert captured["prompt"] == "Anthropic-authored prompt"
    assert captured["model"] == image_gen.DEFAULT_LOCAL_IMAGE_MODEL
    assert captured["width"] == image_gen.TARGET_WIDTH
    assert captured["height"] == image_gen.TARGET_HEIGHT


def test_canonicalize_exact_text_edit_prompt_rebuilds_literal_template():
    assert canonicalize_exact_text_edit_prompt(' Change   "teh"   to   "the" ') == 'change "teh" to "the"'
    assert build_exact_text_edit_prompt("bad", "good") == 'change "bad" to "good"'
    assert canonicalize_exact_text_edit_prompt("Make the image more cinematic") is None
