"""Image generation/editing using local Codex exec, Replicate, local models, and DashScope."""

import json
from pathlib import Path
import base64
import os
import re
import shlex
import shutil
import subprocess
import tempfile
import traceback
import sys
from contextlib import ExitStack

import replicate
from replicate import Client
import requests

from core.local_image_gen import DEFAULT_LOCAL_IMAGE_MODEL, generate_local_image
from core.rate_limiter import image_limiter

# Target dimensions for all generated/edited images (16:9 aspect ratio)
TARGET_WIDTH = 1664
TARGET_HEIGHT = 928
TARGET_SIZE_DASHSCOPE = f"{TARGET_WIDTH}*{TARGET_HEIGHT}"
TARGET_SIZE_OPENAI = f"{TARGET_WIDTH}x{TARGET_HEIGHT}"
DEFAULT_IMAGE_MODEL = "qwen/qwen-image-2512"
DEFAULT_CODEX_IMAGE_MODEL = "gpt-image-2"
DEFAULT_CODEX_IMAGE_QUALITY = "medium"
DEFAULT_OPENAI_IMAGE_EDIT_MODEL = DEFAULT_CODEX_IMAGE_MODEL
OPENAI_IMAGE_EDIT_MODELS = (DEFAULT_OPENAI_IMAGE_EDIT_MODEL,)
DEFAULT_REPLICATE_IMAGE_EDIT_MODEL = "qwen/qwen-image-edit-2511"
DASHSCOPE_IMAGE_EDIT_MODELS = ("qwen-image-edit-plus", "qwen-image-edit")
REPO_ROOT = Path(__file__).resolve().parents[1]
CODEX_IMAGE_SCRIPT = REPO_ROOT / "scripts" / "generate_openai_image.py"
CODEX_IMAGE_EDIT_SCRIPT = REPO_ROOT / "scripts" / "edit_openai_image.py"


def _log(msg):
    """Debug logging to stderr (visible in Streamlit terminal)."""
    print(f"[IMAGE_GEN] {msg}", file=sys.stderr, flush=True)


def _extract_json_object(text: str) -> dict[str, object] | None:
    candidate = str(text or "").strip()
    if not candidate:
        return None
    try:
        parsed = json.loads(candidate)
    except json.JSONDecodeError:
        start = candidate.find("{")
        end = candidate.rfind("}")
        if start < 0 or end <= start:
            return None
        try:
            parsed = json.loads(candidate[start : end + 1])
        except json.JSONDecodeError:
            return None
    return parsed if isinstance(parsed, dict) else None


def _codex_image_quality() -> str:
    value = str(os.getenv("CATHODE_CODEX_IMAGE_QUALITY") or DEFAULT_CODEX_IMAGE_QUALITY).strip().lower()
    return value if value in {"low", "medium", "high"} else DEFAULT_CODEX_IMAGE_QUALITY


def _codex_exec_model() -> str:
    return str(os.getenv("CATHODE_CODEX_EXEC_MODEL") or "").strip()


def _codex_helper_python_command() -> str:
    executable = str(sys.executable or "").strip()
    if executable:
        return shlex.quote(str(Path(executable).expanduser().resolve()))
    return "python3"


# Replicate client with timeout to prevent indefinite hangs
# 120s timeout covers both cold-start queue delays and generation time
_replicate_client = None


def _get_replicate_client() -> Client:
    """Get or create the Replicate client with timeout."""
    global _replicate_client
    if _replicate_client is None:
        _replicate_client = Client(timeout=120)  # 2 minute timeout
        _log("Created Replicate client with 120s timeout")
    return _replicate_client


def _ensure_png(path: Path) -> Path:
    """Convert image to PNG if it's not already (Replicate sometimes returns WebP)."""
    import subprocess
    result = subprocess.run(["file", str(path)], capture_output=True, text=True)
    if "Web/P" in result.stdout or "RIFF" in result.stdout:
        tmp = path.with_suffix(".tmp.png")
        subprocess.run(["ffmpeg", "-y", "-i", str(path), "-f", "image2", str(tmp)],
                      capture_output=True, check=True)
        tmp.replace(path)
        _log(f"  Converted WebP to PNG: {path}")
    return path


