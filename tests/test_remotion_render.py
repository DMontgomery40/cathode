from __future__ import annotations

from pathlib import Path

from core.remotion_render import (
    _progress_payload_from_remotion_event,
    build_remotion_manifest,
    motion_scene_is_ready,
    scene_has_renderable_visual,
)


def test_motion_scene_is_ready_from_template_only():
    scene = {
        "scene_type": "motion",
        "motion": {
            "template_id": "kinetic_title",
            "props": {
                "headline": "Prompts on prompts",
            },
        },
    }

    assert motion_scene_is_ready(scene) is True
    assert scene_has_renderable_visual(scene, render_backend="remotion") is True


def test_build_remotion_manifest_uses_api_media_urls_and_motion_templates(tmp_path):
    project_dir = tmp_path / "demo_project"
    (project_dir / "images").mkdir(parents=True)
    (project_dir / "audio").mkdir()
    (project_dir / "clips").mkdir()
    (project_dir / "images" / "scene_001.png").write_bytes(b"png")
    (project_dir / "clips" / "scene_002.mp4").write_bytes(b"mp4")
    (project_dir / "audio" / "scene_001.wav").write_bytes(b"wav")
    (project_dir / "audio" / "scene_002.wav").write_bytes(b"wav")
    (project_dir / "audio" / "scene_003.wav").write_bytes(b"wav")

    plan = {
        "meta": {
            "project_name": "demo_project",
            "brief": {"text_render_mode": "deterministic_overlay"},
            "render_profile": {"fps": 24, "render_backend": "remotion"},
        },
        "scenes": [
            {
                "uid": "scene_001",
                "id": 1,
                "scene_type": "image",
                "title": "Cover",
                "on_screen_text": ["One prompt", "Whole system"],
                "image_path": str(project_dir / "images" / "scene_001.png"),
                "audio_path": str(project_dir / "audio" / "scene_001.wav"),
            },
            {
                "uid": "scene_002",
                "id": 2,
                "scene_type": "video",
                "title": "App walkthrough",
                "video_path": str(project_dir / "clips" / "scene_002.mp4"),
                "video_audio_source": "clip",
                "audio_path": str(project_dir / "audio" / "scene_002.wav"),
                "video_trim_start": 1.5,
                "video_trim_end": 3.0,
                "video_playback_speed": 1.25,
            },
            {
                "uid": "scene_003",
                "id": 3,
                "scene_type": "motion",
                "title": "Prompt ladder",
                "audio_path": str(project_dir / "audio" / "scene_003.wav"),
                "motion": {
                    "template_id": "bullet_stack",
                    "props": {
                        "headline": "Prompts on prompts",
                        "bullets": ["Human prompt", "System prompt", "Agent prompt"],
                    },
                },
            },
        ],
    }

    manifest = build_remotion_manifest(
        project_dir=project_dir,
        plan=plan,
        output_path=project_dir / "demo_project.mp4",
        render_profile=plan["meta"]["render_profile"],
    )

    assert manifest["projectName"] == "demo_project"
    assert manifest["fps"] == 24
    assert manifest["textRenderMode"] == "deterministic_overlay"
    assert len(manifest["scenes"]) == 3
    assert manifest["scenes"][0]["imageUrl"].endswith("/api/projects/demo_project/media/images/scene_001.png")
    assert manifest["scenes"][0]["textLayerKind"] == "captions"
    assert manifest["scenes"][0]["sequenceDurationInFrames"] == manifest["scenes"][0]["durationInFrames"]
    assert manifest["scenes"][1]["videoUrl"].endswith("/api/projects/demo_project/media/clips/scene_002.mp4")
    assert manifest["scenes"][1]["audioUrl"] is None
    assert manifest["scenes"][1]["videoAudioSource"] == "clip"
    assert manifest["scenes"][1]["textLayerKind"] == "none"
    assert manifest["scenes"][1]["sequenceDurationInFrames"] == manifest["scenes"][1]["durationInFrames"]
    assert manifest["scenes"][1]["trimBeforeFrames"] == 36
    assert manifest["scenes"][1]["trimAfterFrames"] == 72
    assert manifest["scenes"][1]["composition"]["family"] == "static_media"
    assert manifest["scenes"][2]["motion"]["templateId"] == "bullet_stack"
    assert manifest["scenes"][2]["composition"]["family"] == "bullet_stack"
    assert manifest["scenes"][2]["composition"]["mode"] == "native"
    assert manifest["scenes"][2]["textLayerKind"] == "none"
    assert manifest["totalDurationInFrames"] >= sum(scene["durationInFrames"] for scene in manifest["scenes"])


