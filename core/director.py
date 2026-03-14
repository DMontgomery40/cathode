"""LLM-based storyboard generation for generic slide + voice videos."""

from __future__ import annotations

import json
import base64
import mimetypes
import os
import uuid
from pathlib import Path
from typing import Any, Literal

import anthropic
import openai

from .project_schema import normalize_brief

# Singleton LLM clients
_openai_client = None
_anthropic_client = None


def _get_openai_client():
    """Get or create singleton OpenAI client."""
    global _openai_client
    if _openai_client is None:
        _openai_client = openai.OpenAI()
    return _openai_client


def _get_anthropic_client():
    """Get or create singleton Anthropic client."""
    global _anthropic_client
    if _anthropic_client is None:
        _anthropic_client = anthropic.Anthropic()
    return _anthropic_client


# Cached prompts
_PROMPTS: dict[str, str] = {}

SOURCE_MODE_BEHAVIOR: dict[str, str] = {
    "ideas_notes": (
        "You may create structure and wording from rough notes. Fill gaps in phrasing, "
        "but keep the user's intent and constraints."
    ),
    "source_text": (
        "Preserve the factual content and key numbers from source_material. "
        "Restructure and simplify for narration, but do not invent facts."
    ),
    "final_script": (
        "Perform minimal rewriting. Keep the user's language and order as much as possible, "
        "mainly splitting into scene-sized narration with matching visual prompts."
    ),
}


def _resolve_prompt_path(name: str) -> Path:
    """Resolve prompt path, supporting versioned director_system experiments."""
    prompts_dir = Path(__file__).parent.parent / "prompts"

    if name == "director_system":
        version = (os.getenv("DIRECTOR_SYSTEM_VERSION") or "").strip()
        if version:
            versioned_path = prompts_dir / "director_system_versions" / version / "director_system.txt"
            if not versioned_path.exists():
                raise FileNotFoundError(
                    f"DIRECTOR_SYSTEM_VERSION={version!r} not found at {versioned_path}"
                )
            return versioned_path

        override_path = (os.getenv("DIRECTOR_SYSTEM_PROMPT_PATH") or "").strip()
        if override_path:
            path = Path(override_path)
            if not path.is_absolute():
                path = Path(__file__).parent.parent / override_path
            if not path.exists():
                raise FileNotFoundError(f"DIRECTOR_SYSTEM_PROMPT_PATH not found: {path}")
            return path

    return prompts_dir / f"{name}.txt"


def load_prompt(name: str) -> str:
    """Load a prompt from the prompts directory (cached)."""
    prompt_path = _resolve_prompt_path(name)
    cache_key = f"{name}:{prompt_path.resolve()}"
    if cache_key not in _PROMPTS:
        _PROMPTS[cache_key] = prompt_path.read_text()
    return _PROMPTS[cache_key]


def _target_words_from_minutes(minutes: float) -> tuple[int, int]:
    """
    Convert desired runtime into a usable word range.

    Assumes conversational narration around 140 words per minute.
    """
    baseline = max(1.0, float(minutes)) * 140.0
    low = int(round(baseline * 0.9))
    high = int(round(baseline * 1.1))
    return low, high


def _scene_count_guidance_from_minutes(minutes: float) -> str:
    """Return scene-count guidance that keeps still-image videos moving."""
    value = max(1.0, float(minutes))
    if value <= 3.0:
        return "Produce 10-18 scenes."
    if value <= 6.0:
        return "Produce 16-28 scenes."
    if value <= 10.0:
        return "Produce 22-36 scenes."
    return (
        "Produce enough scenes to keep the visuals moving. "
        "For image-led videos, prefer a new scene every 8-18 seconds unless a moment truly benefits from a slower hold."
    )


