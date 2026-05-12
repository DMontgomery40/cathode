"""Normalize storyboard scenes into reusable composition families."""

from __future__ import annotations

import re
from typing import Any

from .project_schema import normalize_brief, scene_composition_payload
from .remotion_render import infer_motion_template

_SOFTWARE_DEMO_SURFACE_HINTS = (
    "dashboard",
    "screen",
    "screenshot",
    "ui",
    "interface",
    "browser",
    "workspace",
    "console",
    "panel",
    "inspector",
    "timeline",
    "form",
    "modal",
    "save endpoint",
    "right panel",
)
_SOFTWARE_DEMO_OVERLAY_HINTS = (
    "callout",
    "callouts",
    "deterministic overlay",
    "overlay label",
    "overlay labels",
    "overlay callout",
    "overlay callouts",
    "tooltip",
    "highlight",
    "highlighted",
    "annotation",
    "annotated",
    "proof moment",
    "pointer",
    "pointing to",
    "focus ring",
    "label appears",
    "labels appear",
    "callout tag",
    "callout tags",
    "callout line",
    "callout lines",
)

_FAMILY_HINTS = {
    "static_media",
    "media_pan",
    "software_demo_focus",
    "kinetic_statements",
    "three_data_stage",
    "surreal_tableau_3d",
}
_MODE_HINTS = {"none", "overlay", "native"}
_TRANSITION_HINTS = {"fade", "wipe"}
_NATIVE_MOTION_HINTS = (
    "motion",
    "animated",
    "animation",
    "kinetic",
    "title card",
    "text-led",
    "text led",
    "statement",
    "quote",
    "roadmap",
    "step",
    "process",
    "comparison",
    "ranked",
    "ranking",
    "callout",
    "reveal",
)
_QUOTE_HINTS = ("quote", "testimonial", "testimony", "founder note", "customer quote")
_BULLET_HINTS = ("roadmap", "step", "steps", "process", "checklist", "workflow")
_DATA_HINTS = ("ranked", "ranking", "compare", "comparison", "top 3", "top three", "podium", "data stage")
_DATA_BAR_HINTS = ("bar chart", "bars", "column", "columns", "spike", "podium", "tallest")
_DATA_LINE_HINTS = ("line chart", "trend", "variable", "fluctuate", "fluctuation", "stable", "shifted", "trajectory")
_SURREAL_TABLEAU_STRONG_HINTS = (
    "3d",
    "three-dimensional",
    "three dimensional",
    "tableau",
    "hero scene",
    "hero tableau",
    "camera orbit",
    "slow orbit",
    "full orbit",
    "dolly around",
    "must-include hero",
)
_SURREAL_TABLEAU_SUPPORTING_HINTS = (
    "orbiting",
    "orbital",
    "surreal",
    "constellation",
    "volumetric fog",
    "theatrical lighting",
    "moon",
    "chamber",
    "filigree",
    "floating",
    "velvet",
    "symbolic",
    "dreamlike",
)
_SURREAL_PALETTE_HINTS = (
    "deep indigo",
    "indigo",
    "warm amber",
    "amber",
    "ivory",
    "brass",
    "gold",
    "violet",
    "midnight blue",
)
_LABELED_VALUE_RE = re.compile(r"(?P<label>[^:]+?):\s*(?P<value>-?\d+(?:\.\d+)?)")
_NUMERIC_RANGE_RE = re.compile(r"(?P<min>-?\d+(?:\.\d+)?)\s*(?:to|[–—-])\s*(?P<max>-?\d+(?:\.\d+)?)")
_CLINICAL_PATIENT_HINTS = (
    "patient",
    "patients",
    "clinician",
    "clinical",
    "medical",
    "assessment",
    "report",
    "findings",
    "results",
    "follow-up",
    "follow up",
)
_CLINICAL_DATA_HINTS = (
    "data",
    "metrics",
    "measure",
    "measurements",
    "test",
    "tests",
    "sessions",
    "reference range",
    "baseline",
    "scores",
    "results",
)


def _scene_text(scene: dict[str, Any]) -> str:
    parts = [
        scene.get("title"),
        scene.get("visual_prompt"),
        scene.get("narration"),
        " ".join(str(item) for item in (scene.get("on_screen_text") or []) if str(item).strip()),
    ]
    return "\n".join(str(value or "").strip() for value in parts if str(value or "").strip()).lower()


def _text_matches_hint(text: str, hint: str) -> bool:
    tokens = re.findall(r"[a-z0-9]+", str(hint or "").lower())
    if not tokens:
        return False
    pattern = r"\b" + r"[\s_-]+".join(re.escape(token) for token in tokens) + r"\b"
    return re.search(pattern, text) is not None


def _matching_hints(text: str, hints: tuple[str, ...]) -> list[str]:
    return [hint for hint in hints if _text_matches_hint(text, hint)]


def _has_any_hint(text: str, hints: tuple[str, ...]) -> bool:
    return any(_text_matches_hint(text, hint) for hint in hints)


def _normalize_composition_intent(scene: dict[str, Any]) -> dict[str, Any]:
    raw = scene.get("composition_intent") if isinstance(scene.get("composition_intent"), dict) else {}
    family_hint = str(raw.get("family_hint") or "").strip()
    mode_hint = str(raw.get("mode_hint") or "").strip().lower()
    layout = str(raw.get("layout") or "").strip()
    motion_notes = str(raw.get("motion_notes") or "").strip()
    transition_after = str(raw.get("transition_after") or "").strip().lower()
    data_points_raw = raw.get("data_points")
    data_points = (
        [str(item).strip() for item in data_points_raw if str(item).strip()]
        if isinstance(data_points_raw, list)
        else []
    )
    return {
        "family_hint": family_hint if family_hint in _FAMILY_HINTS else "",
        "mode_hint": mode_hint if mode_hint in _MODE_HINTS else "",
        "layout": layout,
        "motion_notes": motion_notes,
        "transition_after": transition_after,
        "data_points": data_points,
    }


def _normalized_transition_hint(scene: dict[str, Any], intent: dict[str, Any]) -> str:
    hint = str(scene.get("transition_hint") or "").strip().lower()
    if hint in _TRANSITION_HINTS:
        return hint
    return str(intent.get("transition_after") or "").strip().lower()


def _normalized_data_points(scene: dict[str, Any], intent: dict[str, Any]) -> list[str]:
    raw = scene.get("data_points")
    if isinstance(raw, list):
        normalized = [str(item).strip() for item in raw if str(item).strip()]
        if normalized:
            return normalized
    return intent["data_points"]


def _staging_notes(scene: dict[str, Any], intent: dict[str, Any]) -> str:
    notes = str(scene.get("staging_notes") or "").strip()
    if notes:
        return notes
    return " ".join(part for part in (intent.get("layout"), intent.get("motion_notes")) if str(part or "").strip()).strip()


def _director_scene_text(scene: dict[str, Any], intent: dict[str, Any]) -> str:
    notes = _staging_notes(scene, intent)
    parts = [
        _scene_text(scene),
        notes,
        " ".join(_normalized_data_points(scene, intent)),
        str(scene.get("transition_hint") or "").strip(),
    ]
    return "\n".join(part for part in parts if part).lower()


