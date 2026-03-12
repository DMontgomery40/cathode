from __future__ import annotations

from pathlib import Path

from core.intake import (
    BriefElicitationInput,
    build_brief_from_intent,
    merge_elicitation_into_brief,
    missing_brief_fields,
)


def test_build_brief_from_intent_uses_workspace_context(tmp_path):
    (tmp_path / "README.md").write_text("# Demo Project\n\nThis app helps founders create launch videos.\n")
    (tmp_path / "package.json").write_text('{"name":"demo-app","description":"A product demo app"}\n')
    (tmp_path / ".env").write_text("SECRET=should-not-be-read\n")

    brief, metadata = build_brief_from_intent(
        intent="Make a launch video for the product",
        workspace_path=tmp_path,
    )

    assert brief["video_goal"] == "Make a launch video for the product"
    assert brief["source_mode"] == "source_text"
    assert "README.md" in brief["source_material"]
    assert ".env" not in brief["source_material"]
    assert metadata["workspace_context"]["files"]
    assert missing_brief_fields(brief) == ["audience"]


def test_merge_elicitation_into_brief_fills_missing_fields():
    brief, _ = build_brief_from_intent(intent="Make a demo video", source_text="Feature notes and pricing.")

    merged = merge_elicitation_into_brief(
        brief,
        BriefElicitationInput(
            audience="YC partners",
            source_material="Feature notes and pricing.",
            target_length_minutes=1.5,
            visual_style="clean editorial product demo",
        ),
    )

    assert merged["audience"] == "YC partners"
    assert merged["target_length_minutes"] == 1.5
    assert merged["visual_style"] == "clean editorial product demo"
    assert missing_brief_fields(merged) == []


def test_build_brief_from_intent_promotes_footage_inputs_into_manifest(tmp_path):
    clip_path = tmp_path / "fresh_capture.mp4"
    clip_path.write_bytes(b"demo")

    brief, metadata = build_brief_from_intent(
        intent="Make a live demo video",
        source_text="Product notes.",
        footage_paths=[clip_path],
    )

    assert brief["footage_manifest"][0]["label"] == "fresh capture"
    assert brief["footage_manifest"][0]["path"] == str(clip_path.resolve())
    assert "fresh capture" in brief["available_footage"]
    assert metadata["footage_manifest"][0]["id"] == brief["footage_manifest"][0]["id"]