def test_build_remotion_manifest_tracks_overlay_ownership_and_transition_safe_sequence_lengths(tmp_path):
    project_dir = tmp_path / "overlay_demo"
    (project_dir / "images").mkdir(parents=True)
    (project_dir / "audio").mkdir()
    (project_dir / "images" / "scene_001.png").write_bytes(b"png")
    (project_dir / "images" / "scene_002.png").write_bytes(b"png")
    (project_dir / "audio" / "scene_001.wav").write_bytes(b"wav")
    (project_dir / "audio" / "scene_002.wav").write_bytes(b"wav")

    plan = {
        "meta": {
            "project_name": "overlay_demo",
            "brief": {"text_render_mode": "deterministic_overlay"},
            "render_profile": {"fps": 24, "render_backend": "remotion"},
        },
        "scenes": [
            {
                "uid": "scene_001",
                "id": 1,
                "scene_type": "image",
                "title": "Hero still",
                "on_screen_text": ["Exact overlay copy"],
                "image_path": str(project_dir / "images" / "scene_001.png"),
                "audio_path": str(project_dir / "audio" / "scene_001.wav"),
                "composition": {
                    "family": "media_pan",
                    "mode": "overlay",
                    "transition_after": {"kind": "fade", "duration_in_frames": 20},
                },
            },
            {
                "uid": "scene_002",
                "id": 2,
                "scene_type": "image",
                "title": "Product proof",
                "on_screen_text": ["Pinned callout", "Readable when overlaid"],
                "image_path": str(project_dir / "images" / "scene_002.png"),
                "audio_path": str(project_dir / "audio" / "scene_002.wav"),
                "composition": {
                    "family": "software_demo_focus",
                    "mode": "native",
                    "props": {"headline": "Pinned callout"},
                },
            },
        ],
    }

    manifest = build_remotion_manifest(
        project_dir=project_dir,
        plan=plan,
        output_path=project_dir / "overlay_demo.mp4",
        render_profile=plan["meta"]["render_profile"],
    )

    first_scene, second_scene = manifest["scenes"]
    assert first_scene["textLayerKind"] == "captions"
    assert first_scene["sequenceDurationInFrames"] == first_scene["durationInFrames"] + 20
    assert second_scene["textLayerKind"] == "software_demo_focus"
    assert second_scene["sequenceDurationInFrames"] == second_scene["durationInFrames"]


def test_ffmpeg_motion_scene_accepts_rendered_preview_clip(tmp_path):
    preview_path = tmp_path / "previews" / "motion_scene.mp4"
    preview_path.parent.mkdir(parents=True)
    preview_path.write_bytes(b"mp4")

    scene = {
        "scene_type": "motion",
        "preview_path": str(preview_path),
        "motion": {
            "template_id": "kinetic_title",
            "preview_path": str(preview_path),
        },
    }

    assert scene_has_renderable_visual(scene, render_backend="ffmpeg") is True


