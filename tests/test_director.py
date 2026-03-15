import base64
import json

from core.director import (
    _build_storyboard_user_prompt_from_brief,
    _validate_scenes,
    analyze_style_references,
    build_director_system_prompt,
)
from core.project_schema import normalize_brief


def test_director_prompt_includes_source_mode_behavior_and_brief_payload():
    brief = normalize_brief(
        {
            "project_name": "demo",
            "source_mode": "final_script",
            "video_goal": "Explain the product launch",
            "audience": "Sales engineering team",
            "source_material": "Section A. Section B. Section C.",
            "target_length_minutes": 4.0,
            "tone": "direct and concise",
            "visual_style": "modern infographic",
            "video_scene_style": "speaking",
            "text_render_mode": "deterministic_overlay",
            "style_reference_summary": "High-contrast editorial lighting, restrained teal-and-amber palette, premium product-demo polish, crisp typography, dense but organized composition.",
            "must_include": "timeline",
            "must_avoid": "jargon",
            "ending_cta": "Book a pilot",
            "composition_mode": "hybrid",
        }
    )

    prompt = _build_storyboard_user_prompt_from_brief(brief)

    assert "mode: final_script" in prompt
    assert "Perform minimal rewriting" in prompt
    assert '"video_goal": "Explain the product launch"' in prompt
    assert '"visual_style": "modern infographic"' in prompt
    assert '"video_scene_style": "speaking"' in prompt
    assert '"text_render_mode": "deterministic_overlay"' in prompt
    assert '"style_reference_summary": "High-contrast editorial lighting, restrained teal-and-amber palette, premium product-demo polish, crisp typography, dense but organized composition."' in prompt
    assert '"composition_mode": "hybrid"' in prompt
    assert "target narration words" in prompt
    assert 'reserve on_screen_text for Cathode\'s deterministic overlay' in prompt
    assert '"staging_notes"' in prompt
    assert '"data_points"' in prompt
    assert '"transition_hint"' in prompt
    assert '"composition_intent"' not in prompt


def test_director_system_prompt_selects_capability_blocks():
    prompt = build_director_system_prompt(
        normalize_brief(
            {
                "source_mode": "ideas_notes",
                "source_material": "Use Bella as narrator and different ElevenLabs voices for each section.",
                "visual_source_strategy": "mixed_media",
                "video_scene_style": "speaking",
                "text_render_mode": "deterministic_overlay",
                "composition_mode": "hybrid",
            }
        )
    )

    assert "Capability mode: mixed media." in prompt
    assert "Video style preference: speaking." in prompt
    assert "Capability mode: deterministic overlay." in prompt
    assert "Capability mode: hybrid composition." in prompt
    assert "Capability mode: multi-voice storytelling." in prompt


def test_director_system_prompt_selects_promoted_examples(tmp_path, monkeypatch):
    examples_dir = tmp_path / "director_examples"
    example_dir = examples_dir / "multi_voice_pitch__v1"
    example_dir.mkdir(parents=True)
    (example_dir / "input_brief.json").write_text('{"project_name":"pitch"}', encoding="utf-8")
    (example_dir / "expected_storyboard.json").write_text('{"scenes":[{"title":"Pitch"}]}', encoding="utf-8")
    (example_dir / "why_it_is_good.md").write_text("Great multi-voice pacing.", encoding="utf-8")
    index_path = examples_dir / "index.json"
    index_path.write_text(
        '[{"id":"multi_voice_pitch__v1","title":"Pitch Example","intents":["multi_voice_pitch"]}]',
        encoding="utf-8",
    )

    monkeypatch.setattr("core.director._DIRECTOR_EXAMPLES_INDEX", index_path)

    prompt = build_director_system_prompt(
        normalize_brief(
            {
                "source_mode": "ideas_notes",
                "source_material": "Use Bella as narrator and different voices for commercial examples.",
            }
        )
    )

    assert "Promoted Cathode examples:" in prompt
    assert 'Example "Pitch Example"' in prompt
    assert "Great multi-voice pacing." in prompt


