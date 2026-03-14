"""Cost catalog, estimation, and actual-cost ledger helpers."""

from __future__ import annotations

import copy
import math
import os
from typing import Any

from .project_schema import normalize_brief
from .runtime import resolve_image_profile, resolve_tts_profile, resolve_video_profile
from .video_gen import estimate_scene_duration_seconds, resolve_replicate_video_generation_route

COST_CATALOG_VERSION = "2026-03-14"
DEFAULT_CNY_TO_USD = 1.0 / 6.9

_USD = "USD"
_CNY = "CNY"

_ENTRY_DEFS: list[dict[str, Any]] = [
    {
        "kind": "llm",
        "provider": "anthropic",
        "model": "claude-sonnet-4-6",
        "label": "Anthropic Claude Sonnet 4.6",
        "pricing_type": "per_million_tokens",
        "input_unit_amount": 3.0,
        "output_unit_amount": 15.0,
        "currency": _USD,
        "source_url": "https://www.anthropic.com/pricing#api",
        "gating": False,
    },
    {
        "kind": "llm",
        "provider": "openai",
        "model": "gpt-5.1",
        "label": "OpenAI GPT-5.1",
        "pricing_type": "per_million_tokens",
        "input_unit_amount": 15.0,
        "output_unit_amount": 120.0,
        "currency": _USD,
        "source_url": "https://openai.com/api/pricing/",
        "gating": False,
    },
    {
        "kind": "image_generation",
        "provider": "replicate",
        "model": "qwen/qwen-image-2512",
        "label": "Qwen Image 2512",
        "pricing_type": "per_image",
        "unit_amount": 0.02,
        "currency": _USD,
        "source_url": "https://replicate.com/qwen/qwen-image-2512/api",
        "gating": True,
    },
    {
        "kind": "image_edit",
        "provider": "replicate",
        "model": "qwen/qwen-image-edit-2511",
        "label": "Qwen Image Edit 2511",
        "pricing_type": "per_image",
        "unit_amount": 0.03,
        "currency": _USD,
        "source_url": "https://replicate.com/qwen/qwen-image-edit-2511/api",
        "gating": True,
    },
    {
        "kind": "image_edit",
        "provider": "dashscope",
        "model": "qwen-image-edit",
        "label": "Qwen Image Edit (DashScope)",
        "pricing_type": "per_image",
        "unit_amount": 0.220177,
        "currency": _CNY,
        "source_url": "https://help.aliyun.com/zh/model-studio/image-editing-api-reference",
        "gating": True,
    },
    {
        "kind": "image_edit",
        "provider": "dashscope",
        "model": "qwen-image-edit-plus",
        "label": "Qwen Image Edit Plus (DashScope)",
        "pricing_type": "per_image",
        "unit_amount": 0.330266,
        "currency": _CNY,
        "source_url": "https://help.aliyun.com/zh/model-studio/image-editing-api-reference",
        "gating": True,
    },
    {
        "kind": "video_generation",
        "provider": "replicate",
        "model": "kwaivgi/kling-v3-video",
        "variant": "cinematic_standard",
        "label": "Kling v3 cinematic / standard",
        "pricing_type": "per_second",
        "unit_amount": 0.168,
        "currency": _USD,
        "source_url": "https://replicate.com/kwaivgi/kling-v3-video/api",
        "gating": True,
    },
    {
        "kind": "video_generation",
        "provider": "replicate",
        "model": "kwaivgi/kling-v3-video",
        "variant": "cinematic_standard_audio",
        "label": "Kling v3 cinematic / standard + audio",
        "pricing_type": "per_second",
        "unit_amount": 0.252,
        "currency": _USD,
        "source_url": "https://replicate.com/kwaivgi/kling-v3-video/api",
        "gating": True,
    },
    {
        "kind": "video_generation",
        "provider": "replicate",
        "model": "kwaivgi/kling-v3-video",
        "variant": "cinematic_pro",
        "label": "Kling v3 cinematic / pro",
        "pricing_type": "per_second",
        "unit_amount": 0.224,
        "currency": _USD,
        "source_url": "https://replicate.com/kwaivgi/kling-v3-video/api",
        "gating": True,
    },
    {
        "kind": "video_generation",
        "provider": "replicate",
        "model": "kwaivgi/kling-v3-video",
        "variant": "cinematic_pro_audio",
        "label": "Kling v3 cinematic / pro + audio",
        "pricing_type": "per_second",
        "unit_amount": 0.336,
        "currency": _USD,
        "source_url": "https://replicate.com/kwaivgi/kling-v3-video/api",
        "gating": True,
    },
    {
        "kind": "video_generation",
        "provider": "replicate",
        "model": "kwaivgi/kling-avatar-v2",
        "variant": "speaking_standard",
        "label": "Kling Avatar v2 / standard",
        "pricing_type": "per_second",
        "unit_amount": 0.056,
        "currency": _USD,
        "source_url": "https://replicate.com/kwaivgi/kling-avatar-v2/api",
        "gating": True,
    },
    {
        "kind": "video_generation",
        "provider": "replicate",
        "model": "kwaivgi/kling-avatar-v2",
        "variant": "speaking_pro",
        "label": "Kling Avatar v2 / pro",
        "pricing_type": "per_second",
        "unit_amount": 0.11,
        "currency": _USD,
        "source_url": "https://replicate.com/kwaivgi/kling-avatar-v2/api",
        "gating": True,
    },
    {
        "kind": "tts",
        "provider": "elevenlabs",
        "model": "eleven_multilingual_v2",
        "label": "ElevenLabs Multilingual v2",
        "pricing_type": "per_thousand_characters",
        "unit_amount": 0.12,
        "currency": _USD,
        "source_url": "https://elevenlabs.io/pricing",
        "gating": True,
    },
    {
        "kind": "tts",
        "provider": "replicate",
        "model": "elevenlabs/turbo-v2.5",
        "label": "ElevenLabs Turbo v2.5 (Replicate)",
        "pricing_type": "per_thousand_characters",
        "unit_amount": 0.05,
        "currency": _USD,
        "source_url": "https://replicate.com/elevenlabs/turbo-v2.5/api",
        "gating": True,
    },
    {
        "kind": "tts",
        "provider": "openai",
        "model": "tts-1",
        "label": "OpenAI TTS-1",
        "pricing_type": "per_million_characters",
        "unit_amount": 15.0,
        "currency": _USD,
        "source_url": "https://openai.com/api/pricing/",
        "gating": True,
    },
    {
        "kind": "tts",
        "provider": "replicate",
        "model": "resemble-ai/chatterbox",
        "label": "Chatterbox (Replicate)",
        "pricing_type": "per_thousand_characters",
        "unit_amount": 0.025,
        "currency": _USD,
        "source_url": "https://replicate.com/resemble-ai/chatterbox/api",
        "gating": True,
    },
]


