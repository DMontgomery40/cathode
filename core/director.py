"""LLM-based storyboard generation for generic slide + voice videos."""

from __future__ import annotations

import base64
import json
import mimetypes
import os
import uuid
from pathlib import Path
from typing import Any, Literal

import anthropic
import openai

from .costs import llm_actual_entry, llm_preflight_entry
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
_DIRECTOR_EXAMPLES_INDEX = Path(__file__).parent.parent / "prompts" / "director_examples" / "index.json"
_TRANSITION_HINTS = {"fade", "wipe"}
_OPENAI_DIRECTOR_MODEL = "gpt-5.1"
_ANTHROPIC_DIRECTOR_MODEL = "claude-sonnet-4-6"

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


def _director_prompt_version() -> str:
    return (os.getenv("DIRECTOR_SYSTEM_VERSION") or "").strip()


def _resolve_prompt_path(name: str) -> Path:
    """Resolve prompt path, supporting versioned director prompt bundles."""
    prompts_dir = Path(__file__).parent.parent / "prompts"

    if name.startswith("director_"):
        version = _director_prompt_version()
        if version:
            versioned_path = prompts_dir / "director_system_versions" / version / f"{name}.txt"
            if versioned_path.exists():
                return versioned_path
            if name == "director_system":
                raise FileNotFoundError(
                    f"DIRECTOR_SYSTEM_VERSION={version!r} not found at {versioned_path}"
                )

    if name == "director_system":
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


def load_optional_prompt(name: str) -> str:
    """Load an optional prompt fragment, returning an empty string when absent."""
    prompt_path = _resolve_prompt_path(name)
    if not prompt_path.exists():
        return ""
    return load_prompt(name)


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
    """Return the normalized brief payload the director should consume."""
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
    style_reference_paths = [
        Path(str(path)).name
        for path in (brief.get("style_reference_paths") or [])
        if str(path).strip()
    ]
    prompt_brief = dict(brief)
    prompt_brief["footage_manifest"] = footage_manifest
    prompt_brief["style_reference_paths"] = style_reference_paths
    return prompt_brief


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


def _brief_intent_text(brief: dict[str, Any]) -> str:
    parts = [
        brief.get("video_goal"),
        brief.get("audience"),
        brief.get("source_material"),
        brief.get("must_include"),
        brief.get("must_avoid"),
        brief.get("raw_brief"),
    ]
    return "\n".join(str(value or "").strip() for value in parts if str(value or "").strip()).lower()


def _brief_requests_multi_voice(brief: dict[str, Any]) -> bool:
    text = _brief_intent_text(brief)
    phrases = (
        "different voice",
        "different voices",
        "different elevenlabs voices",
        "multiple voices",
        "all eleven labs voices",
        "all 11 labs voices",
        "voice for each section",
        "voice for every section",
        "voice for each scene",
        "voice for every scene",
        "narrator plus",
        "real estate agent",
        "law firm",
        "commercial spots",
    )
    return any(phrase in text for phrase in phrases)


def _brief_wants_data_stage(brief: dict[str, Any]) -> bool:
    text = _brief_intent_text(brief)
    return any(
        phrase in text
        for phrase in (
            "ranked",
            "ranking",
            "comparison",
            "compare",
            "top three",
            "top 3",
            "data stage",
            "podium",
            "best option",
        )
    )


def _brief_wants_software_demo_example(brief: dict[str, Any]) -> bool:
    text = _brief_intent_text(brief)
    return any(
        phrase in text
        for phrase in (
            "demo",
            "walkthrough",
            "dashboard",
            "screen",
            "screenshot",
            "ui",
            "interface",
            "browser",
            "workspace",
            "product demo",
            "software",
        )
    )


def _brief_wants_whimsical_storybook_example(brief: dict[str, Any]) -> bool:
    text = _brief_intent_text(brief)
    return any(
        phrase in text
        for phrase in (
            "storybook",
            "whimsical",
            "surreal",
            "dreamlike",
            "fairy tale",
            "fairytale",
            "fable",
            "magical",
            "playful",
            "poetic",
            "absurd",
            "impossible",
            "unexpected",
            "must not contain",
            "but it must not",
        )
    )