def _brief_for_prompt(payload: dict[str, Any]) -> dict[str, Any]:
    """Limit prompt payload to fields the director should consume."""
    brief = normalize_brief(payload)
    footage_manifest = []
    for item in brief.get("footage_manifest") or []:
        if not isinstance(item, dict):
            continue
        footage_manifest.append(
            {
                "id": str(item.get("id") or "").strip(),
                "label": str(item.get("label") or "").strip(),
                "path": Path(str(item.get("path") or "")).name if item.get("path") else "",
                "notes": str(item.get("notes") or "").strip(),
                "review_status": str(item.get("review_status") or "").strip(),
                "review_summary": str(item.get("review_summary") or "").strip(),
            }
        )
    return {
        "source_mode": brief["source_mode"],
        "video_goal": brief["video_goal"],
        "audience": brief["audience"],
        "source_material": brief["source_material"],
        "target_length_minutes": brief["target_length_minutes"],
        "tone": brief["tone"],
        "visual_style": brief["visual_style"],
        "must_include": brief["must_include"],
        "must_avoid": brief["must_avoid"],
        "ending_cta": brief["ending_cta"],
        "visual_source_strategy": brief["visual_source_strategy"],
        "text_render_mode": brief["text_render_mode"],
        "available_footage": brief["available_footage"],
        "footage_manifest": footage_manifest,
        "style_reference_summary": brief["style_reference_summary"],
        "raw_brief": brief["raw_brief"],
    }


def _legacy_brief_from_text(input_text: str) -> dict[str, Any]:
    """Compatibility shim for old callers that pass a raw text block."""
    return normalize_brief(
        {
            "source_mode": "source_text",
            "video_goal": "Create a clear, engaging narrated slide video.",
            "audience": "General audience",
            "source_material": input_text,
        }
    )


def _build_storyboard_user_prompt_from_brief(brief: dict[str, Any]) -> str:
    """Build the user prompt for storyboard generation from a normalized brief."""
    normalized = _brief_for_prompt(brief)
    source_mode = normalized["source_mode"]
    behavior = SOURCE_MODE_BEHAVIOR.get(source_mode, SOURCE_MODE_BEHAVIOR["source_text"])
    low_words, high_words = _target_words_from_minutes(normalized["target_length_minutes"])
    scene_count_guidance = _scene_count_guidance_from_minutes(normalized["target_length_minutes"])

    prompt_payload = json.dumps(normalized, indent=2, ensure_ascii=False)

    return f"""Create a storyboard for a narrated video.

Source mode behavior (must follow):
- mode: {source_mode}
- directive: {behavior}

Target runtime:
- desired minutes: {normalized["target_length_minutes"]}
- target narration words: {low_words}-{high_words} total across all scenes

User brief JSON:
{prompt_payload}

Output requirements:
- Return JSON only.
- Prefer an object with key "scenes"; a top-level array is also acceptable.
- {scene_count_guidance}
- Each scene must include:
  - "id" (integer, zero-based)
  - "title" (short scene title)
  - "narration" (spoken voiceover for this scene)
  - "visual_prompt" (for image scenes: a self-contained image prompt; for video scenes: clear footage/clip direction)
- Optional scene fields:
  - "scene_type" ("image" or "video"; default to "image")
  - "on_screen_text" (array of exact strings intended to be visible on the slide)
  - "footage_asset_id" (string id of a provided footage asset when a scene should use supplied video)

Quality constraints:
- Keep narration conversational, vivid, and easy to follow for the specified audience.
- If a brand, product, or identifier contains digits and a TTS engine could misread it, rewrite it the way it should be spoken.
- For image-led videos, err toward more scenes and shorter visual holds rather than a small number of long-held stills.
- If a still image would likely need to sit on screen for longer than about 8-18 seconds, split that beat into another scene, angle, or visual idea.
- Use punctuation intentionally for spoken delivery: commas and periods for pacing, occasional ellipses only when a dramatic pause is truly useful.
- The opening should usually orient the viewer before heavy detail:
  - scene 0 should usually be a cover or hook scene that clearly says what this video is about and why it matters
  - scene 1 should usually provide a roadmap, simple workflow, or viewer orientation
- For product, workflow, or tool explainers, make the ease/value proposition obvious in the first few scenes instead of burying it.
- The ending should feel resolved and intentional, not like a hard stop.
- Keep visual prompts or clip directions concrete and self-contained.
- Visual prompts should feel premium and cinematic rather than like plain template slides.
- Explicitly define:
  - background or environment
  - composition layout
  - exact text labels when needed
  - key objects, graphics, or metaphors
  - lighting, mood, and finish
- Treat text_render_mode as a hard contract:
  - "visual_authored": visible copy may be authored into the generated visual itself, and on_screen_text should stay aligned with that authored text when present.
  - "deterministic_overlay": for image scenes, avoid asking the image model to render readable title/body copy into the visual; reserve on_screen_text for Cathode's deterministic overlay and motion templates instead. Footage scenes may still naturally contain product text from the captured UI.
- Use on_screen_text when there are exact phrases or labels the slide should visibly support.
- If style_reference_summary is present, treat it as the canonical visual direction and make every scene compatible with that style while still matching the scene's content.
- Treat visual_source_strategy as a hard preference:
  - "images_only": keep all scenes as image scenes.
  - "mixed_media": use video scenes only where footage would clearly improve the explanation.
  - "video_preferred": prefer video scenes when the brief or available footage supports them.
- When available_footage is provided, use it to decide which scenes could realistically be video scenes.
- When footage_manifest is present:
  - prefer assets marked "accept" for central proof moments
  - assets marked "warn" can support the story, but should not become the hero proof without an obvious caveat
  - ignore assets marked "retry" unless the brief explicitly says otherwise
  - set "footage_asset_id" on video scenes when a supplied asset should be used
- If visual_source_strategy is "mixed_media" or "video_preferred" and available_footage is strong, include at least one purposeful video scene where the footage meaningfully helps.
- Respect must_include, must_avoid, and ending_cta.
"""


