from __future__ import annotations

import copy
from pathlib import Path

from core.pipeline_service import create_project_from_brief_service, generate_project_assets_service


def test_create_project_from_brief_service_copies_and_assigns_reviewed_footage(monkeypatch, tmp_path):
    source_clip = tmp_path / "fresh_capture.mp4"
    source_clip.write_bytes(b"demo")
    project_dir = tmp_path / "demo_project"

    monkeypatch.setattr(
        "core.pipeline_service.resolve_workflow_llm_roles",
        lambda provider=None: (provider or "anthropic", "openai"),
    )
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

    monkeypatch.setattr(
        "core.pipeline_service.resolve_workflow_llm_roles",
        lambda provider=None: (provider or "anthropic", "openai"),
    )
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


def test_create_project_from_brief_service_persists_agent_demo_profile(monkeypatch, tmp_path):
    project_dir = tmp_path / "demo_project"

    monkeypatch.setattr(
        "core.pipeline_service.resolve_workflow_llm_roles",
        lambda provider=None: (provider or "anthropic", "openai"),
    )
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
            "video_goal": "Demo the repo",
            "audience": "Technical buyers",
            "source_material": "Product notes.",
            "visual_source_strategy": "mixed_media",
        },
        provider="openai",
        agent_demo_profile={"workspace_path": "/tmp/workspace"},
    )

    assert plan["meta"]["agent_demo_profile"]["workspace_path"] == "/tmp/workspace"
    assert plan["meta"]["brief"]["composition_mode"] == "hybrid"
    assert plan["meta"]["video_profile"]["provider"] == "agent"
    assert plan["meta"]["render_profile"]["render_backend"] == "ffmpeg"


def test_generate_project_assets_service_emits_scene_progress(monkeypatch, tmp_path):
    project_dir = tmp_path / "demo_project"
    project_dir.mkdir()

    plan = {
        "meta": {
            "brief": {},
            "image_profile": {"provider": "replicate", "generation_model": "demo-model"},
            "video_profile": {"provider": "manual"},
            "tts_profile": {"provider": "kokoro", "voice": "af", "speed": 1.1},
        },
        "scenes": [
            {
                "id": 1,
                "uid": "scene_001",
                "title": "Intro",
                "scene_type": "image",
                "visual_prompt": "Intro still",
                "narration": "Scene one",
            },
            {
                "id": 2,
                "uid": "scene_002",
                "title": "Results",
                "scene_type": "image",
                "visual_prompt": "Results still",
                "narration": "Scene two",
            },
        ],
    }

    monkeypatch.setattr("core.pipeline_service.load_plan", lambda _project_dir: plan)
    monkeypatch.setattr("core.pipeline_service.save_plan", lambda _project_dir, saved_plan: saved_plan)
    monkeypatch.setattr("core.pipeline_service.resolve_image_profile", lambda profile=None: profile or {})
    monkeypatch.setattr("core.pipeline_service.resolve_video_profile", lambda profile=None: profile or {})
    monkeypatch.setattr("core.pipeline_service.resolve_tts_profile", lambda profile=None: profile or {})

    def fake_image(scene, _project_dir, **_kwargs):
        path = tmp_path / f"{scene['uid']}.png"
        path.write_bytes(b"png")
        return path

    def fake_audio(scene, _project_dir, **_kwargs):
        path = tmp_path / f"{scene['uid']}.wav"
        path.write_bytes(b"wav")
        return {"path": path, "provider": "kokoro", "model": "kokoro-local"}

    monkeypatch.setattr("core.pipeline_service.generate_scene_image", fake_image)
    monkeypatch.setattr("core.pipeline_service.generate_scene_audio_result", fake_audio)

    events: list[dict[str, object]] = []
    result = generate_project_assets_service(
        project_dir,
        generate_images=True,
        generate_audio=True,
        generate_videos=False,
        progress_callback=events.append,
    )

    assert result["images_generated"] == 2
    assert result["audio_generated"] == 2
    assert any(event["progress_label"] == "Generating audio" for event in events)
    assert any(event["progress_label"] == "Generating image" for event in events)
    assert any(str(event["progress_detail"]).startswith("Scene 1 of 2 - Intro") for event in events)
    assert events[-1]["progress"] == 1.0
    assert events[-1]["progress_label"] == "Asset pass complete"


