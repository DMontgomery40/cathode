from __future__ import annotations

from pathlib import Path

from core.pipeline_service import create_project_from_brief_service


def test_create_project_from_brief_service_copies_and_assigns_reviewed_footage(monkeypatch, tmp_path):
    source_clip = tmp_path / "fresh_capture.mp4"
    source_clip.write_bytes(b"demo")
    project_dir = tmp_path / "demo_project"

    monkeypatch.setattr("core.pipeline_service.choose_llm_provider", lambda provider=None: provider or "openai")
    monkeypatch.setattr(
        "core.pipeline_service.create_plan_from_brief",
        lambda **kwargs: {
            "meta": {
                "project_name": kwargs["project_name"],
                "brief": kwargs["brief"],
                "llm_provider": kwargs["provider"],
                "render_profile": kwargs["render_profile"] or {},
                "tts_profile": kwargs["tts_profile"] or {},
                "image_profile": kwargs["image_profile"] or {},
                "video_profile": kwargs["video_profile"] or {},
            },
            "scenes": [
                {
                    "id": 0,
                    "title": "Run Review",
                    "narration": "Show the saved review state.",
                    "visual_prompt": "Play the captured overlay clip.",
                    "scene_type": "video",
                    "footage_asset_id": "hero_capture",
                }
            ],
        },
    )

    _, plan = create_project_from_brief_service(
        project_name="demo_project",
        project_dir=project_dir,
        brief={
            "project_name": "demo_project",
            "source_mode": "source_text",
            "video_goal": "Demo the reviewed product flow",
            "audience": "Technical buyers",
            "source_material": "Product notes.",
            "visual_source_strategy": "mixed_media",
            "footage_manifest": [
                {
                    "id": "hero_capture",
                    "path": str(source_clip),
                    "label": "Run review overlay",
                    "notes": "Fresh capture from a live app.",
                    "review_status": "accept",
                }
            ],
        },
        provider="openai",
    )

    copied_entry = plan["meta"]["footage_manifest"][0]
    assert copied_entry["path"].endswith("clips/hero_capture.mp4")
    assert Path(copied_entry["path"]).exists()
    assert plan["scenes"][0]["video_path"] == copied_entry["path"]
    assert "Run review overlay" in plan["meta"]["brief"]["available_footage"]


def test_create_project_from_brief_service_recomputes_available_footage_after_missing_clips_drop(
    monkeypatch,
    tmp_path,
):
    source_clip = tmp_path / "fresh_capture.mp4"
    source_clip.write_bytes(b"demo")
    project_dir = tmp_path / "demo_project"

    monkeypatch.setattr("core.pipeline_service.choose_llm_provider", lambda provider=None: provider or "openai")
    monkeypatch.setattr(
        "core.pipeline_service.create_plan_from_brief",
        lambda **kwargs: {
            "meta": {
                "project_name": kwargs["project_name"],
                "brief": kwargs["brief"],
                "llm_provider": kwargs["provider"],
                "render_profile": kwargs["render_profile"] or {},
                "tts_profile": kwargs["tts_profile"] or {},
                "image_profile": kwargs["image_profile"] or {},
                "video_profile": kwargs["video_profile"] or {},
            },
            "scenes": [],
        },
    )

    _, plan = create_project_from_brief_service(
        project_name="demo_project",
        project_dir=project_dir,
        brief={
            "project_name": "demo_project",
            "source_mode": "source_text",
            "video_goal": "Demo the reviewed product flow",
            "audience": "Technical buyers",
            "source_material": "Product notes.",
            "visual_source_strategy": "mixed_media",
            "available_footage": "Fresh capture and a missing clip",
            "footage_manifest": [
                {
                    "id": "hero_capture",
                    "path": str(source_clip),
                    "label": "Run review overlay",
                    "notes": "Fresh capture from a live app.",
                    "review_status": "accept",
                },
                {
                    "id": "missing_capture",
                    "path": str(tmp_path / "missing.mp4"),
                    "label": "Missing clip",
                    "notes": "Should not survive persistence.",
                    "review_status": "accept",
                },
            ],
        },
        provider="openai",
    )

    assert "Run review overlay" in plan["meta"]["brief"]["available_footage"]
    assert "Missing clip" not in plan["meta"]["brief"]["available_footage"]
