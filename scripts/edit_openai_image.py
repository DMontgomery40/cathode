#!/usr/bin/env python3
"""Edit a GPT Image asset and save it to disk."""

from __future__ import annotations

import argparse
import base64
import json
from contextlib import ExitStack
from pathlib import Path

import openai


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Edit one OpenAI GPT Image asset and save it locally."
    )
    parser.add_argument(
        "--prompt-file",
        required=True,
        help="Text file containing the image edit prompt.",
    )
    parser.add_argument(
        "--input-image",
        action="append",
        required=True,
        help="Input image path. Repeat to provide multiple reference images.",
    )
    parser.add_argument("--output", required=True, help="Output image path.")
    parser.add_argument("--model", default="gpt-image-2", help="OpenAI image model.")
    parser.add_argument("--size", default="1664x928", help="Requested image size.")
    parser.add_argument("--quality", default="medium", help="Requested image quality.")
    parser.add_argument(
        "--output-format", default="png", help="Requested output format."
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    prompt_path = Path(args.prompt_file).expanduser().resolve()
    output_path = Path(args.output).expanduser().resolve()
    input_paths = [Path(path).expanduser().resolve() for path in args.input_image]
    output_path.parent.mkdir(parents=True, exist_ok=True)

    prompt = prompt_path.read_text(encoding="utf-8")
    if not prompt.strip():
        raise SystemExit("Prompt file is empty.")
    if not input_paths:
        raise SystemExit("At least one input image is required.")

    client = openai.OpenAI()
    with ExitStack() as stack:
        files = [stack.enter_context(path.open("rb")) for path in input_paths]
        image_arg = files[0] if len(files) == 1 else files
        result = client.images.edit(
            model=str(args.model or "gpt-image-2").strip() or "gpt-image-2",
            image=image_arg,
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
                "input_count": len(input_paths),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
