#!/usr/bin/env python3
"""Generate a single GPT Image asset and save it to disk."""

from __future__ import annotations

import argparse
import base64
import json
import os
from pathlib import Path

import openai

# Env var NAMES only (no endpoint/key VALUES). Resolver is inlined rather than
# imported from core.runtime because this helper runs as a standalone subprocess
# (codex exec) where the package may not be importable. Matched-pair rule: a
# shared/proxy key is only paired with an explicit base_url, never the public default.
_OPENAI_KEY_ENV_NAMES = ("OPENAI_API_KEY", "BETTUBE_STUDIO_OPENAI_API_KEY", "LITELLM_API_KEY", "AIPROXY_API_KEY")
_OPENAI_BASE_URL_ENV_NAMES = ("OPENAI_BASE_URL", "BETTUBE_STUDIO_OPENAI_BASE_URL")


def _make_openai_client() -> "openai.OpenAI":
    key = next((os.environ[name] for name in _OPENAI_KEY_ENV_NAMES if os.environ.get(name)), None)
    base_url = next((os.environ[name] for name in _OPENAI_BASE_URL_ENV_NAMES if os.environ.get(name)), None)
    kwargs = {"api_key": key, "base_url": base_url} if (base_url and key) else {}
    return openai.OpenAI(**kwargs)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate one OpenAI GPT Image asset and save it locally.")
    parser.add_argument("--prompt-file", required=True, help="Text file containing the final image prompt.")
    parser.add_argument("--output", required=True, help="Output image path.")
    parser.add_argument("--model", default="gpt-image-2", help="OpenAI image model.")
    parser.add_argument("--size", default="1664x928", help="Requested image size.")
    parser.add_argument("--quality", default="medium", help="Requested image quality.")
    parser.add_argument("--output-format", default="png", help="Requested output format.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    prompt_path = Path(args.prompt_file).expanduser().resolve()
    output_path = Path(args.output).expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    prompt = prompt_path.read_text(encoding="utf-8")
    if not prompt.strip():
        raise SystemExit("Prompt file is empty.")

    client = _make_openai_client()
    result = client.images.generate(
        model=str(args.model or "gpt-image-2").strip() or "gpt-image-2",
        prompt=prompt,
        size=str(args.size or "1664x928").strip() or "1664x928",
        quality=str(args.quality or "medium").strip() or "medium",
        output_format=str(args.output_format or "png").strip() or "png",
    )

    image_base64 = result.data[0].b64_json
    if not image_base64:
        raise SystemExit("OpenAI returned no image payload.")

    output_path.write_bytes(base64.b64decode(image_base64))
    print(
        json.dumps(
            {
                "status": "succeeded",
                "output_path": str(output_path),
                "model": str(args.model),
                "size": str(args.size),
                "quality": str(args.quality),
                "output_format": str(args.output_format),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