def _brief_text(brief: dict[str, Any] | None) -> str:
    normalized = normalize_brief(brief or {})
    parts = [
        normalized.get("video_goal"),
        normalized.get("audience"),
        normalized.get("source_material"),
        normalized.get("must_include"),
        normalized.get("must_avoid"),
        normalized.get("ending_cta"),
        normalized.get("raw_brief"),
    ]
    return "\n".join(str(value or "").strip() for value in parts if str(value or "").strip()).lower()


def _brief_prefers_authored_clinical_stills(brief: dict[str, Any] | None) -> bool:
    text = _brief_text(brief)
    if not text:
        return False
    has_patient_context = _has_any_hint(text, _CLINICAL_PATIENT_HINTS)
    has_data_context = _has_any_hint(text, _CLINICAL_DATA_HINTS) or "|---|" in text
    return has_patient_context and has_data_context


def _brief_allows_native_motion(brief: dict[str, Any] | None) -> bool:
    raw = brief if isinstance(brief, dict) else {}
    return (
        str(raw.get("composition_mode") or "").strip().lower() == "motion_only"
        or str(raw.get("text_render_mode") or "").strip().lower() == "deterministic_overlay"
    )


def _native_motion_requested(scene: dict[str, Any], intent: dict[str, Any]) -> bool:
    scene_type = str(scene.get("scene_type") or "").strip().lower()
    if scene_type == "motion":
        return True
    if intent["mode_hint"] == "native":
        return True
    if _normalized_data_points(scene, intent):
        return True
    notes = _staging_notes(scene, intent).lower()
    if not notes:
        return False
    return any(hint in notes for hint in _NATIVE_MOTION_HINTS)


def _clinical_native_motion_requested(scene: dict[str, Any], intent: dict[str, Any]) -> bool:
    scene_type = str(scene.get("scene_type") or "").strip().lower()
    if scene_type == "motion":
        return True
    if _normalized_data_points(scene, intent):
        return True
    notes = _staging_notes(scene, intent).lower()
    if not notes:
        return False
    return any(hint in notes for hint in _NATIVE_MOTION_HINTS)


def _count_matching_hints(text: str, hints: tuple[str, ...]) -> int:
    return len(_matching_hints(text, hints))


def _surreal_tableau_requested(scene: dict[str, Any], intent: dict[str, Any]) -> bool:
    text = _director_scene_text(scene, intent)
    if _normalized_data_points(scene, intent) and _has_any_hint(text, _DATA_HINTS):
        return False
    if _has_any_hint(text, _SOFTWARE_DEMO_SURFACE_HINTS):
        return False
    if _has_any_hint(text, _QUOTE_HINTS):
        return False
    if _has_any_hint(text, _BULLET_HINTS):
        return False

    strong_matches = _count_matching_hints(text, _SURREAL_TABLEAU_STRONG_HINTS)
    supporting_matches = _count_matching_hints(text, _SURREAL_TABLEAU_SUPPORTING_HINTS)
    return strong_matches >= 1 or supporting_matches >= 2


def _software_demo_focus_requested(scene: dict[str, Any], intent: dict[str, Any]) -> bool:
    if intent["family_hint"] == "software_demo_focus":
        return True

    text = _director_scene_text(scene, intent)
    if not _has_any_hint(text, _SOFTWARE_DEMO_SURFACE_HINTS):
        return False

    if intent["mode_hint"] == "overlay":
        return True

    return _has_any_hint(text, _SOFTWARE_DEMO_OVERLAY_HINTS)


def _surreal_layout_variant(scene: dict[str, Any], intent: dict[str, Any]) -> str:
    text = _director_scene_text(scene, intent)
    if _has_any_hint(text, ("orbiting", "orbital", "camera orbit", "slow orbit", "full orbit", "dolly around")):
        return "orbit_tableau"
    return "symbolic_duet"


def _pick_phrase(source: str, patterns: tuple[str, ...], fallback: str) -> str:
    lowered = source.lower()
    for pattern in patterns:
        if pattern not in lowered:
            continue
        if pattern == "hourglass" and "moon" in lowered:
            return "glowing cracked hourglass moon"
        if pattern == "moon":
            return "glowing moon"
        if pattern == "moth" and "brass" in lowered:
            return "brass moths"
        if pattern == "moth":
            return "moths"
        if pattern == "constellation":
            return "bending constellation lines"
        if pattern == "lichen":
            return "bioluminescent lichen"
        if pattern == "velvet":
            return "indigo velvet chamber"
    return fallback


def _surreal_environment_backdrop(scene: dict[str, Any], intent: dict[str, Any]) -> str:
    source = " ".join(
        value
        for value in (
            str(scene.get("visual_prompt") or "").strip(),
            _staging_notes(scene, intent),
        )
        if value
    )
    lowered = source.lower()
    if "chamber" in lowered and "indigo" in lowered and "velvet" in lowered:
        return "vast dark chamber with deep indigo velvet walls"
    if "chamber" in lowered:
        return "vast cinematic chamber"
    if "void" in lowered:
        return "dreamlike void space"
    if "stage" in lowered:
        return "symbolic theatrical stage"
    return "dreamlike cinematic chamber"


def _surreal_ambient_details(scene: dict[str, Any], intent: dict[str, Any]) -> str:
    source = " ".join(
        value
        for value in (
            str(scene.get("visual_prompt") or "").strip(),
            _staging_notes(scene, intent),
        )
        if value
    ).lower()
    details: list[str] = []
    if "lichen" in source:
        details.append("faint bioluminescent lichen")
    if "constellation" in source:
        details.append("bending constellation lines")
    if "fog" in source:
        details.append("subtle volumetric fog")
    if "shadow" in source:
        details.append("deep edge shadow")
    if "theatrical lighting" in source or "moonlight" in source:
        details.append("motivated theatrical lighting")
    if "filigree" in source:
        details.append("engraved filigree highlights")
    if details:
        return ", ".join(dict.fromkeys(details))
    return "layered atmospheric depth and motivated light falloff"


def _surreal_palette_words(scene: dict[str, Any], intent: dict[str, Any]) -> list[str]:
    text = _director_scene_text(scene, intent)
    palette = [hint for hint in _SURREAL_PALETTE_HINTS if hint in text]
    if palette:
        return list(dict.fromkeys(palette))
    return ["deep indigo", "warm amber", "ivory", "brass"]


def _surreal_camera_move(scene: dict[str, Any], intent: dict[str, Any]) -> str:
    text = _director_scene_text(scene, intent)
    if _has_any_hint(text, ("camera orbit", "slow orbit", "full orbit")):
        return "slow circular camera orbit"
    if _text_matches_hint(text, "dolly around"):
        return "slow circular dolly"
    if _has_any_hint(text, ("push in", "push-in")):
        return "slow push-in"
    return "slow deliberate camera drift"


