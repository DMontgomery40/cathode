from pathlib import Path

from core.project_schema import backfill_plan, infer_composition_mode, normalize_brief, scene_requires_remotion


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
    assert brief["video_scene_style"] == "auto"
    assert brief["text_render_mode"] == "visual_authored"
    assert brief["composition_mode"] == "auto"
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
    assert meta["render_profile"]["text_render_mode"] == "visual_authored"
    assert meta["tts_profile"]["provider"] == "kokoro"
    assert meta["video_profile"]["provider"] == "manual"
    assert scene["scene_type"] == "image"
    assert scene["on_screen_text"] == []
    assert scene["video_path"] is None
    assert scene["video_trim_start"] == 0.0
    assert scene["video_trim_end"] is None
    assert scene["video_playback_speed"] == 1.0
    assert scene["video_hold_last_frame"] is True
    assert scene["video_audio_source"] == "narration"
    assert "video_scene_kind" not in scene or scene["video_scene_kind"] is None
    assert meta["video_profile"]["quality_mode"] == "standard"
    assert meta["video_profile"]["generate_audio"] is True
    assert meta["video_profile"]["model_selection_mode"] == "automatic"


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
    assert render_profile["render_backend"] == "ffmpeg"
    assert "Classic image/video assembly" in render_profile["render_backend_reason"]


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
                    "video_scene_kind": "speaking",
                    "video_reference_image_path": "/tmp/reference.png",
                    "video_reference_audio_path": "/tmp/reference.wav",
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
    assert scene["video_audio_source"] == "narration"
    assert scene["video_scene_kind"] == "speaking"
    assert scene["video_reference_image_path"] == "/tmp/reference.png"
    assert scene["video_reference_audio_path"] == "/tmp/reference.wav"


def test_backfill_plan_keeps_video_scene_kind_open_for_auto_mode():
    plan = backfill_plan(
        {
            "meta": {"project_name": "video_auto_demo"},
            "scenes": [
                {
                    "title": "Auto clip",
                    "narration": "Keep the clip style open so automatic routing can decide.",
                    "visual_prompt": "A local business owner introduces the offer.",
                    "scene_type": "video",
                }
            ],
        }
    )

    scene = plan["scenes"][0]

    assert scene["scene_type"] == "video"
    assert scene["video_scene_kind"] is None


def test_backfill_plan_preserves_motion_scene_metadata():
    plan = backfill_plan(
        {
            "meta": {
                "project_name": "motion_demo",
                "brief": {
                    "project_name": "motion_demo",
                    "source_material": "Prompt stack demo",
                    "composition_mode": "motion_only",
                },
            },
            "scenes": [
                {
                    "title": "Prompt ladder",
                    "narration": "Show prompts calling prompts.",
                    "scene_type": "motion",
                    "motion": {
                        "template_id": "bullet_stack",
                        "props": {
                            "headline": "Prompts on prompts",
                            "bullets": ["One prompt", "Many agents", "Final render"],
                        },
                        "preview_path": "projects/motion_demo/previews/motion_scene.mp4",
                        "rationale": "Text-first beat",
                    },
                }
            ],
        }
    )

    scene = plan["scenes"][0]
    assert scene["scene_type"] == "motion"
    assert scene["composition"]["family"] == "bullet_stack"
    assert scene["composition"]["mode"] == "native"
    assert scene["motion"]["template_id"] == "bullet_stack"
    assert scene["motion"]["props"]["headline"] == "Prompts on prompts"
    assert scene["motion"]["props"]["bullets"] == ["One prompt", "Many agents", "Final render"]
    assert scene["motion"]["preview_path"] == "projects/motion_demo/previews/motion_scene.mp4"
    assert plan["meta"]["render_profile"]["render_backend"] == "remotion"
    assert plan["meta"]["render_profile"]["render_strategy"] == "auto"


def test_backfill_plan_preserves_thin_motion_directives():
    plan = backfill_plan(
        {
            "meta": {"project_name": "thin_motion_demo"},
            "scenes": [
                {
                    "title": "Ranked comparison",
                    "narration": "Show the top categories as a staged ranking.",
                    "visual_prompt": "Motion-first comparison beat.",
                    "scene_type": "motion",
                    "staging_notes": "camera rises from the lowest tier to the highest tier",
                    "transition_hint": "fade",
                    "data_points": ["#3 Services", "#2 Licensing", "#1 Production"],
                }
            ],
        }
    )

    scene = plan["scenes"][0]
    assert scene["staging_notes"] == "camera rises from the lowest tier to the highest tier"
    assert scene["transition_hint"] == "fade"
    assert scene["data_points"] == ["#3 Services", "#2 Licensing", "#1 Production"]
    assert scene["composition"]["family"] == "kinetic_title"