def generate_storyboard(
    source: str | dict[str, Any],
    provider: Literal["openai", "anthropic"] = "openai",
) -> list[dict]:
    """
    Generate storyboard scenes from either a generic brief or legacy source text.

    Args:
        source: Either a brief dictionary or a legacy free-text source string.
        provider: LLM provider ("openai" or "anthropic")
    """
    system_prompt = load_prompt("director_system")

    if isinstance(source, dict):
        brief = normalize_brief(source)
    else:
        brief = _legacy_brief_from_text(str(source or ""))

    user_prompt = _build_storyboard_user_prompt_from_brief(brief)

    if provider == "openai":
        return _generate_with_openai(system_prompt, user_prompt)
    if provider == "anthropic":
        return _generate_with_anthropic(system_prompt, user_prompt)
    raise ValueError(f"Unknown provider: {provider}")


def generate_storyboard_from_text(
    input_text: str,
    provider: Literal["openai", "anthropic"] = "openai",
) -> list[dict]:
    """Compatibility wrapper for callers that still pass raw source text."""
    return generate_storyboard(_legacy_brief_from_text(input_text), provider=provider)


def _guess_image_media_type(path: str | Path) -> str:
    guessed, _ = mimetypes.guess_type(str(path))
    if guessed and guessed.startswith("image/"):
        return guessed
    return "image/png"


def _data_url_for_image(path: str | Path) -> str:
    image_path = Path(path)
    media_type = _guess_image_media_type(image_path)
    b64 = base64.b64encode(image_path.read_bytes()).decode("utf-8")
    return f"data:{media_type};base64,{b64}"