def _brief_wants_abstract_concept_example(brief: dict[str, Any]) -> bool:
    text = _brief_intent_text(brief)
    return any(
        phrase in text
        for phrase in (
            "abstract",
            "invisible machine",
            "orchestration",
            "specialist agents",
            "coordinated agents",
            "system design",
            "concept diagram",
            "visual metaphor",
            "editorial science fiction",
        )
    )


def _director_capability_prompt_names(brief: dict[str, Any]) -> list[str]:
    normalized = normalize_brief(brief)
    names: list[str] = []
    visual_source_strategy = normalized.get("visual_source_strategy")
    if visual_source_strategy == "mixed_media":
        names.append("director_capability_visual_source_mixed_media")
    elif visual_source_strategy == "video_preferred":
        names.append("director_capability_visual_source_video_preferred")

    video_scene_style = normalized.get("video_scene_style")
    if video_scene_style == "cinematic":
        names.append("director_capability_video_style_cinematic")
    elif video_scene_style == "speaking":
        names.append("director_capability_video_style_speaking")
    elif video_scene_style == "mixed":
        names.append("director_capability_video_style_mixed")

    text_render_mode = normalized.get("text_render_mode")
    if text_render_mode == "deterministic_overlay":
        names.append("director_capability_text_render_deterministic_overlay")

    composition_mode = normalized.get("composition_mode")
    if composition_mode == "hybrid":
        names.append("director_capability_composition_hybrid")
    elif composition_mode == "motion_only":
        names.append("director_capability_composition_motion_only")

    if _brief_requests_multi_voice(normalized):
        names.append("director_capability_multi_voice")
    if _brief_wants_data_stage(normalized):
        names.append("director_capability_data_stage")

    return names


def _load_director_example_index() -> list[dict[str, Any]]:
    if not _DIRECTOR_EXAMPLES_INDEX.exists():
        return []
    try:
        parsed = json.loads(_DIRECTOR_EXAMPLES_INDEX.read_text())
    except json.JSONDecodeError:
        return []
    if not isinstance(parsed, list):
        return []
    return [item for item in parsed if isinstance(item, dict)]


def _director_example_intents(brief: dict[str, Any]) -> list[str]:
    normalized = normalize_brief(brief)
    intents: list[str] = []
    if _brief_wants_whimsical_storybook_example(normalized):
        intents.append("whimsical_storybook")
    elif _brief_wants_abstract_concept_example(normalized):
        intents.append("static_image_control")
    if normalized.get("visual_source_strategy") != "images_only" and _brief_wants_software_demo_example(normalized):
        intents.append("software_demo_overlay")
    if normalized.get("composition_mode") in {"hybrid", "motion_only"} or normalized.get("text_render_mode") == "deterministic_overlay":
        intents.extend(["kinetic_statement", "bullet_stack"])
    if _brief_requests_multi_voice(normalized):
        intents.append("multi_voice_pitch")
    if _brief_wants_data_stage(normalized):
        intents.append("ranked_data_stage")
    if any(keyword in _brief_intent_text(normalized) for keyword in ("quote", "testimonial", "founder note", "what she said")):
        intents.append("quote_focus")
    return list(dict.fromkeys(intents))


def _format_director_example(entry: dict[str, Any]) -> str:
    base_dir = _DIRECTOR_EXAMPLES_INDEX.parent / str(entry.get("id") or "").strip()
    if not base_dir.exists():
        return ""
    parts = [f'Example "{str(entry.get("title") or entry.get("id") or "example").strip()}":']
    for filename, label in (
        ("input_brief.json", "Input brief"),
        ("expected_storyboard.json", "Storyboard output"),
        ("why_it_is_good.md", "Why it works"),
    ):
        file_path = base_dir / filename
        if not file_path.exists():
            continue
        content = file_path.read_text().strip()
        if content:
            parts.append(f"{label}:\n{content}")
    return "\n\n".join(parts).strip()


def _selected_director_examples(brief: dict[str, Any]) -> list[str]:
    desired_intents = set(_director_example_intents(brief))
    rendered: list[str] = []
    for entry in _load_director_example_index():
        intents = {
            str(intent).strip()
            for intent in (entry.get("intents") or [])
            if str(intent).strip()
        }
        if not intents or not (desired_intents & intents):
            continue
        formatted = _format_director_example(entry)
        if formatted:
            rendered.append(formatted)
        if len(rendered) >= 3:
            break
    return rendered