def _cny_to_usd_rate() -> float:
    raw = str(os.getenv("CATHODE_CNY_TO_USD") or "").strip()
    try:
        value = float(raw)
    except (TypeError, ValueError):
        value = DEFAULT_CNY_TO_USD
    return value if value > 0 else DEFAULT_CNY_TO_USD


def _money(value: float) -> float:
    return round(float(value), 4)


def _normalize_currency_to_usd(amount: float, currency: str) -> float:
    if str(currency or _USD).upper() == _USD:
        return _money(amount)
    if str(currency or "").upper() == _CNY:
        return _money(float(amount) * _cny_to_usd_rate())
    return _money(amount)


def _display_amount(entry: dict[str, Any]) -> str:
    pricing_type = str(entry.get("pricing_type") or "").strip().lower()
    currency = str(entry.get("currency") or _USD).upper()
    unit_amount = entry.get("unit_amount")
    if pricing_type == "per_million_tokens":
        return f"${entry['input_unit_amount']:.2f}/M input, ${entry['output_unit_amount']:.2f}/M output"
    if unit_amount in (None, ""):
        return "Pricing varies"
    symbol = "$" if currency == _USD else "¥"
    if pricing_type == "per_image":
        return f"{symbol}{float(unit_amount):.3f} / image"
    if pricing_type == "per_second":
        return f"{symbol}{float(unit_amount):.3f} / sec"
    if pricing_type == "per_thousand_characters":
        return f"{symbol}{float(unit_amount):.3f} / 1K chars"
    if pricing_type == "per_million_characters":
        return f"{symbol}{float(unit_amount):.2f} / 1M chars"
    return f"{symbol}{float(unit_amount):.3f}"