def _surreal_orbit_count(scene: dict[str, Any], intent: dict[str, Any]) -> int:
    source = " ".join(
        value
        for value in (
            str(scene.get("visual_prompt") or "").strip(),
            _staging_notes(scene, intent),
        )
        if value
    ).lower()
    match = re.search(r"\b(six|seven|eight|6|7|8)\b", source)
    if not match:
        return 6
    value = match.group(1)
    return {
        "six": 6,
        "seven": 7,
        "eight": 8,
        "6": 6,
        "7": 7,
        "8": 8,
    }.get(value, 6)


def _surreal_tableau_props(scene: dict[str, Any], intent: dict[str, Any]) -> dict[str, Any]:
    source = " ".join(
        value
        for value in (
            str(scene.get("title") or "").strip(),
            str(scene.get("visual_prompt") or "").strip(),
            _staging_notes(scene, intent),
        )
        if value
    )
    layout_variant = _surreal_layout_variant(scene, intent)
    hero_object = _pick_phrase(source, ("hourglass", "moon"), "central hero object")
    orbiting_object = _pick_phrase(source, ("moth", "satellite", "planet"), "symbolic orbiters")
    secondary_object = _pick_phrase(source, ("constellation", "lichen", "velvet"), "symbolic counterform")
    return {
        "layoutVariant": layout_variant,
        "heroObject": hero_object,
        "secondaryObject": secondary_object,
        "orbitingObject": orbiting_object,
        "orbitCount": _surreal_orbit_count(scene, intent) if layout_variant == "orbit_tableau" else 0,
        "environmentBackdrop": _surreal_environment_backdrop(scene, intent),
        "ambientDetails": _surreal_ambient_details(scene, intent),
        "paletteWords": _surreal_palette_words(scene, intent),
        "cameraMove": _surreal_camera_move(scene, intent),
        "copyTreatment": "none",
    }