def build_director_system_prompt(brief: dict[str, Any]) -> str:
    """Assemble the director system prompt from the base prompt, capability blocks, and promoted examples."""
    normalized = normalize_brief(brief)
    sections = [load_prompt("director_system").strip()]
    for name in _director_capability_prompt_names(normalized):
        content = load_optional_prompt(name).strip()
        if content:
            sections.append(content)
    examples = _selected_director_examples(normalized)
    if examples:
        sections.append("Promoted Cathode examples:\n\n" + "\n\n---\n\n".join(examples))
    return "\n\n".join(section for section in sections if section.strip())


def _normalize_director_data_points(scene: dict[str, Any], *, legacy_intent: dict[str, Any] | None = None) -> list[str]:
    raw = scene.get("data_points")
    if isinstance(raw, list):
        return [str(item).strip() for item in raw if str(item).strip()]
    if isinstance(legacy_intent, dict):
        data_points_raw = legacy_intent.get("data_points")
        if isinstance(data_points_raw, list):
            return [str(item).strip() for item in data_points_raw if str(item).strip()]
    return []


def _normalize_transition_hint(scene: dict[str, Any], *, legacy_intent: dict[str, Any] | None = None) -> str | None:
    candidate = str(scene.get("transition_hint") or "").strip().lower()
    if not candidate and isinstance(legacy_intent, dict):
        candidate = str(legacy_intent.get("transition_after") or "").strip().lower()
    return candidate if candidate in _TRANSITION_HINTS else None


def _normalize_staging_notes(scene: dict[str, Any], *, legacy_intent: dict[str, Any] | None = None) -> str | None:
    candidate = str(scene.get("staging_notes") or "").strip()
    if candidate:
        return candidate
    if isinstance(legacy_intent, dict):
        layout = str(legacy_intent.get("layout") or "").strip()
        motion_notes = str(legacy_intent.get("motion_notes") or "").strip()
        combined = " ".join(part for part in (layout, motion_notes) if part)
        return combined or None
    return None


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
  - "visual_prompt" (for image scenes: a self-contained image prompt; for video scenes: clear footage/clip direction; for motion scenes: an art-direction description of the beat)
- Optional scene fields:
  - "scene_type" ("image", "video", or "motion"; default to "image")
  - "video_scene_kind" ("cinematic" or "speaking" when scene_type is "video")
  - "speaker_name" (speaker or character label when a scene is voiced by a specific person)
  - "on_screen_text" (array of exact strings intended to be visible on the slide)
  - "footage_asset_id" (string id of a provided footage asset when a scene should use supplied video)
  - "staging_notes" (optional freeform note about layout, motion, reveals, callouts, pacing, or why the beat should feel motion-first)
  - "data_points" (optional array of ranked items, labels, or values when the scene is data-driven)
  - "transition_hint" (optional outgoing transition hint such as "fade" or "wipe")

Quality constraints:
- Keep narration conversational, vivid, and easy to follow for the specified audience.
- If a brand, product, or identifier contains digits and a TTS engine could misread it, rewrite it the way it should be spoken.
- If the brief asks for multiple voices, recurring characters, or a narrator plus other speakers, use "speaker_name" consistently so downstream voice planning can keep the same person on the same voice across scenes.
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
- Use scene_type "motion" when the beat should be deterministically staged as a text-led or data-led Remotion beat instead of relying on authored text inside an image.
- If style_reference_summary is present, treat it as the canonical visual direction and make every scene compatible with that style while still matching the scene's content.
- Use staging_notes, data_points, and transition_hint when a scene should clearly behave as a motion-first beat, a screenshot/demo callout, a data-stage visualization, or a richer staged layout than a plain still.
- Treat visual_source_strategy as a hard preference:
  - "images_only": keep all scenes as image scenes.
  - "mixed_media": use video scenes only where footage would clearly improve the explanation.
  - "video_preferred": prefer video scenes when the brief or available footage supports them.
- Treat video_scene_style as a planning preference whenever you choose generated video scenes:
  - "auto": choose the right mix from the brief itself
  - "cinematic": prefer action, movement, atmosphere, and b-roll style clips
  - "speaking": prefer direct-to-camera spokesperson or interview-style clips
  - "mixed": use both cinematic and speaking clips when they each materially help