def cost_catalog_entries() -> list[dict[str, Any]]:
    entries = copy.deepcopy(_ENTRY_DEFS)
    for entry in entries:
        entry["display_price"] = _display_amount(entry)
        if str(entry.get("currency") or _USD).upper() == _CNY:
            entry["unit_amount_usd"] = _normalize_currency_to_usd(float(entry.get("unit_amount") or 0.0), _CNY)
    return entries


def frontend_cost_catalog() -> dict[str, Any]:
    return {
        "version": COST_CATALOG_VERSION,
        "entries": cost_catalog_entries(),
        "fx": {
            "cny_to_usd": _money(_cny_to_usd_rate()),
        },
    }


def _find_entry(
    *,
    kind: str,
    provider: str,
    model: str,
    variant: str | None = None,
) -> dict[str, Any] | None:
    provider_name = str(provider or "").strip().lower()
    model_name = str(model or "").strip()
    variant_name = str(variant or "").strip().lower() or None
    for entry in _ENTRY_DEFS:
        if str(entry.get("kind") or "") != kind:
            continue
        if str(entry.get("provider") or "").strip().lower() != provider_name:
            continue
        if str(entry.get("model") or "").strip() != model_name:
            continue
        if variant_name is not None and str(entry.get("variant") or "").strip().lower() != variant_name:
            continue
        if variant_name is None and entry.get("variant"):
            continue
        result = copy.deepcopy(entry)
        result["display_price"] = _display_amount(result)
        if str(result.get("currency") or _USD).upper() == _CNY:
            result["unit_amount_usd"] = _normalize_currency_to_usd(float(result.get("unit_amount") or 0.0), _CNY)
        return result
    return None


def _estimate_tokens(text: str) -> int:
    cleaned = str(text or "")
    if not cleaned:
        return 0
    return max(1, math.ceil(len(cleaned) / 4))


def llm_preflight_entry(
    *,
    provider: str,
    model: str,
    operation: str,
    system_prompt: str,
    user_prompt: str,
) -> dict[str, Any] | None:
    entry = _find_entry(kind="llm", provider=provider, model=model)
    if not entry:
        return None
    input_tokens = _estimate_tokens(system_prompt) + _estimate_tokens(user_prompt)
    output_tokens = max(512, round(input_tokens * 0.7))
    total_usd = _money(
        (float(entry["input_unit_amount"]) * input_tokens / 1_000_000.0)
        + (float(entry["output_unit_amount"]) * output_tokens / 1_000_000.0)
    )
    return {
        "kind": "llm",
        "provider": provider,
        "model": model,
        "label": str(entry.get("label") or model),
        "operation": operation,
        "estimated": True,
        "gating": False,
        "source_url": entry.get("source_url"),
        "units": {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
        },
        "rates": {
            "input_per_million_usd": float(entry["input_unit_amount"]),
            "output_per_million_usd": float(entry["output_unit_amount"]),
        },
        "total_usd": total_usd,
    }