def test_director_system_prompt_selects_whimsical_example_over_abstract_default(tmp_path, monkeypatch):
    examples_dir = tmp_path / "director_examples"
    whimsical_dir = examples_dir / "whimsical_storybook__v1"
    abstract_dir = examples_dir / "static_image_control__v1"
    whimsical_dir.mkdir(parents=True)
    abstract_dir.mkdir(parents=True)
    for example_dir, brief_text, title in (
        (whimsical_dir, '{"project_name":"whimsy"}', "Whimsical Example"),
        (abstract_dir, '{"project_name":"abstract"}', "Abstract Example"),
    ):
        (example_dir / "input_brief.json").write_text(brief_text, encoding="utf-8")
        (example_dir / "expected_storyboard.json").write_text('{"scenes":[{"title":"Scene"}]}', encoding="utf-8")
        (example_dir / "why_it_is_good.md").write_text(title, encoding="utf-8")
    index_path = examples_dir / "index.json"
    index_path.write_text(
        json.dumps(
            [
                {"id": "whimsical_storybook__v1", "title": "Whimsical Example", "intents": ["whimsical_storybook"]},
                {"id": "static_image_control__v1", "title": "Abstract Example", "intents": ["static_image_control"]},
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr("core.director._DIRECTOR_EXAMPLES_INDEX", index_path)

    prompt = build_director_system_prompt(
        normalize_brief(
            {
                "source_mode": "ideas_notes",
                "source_material": "Tell a story about an impossible encounter, but it must not contain the obvious thing.",
                "visual_style": "whimsical storybook cinema",
                "tone": "playful and magical",
            }
        )
    )

    assert "Whimsical Example" in prompt
    assert "Abstract Example" not in prompt


def test_director_system_prompt_does_not_force_static_example_for_unclassified_brief(tmp_path, monkeypatch):
    examples_dir = tmp_path / "director_examples"
    example_dir = examples_dir / "static_image_control__v1"
    example_dir.mkdir(parents=True)
    (example_dir / "input_brief.json").write_text('{"project_name":"abstract"}', encoding="utf-8")
    (example_dir / "expected_storyboard.json").write_text('{"scenes":[{"title":"Scene"}]}', encoding="utf-8")
    (example_dir / "why_it_is_good.md").write_text("Abstract Example", encoding="utf-8")
    index_path = examples_dir / "index.json"
    index_path.write_text(
        '[{"id":"static_image_control__v1","title":"Abstract Example","intents":["static_image_control"]}]',
        encoding="utf-8",
    )

    monkeypatch.setattr("core.director._DIRECTOR_EXAMPLES_INDEX", index_path)

    prompt = build_director_system_prompt(
        normalize_brief(
            {
                "source_mode": "ideas_notes",
                "source_material": "Explain the quarterly rollout plan clearly.",
                "video_goal": "Orient the team to the plan.",
                "audience": "Internal team",
            }
        )
    )

    assert "Promoted Cathode examples:" not in prompt


def test_director_prompt_mentions_reviewed_footage_assets():
    brief = normalize_brief(
        {
            "project_name": "demo",
            "video_goal": "Explain the product",
            "audience": "Developers",
            "source_material": "Feature walkthrough.",
            "visual_source_strategy": "mixed_media",
            "footage_manifest": [
                {
                    "id": "run_review",
                    "path": "/tmp/run_review.mp4",
                    "label": "Run review overlay",
                    "notes": "Saved overlay playback with diagnostics visible.",
                    "review_status": "warn",
                    "review_summary": "Use with a caveat; the state is real but not ideal.",
                }
            ],
        }
    )

    prompt = _build_storyboard_user_prompt_from_brief(brief)

    assert '"footage_manifest"' in prompt
    assert '"review_status": "warn"' in prompt
    assert '"footage_asset_id"' in prompt


def test_analyze_style_references_openai_builds_multimodal_request(tmp_path, monkeypatch):
    image_path = tmp_path / "ref.png"
    image_path.write_bytes(base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jK6cAAAAASUVORK5CYII="
    ))
    captured = {}

    class FakeResponses:
        def create(self, **kwargs):
            captured.update(kwargs)
            return type("Resp", (), {"output_text": "Detailed style summary"})()

    class FakeClient:
        responses = FakeResponses()

    monkeypatch.setattr("core.director._get_openai_client", lambda: FakeClient())
    monkeypatch.setattr("core.director.load_prompt", lambda name: "system prompt")

    summary = analyze_style_references(
        [str(image_path)],
        normalize_brief({"audience": "Design-conscious buyers", "video_goal": "Pitch the product"}),
        provider="openai",
    )

    assert summary == "Detailed style summary"
    assert captured["instructions"] == "system prompt"
    assert captured["input"][0]["content"][0]["type"] == "input_text"
    assert captured["input"][0]["content"][1]["type"] == "input_image"
    assert captured["input"][0]["content"][1]["image_url"].startswith("data:image/png;base64,")


def test_analyze_style_references_anthropic_builds_multimodal_request(tmp_path, monkeypatch):
    image_path = tmp_path / "ref.png"
    image_path.write_bytes(base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jK6cAAAAASUVORK5CYII="
    ))
    captured = {}

    class FakeMessages:
        def create(self, **kwargs):
            captured.update(kwargs)
            return type("Resp", (), {"content": [type("Block", (), {"text": "Anthropic style summary"})()]})()

    class FakeClient:
        messages = FakeMessages()

    monkeypatch.setattr("core.director._get_anthropic_client", lambda: FakeClient())
    monkeypatch.setattr("core.director.load_prompt", lambda name: "system prompt")

    summary = analyze_style_references(
        [str(image_path)],
        normalize_brief({"audience": "Exec team", "video_goal": "Explain the concept"}),
        provider="anthropic",
    )

    assert summary == "Anthropic style summary"
    assert captured["system"] == "system prompt"
    assert captured["messages"][0]["content"][0]["type"] == "image"
    assert captured["messages"][0]["content"][-1]["type"] == "text"


def test_validate_scenes_drops_model_supplied_video_path():
    scenes = _validate_scenes(
        [
            {
                "id": 0,
                "title": "Footage Scene",
                "narration": "Show the reviewed clip.",
                "visual_prompt": "Use the supplied footage.",
                "scene_type": "video",
                "footage_asset_id": "hero_capture",
                "video_path": "/tmp/hallucinated.mp4",
            }
        ]
    )

    assert scenes[0]["footage_asset_id"] == "hero_capture"
    assert scenes[0]["video_path"] is None


def test_validate_scenes_preserves_video_scene_kind_and_speaker_name():
    scenes = _validate_scenes(
        [
            {
                "id": 0,
                "title": "Founder Pitch",
                "narration": "We built this to save teams hours every week.",
                "visual_prompt": "Founder speaking directly to camera in a bright office.",
                "scene_type": "video",
                "video_scene_kind": "speaking",
                "speaker_name": "Founder",
            }
        ]
    )

    assert scenes[0]["video_scene_kind"] == "speaking"
    assert scenes[0]["speaker_name"] == "Founder"


def test_validate_scenes_keeps_thin_motion_fields():
    scenes = _validate_scenes(
        [
            {
                "id": 0,
                "title": "Pricing proof",
                "narration": "The key number needs a stronger animated beat.",
                "visual_prompt": "Centered pricing card.",
                "scene_type": "motion",
                "staging_notes": "headline slams in, source line fades up",
                "transition_hint": "fade",
                "data_points": ["$500 per video", "$200 to salesperson"],
            }
        ]
    )

    assert scenes[0]["scene_type"] == "motion"
    assert scenes[0]["staging_notes"] == "headline slams in, source line fades up"
    assert scenes[0]["transition_hint"] == "fade"
    assert scenes[0]["data_points"] == ["$500 per video", "$200 to salesperson"]


def test_validate_scenes_still_accepts_legacy_composition_intent():
    scenes = _validate_scenes(
        [
            {
                "id": 0,
                "title": "Legacy ranking scene",
                "narration": "Show the top categories as a spatial ranking.",
                "visual_prompt": "Three-dimensional comparison world.",
                "composition_intent": {
                    "family_hint": "three_data_stage",
                    "mode_hint": "native",
                    "layout": "three podium towers in depth",
                    "motion_notes": "camera rises from lowest rank to highest rank",
                    "transition_after": "fade",
                    "data_points": ["#3 Services", "#2 Licensing", "#1 Production"]
                }
            }
        ]
    )

    assert scenes[0]["staging_notes"] == "three podium towers in depth camera rises from lowest rank to highest rank"
    assert scenes[0]["transition_hint"] == "fade"
    assert scenes[0]["data_points"] == ["#3 Services", "#2 Licensing", "#1 Production"]
    assert scenes[0]["composition_intent"]["family_hint"] == "three_data_stage"