def test_clinical_template_families_route_as_native_remotion_compositions(tmp_path):
    """All 10 clinical template families must produce native-mode manifest scenes.

    This guards the pipeline contract between the Python composition planner and
    the Remotion MotionTemplateRenderer switch statement in index.tsx.
    """
    clinical_families = [
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

    project_dir = tmp_path / "clinical_demo"
    (project_dir / "audio").mkdir(parents=True)

    scenes = []
    for idx, family in enumerate(clinical_families, start=1):
        uid = f"scene_{idx:03d}"
        audio = project_dir / "audio" / f"{uid}.wav"
        audio.write_bytes(b"wav")
        scenes.append(
            {
                "uid": uid,
                "id": idx,
                "scene_type": "motion",
                "title": f"Test {family}",
                "audio_path": str(audio),
                "motion": {
                    "template_id": family,
                    "props": {"headline": f"Headline for {family}"},
                },
                "composition": {
                    "family": family,
                    "mode": "native",
                    "props": {"headline": f"Headline for {family}"},
                },
            }
        )

    plan = {
        "meta": {
            "project_name": "clinical_demo",
            "brief": {"text_render_mode": "deterministic_overlay"},
            "render_profile": {"fps": 24, "render_backend": "remotion"},
        },
        "scenes": scenes,
    }

    manifest = build_remotion_manifest(
        project_dir=project_dir,
        plan=plan,
        output_path=project_dir / "clinical_demo.mp4",
        render_profile=plan["meta"]["render_profile"],
    )

    assert len(manifest["scenes"]) == len(clinical_families)
    for manifest_scene, expected_family in zip(manifest["scenes"], clinical_families):
        assert manifest_scene["composition"]["family"] == expected_family, (
            f"Expected family '{expected_family}', got '{manifest_scene['composition']['family']}'"
        )
        assert manifest_scene["composition"]["mode"] == "native", (
            f"Family '{expected_family}' should route as native, got '{manifest_scene['composition']['mode']}'"
        )
        assert manifest_scene["motion"]["templateId"] == expected_family
        assert manifest_scene["textLayerKind"] == "none", (
            f"Native motion family '{expected_family}' should suppress captions text layer"
        )
        assert manifest_scene["motion"]["props"]["headline"] == f"Headline for {expected_family}"


def test_remotion_index_typography_system_regression():
    """Structural regression test: index.tsx must declare the shared typography
    constants and no template composition outside ThreeDataStage should use
    hardcoded font-family strings.

    This does not require a DOM or React runtime -- it reads the source file
    directly to verify the typographic system was applied.
    """
    import re

    index_path = Path(__file__).resolve().parent.parent / "frontend" / "src" / "remotion" / "index.tsx"
    if not index_path.exists():
        # CI environments may not have the frontend tree; skip gracefully.
        return

    source = index_path.read_text()

    # 1. Typography constants must be declared
    for const in ["FONT_HEADLINE", "FONT_BODY", "FONT_DATA", "FONT_CAPTION"]:
        assert f"const {const}" in source, f"Missing typography constant declaration: {const}"

    for const in ["HEADLINE_MAX_SIZE", "BODY_SIZE", "CAPTION_SIZE", "LABEL_SIZE"]:
        assert f"const {const}" in source, f"Missing size constant declaration: {const}"

    # 2. Responsive sizing hooks must be declared
    assert "function useHeadlineFontSize" in source, "Missing useHeadlineFontSize hook"
    assert "function useBodyFontSize" in source, "Missing useBodyFontSize hook"

    # 3. fitText imports must be present
    assert "fitText" in source, "Missing fitText import"
    assert "fitTextOnNLines" in source, "Missing fitTextOnNLines import"

    # 4. No hardcoded font-family strings outside the ThreeDataStage zone.
    #    The ThreeDataStage ecosystem includes its helper types, utility functions,
    #    and PanelMiniChart.  We bracket the zone by:
    #      start: the "type DataStagePoint" type declaration (first data-stage type)
    #      end:   the "function normalizePaletteWords" declaration (start of Surreal zone)
    #    ThreeDataStage has its own internal font choices that this overhaul
    #    intentionally does not touch.
    zone_start_marker = "type DataStagePoint"
    zone_end_marker = "function normalizePaletteWords"

    three_start = source.find(zone_start_marker)
    three_end = source.find(zone_end_marker)
    if three_end == -1:
        three_end = len(source)

    # Build the non-ThreeDataStage source regions
    if three_start >= 0:
        non_three_source = source[:three_start] + source[three_end:]
    else:
        non_three_source = source

    # Font family patterns that should be replaced by constants.
    # We check for inline fontFamily assignments with literal string values
    # that are NOT our constant references.
    hardcoded_font_pattern = re.compile(
        r"fontFamily:\s*['\"](?!FONT_)"  # fontFamily: 'something' or "something"
    )
    violations = []
    for m in hardcoded_font_pattern.finditer(non_three_source):
        # Get the line number for the match
        line_num = non_three_source[:m.start()].count('\n') + 1
        context = non_three_source[m.start():m.start() + 80]
        violations.append(f"  line ~{line_num}: {context.strip()}")

    assert not violations, (
        f"Found {len(violations)} hardcoded fontFamily string(s) outside ThreeDataStage zone:\n"
        + "\n".join(violations)
    )


def test_progress_payload_maps_remotion_events_to_render_job_updates():
    status_payload = _progress_payload_from_remotion_event(
        {
            "type": "status",
            "stage": "render",
            "label": "Starting Remotion render",
            "detail": "codec=h264 hwaccel=required",
        }
    )
    progress_payload = _progress_payload_from_remotion_event(
        {
            "type": "progress",
            "stage": "encoding",
            "progress": 0.42,
            "renderedFrames": 120,
            "encodedFrames": 98,
        }
    )

    assert status_payload["progress_label"] == "Starting Remotion render"
    assert status_payload["progress_detail"] == "codec=h264 hwaccel=required"
    assert progress_payload["progress_label"] == "Encoding video"
    assert progress_payload["progress_detail"] == "rendered 120 frames, encoded 98"
    assert progress_payload["progress"] == 0.42


def test_template_background_resolved_for_native_clinical_scenes(tmp_path):
    """Native clinical template scenes with no image_path should get a template_deck background URL."""
    import shutil
    from core.runtime import REPO_ROOT

    # Ensure the background file exists in the repo (should already exist)
    bg_path = REPO_ROOT / "template_deck" / "backgrounds" / "cover_hook.png"
    if not bg_path.exists():
        bg_path.parent.mkdir(parents=True, exist_ok=True)
        bg_path.write_bytes(b"fake-png")

    project_dir = tmp_path / "bg_test"
    (project_dir / "audio").mkdir(parents=True)
    (project_dir / "audio" / "s1.wav").write_bytes(b"wav")

    plan = {
        "meta": {
            "project_name": "bg_test",
            "brief": {"text_render_mode": "deterministic_overlay"},
            "render_profile": {"fps": 24, "render_backend": "remotion"},
        },
        "scenes": [
            {
                "uid": "s1",
                "id": 1,
                "scene_type": "motion",
                "title": "Cover",
                "audio_path": str(project_dir / "audio" / "s1.wav"),
                "on_screen_text": ["Your Report", "Overview", "Clinic"],
                "composition": {
                    "family": "cover_hook",
                    "mode": "native",
                    "props": {"headline": "Your Report"},
                },
                "motion": {
                    "template_id": "cover_hook",
                    "props": {"headline": "Your Report"},
                },
            },
        ],
    }

    manifest = build_remotion_manifest(
        project_dir=project_dir,
        plan=plan,
        output_path=project_dir / "bg_test.mp4",
        render_profile=plan["meta"]["render_profile"],
    )

    scene = manifest["scenes"][0]
    assert scene["imageUrl"] is not None, "imageUrl should be resolved from template_deck"
    assert "template-deck" in scene["imageUrl"]
    assert "cover_hook" in scene["imageUrl"]


def test_authored_image_no_captions_overlay(tmp_path):
    """Static media scenes with authored_image manifestation should not get captions overlay."""
    project_dir = tmp_path / "authored_test"
    (project_dir / "images").mkdir(parents=True)
    (project_dir / "audio").mkdir()
    img = project_dir / "images" / "authored.png"
    img.write_bytes(b"png")
    (project_dir / "audio" / "s1.wav").write_bytes(b"wav")

    plan = {
        "meta": {
            "project_name": "authored_test",
            "brief": {"text_render_mode": "deterministic_overlay"},
            "render_profile": {"fps": 24, "render_backend": "remotion"},
        },
        "scenes": [
            {
                "uid": "s1",
                "id": 1,
                "scene_type": "image",
                "title": "Authored Scene",
                "image_path": str(img),
                "audio_path": str(project_dir / "audio" / "s1.wav"),
                "on_screen_text": ["Text baked into image"],
                "composition": {
                    "family": "static_media",
                    "mode": "none",
                    "manifestation": "authored_image",
                },
            },
        ],
    }

    manifest = build_remotion_manifest(
        project_dir=project_dir,
        plan=plan,
        output_path=project_dir / "authored_test.mp4",
        render_profile=plan["meta"]["render_profile"],
    )

    scene = manifest["scenes"][0]
    assert scene["textLayerKind"] == "none", (
        f"Authored images with baked text should not get captions overlay, got '{scene['textLayerKind']}'"
    )


def test_manifest_enriches_clinical_props_at_build_time(tmp_path):
    """Plans created before enrichment code should get enriched props at manifest build time.

    Covers: timeline_progression (markers from onScreenText), metric_improvement (stages
    from data_points), brain_region_focus (regions from data_points).
    """
    project_dir = tmp_path / "enrich_test"
    (project_dir / "audio").mkdir(parents=True)

    # timeline_progression: headline-only props, on_screen_text has session markers
    (project_dir / "audio" / "s1.wav").write_bytes(b"wav")
    # metric_improvement: headline-only props, data_points have session values
    (project_dir / "audio" / "s2.wav").write_bytes(b"wav")
    # brain_region_focus: headline-only props, data_points have region info
    (project_dir / "audio" / "s3.wav").write_bytes(b"wav")

    plan = {
        "meta": {
            "project_name": "enrich_test",
            "brief": {"text_render_mode": "deterministic_overlay"},
            "render_profile": {"fps": 24, "render_backend": "remotion"},
        },
        "scenes": [
            {
                "uid": "s1",
                "id": 1,
                "scene_type": "motion",
                "title": "Session Timeline",
                "audio_path": str(project_dir / "audio" / "s1.wav"),
                "on_screen_text": [
                    "Session Timeline",
                    "Session 1 -- 01/15",
                    "Session 2 -- 02/12",
                    "Session 3 -- 03/10",
                ],
                "composition": {
                    "family": "timeline_progression",
                    "mode": "native",
                    "props": {"headline": "Session Timeline"},
                },
            },
            {
                "uid": "s2",
                "id": 2,
                "scene_type": "motion",
                "title": "Alpha Power",
                "audio_path": str(project_dir / "audio" / "s2.wav"),
                "on_screen_text": ["Alpha Power Improvement"],
                "data_points": [
                    "Session 1: 8.2 uV",
                    "Session 2: 9.1 uV",
                    "Session 3: 10.4 uV",
                ],
                "composition": {
                    "family": "metric_improvement",
                    "mode": "native",
                    "props": {"headline": "Alpha Power Improvement"},
                    "data": {
                        "data_points": [
                            "Session 1: 8.2 uV",
                            "Session 2: 9.1 uV",
                            "Session 3: 10.4 uV",
                        ],
                    },
                },
            },
            {
                "uid": "s3",
                "id": 3,
                "scene_type": "motion",
                "title": "Brain Regions",
                "audio_path": str(project_dir / "audio" / "s3.wav"),
                "on_screen_text": ["Brain Region Overview"],
                "composition": {
                    "family": "brain_region_focus",
                    "mode": "native",
                    "props": {"headline": "Brain Region Overview"},
                    "data": {
                        "data_points": [
                            "Frontal: 12.3 uV improved",
                            "Central: 8.1 uV stable",
                        ],
                    },
                },
            },
        ],
    }

    manifest = build_remotion_manifest(
        project_dir=project_dir,
        plan=plan,
        output_path=project_dir / "enrich_test.mp4",
        render_profile=plan["meta"]["render_profile"],
    )

    # timeline_progression should have markers enriched from on_screen_text
    timeline = manifest["scenes"][0]
    markers = timeline["composition"]["props"].get("markers", [])
    assert len(markers) >= 3, f"Expected >= 3 markers from onScreenText, got {len(markers)}"
    assert markers[0]["label"] == "Session 1"

    # metric_improvement with session labels gets rerouted to three_data_stage
    metric = manifest["scenes"][1]
    assert metric["composition"]["family"] == "three_data_stage", (
        f"Expected reroute to three_data_stage, got {metric['composition']['family']}"
    )
    series = metric["composition"].get("data", {}).get("series", [])
    assert len(series) >= 1, f"Expected >= 1 series from data_points, got {len(series)}"
    points = series[0].get("points", [])
    assert any(p.get("y") is not None for p in points), "Expected real y values in series"

    # brain_region_focus should have regions enriched from data_points
    brain = manifest["scenes"][2]
    regions = brain["composition"]["props"].get("regions", [])
    assert len(regions) >= 2, f"Expected >= 2 regions from data_points, got {len(regions)}"
    assert "Frontal" in regions[0].get("name", "")