def llm_actual_entry(
    *,
    provider: str,
    model: str,
    operation: str,
    input_tokens: int | None,
    output_tokens: int | None,
) -> dict[str, Any] | None:
    entry = _find_entry(kind="llm", provider=provider, model=model)
    if not entry:
        return None
    resolved_input = max(0, int(input_tokens or 0))
    resolved_output = max(0, int(output_tokens or 0))
    total_usd = _money(
        (float(entry["input_unit_amount"]) * resolved_input / 1_000_000.0)
        + (float(entry["output_unit_amount"]) * resolved_output / 1_000_000.0)
    )
    return {
        "kind": "llm",
        "provider": provider,
        "model": model,
        "label": str(entry.get("label") or model),
        "operation": operation,
        "estimated": False,
        "gating": False,
        "source_url": entry.get("source_url"),
        "units": {
            "input_tokens": resolved_input,
            "output_tokens": resolved_output,
        },
        "rates": {
            "input_per_million_usd": float(entry["input_unit_amount"]),
            "output_per_million_usd": float(entry["output_unit_amount"]),
        },
        "total_usd": total_usd,
    }


def _scene_identifier(scene: dict[str, Any]) -> dict[str, Any]:
    return {
        "scene_id": scene.get("id"),
        "scene_uid": str(scene.get("uid") or ""),
        "scene_title": str(scene.get("title") or ""),
    }


def image_generation_entry(
    *,
    scene: dict[str, Any],
    provider: str,
    model: str,
    estimated: bool,
    operation: str,
    image_count: int = 1,
) -> dict[str, Any] | None:
    entry = _find_entry(kind="image_generation", provider=provider, model=model)
    if not entry:
        return None
    total_usd = _money(float(entry.get("unit_amount") or 0.0) * max(1, int(image_count)))
    return {
        "kind": "image_generation",
        "provider": provider,
        "model": model,
        "label": str(entry.get("label") or model),
        "operation": operation,
        "estimated": estimated,
        "gating": True,
        "source_url": entry.get("source_url"),
        "units": {"images": max(1, int(image_count))},
        "rates": {"per_image_usd": float(entry.get("unit_amount") or 0.0)},
        "total_usd": total_usd,
        **_scene_identifier(scene),
    }


def image_edit_entry(
    *,
    scene: dict[str, Any],
    provider: str,
    model: str,
    estimated: bool,
    operation: str,
    image_count: int = 1,
) -> dict[str, Any] | None:
    effective_provider = "dashscope" if model.startswith("qwen-image-edit") else provider
    entry = _find_entry(kind="image_edit", provider=effective_provider, model=model)
    if not entry:
        return None
    rate = float(entry.get("unit_amount_usd") or entry.get("unit_amount") or 0.0)
    total_usd = _money(rate * max(1, int(image_count)))
    return {
        "kind": "image_edit",
        "provider": effective_provider,
        "model": model,
        "label": str(entry.get("label") or model),
        "operation": operation,
        "estimated": estimated,
        "gating": True,
        "source_url": entry.get("source_url"),
        "units": {"images": max(1, int(image_count))},
        "rates": {"per_image_usd": rate},
        "total_usd": total_usd,
        **_scene_identifier(scene),
    }


def resolve_video_cost_context(
    *,
    scene: dict[str, Any],
    provider: str,
    model: str | None,
    model_selection_mode: str | None,
    quality_mode: str | None,
    generate_audio: bool | None,
) -> dict[str, Any]:
    provider_name = str(provider or "manual").strip().lower() or "manual"
    resolved_generate_audio = bool(True if generate_audio is None else generate_audio)
    resolved_quality = str(quality_mode or "standard").strip().lower() or "standard"
    resolved_model = str(model or "").strip()
    route_kind = str(scene.get("video_scene_kind") or "").strip().lower() or "cinematic"
    route_reason = ""
    if provider_name == "replicate":
        route = resolve_replicate_video_generation_route(
            scene,
            model=resolved_model,
            model_selection_mode=model_selection_mode,
            generate_audio=resolved_generate_audio,
        )
        resolved_model = route["model"]
        route_kind = route["route_kind"]
        route_reason = route["reason"]
    return {
        "provider": provider_name,
        "model": resolved_model,
        "route_kind": route_kind,
        "route_reason": route_reason,
        "quality_mode": resolved_quality if resolved_quality in {"standard", "pro"} else "standard",
        "generate_audio": resolved_generate_audio,
        "uses_clip_audio": provider_name == "replicate" and resolved_generate_audio,
    }