def analyze_style_references(
    image_paths: list[str | Path],
    brief: dict[str, Any],
    *,
    provider: Literal["openai", "anthropic"] = "openai",
) -> str:
    """Summarize uploaded style-reference images into reusable art-direction guidance."""
    normalized_brief = normalize_brief(brief)
    valid_paths = [Path(p) for p in image_paths if Path(p).exists()]
    if not valid_paths:
        return ""

    system_prompt = load_prompt("style_reference_system")
    audience = normalized_brief.get("audience") or "the intended audience"
    video_goal = normalized_brief.get("video_goal") or "create a cohesive narrated video"
    visual_style = normalized_brief.get("visual_style") or "not specified"

    user_prompt = (
        "Analyze the uploaded reference image set as art-direction input for a storyboard video pipeline.\n\n"
        f"Audience: {audience}\n"
        f"Video goal: {video_goal}\n"
        f"Current visual_style field: {visual_style}\n\n"
        "Return a detailed prose summary describing the shared vibe, palette, lighting, composition, texture, level of realism, "
        "camera language, typography treatment if visible, density of detail, motion/design cues implied by the stills, and any "
        "recurring motifs or constraints that should be preserved scene by scene. Be concrete and specific rather than poetic."
    )

    if provider == "openai":
        client = _get_openai_client()
        content: list[dict[str, Any]] = [{"type": "input_text", "text": user_prompt}]
        for path in valid_paths:
            content.append({"type": "input_image", "image_url": _data_url_for_image(path)})

        response = client.responses.create(
            model="gpt-5.1",
            instructions=system_prompt,
            input=[{"role": "user", "content": content}],
            temperature=0.3,
        )
        return response.output_text.strip()

    if provider == "anthropic":
        client = _get_anthropic_client()
        content: list[dict[str, Any]] = []
        for path in valid_paths:
            content.append(
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": _guess_image_media_type(path),
                        "data": base64.b64encode(Path(path).read_bytes()).decode("utf-8"),
                    },
                }
            )
        content.append({"type": "text", "text": user_prompt})
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2500,
            system=system_prompt,
            messages=[{"role": "user", "content": content}],
        )
        text_block = next((b for b in response.content if hasattr(b, "text")), None)
        if not text_block:
            raise ValueError("No text response from model")
        return text_block.text.strip()

    raise ValueError(f"Unknown provider: {provider}")


def _generate_with_openai(system_prompt: str, user_prompt: str) -> list[dict]:
    """Generate storyboard using OpenAI Responses API."""
    client = _get_openai_client()

    response = client.responses.create(
        model="gpt-5.1",
        instructions=system_prompt,
        input=user_prompt,
        text={"format": {"type": "json_object"}},
        temperature=0.7,
    )

    content = response.output_text
    result = json.loads(content)

    # Handle both direct array and wrapped object responses
    if isinstance(result, list):
        scenes = result
    elif isinstance(result, dict) and "scenes" in result:
        scenes = result["scenes"]
    else:
        # Try to find any array in the response
        for value in result.values():
            if isinstance(value, list):
                scenes = value
                break
        else:
            raise ValueError("Could not find scenes array in response")

    return _validate_scenes(scenes)


def _generate_with_anthropic(system_prompt: str, user_prompt: str) -> list[dict]:
    """Generate storyboard using Anthropic Claude Sonnet 4.6 with forced structured tool output."""
    client = _get_anthropic_client()

    storyboard_tool = {
        "name": "emit_storyboard",
        "description": "Return the full storyboard as structured JSON.",
        "input_schema": {
            "type": "object",
            "properties": {
                "scenes": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "integer"},
                            "title": {"type": "string"},
                            "narration": {"type": "string"},
                            "visual_prompt": {"type": "string"},
                            "scene_type": {"type": "string", "enum": ["image", "video"]},
                            "footage_asset_id": {"type": "string"},
                            "on_screen_text": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                        },
                        "required": ["id", "title", "narration", "visual_prompt"],
                    },
                }
            },
            "required": ["scenes"],
        },
    }

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=12000,
        system=system_prompt,
        messages=[
            {"role": "user", "content": user_prompt},
        ],
        tools=[storyboard_tool],
        tool_choice={"type": "tool", "name": "emit_storyboard"},
    )

    tool_input = None
    for block in response.content:
        if block.type == "tool_use" and getattr(block, "name", "") == "emit_storyboard":
            tool_input = block.input
            break

    if not tool_input:
        raise ValueError("No structured storyboard tool output from Anthropic")

    # Handle both direct array and wrapped object responses
    if isinstance(tool_input, list):
        scenes = tool_input
    elif isinstance(tool_input, dict) and "scenes" in tool_input:
        scenes = tool_input["scenes"]
    else:
        for value in tool_input.values():
            if isinstance(value, list):
                scenes = value
                break
        else:
            raise ValueError("Could not find scenes array in response")

    return _validate_scenes(scenes)


