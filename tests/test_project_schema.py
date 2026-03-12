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


def test_backfill_plan_accepts_local_image_provider():
    plan = backfill_plan(
        {
            "meta": {
                "project_name": "local_image_demo",
                "image_provider": "local",
                "image_model": "Qwen/Qwen-Image-2512",
            },
            "scenes": [],
        }
    )

    image_profile = plan["meta"]["image_profile"]

    assert image_profile["provider"] == "local"
    assert image_profile["generation_model"] == "Qwen/Qwen-Image-2512"


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


def test_normalize_scene_strips_inline_speaker_label_into_metadata():
    plan = backfill_plan(
        {
            "meta": {"project_name": "speaker_demo"},
            "scenes": [
                {
                    "title": "Cold Open",
                    "narration": "NARRATOR (V.O.): Six billion. That's how many requests hit the servers every day.",
                    "visual_prompt": "Dark screen with a single number.",
                }
            ],
        }
    )

    scene = plan["scenes"][0]
    assert scene["speaker_name"] == "Narrator"
    assert scene["narration"].startswith("Six billion.")


def test_normalize_brief_preserves_visual_source_strategy_and_footage_notes():
    brief = normalize_brief(
        {
            "visual_source_strategy": "mixed_media",
            "available_footage": "Dashboard recording, onboarding flow, alert moment",
            "footage_manifest": [
                {
                    "id": "hero_capture",
                    "path": "/tmp/hero.mp4",
                    "label": "Hero capture",
                    "review_status": "warn",
                    "review_summary": "Good frame, but weak state.",
                }
            ],
            "style_reference_summary": "Muted cinematic grade, premium editorial finish.",
            "style_reference_paths": ["/tmp/ref1.png", "", None, "/tmp/ref2.jpg"],
        }
    )

    assert brief["visual_source_strategy"] == "mixed_media"
    assert brief["available_footage"] == "Dashboard recording, onboarding flow, alert moment"
    assert brief["footage_manifest"][0]["id"] == "hero_capture"
    assert brief["footage_manifest"][0]["review_status"] == "warn"
    assert brief["style_reference_summary"] == "Muted cinematic grade, premium editorial finish."
    assert brief["style_reference_paths"] == ["/tmp/ref1.png", "/tmp/ref2.jpg"]


def test_normalize_brief_resolves_relative_footage_paths_from_base_dir(tmp_path):
    captures_dir = tmp_path / "captures"
    captures_dir.mkdir()
    clip_path = captures_dir / "hero.mp4"
    clip_path.write_bytes(b"demo")

    brief = normalize_brief(
        {
            "footage_manifest": [
                {
                    "id": "hero",
                    "path": "captures/hero.mp4",
                    "label": "Hero clip",
                }
            ]
        },
        base_dir=tmp_path,
    )

    assert brief["footage_manifest"][0]["path"] == str(clip_path.resolve())


def test_backfill_plan_resolves_relative_footage_paths_against_project_dir(tmp_path):
    project_dir = tmp_path / "demo_project"
    clips_dir = project_dir / "clips"
    clips_dir.mkdir(parents=True)
    clip_path = clips_dir / "hero.mp4"
    clip_path.write_bytes(b"demo")

    plan = backfill_plan(
        {
            "meta": {
                "project_name": "demo_project",
                "brief": {
                    "source_material": "Text",
                    "footage_manifest": [
                        {
                            "id": "hero",
                            "path": "clips/hero.mp4",
                            "label": "Hero clip",
                        }
                    ],
                },
            },
            "scenes": [],
        },
        base_dir=project_dir,
    )

    assert plan["meta"]["brief"]["footage_manifest"][0]["path"] == str(clip_path.resolve())


def test_normalize_scene_keeps_heading_prefixes_as_narration_text():
    plan = backfill_plan(
        {
            "meta": {"project_name": "heading_demo"},
            "scenes": [
                {
                    "title": "Overview",
                    "narration": "Overview: the pipeline starts locally.",
                    "visual_prompt": "Simple timeline.",
                }
            ],
        }
    )

    scene = plan["scenes"][0]
    assert "speaker_name" not in scene
    assert scene["narration"] == "Overview: the pipeline starts locally."
