"""Anthropic-harvested director example tooling for Cathode."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import textwrap
import threading
import wave
from contextlib import contextmanager
from datetime import datetime, timezone
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import unquote

from dotenv import dotenv_values

from .composition_planner import plan_scene_compositions
from .director import (
    _build_storyboard_user_prompt_from_brief,
    _validate_scenes,
    build_director_system_prompt,
    extract_scenes_array,
    extract_storyboard_tool_input,
    load_prompt,
    storyboard_tool_schema,
)
from .pipeline_service import generate_project_assets_service, render_project_service
from .project_schema import backfill_plan, normalize_brief, normalize_scene
from .project_store import save_plan
from .remotion_render import build_remotion_manifest, render_manifest_with_remotion
from .runtime import REPO_ROOT

DIRECTOR_GOLDEN_ROOT = REPO_ROOT / "experiments" / "director_golden"
DIRECTOR_SCENARIOS_DIR = REPO_ROOT / "prompts" / "director_example_scenarios"
PROMOTED_DIRECTOR_EXAMPLES_DIR = REPO_ROOT / "prompts" / "director_examples"
PROMOTED_DIRECTOR_EXAMPLES_INDEX = PROMOTED_DIRECTOR_EXAMPLES_DIR / "index.json"
_TINY_PNG_BYTES = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc````\xf8\xcf"
    b"\xc0\x00\x00\x04\x00\x01\x93\xdd\xb7\x9f\x00\x00\x00\x00IEND\xaeB`\x82"
)


def _repo_env() -> dict[str, str]:
    env = dict(os.environ)
    dotenv_path = REPO_ROOT / ".env"
    if dotenv_path.exists():
        for key, value in dotenv_values(dotenv_path).items():
            if value is not None and key not in env:
                env[key] = value
    return env


@contextmanager
def repo_env_applied():
    previous = dict(os.environ)
    os.environ.update(_repo_env())
    try:
        yield
    finally:
        os.environ.clear()
        os.environ.update(previous)


def _anthropic_api_key(env: dict[str, str] | None = None) -> str:
    merged = env or _repo_env()
    api_key = str(merged.get("ANTHROPIC_API_KEY") or "").strip()
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY is required for director golden-harvest runs.")
    return api_key


def scenario_brief_paths() -> list[Path]:
    if not DIRECTOR_SCENARIOS_DIR.exists():
        return []
    return sorted(path for path in DIRECTOR_SCENARIOS_DIR.glob("*.json") if path.is_file())


def load_scenario_brief(scenario_id: str) -> dict[str, Any]:
    scenario_path = DIRECTOR_SCENARIOS_DIR / f"{scenario_id}.json"
    if not scenario_path.exists():
        raise FileNotFoundError(f"Unknown director scenario: {scenario_id}")
    return json.loads(scenario_path.read_text())


def create_run_dir(*, scenario_id: str, model: str, root: Path | None = None) -> Path:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    base_root = root or DIRECTOR_GOLDEN_ROOT / "runs"
    run_dir = base_root / f"{timestamp}_{scenario_id}_{model.replace('/', '_')}"
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def build_storyboard_payload(
    brief: dict[str, Any],
    *,
    model: str = "claude-sonnet-4-6",
) -> dict[str, Any]:
    normalized_brief = normalize_brief(brief)
    return {
        "model": model,
        "max_tokens": 12000,
        "system": build_director_system_prompt(normalized_brief),
        "messages": [
            {
                "role": "user",
                "content": _build_storyboard_user_prompt_from_brief(normalized_brief),
            }
        ],
        "tools": [storyboard_tool_schema()],
        "tool_choice": {"type": "tool", "name": "emit_storyboard"},
    }


def build_judge_payload(
    brief: dict[str, Any],
    storyboard: dict[str, Any] | list[dict[str, Any]],
    *,
    model: str = "claude-sonnet-4-6",
) -> dict[str, Any]:
    normalized_brief = normalize_brief(brief)
    storyboard_json = json.dumps(storyboard, indent=2, ensure_ascii=False)
    brief_json = json.dumps(normalized_brief, indent=2, ensure_ascii=False)
    return {
        "model": model,
        "max_tokens": 2500,
        "system": load_prompt("director_judge_system"),
        "messages": [
            {
                "role": "user",
                "content": textwrap.dedent(
                    f"""\
                    Judge this storyboard candidate for Cathode's golden example corpus.

                    Brief:
                    {brief_json}

                    Storyboard candidate:
                    {storyboard_json}
                    """
                ),
            }
        ],
    }


def run_anthropic_curl(payload: dict[str, Any], *, env: dict[str, str] | None = None) -> dict[str, Any]:
    merged_env = dict(_repo_env())
    if env:
        merged_env.update(env)
    api_key = _anthropic_api_key(merged_env)
    response = subprocess.run(
        [
            "curl",
            "-sS",
            "https://api.anthropic.com/v1/messages",
            "-H",
            f"x-api-key: {api_key}",
            "-H",
            "anthropic-version: 2023-06-01",
            "-H",
            "content-type: application/json",
            "-d",
            "@-",
        ],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        env=merged_env,
        check=False,
    )
    if response.returncode != 0:
        raise RuntimeError(response.stderr.strip() or "Anthropic curl request failed.")
    parsed = json.loads(response.stdout)
    if isinstance(parsed, dict) and parsed.get("error"):
        raise RuntimeError(json.dumps(parsed["error"]))
    return parsed


def parse_storyboard_response(response: dict[str, Any]) -> list[dict[str, Any]]:
    content = response.get("content")
    if not isinstance(content, list):
        raise ValueError("Anthropic response did not contain a content array.")
    tool_input = extract_storyboard_tool_input(content)
    if not tool_input:
        raise ValueError("Anthropic response did not contain storyboard tool output.")
    scenes = extract_scenes_array(tool_input)
    return _validate_scenes(scenes)


def parse_judge_response(response: dict[str, Any]) -> dict[str, Any]:
    content = response.get("content")
    if not isinstance(content, list):
        raise ValueError("Anthropic judge response did not contain a content array.")
    for block in content:
        block_type = block.get("type") if isinstance(block, dict) else getattr(block, "type", None)
        if block_type != "text":
            continue
        text = block.get("text") if isinstance(block, dict) else getattr(block, "text", "")
        normalized = str(text or "").strip()
        if "```json" in normalized:
            start = normalized.index("```json") + 7
            end = normalized.index("```", start)
            normalized = normalized[start:end].strip()
        elif normalized.startswith("```") and normalized.count("```") >= 2:
            start = normalized.index("```") + 3
            end = normalized.index("```", start)
            normalized = normalized[start:end].strip()
        return json.loads(normalized)
    raise ValueError("Anthropic judge response did not include a text block.")


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _write_silent_wav(path: Path, *, duration_seconds: float = 1.0, framerate: int = 24000) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame_count = max(1, int(duration_seconds * framerate))
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(framerate)
        handle.writeframes(b"\x00\x00" * frame_count)


def _write_placeholder_png(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(_TINY_PNG_BYTES)


def _write_placeholder_video(path: Path, *, duration_seconds: float = 1.0) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    command = [
        "ffmpeg",
        "-y",
        "-f",
        "lavfi",
        "-i",
        f"color=c=0x111111:s=1664x928:d={duration_seconds}",
        "-pix_fmt",
        "yuv420p",
        str(path),
    ]
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "Failed to synthesize placeholder video.")


@contextmanager
def temporary_project_media_server(project_dir: Path, project_name: str):
    class ProjectMediaHandler(SimpleHTTPRequestHandler):
        def log_message(self, format: str, *args: Any) -> None:  # pragma: no cover - noisy server logs
            return

        def do_GET(self) -> None:  # pragma: no cover - exercised through preview rendering
            prefix = f"/api/projects/{project_name}/media/"
            if not self.path.startswith(prefix):
                self.send_response(404)
                self.end_headers()
                return
            relative_path = unquote(self.path[len(prefix) :]).lstrip("/")
            file_path = (project_dir / relative_path).resolve()
            if not str(file_path).startswith(str(project_dir.resolve())) or not file_path.exists():
                self.send_response(404)
                self.end_headers()
                return
            self.path = "/" + relative_path
            return super().do_GET()

    temp_root = tempfile.mkdtemp(prefix="director-golden-media-")
    try:
        for relative in ("audio", "images", "clips", "previews"):
            source = project_dir / relative
            if source.exists():
                target = Path(temp_root) / relative
                if target.exists():
                    target.unlink()
                target.parent.mkdir(parents=True, exist_ok=True)
                os.symlink(source, target, target_is_directory=True)

        server = ThreadingHTTPServer(("127.0.0.1", 0), ProjectMediaHandler)
        server_thread = threading.Thread(target=server.serve_forever, daemon=True)
        previous = os.getcwd()
        os.chdir(temp_root)
        server_thread.start()
        try:
            base_url = f"http://127.0.0.1:{server.server_address[1]}"
            yield base_url
        finally:
            server.shutdown()
            server.server_close()
            os.chdir(previous)
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)


def normalize_storyboard_candidate(
    *,
    brief: dict[str, Any],
    scenes: list[dict[str, Any]],
    project_name: str = "director_golden_preview",
) -> dict[str, Any]:
    normalized_brief = normalize_brief(brief)
    normalized_scenes = [normalize_scene(scene, index) for index, scene in enumerate(scenes)]
    planned_scenes = plan_scene_compositions(normalized_scenes, brief=normalized_brief)
    plan = {
        "meta": {
            "project_name": project_name,
            "brief": normalized_brief,
            "render_profile": {"render_backend": "remotion", "render_strategy": "auto"},
        },
        "scenes": planned_scenes,
    }
    return backfill_plan(plan)


def synthesize_preview_assets(plan: dict[str, Any], *, project_dir: Path) -> dict[str, Any]:
    preview_plan = json.loads(json.dumps(plan))
    project_name = str(preview_plan.get("meta", {}).get("project_name") or project_dir.name)
    for scene in preview_plan.get("scenes", []):
        scene_id = int(scene.get("id") or 0)
        if not scene.get("audio_path"):
            audio_path = project_dir / "audio" / f"scene_{scene_id:03d}.wav"
            _write_silent_wav(audio_path)
            scene["audio_path"] = str(audio_path)

        scene_type = str(scene.get("scene_type") or "image").strip().lower()
        if scene_type == "image" and not scene.get("image_path"):
            image_path = project_dir / "images" / f"scene_{scene_id:03d}.png"
            _write_placeholder_png(image_path)
            scene["image_path"] = str(image_path)
        if scene_type == "video" and not scene.get("video_path"):
            video_path = project_dir / "clips" / f"scene_{scene_id:03d}.mp4"
            _write_placeholder_video(video_path)
            scene["video_path"] = str(video_path)

    return backfill_plan(preview_plan, base_dir=project_dir)


def render_candidate_preview(
    *,
    plan: dict[str, Any],
    run_dir: Path,
) -> dict[str, Any]:
    preview_project_dir = run_dir / "preview_project"
    preview_project_dir.mkdir(parents=True, exist_ok=True)
    preview_plan = synthesize_preview_assets(plan, project_dir=preview_project_dir)
    first_scene_uid = str(preview_plan["scenes"][0]["uid"])
    project_name = str(preview_plan["meta"]["project_name"])

    with temporary_project_media_server(preview_project_dir, project_name) as base_url:
        previous_api_base = os.getenv("CATHODE_API_BASE_URL")
        os.environ["CATHODE_API_BASE_URL"] = base_url
        try:
            manifest = build_remotion_manifest(
                project_dir=preview_project_dir,
                plan=preview_plan,
                output_path=preview_project_dir / "preview.mp4",
                render_profile=preview_plan.get("meta", {}).get("render_profile"),
                preview_scene_uid=first_scene_uid,
            )
            preview_path = render_manifest_with_remotion(
                manifest,
                output_path=preview_project_dir / "preview.mp4",
            )
        finally:
            if previous_api_base is None:
                os.environ.pop("CATHODE_API_BASE_URL", None)
            else:
                os.environ["CATHODE_API_BASE_URL"] = previous_api_base

    _write_json(run_dir / "preview_plan.json", preview_plan)
    _write_json(run_dir / "manifest_excerpt.json", manifest)
    return {
        "preview_path": str(preview_path),
        "manifest_path": str(run_dir / "manifest_excerpt.json"),
        "preview_plan_path": str(run_dir / "preview_plan.json"),
    }


def materialize_run(
    *,
    run_dir: Path,
    scene_count: int = 3,
) -> dict[str, Any]:
    brief = json.loads((run_dir / "brief.json").read_text())
    parsed_storyboard = json.loads((run_dir / "response_parsed.json").read_text())
    scenes = parsed_storyboard.get("scenes")
    if not isinstance(scenes, list) or not scenes:
        raise ValueError("Run does not contain a parsed storyboard scene list.")

    plan = normalize_storyboard_candidate(
        brief=brief,
        scenes=scenes,
        project_name=f"director_materialized_{run_dir.name}",
    )
    plan["scenes"] = list(plan.get("scenes", []))[: max(1, int(scene_count))]
    materialized_dir = REPO_ROOT / "projects" / f"director_golden_{run_dir.name}"
    if materialized_dir.exists():
        shutil.rmtree(materialized_dir)
    materialized_dir.mkdir(parents=True, exist_ok=True)
    plan.setdefault("meta", {})["project_name"] = materialized_dir.name

    with repo_env_applied():
        saved_plan = save_plan(materialized_dir, plan)
        has_video_scenes = any(str(scene.get("scene_type") or "").strip().lower() == "video" for scene in saved_plan.get("scenes", []))
        assets_result = generate_project_assets_service(
            materialized_dir,
            generate_videos=has_video_scenes,
            regenerate_images=True,
            regenerate_videos=has_video_scenes,
            regenerate_audio=True,
        )
        previous_api_base = os.getenv("CATHODE_API_BASE_URL")
        with temporary_project_media_server(materialized_dir, str(saved_plan["meta"]["project_name"])) as base_url:
            os.environ["CATHODE_API_BASE_URL"] = base_url
            try:
                render_result = render_project_service(
                    materialized_dir,
                    output_filename="mini_video.mp4",
                )
            finally:
                if previous_api_base is None:
                    os.environ.pop("CATHODE_API_BASE_URL", None)
                else:
                    os.environ["CATHODE_API_BASE_URL"] = previous_api_base

    result = {
        "materialized_project_dir": str(materialized_dir),
        "scene_count": len(plan["scenes"]),
        "assets": assets_result,
        "render": render_result,
    }
    _write_json(run_dir / "materialized_result.json", result)
    return result


def harvest_scenario(
    *,
    scenario_id: str,
    model: str = "claude-sonnet-4-6",
    run_dir: Path | None = None,
    judge: bool = True,
    render_preview: bool = True,
) -> dict[str, Any]:
    brief = load_scenario_brief(scenario_id)
    current_run_dir = run_dir or create_run_dir(scenario_id=scenario_id, model=model)
    storyboard_payload = build_storyboard_payload(brief, model=model)
    _write_json(current_run_dir / "brief.json", brief)
    _write_text(current_run_dir / "system_prompt.txt", storyboard_payload["system"])
    _write_text(current_run_dir / "user_prompt.txt", storyboard_payload["messages"][0]["content"])
    _write_json(current_run_dir / "request.json", storyboard_payload)

    storyboard_response = run_anthropic_curl(storyboard_payload)
    _write_json(current_run_dir / "response_raw.json", storyboard_response)
    storyboard_scenes = parse_storyboard_response(storyboard_response)
    parsed_storyboard = {"scenes": storyboard_scenes}
    _write_json(current_run_dir / "response_parsed.json", parsed_storyboard)

    normalized_plan = normalize_storyboard_candidate(
        brief=brief,
        scenes=storyboard_scenes,
        project_name=f"director_golden_{scenario_id}",
    )
    _write_json(
        current_run_dir / "normalized_scene_excerpt.json",
        {
            "brief": normalized_plan["meta"]["brief"],
            "scenes": normalized_plan["scenes"],
        },
    )

    result: dict[str, Any] = {
        "scenario_id": scenario_id,
        "run_dir": str(current_run_dir),
        "parsed_storyboard_path": str(current_run_dir / "response_parsed.json"),
    }

    if judge:
        judge_payload = build_judge_payload(brief, parsed_storyboard, model=model)
        _write_json(current_run_dir / "judge_request.json", judge_payload)
        judge_response = run_anthropic_curl(judge_payload)
        _write_json(current_run_dir / "judge_response_raw.json", judge_response)
        judge_result = parse_judge_response(judge_response)
        _write_json(current_run_dir / "judge_response_parsed.json", judge_result)
        result["judge_path"] = str(current_run_dir / "judge_response_parsed.json")

    if render_preview:
        preview = render_candidate_preview(plan=normalized_plan, run_dir=current_run_dir)
        _write_json(current_run_dir / "preview_artifacts.json", preview)
        result.update(preview)

    return result


def promote_example(
    *,
    run_dir: Path,
    example_id: str,
    title: str,
    intents: list[str],
) -> dict[str, Any]:
    promoted_dir = PROMOTED_DIRECTOR_EXAMPLES_DIR / example_id
    promoted_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(run_dir / "brief.json", promoted_dir / "input_brief.json")
    shutil.copy2(run_dir / "response_parsed.json", promoted_dir / "expected_storyboard.json")
    judge_path = run_dir / "judge_response_parsed.json"
    if judge_path.exists():
        judge = json.loads(judge_path.read_text())
        strengths = "\n".join(f"- {item}" for item in judge.get("strengths") or [])
        notes = "\n".join(f"- {item}" for item in judge.get("notes_for_prompting") or [])
        rationale = f"# Why It Works\n\n{judge.get('summary', '').strip()}\n\n## Strengths\n{strengths or '- (none)'}\n\n## Prompting Notes\n{notes or '- (none)'}\n"
        _write_text(promoted_dir / "why_it_is_good.md", rationale)
    else:
        _write_text(promoted_dir / "why_it_is_good.md", "# Why It Works\n\nPromoted without a saved judge file.\n")

    metadata = {
        "id": example_id,
        "title": title,
        "intents": intents,
        "source_run": str(run_dir),
        "promoted_utc": datetime.now(timezone.utc).isoformat(),
    }
    _write_json(promoted_dir / "promotion.json", metadata)

    current_index: list[dict[str, Any]] = []
    if PROMOTED_DIRECTOR_EXAMPLES_INDEX.exists():
        parsed = json.loads(PROMOTED_DIRECTOR_EXAMPLES_INDEX.read_text())
        if isinstance(parsed, list):
            current_index = [item for item in parsed if isinstance(item, dict) and str(item.get("id") or "") != example_id]
    current_index.append({"id": example_id, "title": title, "intents": intents})
    _write_json(PROMOTED_DIRECTOR_EXAMPLES_INDEX, current_index)
    return metadata
