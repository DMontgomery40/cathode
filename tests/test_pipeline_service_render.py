from __future__ import annotations

import copy
from pathlib import Path

from core.pipeline_service import normalize_authored_image_scene_identities, render_project_service


def test_render_project_service_persists_video_compression_metadata(monkeypatch, tmp_path):
    project_dir = tmp_path / "render_project"
    project_dir.mkdir(parents=True, exist_ok=True)
    audio_path = project_dir / "audio" / "scene_000.wav"
    audio_path.parent.mkdir(parents=True, exist_ok=True)
    audio_path.write_bytes(b"wav")

    plan = {
        "meta": {
            "render_profile": {
                "render_backend": "ffmpeg",
                "fps": 24,
            }
        },
        "scenes": [
            {
                "id": 1,
                "scene_type": "image",
                "audio_path": str(audio_path),
            }
        ],
    }
    rendered_video_path = project_dir / "rendered.mp4"
    rendered_video_path.write_bytes(b"mp4")
    saved_plans: list[dict] = []
    compression_payload = {
        "path": str(rendered_video_path),
        "compressed": True,
        "reason": "compressed",
        "original_size_bytes": 987654,
        "final_size_bytes": 321000,
        "duration_seconds": 12.5,
        "original_average_bitrate_mbps": 6.3,
        "final_average_bitrate_mbps": 2.1,
    }

    monkeypatch.setattr("core.pipeline_service.load_plan", lambda _: plan)
    monkeypatch.setattr("core.pipeline_service._scene_has_primary_visual", lambda *args, **kwargs: True)
    monkeypatch.setattr("core.pipeline_service.assemble_video", lambda *args, **kwargs: rendered_video_path)
    monkeypatch.setattr(
        "core.pipeline_service.compress_video_if_oversized",
        lambda *args, **kwargs: compression_payload,
    )
    monkeypatch.setattr(
        "core.pipeline_service.save_plan",
        lambda _project_dir, updated_plan: saved_plans.append(updated_plan) or updated_plan,
    )
    monkeypatch.setattr(
        "core.pipeline_service.review_project_scenes",
        lambda *_args, **_kwargs: {"provider": "codex", "scene_count": 1, "review_dir": "/tmp/review"},
    )

    result = render_project_service(project_dir)

    assert result["status"] == "succeeded"
    assert result["video_path"] == str(rendered_video_path)
    assert result["compression"] == compression_payload
    assert result["scene_review"]["provider"] == "codex"
    assert saved_plans
    assert saved_plans[-1]["meta"]["video_path"] == str(rendered_video_path)
    assert saved_plans[-1]["meta"]["video_compression"] == compression_payload


def test_render_project_service_allows_clip_audio_video_without_audio_path(monkeypatch, tmp_path):
    project_dir = tmp_path / "render_project"
    project_dir.mkdir(parents=True, exist_ok=True)
    clip_path = project_dir / "clips" / "scene_000.mp4"
    clip_path.parent.mkdir(parents=True, exist_ok=True)
    clip_path.write_bytes(b"mp4")

    plan = {
        "meta": {
            "render_profile": {
                "render_backend": "ffmpeg",
                "fps": 24,
            }
        },
        "scenes": [
            {
                "id": 1,
                "scene_type": "video",
                "video_path": str(clip_path),
                "video_audio_source": "clip",
                "audio_path": None,
            }
        ],
    }
    rendered_video_path = project_dir / "rendered.mp4"
    rendered_video_path.write_bytes(b"mp4")
    saved_plans: list[dict] = []

    monkeypatch.setattr("core.pipeline_service.load_plan", lambda _: plan)
    monkeypatch.setattr("core.pipeline_service._scene_has_primary_visual", lambda *args, **kwargs: True)
    monkeypatch.setattr("core.pipeline_service.assemble_video", lambda *args, **kwargs: rendered_video_path)
    monkeypatch.setattr(
        "core.pipeline_service.compress_video_if_oversized",
        lambda *args, **kwargs: {"path": str(rendered_video_path), "compressed": False},
    )
    monkeypatch.setattr(
        "core.pipeline_service.save_plan",
        lambda _project_dir, updated_plan: saved_plans.append(updated_plan) or updated_plan,
    )
    monkeypatch.setattr(
        "core.pipeline_service.review_project_scenes",
        lambda *_args, **_kwargs: {"provider": "codex", "scene_count": 1, "review_dir": "/tmp/review"},
    )

    result = render_project_service(project_dir)

    assert result["status"] == "succeeded"
    assert result["video_path"] == str(rendered_video_path)


