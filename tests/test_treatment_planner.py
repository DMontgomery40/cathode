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


def test_treatment_planning_needed_requires_explicit_native_composition():
    brief = {
        "source_mode": "ideas_notes",
        "source_material": "Build a motion-first surreal 3D observatory sequence.",
        "composition_mode": "motion_only",
        "visual_source_strategy": "images_only",
        "text_render_mode": "visual_authored",
    }
    scenes = [
        {
            "uid": "scene_001",
            "title": "Hero beat",
            "scene_type": "motion",
            "narration": "The scene should move.",
            "visual_prompt": "Orbit around the hero chamber.",
        }
    ]

    assert treatment_planning_needed(brief, scenes) is False


def test_treatment_planner_prompt_forbids_transitions_for_clinical_decks():
    """Treatment planner system prompt must enforce hard cuts for clinical/qEEG content."""
    from core.director import load_prompt

    prompt_text = load_prompt("treatment_planner_system")
    assert "hard cut" in prompt_text.lower() or "Hard cuts" in prompt_text
    assert "transition_hint" in prompt_text
    assert "qEEG" in prompt_text or "clinical" in prompt_text.lower()


def test_treatment_planner_applies_supported_registry_override_without_decorative_fade_drift(monkeypatch):
    captured = {}

    class FakeResponses:
        def create(self, **kwargs):
            captured.update(kwargs)
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
                                        "layoutVariant": "symbolic_duet",
                                        "heroObject": "Warm wave",
                                        "secondaryObject": "Luminous drift",
                                        "orbitingObject": "Lantern fragments",
                                        "orbitCount": 0,
                                        "environmentBackdrop": "dreamlike sea dusk",
                                        "ambientDetails": "soft fog and salt haze",
                                        "paletteWords": ["sea blue", "amber"],
                                        "cameraMove": "slow lateral drift",
                                        "copyTreatment": "none",
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

    monkeypatch.setattr("core.director._get_openai_client", lambda: FakeClient())
    monkeypatch.setattr("core.treatment_planner.load_prompt", lambda name: "system prompt")

    scenes, metadata = plan_scene_treatments_with_metadata(
        [
                {
                    "uid": "scene_001",
                    "title": "Impossible hello",
                    "scene_type": "image",
                    "narration": "Two unlikely forms acknowledge each other inside a cinematic hero chamber.",
                    "visual_prompt": "A dreamlike three-dimensional hero tableau with orbiting lantern fragments and a slow camera orbit.",
                    "transition_hint": "fade",
                    "composition_intent": {"transition_after": "fade"},
                    "composition": {
                    "family": "quote_focus",
                    "mode": "native",
                    "props": {
                        "headline": "Impossible hello",
                        "body": "Two unlikely forms acknowledge each other.",
                        "kicker": "Impossible hello",
                    },
                },
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
    assert scene["composition"]["transition_after"] is None
    assert scene["transition_hint"] is None
    assert scene["composition_intent"] == {}
    assert scene["composition"]["props"]["heroObject"] == "Warm wave"
    assert scene["composition"]["rationale"] == "Symbolic duet benefits from a cinematic 3D tableau."
    assert metadata["actual"]["operation"] == "treatment_planning"
    assert captured["model"] == "gpt-5.4"
    assert captured["reasoning"] == {"effort": "xhigh"}


def test_treatment_planner_can_upgrade_weak_text_card_family_to_surreal_tableau(monkeypatch):
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
                                    "uid": "scene_hero",
                                    "family": "surreal_tableau_3d",
                                    "mode": "native",
                                    "props": {
                                        "layoutVariant": "orbit_tableau",
                                        "heroObject": "glowing cracked hourglass moon",
                                        "secondaryObject": "bending constellation curtains",
                                        "orbitingObject": "brass moths",
                                        "orbitCount": 7,
                                        "environmentBackdrop": "vast dark chamber with deep indigo velvet walls",
                                        "ambientDetails": "faint bioluminescent lichen, subtle volumetric fog",
                                        "paletteWords": ["deep indigo", "warm amber", "ivory", "brass"],
                                        "cameraMove": "slow circular camera orbit",
                                        "copyTreatment": "none",
                                    },
                                    "rationale": "Hero tableau should not stay a quote card.",
                                }
                            ]
                        }
                    ),
                    "usage": {"input_tokens": 120, "output_tokens": 60},
                },
            )()

    class FakeClient:
        responses = FakeResponses()

    monkeypatch.setattr("core.director._get_openai_client", lambda: FakeClient())
    monkeypatch.setattr("core.treatment_planner.load_prompt", lambda name: "system prompt")

    scenes, _ = plan_scene_treatments_with_metadata(
        [
            {
                "uid": "scene_hero",
                "title": "The 3D Observatory Tableau",
                "scene_type": "motion",
                "narration": "The hero room finally reveals itself in full orbit.",
                "visual_prompt": "A fully three-dimensional tableau with a glowing hourglass moon and orbiting brass moths.",
                "composition": {
                    "family": "quote_focus",
                    "mode": "native",
                    "props": {"headline": "The 3D Observatory Tableau"},
                },
            }
        ],
        brief={
            "source_mode": "ideas_notes",
            "source_material": "Build a motion-first surreal 3D observatory sequence.",
            "composition_mode": "motion_only",
            "visual_source_strategy": "images_only",
            "text_render_mode": "visual_authored",
        },
        provider="openai",
    )

    scene = scenes[0]
    assert scene["composition"]["family"] == "surreal_tableau_3d"
    assert scene["composition"]["props"]["layoutVariant"] == "orbit_tableau"
    assert scene["composition"]["props"]["heroObject"] == "glowing cracked hourglass moon"