def test_infer_composition_mode_keeps_demo_context_image_first_without_mixed_media_request():
    mode = infer_composition_mode(
        {
            "project_name": "demo_run",
            "source_material": "Prompt notes",
        },
        agent_demo_profile={"workspace_path": "/tmp/workspace"},
    )

    assert mode == "classic"


def test_infer_composition_mode_treats_auto_as_image_first_without_mixed_media_request():
    mode = infer_composition_mode(
        {
            "project_name": "auto_demo",
            "source_material": "Prompt notes",
            "composition_mode": "auto",
        },
        agent_demo_profile={"workspace_path": "/tmp/workspace"},
    )

    assert mode == "classic"


def test_backfill_plan_heals_same_project_absolute_asset_paths(tmp_path):
    project_dir = tmp_path / "demo_project"
    images_dir = project_dir / "images"
    audio_dir = project_dir / "audio"
    previews_dir = project_dir / "previews"
    images_dir.mkdir(parents=True)
    audio_dir.mkdir(parents=True)
    previews_dir.mkdir(parents=True)
    image_path = images_dir / "scene_000.png"
    audio_path = audio_dir / "scene_000.wav"
    preview_path = previews_dir / "preview_scene_000.mp4"
    video_path = project_dir / "demo_project.mp4"
    for path in (image_path, audio_path, preview_path, video_path):
        path.write_bytes(b"demo")

    old_root = Path("/tmp/other_checkout/projects/demo_project")
    plan = backfill_plan(
        {
            "meta": {
                "project_name": "demo_project",
                "video_path": str(old_root / "demo_project.mp4"),
            },
            "scenes": [
                {
                    "image_path": str(old_root / "images" / "scene_000.png"),
                    "audio_path": str(old_root / "audio" / "scene_000.wav"),
                    "preview_path": str(old_root / "previews" / "preview_scene_000.mp4"),
                }
            ],
        },
        base_dir=project_dir,
    )

    scene = plan["scenes"][0]
    assert scene["image_path"] == str(image_path.resolve())
    assert scene["audio_path"] == str(audio_path.resolve())
    assert scene["preview_path"] == str(preview_path.resolve())
    assert plan["meta"]["video_path"] == str(video_path.resolve())


def test_backfill_plan_clears_unhealed_same_project_asset_paths(tmp_path):
    project_dir = tmp_path / "demo_project"
    project_dir.mkdir()
    old_root = Path("/tmp/other_checkout/projects/demo_project")

    plan = backfill_plan(
        {
            "meta": {
                "project_name": "demo_project",
                "video_path": str(old_root / "demo_project.mp4"),
            },
            "scenes": [
                {
                    "image_path": str(old_root / "images" / "scene_000.png"),
                    "audio_path": str(old_root / "audio" / "scene_000.wav"),
                    "preview_path": str(old_root / "previews" / "preview_scene_000.mp4"),
                }
            ],
        },
        base_dir=project_dir,
    )

    scene = plan["scenes"][0]
    assert scene["image_path"] is None
    assert scene["audio_path"] is None
    assert scene["preview_path"] is None
    assert plan["meta"]["video_path"] is None


def test_backfill_plan_clears_missing_absolute_paths_inside_project(tmp_path):
    project_dir = tmp_path / "demo_project"
    project_dir.mkdir()
    missing_image = project_dir / "images" / "scene_000.png"
    missing_audio = project_dir / "audio" / "scene_000.wav"
    missing_video = project_dir / "demo_project.mp4"

    plan = backfill_plan(
        {
            "meta": {
                "project_name": "demo_project",
                "video_path": str(missing_video),
            },
            "scenes": [
                {
                    "image_path": str(missing_image),
                    "audio_path": str(missing_audio),
                }
            ],
        },
        base_dir=project_dir,
    )

    scene = plan["scenes"][0]
    assert scene["image_path"] is None
    assert scene["audio_path"] is None
    assert plan["meta"]["video_path"] is None


