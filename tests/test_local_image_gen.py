from pathlib import Path

import core.local_image_gen as local_image_gen


def test_resolve_local_image_backend_prefers_torch_when_requested(monkeypatch):
    monkeypatch.setenv("CATHODE_LOCAL_IMAGE_RUNTIME", "torch")

    runtime, model = local_image_gen.resolve_local_image_backend("Qwen/Qwen-Image-2512")

    assert runtime == "torch"
    assert model == "Qwen/Qwen-Image-2512"


def test_resolve_local_image_backend_prefers_mlx_on_apple_silicon(monkeypatch):
    monkeypatch.setenv("CATHODE_LOCAL_IMAGE_RUNTIME", "auto")
    monkeypatch.setattr(local_image_gen, "_is_apple_silicon", lambda: True)
    monkeypatch.setattr(local_image_gen, "_mlx_command_available", lambda: True)

    runtime, model = local_image_gen.resolve_local_image_backend("Qwen/Qwen-Image-2512")

    assert runtime == "mlx"
    assert model == local_image_gen.DEFAULT_LOCAL_IMAGE_MLX_MODEL


def test_resolve_local_image_backend_keeps_explicit_mlx_model(monkeypatch):
    monkeypatch.setenv("CATHODE_LOCAL_IMAGE_RUNTIME", "mlx")

    runtime, model = local_image_gen.resolve_local_image_backend(
        "mlx-community/Qwen-Image-2512-6bit"
    )

    assert runtime == "mlx"
    assert model == "mlx-community/Qwen-Image-2512-6bit"


def test_generate_local_image_torch_does_not_inject_negative_prompt(monkeypatch, tmp_path):
    captured: dict[str, object] = {}

    class FakeImage:
        def save(self, output_path):
            Path(output_path).write_bytes(b"fake-local-image")

    class FakePipeline:
        def __call__(self, **kwargs):
            captured.update(kwargs)
            return type("FakeResult", (), {"images": [FakeImage()]})()

    class FakeTorch:
        mps = None

    monkeypatch.setenv("CATHODE_LOCAL_IMAGE_RUNTIME", "torch")
    monkeypatch.setattr(local_image_gen, "_load_torch_pipeline", lambda model: (FakePipeline(), FakeTorch(), "cpu"))
    monkeypatch.setattr(local_image_gen, "_inference_steps", lambda: 12)
    monkeypatch.setattr(local_image_gen, "_guidance_scale", lambda: 3.5)

    result = local_image_gen.generate_local_image(
        prompt="Anthropic-authored prompt",
        output_path=tmp_path / "scene.png",
        model=local_image_gen.DEFAULT_LOCAL_IMAGE_MODEL,
        width=1280,
        height=720,
    )

    assert result.exists()
    assert result.read_bytes() == b"fake-local-image"
    assert captured["prompt"] == "Anthropic-authored prompt"
    assert "negative_prompt" not in captured