def test_generate_project_assets_service_skips_native_remotion_scenes_for_image_generation(monkeypatch, tmp_path):
    project_dir = tmp_path / "demo_project"
    project_dir.mkdir()

    plan = {
        "meta": {
            "brief": {},
            "image_profile": {"provider": "replicate", "generation_model": "demo-model"},
            "video_profile": {"provider": "manual"},
            "tts_profile": {"provider": "kokoro", "voice": "af", "speed": 1.1},
        },
        "scenes": [
            {
                "id": 1,
                "uid": "scene_001",
                "title": "Still",
                "scene_type": "image",
                "visual_prompt": "Ordinary still",
                "narration": "Scene one",
            },
            {
                "id": 2,
                "uid": "scene_002",
                "title": "Overlay beat",
                "scene_type": "image",
                "visual_prompt": "Pinned callout scene",
                "narration": "Scene two",
                "composition": {
                    "family": "software_demo_focus",
                    "mode": "overlay",
                    "manifestation": "native_remotion",
                    "props": {"headline": "Pinned callout"},
                },
            },
        ],
    }

    image_calls: list[str] = []

    monkeypatch.setattr("core.pipeline_service.load_plan", lambda _project_dir: plan)
    monkeypatch.setattr("core.pipeline_service.save_plan", lambda _project_dir, saved_plan: saved_plan)
    monkeypatch.setattr("core.pipeline_service.resolve_image_profile", lambda profile=None: profile or {})
    monkeypatch.setattr("core.pipeline_service.resolve_video_profile", lambda profile=None: profile or {})
    monkeypatch.setattr("core.pipeline_service.resolve_tts_profile", lambda profile=None: profile or {})

    def fake_image(scene, _project_dir, **_kwargs):
        image_calls.append(str(scene["uid"]))
        path = tmp_path / f"{scene['uid']}.png"
        path.write_bytes(b"png")
        return path

    monkeypatch.setattr("core.pipeline_service.generate_scene_image", fake_image)

    result = generate_project_assets_service(
        project_dir,
        generate_images=True,
        generate_audio=False,
        generate_videos=False,
    )

    assert result["images_generated"] == 1
    assert image_calls == ["scene_001"]


def test_generate_project_assets_service_skips_final_audio_when_replicate_clip_audio_is_expected(monkeypatch, tmp_path):
    project_dir = tmp_path / "demo_project"
    project_dir.mkdir()
    saved_plans: list[dict] = []

    plan = {
        "meta": {
            "brief": {},
            "image_profile": {"provider": "replicate", "generation_model": "qwen/qwen-image-2512"},
            "video_profile": {
                "provider": "replicate",
                "generation_model": "",
                "model_selection_mode": "automatic",
                "quality_mode": "standard",
                "generate_audio": True,
            },
            "tts_profile": {"provider": "openai", "model_id": "gpt-4o-mini-tts", "voice": "marin", "speed": 1.0},
        },
        "scenes": [
            {
                "id": 1,
                "uid": "scene_001",
                "title": "Spokesperson",
                "scene_type": "video",
                "visual_prompt": "A founder speaks to camera.",
                "narration": "Come visit our showroom this weekend.",
                "audio_path": str(tmp_path / "stale.wav"),
                "composition": {
                    "family": "software_demo_focus",
                    "mode": "overlay",
                    "manifestation": "source_video",
                    "props": {"headline": "Pinned callout"},
                },
            },
        ],
    }

    monkeypatch.setattr("core.pipeline_service.load_plan", lambda _project_dir: plan)
    monkeypatch.setattr("core.pipeline_service.save_plan", lambda _project_dir, saved_plan: saved_plans.append(saved_plan) or saved_plan)
    monkeypatch.setattr("core.pipeline_service.resolve_image_profile", lambda profile=None: profile or {})
    monkeypatch.setattr("core.pipeline_service.resolve_video_profile", lambda profile=None: profile or {})
    monkeypatch.setattr("core.pipeline_service.resolve_tts_profile", lambda profile=None: profile or {})
    monkeypatch.setattr(
        "core.pipeline_service.generate_scene_video_result",
        lambda scene, _project_dir, **_kwargs: {
            "path": tmp_path / "scene_001.mp4",
            "provider": "replicate",
            "model": "kwaivgi/kling-avatar-v2",
            "route_kind": "speaking",
            "quality_mode": "standard",
            "generate_audio": True,
            "duration_seconds": 4.0,
            "reference_image_generated": True,
            "reference_audio_generated": True,
            "reference_audio_provider": "openai",
            "reference_audio_model": "gpt-4o-mini-tts",
        },
    )
    (tmp_path / "scene_001.mp4").write_bytes(b"mp4")

    result = generate_project_assets_service(
        project_dir,
        generate_images=False,
        generate_audio=True,
        generate_videos=True,
    )

    assert result["audio_generated"] == 0
    assert result["audio_skipped"] == 1
    assert result["videos_generated"] == 1
    assert saved_plans
    saved_scene = saved_plans[-1]["scenes"][0]
    assert saved_scene["video_audio_source"] == "clip"
    assert saved_scene["audio_path"] is None


