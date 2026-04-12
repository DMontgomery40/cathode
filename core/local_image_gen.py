"""Local image generation adapters for torch/diffusers and Apple Silicon MLX."""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

DEFAULT_LOCAL_IMAGE_MODEL = "Qwen/Qwen-Image-2512"
DEFAULT_LOCAL_IMAGE_MLX_MODEL = "mlx-community/Qwen-Image-2512-8bit"
DEFAULT_LOCAL_IMAGE_STEPS = 50
DEFAULT_LOCAL_IMAGE_TRUE_CFG_SCALE = 4.0

_PIPELINE_CACHE: dict[tuple[str, str, str], Any] = {}


def _log(message: str) -> None:
    print(f"[LOCAL_IMAGE] {message}", file=sys.stderr, flush=True)


def _runtime_preference() -> str:
    value = str(os.getenv("CATHODE_LOCAL_IMAGE_RUNTIME") or "auto").strip().lower() or "auto"
    if value not in {"auto", "torch", "mlx"}:
        raise ValueError(f"Unsupported CATHODE_LOCAL_IMAGE_RUNTIME={value!r}.")
    return value


def _is_apple_silicon() -> bool:
    return platform.system() == "Darwin" and platform.machine() == "arm64"


def _mlx_command_available() -> bool:
    return bool(shutil.which("mflux-generate-qwen"))


def _preferred_device(torch: Any) -> str:
    requested = str(os.getenv("CATHODE_LOCAL_IMAGE_DEVICE") or "auto").strip().lower() or "auto"
    if requested != "auto":
        return requested
    if torch.cuda.is_available():
        return "cuda"
    if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def _preferred_dtype(torch: Any, device: str) -> Any:
    requested = str(os.getenv("CATHODE_LOCAL_IMAGE_DTYPE") or "auto").strip().lower() or "auto"
    dtype_map = {
        "float16": getattr(torch, "float16"),
        "fp16": getattr(torch, "float16"),
        "bfloat16": getattr(torch, "bfloat16"),
        "bf16": getattr(torch, "bfloat16"),
        "float32": getattr(torch, "float32"),
        "fp32": getattr(torch, "float32"),
    }
    if requested != "auto":
        if requested not in dtype_map:
            raise ValueError(f"Unsupported CATHODE_LOCAL_IMAGE_DTYPE={requested!r}.")
        return dtype_map[requested]
    if device == "cuda":
        return torch.bfloat16
    if device == "mps":
        return torch.float16
    return torch.float32


def _generator_for_seed(torch: Any, *, device: str, seed: int | None) -> Any | None:
    if seed is None:
        return None
    generator_device = "cuda" if device == "cuda" else "cpu"
    return torch.Generator(device=generator_device).manual_seed(int(seed))


def _inference_steps() -> int:
    raw = str(os.getenv("CATHODE_LOCAL_IMAGE_STEPS") or "").strip()
    if not raw:
        return DEFAULT_LOCAL_IMAGE_STEPS
    try:
        value = int(raw)
    except ValueError:
        return DEFAULT_LOCAL_IMAGE_STEPS
    return value if value > 0 else DEFAULT_LOCAL_IMAGE_STEPS


def _guidance_scale() -> float:
    raw = str(os.getenv("CATHODE_LOCAL_IMAGE_TRUE_CFG_SCALE") or "").strip()
    if not raw:
        return DEFAULT_LOCAL_IMAGE_TRUE_CFG_SCALE
    try:
        value = float(raw)
    except ValueError:
        return DEFAULT_LOCAL_IMAGE_TRUE_CFG_SCALE
    return value if value > 0 else DEFAULT_LOCAL_IMAGE_TRUE_CFG_SCALE


def resolve_local_image_backend(model_name: str) -> tuple[str, str]:
    """Resolve the runtime engine and concrete model repo/path for local image generation."""
    requested_runtime = _runtime_preference()
    normalized_model = str(model_name or "").strip() or DEFAULT_LOCAL_IMAGE_MODEL

    if requested_runtime == "torch":
        return "torch", normalized_model

    mlx_model = str(os.getenv("CATHODE_LOCAL_IMAGE_MLX_MODEL") or "").strip() or DEFAULT_LOCAL_IMAGE_MLX_MODEL
    if requested_runtime == "mlx":
        return "mlx", mlx_model if normalized_model == DEFAULT_LOCAL_IMAGE_MODEL else normalized_model

    if _is_apple_silicon() and _mlx_command_available():
        return "mlx", mlx_model if normalized_model == DEFAULT_LOCAL_IMAGE_MODEL else normalized_model
    return "torch", normalized_model


