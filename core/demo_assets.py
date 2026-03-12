"""Generic live-demo footage helpers for Cathode and bundled demo skills."""

from __future__ import annotations

import copy
import re
from pathlib import Path
from typing import Any

REVIEW_STATUSES = {"accept", "warn", "retry", "unknown"}


def _slugify(value: Any, fallback: str) -> str:
    text = str(value or "").strip().lower()
    if not text:
        text = fallback
    text = re.sub(r"[^a-z0-9]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    return text or fallback


def _safe_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _safe_int(value: Any, fallback: int) -> int:
    if value in (None, ""):
        return fallback
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback


def _normalized_keywords(*values: Any) -> set[str]:
    combined = " ".join(str(value or "") for value in values)
    parts = re.findall(r"[a-z0-9]+", combined.lower())
    return {part for part in parts if len(part) >= 3}


def _coerce_warning_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if value in (None, ""):
        return []
    return [str(value).strip()]


def normalize_footage_manifest(
    manifest: Any,
    *,
    base_dir: str | Path | None = None,
) -> list[dict[str, Any]]:
    """Normalize external footage references into a stable generic manifest."""
    if not isinstance(manifest, list):
        return []

    base = Path(base_dir).expanduser().resolve() if base_dir not in (None, "") else None
    normalized: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    for index, raw in enumerate(manifest, start=1):
        if isinstance(raw, (str, Path)):
            item = {"path": str(raw)}
        elif isinstance(raw, dict):
            item = dict(raw)
        else:
            continue

        raw_path = str(item.get("path") or item.get("video_path") or "").strip()
        if not raw_path:
            continue

        path = Path(raw_path).expanduser()
        if not path.is_absolute() and base is not None:
            path = (base / path).resolve()
        else:
            path = path.resolve()

        clip_id = _slugify(
            item.get("id") or item.get("label") or path.stem,
            fallback=f"footage_{index:02d}",
        )
        suffix_counter = 2
        unique_id = clip_id
        while unique_id in seen_ids:
            unique_id = f"{clip_id}_{suffix_counter:02d}"
            suffix_counter += 1
        seen_ids.add(unique_id)

        review_status = str(item.get("review_status") or "accept").strip().lower()
        if review_status not in REVIEW_STATUSES:
            review_status = "accept"

        normalized.append(
            {
                **copy.deepcopy(item),
                "id": unique_id,
                "label": str(item.get("label") or path.stem.replace("_", " ")).strip() or unique_id,
                "path": str(path),
                "kind": str(item.get("kind") or "video_clip").strip() or "video_clip",
                "notes": str(item.get("notes") or item.get("summary") or "").strip(),
                "review_status": review_status,
                "review_summary": str(item.get("review_summary") or "").strip(),
                "review_warnings": _coerce_warning_list(item.get("review_warnings")),
                "theme": str(item.get("theme") or "").strip(),
                "source_url": str(item.get("source_url") or "").strip(),
                "scene_hint": str(item.get("scene_hint") or "").strip(),
                "dom_summary": str(item.get("dom_summary") or "").strip(),
                "duration_seconds": _safe_float(item.get("duration_seconds")),
                "priority": _safe_int(item.get("priority"), index),
            }
        )

    return normalized


def build_footage_summary(manifest: list[dict[str, Any]]) -> str:
    """Build a concise textual summary of available reviewed footage for prompts."""
    parts: list[str] = []
    for entry in manifest:
        label = str(entry.get("label") or entry.get("id") or "clip").strip()
        notes = str(entry.get("notes") or "").strip()
        review_status = str(entry.get("review_status") or "accept").strip().lower()
        review_summary = str(entry.get("review_summary") or "").strip()

        bit = label
        if notes:
            bit = f"{bit}: {notes}"
        if review_status == "warn" and review_summary:
            bit = f"{bit} Warning: {review_summary}"
        elif review_status == "warn":
            bit = f"{bit} Warning: use with caution."
        elif review_status == "retry" and review_summary:
            bit = f"{bit} Avoid as a hero shot: {review_summary}"
        elif review_status == "retry":
            bit = f"{bit} Avoid as a hero shot."
        parts.append(bit.strip())
    return "; ".join(part for part in parts if part)


def copy_footage_manifest_into_project(
    project_dir: str | Path,
    manifest: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Copy approved footage references into the project clips directory."""
    root = Path(project_dir)
    clips_dir = root / "clips"
    clips_dir.mkdir(parents=True, exist_ok=True)

    copied: list[dict[str, Any]] = []
    for entry in manifest:
        path = Path(str(entry.get("path") or "")).expanduser()
        if not path.exists() or not path.is_file():
            continue
        suffix = path.suffix.lower() or ".mp4"
        dest = clips_dir / f"{entry['id']}{suffix}"
        if path.resolve() != dest.resolve():
            dest.write_bytes(path.read_bytes())
        current = copy.deepcopy(entry)
        current["source_path"] = str(path.resolve())
        current["path"] = str(dest.resolve())
        copied.append(current)
    return copied


def _score_scene_match(scene: dict[str, Any], entry: dict[str, Any]) -> int:
    scene_terms = _normalized_keywords(
        scene.get("title"),
        scene.get("visual_prompt"),
        scene.get("narration"),
    )
    entry_terms = _normalized_keywords(
        entry.get("label"),
        entry.get("notes"),
        entry.get("scene_hint"),
        entry.get("dom_summary"),
    )
    if not scene_terms or not entry_terms:
        return 0
    overlap = len(scene_terms & entry_terms)
    if overlap <= 0:
        return 0
    return overlap * 10


def apply_footage_manifest_to_scenes(
    scenes: list[dict[str, Any]],
    manifest: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Assign copied footage clips to video scenes using explicit ids or best-effort matching."""
    available = [entry for entry in manifest if str(entry.get("review_status") or "accept") != "retry"]
    by_id = {str(entry["id"]): entry for entry in available}
    unused_ids = {str(entry["id"]) for entry in available}

    for scene in scenes:
        if str(scene.get("scene_type") or "image").strip().lower() != "video":
            continue
        existing_path = str(scene.get("video_path") or "").strip()
        if existing_path:
            continue

        chosen: dict[str, Any] | None = None
        explicit_id = str(scene.get("footage_asset_id") or "").strip()
        if explicit_id and explicit_id in by_id:
            chosen = by_id[explicit_id]
        else:
            ranked = sorted(
                available,
                key=lambda entry: (
                    _score_scene_match(scene, entry),
                    1 if str(entry.get("review_status") or "accept") == "accept" else 0,
                    -int(entry.get("priority") or 0),
                ),
                reverse=True,
            )
            for candidate in ranked:
                candidate_id = str(candidate["id"])
                if candidate_id in unused_ids:
                    chosen = candidate
                    break
            if chosen is None and ranked:
                chosen = ranked[0]

        if not chosen:
            continue

        chosen_id = str(chosen["id"])
        scene["footage_asset_id"] = chosen_id
        scene["video_path"] = str(chosen["path"])
        scene["footage_label"] = str(chosen.get("label") or chosen_id)
        scene["footage_review_status"] = str(chosen.get("review_status") or "accept")
        if chosen.get("review_summary"):
            scene["footage_review_summary"] = str(chosen["review_summary"])
        if chosen.get("notes"):
            scene["footage_notes"] = str(chosen["notes"])
        unused_ids.discard(chosen_id)

    return scenes