def test_backfill_plan_preserves_motion_scene_metadata():
    plan = backfill_plan(
        {
            "meta": {
                "project_name": "motion_demo",
                "brief": {
                    "project_name": "motion_demo",
                    "source_material": "Prompt stack demo",
                    "composition_mode": "motion_only",
                },
            },
            "scenes": [
                {
                    "title": "Prompt ladder",
                    "narration": "Show prompts calling prompts.",
                    "scene_type": "motion",
                    "motion": {
                        "template_id": "bullet_stack",
                        "props": {
                            "headline": "Prompts on prompts",
                            "bullets": ["One prompt", "Many agents", "Final render"],
                        },
                        "preview_path": "projects/motion_demo/previews/motion_scene.mp4",
                        "rationale": "Text-first beat",
                    },
                }
            ],
        }
    )

    scene = plan["scenes"][0]
    assert scene["scene_type"] == "motion"
    assert scene["motion"]["template_id"] == "bullet_stack"
    assert scene["motion"]["props"]["headline"] == "Prompts on prompts"
    assert scene["motion"]["props"]["bullets"] == ["One prompt", "Many agents", "Final render"]
    assert scene["motion"]["preview_path"] == "projects/motion_demo/previews/motion_scene.mp4"
    assert plan["meta"]["render_profile"]["render_backend"] == "remotion"


def test_infer_composition_mode_defaults_to_classic_for_demo_context_without_mixed_media_request():
    mode = infer_composition_mode(
        {
            "project_name": "demo_run",
            "source_material": "Prompt notes",
        },
        agent_demo_profile={"workspace_path": "/tmp/workspace"},
    )

    assert mode == "classic"


def test_backfill_plan_heals_same_project_absolute_asset_paths(tmp_path):
    project_dir = tmp_path / "demo_project"
    images_dir = project_dir / "images"
    audio_dir = project_dir / "audio"
    previews_dir = project_dir / "previews"
    images_dir.mkdir(parents=True)
    audio_dir.mkdir(parents=True)
    previews_dir.mkdir(parents=True)
    image_path = images_dir / "scene_000.png"
    audio_path = audio_dir / "scene_000.wav"
    preview_path = previews_dir / "preview_scene_000.mp4"
    video_path = project_dir / "demo_project.mp4"
    for path in (image_path, audio_path, preview_path, video_path):
        path.write_bytes(b"demo")

    old_root = Path("/tmp/other_checkout/projects/demo_project")
    plan = backfill_plan(
        {
            "meta": {
                "project_name": "demo_project",
                "video_path": str(old_root / "demo_project.mp4"),
            },
            "scenes": [
                {
                    "image_path": str(old_root / "images" / "scene_000.png"),
                    "audio_path": str(old_root / "audio" / "scene_000.wav"),
                    "preview_path": str(old_root / "previews" / "preview_scene_000.mp4"),
                }
            ],
        },
        base_dir=project_dir,
    )

    scene = plan["scenes"][0]
    assert scene["image_path"] == str(image_path.resolve())
    assert scene["audio_path"] == str(audio_path.resolve())
    assert scene["preview_path"] == str(preview_path.resolve())
    assert plan["meta"]["video_path"] == str(video_path.resolve())


def test_backfill_plan_clears_unhealed_same_project_asset_paths(tmp_path):
    project_dir = tmp_path / "demo_project"
    project_dir.mkdir()
    old_root = Path("/tmp/other_checkout/projects/demo_project")

    plan = backfill_plan(
        {
            "meta": {
                "project_name": "demo_project",
                "video_path": str(old_root / "demo_project.mp4"),
            },
            "scenes": [
                {
                    "image_path": str(old_root / "images" / "scene_000.png"),
                    "audio_path": str(old_root / "audio" / "scene_000.wav"),
                    "preview_path": str(old_root / "previews" / "preview_scene_000.mp4"),
                }
            ],
        },
        base_dir=project_dir,
    )

    scene = plan["scenes"][0]
    assert scene["image_path"] is None
    assert scene["audio_path"] is None
    assert scene["preview_path"] is None
    assert plan["meta"]["video_path"] is None


def test_backfill_plan_clears_missing_absolute_paths_inside_project(tmp_path):
    project_dir = tmp_path / "demo_project"
    project_dir.mkdir()
    missing_image = project_dir / "images" / "scene_000.png"
    missing_audio = project_dir / "audio" / "scene_000.wav"
    missing_video = project_dir / "demo_project.mp4"

    plan = backfill_plan(
        {
            "meta": {
                "project_name": "demo_project",
                "video_path": str(missing_video),
            },
            "scenes": [
                {
                    "image_path": str(missing_image),
                    "audio_path": str(missing_audio),
                }
            ],
        },
        base_dir=project_dir,
    )

    scene = plan["scenes"][0]
    assert scene["image_path"] is None
    assert scene["audio_path"] is None
    assert plan["meta"]["video_path"] is None


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

    assert image_profile["provider"] == "codex"
    assert image_profile["generation_model"] == "custom/model"
    assert image_profile["edit_model"] == "gpt-image-2"
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
    assert video_profile["model_selection_mode"] == "automatic"
    assert video_profile["quality_mode"] == "standard"
    assert video_profile["generate_audio"] is True
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