def video_generation_entry(
    *,
    scene: dict[str, Any],
    provider: str,
    model: str | None,
    model_selection_mode: str | None,
    quality_mode: str | None,
    generate_audio: bool | None,
    estimated: bool,
    operation: str,
    duration_seconds: float | None = None,
) -> dict[str, Any] | None:
    context = resolve_video_cost_context(
        scene=scene,
        provider=provider,
        model=model,
        model_selection_mode=model_selection_mode,
        quality_mode=quality_mode,
        generate_audio=generate_audio,
    )
    if context["provider"] != "replicate":
        return None
    variant = (
        f"cinematic_{context['quality_mode']}{'_audio' if context['uses_clip_audio'] else ''}"
        if context["route_kind"] == "cinematic"
        else f"speaking_{context['quality_mode']}"
    )
    entry = _find_entry(
        kind="video_generation",
        provider="replicate",
        model=str(context["model"] or ""),
        variant=variant,
    )
    if not entry:
        return None
    seconds = float(duration_seconds if duration_seconds is not None else estimate_scene_duration_seconds(scene))
    seconds = max(seconds, 1.0)
    total_usd = _money(float(entry.get("unit_amount") or 0.0) * seconds)
    return {
        "kind": "video_generation",
        "provider": "replicate",
        "model": str(context["model"] or ""),
        "label": str(entry.get("label") or context["model"] or "Video generation"),
        "operation": operation,
        "estimated": estimated,
        "gating": True,
        "source_url": entry.get("source_url"),
        "route_kind": context["route_kind"],
        "route_reason": context["route_reason"],
        "quality_mode": context["quality_mode"],
        "audio_mode": "clip" if context["uses_clip_audio"] else "narration",
        "units": {"seconds": _money(seconds)},
        "rates": {"per_second_usd": float(entry.get("unit_amount") or 0.0)},
        "total_usd": total_usd,
        **_scene_identifier(scene),
    }


def tts_entry(
    *,
    scene: dict[str, Any],
    provider: str,
    model: str | None,
    estimated: bool,
    operation: str,
    purpose: str,
    text: str,
) -> dict[str, Any] | None:
    provider_name = str(provider or "").strip().lower()
    model_name = str(model or "").strip()
    if provider_name == "kokoro":
        return None
    if provider_name == "elevenlabs":
        model_name = model_name or "eleven_multilingual_v2"
        entry = _find_entry(kind="tts", provider="elevenlabs", model=model_name)
        if entry is None and ("flash" in model_name or "turbo" in model_name):
            entry = {
                "label": model_name,
                "source_url": "https://elevenlabs.io/pricing",
                "unit_amount": 0.06,
            }
    elif provider_name == "openai":
        model_name = model_name or "tts-1"
        entry = _find_entry(kind="tts", provider="openai", model=model_name)
    elif provider_name == "chatterbox":
        entry = _find_entry(kind="tts", provider="replicate", model="resemble-ai/chatterbox")
        provider_name = "replicate"
        model_name = "resemble-ai/chatterbox"
    elif provider_name == "replicate" and model_name == "elevenlabs/turbo-v2.5":
        entry = _find_entry(kind="tts", provider="replicate", model=model_name)
    else:
        entry = None
    if not entry:
        return None
    characters = max(1, len(str(text or "")))
    pricing_type = str(entry.get("pricing_type") or "")
    if pricing_type == "per_thousand_characters":
        rate = float(entry.get("unit_amount") or 0.0)
        total_usd = _money(rate * characters / 1000.0)
        rates = {"per_thousand_characters_usd": rate}
    elif pricing_type == "per_million_characters":
        rate = float(entry.get("unit_amount") or 0.0)
        total_usd = _money(rate * characters / 1_000_000.0)
        rates = {"per_million_characters_usd": rate}
    else:
        return None
    return {
        "kind": "tts",
        "provider": provider_name,
        "model": model_name,
        "label": str(entry.get("label") or model_name or provider_name),
        "operation": operation,
        "estimated": estimated,
        "gating": True,
        "purpose": purpose,
        "source_url": entry.get("source_url"),
        "units": {"characters": characters},
        "rates": rates,
        "total_usd": total_usd,
        **_scene_identifier(scene),
    }


