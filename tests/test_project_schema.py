from core.project_schema import backfill_plan, normalize_brief


def test_normalize_brief_defaults_and_fallbacks():
    brief = normalize_brief(
        {
            "project_name": "My Demo!",
            "source_mode": "unknown_mode",
            "target_length_minutes": "not-a-number",
            "raw_brief": "Use this as source.",
        }
    )

    assert brief["project_name"] == "My_Demo_"
    assert brief["source_mode"] == "source_text"
    assert brief["visual_source_strategy"] == "images_only"
    assert brief["target_length_minutes"] == 3.0
    assert brief["source_material"] == "Use this as source."


def test_backfill_legacy_plan_adds_generic_defaults():
    legacy_plan = {
        "meta": {
            "project_name": "legacy_demo",
            "input_text": "Legacy source text",
            "llm_provider": "openai",
        },
        "scenes": [
            {
                "title": "Legacy Scene",
                "narration": "Narration text",
                "visual_prompt": "Prompt text",
            }
        ],
    }

    plan = backfill_plan(legacy_plan)
    meta = plan["meta"]
    scene = plan["scenes"][0]

    assert meta["pipeline_mode"] == "generic_slides_v1"
    assert meta["brief"]["source_material"] == "Legacy source text"
    assert meta["render_profile"]["aspect_ratio"] == "16:9"
    assert meta["tts_profile"]["provider"] == "kokoro"
    assert meta["video_profile"]["provider"] == "manual"
    assert scene["scene_type"] == "image"
    assert scene["on_screen_text"] == []
    assert scene["video_path"] is None
    assert scene["video_trim_start"] == 0.0
    assert scene["video_trim_end"] is None
    assert scene["video_playback_speed"] == 1.0
    assert scene["video_hold_last_frame"] is True


def test_render_profile_defaulting_preserves_partial_override():
    plan = backfill_plan(
        {
            "meta": {
                "project_name": "render_demo",
                "brief": {"source_material": "Text"},
                "render_profile": {"fps": 30},
            },
            "scenes": [],
        }
    )
    render_profile = plan["meta"]["render_profile"]

    assert render_profile["fps"] == 30
    assert render_profile["aspect_ratio"] == "16:9"
    assert render_profile["width"] == 1664
    assert render_profile["height"] == 928


def test_backfill_plan_preserves_video_scene_metadata():
    plan = backfill_plan(
        {
            "meta": {
                "project_name": "video_demo",
            },
            "scenes": [
                {
                    "title": "Demo clip",
                    "narration": "Walk through the live demo.",
                    "visual_prompt": "Use the moment where the dashboard alert flips on.",
                    "scene_type": "video",
                    "video_path": "/tmp/demo.mp4",
                    "video_trim_start": "3.5",
                    "video_trim_end": "14.0",
                    "video_playback_speed": "1.25",
                    "video_hold_last_frame": False,
                }
            ],
        }
    )

    scene = plan["scenes"][0]

    assert scene["scene_type"] == "video"
    assert scene["video_path"] == "/tmp/demo.mp4"
    assert scene["video_trim_start"] == 3.5
    assert scene["video_trim_end"] == 14.0
    assert scene["video_playback_speed"] == 1.25
    assert scene["video_hold_last_frame"] is False


def test_backfill_plan_adds_image_profile_defaults_and_compatibility():
    plan = backfill_plan(
        {
            "meta": {
                "project_name": "image_demo",
                "image_model": "custom/model",
            },
            "scenes": [],
        }
    )

    image_profile = plan["meta"]["image_profile"]

    assert image_profile["provider"] == "replicate"
    assert image_profile["generation_model"] == "custom/model"
    assert image_profile["edit_model"] == "qwen/qwen-image-edit-2511"
    assert plan["meta"]["image_model"] == "custom/model"


def test_backfill_plan_adds_video_profile_defaults_and_compatibility():
    plan = backfill_plan(
        {
            "meta": {
                "project_name": "video_profile_demo",
                "video_provider": "local",
                "video_model": "/models/wan",
            },
            "scenes": [],
        }
    )

    video_profile = plan["meta"]["video_profile"]

    assert video_profile["provider"] == "local"
    assert video_profile["generation_model"] == "/models/wan"
    assert plan["meta"]["video_model"] == "/models/wan"


def test_normalize_brief_preserves_visual_source_strategy_and_footage_notes():
    brief = normalize_brief(
        {
            "visual_source_strategy": "mixed_media",
            "available_footage": "Dashboard recording, onboarding flow, alert moment",
            "style_reference_summary": "Muted cinematic grade, premium editorial finish.",
            "style_reference_paths": ["/tmp/ref1.png", "", None, "/tmp/ref2.jpg"],
        }
    )

    assert brief["visual_source_strategy"] == "mixed_media"
    assert brief["available_footage"] == "Dashboard recording, onboarding flow, alert moment"
    assert brief["style_reference_summary"] == "Muted cinematic grade, premium editorial finish."
    assert brief["style_reference_paths"] == ["/tmp/ref1.png", "/tmp/ref2.jpg"]