def test_normalize_authored_image_scene_identities_preserves_existing_mixed_timeline_paths(tmp_path):
    project_dir = tmp_path / "mixed_project"
    images_dir = project_dir / "images"
    clips_dir = project_dir / "clips"
    images_dir.mkdir(parents=True)
    clips_dir.mkdir(parents=True)
    first_image = images_dir / "scene_000.png"
    second_image = images_dir / "scene_001.png"
    clip_path = clips_dir / "intro.mp4"
    first_image.write_bytes(b"first")
    second_image.write_bytes(b"second")
    clip_path.write_bytes(b"clip")

    plan = {
        "scenes": [
            {
                "id": 0,
                "uid": "cover",
                "scene_type": "image",
                "image_path": str(first_image),
                "composition": {"manifestation": "authored_image"},
            },
            {
                "id": 1,
                "uid": "intro_clip",
                "scene_type": "video",
                "video_path": str(clip_path),
                "video_audio_source": "clip",
                "composition": {"manifestation": "source_video"},
            },
            {
                "id": 2,
                "uid": "next_slide",
                "scene_type": "image",
                "image_path": str(second_image),
                "composition": {"manifestation": "authored_image"},
            },
        ],
    }

    updated, changed = normalize_authored_image_scene_identities(project_dir, plan)

    assert changed is False
    assert updated["scenes"][2]["image_path"] == str(second_image)
    assert second_image.read_bytes() == b"second"
    assert not (images_dir / "scene_002.png").exists()