def append_actual_cost_entry(plan: dict[str, Any], entry: dict[str, Any] | None) -> dict[str, Any]:
    if not entry:
        return plan
    meta = plan.setdefault("meta", {})
    cost_actual = meta.get("cost_actual") if isinstance(meta.get("cost_actual"), dict) else {}
    entries = cost_actual.get("entries") if isinstance(cost_actual.get("entries"), list) else []
    entries = [*entries, copy.deepcopy(entry)]
    cost_actual["entries"] = entries
    cost_actual["version"] = COST_CATALOG_VERSION
    meta["cost_actual"] = cost_actual
    return plan


def summarize_cost_entries(entries: list[dict[str, Any]]) -> dict[str, Any]:
    total = 0.0
    gating_total = 0.0
    llm_total = 0.0
    breakdown = {
        "llm_total_usd": 0.0,
        "image_generation_total_usd": 0.0,
        "image_edit_total_usd": 0.0,
        "video_generation_total_usd": 0.0,
        "tts_total_usd": 0.0,
    }
    for entry in entries:
        amount = float(entry.get("total_usd") or 0.0)
        total += amount
        if entry.get("gating"):
            gating_total += amount
        if entry.get("kind") == "llm":
            llm_total += amount
            breakdown["llm_total_usd"] += amount
        elif entry.get("kind") == "image_generation":
            breakdown["image_generation_total_usd"] += amount
        elif entry.get("kind") == "image_edit":
            breakdown["image_edit_total_usd"] += amount
        elif entry.get("kind") == "video_generation":
            breakdown["video_generation_total_usd"] += amount
        elif entry.get("kind") == "tts":
            breakdown["tts_total_usd"] += amount
    return {
        "version": COST_CATALOG_VERSION,
        "currency": _USD,
        "total_usd": _money(total),
        "gating_total_usd": _money(gating_total),
        "llm_total_usd": _money(llm_total),
        "breakdown": {key: _money(value) for key, value in breakdown.items()},
        "entries": copy.deepcopy(entries),
    }


