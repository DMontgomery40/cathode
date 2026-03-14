from core.workflow import create_plan_from_brief, rebuild_plan_from_meta


def _sample_scene():
    return {
        "id": 0,
        "title": "Intro",
        "narration": "Welcome to the demo.",
        "visual_prompt": "Clean title card with text \"Welcome\".",
    }


def test_smoke_wizard_created_brief(monkeypatch):
    captured = {}

    def fake_generate(source, provider="openai"):
        captured["source"] = source
        captured["provider"] = provider
        return [_sample_scene()]

    monkeypatch.setattr("core.workflow.generate_storyboard", fake_generate)

    plan = create_plan_from_brief(
        project_name="wizard_demo",
        brief={
            "project_name": "wizard_demo",
            "source_mode": "ideas_notes",
            "video_goal": "Pitch a feature",
            "audience": "Executives",
            "source_material": "Rough notes only",
            "target_length_minutes": 2.5,
            "tone": "confident",
            "visual_style": "cinematic minimal",
            "must_include": "ROI metric",
            "must_avoid": "acronyms",
            "ending_cta": "Approve rollout",
        },
        provider="anthropic",
    )

    assert captured["provider"] == "anthropic"
    assert isinstance(captured["source"], dict)
    assert captured["source"]["source_mode"] == "ideas_notes"
    assert plan["meta"]["brief"]["video_goal"] == "Pitch a feature"
    assert plan["scenes"][0]["scene_type"] == "image"
    assert plan["scenes"][0]["composition"]["family"] == "media_pan"


def test_smoke_raw_script_path(monkeypatch):
    captured = {}

    def fake_generate(source, provider="openai"):
        captured["source"] = source
        return [_sample_scene()]

    monkeypatch.setattr("core.workflow.generate_storyboard", fake_generate)

    plan = create_plan_from_brief(
        project_name="script_demo",
        brief={
            "project_name": "script_demo",
            "source_mode": "final_script",
            "source_material": "",
            "raw_brief": "This is the final script to segment scene by scene.",
        },
        provider="openai",
    )

    assert captured["source"]["source_mode"] == "final_script"
    assert captured["source"]["source_material"] == "This is the final script to segment scene by scene."
    assert plan["meta"]["pipeline_mode"] == "generic_slides_v1"


def test_smoke_legacy_plan_rebuild(monkeypatch):
    captured = {}

    def fake_generate(source, provider="openai"):
        captured["source"] = source
        captured["provider"] = provider
        return [_sample_scene()]

    monkeypatch.setattr("core.workflow.generate_storyboard", fake_generate)

    legacy_plan = {
        "meta": {
            "project_name": "legacy_plan",
            "input_text": "Legacy script block.",
            "llm_provider": "anthropic",
        },
        "scenes": [],
    }
    rebuilt = rebuild_plan_from_meta(legacy_plan)

    assert isinstance(captured["source"], dict)
    assert captured["source"]["source_material"] == "Legacy script block."
    assert captured["provider"] == "anthropic"
    assert rebuilt["scenes"][0]["image_path"] is None
    assert rebuilt["scenes"][0]["audio_path"] is None
    assert rebuilt["scenes"][0]["scene_type"] == "image"
    assert rebuilt["scenes"][0]["composition"]["family"] == "media_pan"


def test_motion_only_brief_converts_storyboard_to_motion_scenes(monkeypatch):
    def fake_generate(_source, provider="openai"):
        return [_sample_scene()]

    monkeypatch.setattr("core.workflow.generate_storyboard", fake_generate)

    plan = create_plan_from_brief(
        project_name="motion_only_demo",
        brief={
            "project_name": "motion_only_demo",
            "source_mode": "ideas_notes",
            "source_material": "Prompt ladder demo",
            "composition_mode": "motion_only",
        },
        provider="openai",
    )

    scene = plan["scenes"][0]
    assert scene["scene_type"] == "motion"
    assert scene["image_path"] is None
    assert scene["video_path"] is None
    assert scene["motion"]["template_id"]
    assert scene["composition"]["mode"] == "native"


def test_create_plan_from_brief_assigns_scene_voice_overrides_for_multiple_speakers(monkeypatch):
    def fake_generate(_source, provider="openai"):
        return [
            {
                "id": 0,
                "title": "Intro",
                "narration": "Narrator intro.",
                "visual_prompt": "Title card.",
                "speaker_name": "Bella",
            },
            {
                "id": 1,
                "title": "Agent",
                "narration": "Luxury listing pitch.",
                "visual_prompt": "House frame.",
                "speaker_name": "Real Estate Agent",
            },
        ]

    monkeypatch.setattr("core.workflow.generate_storyboard", fake_generate)
    monkeypatch.setattr(
        "core.workflow.available_tts_providers",
        lambda keys=None: {
            "kokoro": "Kokoro (Local)",
            "elevenlabs": "ElevenLabs (API / Replicate fallback)",
        },
    )

    plan = create_plan_from_brief(
        project_name="voice_plan_demo",
        brief={
            "project_name": "voice_plan_demo",
            "source_mode": "ideas_notes",
            "source_material": "Use Bella as narrator and different ElevenLabs voices for each section.",
        },
        provider="anthropic",
    )

    narrator_scene, agent_scene = plan["scenes"]
    assert plan["meta"]["tts_profile"]["provider"] == "elevenlabs"
    assert plan["meta"]["tts_profile"]["voice"] == "Bella"
    assert narrator_scene["tts_override_enabled"] is False
    assert agent_scene["tts_override_enabled"] is True
    assert agent_scene["tts_provider"] == "elevenlabs"
    assert agent_scene["tts_voice"]
    assert agent_scene["tts_voice"] != "Bella"