def test_backfill_plan_preserves_scene_tts_override_metadata():
    plan = backfill_plan(
        {
            "meta": {"project_name": "voice_demo"},
            "scenes": [
                {
                    "title": "Cold Open",
                    "narration": "Hello there.",
                    "visual_prompt": "Simple frame.",
                    "tts_override_enabled": True,
                    "tts_provider": "elevenlabs",
                    "tts_voice": "Bella",
                    "tts_speed": "0.95",
                    "elevenlabs_model_id": "eleven_multilingual_v2",
                    "elevenlabs_text_normalization": "auto",
                    "elevenlabs_stability": "0.42",
                    "elevenlabs_similarity_boost": "0.88",
                    "elevenlabs_style": "0.61",
                    "elevenlabs_use_speaker_boost": False,
                }
            ],
        }
    )

    scene = plan["scenes"][0]
    assert scene["tts_override_enabled"] is True
    assert scene["tts_provider"] == "elevenlabs"
    assert scene["tts_voice"] == "Bella"
    assert scene["tts_speed"] == 0.95
    assert scene["elevenlabs_model_id"] == "eleven_multilingual_v2"
    assert scene["elevenlabs_text_normalization"] == "auto"
    assert scene["elevenlabs_stability"] == 0.42
    assert scene["elevenlabs_similarity_boost"] == 0.88
    assert scene["elevenlabs_style"] == 0.61
    assert scene["elevenlabs_use_speaker_boost"] is False


def test_scene_requires_remotion_for_overlay_and_native_composition():
    assert scene_requires_remotion(
        {"scene_type": "image", "composition": {"family": "media_pan", "mode": "overlay"}}
    ) is True
    assert scene_requires_remotion(
        {"scene_type": "motion", "composition": {"family": "kinetic_title", "mode": "native"}}
    ) is True
    assert scene_requires_remotion(
        {"scene_type": "image", "composition": {"family": "static_media", "mode": "none"}}
    ) is False


# ── Clinical template families: schema integration ──

CLINICAL_TEMPLATE_FAMILIES = [
    "cover_hook",
    "orientation",
    "synthesis_summary",
    "closing_cta",
    "clinical_explanation",
    "metric_improvement",
    "brain_region_focus",
    "metric_comparison",
    "timeline_progression",
    "analogy_metaphor",
]


def test_scene_requires_remotion_for_all_clinical_template_families():
    """Every clinical template family with mode=native requires the Remotion render backend."""
    for family in CLINICAL_TEMPLATE_FAMILIES:
        result = scene_requires_remotion(
            {"scene_type": "motion", "composition": {"family": family, "mode": "native"}}
        )
        assert result is True, f"{family} with mode=native should require Remotion"