def test_render_project_service_scopes_exact_repairs_and_preserves_canonical_slide_path(monkeypatch, tmp_path):
    project_dir = tmp_path / "render_project"
    project_dir.mkdir(parents=True, exist_ok=True)
    audio_path = project_dir / "audio" / "scene_000.wav"
    audio_path.parent.mkdir(parents=True, exist_ok=True)
    audio_path.write_bytes(b"wav")
    image_path = project_dir / "images" / "scene_001.png"
    image_path.parent.mkdir(parents=True, exist_ok=True)
    image_path.write_bytes(b"png")
    edited_paths = [
        project_dir / "images" / ".scene_000_textfix_a.png",
        project_dir / "images" / ".scene_000_textfix_b.png",
    ]
    for path in edited_paths:
        path.write_bytes(b"png-edit")
    regenerated_path = project_dir / "images" / ".scene_000_regen.png"
    regenerated_path.write_bytes(b"png-regen")

    plan_state = {
        "meta": {
            "brief": {"source_material": "demo"},
            "image_profile": {
                "provider": "replicate",
                "generation_model": "qwen/qwen-image-2512",
                "edit_model": "qwen/qwen-image-edit-2511",
            },
            "render_profile": {
                "render_backend": "ffmpeg",
                "fps": 24,
            },
        },
        "scenes": [
            {
                "id": 1,
                "uid": "scene_000",
                "scene_type": "image",
                "narration": "Spell the surname correctly.",
                "visual_prompt": 'Title card with "Montgomery"',
                "on_screen_text": ["Montgomery"],
                "manifestation_plan": {"text_expected": True, "text_critical": False},
                "composition": {"manifestation": "authored_image", "family": "static_media", "mode": "none"},
                "image_path": str(image_path),
                "audio_path": str(audio_path),
            }
        ],
    }
    compression_payload = {"path": str(project_dir / "rendered.mp4"), "compressed": False}
    rendered_video_path = project_dir / "rendered.mp4"
    rendered_video_path.write_bytes(b"mp4")
    review_calls: list[tuple[str, tuple[str, ...] | None]] = []
    edit_prompts: list[str] = []
    rewrite_inputs: list[tuple[str, str]] = []
    exact_review_count = 0
    edit_output_count = 0

    def fake_load(_project_dir):
        return copy.deepcopy(plan_state)

    def fake_save(_project_dir, updated_plan):
        nonlocal plan_state
        plan_state = copy.deepcopy(updated_plan)
        return updated_plan

    def fake_review(_project_dir, *, trigger, scene_uids=None):
        nonlocal exact_review_count
        review_calls.append((trigger, tuple(scene_uids) if scene_uids else None))
        scene = plan_state["scenes"][0]
        if trigger == "post_render_review":
            scene["judge_verdict"] = {
                "winner": "primary",
                "text_repairs": [
                    {
                        "candidate_id": "primary",
                        "wrong_text": "Mongogmery",
                        "correct_text": "Montgomery",
                        "reason": "Direct literal correction is safe.",
                    }
                ],
            }
        elif trigger == "post_exact_text_edit_review":
            exact_review_count += 1
            scene["judge_verdict"] = {
                "winner": "primary",
                "text_repairs": [
                    {
                        "candidate_id": "primary",
                        "wrong_text": "Montgomey",
                        "correct_text": "Montgomery",
                        "reason": (
                            "A second exact edit is still safe."
                            if exact_review_count == 1
                            else "The same literal issue is still present after the second edit."
                        ),
                    }
                ],
            }
        elif trigger == "post_synonym_regenerate_review":
            scene["judge_verdict"] = {"winner": "primary", "text_repairs": []}
        else:
            scene["judge_verdict"] = {"winner": "primary", "text_repairs": []}
        scene["candidate_outputs"] = {
            "primary": {
                "candidate_type": "authored_image",
                "source_path": str(image_path.resolve()),
                "review_status": "winner",
            }
        }
        return {"provider": "codex", "scene_count": 1, "review_dir": "/tmp/review", "scenes": []}

    def fake_edit_image(prompt, *_args, **_kwargs):
        nonlocal edit_output_count
        output_path = edited_paths[edit_output_count]
        edit_output_count += 1
        edit_prompts.append(prompt)
        return output_path

    monkeypatch.setattr("core.pipeline_service.load_plan", fake_load)
    monkeypatch.setattr("core.pipeline_service.save_plan", fake_save)
    monkeypatch.setattr("core.pipeline_service._scene_has_primary_visual", lambda *args, **kwargs: True)
    monkeypatch.setattr("core.pipeline_service.assemble_video", lambda *args, **kwargs: rendered_video_path)
    monkeypatch.setattr("core.pipeline_service.compress_video_if_oversized", lambda *args, **kwargs: compression_payload)
    monkeypatch.setattr("core.pipeline_service.review_project_scenes", fake_review)
    monkeypatch.setattr("core.pipeline_service.edit_image", fake_edit_image)
    monkeypatch.setattr(
        "core.pipeline_service.rewrite_prompt_for_synonym_fallback_with_metadata",
        lambda **kwargs: rewrite_inputs.append((kwargs["wrong_text"], kwargs["correct_text"])) or (
            {
                "replacement_text": "Family name",
                "rewritten_prompt": 'Title card with "Family name"',
                "rewritten_on_screen_text": ["Family name"],
            },
            {"actual": None, "preflight": None},
        ),
    )
    monkeypatch.setattr(
        "core.pipeline_service.generate_scene_image",
        lambda *_args, **_kwargs: regenerated_path,
    )

    result = render_project_service(project_dir)

    assert result["status"] == "succeeded"
    assert review_calls == [
        ("post_render_review", None),
        ("post_exact_text_edit_review", ("scene_000",)),
        ("post_exact_text_edit_review", ("scene_000",)),
        ("post_synonym_regenerate_review", ("scene_000",)),
        ("post_render_review_after_repairs", None),
    ]
    assert edit_prompts == [
        'change "Mongogmery" to "Montgomery"',
        'change "Montgomey" to "Montgomery"',
    ]
    assert rewrite_inputs == [("Montgomey", "Montgomery")]
    assert plan_state["scenes"][0]["image_path"] == str(image_path.resolve())
    assert plan_state["scenes"][0]["candidate_outputs"]["primary"]["source_path"] == str(image_path.resolve())
    assert plan_state["scenes"][0]["visual_prompt"] == 'Title card with "Family name"'
    assert plan_state["scenes"][0]["on_screen_text"] == ["Family name"]
    assert image_path.exists()
    assert not any(path.exists() for path in edited_paths)
    assert not regenerated_path.exists()


