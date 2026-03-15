import json

from core.treatment_planner import (
    plan_scene_treatments_with_metadata,
    treatment_planning_needed,
)


def test_treatment_planning_needed_stays_off_for_pure_creative_image_first_brief():
    brief = {
        "source_mode": "ideas_notes",
        "source_material": "Tell a whimsical short story about an impossible encounter.",
        "visual_style": "storybook illustration",
        "tone": "warm and playful",
        "composition_mode": "classic",
        "visual_source_strategy": "images_only",
        "text_render_mode": "visual_authored",
    }
    scenes = [
        {
            "uid": "scene_001",
            "title": "Hello",
            "scene_type": "image",
            "narration": "A tiny wave starts it all.",
            "visual_prompt": "Warm cinematic still.",
        }
    ]

    assert treatment_planning_needed(brief, scenes) is False


def test_treatment_planner_applies_supported_registry_override(monkeypatch):
    class FakeResponses:
        def create(self, **kwargs):
            return type(
                "Resp",
                (),
                {
                    "output_text": json.dumps(
                        {
                            "scenes": [
                                {
                                    "uid": "scene_001",
                                    "family": "surreal_tableau_3d",
                                    "mode": "native",
                                    "transition_hint": "fade",
                                    "props": {
                                        "headline": "Impossible hello",
                                        "leftSubject": "Warm wave",
                                        "rightSubject": "Luminous drift",
                                        "environment": "dreamlike sea dusk",
                                    },
                                    "rationale": "Symbolic duet benefits from a cinematic 3D tableau.",
                                }
                            ]
                        }
                    ),
                    "usage": {"input_tokens": 100, "output_tokens": 40},
                },
            )()

    class FakeClient:
        responses = FakeResponses()

    monkeypatch.setattr("core.treatment_planner._get_openai_client", lambda: FakeClient())
    monkeypatch.setattr("core.treatment_planner.load_prompt", lambda name: "system prompt")

    scenes, metadata = plan_scene_treatments_with_metadata(
        [
            {
                "uid": "scene_001",
                "title": "Impossible hello",
                "scene_type": "image",
                "narration": "Two unlikely forms acknowledge each other.",
                "visual_prompt": "A dreamlike meeting in motion.",
            }
        ],
        brief={
            "source_mode": "ideas_notes",
            "source_material": "Stage a surreal 3D motion treatment for an impossible encounter.",
            "composition_mode": "classic",
            "visual_source_strategy": "images_only",
            "text_render_mode": "visual_authored",
        },
        provider="openai",
    )

    scene = scenes[0]
    assert scene["composition"]["family"] == "surreal_tableau_3d"
    assert scene["composition"]["mode"] == "native"
    assert scene["composition"]["transition_after"]["kind"] == "fade"
    assert scene["composition"]["props"]["leftSubject"] == "Warm wave"
    assert scene["composition"]["rationale"] == "Symbolic duet benefits from a cinematic 3D tableau."
    assert metadata["actual"]["operation"] == "treatment_planning"