def test_generate_project_assets_service_runs_agent_demo_for_video_scenes(monkeypatch, tmp_path):
    project_dir = tmp_path / "demo_project"
    project_dir.mkdir()

    updated_plan = {
        "meta": {
            "brief": {},
            "video_profile": {"provider": "agent"},
            "agent_demo_profile": {"workspace_path": "/tmp/workspace"},
            "tts_profile": {"provider": "kokoro", "voice": "af", "speed": 1.1},
        },
        "scenes": [
            {
                "id": 1,
                "uid": "scene_001",
                "title": "Repo walkthrough",
                "scene_type": "video",
                "visual_prompt": "Capture the repo walkthrough.",
                "narration": "Show the nested prompt system.",
                "audio_path": str(tmp_path / "scene_001.wav"),
                "video_path": str(tmp_path / "scene_001.mp4"),
            },
        ],
    }
    Path(updated_plan["scenes"][0]["audio_path"]).write_bytes(b"wav")
    Path(updated_plan["scenes"][0]["video_path"]).write_bytes(b"mp4")

    initial_plan = {
        "meta": {
            "brief": {},
            "video_profile": {"provider": "agent"},
            "agent_demo_profile": {"workspace_path": "/tmp/workspace"},
            "tts_profile": {"provider": "kokoro", "voice": "af", "speed": 1.1},
        },
        "scenes": [
            {
                "id": 1,
                "uid": "scene_001",
                "title": "Repo walkthrough",
                "scene_type": "video",
                "visual_prompt": "Capture the repo walkthrough.",
                "narration": "Show the nested prompt system.",
                "audio_path": str(tmp_path / "scene_001.wav"),
                "video_path": None,
            },
        ],
    }
    Path(initial_plan["scenes"][0]["audio_path"]).write_bytes(b"wav")

    saved_plans: list[dict] = []
    prompt_calls: list[dict] = []
    run_calls: list[dict] = []

    def fake_load_plan(_project_dir):
        return updated_plan if run_calls else initial_plan

    monkeypatch.setattr("core.pipeline_service.load_plan", fake_load_plan)
    monkeypatch.setattr("core.pipeline_service.save_plan", lambda _project_dir, saved_plan: saved_plans.append(saved_plan) or saved_plan)
    monkeypatch.setattr("core.pipeline_service.resolve_image_profile", lambda profile=None: profile or {})
    monkeypatch.setattr("core.pipeline_service.resolve_video_profile", lambda profile=None: profile or {})
    monkeypatch.setattr("core.pipeline_service.resolve_tts_profile", lambda profile=None: profile or {})
    monkeypatch.setattr("core.pipeline_service.choose_agent_cli", lambda preferred=None: ("codex", "/usr/bin/codex"))
    monkeypatch.setattr(
        "core.pipeline_service.build_agent_demo_prompt",
        lambda **kwargs: prompt_calls.append(kwargs) or "agent demo prompt",
    )
    monkeypatch.setattr(
        "core.pipeline_service.run_agent_demo_cli",
        lambda **kwargs: run_calls.append(kwargs) or None,
    )

    result = generate_project_assets_service(
        project_dir,
        generate_images=False,
        generate_videos=True,
        generate_audio=False,
    )

    assert result["videos_generated"] == 1
    assert prompt_calls[0]["scene_uids"] == ["scene_001"]
    assert prompt_calls[0]["workspace_path"] == "/tmp/workspace"
    assert run_calls[0]["agent_name"] == "codex"
    assert saved_plans[-1]["scenes"][0]["video_path"] == str(tmp_path / "scene_001.mp4")