_EXACT_TEXT_EDIT_PROMPT_RE = re.compile(
    r'^change\s+"([^"\r\n]+)"\s+to\s+"([^"\r\n]+)"$',
    re.IGNORECASE,
)


def build_exact_text_edit_prompt(source_text: str, target_text: str) -> str:
    source = str(source_text or "")
    target = str(target_text or "")
    if not source.strip() or not target.strip():
        raise ValueError("Exact text edit prompts require both source and target text.")
    if '"' in source or '"' in target:
        raise ValueError("Exact text edit prompts do not support embedded double quotes.")
    return f'change "{source}" to "{target}"'


def canonicalize_exact_text_edit_prompt(prompt: str) -> str | None:
    match = _EXACT_TEXT_EDIT_PROMPT_RE.fullmatch(str(prompt or "").strip())
    if not match:
        return None
    return build_exact_text_edit_prompt(match.group(1), match.group(2))

# DashScope (Alibaba Model Studio) endpoints for Qwen image edit models.
# NOTE: Beijing + Singapore have separate API keys and endpoints (cross-region calls fail).
_DASHSCOPE_ENDPOINT_SINGAPORE = "https://dashscope-intl.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation"
_DASHSCOPE_ENDPOINT_BEIJING = "https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation"


def _dashscope_endpoint() -> str:
    override = (os.getenv("DASHSCOPE_ENDPOINT") or "").strip()
    if override:
        return override
    region = (os.getenv("DASHSCOPE_REGION") or "").strip().upper()
    if region in {"BEIJING", "BJ", "CN"}:
        return _DASHSCOPE_ENDPOINT_BEIJING
    # Default to the "intl" endpoint (Singapore) because this repo is commonly run outside CN.
    return _DASHSCOPE_ENDPOINT_SINGAPORE


def _dashscope_api_key() -> str:
    # Accept both DASHSCOPE_API_KEY and ALIBABA_API_KEY (same platform, different naming)
    key = (os.getenv("DASHSCOPE_API_KEY") or os.getenv("ALIBABA_API_KEY") or "").strip()
    if not key:
        raise ValueError("DASHSCOPE_API_KEY (or ALIBABA_API_KEY) is not set (required for DashScope qwen-image-edit-* models).")
    return key


def _data_uri_for_image(path: Path) -> str:
    ext = path.suffix.lower().lstrip(".")
    mime = {
        "png": "image/png",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "webp": "image/webp",
        "bmp": "image/bmp",
        "tif": "image/tiff",
        "tiff": "image/tiff",
        "gif": "image/gif",
    }.get(ext, "application/octet-stream")
    b64 = base64.b64encode(path.read_bytes()).decode("utf-8")
    return f"data:{mime};base64,{b64}"


def _infer_dashscope_size(path: Path) -> str | None:
    """Infer an explicit DashScope size from an image, if within allowed bounds."""
    try:
        from PIL import Image  # Pillow is already a project dependency

        with Image.open(path) as im:
            w, h = im.size
        if 512 <= int(w) <= 2048 and 512 <= int(h) <= 2048:
            return f"{int(w)}*{int(h)}"
    except Exception:
        return None
    return None


def _extract_dashscope_image_urls(payload: dict) -> list[str]:
    """
    DashScope response example:
      { "output": { "choices": [ { "message": { "content": [ {"image": "https://...png"}, ... ]}}]}}
    """
    urls: list[str] = []
    output = payload.get("output")
    if not isinstance(output, dict):
        return urls
    choices = output.get("choices")
    if not isinstance(choices, list):
        return urls
    for c in choices:
        if not isinstance(c, dict):
            continue
        msg = c.get("message")
        if not isinstance(msg, dict):
            continue
        content = msg.get("content")
        if not isinstance(content, list):
            continue
        for part in content:
            if not isinstance(part, dict):
                continue
            img = part.get("image")
            if isinstance(img, str) and img.strip():
                urls.append(img.strip())
    return urls