def _data_stage_source_lines(scene: dict[str, Any], intent: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    for item in _normalized_data_points(scene, intent):
        if item and item not in lines:
            lines.append(item)
    for item in (scene.get("on_screen_text") or []):
        value = str(item).strip()
        if value and value not in lines:
            lines.append(value)
    title = str(scene.get("title") or "").strip()
    if title and title not in lines:
        lines.append(title)
    return lines


def _data_stage_slug(value: str, fallback: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return slug or fallback


def _three_data_stage_layout_variant(scene: dict[str, Any], intent: dict[str, Any]) -> str:
    text = _director_scene_text(scene, intent)
    if any(_text_matches_hint(text, hint) for hint in _DATA_BAR_HINTS):
        if any(word in text for word in ("faster", "slower", "improvement", "delta", "difference")):
            return "bars_with_delta"
        return "bars_with_band"
    if any(word in text for word in ("shifted", "above range", "below range", "crosses the band", "crossing the band")):
        return "line_with_zones"
    if any(word in text for word in ("outlier", "dip", "exception", "session-specific")) or text.count("reference") >= 2:
        return "line_with_multi_band"
    if any(_text_matches_hint(text, hint) for hint in _DATA_LINE_HINTS):
        return "line_with_band"
    return "line_with_band"


def _three_data_stage_palette(scene: dict[str, Any], intent: dict[str, Any], layout_variant: str) -> str:
    text = _director_scene_text(scene, intent)
    if layout_variant == "line_with_zones":
        return "multi_zone_on_charcoal"
    if layout_variant == "bars_with_band" and any(word in text for word in ("spike", "above range", "amber", "charcoal")):
        return "teal_amber_on_charcoal"
    if layout_variant.startswith("line"):
        return "amber_on_navy"
    return "teal_on_navy"


def _three_data_stage_emphasis(scene: dict[str, Any], intent: dict[str, Any], layout_variant: str) -> str:
    text = _director_scene_text(scene, intent)
    if layout_variant == "bars_with_delta":
        return "start_end_comparison"
    if layout_variant == "bars_with_band":
        return "single_spike" if "spike" in text else "within_band_comparison"
    if layout_variant == "line_with_multi_band":
        return "start_end_and_outlier"
    if layout_variant == "line_with_zones":
        return "crossing_the_band"
    if "stable" in text or "within range" in text:
        return "fluctuation_within_band"
    if "variable" in text or "not a steady trend" in text:
        return "variability_over_time"
    return "trend_over_time"


_TARGET_PARENS_RE = re.compile(r"\(target[^)]*\)", re.IGNORECASE)
_ARROW_SPLIT_RE = re.compile(r"\s*(?:→|->|=>)\s*")
_LEADING_NUM_RE = re.compile(r"^-?\d+(?:\.\d+)?")


def _expand_arrow_lines_for_data_stage(
    data_points: list[str],
) -> tuple[list[str], list[str]]:
    """Expand arrow data_points into per-session labelled lines.

    Returns (expanded_lines, extra_band_lines).
    Example: "Trail Making A: 33s → 41s → 42s (target 38–65s)"
    → lines: ["Trail Making A — Session 1: 33", ...]
    → bands: ["Trail Making A target: 38–65"]
    """
    expanded: list[str] = []
    extra_bands: list[str] = []
    for dp in data_points:
        if not _ARROW_PAT.search(dp):
            expanded.append(dp)
            continue
        # Strip embedded (target ...) and capture it as a band line
        target_m = _TARGET_PARENS_RE.search(dp)
        if target_m:
            # Extract range from target parens for reference band
            range_m = _NUMERIC_RANGE_RE.search(target_m.group())
            if range_m:
                colon_idx = dp.find(":")
                metric = dp[:colon_idx].strip() if colon_idx >= 0 else "Target"
                extra_bands.append(f"{metric} target: {range_m.group('min')}–{range_m.group('max')}")
        clean = _TARGET_PARENS_RE.sub("", dp).strip()
        # Split on label: prefix
        colon_idx = clean.find(":")
        if colon_idx >= 0:
            metric_name = clean[:colon_idx].strip()
            values_part = clean[colon_idx + 1:].strip()
        else:
            metric_name = ""
            values_part = clean.strip()
        segments = _ARROW_SPLIT_RE.split(values_part)
        for idx, seg in enumerate(segments, 1):
            seg = seg.strip()
            num_m = _LEADING_NUM_RE.match(seg)
            if num_m:
                label = f"{metric_name} — Session {idx}" if metric_name else f"Session {idx}"
                expanded.append(f"{label}: {num_m.group()}")
    return expanded, extra_bands


def _three_data_stage_points(scene: dict[str, Any], intent: dict[str, Any]) -> list[dict[str, Any]]:
    points: list[dict[str, Any]] = []
    seen_labels: set[str] = set()
    # Expand arrow data_points (e.g. "Metric: 33s → 41s → 42s") into
    # per-session lines before the main extraction loop.
    raw_dp = _normalized_data_points(scene, intent)
    expanded_dp, _ = _expand_arrow_lines_for_data_stage(raw_dp)
    # Build source lines: expanded data_points + on_screen_text + title
    source_lines: list[str] = []
    for item in expanded_dp:
        if item and item not in source_lines:
            source_lines.append(item)
    data_point_boundary = len(source_lines)
    for item in (scene.get("on_screen_text") or []):
        value = str(item).strip()
        if value and value not in source_lines:
            source_lines.append(value)
    title = str(scene.get("title") or "").strip()
    if title and title not in source_lines:
        source_lines.append(title)
    for source_idx, line in enumerate(source_lines):
        if source_idx >= data_point_boundary and len(points) >= 2:
            break
        lowered = line.lower()
        if any(keyword in lowered for keyword in ("range", "band", "zone", "window")):
            continue
        # Skip lines that encode a numeric range (e.g. "Target: 8–20 µV") — those are bands not points.
        if _NUMERIC_RANGE_RE.search(lowered):
            continue
        match = _LABELED_VALUE_RE.search(line)
        if not match:
            continue
        label = re.sub(r"\s+", " ", match.group("label")).strip(" :-")
        if not label:
            continue
        key = label.lower()
        if key in seen_labels:
            continue
        seen_labels.add(key)
        points.append(
            {
                "x": label,
                "y": float(match.group("value")),
            }
        )
    return points


def _three_data_stage_reference_bands(scene: dict[str, Any], intent: dict[str, Any]) -> list[dict[str, Any]]:
    bands: list[dict[str, Any]] = []
    seen: set[tuple[float, float]] = set()
    for line in _data_stage_source_lines(scene, intent):
        lowered = line.lower()
        if not any(keyword in lowered for keyword in ("range", "band", "zone", "window", "target")):
            continue
        match = _NUMERIC_RANGE_RE.search(lowered)
        if not match:
            continue
        y_min = float(match.group("min"))
        y_max = float(match.group("max"))
        key = (min(y_min, y_max), max(y_min, y_max))
        if key in seen:
            continue
        seen.add(key)
        bands.append(
            {
                "id": _data_stage_slug(line, "reference"),
                "label": line,
                "yMin": min(y_min, y_max),
                "yMax": max(y_min, y_max),
            }
        )
    return bands


def _detect_panel_split(
    points: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]] | None:
    """Return (low_group, high_group) when points span two incompatible scales (>5× gap), else None."""
    numeric = [p for p in points if p.get("y") is not None]
    if len(numeric) < 4:
        return None
    sorted_vals = sorted(numeric, key=lambda p: p["y"])
    values = [p["y"] for p in sorted_vals]
    max_ratio = 1.0
    split_after = -1
    for i in range(len(values) - 1):
        lo, hi = values[i], values[i + 1]
        if lo > 0:
            ratio = hi / lo
            if ratio > max_ratio:
                max_ratio = ratio
                split_after = i
    if max_ratio < 5.0 or split_after < 0:
        return None
    threshold = (values[split_after] + values[split_after + 1]) / 2
    low_group = [p for p in points if p.get("y") is not None and p["y"] <= threshold]
    high_group = [p for p in points if p.get("y") is not None and p["y"] > threshold]
    if len(low_group) < 2 or len(high_group) < 2:
        return None
    return low_group, high_group


def _panel_titles_from_text(scene: dict[str, Any]) -> list[str]:
    """Extract non-numeric header lines from on_screen_text as panel titles."""
    titles = []
    for item in (scene.get("on_screen_text") or []):
        line = str(item).strip()
        if not line:
            continue
        if _LABELED_VALUE_RE.search(line):
            continue
        if _NUMERIC_RANGE_RE.search(line):
            continue
        titles.append(line)
    return titles


def _three_data_stage_callouts(scene: dict[str, Any], intent: dict[str, Any], points: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if len(points) < 2:
        return []
    for line in _data_stage_source_lines(scene, intent):
        lowered = line.lower()
        if any(keyword in lowered for keyword in ("faster", "slower", "difference", "delta", "improvement")):
            return [
                {
                    "id": _data_stage_slug(line, "delta"),
                    "fromX": points[0]["x"],
                    "toX": points[-1]["x"],
                    "label": line,
                }
            ]
    return []


def _three_data_stage_axis_label(points: list[dict[str, Any]]) -> str:
    labels = [str(point.get("x") or "").strip().lower() for point in points if str(point.get("x") or "").strip()]
    if labels and all(label.startswith("session") for label in labels):
        return "Session"
    if labels and all(label.startswith("rank") for label in labels):
        return "Rank"
    return "Category"


def _three_data_stage_value_label(scene: dict[str, Any]) -> str:
    title = str(scene.get("title") or "").strip()
    if ":" in title:
        return title.split(":", 1)[0].strip()
    lines = [str(item).strip() for item in (scene.get("on_screen_text") or []) if str(item).strip()]
    return lines[0] if lines else title or "Value"


def _three_data_stage_props(scene: dict[str, Any], intent: dict[str, Any]) -> dict[str, Any]:
    lines = [str(item).strip() for item in (scene.get("on_screen_text") or []) if str(item).strip()]
    title = str(scene.get("title") or "").strip()
    layout_variant = _three_data_stage_layout_variant(scene, intent)
    return {
        "headline": lines[0] if lines else title or "Data stage",
        "kicker": title or "Cathode",
        "layoutVariant": layout_variant,
        "emphasis": _three_data_stage_emphasis(scene, intent, layout_variant),
        "palette": _three_data_stage_palette(scene, intent, layout_variant),
    }


def _strip_common_series_prefix(series: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Strip a shared metric-name prefix from x-labels across all series.

    E.g. "F3/F4 Alpha Ratio — Session 1" → "Session 1" when every label
    shares the "F3/F4 Alpha Ratio" prefix.
    """
    _SEPS = (" — ", " - ", ": ")
    all_points = [
        pt for s in series if isinstance(s, dict) for pt in (s.get("points") or []) if isinstance(pt, dict)
    ]
    if len(all_points) < 2:
        return series
    # Find common prefix before a separator
    first_x = str(all_points[0].get("x") or "")
    prefix = ""
    sep_used = ""
    for sep in _SEPS:
        idx = first_x.find(sep)
        if idx > 0:
            candidate = first_x[:idx]
            if all(str(pt.get("x") or "").startswith(candidate + sep) for pt in all_points):
                prefix = candidate
                sep_used = sep
                break
    if not prefix:
        return series
    strip_len = len(prefix) + len(sep_used)
    cleaned = []
    for s in series:
        if not isinstance(s, dict):
            cleaned.append(s)
            continue
        new_points = []
        for pt in (s.get("points") or []):
            if not isinstance(pt, dict):
                new_points.append(pt)
                continue
            x = str(pt.get("x") or "")
            new_x = x[strip_len:].strip() if x.startswith(prefix + sep_used) else x
            new_points.append({**pt, "x": new_x or x})
        cleaned.append({**s, "points": new_points})
    return cleaned


def _infer_polarity(
    points: list[dict[str, Any]],
    reference_bands: list[dict[str, Any]],
) -> str | None:
    """Classify metric direction from first/last point position relative to band.

    Returns 'lower_is_better', 'higher_is_better', 'in_range_is_better', or None.
    """
    if not reference_bands or len(points) < 2:
        return None
    band = reference_bands[0]
    y_min, y_max = band["yMin"], band["yMax"]
    numeric = [p for p in points if p.get("y") is not None]
    if not numeric:
        return None
    first, last = numeric[0]["y"], numeric[-1]["y"]
    first_in = y_min <= first <= y_max
    last_in = y_min <= last <= y_max
    if first > y_max and last_in:
        return "lower_is_better"
    if first < y_min and last_in:
        return "higher_is_better"
    if first_in and last > y_max:
        return "lower_is_better"
    if first_in and last < y_min:
        return "higher_is_better"
    if first_in and last_in:
        return "in_range_is_better"
    # Both out of band on same side
    if first > y_max and last > y_max:
        return "lower_is_better" if last < first else None
    if first < y_min and last < y_min:
        return "higher_is_better" if last > first else None
    return "in_range_is_better"


def _three_data_stage_data(
    scene: dict[str, Any],
    intent: dict[str, Any],
    current_data: Any,
    props: dict[str, Any],
) -> Any:
    if isinstance(current_data, list):
        return current_data

    data = dict(current_data) if isinstance(current_data, dict) else {}
    data_points = _normalized_data_points(scene, intent)
    if data_points and not isinstance(data.get("data_points"), list):
        data["data_points"] = data_points

    points = _three_data_stage_points(scene, intent)
    reference_bands = _three_data_stage_reference_bands(scene, intent)
    layout_variant = str(props.get("layoutVariant") or "")
    chart_type: str = "bar" if layout_variant.startswith("bars") else "line"

    # Detect dual-metric scenes that need side-by-side panels with independent Y axes.
    if not isinstance(data.get("panels"), list):
        panel_split = _detect_panel_split(points)
        if panel_split is not None:
            low_group, high_group = panel_split
            panel_titles = _panel_titles_from_text(scene)

            # Derive better panel titles from metric prefixes in x labels
            # (e.g. "Trail Making A — Session 1" → "Trail Making A")
            def _group_metric_name(group: list[dict[str, Any]]) -> str | None:
                prefixes: list[str] = []
                for pt in group:
                    x = str(pt.get("x") or "")
                    for sep in (" — ", " - "):
                        idx = x.find(sep)
                        if idx > 0:
                            prefixes.append(x[:idx].strip())
                            break
                if prefixes and len(set(prefixes)) == 1:
                    return prefixes[0]
                return None

            for grp_idx, grp in enumerate([low_group, high_group]):
                metric = _group_metric_name(grp)
                if metric:
                    # Prefer metric name over generic on_screen_text headlines
                    if grp_idx < len(panel_titles):
                        panel_titles[grp_idx] = metric
                    else:
                        panel_titles.append(metric)

            def _band_distance(band: dict[str, Any], group: list[dict[str, Any]]) -> float:
                band_center = (band["yMin"] + band["yMax"]) / 2
                group_center = sum(p["y"] for p in group) / max(len(group), 1)
                return abs(band_center - group_center)

            panels = []
            for panel_idx, group in enumerate([low_group, high_group]):
                other = [high_group, low_group][panel_idx]
                title = panel_titles[panel_idx] if panel_idx < len(panel_titles) else f"Panel {panel_idx + 1}"
                panel_bands = [b for b in reference_bands if _band_distance(b, group) < _band_distance(b, other)]
                # Strip the panel title prefix from x labels so bars don't
                # redundantly repeat "P300 Strength — Session 1" when the
                # panel header already says "P300 Strength (µV)".
                clean_title = title.split("(")[0].strip().rstrip(":")
                cleaned_points = []
                for pt in group:
                    x = str(pt.get("x") or "")
                    for sep in (" — ", " - ", ": "):
                        if x.lower().startswith(clean_title.lower() + sep.lower()):
                            x = x[len(clean_title) + len(sep):].strip()
                            break
                        elif x.lower().startswith(clean_title.lower()):
                            x = x[len(clean_title):].lstrip(" —-:").strip()
                            break
                    cleaned_points.append({**pt, "x": x or pt.get("x", "")})
                panel_polarity = _infer_polarity(cleaned_points, panel_bands)
                panel_dict: dict[str, Any] = {
                    "id": f"panel_{panel_idx + 1}",
                    "title": title,
                    "series": [
                        {
                            "id": _data_stage_slug(title, f"series_{panel_idx}"),
                            "label": title,
                            "type": chart_type,
                            "points": cleaned_points,
                        }
                    ],
                    "referenceBands": panel_bands,
                    "yAxisLabel": title,
                }
                if panel_polarity:
                    panel_dict["polarity"] = panel_polarity
                panels.append(panel_dict)
            # Remove stale single-chart keys so they don't shadow the panels.
            for _k in ("series", "referenceBands", "callouts", "xAxisLabel", "yAxisLabel"):
                data.pop(_k, None)
            data["panels"] = panels
            return data

    # Single-chart path.
    # Replace the existing series when all y values are None (director
    # placeholder) AND we extracted real numeric points from data_points.
    existing_series = data.get("series")
    series_has_real_values = False
    if isinstance(existing_series, list):
        for s in existing_series:
            if isinstance(s, dict):
                for pt in (s.get("points") or []):
                    if isinstance(pt, dict) and pt.get("y") is not None:
                        series_has_real_values = True
                        break
            if series_has_real_values:
                break
    need_series = not isinstance(existing_series, list) or not series_has_real_values
    if len(points) >= 2 and need_series:
        value_label = _three_data_stage_value_label(scene)
        data["series"] = [
            {
                "id": _data_stage_slug(value_label, "series"),
                "label": value_label,
                "type": chart_type,
                "points": points,
            }
        ]
        data["xAxisLabel"] = _three_data_stage_axis_label(points)
        data["yAxisLabel"] = value_label
    elif isinstance(existing_series, list) and series_has_real_values:
        # Strip redundant metric-name prefixes from x-labels in existing
        # series (same logic the dual-panel path uses).  "F3/F4 Alpha
        # Ratio — Session 1" → "Session 1" when all labels share the prefix.
        data["series"] = _strip_common_series_prefix(existing_series)

    if reference_bands and not isinstance(data.get("referenceBands"), list):
        data["referenceBands"] = reference_bands

    # Infer polarity from data shape when not explicitly set by the director.
    all_bands = data.get("referenceBands") or reference_bands
    all_points = points
    if not all_points and isinstance(data.get("series"), list):
        for s in data["series"]:
            if isinstance(s, dict):
                all_points = s.get("points") or []
                break
    if all_bands and not data.get("polarity"):
        polarity = _infer_polarity(all_points, all_bands)
        if polarity:
            data["polarity"] = polarity

    callouts = _three_data_stage_callouts(scene, intent, points)
    if callouts and not isinstance(data.get("callouts"), list):
        data["callouts"] = callouts

    return data


def _motion_family_from_scene(scene: dict[str, Any], intent: dict[str, Any]) -> str:
    if intent["family_hint"]:
        return intent["family_hint"]
    text = _director_scene_text(scene, intent)
    if _normalized_data_points(scene, intent) and _has_any_hint(text, _DATA_HINTS):
        return "three_data_stage"
    if _software_demo_focus_requested(scene, intent):
        return "software_demo_focus"
    if _surreal_tableau_requested(scene, intent):
        return "surreal_tableau_3d"
    if _has_any_hint(text, _QUOTE_HINTS):
        return "quote_focus"
    if _has_any_hint(text, _BULLET_HINTS):
        return "bullet_stack"
    template = infer_motion_template(scene)
    if template == "three_data_stage":
        return "three_data_stage"
    if template == "bullet_stack":
        return "bullet_stack"
    return "kinetic_statements"


def _composition_props_from_scene(scene: dict[str, Any], intent: dict[str, Any], family: str) -> dict[str, Any]:
    lines = [str(item).strip() for item in (scene.get("on_screen_text") or []) if str(item).strip()]
    title = str(scene.get("title") or "").strip()
    narration = str(scene.get("narration") or "").strip()
    staging_notes = _staging_notes(scene, intent)
    headline = lines[0] if lines else title
    body = " ".join(lines[1:3]).strip() if len(lines) > 1 else narration[:180].strip()
    props: dict[str, Any] = {}
    # Clinical template families: prefer director-provided structured props, but
    # fall back to building them from on_screen_text / data_points when the
    # director only populated flat text.
    if family in _CLINICAL_TEMPLATE_FAMILIES:
        existing_props = (scene.get("composition") or {}).get("props") or {}
        if existing_props:
            props.update(existing_props)
        if "headline" not in props:
            props["headline"] = headline
        data_points = _scene_data_points(scene)
        _enrich_clinical_props(family, props, lines, data_points)
        return props

    if family in {"media_pan", "software_demo_focus", "kinetic_statements", "bullet_stack", "quote_focus"}:
        props["headline"] = headline
        if body:
            props["body"] = body
    if family in {"kinetic_statements", "bullet_stack"}:
        props["kicker"] = title or "Cathode"
        if lines[:4]:
            props["bullets"] = lines[:4]
        elif title:
            props["bullets"] = [title]
    if family == "quote_focus":
        props["kicker"] = title or "Cathode"
    if family == "three_data_stage":
        props.update(_three_data_stage_props(scene, intent))
    if family == "surreal_tableau_3d":
        props.update(_surreal_tableau_props(scene, intent))
    if staging_notes:
        if family == "surreal_tableau_3d":
            props["motionNotes"] = staging_notes
        else:
            props["layout"] = staging_notes
            props["motion_notes"] = staging_notes
    return props


_CLINICAL_TEMPLATE_FAMILIES = {
    "cover_hook", "orientation", "synthesis_summary", "closing_cta",
    "clinical_explanation", "metric_improvement", "brain_region_focus",
    "metric_comparison", "timeline_progression", "analogy_metaphor",
}

_ARROW_PAT = re.compile(r"[\u2192]|->|=>")


def _has_temporal_progression(data_points: list[str]) -> bool:
    """Return True if any data_point contains arrow notation (temporal series)."""
    return any(_ARROW_PAT.search(dp) for dp in data_points)


def _expand_arrow_data_points(data_points: list[str]) -> list[str]:
    """Convert 'Metric: v1 -> v2 -> v3' into per-session stage lines.

    Non-arrow lines are passed through unchanged.
    """
    expanded: list[str] = []
    for dp in data_points:
        if not _ARROW_PAT.search(dp):
            expanded.append(dp)
            continue
        # Split on label prefix if present (e.g. "F3/F4 Alpha Ratio: 0.8 -> 1.0")
        colon_idx = dp.find(":")
        if colon_idx >= 0:
            values_part = dp[colon_idx + 1:].strip()
        else:
            values_part = dp.strip()
        # Split on arrow tokens
        parts = re.split(r"\s*(?:[\u2192]|->|=>)\s*", values_part)
        parts = [p.strip() for p in parts if p.strip()]
        for i, val in enumerate(parts):
            expanded.append(f"Session {i + 1}: {val}")
    return expanded


_SESSION_LABEL_PAT = re.compile(r"session\s+\d", re.IGNORECASE)


def _has_session_labels(data_points: list[str]) -> bool:
    """Return True if data_points contain session-labeled values (e.g. 'Session 1: 6.9')."""
    count = sum(1 for dp in data_points if _SESSION_LABEL_PAT.search(dp))
    return count >= 2


def _reroute_family_by_data_shape(family: str, scene: dict[str, Any]) -> str:
    """Reroute families when data shape doesn't match the template.

    - metric_improvement + session data → three_data_stage (charts)
    - metric_comparison + temporal arrows → three_data_stage (charts)
    - brain_region_focus + temporal arrows → three_data_stage (charts)
    """
    if family == "metric_improvement":
        data_points = _scene_data_points(scene)
        if _has_temporal_progression(data_points):
            expanded = _expand_arrow_data_points(data_points)
            comp = scene.get("composition")
            if isinstance(comp, dict):
                data = comp.get("data")
                if isinstance(data, dict):
                    data["data_points"] = expanded
                else:
                    comp["data"] = {"data_points": expanded}
            return "three_data_stage"
        if _has_session_labels(data_points):
            # Already in "Session N: value" format — just reroute, no expansion needed
            return "three_data_stage"
        return family
    if family == "metric_comparison":
        data_points = _scene_data_points(scene)
        if _has_temporal_progression(data_points):
            expanded = _expand_arrow_data_points(data_points)
            comp = scene.get("composition")
            if isinstance(comp, dict):
                data = comp.get("data")
                if isinstance(data, dict):
                    data["data_points"] = expanded
                else:
                    comp["data"] = {"data_points": expanded}
            return "three_data_stage"
        if _has_session_labels(data_points):
            return "three_data_stage"
        return family
    if family != "brain_region_focus":
        return family
    data_points = _scene_data_points(scene)
    if _has_temporal_progression(data_points):
        expanded = _expand_arrow_data_points(data_points)
        comp = scene.get("composition")
        if isinstance(comp, dict):
            data = comp.get("data")
            if isinstance(data, dict):
                data["data_points"] = expanded
            else:
                comp["data"] = {"data_points": expanded}
            props = comp.get("props")
            if isinstance(props, dict):
                bg = props.get("background_id", "")
                if "brain" in bg.lower():
                    del props["background_id"]
        return "three_data_stage"
    if _has_session_labels(data_points):
        comp = scene.get("composition")
        if isinstance(comp, dict):
            props = comp.get("props")
            if isinstance(props, dict):
                bg = props.get("background_id", "")
                if "brain" in bg.lower():
                    del props["background_id"]
        return "three_data_stage"
    return family


def _scene_data_points(scene: dict[str, Any]) -> list[str]:
    comp = scene.get("composition") or {}
    data = comp.get("data") or {}
    raw = data.get("data_points") or []
    return [str(d).strip() for d in raw if str(d).strip()]


# ---------------------------------------------------------------------------
# Per-family fallback parsing: build structured props from on_screen_text
# and data_points when the director didn't populate them directly.
# ---------------------------------------------------------------------------

def _enrich_clinical_props(
    family: str,
    props: dict[str, Any],
    lines: list[str],
    data_points: list[str],
) -> None:
    """Mutate *props* in-place, filling structured fields from flat text when absent."""
    fn = _CLINICAL_ENRICHERS.get(family)
    if fn:
        fn(props, lines, data_points)


def _enrich_cover_hook(props: dict[str, Any], lines: list[str], _dp: list[str]) -> None:
    if "subtitle" not in props and len(lines) > 1:
        props["subtitle"] = lines[1]
    if "kicker" not in props and len(lines) > 2:
        props["kicker"] = lines[2]


def _enrich_orientation(props: dict[str, Any], lines: list[str], _dp: list[str]) -> None:
    if "items" not in props and len(lines) > 1:
        props["items"] = lines[1:7]


def _enrich_timeline_progression(props: dict[str, Any], lines: list[str], _dp: list[str]) -> None:
    if "markers" in props and props["markers"]:
        return
    markers: list[dict[str, str]] = []
    # Try to parse "Session N -- date" or "Session N - date" patterns from lines[1:]
    session_pat = re.compile(r"^(Session\s*\d+)\s*[-\u2013\u2014]+\s*(.+)", re.IGNORECASE)
    for line in lines[1:]:
        m = session_pat.match(line.strip())
        if m:
            markers.append({"label": m.group(1).strip(), "date": m.group(2).strip(), "status": "completed"})
        else:
            markers.append({"label": line.strip()})
    if markers:
        props["markers"] = markers


def _enrich_metric_improvement(props: dict[str, Any], lines: list[str], data_points: list[str]) -> None:
    if "stages" in props and props["stages"]:
        return
    source = data_points if data_points else lines[1:]
    session_pat = re.compile(r"^(.+?):\s*(.+)$")
    target_pat = re.compile(r"^target", re.IGNORECASE)
    stages: list[dict[str, str]] = []
    for item in source:
        stripped = item.strip()
        # Skip "Target: ..." / "Target Range: ..." lines — they are reference, not data
        if target_pat.match(stripped):
            props.setdefault("caption", stripped)
            continue
        m = session_pat.match(stripped)
        if m:
            stages.append({"label": m.group(1).strip(), "value": m.group(2).strip()})
    if len(stages) >= 2:
        props["stages"] = stages
        if "delta" not in props:
            try:
                def _first_number(s: str) -> float:
                    """Extract the first decimal number from a string."""
                    m = re.search(r"-?\d+(?:\.\d+)?", s)
                    if m is None:
                        raise ValueError(s)
                    return float(m.group())
                first_val = _first_number(stages[0]["value"])
                last_val = _first_number(stages[-1]["value"])
                diff = last_val - first_val
                sign = "+" if diff > 0 else ""
                props["delta"] = f"{sign}{diff:.1f}"
                props.setdefault("direction", "improvement" if diff > 0 else "decline" if diff < 0 else "stable")
            except (ValueError, IndexError):
                pass
    elif not stages and len(source) >= 2:
        for item in source[:4]:
            stages.append({"label": item.strip(), "value": ""})
        if stages:
            props["stages"] = stages


def _enrich_brain_region_focus(props: dict[str, Any], lines: list[str], data_points: list[str]) -> None:
    if "regions" in props and props["regions"]:
        return
    # Filter data_points: drop progression arrows and target/reference lines
    _arrow_pat = re.compile(r"[\u2192]|->|=>")  # → or -> or =>
    _target_pat = re.compile(r"^target", re.IGNORECASE)
    usable_dp = [
        dp for dp in data_points
        if dp.strip() and not _arrow_pat.search(dp) and not _target_pat.match(dp.strip())
    ]
    source = usable_dp if usable_dp else lines[1:]
    # Filter target/reference and pure-prose lines from any source
    source = [
        s for s in source
        if s.strip() and not _target_pat.match(s.strip())
    ]
    # Parse "Region: value status" or "Region -- value (status)"
    # Also handle "F3 (Left): 1.0 ✓" style
    region_pat = re.compile(
        r"^([A-Za-z][\w\s/\-()]*?)(?:\s*[-:]\s*)(.+?)(?:\s*[\(\[]?(improved|stable|declined|flagged)[\)\]]?\s*)?$",
        re.IGNORECASE,
    )
    # Status indicators: ✓ = improved/stable, ✗/✘ = declined/flagged
    check_mark = re.compile(r"[\u2713\u2714\u2705]")  # ✓ ✔ ✅
    cross_mark = re.compile(r"[\u2717\u2718\u274C]")   # ✗ ✘ ❌
    regions: list[dict[str, str]] = []
    for item in source:
        stripped = item.strip()
        m = region_pat.match(stripped)
        if not m:
            # Skip lines that don't match "Name: value" pattern (prose captions, etc.)
            continue
        value_str = m.group(2).strip()
        region: dict[str, str] = {"name": m.group(1).strip(), "value": value_str}
        if m.group(3):
            region["status"] = m.group(3).strip().lower()
        elif check_mark.search(value_str):
            region["status"] = "improved"
            region["value"] = check_mark.sub("", value_str).strip()
        elif cross_mark.search(value_str):
            region["status"] = "declined"
            region["value"] = cross_mark.sub("", value_str).strip()
        regions.append(region)
    if regions:
        props["regions"] = regions


def _enrich_metric_comparison(props: dict[str, Any], lines: list[str], data_points: list[str]) -> None:
    if ("left" in props and props["left"]) or ("right" in props and props["right"]):
        return
    source = data_points if data_points else lines[1:]
    # Split items into two halves for left/right panels
    if len(source) >= 2:
        mid = len(source) // 2
        props["left"] = {"title": "Before", "items": source[:mid], "accent": "amber"}
        props["right"] = {"title": "After", "items": source[mid:], "accent": "teal"}


def _enrich_clinical_explanation(props: dict[str, Any], lines: list[str], _dp: list[str]) -> None:
    if "body" not in props and len(lines) > 1:
        props["body"] = " ".join(lines[1:3])


def _enrich_synthesis_summary(props: dict[str, Any], lines: list[str], data_points: list[str]) -> None:
    if "columns" in props and props["columns"]:
        return
    source = data_points if data_points else lines[1:]
    if not source:
        return
    # Build a single column from available items
    items = [{"label": item.strip()} for item in source if item.strip()]
    if items:
        # Split into 2-3 columns for visual balance
        col_count = min(3, max(1, len(items) // 2))
        chunk = max(1, len(items) // col_count)
        accents = ["teal", "amber", "blue"]
        columns = []
        for ci in range(col_count):
            start = ci * chunk
            end = start + chunk if ci < col_count - 1 else len(items)
            col_items = items[start:end]
            if col_items:
                columns.append({"title": col_items[0]["label"], "accent": accents[ci % len(accents)], "items": col_items})
        if columns:
            props["columns"] = columns


def _enrich_closing_cta(props: dict[str, Any], lines: list[str], _dp: list[str]) -> None:
    if "bullets" not in props and len(lines) > 1:
        props["bullets"] = lines[1:5]
    if "kicker" not in props and len(lines) > 2:
        props["kicker"] = lines[-1]


def _enrich_analogy_metaphor(props: dict[str, Any], lines: list[str], data_points: list[str]) -> None:
    if ("left" in props and props["left"]) or ("right" in props and props["right"]):
        return
    source = data_points if data_points else lines[1:]
    if len(source) >= 2:
        mid = len(source) // 2
        props["left"] = {"title": source[0], "items": source[1:mid] if mid > 1 else [], "accent": "amber"}
        props["right"] = {"title": source[mid], "items": source[mid + 1:] if len(source) > mid + 1 else [], "accent": "teal"}


_CLINICAL_ENRICHERS: dict[str, Any] = {
    "cover_hook": _enrich_cover_hook,
    "orientation": _enrich_orientation,
    "timeline_progression": _enrich_timeline_progression,
    "metric_improvement": _enrich_metric_improvement,
    "brain_region_focus": _enrich_brain_region_focus,
    "metric_comparison": _enrich_metric_comparison,
    "clinical_explanation": _enrich_clinical_explanation,
    "synthesis_summary": _enrich_synthesis_summary,
    "closing_cta": _enrich_closing_cta,
    "analogy_metaphor": _enrich_analogy_metaphor,
}


def _default_mode_for_family(scene: dict[str, Any], family: str, current_mode: str) -> str:
    scene_type = str(scene.get("scene_type") or "").strip().lower()
    if scene_type == "motion":
        return "native"
    if family in {"kinetic_statements", "bullet_stack", "quote_focus", "three_data_stage", "surreal_tableau_3d"}:
        return "native"
    if family in _CLINICAL_TEMPLATE_FAMILIES:
        return "native"
    if family == "software_demo_focus":
        return "overlay"
    return current_mode or "none"


def _family_needs_native_renderer(family: str) -> bool:
    return family in (
        {"kinetic_statements", "bullet_stack", "quote_focus", "three_data_stage", "surreal_tableau_3d"}
        | _CLINICAL_TEMPLATE_FAMILIES
        | {"software_demo_focus"}
    )


def _mode_for_family(
    scene: dict[str, Any],
    family: str,
    intent_mode: str,
    current_mode: str,
) -> str:
    native_families = {
        "kinetic_statements", "bullet_stack", "quote_focus", "three_data_stage", "surreal_tableau_3d",
    } | _CLINICAL_TEMPLATE_FAMILIES
    if str(scene.get("scene_type") or "").strip().lower() == "motion":
        return "native"
    if family in native_families:
        return "native"
    if family == "software_demo_focus":
        return "overlay"
    if family in {"static_media", "media_pan"}:
        return "none"

    mode = intent_mode or _default_mode_for_family(scene, family, current_mode)
    if mode not in _MODE_HINTS:
        return _default_mode_for_family(scene, family, "none")
    return mode


def _family_for_scene(
    scene: dict[str, Any],
    current_family: str,
    *,
    brief: dict[str, Any] | None = None,
) -> str:
    intent = _normalize_composition_intent(scene)
    scene_type = str(scene.get("scene_type") or "image").strip().lower()
    prefers_clinical_stills = scene_type == "image" and _brief_prefers_authored_clinical_stills(brief)
    if prefers_clinical_stills and not _clinical_native_motion_requested(scene, intent):
        if intent["family_hint"] in {"", "static_media", "media_pan"}:
            return "static_media"

    if intent["family_hint"]:
        return intent["family_hint"]

    if scene_type == "motion":
        if current_family and current_family not in {"static_media", "kinetic_title"}:
            return current_family
        return _motion_family_from_scene(scene, intent)
    if current_family and current_family not in {"static_media", "media_pan"}:
        return current_family
    if scene_type == "video":
        if _software_demo_focus_requested(scene, intent):
            return "software_demo_focus"
        return "static_media"
    if scene_type == "image":
        if _software_demo_focus_requested(scene, intent):
            return "software_demo_focus"
        if prefers_clinical_stills:
            if _clinical_native_motion_requested(scene, intent):
                return _motion_family_from_scene(scene, intent)
            return "static_media"
        if _native_motion_requested(scene, intent):
            return _motion_family_from_scene(scene, intent)
        if current_family == "media_pan":
            return "media_pan"
        return "media_pan"
    return current_family or "static_media"


def plan_scene_compositions(
    scenes: list[dict[str, Any]],
    *,
    brief: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Populate stable composition families without forcing a new render path yet."""
    planned: list[dict[str, Any]] = []
    native_motion_allowed = _brief_allows_native_motion(brief)
    suppress_transitions = _brief_prefers_authored_clinical_stills(brief) or not native_motion_allowed

    for scene in scenes:
        current = scene_composition_payload(scene)
        intent = _normalize_composition_intent(scene)
        next_scene = dict(scene)
        if suppress_transitions:
            next_scene["transition_hint"] = None
            composition_intent = next_scene.get("composition_intent")
            if isinstance(composition_intent, dict) and "transition_after" in composition_intent:
                cleaned_intent = dict(composition_intent)
                cleaned_intent.pop("transition_after", None)
                next_scene["composition_intent"] = cleaned_intent
        family = _family_for_scene(
            next_scene,
            str(current.get("family") or "").strip(),
            brief=brief,
        )
        original_family = family
        family = _reroute_family_by_data_shape(family, next_scene)
        if not native_motion_allowed and _family_needs_native_renderer(family):
            family = "static_media" if _brief_prefers_authored_clinical_stills(brief) else "media_pan"
        if family != original_family:
            # Update current composition family for downstream logic
            if isinstance(next_scene.get("composition"), dict):
                next_scene["composition"]["family"] = family
        mode = _mode_for_family(
            next_scene,
            family,
            intent["mode_hint"],
            str(current.get("mode") or "none"),
        )
        if not native_motion_allowed and mode in {"native", "overlay"}:
            mode = "none"
        transition_after = None if suppress_transitions else current.get("transition_after")
        if not suppress_transitions:
            transition_hint = _normalized_transition_hint(next_scene, intent)
            if transition_hint in _TRANSITION_HINTS:
                transition_after = {"kind": transition_hint, "duration_in_frames": 20}
        props = _composition_props_from_scene(next_scene, intent, family) or (
            current.get("props") if isinstance(current.get("props"), dict) else {}
        )
        data = current.get("data")
        data_points = _normalized_data_points(next_scene, intent)
        if family == "three_data_stage":
            data = _three_data_stage_data(next_scene, intent, data, props)
        elif data_points:
            data = {"data_points": data_points}
        next_scene["composition"] = {
            "family": family,
            "mode": mode,
            "props": props,
            "transition_after": transition_after,
            "data": data,
            "render_path": current.get("render_path"),
            "preview_path": current.get("preview_path"),
            "rationale": str(
                current.get("rationale")
                or _staging_notes(next_scene, intent)
                or ""
            ).strip(),
        }
        planned.append(next_scene)

    return planned
