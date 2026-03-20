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
        return [_sample_scene()], {}

    monkeypatch.setattr("core.workflow.generate_storyboard_with_metadata", fake_generate)
    monkeypatch.setattr("core.workflow.plan_scene_treatments_with_metadata", lambda scenes, brief, provider: (scenes, {}))

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
        return [_sample_scene()], {}

    monkeypatch.setattr("core.workflow.generate_storyboard_with_metadata", fake_generate)
    monkeypatch.setattr("core.workflow.plan_scene_treatments_with_metadata", lambda scenes, brief, provider: (scenes, {}))

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
        return [_sample_scene()], {}

    monkeypatch.setattr("core.workflow.generate_storyboard_with_metadata", fake_generate)
    monkeypatch.setattr("core.workflow.plan_scene_treatments_with_metadata", lambda scenes, brief, provider: (scenes, {}))

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
        return [_sample_scene()], {}

    monkeypatch.setattr("core.workflow.generate_storyboard_with_metadata", fake_generate)
    monkeypatch.setattr("core.workflow.plan_scene_treatments_with_metadata", lambda scenes, brief, provider: (scenes, {}))

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


def test_motion_only_3d_tableau_scene_becomes_surreal_tableau_not_quote_focus(monkeypatch):
    def fake_generate(_source, provider="openai"):
        return [
            {
                "id": 0,
                "title": "The 3D Observatory Tableau — Orbiting Moths",
                "narration": (
                    "And then the observatory reveals its innermost room, where brass moths orbit a cracked moon "
                    "inside a chamber that seems to keep a different kind of time."
                ),
                "visual_prompt": (
                    "A fully three-dimensional surreal tableau in a vast dark chamber with deep indigo velvet walls, "
                    "a glowing cracked hourglass moon, orbiting brass moths, bending constellation lines, subtle volumetric fog, and a cinematic widescreen finish."
                ),
                "scene_type": "motion",
                "staging_notes": "This is the must-include hero scene. The camera performs a slow circular orbit around the tableau.",
            }
        ], {}

    monkeypatch.setattr("core.workflow.generate_storyboard_with_metadata", fake_generate)
    monkeypatch.setattr("core.workflow.plan_scene_treatments_with_metadata", lambda scenes, brief, provider: (scenes, {}))

    plan = create_plan_from_brief(
        project_name="moth_observatory_demo",
        brief={
            "project_name": "moth_observatory_demo",
            "source_mode": "ideas_notes",
            "source_material": "Build a motion-first surreal 3D observatory scene with orbiting moths.",
            "composition_mode": "motion_only",
        },
        provider="openai",
    )

    scene = plan["scenes"][0]
    assert scene["composition"]["family"] == "surreal_tableau_3d"
    assert scene["motion"]["template_id"] == "surreal_tableau_3d"
    assert scene["composition"]["props"]["layoutVariant"] == "orbit_tableau"
    assert scene["composition"]["props"]["heroObject"] == "glowing cracked hourglass moon"


def test_motion_only_long_narration_alone_no_longer_forces_quote_focus(monkeypatch):
    def fake_generate(_source, provider="openai"):
        return [
            {
                "id": 0,
                "title": "Long motion beat",
                "narration": (
                    "This scene has intentionally long narration so the classifier has to decide based on the actual beat "
                    "instead of treating length alone as proof that it should become a generic centered text layout."
                ),
                "visual_prompt": "Elegant motion-first opener with animated typographic hierarchy.",
                "scene_type": "motion",
                "staging_notes": "Kinetic words rise and settle into a deliberate statement.",
            }
        ], {}

    monkeypatch.setattr("core.workflow.generate_storyboard_with_metadata", fake_generate)
    monkeypatch.setattr("core.workflow.plan_scene_treatments_with_metadata", lambda scenes, brief, provider: (scenes, {}))

    plan = create_plan_from_brief(
        project_name="long_motion_narration_demo",
        brief={
            "project_name": "long_motion_narration_demo",
            "source_mode": "ideas_notes",
            "source_material": "Create one motion-first statement beat.",
            "composition_mode": "motion_only",
        },
        provider="openai",
    )

    assert plan["scenes"][0]["composition"]["family"] != "quote_focus"