def test_create_plan_from_brief_prefers_explicit_composition_intent_over_heuristics(monkeypatch):
    def fake_generate(_source, provider="openai"):
        return [
            {
                "id": 0,
                "title": "Ranking scene",
                "narration": "Show the top categories as a spatial ranking.",
                "visual_prompt": "Three-dimensional comparison world.",
                "composition_intent": {
                    "family_hint": "three_data_stage",
                    "mode_hint": "native",
                    "layout": "three podium towers in depth",
                    "motion_notes": "camera rises from lowest rank to highest rank",
                    "transition_after": "fade",
                    "data_points": ["#3 Services", "#2 Licensing", "#1 Production"],
                },
            }
        ]

    monkeypatch.setattr("core.workflow.generate_storyboard", fake_generate)

    plan = create_plan_from_brief(
        project_name="composition_intent_demo",
        brief={
            "project_name": "composition_intent_demo",
            "source_mode": "ideas_notes",
            "source_material": "Rank the business options.",
        },
        provider="anthropic",
    )

    scene = plan["scenes"][0]
    assert scene["composition"]["family"] == "three_data_stage"
    assert scene["composition"]["mode"] == "native"
    assert scene["composition"]["transition_after"]["kind"] == "fade"
    assert scene["composition"]["data"]["data_points"] == ["#3 Services", "#2 Licensing", "#1 Production"]


def test_create_plan_from_brief_maps_thin_motion_fields_into_deterministic_composition(monkeypatch):
    def fake_generate(_source, provider="openai"):
        return [
            {
                "id": 0,
                "title": "Workflow roadmap",
                "narration": "Here is the three-step path from brief to render.",
                "visual_prompt": "Elegant motion roadmap beat.",
                "scene_type": "motion",
                "on_screen_text": ["Capture intent", "Draft the storyboard", "Generate and render"],
                "staging_notes": "clean dark roadmap with staggered card reveals",
                "transition_hint": "wipe",
            }
        ]

    monkeypatch.setattr("core.workflow.generate_storyboard", fake_generate)

    plan = create_plan_from_brief(
        project_name="thin_motion_contract_demo",
        brief={
            "project_name": "thin_motion_contract_demo",
            "source_mode": "ideas_notes",
            "source_material": "Explain the simple workflow.",
        },
        provider="anthropic",
    )

    scene = plan["scenes"][0]
    assert scene["composition"]["mode"] == "native"
    assert scene["composition"]["family"] == "bullet_stack"
    assert scene["composition"]["transition_after"]["kind"] == "wipe"


def test_pitch_style_raw_brief_stays_intact_and_yields_multi_voice_motion_capable_plan(monkeypatch):
    captured = {}

    def fake_generate(source, provider="openai"):
        captured["source"] = source
        return [
            {
                "id": 0,
                "title": "Hook",
                "narration": "Bella sets up the opportunity.",
                "visual_prompt": "Premium title card.",
                "speaker_name": "Bella",
            },
            {
                "id": 1,
                "title": "Business Model",
                "narration": "A motion roadmap explains how the system works.",
                "visual_prompt": "Deterministic roadmap beat.",
                "scene_type": "motion",
                "on_screen_text": ["We make the video", "Someone sells it", "Everyone gets paid"],
                "staging_notes": "clean dark roadmap with staggered reveals",
            },
            {
                "id": 2,
                "title": "Real Estate Spot",
                "narration": "A real estate agent delivers the ad read.",
                "visual_prompt": "Luxury listing commercial frame.",
                "speaker_name": "Real Estate Agent",
            },
        ]

    monkeypatch.setattr("core.workflow.generate_storyboard", fake_generate)
    monkeypatch.setattr(
        "core.workflow.available_tts_providers",
        lambda keys=None: {
            "kokoro": "Kokoro (Local)",
            "elevenlabs": "ElevenLabs (API / Replicate fallback)",
        },
    )

    raw_pitch_dump = (
        "I need to make a video convincing my wife that this is a no-brainer business. "
        "Use Bella as narrator but not too much. Use multiple recurring commercial voices and all 11 labs voices. "
        "Show how easy it is now that the pipeline is tuned."
    )

    plan = create_plan_from_brief(
        project_name="pitch_benchmark_demo",
        brief={
            "project_name": "pitch_benchmark_demo",
            "source_mode": "ideas_notes",
            "source_material": raw_pitch_dump,
            "tone": "friendly, persuasive, funny",
        },
        provider="anthropic",
    )

    assert captured["source"]["source_material"] == raw_pitch_dump
    assert plan["meta"]["brief"]["source_material"] == raw_pitch_dump
    assert plan["scenes"][0]["tts_override_enabled"] is False
    assert plan["scenes"][2]["tts_override_enabled"] is True
    assert plan["scenes"][2]["tts_provider"] == "elevenlabs"
    assert plan["meta"]["render_profile"]["render_backend"] == "remotion"
