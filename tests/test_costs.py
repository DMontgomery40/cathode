from core.costs import (
    COST_CATALOG_VERSION,
    estimate_plan_cost,
    frontend_cost_catalog,
    image_edit_entry,
    llm_actual_entry,
    summarize_cost_entries,
)


def test_frontend_cost_catalog_exposes_versioned_entries():
    catalog = frontend_cost_catalog()

    assert catalog["version"] == COST_CATALOG_VERSION
    assert any(entry["model"] == "gpt-5.4" for entry in catalog["entries"])
    assert any(entry["model"] == "qwen/qwen-image-2512" for entry in catalog["entries"])
    assert any(entry["model"] == "kwaivgi/kling-v3-video" for entry in catalog["entries"])


def test_estimate_plan_cost_is_route_aware_and_budget_gated():
    plan = {
        "meta": {
            "brief": {
                "paid_media_budget_usd": "0.50",
                "source_material": "demo",
            },
            "image_profile": {"provider": "replicate", "generation_model": "qwen/qwen-image-2512"},
            "video_profile": {
                "provider": "replicate",
                "generation_model": "",
                "model_selection_mode": "automatic",
                "quality_mode": "standard",
                "generate_audio": True,
            },
            "tts_profile": {"provider": "openai", "model_id": "tts-1", "voice": "nova"},
        },
        "scenes": [
            {
                "id": 0,
                "uid": "scene_a",
                "title": "Image scene",
                "scene_type": "image",
                "narration": "Short narration for the still image.",
            },
            {
                "id": 1,
                "uid": "scene_b",
                "title": "Speaking scene",
                "scene_type": "video",
                "narration": "A spokesperson explains the offer directly to camera.",
            },
            {
                "id": 2,
                "uid": "scene_c",
                "title": "Cinematic scene",
                "scene_type": "video",
                "video_scene_kind": "cinematic",
                "narration": "A longer cinematic beat with movement and atmosphere.",
            },
        ],
    }

    estimate = estimate_plan_cost(plan)
    entries = estimate["entries"]

    speaking = next(entry for entry in entries if entry.get("scene_uid") == "scene_b" and entry["kind"] == "video_generation")
    cinematic = next(entry for entry in entries if entry.get("scene_uid") == "scene_c" and entry["kind"] == "video_generation")

    assert speaking["model"] == "kwaivgi/kling-avatar-v2"
    assert cinematic["model"] == "kwaivgi/kling-v3-video"
    assert speaking["total_usd"] != cinematic["total_usd"]
    assert estimate["status"] == "over_budget"


def test_image_edit_entry_distinguishes_replicate_and_dashscope_models():
    scene = {"id": 1, "uid": "scene_1", "title": "Edit me"}

    replicate_entry = image_edit_entry(
        scene=scene,
        provider="replicate",
        model="qwen/qwen-image-edit-2511",
        estimated=False,
        operation="scene_image_edit",
    )
    dashscope_entry = image_edit_entry(
        scene=scene,
        provider="dashscope",
        model="qwen-image-edit-plus",
        estimated=False,
        operation="scene_image_edit",
    )

    assert replicate_entry is not None
    assert dashscope_entry is not None
    assert replicate_entry["total_usd"] != dashscope_entry["total_usd"]


def test_llm_entries_are_tracked_but_do_not_count_toward_gating_total():
    entry = llm_actual_entry(
        provider="anthropic",
        model="claude-sonnet-4-6",
        operation="storyboard",
        input_tokens=2000,
        output_tokens=1000,
    )
    summary = summarize_cost_entries([entry] if entry else [])

    assert summary["llm_total_usd"] > 0
    assert summary["gating_total_usd"] == 0