def default_image_edit_model() -> str:
    """
    Default selection:
    - If IMAGE_EDIT_MODEL is set, use it verbatim.
    - If IMAGE_EDIT_PROVIDER is set to openai/codex, default to GPT Image 2.
    - If IMAGE_EDIT_PROVIDER is set to dashscope/alibaba/modelstudio, default to DashScope 'qwen-image-edit-plus'.
    - Otherwise prefer GPT Image 2 when OPENAI_API_KEY is configured, then Qwen fallbacks.
    """
    provider = (os.getenv("IMAGE_EDIT_PROVIDER") or "").strip().lower()
    env_model = (os.getenv("IMAGE_EDIT_MODEL") or "").strip()
    if provider in {"openai", "codex", "gpt", "gpt-image"}:
        return env_model or DEFAULT_OPENAI_IMAGE_EDIT_MODEL
    if provider in {"replicate", "rep"}:
        return env_model or DEFAULT_REPLICATE_IMAGE_EDIT_MODEL
    if provider in {"dashscope", "alibaba", "modelstudio"}:
        return env_model or DASHSCOPE_IMAGE_EDIT_MODELS[0]
    if env_model:
        return env_model
    if os.getenv("OPENAI_API_KEY"):
        return DEFAULT_OPENAI_IMAGE_EDIT_MODEL
    if os.getenv("REPLICATE_API_TOKEN"):
        return DEFAULT_REPLICATE_IMAGE_EDIT_MODEL
    if os.getenv("DASHSCOPE_API_KEY") or os.getenv("ALIBABA_API_KEY"):
        return DASHSCOPE_IMAGE_EDIT_MODELS[0]
    return DEFAULT_OPENAI_IMAGE_EDIT_MODEL


def available_image_edit_models(
    *,
    include_openai: bool,
    include_replicate: bool,
    include_dashscope: bool,
) -> list[str]:
    """Return image edit model options in public-facing preference order."""
    models: list[str] = []
    if include_openai:
        models.extend(OPENAI_IMAGE_EDIT_MODELS)
    if include_replicate:
        models.append(DEFAULT_REPLICATE_IMAGE_EDIT_MODEL)
    if include_dashscope:
        models.extend(DASHSCOPE_IMAGE_EDIT_MODELS)
    return models


def _openai_image_edit_api_available() -> bool:
    return bool(os.getenv("OPENAI_API_KEY"))


def _openai_image_edit_model(model: str | None) -> bool:
    return str(model or "").strip().startswith("gpt-image")


def _edit_image_replicate(
    *,
    prompt: str,
    input_image_paths: list[Path],
    output_path: Path,
    model: str,
    seed: int | None,
) -> Path:
    # Note: We need to define the call inside the retry loop to re-open the files on retry
    def _call_replicate_edit():
        client = _get_replicate_client()
        with ExitStack() as stack:
            files = [stack.enter_context(open(p, "rb")) for p in input_image_paths]
            inputs: dict = {
                "prompt": prompt,
                "image": files,  # Model expects an array
                "aspect_ratio": "16:9",
                "output_format": "png",
                "go_fast": False,
            }
            if seed is not None:
                inputs["seed"] = int(seed)
            return client.run(
                model,
                input=inputs,
            )

    output = image_limiter.call_with_retry(_call_replicate_edit)

    # Handle output
    if isinstance(output, list):
        image_url = output[0]
    elif hasattr(output, "url"):
        image_url = output.url
    else:
        image_url = str(output)

    # Download and save
    response = requests.get(image_url, timeout=(5, 60))  # (connect, read)
    response.raise_for_status()
    output_path.write_bytes(response.content)

    # Ensure PNG format (Replicate may return WebP despite output_format: png)
    _ensure_png(output_path)

    return output_path