def test_backfill_plan_preserves_clinical_template_composition_props():
    """Clinical template scenes survive plan normalization with family, mode, and rich props intact."""
    plan = backfill_plan(
        {
            "meta": {
                "project_name": "clinical_demo",
                "brief": {
                    "project_name": "clinical_demo",
                    "source_material": "Clinical explainer demo",
                    "composition_mode": "motion_only",
                },
            },
            "scenes": [
                {
                    "title": "Cover",
                    "narration": "Welcome to your brain map.",
                    "visual_prompt": "Warm clinical background.",
                    "scene_type": "motion",
                    "composition": {
                        "family": "cover_hook",
                        "mode": "native",
                        "props": {
                            "headline": "Your Brain Map",
                            "subtitle": "A personalized look at your neural landscape",
                            "kicker": "Session 3 of 10",
                        },
                    },
                },
                {
                    "title": "Metric Change",
                    "narration": "Alpha power improved by 18 percent.",
                    "visual_prompt": "Before/after comparison.",
                    "scene_type": "motion",
                    "composition": {
                        "family": "metric_improvement",
                        "mode": "native",
                        "props": {
                            "headline": "Alpha Power",
                            "metric_name": "Fz Alpha (8-12 Hz)",
                            "before": {"value": "4.2 uV", "label": "Session 1"},
                            "after": {"value": "6.1 uV", "label": "Session 3"},
                            "delta": "+45%",
                            "direction": "improvement",
                            "caption": "Consistent upward trend",
                        },
                    },
                },
                {
                    "title": "Brain Focus",
                    "narration": "Frontal and temporal regions show improvement.",
                    "visual_prompt": "Brain diagram.",
                    "scene_type": "motion",
                    "composition": {
                        "family": "brain_region_focus",
                        "mode": "native",
                        "props": {
                            "headline": "Regional Activity",
                            "regions": [
                                {"name": "Frontal", "value": "+18%", "status": "improved"},
                                {"name": "Temporal", "value": "+12%", "status": "improved"},
                                {"name": "Parietal", "value": "-2%", "status": "stable"},
                            ],
                            "caption": "Three regions tracked",
                        },
                    },
                },
                {
                    "title": "Timeline",
                    "narration": "Showing progress over the treatment window.",
                    "visual_prompt": "Timeline track.",
                    "scene_type": "motion",
                    "composition": {
                        "family": "timeline_progression",
                        "mode": "native",
                        "props": {
                            "headline": "Treatment Window",
                            "span_label": "6-month protocol",
                            "markers": [
                                {"label": "Intake", "date": "Jan", "annotation": "Baseline", "status": "completed"},
                                {"label": "Mid-point", "date": "Apr", "annotation": "Check-in", "status": "current"},
                            ],
                            "caption": "On track",
                        },
                    },
                },
            ],
        }
    )

    # All scenes should survive normalization
    assert len(plan["scenes"]) == 4

    # Cover hook
    cover = plan["scenes"][0]
    assert cover["scene_type"] == "motion"
    assert cover["composition"]["family"] == "cover_hook"
    assert cover["composition"]["mode"] == "native"
    assert cover["composition"]["props"]["headline"] == "Your Brain Map"
    assert cover["composition"]["props"]["subtitle"] == "A personalized look at your neural landscape"
    assert cover["composition"]["props"]["kicker"] == "Session 3 of 10"

    # Metric improvement -- nested before/after objects
    metric = plan["scenes"][1]
    assert metric["composition"]["family"] == "metric_improvement"
    assert metric["composition"]["props"]["before"]["value"] == "4.2 uV"
    assert metric["composition"]["props"]["after"]["label"] == "Session 3"
    assert metric["composition"]["props"]["delta"] == "+45%"
    assert metric["composition"]["props"]["direction"] == "improvement"

    # Brain region focus -- regions array
    brain = plan["scenes"][2]
    assert brain["composition"]["family"] == "brain_region_focus"
    assert len(brain["composition"]["props"]["regions"]) == 3
    assert brain["composition"]["props"]["regions"][0]["name"] == "Frontal"
    assert brain["composition"]["props"]["regions"][2]["status"] == "stable"

    # Timeline progression -- markers array
    timeline = plan["scenes"][3]
    assert timeline["composition"]["family"] == "timeline_progression"
    assert timeline["composition"]["props"]["span_label"] == "6-month protocol"
    assert len(timeline["composition"]["props"]["markers"]) == 2
    assert timeline["composition"]["props"]["markers"][0]["label"] == "Intake"

    # Remotion backend should be auto-selected
    assert plan["meta"]["render_profile"]["render_backend"] == "remotion"


def test_backfill_plan_keeps_auto_backend_ffmpeg_for_overlay_metadata():
    plan = backfill_plan(
        {
            "meta": {
                "project_name": "overlay_demo",
                "brief": {"source_material": "Explain the dashboard."},
                "render_profile": {"render_strategy": "auto"},
            },
            "scenes": [
                {
                    "title": "Overlay beat",
                    "narration": "Highlight the KPI stack.",
                    "visual_prompt": "Dashboard still.",
                    "scene_type": "image",
                    "composition": {
                        "family": "software_demo_focus",
                        "mode": "overlay",
                        "props": {"headline": "Revenue up"},
                    },
                }
            ],
        }
    )

    assert plan["meta"]["render_profile"]["render_backend"] == "ffmpeg"
    assert "overlay metadata" in plan["meta"]["render_profile"]["render_backend_reason"]


def test_normalize_brief_preserves_visual_source_strategy_and_footage_notes():
    brief = normalize_brief(
        {
            "visual_source_strategy": "mixed_media",
            "text_render_mode": "deterministic_overlay",
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
    assert brief["text_render_mode"] == "deterministic_overlay"
    assert brief["available_footage"] == "Dashboard recording, onboarding flow, alert moment"
    assert brief["footage_manifest"][0]["id"] == "hero_capture"
    assert brief["footage_manifest"][0]["review_status"] == "warn"
    assert brief["style_reference_summary"] == "Muted cinematic grade, premium editorial finish."
    assert brief["style_reference_paths"] == [
        str(Path("/tmp/ref1.png").resolve()),
        str(Path("/tmp/ref2.jpg").resolve()),
    ]


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
