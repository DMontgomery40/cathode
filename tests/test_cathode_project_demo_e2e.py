from __future__ import annotations

import json
import shutil
import socketserver
import subprocess
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler
from pathlib import Path

import pytest

from core.pipeline_service import create_project_from_brief_service, render_project_service
from core.project_store import load_plan, save_plan


FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "live_demo_app"
SKILL_SCRIPTS = Path(__file__).resolve().parent.parent / "skills" / "cathode-project-demo" / "scripts"


@pytest.mark.skipif(
    shutil.which("ffmpeg") is None or shutil.which("npx") is None,
    reason="ffmpeg and npx are required for demo fixture e2e",
)
def test_live_demo_skill_scripts_prepare_review_and_render(monkeypatch, tmp_path):
    handler = partial(SimpleHTTPRequestHandler, directory=str(FIXTURE_DIR))
    with socketserver.TCPServer(("127.0.0.1", 0), handler) as server:
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            app_url = f"http://127.0.0.1:{server.server_address[1]}/index.html"
            bundle_dir = tmp_path / "bundle"
            prepare_cmd = [
                "python3",
                str(SKILL_SCRIPTS / "prepare_live_demo_session.py"),
                "--target-repo-path",
                str(FIXTURE_DIR),
                "--output-dir",
                str(bundle_dir),
                "--app-url",
                app_url,
                "--flow-hint",
                "Use Run Review as the hero state.",
            ]
            subprocess.run(prepare_cmd, check=True, capture_output=True, text=True)

            capture_manifest_path = bundle_dir / "capture_manifest.json"
            subprocess.run(
                [
                    "python3",
                    str(SKILL_SCRIPTS / "capture_live_demo.py"),
                    "--session-json",
                    str(bundle_dir / "session.json"),
                    "--capture-plan",
                    str(FIXTURE_DIR / "capture_plan.json"),
                    "--output-manifest",
                    str(capture_manifest_path),
                    "--attempt-name",
                    "fixture_capture",
                    "--headless",
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            capture_manifest = json.loads(capture_manifest_path.read_text(encoding="utf-8"))

            processed_manifest_path = bundle_dir / "processed_manifest.json"
            subprocess.run(
                [
                    "python3",
                    str(SKILL_SCRIPTS / "postprocess_capture.py"),
                    "--capture-manifest",
                    str(capture_manifest_path),
                    "--output-manifest",
                    str(processed_manifest_path),
                ],
                check=True,
                capture_output=True,
                text=True,
            )

            review_frames_dir = bundle_dir / "review_frames"
            subprocess.run(
                [
                    "python3",
                    str(SKILL_SCRIPTS / "extract_review_frames.py"),
                    "--bundle-manifest",
                    str(processed_manifest_path),
                    "--output-dir",
                    str(review_frames_dir),
                ],
                check=True,
                capture_output=True,
                text=True,
            )

            reports_dir = bundle_dir / "reports"
            reports_dir.mkdir(parents=True, exist_ok=True)
            raw_review_path = reports_dir / "subagent_qc_raw.md"
            raw_review_path.write_text(
                "Looks good overall. The run review clip is the strongest proof state and is readable enough to ship.\n",
                encoding="utf-8",
            )

            template_path = reports_dir / "review_observations.template.json"
            subprocess.run(
                [
                    "python3",
                    str(SKILL_SCRIPTS / "init_review_observations.py"),
                    "--bundle-manifest",
                    str(processed_manifest_path),
                    "--review-frames-manifest",
                    str(review_frames_dir / "review_frames.json"),
                    "--raw-review-path",
                    str(raw_review_path),
                    "--output-json",
                    str(template_path),
                ],
                check=True,
                capture_output=True,
                text=True,
            )

            observations_path = reports_dir / "review_observations.json"
            observations = json.loads(template_path.read_text(encoding="utf-8"))
            observations["decision"] = "accept"
            observations["recommended_clip_id"] = "run_review"
            observations["summary"] = "The run review clip is readable and visually dominant. The metrics panel is weaker support."
            for item in observations["clip_assessments"]:
                if item["clip_id"] == "run_review":
                    item.update(
                        {
                            "recommended": True,
                            "notes": "Good framing and readable proof state.",
                            "framing": "good",
                            "legibility": "good",
                            "theme": "good",
                            "artifact_dominance": "strong",
                            "state_quality": "strong",
                            "crop_quality": "better",
                        }
                    )
                elif item["clip_id"] == "metrics_panel":
                    item.update(
                        {
                            "recommended": False,
                            "notes": "Readable, but the weak metrics panel should not be the hero.",
                            "framing": "good",
                            "legibility": "good",
                            "theme": "good",
                            "artifact_dominance": "strong",
                            "state_quality": "weak",
                            "crop_quality": "better",
                        }
                    )
            observations_path.write_text(json.dumps(observations, indent=2), encoding="utf-8")

            review_report_path = bundle_dir / "reports" / "review_report.json"
            subprocess.run(
                [
                    "python3",
                    str(SKILL_SCRIPTS / "review_bundle.py"),
                    "--bundle-manifest",
                    str(processed_manifest_path),
                    "--observations-json",
                    str(observations_path),
                    "--raw-review-path",
                    str(raw_review_path),
                    "--output-json",
                    str(review_report_path),
                ],
                check=True,
                capture_output=True,
                text=True,
            )

            handoff_payload_path = bundle_dir / "reports" / "handoff_payload.json"
            subprocess.run(
                [
                    "python3",
                    str(SKILL_SCRIPTS / "prepare_cathode_handoff.py"),
                    "--bundle-manifest",
                    str(processed_manifest_path),
                    "--review-report",
                    str(review_report_path),
                    "--target-repo-path",
                    str(FIXTURE_DIR),
                    "--intent",
                    "Create a concise product demo for this live app.",
                    "--audience",
                    "technical buyers",
                    "--target-length-minutes",
                    "1.2",
                    "--source-path",
                    str(FIXTURE_DIR / "README.md"),
                    "--output-json",
                    str(handoff_payload_path),
                ],
                check=True,
                capture_output=True,
                text=True,
            )

            payload = json.loads(handoff_payload_path.read_text(encoding="utf-8"))
            monkeypatch.setattr(
                "core.pipeline_service.resolve_workflow_llm_roles",
                lambda provider=None: (provider or "openai", provider or "openai"),
            )
            monkeypatch.setattr(
                "core.pipeline_service.create_plan_from_brief",
                lambda **kwargs: {
                    "meta": {
                        "project_name": kwargs["project_name"],
                        "brief": kwargs["brief"],
                        "llm_provider": kwargs["provider"],
                        "render_profile": kwargs["render_profile"] or {},
                        "tts_profile": kwargs["tts_profile"] or {},
                        "image_profile": kwargs["image_profile"] or {},
                        "video_profile": kwargs["video_profile"] or {},
                    },
                    "scenes": [
                        {
                            "id": 0,
                            "title": "Run Review",
                            "narration": "Show the reviewed run state.",
                            "visual_prompt": "Play the captured run review clip.",
                            "scene_type": "video",
                            "footage_asset_id": "run_review",
                        }
                    ],
                },
            )

            project_dir = tmp_path / "cathode_project"
            _, plan = create_project_from_brief_service(
                project_name="fixture_demo",
                project_dir=project_dir,
                provider="openai",
                brief={
                    "project_name": "fixture_demo",
                    "source_mode": "source_text",
                    "video_goal": payload["intent"],
                    "audience": payload["audience"],
                    "source_material": "Fresh fixture capture.",
                    "target_length_minutes": payload["target_length_minutes"],
                    "tone": payload["tone"],
                    "visual_style": payload["visual_style"],
                    "visual_source_strategy": payload["visual_source_strategy"],
                    "available_footage": payload["available_footage"],
                    "footage_manifest": payload["footage_manifest"],
                },
                render_profile={"render_strategy": "force_ffmpeg", "render_backend": "ffmpeg"},
            )

            audio_path = project_dir / "audio" / "scene_000.wav"
            audio_path.parent.mkdir(parents=True, exist_ok=True)
            subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-f",
                    "lavfi",
                    "-i",
                    "anullsrc=r=48000:cl=stereo",
                    "-t",
                    "2.0",
                    str(audio_path),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            plan = load_plan(project_dir)
            assert plan is not None
            plan["scenes"][0]["audio_path"] = str(audio_path)
            save_plan(project_dir, plan)

            render_result = render_project_service(project_dir, output_filename="fixture_demo.mp4")

            assert payload["ready_for_handoff"] is True
            assert Path(payload["footage_manifest"][0]["path"]).exists()
            assert render_result["status"] == "succeeded"
            assert Path(render_result["video_path"]).exists()
            assert Path(review_report_path).exists()
            assert Path(processed_manifest_path).exists()
            assert Path(capture_manifest["raw_video_path"]).exists()
            assert Path(capture_manifest["trace_path"]).exists()
            assert Path(capture_manifest["step_manifest_path"]).exists()
            assert json.loads(review_report_path.read_text(encoding="utf-8"))["raw_review_path"] == str(raw_review_path.resolve())
        finally:
            server.shutdown()
            thread.join(timeout=5)