def _edit_image_dashscope(
    *,
    prompt: str,
    input_image_paths: list[Path],
    output_path: Path,
    model: str,
    n: int,
    size: str | None,
    prompt_extend: bool,
    negative_prompt: str,
    watermark: bool,
    seed: int | None,
) -> Path:
    if not (1 <= int(n) <= 6):
        raise ValueError("DashScope qwen-image-edit-max/qwen-image-edit-plus supports n in [1, 6].")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    endpoint = _dashscope_endpoint()
    api_key = _dashscope_api_key()

    # Always use target dimensions for consistent output (size arg can override)
    inferred_size = size or TARGET_SIZE_DASHSCOPE
    params: dict = {
        "n": int(n),
        "negative_prompt": negative_prompt if isinstance(negative_prompt, str) else " ",
        "prompt_extend": bool(prompt_extend),
        "watermark": bool(watermark),
    }
    if inferred_size:
        params["size"] = inferred_size
    if seed is not None:
        # DashScope supports seed 0-2147483647 for reproducible edits
        params["seed"] = int(seed) % 2147483648

    content = [{"image": _data_uri_for_image(p)} for p in input_image_paths]
    content.append({"text": prompt})

    body = {
        "model": model,
        "input": {"messages": [{"role": "user", "content": content}]},
        "parameters": params,
    }

    def _call_dashscope() -> dict:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }
        _log(f"  DashScope POST model={model} n={params.get('n')} size={params.get('size', '(default)')}")
        resp = requests.post(endpoint, headers=headers, json=body, timeout=(10, 240))
        _log(f"  DashScope response status: {resp.status_code}")
        try:
            payload = resp.json()
        except Exception:
            # Bubble up HTTP errors with some context
            snippet = (resp.text or "")[:500]
            raise RuntimeError(f"DashScope returned non-JSON (HTTP {resp.status_code}): {snippet}") from None

        if resp.status_code != 200:
            msg = payload.get("message") if isinstance(payload, dict) else None
            code = payload.get("code") if isinstance(payload, dict) else None
            raise RuntimeError(f"DashScope image edit failed (HTTP {resp.status_code}, code={code}): {msg}")

        if isinstance(payload, dict) and str(payload.get("code") or "").strip():
            raise RuntimeError(f"DashScope image edit failed (code={payload.get('code')}): {payload.get('message')}")

        return payload if isinstance(payload, dict) else {}

    payload = image_limiter.call_with_retry(_call_dashscope)
    urls = _extract_dashscope_image_urls(payload)
    if not urls:
        raise RuntimeError(f"DashScope returned no image URLs. Top-level keys: {list(payload.keys())}")

    # Save first image to output_path; if n>1, also save additional images next to it.
    first_written = False
    for idx, url in enumerate(urls[: int(n)]):
        out = (
            output_path
            if idx == 0
            else output_path.with_name(f"{output_path.stem}__n{idx + 1}{output_path.suffix}")
        )
        r = requests.get(url, timeout=(5, 120))
        r.raise_for_status()
        out.write_bytes(r.content)
        if not first_written:
            first_written = True
    return output_path


def _edit_image_openai_api(
    *,
    prompt: str,
    input_image_paths: list[Path],
    output_path: Path,
    model: str,
) -> Path:
    if not _openai_image_edit_api_available():
        raise ValueError("OPENAI_API_KEY is not set, so GPT Image editing cannot use the OpenAI API fallback.")

    import openai

    output_path.parent.mkdir(parents=True, exist_ok=True)
    client = openai.OpenAI()

    def _call_openai_edit():
        with ExitStack() as stack:
            files = [stack.enter_context(open(p, "rb")) for p in input_image_paths]
            image_arg = files[0] if len(files) == 1 else files
            return client.images.edit(
                model=str(model or DEFAULT_OPENAI_IMAGE_EDIT_MODEL).strip() or DEFAULT_OPENAI_IMAGE_EDIT_MODEL,
                image=image_arg,
                prompt=prompt,
                size=TARGET_SIZE_OPENAI,
                quality=_codex_image_quality(),
                output_format="png",
            )

    result = image_limiter.call_with_retry(_call_openai_edit)
    image_base64 = result.data[0].b64_json if result.data else None
    if image_base64:
        output_path.write_bytes(base64.b64decode(image_base64))
        return output_path

    image_url = getattr(result.data[0], "url", None) if result.data else None
    if image_url:
        response = requests.get(str(image_url), timeout=(5, 60))
        response.raise_for_status()
        output_path.write_bytes(response.content)
        _ensure_png(output_path)
        return output_path
    raise RuntimeError("OpenAI image edit returned no image payload.")


