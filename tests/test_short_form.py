from core.short_form import build_short_form_payload, short_form_options
from core.intake import build_brief_from_intent
from core.pipeline_service import prepare_project_execution_profiles
from core.project_schema import backfill_plan


def test_short_form_options_expose_strategy_options():
    options = short_form_options()

    assert options["defaults"]["approach"] == "public-reframe"
    assert options["defaults"]["render_profile"]["aspect_ratio"] == "9:16"
    assert {item["value"] for item in options["approaches"]} == {
        "public-reframe",
        "mixed-media-proof",
        "source-cutdown",
    }


def test_short_form_payload_encodes_vertical_pipeline_contract():
    payload = build_short_form_payload(
        {
            "project_name": "AI Agent Demo!",
            "source_material": "A longer product demo about agent teams.",
            "hook_promise": "This is what agent teams look like when they stop being slides.",
            "payoff": "The viewer sees a real workflow handoff.",
            "short_form_tier": "dev_native_credible",
            "approach": "mixed_media_proof",
            "caption_strategy": "meaning_card_captions",
            "runtime_seconds": 48,
            "subject": "betTube Studio",
            "domain": "AI tooling",
            "evidence_boundary": "Prototype workflow evidence, not autonomous publishing proof.",
            "run_until": "assets",
        }
    )

    brief = payload["brief"]
    render_profile = payload["render_profile"]

    assert payload["project_name"] == "AI_Agent_Demo_"
    assert payload["run_until"] == "assets"
    assert brief["short_form_format"] == "vertical_short"
    assert brief["short_form_tier"] == "dev-native-credible"
    assert brief["short_form_approach"] == "mixed-media-proof"
    assert "Platform targets: TikTok, Instagram Reels, YouTube Shorts." in brief["video_goal"]
    assert brief["target_length_minutes"] == 0.8
    assert "Subject: betTube Studio" in brief["source_anchor_card"]
    assert "Prototype workflow evidence" in brief["source_context_lock"]
    assert "3-5 short-form beats" in brief["must_include"]
    assert "Current-word captions without accurate word timing" in brief["must_avoid"]
    assert render_profile["aspect_ratio"] == "9:16"
    assert render_profile["width"] == 928
    assert render_profile["height"] == 1664
    assert render_profile["render_strategy"] == "force_ffmpeg"
    assert payload["tts_profile"]["speed"] == 1.0
    assert payload["preview"]["frame"] == "9:16 928x1664 @ 30fps"
    assert payload["preview"]["source_role"].startswith("Source footage supplies proof moments")


def test_short_form_payload_uses_openai_voice_when_available(monkeypatch):
    monkeypatch.setattr(
        "core.short_form.available_tts_providers",
        lambda: {
            "kokoro": "Kokoro (Local)",
            "openai": "OpenAI TTS (Cloud)",
        },
    )
    monkeypatch.setenv("BETTUBE_STUDIO_OPENAI_TTS_VOICE", "nova")
    monkeypatch.setenv("BETTUBE_STUDIO_OPENAI_TTS_MODEL", "tts-1")

    payload = build_short_form_payload(
        {
            "project_name": "openai_voice_short",
            "source_material": "Source notes.",
        }
    )

    assert payload["tts_profile"] == {
        "provider": "openai",
        "voice": "nova",
        "model_id": "tts-1",
        "speed": 1.0,
    }


def test_short_form_payload_repairs_unsupported_tts_1_voice(monkeypatch):
    monkeypatch.setattr(
        "core.short_form.available_tts_providers",
        lambda: {
            "kokoro": "Kokoro (Local)",
            "openai": "OpenAI TTS (Cloud)",
        },
    )
    monkeypatch.setenv("BETTUBE_STUDIO_OPENAI_TTS_VOICE", "marin")
    monkeypatch.setenv("BETTUBE_STUDIO_OPENAI_TTS_MODEL", "tts-1")

    payload = build_short_form_payload(
        {
            "project_name": "openai_voice_short",
            "source_material": "Source notes.",
        }
    )

    assert payload["tts_profile"]["voice"] == "alloy"
    assert payload["tts_profile"]["model_id"] == "tts-1"


