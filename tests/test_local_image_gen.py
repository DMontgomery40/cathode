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