def _load_torch_pipeline(model_name: str):
    try:
        import torch
    except Exception as exc:  # pragma: no cover - runtime dependency failure
        raise RuntimeError(
            "Local torch image generation requires torch. Install the optional local image dependencies first."
        ) from exc

    try:
        from diffusers import DiffusionPipeline
    except Exception as exc:  # pragma: no cover - runtime dependency failure
        raise RuntimeError(
            "Local torch image generation requires diffusers and transformers. "
            "Install the optional local image dependencies first."
        ) from exc

    device = _preferred_device(torch)
    torch_dtype = _preferred_dtype(torch, device)
    dtype_name = str(torch_dtype).split(".")[-1]
    cache_key = (model_name, device, dtype_name)
    if cache_key in _PIPELINE_CACHE:
        return _PIPELINE_CACHE[cache_key], torch, device

    _log(f"Loading torch image pipeline model={model_name} device={device} dtype={dtype_name}")
    pipe = DiffusionPipeline.from_pretrained(model_name, torch_dtype=torch_dtype)
    if hasattr(pipe, "set_progress_bar_config"):
        pipe.set_progress_bar_config(disable=True)
    if hasattr(pipe, "enable_attention_slicing"):
        pipe.enable_attention_slicing()
    pipe = pipe.to(device)
    _PIPELINE_CACHE[cache_key] = pipe
    return pipe, torch, device


def _generate_local_image_torch(
    *,
    prompt: str,
    output_path: Path,
    model: str,
    width: int,
    height: int,
    seed: int | None,
) -> Path:
    pipe, torch, device = _load_torch_pipeline(model)
    generator = _generator_for_seed(torch, device=device, seed=seed)

    kwargs: dict[str, Any] = {
        "prompt": prompt,
        "width": int(width),
        "height": int(height),
        "num_inference_steps": _inference_steps(),
        "true_cfg_scale": _guidance_scale(),
    }
    if generator is not None:
        kwargs["generator"] = generator

    image = pipe(**kwargs).images[0]
    image.save(output_path)

    if device == "mps" and getattr(torch, "mps", None) is not None:
        try:
            torch.mps.empty_cache()
        except Exception:
            pass

    return output_path


def _generate_local_image_mlx(
    *,
    prompt: str,
    output_path: Path,
    model: str,
    width: int,
    height: int,
    seed: int | None,
) -> Path:
    command = shutil.which("mflux-generate-qwen")
    if not command:
        raise RuntimeError(
            "Local MLX image generation requires mflux. Install it with `uv tool install --upgrade mflux`."
        )

    cmd = [
        command,
        "--model",
        model,
        "--prompt",
        prompt,
        "--width",
        str(int(width)),
        "--height",
        str(int(height)),
        "--steps",
        str(_inference_steps()),
        "--guidance",
        str(_guidance_scale()),
        "--output",
        str(output_path),
    ]

    if "/" in model:
        cmd.extend(["--base-model", "qwen"])
    if seed is not None:
        cmd.extend(["--seed", str(int(seed))])

    cache_limit_gb = str(os.getenv("CATHODE_LOCAL_IMAGE_MLX_CACHE_LIMIT_GB") or "").strip()
    if cache_limit_gb:
        cmd.extend(["--mlx-cache-limit-gb", cache_limit_gb])
    if str(os.getenv("CATHODE_LOCAL_IMAGE_MLX_LOW_RAM") or "").strip().lower() in {"1", "true", "yes"}:
        cmd.append("--low-ram")

    _log(f"Running MLX image command model={model}")
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as exc:
        details = (exc.stderr or exc.stdout or "").strip()
        if details:
            raise RuntimeError(f"MLX image generation failed: {details}") from exc
        raise RuntimeError("MLX image generation failed without error output.") from exc
    if not output_path.exists():
        raise RuntimeError("MLX image generation completed without writing the requested output file.")
    return output_path


def generate_local_image(
    *,
    prompt: str,
    output_path: str | Path,
    model: str,
    width: int,
    height: int,
    seed: int | None = None,
) -> Path:
    """Generate an image locally using the resolved runtime backend."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    runtime, resolved_model = resolve_local_image_backend(model)
    if runtime == "mlx":
        return _generate_local_image_mlx(
            prompt=prompt,
            output_path=output_path,
            model=resolved_model,
            width=width,
            height=height,
            seed=seed,
        )
    return _generate_local_image_torch(
        prompt=prompt,
        output_path=output_path,
        model=resolved_model,
        width=width,
        height=height,
        seed=seed,
    )