def test_treatment_planner_cannot_downgrade_obvious_surreal_tableau_to_quote_focus(monkeypatch):
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
                                    "uid": "scene_hero",
                                    "family": "quote_focus",
                                    "mode": "native",
                                    "props": {
                                        "headline": "The Hero Tableau",
                                        "body": "This should have been downgraded, but must not be.",
                                        "kicker": "The Hero Tableau",
                                    },
                                    "rationale": "Incorrect downgrade.",
                                }
                            ]
                        }
                    ),
                    "usage": {"input_tokens": 120, "output_tokens": 60},
                },
            )()

    class FakeClient:
        responses = FakeResponses()

    monkeypatch.setattr("core.director._get_openai_client", lambda: FakeClient())
    monkeypatch.setattr("core.treatment_planner.load_prompt", lambda name: "system prompt")

    scenes, _ = plan_scene_treatments_with_metadata(
        [
            {
                "uid": "scene_hero",
                "title": "The Hero Tableau — Circular Orbit",
                "scene_type": "motion",
                "narration": "The moon and moths move in a full living orbit.",
                "visual_prompt": "The complete observatory tableau in a dramatic chamber with orbiting brass moths and a cracked hourglass moon.",
                "staging_notes": "This is the hero scene. The camera performs a slow circular arc around the tableau for a true three-dimensional read.",
                "composition": {
                    "family": "surreal_tableau_3d",
                    "mode": "native",
                    "props": {
                        "layoutVariant": "orbit_tableau",
                        "heroObject": "glowing cracked hourglass moon",
                    },
                },
            }
        ],
        brief={
            "source_mode": "ideas_notes",
            "source_material": "Motion-first observatory tableau.",
            "composition_mode": "motion_only",
            "visual_source_strategy": "images_only",
            "text_render_mode": "visual_authored",
        },
        provider="openai",
    )

    scene = scenes[0]
    assert scene["composition"]["family"] == "surreal_tableau_3d"
    assert scene["composition"]["props"]["heroObject"] == "glowing cracked hourglass moon"


