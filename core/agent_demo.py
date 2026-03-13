"""Agent-driven demo orchestration helpers for Cathode video scenes."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from .project_store import load_plan

REPO_ROOT = Path(__file__).resolve().parents[1]
SKILL_PATH = REPO_ROOT / "skills" / "cathode-project-demo" / "SKILL.md"


def available_agent_clis() -> dict[str, str]:
    tools: dict[str, str] = {}
    codex_path = shutil.which("codex")
    claude_path = shutil.which("claude")
    if codex_path:
        tools["codex"] = codex_path
    if claude_path:
        tools["claude"] = claude_path
    return tools


def choose_agent_cli(preferred: str | None = None) -> tuple[str, str] | None:
    available = available_agent_clis()
    candidate = str(preferred or "").strip().lower()
    if candidate in available:
        return candidate, available[candidate]
    for name in ("codex", "claude"):
        if name in available:
            return name, available[name]
    return None


def default_target_repo_path() -> str:
    return str(REPO_ROOT)


def _scene_snapshot(scene: dict[str, Any], index: int) -> dict[str, Any]:
    return {
        "scene_index": index + 1,
        "uid": str(scene.get("uid") or ""),
        "title": str(scene.get("title") or "").strip(),
        "scene_type": str(scene.get("scene_type") or "image").strip(),
        "narration": str(scene.get("narration") or "").strip(),
        "visual_prompt": str(scene.get("visual_prompt") or "").strip(),
        "on_screen_text": scene.get("on_screen_text") if isinstance(scene.get("on_screen_text"), list) else [],
        "video_path": str(scene.get("video_path") or "").strip() or None,
        "audio_path": str(scene.get("audio_path") or "").strip() or None,
        "preview_path": str(scene.get("preview_path") or "").strip() or None,
        "video_trim_start": scene.get("video_trim_start"),
        "video_trim_end": scene.get("video_trim_end"),
        "video_playback_speed": scene.get("video_playback_speed"),
        "video_hold_last_frame": scene.get("video_hold_last_frame"),
    }


def build_agent_demo_prompt(
    *,
    project_dir: Path,
    scene_uids: list[str] | None = None,
    workspace_path: str | None = None,
    app_url: str | None = None,
    launch_command: str | None = None,
    expected_url: str | None = None,
    run_until: str = "assets",
) -> str:
    plan = load_plan(project_dir)
    if not plan:
        raise ValueError(f"Could not load plan.json for project: {project_dir.name}")

    scenes = plan.get("scenes", [])
    target_scene_uids = [uid for uid in (scene_uids or []) if uid]
    if target_scene_uids:
        target_scenes = [
            _scene_snapshot(scene, index)
            for index, scene in enumerate(scenes)
            if str(scene.get("uid") or "") in set(target_scene_uids)
        ]
    else:
        target_scenes = [
            _scene_snapshot(scene, index)
            for index, scene in enumerate(scenes)
            if str(scene.get("scene_type") or "image").strip().lower() == "video"
        ]

    if not target_scenes:
        raise ValueError("No target video scenes were found for the Agent Demo run.")

    resolved_workspace = str(workspace_path or default_target_repo_path()).strip()
    run_label = "render the project" if run_until == "render" else "stop after the scene media/preview work is complete"

    prompt_context = {
        "project_dir": str(project_dir),
        "project_name": project_dir.name,
        "target_repo_path": resolved_workspace,
        "app_url": str(app_url or "").strip(),
        "launch_command": str(launch_command or "").strip(),
        "expected_url": str(expected_url or "").strip(),
        "run_until": run_until,
        "skill_path": str(SKILL_PATH),
        "target_scenes": target_scenes,
    }

    return (
        "You are running as Cathode's explicit Agent Demo path.\n"
        "This is separate from local video generation and should use the packaged live-demo workflow, not the image pipeline.\n\n"
        f"Repository root: {REPO_ROOT}\n"
        f"Skill to use: {SKILL_PATH}\n"
        f"Existing Cathode project to update in place: {project_dir}\n"
        f"Demo target workspace: {resolved_workspace}\n"
        f"Target app URL (if already running): {str(app_url or '').strip() or '(infer or launch from workspace)'}\n"
        f"Launch command override: {str(launch_command or '').strip() or '(infer if possible)'}\n"
        f"Expected URL override: {str(expected_url or '').strip() or '(infer if possible)'}\n\n"
        "Goals:\n"
        "1. Use the cathode-project-demo workflow to capture fresh proof for the target video scenes.\n"
        "2. Work scene-by-scene through the listed video scenes.\n"
        "3. For each target scene, ensure narration audio exists or generate it first so audio length becomes the timing source of truth.\n"
        "4. Capture/review/select footage, then trim or speed-adjust the chosen clip so it fits the narration intent.\n"
        "5. Update the existing Cathode project in place: write the chosen clip path into the scene's video_path, preserve scene_type=video, clear image_path if needed, set video_trim_start/video_trim_end/video_playback_speed/video_hold_last_frame thoughtfully, and generate preview clips where helpful.\n"
        "6. Keep operator-facing artifacts and logs; do not fake completion from code inspection alone.\n"
        f"7. When the targeted video scenes are complete, {run_label}.\n\n"
        "Important:\n"
        "- Treat projects/<project>/plan.json as the source of truth.\n"
        "- Do not create a brand new Cathode project; update the existing one in place.\n"
        "- Prefer the packaged skill scripts and review loop over ad-hoc screenshots.\n"
        "- If a capture attempt looks weak, use the retry workflow instead of shipping it blindly.\n"
        "- Keep logs readable and explicit about what scene you are on and what command/script is running.\n\n"
        "Structured context:\n"
        f"{json.dumps(prompt_context, indent=2)}\n\n"
        "Full current plan.json:\n"
        f"{json.dumps(plan, indent=2)}\n"
    )


def run_agent_demo_cli(
    *,
    agent_name: str,
    prompt: str,
    prompt_path: Path,
    project_dir: Path,
    workspace_path: str | None = None,
) -> subprocess.CompletedProcess[str]:
    prompt_path.parent.mkdir(parents=True, exist_ok=True)
    prompt_path.write_text(prompt, encoding="utf-8")

    if agent_name == "codex":
        command = [
            "codex",
            "exec",
            "--dangerously-bypass-approvals-and-sandbox",
            "--skip-git-repo-check",
            "-C",
            str(REPO_ROOT),
            "-",
        ]
    elif agent_name == "claude":
        command = [
            "claude",
            "-p",
            "--dangerously-skip-permissions",
            "--add-dir",
            str(REPO_ROOT),
            "--add-dir",
            str(project_dir),
        ]
        if workspace_path:
            command.extend(["--add-dir", str(Path(workspace_path).expanduser().resolve())])
    else:  # pragma: no cover - guarded by caller
        raise ValueError(f"Unsupported agent CLI: {agent_name}")

    print(f"[AGENT_DEMO] Running {agent_name} from {REPO_ROOT}", file=sys.stderr, flush=True)
    print(f"[AGENT_DEMO] Prompt saved to {prompt_path}", file=sys.stderr, flush=True)

    return subprocess.run(
        command,
        cwd=str(REPO_ROOT),
        input=prompt,
        text=True,
        check=True,
    )