- When available_footage is provided, use it to decide which scenes could realistically be video scenes.
- Use "video_scene_kind" intentionally on generated video scenes:
  - "speaking": a real person should plausibly be on camera delivering the words or a very close paraphrase
  - "cinematic": the clip is visual action or atmosphere that supports voiceover without lip-sync pressure
- For motion scenes:
  - keep the narration natural and viewer-facing, not like animation instructions
  - use on_screen_text for exact visible copy
  - use staging_notes to describe the motion, reveals, callouts, or camera-feel of the beat
  - use data_points when the beat depends on an ordered comparison, ranking, or structured values
- For "speaking" video scenes:
  - narration should sound like something a spokesperson could say naturally to camera
  - visual_prompt should describe one visible speaker, framing, gestures, wardrobe, setting, and camera treatment
- For "cinematic" video scenes:
  - visual_prompt should describe movement, action, setting, and camera language rather than a lip-synced talker
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
    if isinstance(source, dict):
        brief = normalize_brief(source)
    else:
        brief = _legacy_brief_from_text(str(source or ""))

    return generate_storyboard_with_metadata(source, provider=provider)[0]


def _response_usage_value(usage: Any, key: str) -> int | None:
    if usage is None:
        return None
    if isinstance(usage, dict):
        value = usage.get(key)
    else:
        value = getattr(usage, key, None)
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _llm_call_metadata(
    *,
    provider: Literal["openai", "anthropic"],
    model: str,
    operation: str,
    system_prompt: str,
    user_prompt: str,
    response: Any,
) -> dict[str, Any]:
    usage = getattr(response, "usage", None) or (response.get("usage") if isinstance(response, dict) else None)
    input_tokens = _response_usage_value(usage, "input_tokens")
    output_tokens = _response_usage_value(usage, "output_tokens")
    return {
        "provider": provider,
        "model": model,
        "operation": operation,
        "preflight": llm_preflight_entry(
            provider=provider,
            model=model,
            operation=operation,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        ),
        "actual": llm_actual_entry(
            provider=provider,
            model=model,
            operation=operation,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        ),
    }


def generate_storyboard_with_metadata(
    source: str | dict[str, Any],
    provider: Literal["openai", "anthropic"] = "openai",
) -> tuple[list[dict], dict[str, Any]]:
    """Generate storyboard scenes and return cost-aware LLM metadata."""
    if isinstance(source, dict):
        brief = normalize_brief(source)
    else:
        brief = _legacy_brief_from_text(str(source or ""))

    system_prompt = build_director_system_prompt(brief)
    user_prompt = _build_storyboard_user_prompt_from_brief(brief)

    if provider == "openai":
        scenes, response = _generate_with_openai(system_prompt, user_prompt, return_response=True)
        return scenes, _llm_call_metadata(
            provider="openai",
            model=_OPENAI_DIRECTOR_MODEL,
            operation="storyboard",
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response=response,
        )
    if provider == "anthropic":
        scenes, response = _generate_with_anthropic(system_prompt, user_prompt, return_response=True)
        return scenes, _llm_call_metadata(
            provider="anthropic",
            model=_ANTHROPIC_DIRECTOR_MODEL,
            operation="storyboard",
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response=response,
        )
    raise ValueError(f"Unknown provider: {provider}")


def generate_storyboard_from_text(
    input_text: str,
    provider: Literal["openai", "anthropic"] = "openai",
) -> list[dict]:
    """Compatibility wrapper for callers that still pass raw source text."""
    return generate_storyboard(_legacy_brief_from_text(input_text), provider=provider)


