"""Session-building helpers for generic live product demo capture."""

from __future__ import annotations

import re
import uuid
from pathlib import Path
from typing import Any

DEFAULT_VIEWPORT_WIDTH = 1664
DEFAULT_VIEWPORT_HEIGHT = 928


def _slugify(value: Any, fallback: str) -> str:
    text = str(value or "").strip().lower()
    if not text:
        text = fallback
    text = re.sub(r"[^a-z0-9]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    return text or fallback


def infer_launch_command(target_repo_path: str | Path) -> str | None:
    """Infer a likely local launch command from a target repository."""
    root = Path(target_repo_path).expanduser().resolve()
    candidates = [
        root / "run_all.sh",
        root / "start.sh",
        root / "frontend" / "run_frontend.sh",
        root / "app.py",
    ]
    for path in candidates:
        if not path.exists():
            continue
        if path.name.endswith(".sh"):
            return f"./{path.relative_to(root)}"
        if path.name == "app.py":
            return "python3 app.py"
    return None


def infer_expected_url(target_repo_path: str | Path) -> str | None:
    """Infer a loopback URL from repo docs when the user does not provide one."""
    root = Path(target_repo_path).expanduser().resolve()
    candidates = [root / "README.md", root / "docs" / "getting-started.md", root / "docs" / "workflows.md"]
    pattern = re.compile(r"https?://(?:127\.0\.0\.1|localhost):\d+(?:/[^\s)\"']*)?")
    for path in candidates:
        if not path.exists() or not path.is_file():
            continue
        match = pattern.search(path.read_text(encoding="utf-8", errors="ignore"))
        if match:
            return match.group(0)
    return None


def build_live_demo_session(
    *,
    target_repo_path: str | Path,
    output_dir: str | Path,
    app_url: str | None = None,
    launch_command: str | None = None,
    expected_url: str | None = None,
    preferred_theme: str = "dark",
    flow_hints: list[str] | None = None,
    viewport_width: int = DEFAULT_VIEWPORT_WIDTH,
    viewport_height: int = DEFAULT_VIEWPORT_HEIGHT,
) -> dict[str, Any]:
    """Build a deterministic session manifest for a live demo capture attempt."""
    root = Path(target_repo_path).expanduser().resolve()
    bundle_root = Path(output_dir).expanduser().resolve()
    bundle_root.mkdir(parents=True, exist_ok=True)

    session_slug = _slugify(root.name, "demo_target")
    session_id = f"{session_slug}_{uuid.uuid4().hex[:8]}"
    launch = str(launch_command or "").strip()
    if not launch and not str(app_url or "").strip():
        launch = str(infer_launch_command(root) or "").strip()
    resolved_expected_url = str(expected_url or app_url or infer_expected_url(root) or "").strip()

    artifacts = {
        "root": str(bundle_root),
        "raw_dir": str((bundle_root / "raw").resolve()),
        "processed_dir": str((bundle_root / "processed").resolve()),
        "screenshots_dir": str((bundle_root / "screenshots").resolve()),
        "traces_dir": str((bundle_root / "traces").resolve()),
        "reports_dir": str((bundle_root / "reports").resolve()),
        "session_manifest_path": str((bundle_root / "session.json").resolve()),
        "capture_manifest_path": str((bundle_root / "capture_manifest.json").resolve()),
        "review_observations_path": str((bundle_root / "reports" / "review_observations.json").resolve()),
        "review_report_path": str((bundle_root / "reports" / "review_report.json").resolve()),
        "handoff_payload_path": str((bundle_root / "reports" / "cathode_make_video_payload.json").resolve()),
        "launch_state_path": str((bundle_root / "launch_state.json").resolve()),
    }
    for path in artifacts.values():
        if path.endswith(".json"):
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        else:
            Path(path).mkdir(parents=True, exist_ok=True)

    return {
        "session_id": session_id,
        "target_repo_path": str(root),
        "app_url": str(app_url or "").strip(),
        "launch_command": launch,
        "expected_url": resolved_expected_url,
        "preferred_theme": preferred_theme if preferred_theme in {"light", "dark"} else "dark",
        "flow_hints": [str(item).strip() for item in (flow_hints or []) if str(item).strip()],
        "viewport": {"width": int(viewport_width), "height": int(viewport_height)},
        "capture_defaults": {
            "headed": True,
            "record_video": True,
            "trace": True,
            "explicit_theme": True,
            "explicit_viewport": True,
        },
        "retry_policy": {
            "max_attempts": 3,
            "allowed_actions": [
                "switch_theme",
                "expand_viewport",
                "collapse_sidebar",
                "pick_better_state",
                "refocus_crop",
            ],
        },
        "artifacts": artifacts,
    }