def test_short_form_payload_clamps_runtime_and_defaults_platforms():
    payload = build_short_form_payload(
        {
            "project_name": "too_long",
            "runtime_seconds": 120,
            "platform_targets": ["unknown"],
        }
    )

    assert payload["runtime_seconds"] == 50.0
    assert payload["brief"]["platform_targets"] == ["tiktok", "instagram-reels", "youtube-shorts"]


def test_short_form_brief_infers_vertical_profiles_for_standard_make_video_path():
    payload = build_short_form_payload(
        {
            "project_name": "brief_mode_short",
            "source_material": "Source notes.",
        }
    )

    plan = backfill_plan({"meta": {"project_name": "brief_mode_short", "brief": payload["brief"]}, "scenes": []})
    brief = plan["meta"]["brief"]
    render_profile = plan["meta"]["render_profile"]

    assert brief["short_form_format"] == "vertical_short"
    assert plan["meta"]["pipeline_mode"] == "short_form_vertical_v1"
    assert plan["meta"]["video_profile"]["provider"] == "manual"
    assert render_profile["aspect_ratio"] == "9:16"
    assert render_profile["width"] == 928
    assert render_profile["height"] == 1664
    assert render_profile["render_strategy"] == "force_ffmpeg"


def test_short_form_execution_profiles_override_stale_landscape_render_profile():
    payload = build_short_form_payload(
        {
            "project_name": "brief_mode_short",
            "source_material": "Source notes.",
        }
    )

    _brief, _video_profile, render_profile = prepare_project_execution_profiles(
        brief=payload["brief"],
        render_profile={
            "aspect_ratio": "16:9",
            "width": 1664,
            "height": 928,
            "fps": 24,
            "render_strategy": "auto",
        },
    )

    assert render_profile["aspect_ratio"] == "9:16"
    assert render_profile["width"] == 928
    assert render_profile["height"] == 1664
    assert render_profile["fps"] == 30
    assert render_profile["render_strategy"] == "force_ffmpeg"


def test_short_form_execution_profiles_repair_partial_vertical_render_profile():
    payload = build_short_form_payload(
        {
            "project_name": "partial_vertical_short",
            "source_material": "Source notes.",
        }
    )

    _brief, _video_profile, render_profile = prepare_project_execution_profiles(
        brief=payload["brief"],
        render_profile={
            "aspect_ratio": "9:16",
            "width": 1664,
            "height": 928,
            "fps": 24,
            "render_strategy": "auto",
        },
    )

    assert render_profile["aspect_ratio"] == "9:16"
    assert render_profile["width"] == 928
    assert render_profile["height"] == 1664
    assert render_profile["fps"] == 30
    assert render_profile["render_strategy"] == "force_ffmpeg"


def test_intake_preserves_short_form_overrides_for_mcp_make_video_path():
    brief, _metadata = build_brief_from_intent(
        intent="Make a vertical short from this demo.",
        source_text="A source demo about agent teams handing off work.",
        brief_overrides={
            "short_form_format": "vertical_short",
            "short_form_tier": "dev-native-credible",
            "short_form_approach": "mixed-media-proof",
            "short_form_duration_seconds": 45,
            "platform_targets": ["tiktok", "youtube_shorts"],
            "hook_promise": "The handoff is the product.",
            "payoff": "The viewer sees the workflow reach render.",
            "source_anchor_card": "Subject: betTube Studio\nDomain: AI video tooling",
            "caption_strategy": "meaning-card-captions",
        },
    )

    assert brief["short_form_format"] == "vertical_short"
    assert brief["short_form_tier"] == "dev-native-credible"
    assert brief["short_form_approach"] == "mixed-media-proof"
    assert brief["short_form_duration_seconds"] == 45.0
    assert brief["target_length_minutes"] == 0.75
    assert brief["platform_targets"] == ["tiktok", "youtube-shorts"]
    assert brief["visual_source_strategy"] == "mixed_media"
    assert brief["caption_strategy"] == "meaning-card-captions"


def test_intake_short_form_without_duration_uses_short_default_not_standard_length():
    brief, _metadata = build_brief_from_intent(
        intent="Make a vertical short from this demo.",
        source_text="A source demo about agent teams handing off work.",
        brief_overrides={"short_form_format": "vertical_short"},
    )

    assert brief["short_form_duration_seconds"] == 42.0
    assert brief["target_length_minutes"] == 0.7