def storyboard_tool_schema() -> dict[str, Any]:
    """Return the structured Anthropic tool schema for storyboard generation."""
    return {
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
                            "scene_type": {"type": "string", "enum": ["image", "video", "motion"]},
                            "video_scene_kind": {"type": "string", "enum": ["cinematic", "speaking"]},
                            "speaker_name": {"type": "string"},
                            "footage_asset_id": {"type": "string"},
                            "staging_notes": {"type": "string"},
                            "data_points": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                            "transition_hint": {"type": "string", "enum": ["fade", "wipe"]},
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


def extract_storyboard_tool_input(content: list[Any]) -> Any:
    """Extract the Anthropic storyboard tool input from SDK or raw API response content."""
    for block in content:
        block_type = getattr(block, "type", None)
        if block_type is None and isinstance(block, dict):
            block_type = block.get("type")
        block_name = getattr(block, "name", None)
        if block_name is None and isinstance(block, dict):
            block_name = block.get("name")
        if block_type == "tool_use" and block_name == "emit_storyboard":
            if isinstance(block, dict):
                return block.get("input")
            return getattr(block, "input", None)
    return None


def extract_scenes_array(result: Any) -> list[dict]:
    """Extract the scenes list from either a direct array or a wrapped object."""
    if isinstance(result, list):
        return result
    if isinstance(result, dict) and isinstance(result.get("scenes"), list):
        return result["scenes"]
    if isinstance(result, dict):
        for value in result.values():
            if isinstance(value, list):
                return value
    raise ValueError("Could not find scenes array in response")


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

    return analyze_style_references_with_metadata(image_paths, brief, provider=provider)[0]


def analyze_style_references_with_metadata(
    image_paths: list[str | Path],
    brief: dict[str, Any],
    *,
    provider: Literal["openai", "anthropic"] = "openai",
) -> tuple[str, dict[str, Any]]:
    """Summarize style references and return LLM usage metadata."""
    normalized_brief = normalize_brief(brief)
    valid_paths = [Path(p) for p in image_paths if Path(p).exists()]
    if not valid_paths:
        return "", {}

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
            model=_OPENAI_DIRECTOR_MODEL,
            instructions=system_prompt,
            input=[{"role": "user", "content": content}],
            temperature=0.3,
        )
        return response.output_text.strip(), _llm_call_metadata(
            provider="openai",
            model=_OPENAI_DIRECTOR_MODEL,
            operation="style_reference_analysis",
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response=response,
        )

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
            model=_ANTHROPIC_DIRECTOR_MODEL,
            max_tokens=2500,
            system=system_prompt,
            messages=[{"role": "user", "content": content}],
        )
        text_block = next((b for b in response.content if hasattr(b, "text")), None)
        if not text_block:
            raise ValueError("No text response from model")
        return text_block.text.strip(), _llm_call_metadata(
            provider="anthropic",
            model=_ANTHROPIC_DIRECTOR_MODEL,
            operation="style_reference_analysis",
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response=response,
        )

    raise ValueError(f"Unknown provider: {provider}")


def _generate_with_openai(system_prompt: str, user_prompt: str, *, return_response: bool = False) -> list[dict] | tuple[list[dict], Any]:
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
    scenes = _validate_scenes(extract_scenes_array(result))
    if return_response:
        return scenes, response
    return scenes


