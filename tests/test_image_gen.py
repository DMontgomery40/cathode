from core.image_gen import (
    DASHSCOPE_IMAGE_EDIT_MODELS,
    DEFAULT_REPLICATE_IMAGE_EDIT_MODEL,
    available_image_edit_models,
    default_image_edit_model,
)


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