def test_generate_project_assets_service_runs_primary_only_review_and_text_repair(monkeypatch, tmp_path):
    project_dir = tmp_path / "demo_project"
    project_dir.mkdir()
    images_dir = project_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)
    drifted_image = images_dir / "image_scene_001_textfix.png"
    drifted_image.write_bytes(b"png-drifted")
    canonical_image = images_dir / "scene_001.png"

    plan_state = {
        "meta": {
            "brief": {},
            "image_profile": {
                "provider": "replicate",
                "generation_model": "demo-model",
                "edit_model": "qwen-image-edit-2511",
            },
            "video_profile": {"provider": "manual"},
            "tts_profile": {"provider": "kokoro", "voice": "af", "speed": 1.1},
        },
        "scenes": [
            {
                "id": 1,
                "uid": "scene_001",
                "title": "Gap slide",
                "scene_type": "image",
                "visual_prompt": 'Still slide with "Inconsistency".',
                "narration": "Call out the remaining gaps honestly.",
                "on_screen_text": ["Inconsistency in low-structure situations"],
                "manifestation_plan": {
                    "primary_path": "authored_image",
                    "fallback_path": "native_remotion",
                    "text_expected": True,
                    "text_critical": False,
                },
                "composition": {
                    "manifestation": "authored_image",
                    "family": "static_media",
                    "mode": "none",
                },
                "image_path": str(drifted_image),
                "judge_verdict": {
                    "winner": "primary",
                    "text_repairs": [],
                    "frame_refs": [{"path": "images/image_scene_001_textfix.png"}],
                },
                "candidate_outputs": {
                    "primary": {
                        "candidate_id": "primary",
                        "candidate_type": "authored_image",
                        "source_path": "images/image_scene_001_textfix.png",
                        "review_status": "winner",
                    }
                },
            }
        ],
    }

    review_calls: list[tuple[str, tuple[str, ...] | None, str]] = []
    edit_prompts: list[str] = []
    edited_image = images_dir / ".scene_001_textfix.png"
    edited_image.write_bytes(b"png-edit")

    def fake_load(_project_dir):
        return copy.deepcopy(plan_state)

    def fake_save(_project_dir, saved_plan):
        nonlocal plan_state
        plan_state = copy.deepcopy(saved_plan)
        return saved_plan

    def fake_review(_project_dir, *, trigger, scene_candidates=None, scene_uids=None):
        assert scene_candidates is not None
        candidate_source = scene_candidates["scene_001"][0]["source_path"]
        review_calls.append((trigger, tuple(scene_uids) if scene_uids else None, candidate_source))
        assert scene_candidates is not None
        assert list(scene_candidates) == ["scene_001"]
        assert len(scene_candidates["scene_001"]) == 1
        assert scene_candidates["scene_001"][0]["candidate_id"] == "primary"
        assert candidate_source == str(canonical_image.resolve())
        scene = plan_state["scenes"][0]
        scene["candidate_outputs"] = {
            "primary": {
                "candidate_id": "primary",
                "candidate_type": "authored_image",
                "source_path": str(canonical_image.resolve()),
                "review_status": "winner",
            }
        }
        if trigger == "post_asset_generation_review":
            scene["judge_verdict"] = {
                "winner": "primary",
                "text_repairs": [
                    {
                        "candidate_id": "primary",
                        "wrong_text": "Inconsitency",
                        "correct_text": "Inconsistency",
                        "reason": "Direct literal correction is safe.",
                    }
                ],
            }
        else:
            scene["judge_verdict"] = {
                "winner": "primary",
                "text_repairs": [],
            }
        return {"provider": "codex", "scene_count": 1, "review_dir": "/tmp/review", "scenes": []}

    monkeypatch.setattr("core.pipeline_service.load_plan", fake_load)
    monkeypatch.setattr("core.pipeline_service.save_plan", fake_save)
    monkeypatch.setattr("core.pipeline_service.resolve_image_profile", lambda profile=None: profile or {})
    monkeypatch.setattr("core.pipeline_service.resolve_video_profile", lambda profile=None: profile or {})
    monkeypatch.setattr("core.pipeline_service.resolve_tts_profile", lambda profile=None: profile or {})
    monkeypatch.setattr("core.pipeline_service.review_project_scenes", fake_review)
    monkeypatch.setattr(
        "core.pipeline_service.edit_image",
        lambda prompt, *_args, **_kwargs: edit_prompts.append(prompt) or edited_image,
    )

    result = generate_project_assets_service(
        project_dir,
        generate_images=False,
        generate_audio=False,
        generate_videos=False,
    )

    assert result["images_generated"] == 0
    assert review_calls == [
        ("post_asset_generation_review", None, str(canonical_image.resolve())),
        ("post_asset_exact_text_edit_review", ("scene_001",), str(canonical_image.resolve())),
        ("post_asset_review_after_repairs", None, str(canonical_image.resolve())),
    ]
    assert edit_prompts == ['change "Inconsitency" to "Inconsistency"']
    assert plan_state["scenes"][0]["image_path"] == str(canonical_image.resolve())
    assert plan_state["scenes"][0]["candidate_outputs"]["primary"]["source_path"] == str(canonical_image.resolve())
    assert canonical_image.exists()
    assert not drifted_image.exists()
    assert not edited_image.exists()
    assert result["scene_review"]["provider"] == "codex"