def test_treatment_planner_cannot_upgrade_plain_ui_surface_to_overlay_without_callout_intent(monkeypatch):
    def fail_if_called(**kwargs):
        raise AssertionError("non-native scenes should not call the treatment planner")

    monkeypatch.setattr("core.director._get_openai_client", fail_if_called)
    monkeypatch.setattr("core.treatment_planner.load_prompt", lambda name: "system prompt")

    scenes, metadata = plan_scene_treatments_with_metadata(
        [
            {
                "uid": "scene_plain_ui",
                "title": "The React Control Room",
                "scene_type": "image",
                "narration": "A clean screenshot shows the current product workspace.",
                "visual_prompt": "Dark-mode screenshot of the workspace with the scene rail and inspector visible.",
                "on_screen_text": ["Brief", "Scenes", "Render"],
                "composition": {
                    "family": "media_pan",
                    "mode": "none",
                    "props": {},
                },
            }
        ],
        brief={
            "source_mode": "ideas_notes",
            "source_material": "Show the current product UI honestly.",
            "composition_mode": "classic",
            "visual_source_strategy": "images_only",
            "text_render_mode": "visual_authored",
        },
        provider="openai",
    )

    scene = scenes[0]
    assert scene["composition"]["family"] == "media_pan"
    assert scene["composition"]["mode"] == "none"
    assert metadata == {}


def test_treatment_planner_preserves_scene_copy_and_rebuilds_data_from_scene_source(monkeypatch):
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
                                    "uid": "scene_data",
                                    "family": "three_data_stage",
                                    "mode": "native",
                                    "props": {
                                        "headline": "Invented headline",
                                        "kicker": "Invented kicker",
                                        "layoutVariant": "line_with_band",
                                        "emphasis": "trend_over_time",
                                        "palette": "amber_on_navy",
                                    },
                                    "data": {
                                        "series": [
                                            {
                                                "id": "fake",
                                                "label": "Fake",
                                                "type": "line",
                                                "points": [
                                                    {"x": "Session 1", "y": 99},
                                                    {"x": "Session 2", "y": 101},
                                                ],
                                            }
                                        ]
                                    },
                                    "rationale": "Scene is data-led and should stay in the native chart branch.",
                                }
                            ]
                        }
                    ),
                    "usage": {"input_tokens": 130, "output_tokens": 70},
                },
            )()

    class FakeClient:
        responses = FakeResponses()

    monkeypatch.setattr("core.director._get_openai_client", lambda: FakeClient())
    monkeypatch.setattr("core.treatment_planner.load_prompt", lambda name: "system prompt")

    scenes, _ = plan_scene_treatments_with_metadata(
        [
            {
                "uid": "scene_data",
                "title": "Reaction Time Trend",
                "scene_type": "image",
                "narration": "Reaction time improves across the measured sessions.",
                "visual_prompt": "Clinical data card with calm chart treatment.",
                "on_screen_text": ["Reaction Time", "Improved over time"],
                "data_points": [
                    "Session 1: 3",
                    "Session 2: 5",
                    "Reference range: 2 to 4",
                ],
                "composition": {
                    "family": "quote_focus",
                    "mode": "native",
                    "props": {
                        "headline": "Reaction Time",
                        "body": "Improved over time",
                        "kicker": "Reaction Time Trend",
                    },
                },
            }
        ],
        brief={
            "source_mode": "ideas_notes",
            "source_material": "Show the patient data clearly and honestly.",
            "composition_mode": "classic",
            "visual_source_strategy": "images_only",
            "text_render_mode": "visual_authored",
        },
        provider="openai",
    )

    scene = scenes[0]
    assert scene["composition"]["family"] == "three_data_stage"
    assert scene["on_screen_text"] == ["Reaction Time", "Improved over time"]
    assert scene["composition"]["props"]["headline"] == "Reaction Time"
    assert scene["composition"]["props"]["kicker"] == "Reaction Time Trend"
    assert scene["composition"]["props"]["layoutVariant"] == "line_with_band"
    assert scene["composition"]["props"]["palette"] == "amber_on_navy"
    assert scene["composition"]["data"]["series"][0]["points"] == [
        {"x": "Session 1", "y": 3.0},
        {"x": "Session 2", "y": 5.0},
    ]
    assert scene["composition"]["data"]["referenceBands"] == [
        {
            "id": "reference_range_2_to_4",
            "label": "Reference range: 2 to 4",
            "yMin": 2.0,
            "yMax": 4.0,
        }
    ]
