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