def test_create_plan_from_brief_can_split_creative_and_treatment_providers(monkeypatch):
    captured: dict[str, str] = {}

    def fake_generate(source, provider="openai"):
        captured["storyboard_provider"] = provider
        return [_sample_scene()], {}

    def fake_treat(scenes, brief, provider):
        captured["treatment_provider"] = provider
        return scenes, {}

    monkeypatch.setattr("core.workflow.generate_storyboard_with_metadata", fake_generate)
    monkeypatch.setattr("core.workflow.plan_scene_treatments_with_metadata", fake_treat)

    plan = create_plan_from_brief(
        project_name="provider_split_demo",
        brief={
            "project_name": "provider_split_demo",
            "source_mode": "ideas_notes",
            "source_material": "A creative brief that still needs deterministic machinery.",
        },
        provider="anthropic",
        storyboard_provider="anthropic",
        treatment_provider="openai",
    )

    assert captured["storyboard_provider"] == "anthropic"
    assert captured["treatment_provider"] == "openai"
    assert plan["meta"]["creative_llm_provider"] == "anthropic"
    assert plan["meta"]["treatment_llm_provider"] == "openai"


def test_create_plan_from_brief_records_runtime_repair_costs(monkeypatch):
    def fake_generate(source, provider="openai"):
        return [
            {
                "id": 0,
                "title": "Intro",
                "narration": "Welcome to the demo.",
                "visual_prompt": "Clean title card.",
            }
        ], {
            "actual": {"kind": "llm", "label": "storyboard", "total_usd": 0.12},
            "preflight": {"label": "storyboard_preflight"},
            "runtime_repair": {
                "actual": {"kind": "llm", "label": "storyboard_runtime_repair", "total_usd": 0.07},
                "preflight": {"label": "storyboard_runtime_repair_preflight"},
            },
        }

    monkeypatch.setattr("core.workflow.generate_storyboard_with_metadata", fake_generate)
    monkeypatch.setattr("core.workflow.plan_scene_treatments_with_metadata", lambda scenes, brief, provider: (scenes, {}))

    plan = create_plan_from_brief(
        project_name="runtime_repair_cost_demo",
        brief={
            "project_name": "runtime_repair_cost_demo",
            "source_mode": "ideas_notes",
            "source_material": "Explain the runtime fix.",
        },
        provider="openai",
    )

    entries = plan["meta"]["cost_actual"]["entries"]
    assert [entry["label"] for entry in entries] == ["storyboard", "storyboard_runtime_repair"]
    assert plan["meta"]["cost_actual"]["llm_preflight"] == {"label": "storyboard_preflight"}
    assert plan["meta"]["cost_actual"]["llm_preflight_runtime_repair"] == {
        "label": "storyboard_runtime_repair_preflight"
    }


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
        ], {}

    monkeypatch.setattr("core.workflow.generate_storyboard_with_metadata", fake_generate)
    monkeypatch.setattr("core.workflow.plan_scene_treatments_with_metadata", lambda scenes, brief, provider: (scenes, {}))
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
        ], {}

    monkeypatch.setattr("core.workflow.generate_storyboard_with_metadata", fake_generate)
    monkeypatch.setattr("core.workflow.plan_scene_treatments_with_metadata", lambda scenes, brief, provider: (scenes, {}))

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
        ], {}

    monkeypatch.setattr("core.workflow.generate_storyboard_with_metadata", fake_generate)
    monkeypatch.setattr("core.workflow.plan_scene_treatments_with_metadata", lambda scenes, brief, provider: (scenes, {}))

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


