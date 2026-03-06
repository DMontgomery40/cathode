import base64

from core.director import _build_storyboard_user_prompt_from_brief, analyze_style_references
from core.project_schema import normalize_brief


def test_director_prompt_includes_source_mode_behavior_and_brief_payload():
    brief = normalize_brief(
        {
            "project_name": "demo",
            "source_mode": "final_script",
            "video_goal": "Explain the product launch",
            "audience": "Sales engineering team",
            "source_material": "Section A. Section B. Section C.",
            "target_length_minutes": 4.0,
            "tone": "direct and concise",
            "visual_style": "modern infographic",
            "style_reference_summary": "High-contrast editorial lighting, restrained teal-and-amber palette, premium product-demo polish, crisp typography, dense but organized composition.",
            "must_include": "timeline",
            "must_avoid": "jargon",
            "ending_cta": "Book a pilot",
        }
    )

    prompt = _build_storyboard_user_prompt_from_brief(brief)

    assert "mode: final_script" in prompt
    assert "Perform minimal rewriting" in prompt
    assert '"video_goal": "Explain the product launch"' in prompt
    assert '"visual_style": "modern infographic"' in prompt
    assert '"style_reference_summary": "High-contrast editorial lighting, restrained teal-and-amber palette, premium product-demo polish, crisp typography, dense but organized composition."' in prompt
    assert "target narration words" in prompt


def test_analyze_style_references_openai_builds_multimodal_request(tmp_path, monkeypatch):
    image_path = tmp_path / "ref.png"
    image_path.write_bytes(base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jK6cAAAAASUVORK5CYII="
    ))
    captured = {}

    class FakeResponses:
        def create(self, **kwargs):
            captured.update(kwargs)
            return type("Resp", (), {"output_text": "Detailed style summary"})()

    class FakeClient:
        responses = FakeResponses()

    monkeypatch.setattr("core.director._get_openai_client", lambda: FakeClient())
    monkeypatch.setattr("core.director.load_prompt", lambda name: "system prompt")

    summary = analyze_style_references(
        [str(image_path)],
        normalize_brief({"audience": "Design-conscious buyers", "video_goal": "Pitch the product"}),
        provider="openai",
    )

    assert summary == "Detailed style summary"
    assert captured["instructions"] == "system prompt"
    assert captured["input"][0]["content"][0]["type"] == "input_text"
    assert captured["input"][0]["content"][1]["type"] == "input_image"
    assert captured["input"][0]["content"][1]["image_url"].startswith("data:image/png;base64,")


def test_analyze_style_references_anthropic_builds_multimodal_request(tmp_path, monkeypatch):
    image_path = tmp_path / "ref.png"
    image_path.write_bytes(base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jK6cAAAAASUVORK5CYII="
    ))
    captured = {}

    class FakeMessages:
        def create(self, **kwargs):
            captured.update(kwargs)
            return type("Resp", (), {"content": [type("Block", (), {"text": "Anthropic style summary"})()]})()

    class FakeClient:
        messages = FakeMessages()

    monkeypatch.setattr("core.director._get_anthropic_client", lambda: FakeClient())
    monkeypatch.setattr("core.director.load_prompt", lambda name: "system prompt")

    summary = analyze_style_references(
        [str(image_path)],
        normalize_brief({"audience": "Exec team", "video_goal": "Explain the concept"}),
        provider="anthropic",
    )

    assert summary == "Anthropic style summary"
    assert captured["system"] == "system prompt"
    assert captured["messages"][0]["content"][0]["type"] == "image"
    assert captured["messages"][0]["content"][-1]["type"] == "text"