def _validate_scenes(scenes: list[dict]) -> list[dict]:
    """Validate and normalize scene data."""
    validated = []
    for i, scene in enumerate(scenes):
        narration = str(scene.get("narration", "")).strip()
        visual_prompt = str(scene.get("visual_prompt", "")).strip()

        if not narration:
            raise ValueError(f"Scene {i + 1} has empty narration")
        if not visual_prompt:
            raise ValueError(f"Scene {i + 1} has empty visual prompt")

        on_screen_text = scene.get("on_screen_text")
        if isinstance(on_screen_text, list):
            normalized_on_screen = [str(item).strip() for item in on_screen_text if str(item).strip()]
        else:
            normalized_on_screen = []

        validated.append(
            {
                "id": scene.get("id", i),
                "uid": scene.get("uid", str(uuid.uuid4())[:8]),
                "title": scene.get("title", f"Scene {i + 1}"),
                "narration": narration,
                "visual_prompt": visual_prompt,
                "scene_type": str(scene.get("scene_type") or "image").strip().lower(),
                "footage_asset_id": str(scene.get("footage_asset_id") or "").strip() or None,
                "on_screen_text": normalized_on_screen,
                "refinement_history": scene.get("refinement_history", []),
                "image_path": scene.get("image_path"),
                # Model output should not be allowed to point directly at local files.
                "video_path": None,
                "audio_path": scene.get("audio_path"),
                "preview_path": scene.get("preview_path"),
            }
        )
    return validated


def refine_prompt(
    original_prompt: str,
    feedback: str,
    narration: str = "",
    provider: Literal["openai", "anthropic"] = "openai",
) -> str:
    """
    Refine an image prompt based on user feedback.

    Args:
        original_prompt: The current image prompt
        feedback: User's requested changes
        narration: The scene narration for context
        provider: LLM provider to use

    Returns:
        Refined prompt string
    """
    system_prompt = load_prompt("refiner_system")

    narration_context = f"\nScene narration (for context): {narration}\n" if narration else ""

    user_prompt = f"""Original prompt: {original_prompt}
{narration_context}
User feedback: {feedback}

Please provide the refined prompt."""

    if provider == "openai":
        client = _get_openai_client()
        response = client.responses.create(
            model="gpt-5.1",
            instructions=system_prompt,
            input=user_prompt,
            temperature=0.7,
        )
        return response.output_text.strip()

    if provider == "anthropic":
        client = _get_anthropic_client()
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2048,
            system=system_prompt,
            messages=[
                {"role": "user", "content": user_prompt},
            ],
        )
        text_block = next((b for b in response.content if hasattr(b, "text")), None)
        if not text_block:
            raise ValueError("No text response from model")
        return text_block.text.strip()

    raise ValueError(f"Unknown provider: {provider}")


def refine_narration(
    original_narration: str,
    feedback: str,
    provider: Literal["openai", "anthropic"] = "openai",
) -> str:
    """
    Refine a scene narration based on user feedback.

    Args:
        original_narration: The current narration text
        feedback: User's requested changes
        provider: LLM provider to use

    Returns:
        Refined narration string
    """
    system_prompt = load_prompt("refiner_narration_system")

    user_prompt = f"""Original narration: {original_narration}

User feedback: {feedback}

Please provide the refined narration."""

    if provider == "openai":
        client = _get_openai_client()
        response = client.responses.create(
            model="gpt-5.1",
            instructions=system_prompt,
            input=user_prompt,
            temperature=0.7,
        )
        return response.output_text.strip()

    if provider == "anthropic":
        client = _get_anthropic_client()
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2048,
            system=system_prompt,
            messages=[
                {"role": "user", "content": user_prompt},
            ],
        )
        text_block = next((b for b in response.content if hasattr(b, "text")), None)
        if not text_block:
            raise ValueError("No text response from model")
        return text_block.text.strip()

    raise ValueError(f"Unknown provider: {provider}")