def test_render_project_service_reports_unresolved_text_repairs_honestly(monkeypatch, tmp_path):
    project_dir = tmp_path / "render_project"
    project_dir.mkdir(parents=True, exist_ok=True)
    audio_path = project_dir / "audio" / "scene_000.wav"
    audio_path.parent.mkdir(parents=True, exist_ok=True)
    audio_path.write_bytes(b"wav")
    image_path = project_dir / "images" / "scene_001.png"
    image_path.parent.mkdir(parents=True, exist_ok=True)
    image_path.write_bytes(b"png")
    edited_path = project_dir / "images" / ".scene_000_textfix.png"
    edited_path.write_bytes(b"png-edit")
    regenerated_path = project_dir / "images" / ".scene_000_regen.png"
    regenerated_path.write_bytes(b"png-regen")

    plan_state = {
        "meta": {
            "brief": {"source_material": "demo"},
            "image_profile": {
                "provider": "replicate",
                "generation_model": "qwen/qwen-image-2512",
                "edit_model": "qwen/qwen-image-edit-2511",
            },
            "render_profile": {
                "render_backend": "ffmpeg",
                "fps": 24,
            },
        },
        "scenes": [
            {
                "id": 1,
                "uid": "scene_000",
                "scene_type": "image",
                "narration": "Spell the surname correctly.",
                "visual_prompt": 'Title card with "Montgomery"',
                "on_screen_text": ["Montgomery"],
                "manifestation_plan": {"text_expected": True, "text_critical": False},
                "composition": {"manifestation": "authored_image", "family": "static_media", "mode": "none"},
                "image_path": str(image_path),
                "audio_path": str(audio_path),
            }
        ],
    }
    compression_payload = {"path": str(project_dir / "rendered.mp4"), "compressed": False}
    rendered_video_path = project_dir / "rendered.mp4"
    rendered_video_path.write_bytes(b"mp4")

    def fake_load(_project_dir):
        return copy.deepcopy(plan_state)

    def fake_save(_project_dir, updated_plan):
        nonlocal plan_state
        plan_state = copy.deepcopy(updated_plan)
        return updated_plan

    def fake_review(_project_dir, *, trigger, scene_uids=None):
        scene = plan_state["scenes"][0]
        if trigger == "post_render_review":
            scene["judge_verdict"] = {
                "winner": "primary",
                "text_repairs": [
                    {
                        "candidate_id": "primary",
                        "wrong_text": "Mongogmery",
                        "correct_text": "Montgomery",
                        "reason": "Direct literal correction is safe.",
                    }
                ],
            }
        else:
            scene["judge_verdict"] = {
                "winner": "primary",
                "text_repairs": [
                    {
                        "candidate_id": "primary",
                        "wrong_text": "Montgomey",
                        "correct_text": "Montgomery",
                        "reason": "The slide is still visibly wrong.",
                    }
                ],
            }
        scene["candidate_outputs"] = {
            "primary": {
                "candidate_type": "authored_image",
                "source_path": str(image_path.resolve()),
                "review_status": "winner",
            }
        }
        return {"provider": "codex", "scene_count": 1, "review_dir": "/tmp/review", "scenes": []}

    monkeypatch.setattr("core.pipeline_service.load_plan", fake_load)
    monkeypatch.setattr("core.pipeline_service.save_plan", fake_save)
    monkeypatch.setattr("core.pipeline_service._scene_has_primary_visual", lambda *args, **kwargs: True)
    monkeypatch.setattr("core.pipeline_service.assemble_video", lambda *args, **kwargs: rendered_video_path)
    monkeypatch.setattr("core.pipeline_service.compress_video_if_oversized", lambda *args, **kwargs: compression_payload)
    monkeypatch.setattr("core.pipeline_service.review_project_scenes", fake_review)
    monkeypatch.setattr("core.pipeline_service.edit_image", lambda *_args, **_kwargs: edited_path)
    monkeypatch.setattr(
        "core.pipeline_service.rewrite_prompt_for_synonym_fallback_with_metadata",
        lambda **_kwargs: (
            {
                "replacement_text": "Family name",
                "rewritten_prompt": 'Title card with "Family name"',
                "rewritten_on_screen_text": ["Family name"],
            },
            {"actual": None, "preflight": None},
        ),
    )
    monkeypatch.setattr("core.pipeline_service.generate_scene_image", lambda *_args, **_kwargs: regenerated_path)

    result = render_project_service(project_dir)

    assert result["status"] == "partial_success"
    assert result["text_review_failures"] == ["scene_000"]
    assert result["scene_review"]["provider"] == "codex"


