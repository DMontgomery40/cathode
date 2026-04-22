"""Intent intake and bounded workspace inspection for headless video requests."""

from __future__ import annotations

import fnmatch
import os
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from .demo_assets import build_footage_summary, normalize_footage_manifest
from .project_schema import normalize_brief, sanitize_project_name

TEXT_SUFFIX_ALLOWLIST = {
    ".md",
    ".txt",
    ".rst",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".ini",
    ".cfg",
    ".py",
    ".js",
    ".ts",
    ".tsx",
    ".jsx",
    ".css",
    ".html",
    ".sh",
}
SKIP_DIR_NAMES = {
    ".git",
    ".hg",
    ".svn",
    ".venv",
    "venv",
    "__pycache__",
    "node_modules",
    "dist",
    "build",
    "coverage",
    ".pytest_cache",
    ".mypy_cache",
    "output",
}
SKIP_FILE_PATTERNS = ("*.env", "*.pem", "*.key", "*.sqlite", "*.db")
AUTO_CANDIDATE_PATTERNS = (
    "README*",
    "docs/*.md",
    "docs/**/*.md",
    "requirements*.txt",
    "pyproject.toml",
    "package.json",
    "Cargo.toml",
    "go.mod",
    "app.py",
    "main.py",
    "index.*",
)
MAX_SOURCE_FILE_BYTES = 128_000
MAX_SOURCE_FILES = 8
MAX_SOURCE_CHARS = 14_000


class BriefElicitationInput(BaseModel):
    """Minimal follow-up fields required to safely create a video brief."""

    audience: str = Field(
        default="",
        description="Who the finished video is for. Example: founders, customers, investors, internal team.",
    )
    source_material: str = Field(
        default="",
        description="Facts, notes, or script text the video should rely on. Include enough detail to avoid guessing.",
    )
    target_length_minutes: float = Field(
        default=2.0,
        ge=0.5,
        le=20.0,
        description="Approximate target runtime in minutes.",
    )
    visual_style: str = Field(
        default="",
        description="Optional art direction. Example: product demo, editorial, cinematic infographic, case-study.",
    )


def derive_project_name(intent: str, provided_name: str | None = None) -> str:
    """Build a stable filesystem-safe project name from the request."""
    if provided_name:
        return sanitize_project_name(provided_name)

    cleaned_words = [part.strip(" -_") for part in intent.replace("/", " ").split()]
    base = "_".join(word for word in cleaned_words[:6] if word)
    return sanitize_project_name(base or "cathode_video")


def _is_probably_text_file(path: Path) -> bool:
    return path.suffix.lower() in TEXT_SUFFIX_ALLOWLIST


def _should_skip_path(path: Path) -> bool:
    for part in path.parts:
        if part in SKIP_DIR_NAMES:
            return True
    return any(fnmatch.fnmatch(path.name, pattern) for pattern in SKIP_FILE_PATTERNS)


def _read_text_excerpt(path: Path, root: Path | None = None) -> str:
    if not path.exists() or not path.is_file() or _should_skip_path(path):
        return ""
    if path.stat().st_size > MAX_SOURCE_FILE_BYTES or not _is_probably_text_file(path):
        return ""
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return ""
    except Exception:
        return ""

    text = text.strip()
    if not text:
        return ""
    label = str(path.relative_to(root)) if root and path.is_relative_to(root) else path.name
    return f"## {label}\n{text[:2200].strip()}"


def inspect_workspace(
    workspace_path: str | Path | None,
    *,
    source_paths: list[str | Path] | None = None,
) -> dict[str, Any]:
    """Collect bounded text context from an optional workspace and explicit file paths."""
    explicit = [Path(p) for p in (source_paths or []) if p]
    if workspace_path in (None, "") and not explicit:
        return {"workspace_path": None, "files": [], "source_material": ""}

    root = Path(workspace_path).expanduser().resolve() if workspace_path not in (None, "") else None
    candidates: list[Path] = []

    for path in explicit:
        resolved = path.expanduser().resolve()
        if resolved.exists() and resolved.is_file():
            candidates.append(resolved)

    if root and root.exists() and not candidates:
        for pattern in AUTO_CANDIDATE_PATTERNS:
            for path in sorted(root.glob(pattern)):
                if path.is_file() and path not in candidates:
                    candidates.append(path)

    excerpts: list[str] = []
    kept_paths: list[str] = []
    total_chars = 0

    for path in candidates:
        excerpt = _read_text_excerpt(path, root=root)
        if not excerpt:
            continue
        if len(excerpts) >= MAX_SOURCE_FILES:
            break
        if total_chars + len(excerpt) > MAX_SOURCE_CHARS:
            remaining = MAX_SOURCE_CHARS - total_chars
            if remaining <= 0:
                break
            excerpt = excerpt[:remaining].rstrip()
        excerpts.append(excerpt)
        kept_paths.append(str(path))
        total_chars += len(excerpt)

    return {
        "workspace_path": str(root) if root else None,
        "files": kept_paths,
        "source_material": "\n\n".join(excerpts).strip(),
    }