def generate_image(
    prompt: str,
    output_path: str | Path,
    model: str = DEFAULT_IMAGE_MODEL,
    apply_style: bool = True,
    seed: int | None = None,
    brief: dict | None = None,
) -> Path:
    """
    Generate an image using Qwen Image 2512 model.

    $0.02/image, ~7s, strongest text rendering available.

    Args:
        prompt: The image generation prompt
        output_path: Where to save the generated image
        model: Replicate model identifier
        apply_style: Whether to append the style suffix

    Returns:
        Path to the saved image
    """
    _log(f"generate_image() called")
    _log(f"  output_path: {output_path}")
    _log(f"  model: {model}")
    _log(f"  prompt (first 100 chars): {prompt[:100]}...")

    output_path = Path(output_path)
    _log(f"  Creating parent dir: {output_path.parent}")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    full_prompt = prompt
    _log(f"  Full prompt length: {len(full_prompt)} chars")

    # Run the model with rate limiting and retry
    def _call_replicate():
        client = _get_replicate_client()
        _log(f"  Calling client.run() with model: {model} (120s timeout)")
        inputs: dict = {
            "prompt": full_prompt,
            "aspect_ratio": "16:9",
            "output_format": "png",
            "go_fast": False,
            "guidance": 5,
            "num_inference_steps": 50,
        }
        if seed is not None:
            inputs["seed"] = int(seed)
        return client.run(
            model,
            input=inputs,
        )

    try:
        _log(f"  Starting API call with retry...")
        output = image_limiter.call_with_retry(_call_replicate)
        _log(f"  API call succeeded, output type: {type(output)}")
        _log(f"  Output value: {output}")
    except Exception as e:
        _log(f"  API CALL FAILED: {type(e).__name__}: {e}")
        _log(f"  Traceback:\n{traceback.format_exc()}")
        raise

    # Handle different output formats from Replicate
    if isinstance(output, list):
        image_url = output[0]
        _log(f"  Output was list, first element: {image_url}")
    elif hasattr(output, 'url'):
        image_url = output.url
        _log(f"  Output had .url attribute: {image_url}")
    else:
        image_url = str(output)
        _log(f"  Output stringified: {image_url}")

    # Download and save the image
    _log(f"  Downloading image from URL...")
    try:
        response = requests.get(image_url, timeout=(5, 60))  # (connect, read)
        _log(f"  Download response status: {response.status_code}")
        response.raise_for_status()
        _log(f"  Downloaded {len(response.content)} bytes")
    except Exception as e:
        _log(f"  DOWNLOAD FAILED: {type(e).__name__}: {e}")
        _log(f"  Traceback:\n{traceback.format_exc()}")
        raise

    try:
        output_path.write_bytes(response.content)
        _log(f"  Saved to: {output_path}")
        _log(f"  File exists: {output_path.exists()}, size: {output_path.stat().st_size if output_path.exists() else 'N/A'}")
    except Exception as e:
        _log(f"  FILE WRITE FAILED: {type(e).__name__}: {e}")
        _log(f"  Traceback:\n{traceback.format_exc()}")
        raise

    # Ensure PNG format (Replicate may return WebP despite output_format: png)
    _ensure_png(output_path)

    return output_path