def test_create_plan_from_brief_keeps_whimsical_creative_brief_image_first(monkeypatch):
    def fake_generate(_source, provider="openai"):
        return [
            {
                "id": 0,
                "title": "Impossible hello",
                "narration": "A strange meeting unfolds under storybook moonlight.",
                "visual_prompt": "Warm illustrated meeting on a bridge.",
                "scene_type": "image",
            }
        ], {}

    monkeypatch.setattr("core.workflow.generate_storyboard_with_metadata", fake_generate)
    monkeypatch.setattr("core.workflow.plan_scene_treatments_with_metadata", lambda scenes, brief, provider: (scenes, {}))

    plan = create_plan_from_brief(
        project_name="whimsical_demo",
        brief={
            "project_name": "whimsical_demo",
            "source_mode": "ideas_notes",
            "source_material": "Tell a whimsical story about an impossible encounter, but it must not contain the obvious thing.",
            "visual_style": "storybook illustration",
            "tone": "playful and magical",
        },
        provider="anthropic",
    )

    scene = plan["scenes"][0]
    assert scene["scene_type"] == "image"
    assert scene["composition"]["family"] == "media_pan"
    assert plan["meta"]["render_profile"]["render_backend"] == "ffmpeg"


def test_create_plan_from_brief_finalizes_native_remotion_manifestation_after_treatment(monkeypatch):
    def fake_generate(_source, provider="openai"):
        return [_sample_scene()], {}

    def fake_treat(scenes, brief, provider):
        treated = dict(scenes[0])
        treated["composition"] = {
            "family": "software_demo_focus",
            "mode": "overlay",
            "props": {"headline": "Pinned callout"},
        }
        return [treated], {}

    monkeypatch.setattr("core.workflow.generate_storyboard_with_metadata", fake_generate)
    monkeypatch.setattr("core.workflow.plan_scene_treatments_with_metadata", fake_treat)

    plan = create_plan_from_brief(
        project_name="overlay_manifest_demo",
        brief={
            "project_name": "overlay_manifest_demo",
            "source_mode": "ideas_notes",
            "source_material": "Highlight one UI state with a pinned callout.",
        },
        provider="anthropic",
    )

    scene = plan["scenes"][0]
    assert scene["composition"]["manifestation"] == "native_remotion"
    assert plan["meta"]["render_profile"]["render_backend"] == "remotion"


def test_create_plan_from_brief_keeps_source_video_manifestation_when_treatment_adds_overlay(monkeypatch):
    def fake_generate(_source, provider="openai"):
        return [
            {
                "id": 0,
                "title": "Guided clip",
                "narration": "Walk through the product clip.",
                "visual_prompt": "Use the uploaded walkthrough clip.",
                "scene_type": "video",
            }
        ], {}

    def fake_treat(scenes, brief, provider):
        treated = dict(scenes[0])
        treated["composition"] = {
            "family": "software_demo_focus",
            "mode": "overlay",
            "props": {"headline": "Pinned callout"},
        }
        return [treated], {}

    monkeypatch.setattr("core.workflow.generate_storyboard_with_metadata", fake_generate)
    monkeypatch.setattr("core.workflow.plan_scene_treatments_with_metadata", fake_treat)

    plan = create_plan_from_brief(
        project_name="video_overlay_manifest_demo",
        brief={
            "project_name": "video_overlay_manifest_demo",
            "source_mode": "ideas_notes",
            "source_material": "Use the walkthrough clip and add one callout.",
        },
        provider="anthropic",
    )

    scene = plan["scenes"][0]
    assert scene["composition"]["manifestation"] == "source_video"
    assert plan["meta"]["render_profile"]["render_backend"] == "remotion"


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
        ], {}

    monkeypatch.setattr("core.workflow.generate_storyboard_with_metadata", fake_generate)
    monkeypatch.setattr("core.workflow.plan_scene_treatments_with_metadata", lambda scenes, brief, provider: (scenes, {}))
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