def test_render_project_service_applies_pre_render_native_candidate_winner(monkeypatch, tmp_path):
    project_dir = tmp_path / "render_project"
    project_dir.mkdir(parents=True, exist_ok=True)
    audio_path = project_dir / "audio" / "scene_000.wav"
    audio_path.parent.mkdir(parents=True, exist_ok=True)
    audio_path.write_bytes(b"wav")
    image_path = project_dir / "images" / "scene_000.png"
    image_path.parent.mkdir(parents=True, exist_ok=True)
    image_path.write_bytes(b"png")
    native_preview = project_dir / ".cathode" / "scene_review" / "candidate.mp4"
    native_preview.parent.mkdir(parents=True, exist_ok=True)
    native_preview.write_bytes(b"mp4")
    rendered_video_path = project_dir / "rendered.mp4"
    rendered_video_path.write_bytes(b"mp4")

    plan_state = {
        "meta": {
            "render_profile": {
                "render_backend": "ffmpeg",
                "fps": 24,
            }
        },
        "scenes": [
            {
                "id": 1,
                "uid": "scene_000",
                "scene_type": "image",
                "narration": "Prefer the precise native layout.",
                "visual_prompt": "Readable title card.",
                "manifestation_plan": {
                    "primary_path": "authored_image",
                    "fallback_path": "native_remotion",
                },
                "composition": {
                    "manifestation": "authored_image",
                    "family": "static_media",
                    "mode": "none",
                },
                "image_path": str(image_path),
                "audio_path": str(audio_path),
            }
        ],
    }
    review_calls: list[tuple[str, tuple[str, ...] | None]] = []
    assembled_scene_snapshots: list[dict] = []

    def fake_load(_project_dir):
        return copy.deepcopy(plan_state)

    def fake_save(_project_dir, updated_plan):
        nonlocal plan_state
        plan_state = copy.deepcopy(updated_plan)
        return updated_plan

    def fake_review(_project_dir, *, trigger, scene_uids=None):
        review_calls.append((trigger, tuple(scene_uids) if scene_uids else None))
        if trigger == "pre_render_candidate_selection":
            scene = plan_state["scenes"][0]
            scene["candidate_outputs"] = {
                "native_remotion": {
                    "candidate_id": "native_remotion",
                    "candidate_type": "native_remotion",
                    "source_kind": "video",
                    "source_path": str(native_preview),
                    "review_status": "winner",
                    "candidate_spec": {
                        "composition": {
                            "family": "bullet_stack",
                            "mode": "native",
                            "manifestation": "native_remotion",
                            "props": {"headline": "Exact title"},
                            "transition_after": None,
                            "rationale": "Use the exact deterministic layout.",
                        },
                        "motion": {
                            "template_id": "bullet_stack",
                            "props": {"headline": "Exact title"},
                            "rationale": "Use the exact deterministic layout.",
                        },
                    },
                }
            }
            scene["judge_verdict"] = {
                "winner": "native_remotion",
                "text_repairs": [],
            }
        else:
            scene = plan_state["scenes"][0]
            scene["candidate_outputs"] = {
                "native_remotion": {
                    "candidate_id": "native_remotion",
                    "candidate_type": "native_remotion",
                    "source_kind": "video",
                    "source_path": str(native_preview),
                    "review_status": "winner",
                }
            }
            scene["judge_verdict"] = {
                "winner": "native_remotion",
                "text_repairs": [],
            }
        return {"provider": "codex", "scene_count": 1, "review_dir": "/tmp/review", "scenes": []}

    def fake_assemble(scenes, *_args, **_kwargs):
        assembled_scene_snapshots.append(copy.deepcopy(scenes[0]))
        return rendered_video_path

    monkeypatch.setattr("core.pipeline_service.load_plan", fake_load)
    monkeypatch.setattr("core.pipeline_service.save_plan", fake_save)
    monkeypatch.setattr("core.pipeline_service._scene_has_primary_visual", lambda *args, **kwargs: True)
    monkeypatch.setattr("core.pipeline_service.assemble_video", fake_assemble)
    monkeypatch.setattr("core.pipeline_service.compress_video_if_oversized", lambda *args, **kwargs: {"path": str(rendered_video_path), "compressed": False})
    monkeypatch.setattr("core.pipeline_service.review_project_scenes", fake_review)

    result = render_project_service(project_dir)

    assert result["status"] == "succeeded"
    assert review_calls == [
        ("pre_render_candidate_selection", ("scene_000",)),
        ("post_render_review", None),
    ]
    assert assembled_scene_snapshots
    rendered_scene = assembled_scene_snapshots[0]
    assert rendered_scene["scene_type"] == "motion"
    assert rendered_scene["image_path"] is None
    assert rendered_scene["preview_path"] == str(native_preview.resolve())
    assert rendered_scene["composition"]["manifestation"] == "native_remotion"
    assert rendered_scene["composition"]["family"] == "bullet_stack"
    assert rendered_scene["motion"]["template_id"] == "bullet_stack"