def generate_image_local(
    prompt: str,
    output_path: str | Path,
    model: str = DEFAULT_LOCAL_IMAGE_MODEL,
    apply_style: bool = True,
    seed: int | None = None,
    brief: dict | None = None,
) -> Path:
    """Generate an image locally with the configured Hugging Face Qwen Image model."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    return generate_local_image(
        prompt=prompt,
        output_path=output_path,
        model=str(model or DEFAULT_LOCAL_IMAGE_MODEL).strip() or DEFAULT_LOCAL_IMAGE_MODEL,
        width=TARGET_WIDTH,
        height=TARGET_HEIGHT,
        seed=seed,
    )


def generate_image_codex_exec(
    prompt: str,
    output_path: str | Path,
    model: str = DEFAULT_CODEX_IMAGE_MODEL,
    apply_style: bool = True,
    seed: int | None = None,
    brief: dict | None = None,
) -> Path:
    """Generate an image by asking the local Codex CLI to run the checked-in GPT Image helper."""
    del apply_style, seed, brief

    codex_path = shutil.which("codex")
    if not codex_path:
        raise ValueError("codex is not available in PATH, so the local Codex image lane cannot run.")
    if not CODEX_IMAGE_SCRIPT.exists():
        raise ValueError(f"Missing Codex image helper script: {CODEX_IMAGE_SCRIPT}")

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    resolved_model = str(model or DEFAULT_CODEX_IMAGE_MODEL).strip() or DEFAULT_CODEX_IMAGE_MODEL
    resolved_quality = _codex_image_quality()

    with tempfile.TemporaryDirectory(prefix="cathode-codex-image-") as tmp_dir:
        temp_root = Path(tmp_dir)
        prompt_path = temp_root / "prompt.txt"
        prompt_path.write_text(str(prompt or ""), encoding="utf-8")
        result_path = temp_root / "result.json"
        workdir = temp_root / "workdir"
        workdir.mkdir(parents=True, exist_ok=True)

        helper_command = " ".join(
            [
                _codex_helper_python_command(),
                shlex.quote(str(CODEX_IMAGE_SCRIPT)),
                "--prompt-file",
                shlex.quote(str(prompt_path)),
                "--output",
                shlex.quote(str(output_path.resolve())),
                "--model",
                shlex.quote(resolved_model),
                "--size",
                shlex.quote(TARGET_SIZE_OPENAI),
                "--quality",
                shlex.quote(resolved_quality),
                "--output-format",
                "png",
            ]
        )
        agent_prompt = (
            "You are Cathode's local Codex image-generation lane.\n"
            "Run the exact command below once, do not rewrite it, and do not modify any files except the requested output image.\n\n"
            f"{helper_command}\n\n"
            f"After it finishes, verify the file exists at {output_path.resolve()} and return one JSON object only.\n"
            "Success shape:\n"
            f'{{"status":"succeeded","provider":"codex","model":"{resolved_model}","output_path":"{output_path.resolve()}"}}\n'
            "Failure shape:\n"
            f'{{"status":"failed","provider":"codex","model":"{resolved_model}","output_path":"","error":"short reason"}}\n'
            "Do not add markdown or commentary."
        )

        command = [
            codex_path,
            "exec",
            "--dangerously-bypass-approvals-and-sandbox",
            "--skip-git-repo-check",
            "--ephemeral",
            "-C",
            str(workdir),
            "--add-dir",
            str(REPO_ROOT),
            "--add-dir",
            str(output_path.parent.resolve()),
            "-o",
            str(result_path),
            "-",
        ]
        configured_model = _codex_exec_model()
        if configured_model:
            command.extend(["-m", configured_model])

        completed = subprocess.run(
            command,
            input=agent_prompt,
            text=True,
            capture_output=True,
            check=False,
        )

        response_payload = (
            _extract_json_object(result_path.read_text(encoding="utf-8"))
            if result_path.exists()
            else _extract_json_object(completed.stdout)
        ) or {}

        if output_path.exists() and output_path.stat().st_size > 0:
            return output_path

        error = str(response_payload.get("error") or "").strip()
        detail = error or completed.stderr.strip() or completed.stdout.strip() or "Codex image generation failed."
        raise RuntimeError(detail)


def edit_image_codex_exec(
    prompt: str,
    input_image_path: str | Path | list[str | Path],
    output_path: str | Path,
    model: str = DEFAULT_OPENAI_IMAGE_EDIT_MODEL,
) -> Path:
    """Edit an image by asking the local Codex CLI to run the checked-in GPT Image edit helper."""
    if isinstance(input_image_path, (list, tuple)):
        input_image_paths = [Path(p) for p in input_image_path]
    else:
        input_image_paths = [Path(input_image_path)]

    codex_path = shutil.which("codex")
    if not codex_path:
        raise ValueError("codex is not available in PATH, so the local Codex image-edit lane cannot run.")
    if not CODEX_IMAGE_EDIT_SCRIPT.exists():
        raise ValueError(f"Missing Codex image edit helper script: {CODEX_IMAGE_EDIT_SCRIPT}")

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    resolved_model = str(model or DEFAULT_OPENAI_IMAGE_EDIT_MODEL).strip() or DEFAULT_OPENAI_IMAGE_EDIT_MODEL
    resolved_quality = _codex_image_quality()

    with tempfile.TemporaryDirectory(prefix="cathode-codex-image-edit-") as tmp_dir:
        temp_root = Path(tmp_dir)
        prompt_path = temp_root / "prompt.txt"
        prompt_path.write_text(str(prompt or ""), encoding="utf-8")
        result_path = temp_root / "result.json"
        workdir = temp_root / "workdir"
        workdir.mkdir(parents=True, exist_ok=True)

        image_args = []
        for image_path in input_image_paths:
            image_args.extend(["--input-image", shlex.quote(str(image_path.expanduser().resolve()))])
        helper_parts = [
            _codex_helper_python_command(),
            shlex.quote(str(CODEX_IMAGE_EDIT_SCRIPT)),
            "--prompt-file",
            shlex.quote(str(prompt_path)),
            *image_args,
            "--output",
            shlex.quote(str(output_path.resolve())),
            "--model",
            shlex.quote(resolved_model),
            "--size",
            shlex.quote(TARGET_SIZE_OPENAI),
            "--quality",
            shlex.quote(resolved_quality),
            "--output-format",
            "png",
        ]
        helper_command = " ".join(helper_parts)
        agent_prompt = (
            "You are Cathode's local Codex image-edit lane.\n"
            "Run the exact command below once, do not rewrite it, and do not modify any files except the requested output image.\n\n"
            f"{helper_command}\n\n"
            f"After it finishes, verify the file exists at {output_path.resolve()} and return one JSON object only.\n"
            "Success shape:\n"
            f'{{"status":"succeeded","provider":"codex","model":"{resolved_model}","output_path":"{output_path.resolve()}"}}\n'
            "Failure shape:\n"
            f'{{"status":"failed","provider":"codex","model":"{resolved_model}","output_path":"","error":"short reason"}}\n'
            "Do not add markdown or commentary."
        )

        command = [
            codex_path,
            "exec",
            "--dangerously-bypass-approvals-and-sandbox",
            "--skip-git-repo-check",
            "--ephemeral",
            "-C",
            str(workdir),
            "--add-dir",
            str(REPO_ROOT),
            "--add-dir",
            str(output_path.parent.resolve()),
        ]
        for image_path in input_image_paths:
            command.extend(["--add-dir", str(image_path.expanduser().resolve().parent)])
        command.extend(["-o", str(result_path), "-"])
        configured_model = _codex_exec_model()
        if configured_model:
            command.extend(["-m", configured_model])

        completed = subprocess.run(
            command,
            input=agent_prompt,
            text=True,
            capture_output=True,
            check=False,
        )

        response_payload = (
            _extract_json_object(result_path.read_text(encoding="utf-8"))
            if result_path.exists()
            else _extract_json_object(completed.stdout)
        ) or {}

        if output_path.exists() and output_path.stat().st_size > 0:
            return output_path

        error = str(response_payload.get("error") or "").strip()
        detail = error or completed.stderr.strip() or completed.stdout.strip() or "Codex image edit failed."
        raise RuntimeError(detail)


def edit_image(
    prompt: str,
    input_image_path: str | Path | list[str | Path],
    output_path: str | Path,
    model: str | None = None,
    seed: int | None = None,
    *,
    # DashScope-only controls (ignored by Replicate models)
    n: int = 1,
    size: str | None = None,
    prompt_extend: bool = True,
    negative_prompt: str = " ",
    watermark: bool = False,
) -> Path:
    """
    Edit an existing image using Qwen Image Edit model.

    $0.03/edit, ~4.5s, preserves style while making targeted changes.

    Args:
        prompt: Text instruction describing the edit
        input_image_path: Path to the image to edit
        output_path: Where to save the edited image

    Returns:
        Path to the edited image
    """
    # Normalize input images (DashScope supports 1-3 images; Replicate model accepts an array too)
    if isinstance(input_image_path, (list, tuple)):
        input_image_paths = [Path(p) for p in input_image_path]
    else:
        input_image_paths = [Path(input_image_path)]

    normalized_prompt = canonicalize_exact_text_edit_prompt(prompt)
    prompt = normalized_prompt or str(prompt or "").strip()
    chosen_model = (model or "").strip() or default_image_edit_model()
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # DashScope model names look like: qwen-image-edit-max, qwen-image-edit-max-2026-01-16, qwen-image-edit-plus, qwen-image-edit
    if chosen_model.startswith("qwen-image-edit"):
        return _edit_image_dashscope(
            prompt=prompt,
            input_image_paths=input_image_paths,
            output_path=output_path,
            model=chosen_model,
            n=int(n),
            size=size,
            prompt_extend=bool(prompt_extend),
            negative_prompt=negative_prompt,
            watermark=bool(watermark),
            seed=seed,
        )

    if _openai_image_edit_model(chosen_model):
        if shutil.which("codex"):
            return edit_image_codex_exec(
                prompt,
                input_image_paths,
                output_path,
                model=chosen_model,
            )
        return _edit_image_openai_api(
            prompt=prompt,
            input_image_paths=input_image_paths,
            output_path=output_path,
            model=chosen_model,
        )

    # Otherwise assume Replicate model id (e.g., "qwen/qwen-image-edit-2511")
    return _edit_image_replicate(
        prompt=prompt,
        input_image_paths=input_image_paths,
        output_path=output_path,
        model=chosen_model,
        seed=seed,
    )


def generate_scene_image(
    scene: dict,
    project_dir: Path,
    brief: dict | None = None,
    provider: str = "replicate",
    model: str = DEFAULT_IMAGE_MODEL,
) -> Path:
    """
    Generate an image for a specific scene.

    Args:
        scene: Scene dictionary with 'id' and 'visual_prompt'
        project_dir: Project directory for saving assets

    Returns:
        Path to the generated image
    """
    _log(f"=== generate_scene_image() START ===")
    _log(f"  scene keys: {list(scene.keys())}")
    _log(f"  project_dir: {project_dir}")
    _log(f"  provider: {provider}")

    scene_id = scene.get("id")
    _log(f"  scene_id: {scene_id}")

    raw_prompt = scene.get("visual_prompt")
    prompt = raw_prompt if isinstance(raw_prompt, str) else str(raw_prompt or "")
    if not prompt.strip():
        _log(f"  ERROR: No visual_prompt in scene!")
        raise ValueError(f"Scene {scene_id} has no visual_prompt")

    _log(f"  visual_prompt length: {len(prompt)}")

    output_path = project_dir / "images" / f"scene_{scene_id:03d}.png"
    _log(f"  output_path: {output_path}")

    normalized_provider = str(provider).strip().lower()
    if normalized_provider == "manual":
        raise ValueError(
            "AI image generation is disabled for this project. Upload a still image instead, or switch the image provider back to Cathode's Codex Exec still-image lane."
        )

    try:
        if normalized_provider == "local":
            result = generate_image_local(prompt, output_path, model=model, brief=brief)
        elif normalized_provider == "codex":
            result = generate_image_codex_exec(prompt, output_path, model=model, brief=brief)
        else:
            result = generate_image(prompt, output_path, model=model, brief=brief)
        _log(f"=== generate_scene_image() SUCCESS: {result} ===")
        return result
    except Exception as e:
        _log(f"=== generate_scene_image() FAILED: {type(e).__name__}: {e} ===")
        raise