def _generate_with_anthropic(system_prompt: str, user_prompt: str, *, return_response: bool = False) -> list[dict] | tuple[list[dict], Any]:
    """Generate storyboard using Anthropic Claude Sonnet 4.6 with forced structured tool output."""
    client = _get_anthropic_client()

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=12000,
        system=system_prompt,
        messages=[
            {"role": "user", "content": user_prompt},
        ],
        tools=[storyboard_tool_schema()],
        tool_choice={"type": "tool", "name": "emit_storyboard"},
    )

    tool_input = extract_storyboard_tool_input(response.content)
    if not tool_input:
        raise ValueError("No structured storyboard tool output from Anthropic")
    scenes = _validate_scenes(extract_scenes_array(tool_input))
    if return_response:
        return scenes, response
    return scenes


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

        composition_intent_raw = scene.get("composition_intent")
        composition_intent = None
        if isinstance(composition_intent_raw, dict):
            family_hint = str(composition_intent_raw.get("family_hint") or "").strip()
            mode_hint = str(composition_intent_raw.get("mode_hint") or "").strip().lower()
            layout = str(composition_intent_raw.get("layout") or "").strip()
            motion_notes = str(composition_intent_raw.get("motion_notes") or "").strip()
            transition_after = str(composition_intent_raw.get("transition_after") or "").strip().lower()
            data_points_raw = composition_intent_raw.get("data_points")
            data_points = (
                [str(item).strip() for item in data_points_raw if str(item).strip()]
                if isinstance(data_points_raw, list)
                else []
            )
            composition_intent = {
                "family_hint": family_hint or None,
                "mode_hint": mode_hint if mode_hint in {"none", "overlay", "native"} else None,
                "layout": layout or None,
                "motion_notes": motion_notes or None,
                "transition_after": transition_after or None,
                "data_points": data_points,
            }

        data_points = _normalize_director_data_points(scene, legacy_intent=composition_intent)
        transition_hint = _normalize_transition_hint(scene, legacy_intent=composition_intent)
        staging_notes = _normalize_staging_notes(scene, legacy_intent=composition_intent)

        validated.append(
            {
                "id": scene.get("id", i),
                "uid": scene.get("uid", str(uuid.uuid4())[:8]),
                "title": scene.get("title", f"Scene {i + 1}"),
                "narration": narration,
                "visual_prompt": visual_prompt,
                "scene_type": str(scene.get("scene_type") or "image").strip().lower(),
                "video_scene_kind": str(scene.get("video_scene_kind") or "").strip().lower() or None,
                "speaker_name": str(scene.get("speaker_name") or "").strip() or None,
                "footage_asset_id": str(scene.get("footage_asset_id") or "").strip() or None,
                "staging_notes": staging_notes,
                "data_points": data_points,
                "transition_hint": transition_hint,
                "composition_intent": composition_intent,
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
    return refine_prompt_with_metadata(
        original_prompt,
        feedback,
        narration=narration,
        provider=provider,
    )[0]


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
    return refine_narration_with_metadata(
        original_narration,
        feedback,
        provider=provider,
    )[0]


def refine_prompt_with_metadata(
    original_prompt: str,
    feedback: str,
    narration: str = "",
    provider: Literal["openai", "anthropic"] = "openai",
) -> tuple[str, dict[str, Any]]:
    """Refine an image prompt and return LLM usage metadata."""
    system_prompt = load_prompt("refiner_system")
    narration_context = f"\nScene narration (for context): {narration}\n" if narration else ""
    user_prompt = f"""Original prompt: {original_prompt}
{narration_context}
User feedback: {feedback}

Please provide the refined prompt."""

    if provider == "openai":
        client = _get_openai_client()
        response = client.responses.create(
            model=_OPENAI_DIRECTOR_MODEL,
            instructions=system_prompt,
            input=user_prompt,
            temperature=0.7,
        )
        return response.output_text.strip(), _llm_call_metadata(
            provider="openai",
            model=_OPENAI_DIRECTOR_MODEL,
            operation="refine_prompt",
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response=response,
        )

    if provider == "anthropic":
        client = _get_anthropic_client()
        response = client.messages.create(
            model=_ANTHROPIC_DIRECTOR_MODEL,
            max_tokens=2048,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        text_block = next((b for b in response.content if hasattr(b, "text")), None)
        if not text_block:
            raise ValueError("No text response from model")
        return text_block.text.strip(), _llm_call_metadata(
            provider="anthropic",
            model=_ANTHROPIC_DIRECTOR_MODEL,
            operation="refine_prompt",
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response=response,
        )

    raise ValueError(f"Unknown provider: {provider}")


def refine_narration_with_metadata(
    original_narration: str,
    feedback: str,
    provider: Literal["openai", "anthropic"] = "openai",
) -> tuple[str, dict[str, Any]]:
    """Refine narration and return LLM usage metadata."""
    system_prompt = load_prompt("refiner_narration_system")
    user_prompt = f"""Original narration: {original_narration}

User feedback: {feedback}

Please provide the refined narration."""

    if provider == "openai":
        client = _get_openai_client()
        response = client.responses.create(
            model=_OPENAI_DIRECTOR_MODEL,
            instructions=system_prompt,
            input=user_prompt,
            temperature=0.7,
        )
        return response.output_text.strip(), _llm_call_metadata(
            provider="openai",
            model=_OPENAI_DIRECTOR_MODEL,
            operation="refine_narration",
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response=response,
        )

    if provider == "anthropic":
        client = _get_anthropic_client()
        response = client.messages.create(
            model=_ANTHROPIC_DIRECTOR_MODEL,
            max_tokens=2048,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        text_block = next((b for b in response.content if hasattr(b, "text")), None)
        if not text_block:
            raise ValueError("No text response from model")
        return text_block.text.strip(), _llm_call_metadata(
            provider="anthropic",
            model=_ANTHROPIC_DIRECTOR_MODEL,
            operation="refine_narration",
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response=response,
        )

    raise ValueError(f"Unknown provider: {provider}")