def build_brief_from_intent(
    *,
    intent: str,
    project_name: str | None = None,
    source_text: str | None = None,
    workspace_path: str | Path | None = None,
    source_paths: list[str | Path] | None = None,
    footage_paths: list[str | Path] | None = None,
    footage_manifest: list[dict[str, Any]] | None = None,
    brief_overrides: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Build a normalized brief from natural-language intent plus optional local context."""
    overrides = dict(brief_overrides or {})
    workspace = inspect_workspace(workspace_path, source_paths=source_paths)

    source_parts = [str(source_text or "").strip(), workspace["source_material"]]
    source_material = "\n\n".join(part for part in source_parts if part).strip()
    normalized_footage_manifest = normalize_footage_manifest(
        list(footage_manifest or [])
        + [{"path": str(path)} for path in (footage_paths or []) if path],
        base_dir=workspace_path,
    )
    derived_footage_summary = build_footage_summary(normalized_footage_manifest)
    resolved_visual_source_strategy = overrides.get("visual_source_strategy") or (
        "video_preferred" if normalized_footage_manifest else "images_only"
    )

    explicit_source_mode = str(overrides.get("source_mode") or "").strip()
    if explicit_source_mode:
        source_mode = explicit_source_mode
    elif source_text and len(str(source_text).split()) > 120:
        source_mode = "source_text"
    elif source_material:
        source_mode = "source_text"
    else:
        source_mode = "ideas_notes"

    brief = normalize_brief(
        {
            "project_name": derive_project_name(intent, project_name),
            "source_mode": source_mode,
            "video_goal": overrides.get("video_goal") or intent.strip(),
            "audience": overrides.get("audience") or "",
            "source_material": source_material,
            "target_length_minutes": overrides.get("target_length_minutes") or 2.0,
            "tone": overrides.get("tone") or "",
            "visual_style": overrides.get("visual_style") or "",
            "must_include": overrides.get("must_include") or "",
            "must_avoid": overrides.get("must_avoid") or "",
            "ending_cta": overrides.get("ending_cta") or "",
            "composition_mode": overrides.get("composition_mode") or "",
            "visual_source_strategy": resolved_visual_source_strategy,
            "available_footage": overrides.get("available_footage") or derived_footage_summary,
            "footage_manifest": normalized_footage_manifest,
            "style_reference_paths": overrides.get("style_reference_paths") or [],
            "style_reference_summary": overrides.get("style_reference_summary") or "",
            "raw_brief": overrides.get("raw_brief") or f"User intent: {intent.strip()}",
        },
        base_dir=workspace_path,
    )
    metadata = {
        "workspace_context": workspace,
        "intent": intent.strip(),
        "source_paths": [str(Path(p).expanduser().resolve()) for p in (source_paths or []) if Path(p).exists()],
        "footage_manifest": normalized_footage_manifest,
    }
    return brief, metadata


def merge_elicitation_into_brief(
    brief: dict[str, Any],
    elicited: BriefElicitationInput | dict[str, Any] | None,
) -> dict[str, Any]:
    """Merge user follow-up answers into an existing brief."""
    if elicited is None:
        return normalize_brief(brief)
    if isinstance(elicited, BriefElicitationInput):
        payload = elicited.model_dump()
    else:
        payload = dict(elicited)

    merged = dict(brief)
    for key in ("audience", "source_material", "target_length_minutes", "visual_style"):
        value = payload.get(key)
        if value not in (None, ""):
            merged[key] = value
    return normalize_brief(merged)


def missing_brief_fields(brief: dict[str, Any]) -> list[str]:
    """Return the high-value fields still missing from a draft brief."""
    missing: list[str] = []
    if not str(brief.get("video_goal") or "").strip():
        missing.append("video_goal")
    if not str(brief.get("audience") or "").strip():
        missing.append("audience")
    if not str(brief.get("source_material") or "").strip():
        missing.append("source_material")
    return missing
