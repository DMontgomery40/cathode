import json
from pathlib import Path

from core.director_golden import (
    build_storyboard_payload,
    harvest_scenario,
    materialize_run,
    promote_example,
)


def test_build_storyboard_payload_uses_director_tool_and_full_prompt():
    payload = build_storyboard_payload(
        {
            "project_name": "golden_demo",
            "source_mode": "ideas_notes",
            "source_material": "Use Bella as narrator and stage a premium motion roadmap.",
            "composition_mode": "hybrid",
            "text_render_mode": "deterministic_overlay",
        }
    )

    assert payload["tools"][0]["name"] == "emit_storyboard"
    assert "Cathode" in payload["system"]
    assert "Use Bella as narrator" in payload["messages"][0]["content"]
    assert '"staging_notes"' in payload["messages"][0]["content"]


def test_harvest_scenario_persists_artifacts_and_judge_output(tmp_path, monkeypatch):
    scenarios_dir = tmp_path / "scenarios"
    scenarios_dir.mkdir()
    (scenarios_dir / "demo.json").write_text(
        json.dumps(
            {
                "project_name": "demo",
                "source_mode": "ideas_notes",
                "source_material": "Show a premium roadmap beat.",
                "composition_mode": "motion_only",
                "text_render_mode": "deterministic_overlay",
            }
        ),
        encoding="utf-8",
    )

    calls = {"count": 0}

    def fake_run(payload, env=None):
        calls["count"] += 1
        if calls["count"] == 1:
            return {
                "content": [
                    {
                        "type": "tool_use",
                        "name": "emit_storyboard",
                        "input": {
                            "scenes": [
                                {
                                    "id": 0,
                                    "title": "Roadmap",
                                    "narration": "Capture intent, draft, and render.",
                                    "visual_prompt": "Dark roadmap beat.",
                                    "scene_type": "motion",
                                    "on_screen_text": ["Capture intent", "Draft storyboard", "Render video"],
                                    "staging_notes": "clean staggered roadmap cards",
                                }
                            ]
                        },
                    }
                ]
            }
        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(
                        {
                            "summary": "Strong deterministic roadmap beat.",
                            "recommendation": "promote",
                            "scores": {
                                "creativity": 8,
                                "clarity": 9,
                                "deterministic_anchors": 9,
                                "planner_fit": 9,
                                "remotion_exploitability": 9,
                            },
                            "strengths": ["Exact copy", "Strong pacing"],
                            "weaknesses": [],
                            "notes_for_prompting": ["Good roadmap example"],
                        }
                    ),
                }
            ]
        }

    monkeypatch.setattr("core.director_golden.DIRECTOR_SCENARIOS_DIR", scenarios_dir)
    monkeypatch.setattr("core.director_golden.run_anthropic_curl", fake_run)

    run_dir = tmp_path / "run"
    result = harvest_scenario(
        scenario_id="demo",
        run_dir=run_dir,
        judge=True,
        render_preview=False,
    )

    assert result["run_dir"] == str(run_dir)
    assert (run_dir / "brief.json").exists()
    assert (run_dir / "request.json").exists()
    assert (run_dir / "response_parsed.json").exists()
    assert (run_dir / "judge_response_parsed.json").exists()
    parsed_storyboard = json.loads((run_dir / "response_parsed.json").read_text())
    assert parsed_storyboard["scenes"][0]["scene_type"] == "motion"


def test_promote_example_writes_example_bundle_and_updates_index(tmp_path, monkeypatch):
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "brief.json").write_text('{"project_name":"demo"}', encoding="utf-8")
    (run_dir / "response_parsed.json").write_text('{"scenes":[{"title":"Demo"}]}', encoding="utf-8")
    (run_dir / "judge_response_parsed.json").write_text(
        json.dumps(
            {
                "summary": "Great multi-voice pacing.",
                "strengths": ["Strong structure"],
                "notes_for_prompting": ["Keep the narrator spine"],
            }
        ),
        encoding="utf-8",
    )

    promoted_root = tmp_path / "promoted"
    monkeypatch.setattr("core.director_golden.PROMOTED_DIRECTOR_EXAMPLES_DIR", promoted_root)
    monkeypatch.setattr("core.director_golden.PROMOTED_DIRECTOR_EXAMPLES_INDEX", promoted_root / "index.json")

    metadata = promote_example(
        run_dir=run_dir,
        example_id="multi_voice_pitch__v1",
        title="Pitch Example",
        intents=["multi_voice_pitch"],
    )

    example_dir = promoted_root / "multi_voice_pitch__v1"
    assert metadata["id"] == "multi_voice_pitch__v1"
    assert (example_dir / "input_brief.json").exists()
    assert (example_dir / "expected_storyboard.json").exists()
    assert (example_dir / "why_it_is_good.md").exists()
    index = json.loads((promoted_root / "index.json").read_text())
    assert index[0]["id"] == "multi_voice_pitch__v1"


def test_materialize_run_builds_mini_project_with_asset_and_render_calls(tmp_path, monkeypatch):
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "brief.json").write_text(
        json.dumps(
            {
                "project_name": "demo",
                "source_mode": "ideas_notes",
                "source_material": "Explain the workflow clearly.",
            }
        ),
        encoding="utf-8",
    )
    (run_dir / "response_parsed.json").write_text(
        json.dumps(
            {
                "scenes": [
                    {
                        "id": 0,
                        "title": "Hook",
                        "narration": "Start strong.",
                        "visual_prompt": "Premium title card.",
                    },
                    {
                        "id": 1,
                        "title": "Roadmap",
                        "narration": "Three steps from brief to render.",
                        "visual_prompt": "Roadmap beat.",
                        "scene_type": "motion",
                        "on_screen_text": ["Capture intent", "Draft storyboard", "Render video"],
                    },
                ]
            }
        ),
        encoding="utf-8",
    )

    captured = {}

    monkeypatch.setattr("core.director_golden.generate_project_assets_service", lambda *args, **kwargs: {"images_generated": 2})
    monkeypatch.setattr("core.director_golden.render_project_service", lambda *args, **kwargs: {"video_path": str(run_dir / "mini_video.mp4")})

    result = materialize_run(run_dir=run_dir, scene_count=2)

    assert result["scene_count"] == 2
    assert result["assets"]["images_generated"] == 2
    assert result["render"]["video_path"].endswith("mini_video.mp4")
    assert (run_dir / "materialized_result.json").exists()
