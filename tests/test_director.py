import base64
import json

from core.director import (
    _build_storyboard_user_prompt_from_brief,
    _validate_scenes,
    analyze_style_references,
    build_director_system_prompt,
    generate_storyboard_with_metadata,
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
    assert 'for scenes Cathode explicitly renders as deterministic overlays or motion templates' in prompt
    assert '"staging_notes"' in prompt
    assert '"data_points"' in prompt
    assert '"transition_hint"' in prompt
    assert '"composition_intent"' in prompt
    assert '"manifestation_plan"' in prompt
    assert '"native_build_prompt"' in prompt
    assert '"authored_image"' in prompt
    assert '"native_remotion"' in prompt
    assert '"source_video"' in prompt
    assert "Do not expect code-side prompt mutation before Qwen." in prompt
    assert "No OCR." in prompt


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


def test_director_system_prompt_includes_official_remotion_stack_for_anthropic_only():
    brief = normalize_brief(
        {
            "source_mode": "ideas_notes",
            "source_material": "Explain the workflow clearly.",
        }
    )

    anthropic_prompt = build_director_system_prompt(brief, provider="anthropic")
    openai_prompt = build_director_system_prompt(brief, provider="openai")

    assert "# About Remotion" in anthropic_prompt
    assert "Cathode manifestation-path contract." in anthropic_prompt
    assert "Cathode supported-family registry constraints." in anthropic_prompt
    assert "# About Remotion" not in openai_prompt
    assert "Cathode manifestation-path contract." not in openai_prompt


def test_director_system_prompt_selects_clinical_data_authored_stills_capability():
    prompt = build_director_system_prompt(
        normalize_brief(
            {
                "source_mode": "source_text",
                "video_goal": "Educate the patient on their assessment data.",
                "audience": "The patient whose report this is.",
                "source_material": "Assessment results across sessions with reference ranges and follow-up recommendations.",
            }
        )
    )

    assert "Capability mode: authored clinical data stills." in prompt


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


def test_director_prompt_warns_clinical_results_explainers_away_from_camera_pan():
    prompt = _build_storyboard_user_prompt_from_brief(
        normalize_brief(
            {
                "project_name": "clinical_results_demo",
                "source_mode": "source_text",
                "video_goal": "Explain the patient assessment results clearly.",
                "audience": "The patient whose report this is.",
                "source_material": "Assessment results across sessions with reference ranges and test scores.",
            }
        )
    )

    assert "prefer calm authored stills with exact labels, charts, and comparison layouts rather than camera-pan treatment" in prompt


def test_director_prompt_uses_tighter_runtime_budget_for_longer_videos():
    prompt = _build_storyboard_user_prompt_from_brief(
        normalize_brief(
            {
                "project_name": "runtime_budget_demo",
                "source_mode": "ideas_notes",
                "video_goal": "Explain the progression clearly.",
                "audience": "General audience",
                "source_material": "Walk through the baseline, shifts, and conclusion.",
                "target_length_minutes": 6.0,
            }
        )
    )

    assert "target narration words: 702-858 total across all scenes" in prompt
    assert "Produce 12-20 scenes." in prompt
    assert "landing below 85% of the target is a failure" in prompt
    assert "most scene narrations should be 1-3 sentences" in prompt
    assert "Aim for the finished storyboard to land roughly within 85%-115% of the requested runtime" in prompt


def test_director_clinical_template_prompt_forbids_transitions():
    """Clinical template system prompt must instruct hard cuts, no transitions."""
    prompt = build_director_system_prompt(
        normalize_brief(
            {
                "source_mode": "source_text",
                "video_goal": "Educate the patient on their assessment data.",
                "audience": "The patient whose report this is.",
                "source_material": "Assessment results across sessions with reference ranges.",
            }
        ),
        provider="anthropic",
    )

    assert "transition_after to null" in prompt or "transition_after" in prompt
    assert "hard cut" in prompt.lower() or "Hard cuts" in prompt


def test_director_clinical_template_prompt_documents_brain_region_names():
    """Clinical template prompt must list the recognized brain region names for coordinate mapping."""
    prompt = build_director_system_prompt(
        normalize_brief(
            {
                "source_mode": "source_text",
                "video_goal": "Educate the patient on their assessment data.",
                "audience": "The patient whose report this is.",
                "source_material": "Assessment results across sessions.",
            }
        ),
        provider="anthropic",
    )

    for region in ["Frontal", "Central", "Parietal", "Temporal", "Occipital"]:
        assert region in prompt, f"Missing region {region!r} from brain_region_focus coordinate table"


def test_director_deterministic_overlay_prefers_template_families_over_authored_stills():
    """When deterministic overlay is active on a clinical brief, the prompt should tell the director
    to prefer clinical template families, not authored stills."""
    prompt_user = _build_storyboard_user_prompt_from_brief(
        normalize_brief(
            {
                "source_mode": "source_text",
                "video_goal": "Educate the patient on their assessment data.",
                "audience": "The patient whose report this is.",
                "source_material": "Assessment results across sessions with reference ranges.",
                "text_render_mode": "deterministic_overlay",
            }
        )
    )
    # Should NOT say "prefer calm authored stills"
    assert "prefer calm authored stills" not in prompt_user
    # Should say to use clinical template families
    assert "clinical template composition families" in prompt_user
    assert "three_data_stage" in prompt_user  # mentions reserving it

    prompt_system = build_director_system_prompt(
        normalize_brief(
            {
                "source_mode": "source_text",
                "video_goal": "Educate the patient on their assessment data.",
                "audience": "The patient whose report this is.",
                "source_material": "Assessment results across sessions with reference ranges.",
                "text_render_mode": "deterministic_overlay",
            }
        ),
        provider="anthropic",
    )
    # Registry constraints should prefer templates
    assert "prefer the clinical template composition families" in prompt_system
    # Should NOT say "prefer authored stillness" when deterministic overlay is active
    assert "prefer authored stillness" not in prompt_system


def test_director_visual_authored_clinical_still_prefers_authored_stills():
    """When visual_authored is active on a clinical brief, the prompt should still prefer authored stills."""
    prompt_user = _build_storyboard_user_prompt_from_brief(
        normalize_brief(
            {
                "source_mode": "source_text",
                "video_goal": "Educate the patient on their assessment data.",
                "audience": "The patient whose report this is.",
                "source_material": "Assessment results across sessions with reference ranges.",
                "text_render_mode": "visual_authored",
            }
        )
    )
    assert "prefer calm authored stills" in prompt_user


def test_director_clinical_template_diversity_guidance():
    """Clinical template prompt should include the family selection table and diversity requirement."""
    prompt = build_director_system_prompt(
        normalize_brief(
            {
                "source_mode": "source_text",
                "video_goal": "Educate the patient on their assessment data.",
                "audience": "The patient whose report this is.",
                "source_material": "Assessment results across sessions.",
                "text_render_mode": "deterministic_overlay",
            }
        ),
        provider="anthropic",
    )
    # Should have the family selection table differentiating from three_data_stage
    assert "metric_improvement" in prompt
    assert "brain_region_focus" in prompt
    assert "metric_comparison" in prompt
    assert "timeline_progression" in prompt
    assert "analogy_metaphor" in prompt
    assert "synthesis_summary" in prompt
    # Diversity requirement
    assert "at least 7 different template families" in prompt


def test_generate_storyboard_repairs_openai_storyboard_when_runtime_budget_is_blown(monkeypatch):
    calls: list[str] = []

    def make_scene(index: int, word_count: int) -> dict[str, object]:
        return {
            "id": index,
            "title": f"Scene {index + 1}",
            "narration": " ".join([f"word{index}"] * word_count),
            "visual_prompt": f"Visual beat {index + 1}",
        }

    over_budget_scenes = [make_scene(index, 45) for index in range(22)]
    repaired_scenes = [make_scene(index, 20) for index in range(12)]

    def fake_generate(system_prompt, user_prompt, *, return_response=False):
        calls.append(user_prompt)
        scenes = over_budget_scenes if len(calls) == 1 else repaired_scenes
        response = type("Resp", (), {"usage": None})()
        if return_response:
            return scenes, response
        return scenes

    monkeypatch.setattr("core.director.build_director_system_prompt", lambda brief, **kwargs: "system prompt")
    monkeypatch.setattr("core.director._generate_with_openai", fake_generate)

    scenes, metadata = generate_storyboard_with_metadata(
        {
            "project_name": "runtime_repair_demo",
            "source_mode": "ideas_notes",
            "video_goal": "Explain the progression clearly.",
            "audience": "General audience",
            "source_material": "Walk through the baseline, shifts, and conclusion.",
            "target_length_minutes": 3.0,
        },
        provider="openai",
    )

    assert scenes == repaired_scenes
    assert len(calls) == 2
    assert "Revise this storyboard so it actually fits the runtime budget." in calls[1]
    assert "current scenes: 22" in calls[1]
    assert metadata["runtime_repair"]["operation"] == "storyboard_runtime_repair"


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
    assert scenes[0]["manifestation_plan"]["primary_path"] == "source_video"


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
    assert scenes[0]["manifestation_plan"]["primary_path"] == "native_remotion"


def test_validate_scenes_derives_scene_type_from_manifestation_plan_when_missing():
    scenes = _validate_scenes(
        [
            {
                "id": 0,
                "title": "Reviewed clip",
                "narration": "Use the supplied walkthrough clip here.",
                "visual_prompt": "UI cursor moves through the key workflow.",
                "manifestation_plan": {
                    "primary_path": "source_video",
                    "fallback_path": "authored_image",
                    "risk_level": "medium",
                    "failure_notes": ["Footage may be too cramped on smaller viewports."],
                },
            }
        ]
    )

    assert scenes[0]["scene_type"] == "video"
    assert scenes[0]["manifestation_plan"]["primary_path"] == "source_video"
    assert scenes[0]["manifestation_plan"]["fallback_path"] == "authored_image"
    assert scenes[0]["manifestation_plan"]["risk_level"] == "medium"


def test_validate_scenes_keeps_native_build_prompt_inside_manifestation_plan():
    scenes = _validate_scenes(
        [
            {
                "id": 0,
                "title": "Data proof",
                "narration": "Stage the ranked outcomes in one deterministic beat.",
                "visual_prompt": "Three-dimensional data tableau.",
                "scene_type": "motion",
                "on_screen_text": ["Fastest", "Most Stable", "Lowest Cost"],
                "native_build_prompt": "Native build: three illuminated podiums with exact labels.",
                "manifestation_plan": {
                    "primary_path": "native_remotion",
                    "fallback_path": "authored_image",
                    "native_family_hint": "three_data_stage",
                    "text_critical": True,
                },
            }
        ]
    )

    assert scenes[0]["manifestation_plan"]["primary_path"] == "native_remotion"
    assert scenes[0]["manifestation_plan"]["native_family_hint"] == "three_data_stage"
    assert scenes[0]["manifestation_plan"]["native_build_prompt"] == "Native build: three illuminated podiums with exact labels."
    assert scenes[0]["manifestation_plan"]["text_expected"] is True
    assert scenes[0]["manifestation_plan"]["text_critical"] is True


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
    assert scenes[0]["scene_type"] == "motion"
    assert scenes[0]["manifestation_plan"]["primary_path"] == "native_remotion"
    assert scenes[0]["manifestation_plan"]["native_family_hint"] == "three_data_stage"
