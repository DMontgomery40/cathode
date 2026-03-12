from pathlib import Path

import core.image_gen as image_gen
import core.runtime as runtime
from core.image_gen import (
    DASHSCOPE_IMAGE_EDIT_MODELS,
    DEFAULT_REPLICATE_IMAGE_EDIT_MODEL,
    available_image_edit_models,
    default_image_edit_model,
    generate_scene_image,
)
from core.runtime import available_image_generation_providers, resolve_image_profile


def test_default_image_edit_model_prefers_replicate_even_when_dashscope_key_exists(monkeypatch):
    monkeypatch.delenv("IMAGE_EDIT_PROVIDER", raising=False)
    monkeypatch.delenv("IMAGE_EDIT_MODEL", raising=False)
    monkeypatch.setenv("DASHSCOPE_API_KEY", "test-key")
    monkeypatch.delenv("ALIBABA_API_KEY", raising=False)

    assert default_image_edit_model() == DEFAULT_REPLICATE_IMAGE_EDIT_MODEL


def test_default_image_edit_model_respects_explicit_dashscope_provider(monkeypatch):
    monkeypatch.setenv("IMAGE_EDIT_PROVIDER", "dashscope")
    monkeypatch.delenv("IMAGE_EDIT_MODEL", raising=False)

    assert default_image_edit_model() == DASHSCOPE_IMAGE_EDIT_MODELS[0]


def test_available_image_edit_models_orders_public_default_first():
    assert available_image_edit_models(include_replicate=True, include_dashscope=False) == [
        DEFAULT_REPLICATE_IMAGE_EDIT_MODEL
    ]
    assert available_image_edit_models(include_replicate=True, include_dashscope=True) == [
        DEFAULT_REPLICATE_IMAGE_EDIT_MODEL,
        *DASHSCOPE_IMAGE_EDIT_MODELS,
    ]
    assert available_image_edit_models(include_replicate=False, include_dashscope=True) == [
        *DASHSCOPE_IMAGE_EDIT_MODELS
    ]


def test_available_image_generation_providers_includes_local_when_configured(monkeypatch):
    monkeypatch.delenv("REPLICATE_API_TOKEN", raising=False)
    monkeypatch.setenv("CATHODE_LOCAL_IMAGE_MODEL", "Qwen/Qwen-Image-2512")
    monkeypatch.setattr(runtime, "_local_image_backend_runnable", lambda: True)

    assert available_image_generation_providers() == ["local", "manual"]


def test_available_image_generation_providers_hides_local_when_backend_not_runnable(monkeypatch):
    monkeypatch.delenv("REPLICATE_API_TOKEN", raising=False)
    monkeypatch.setenv("CATHODE_LOCAL_IMAGE_MODEL", "Qwen/Qwen-Image-2512")
    monkeypatch.setattr(runtime, "_local_image_backend_runnable", lambda: False)

    assert available_image_generation_providers() == ["manual"]


def test_resolve_image_profile_keeps_explicit_local_model_when_backend_is_runnable(monkeypatch):
    monkeypatch.delenv("REPLICATE_API_TOKEN", raising=False)
    monkeypatch.delenv("CATHODE_LOCAL_IMAGE_MODEL", raising=False)
    monkeypatch.setattr(runtime, "_local_image_backend_runnable", lambda: True)

    resolved = resolve_image_profile(
        {"provider": "local", "generation_model": "Qwen/Qwen-Image-2512"}
    )

    assert resolved["provider"] == "local"
    assert resolved["generation_model"] == "Qwen/Qwen-Image-2512"


def test_resolve_image_profile_falls_back_when_local_backend_is_not_runnable(monkeypatch):
    monkeypatch.delenv("REPLICATE_API_TOKEN", raising=False)
    monkeypatch.delenv("CATHODE_LOCAL_IMAGE_MODEL", raising=False)
    monkeypatch.setattr(runtime, "_local_image_backend_runnable", lambda: False)

    resolved = resolve_image_profile(
        {"provider": "local", "generation_model": "Qwen/Qwen-Image-2512"}
    )

    assert resolved["provider"] == "manual"


def test_generate_scene_image_uses_local_backend(monkeypatch, tmp_path):
    def fake_generate_image_local(prompt, output_path, model, apply_style=True, seed=None, brief=None):
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