def estimate_plan_cost(plan: dict[str, Any]) -> dict[str, Any]:
    meta = plan.get("meta") if isinstance(plan.get("meta"), dict) else {}
    scenes = plan.get("scenes") if isinstance(plan.get("scenes"), list) else []
    brief = normalize_brief(meta.get("brief") or {})
    image_profile = resolve_image_profile(meta.get("image_profile"))
    video_profile = resolve_video_profile(meta.get("video_profile"))
    tts_profile = resolve_tts_profile(meta.get("tts_profile"))
    budget_raw = str(brief.get("paid_media_budget_usd") or "").strip()
    try:
        budget_usd = float(budget_raw) if budget_raw else None
    except ValueError:
        budget_usd = None
    entries: list[dict[str, Any]] = []
    provider = str(tts_profile.get("provider") or "kokoro").strip().lower()
    tts_model = (
        str(tts_profile.get("model_id") or "")
        if provider in {"elevenlabs", "openai"}
        else "resemble-ai/chatterbox"
        if provider == "chatterbox"
        else ""
    )
    for scene in scenes:
        if not isinstance(scene, dict):
            continue
        scene_type = str(scene.get("scene_type") or "image").strip().lower()
        if scene_type == "image":
            has_image = bool(str(scene.get("image_path") or "").strip())
            if not has_image:
                entry = image_generation_entry(
                    scene=scene,
                    provider=str(image_profile.get("provider") or "manual"),
                    model=str(image_profile.get("generation_model") or ""),
                    estimated=True,
                    operation="asset_pass",
                )
                if entry:
                    entries.append(entry)
        if scene_type == "video":
            has_video = bool(str(scene.get("video_path") or "").strip())
            context = resolve_video_cost_context(
                scene=scene,
                provider=str(video_profile.get("provider") or "manual"),
                model=str(video_profile.get("generation_model") or ""),
                model_selection_mode=str(video_profile.get("model_selection_mode") or "automatic"),
                quality_mode=str(video_profile.get("quality_mode") or "standard"),
                generate_audio=video_profile.get("generate_audio"),
            )
            if not has_video:
                entry = video_generation_entry(
                    scene=scene,
                    provider=context["provider"],
                    model=context["model"],
                    model_selection_mode=str(video_profile.get("model_selection_mode") or "automatic"),
                    quality_mode=context["quality_mode"],
                    generate_audio=context["generate_audio"],
                    estimated=True,
                    operation="asset_pass",
                )
                if entry:
                    entries.append(entry)
            if context["route_kind"] == "speaking":
                if not str(scene.get("video_reference_image_path") or "").strip():
                    entry = image_generation_entry(
                        scene=scene,
                        provider=str(image_profile.get("provider") or "manual"),
                        model=str(image_profile.get("generation_model") or ""),
                        estimated=True,
                        operation="video_reference_image",
                    )
                    if entry:
                        entries.append(entry)
                if not str(scene.get("video_reference_audio_path") or "").strip():
                    tts_cost = tts_entry(
                        scene=scene,
                        provider=provider,
                        model=tts_model,
                        estimated=True,
                        operation="video_reference_audio",
                        purpose="reference_audio",
                        text=str(scene.get("narration") or ""),
                    )
                    if tts_cost:
                        entries.append(tts_cost)
            elif not context["uses_clip_audio"] and not str(scene.get("audio_path") or "").strip():
                tts_cost = tts_entry(
                    scene=scene,
                    provider=provider,
                    model=tts_model,
                    estimated=True,
                    operation="asset_pass",
                    purpose="narration",
                    text=str(scene.get("narration") or ""),
                )
                if tts_cost:
                    entries.append(tts_cost)
        if scene_type in {"image", "motion"} and not str(scene.get("audio_path") or "").strip():
            tts_cost = tts_entry(
                scene=scene,
                provider=provider,
                model=tts_model,
                estimated=True,
                operation="asset_pass",
                purpose="narration",
                text=str(scene.get("narration") or ""),
            )
            if tts_cost:
                entries.append(tts_cost)

    summary = summarize_cost_entries(entries)
    gating_total = float(summary["gating_total_usd"])
    status = "unbudgeted"
    if budget_usd is not None:
        status = "over_budget" if gating_total > budget_usd + 1e-6 else "within_budget"
    summary.update(
        {
            "budget_usd": _money(budget_usd) if budget_usd is not None else None,
            "status": status,
        }
    )
    actual = meta.get("cost_actual") if isinstance(meta.get("cost_actual"), dict) else {}
    storyboard_preflight = actual.get("llm_preflight") if isinstance(actual.get("llm_preflight"), dict) else None
    if storyboard_preflight:
        summary["llm_preflight"] = copy.deepcopy(storyboard_preflight)
    return summary


def refresh_plan_costs(plan: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(plan, dict):
        return plan
    meta = plan.setdefault("meta", {})
    actual = meta.get("cost_actual") if isinstance(meta.get("cost_actual"), dict) else {}
    actual_entries = actual.get("entries") if isinstance(actual.get("entries"), list) else []
    refreshed_actual = summarize_cost_entries([entry for entry in actual_entries if isinstance(entry, dict)])
    if isinstance(actual.get("llm_preflight"), dict):
        refreshed_actual["llm_preflight"] = copy.deepcopy(actual["llm_preflight"])
    meta["cost_actual"] = refreshed_actual
    meta["cost_estimate"] = estimate_plan_cost(plan)
    meta["cost_catalog_version"] = COST_CATALOG_VERSION
    return plan
