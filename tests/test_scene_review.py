from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from core.project_store import load_plan, save_plan
from core.scene_review import (
    auto_scene_review_candidates,
    build_scene_review_request,
    choose_scene_judge_provider,
    _parse_scene_judge_json_output,
    _run_codex_scene_judge,
    _scene_review_schema,
    prepare_scene_review_candidates,
    review_project_scenes,
    scene_judge_providers,
)

_TINY_PNG_BYTES = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc````\xf8\xcf"
    b"\xc0\x00\x00\x04\x00\x01\x93\xdd\xb7\x9f\x00\x00\x00\x00IEND\xaeB`\x82"
)


def _write_png(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(_TINY_PNG_BYTES)
    return path


def test_scene_judge_providers_follow_locked_order(monkeypatch):
    monkeypatch.setattr(
        "core.scene_review.check_api_keys",
        lambda: {"openai": True},
    )
    monkeypatch.setattr(
        "core.scene_review.shutil.which",
        lambda name: {
            "codex": "/usr/local/bin/codex",
            "claude": "/usr/local/bin/claude",
        }.get(name),
    )

    providers = scene_judge_providers()

    assert [provider["provider"] for provider in providers] == ["codex", "claude_code", "openai_api"]
    assert providers[0]["builtin_runner"] is True
    assert providers[1]["available"] is True
    assert providers[1]["builtin_runner"] is False
    assert "not guess a local-image attachment contract" in providers[1]["reason"]
    assert providers[2]["model"] == "gpt-5.4"
    assert providers[2]["reasoning_effort"] == "xhigh"


def test_choose_scene_judge_provider_respects_external_runner_gate(monkeypatch):
    monkeypatch.setattr(
        "core.scene_review.check_api_keys",
        lambda: {"openai": True},
    )
    monkeypatch.setattr(
        "core.scene_review.shutil.which",
        lambda name: {
            "claude": "/usr/local/bin/claude",
        }.get(name),
    )

    assert choose_scene_judge_provider()["provider"] == "openai_api"
    assert choose_scene_judge_provider(allow_external_runner=True)["provider"] == "claude_code"


def test_prepare_scene_review_candidates_reuses_image_for_required_roles(tmp_path):
    project_dir = tmp_path / "demo_project"
    image_path = _write_png(project_dir / "images" / "scene_001.png")
    scene = {
        "uid": "scene_001",
        "id": 0,
        "scene_type": "image",
        "title": "Cover",
        "narration": "Introduce the deck.",
        "visual_prompt": "Minimal cover slide.",
        "image_path": str(image_path),
    }

    prepared = prepare_scene_review_candidates(project_dir, scene)
    request = build_scene_review_request(scene, prepared_candidates=prepared, trigger="post_render_review")

    assert len(prepared) == 1
    assert [frame["frame_role"] for frame in prepared[0]["frame_refs"]] == [
        "first_stable_readable",
        "midpoint",
    ]
    assert all(frame["absolute_path"] == str(image_path.resolve()) for frame in prepared[0]["frame_refs"])
    assert request["review_mode"] == "single"
    assert [item["frame_role"] for item in request["attachments"]] == [
        "first_stable_readable",
        "midpoint",
    ]
    assert "Do not use OCR" in request["prompt"]


def test_auto_scene_review_candidates_builds_native_fallback_for_authored_image_scene(tmp_path, monkeypatch):
    project_dir = tmp_path / "demo_project"
    image_path = _write_png(project_dir / "images" / "scene_001.png")
    plan = {
        "meta": {
            "project_name": "demo_project",
            "render_profile": {"render_backend": "remotion", "fps": 24},
        },
        "scenes": [],
    }
    scene = {
        "uid": "scene_001",
        "id": 0,
        "scene_type": "image",
        "title": "Cover",
        "narration": "Introduce the deck.",
        "visual_prompt": 'Illustrated still with title "Hello".',
        "image_path": str(image_path),
        "manifestation_plan": {
            "primary_path": "authored_image",
            "fallback_path": "native_remotion",
            "native_family_hint": "bullet_stack",
            "native_build_prompt": "Native build: bold stacked headline with exact visible words.",
        },
        "composition": {
            "family": "static_media",
            "mode": "none",
            "manifestation": "authored_image",
        },
    }
    plan["scenes"] = [scene]

    captured: dict[str, object] = {}

    def fake_build_manifest(*, project_dir, plan, output_path, render_profile, preview_scene_uid=None):
        captured["scene_type"] = plan["scenes"][0]["scene_type"]
        captured["family"] = plan["scenes"][0]["composition"]["family"]
        captured["manifestation"] = plan["scenes"][0]["composition"]["manifestation"]
        captured["preview_scene_uid"] = preview_scene_uid
        return {"outputPath": str(output_path)}

    def fake_render_manifest(manifest, output_path):
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"mp4")
        return output_path

    monkeypatch.setattr("core.scene_review.build_remotion_manifest", fake_build_manifest)
    monkeypatch.setattr("core.scene_review.render_manifest_with_remotion", fake_render_manifest)

    candidates = auto_scene_review_candidates(project_dir, plan, scene, review_root=project_dir / ".cathode" / "scene_review" / "test-run")

    assert [candidate["candidate_id"] for candidate in candidates] == ["authored_image", "native_remotion"]
    assert candidates[0]["source_path"] == str(image_path.resolve())
    assert candidates[1]["source_path"].endswith("native_remotion_preview.mp4")
    assert captured["scene_type"] == "motion"
    assert captured["family"] == "bullet_stack"
    assert captured["manifestation"] == "native_remotion"
    assert captured["preview_scene_uid"] == "scene_001"


def test_auto_scene_review_candidates_builds_authored_image_fallback_for_native_scene(tmp_path, monkeypatch):
    project_dir = tmp_path / "demo_project"
    plan = {
        "meta": {
            "project_name": "demo_project",
            "brief": {"source_material": "Deck"},
            "image_profile": {"provider": "local", "generation_model": "Qwen/Qwen-Image-2512"},
        },
        "scenes": [],
    }
    scene = {
        "uid": "scene_001",
        "id": 0,
        "scene_type": "motion",
        "title": "Proof beat",
        "narration": "Use an exact deterministic statement.",
        "visual_prompt": 'Premium still with exact title "Proof".',
        "manifestation_plan": {
            "primary_path": "native_remotion",
            "fallback_path": "authored_image",
        },
        "composition": {
            "family": "bullet_stack",
            "mode": "native",
            "manifestation": "native_remotion",
            "render_path": str(project_dir / "renders" / "scene_001.mp4"),
        },
        "motion": {
            "template_id": "bullet_stack",
            "render_path": str(project_dir / "renders" / "scene_001.mp4"),
        },
    }
    Path(scene["composition"]["render_path"]).parent.mkdir(parents=True, exist_ok=True)
    Path(scene["composition"]["render_path"]).write_bytes(b"mp4")
    plan["scenes"] = [scene]

    def fake_generate_scene_image(scene_arg, review_project_dir, brief=None, provider="replicate", model=""):
        assert scene_arg["visual_prompt"] == 'Premium still with exact title "Proof".'
        assert provider == "local"
        output_path = Path(review_project_dir) / "images" / "scene_000.png"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"png")
        return output_path

    monkeypatch.setattr("core.scene_review.generate_scene_image", fake_generate_scene_image)

    candidates = auto_scene_review_candidates(project_dir, plan, scene, review_root=project_dir / ".cathode" / "scene_review" / "test-run")

    assert [candidate["candidate_id"] for candidate in candidates] == ["native_remotion", "authored_image"]
    assert candidates[0]["source_path"].endswith("scene_001.mp4")
    assert candidates[1]["source_path"].endswith("scene_000.png")


@pytest.mark.skipif(
    shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None,
    reason="ffmpeg and ffprobe are required",
)
def test_prepare_scene_review_candidates_extracts_first_stable_and_midpoint_video_frames(tmp_path):
    project_dir = tmp_path / "video_project"
    source_video = project_dir / "clips" / "scene_001.mp4"
    source_video.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "testsrc=size=640x360:rate=24:duration=2",
            "-pix_fmt",
            "yuv420p",
            str(source_video),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    scene = {
        "uid": "scene_001",
        "id": 0,
        "scene_type": "video",
        "title": "Walkthrough",
        "narration": "Show the product state.",
        "visual_prompt": "Use the saved success state.",
        "video_path": str(source_video),
    }

    prepared = prepare_scene_review_candidates(
        project_dir,
        scene,
        candidates=[
            {
                "candidate_id": "primary",
                "label": "Primary render",
                "source_path": str(source_video),
                "first_stable_timestamp_seconds": 0.4,
            }
        ],
        review_root=project_dir / ".cathode" / "scene_review" / "test-run",
    )

    frame_refs = prepared[0]["frame_refs"]
    assert [frame["frame_role"] for frame in frame_refs] == ["first_stable_readable", "midpoint"]
    assert frame_refs[0]["timestamp_seconds"] == pytest.approx(0.4)
    assert frame_refs[1]["timestamp_seconds"] == pytest.approx(1.0, abs=0.01)
    assert all(Path(frame["absolute_path"]).exists() for frame in frame_refs)


def test_review_project_scenes_persists_judge_verdict_metadata_for_full_deck(tmp_path, monkeypatch):
    project_dir = tmp_path / "review_project"
    primary_scene_image = _write_png(project_dir / "images" / "scene_001.png")
    ffmpeg_candidate = _write_png(project_dir / "images" / "scene_001_ffmpeg.png")
    remotion_candidate = _write_png(project_dir / "images" / "scene_001_remotion.png")
    second_scene_image = _write_png(project_dir / "images" / "scene_002.png")

    save_plan(
        project_dir,
        {
            "meta": {
                "project_name": "review_project",
                "brief": {"source_material": "Demo review deck"},
            },
            "scenes": [
                {
                    "uid": "scene_001",
                    "title": "Scene one",
                    "narration": "Compare two rendered candidates.",
                    "visual_prompt": "A clean summary slide.",
                    "scene_type": "image",
                    "image_path": str(primary_scene_image),
                },
                {
                    "uid": "scene_002",
                    "title": "Scene two",
                    "narration": "Review the current primary slide.",
                    "visual_prompt": "A readable proof slide.",
                    "scene_type": "image",
                    "image_path": str(second_scene_image),
                },
            ],
        },
    )

    monkeypatch.setattr(
        "core.scene_review.check_api_keys",
        lambda: {"openai": True},
    )
    monkeypatch.setattr(
        "core.scene_review.shutil.which",
        lambda name: {
            "claude": "/usr/local/bin/claude",
        }.get(name),
    )

    seen_uids: list[str] = []

    def fake_judge(provider: dict[str, str], request: dict[str, object]) -> dict[str, object]:
        seen_uids.append(str(request["scene"]["uid"]))
        assert provider["provider"] == "claude_code"
        if request["scene"]["uid"] == "scene_001":
            assert request["review_mode"] == "compare"
            assert [candidate["candidate_id"] for candidate in request["candidates"]] == ["ffmpeg", "remotion"]
            return {
                "winner": "remotion",
                "reasons": ["Cleaner spacing and a more stable visual hierarchy."],
                "candidate_notes": {
                    "ffmpeg": ["Feels more cramped at the readable frame."],
                    "remotion": ["Cleaner and easier to scan in both frames."],
                },
            }
        return {
            "winner": "primary",
            "reasons": ["Readable and stable across the required review frames."],
            "candidate_notes": {
                "primary": ["Single candidate remains acceptable."],
            },
        }

    result = review_project_scenes(
        project_dir,
        trigger="post_render_review",
        scene_candidates={
            "scene_001": [
                {
                    "candidate_id": "ffmpeg",
                    "label": "FFmpeg candidate",
                    "source_path": str(ffmpeg_candidate),
                },
                {
                    "candidate_id": "remotion",
                    "label": "Remotion candidate",
                    "source_path": str(remotion_candidate),
                },
            ]
        },
        judge_runner=fake_judge,
    )

    plan = load_plan(project_dir)
    assert plan is not None
    first_scene, second_scene = plan["scenes"]

    assert seen_uids == ["scene_001", "scene_002"]
    assert result["provider"] == "claude_code"
    assert result["scene_count"] == 2
    assert Path(result["review_dir"]).exists()
    assert Path(result["review_dir"] , "scenes", "scene_001", "request.json").exists()
    assert Path(result["review_dir"] , "scenes", "scene_001", "response.json").exists()

    first_verdict = first_scene["judge_verdict"]
    assert first_verdict["trigger"] == "post_render_review"
    assert first_verdict["judge_provider"] == "claude_code"
    assert first_verdict["judge_model"] == "local-default"
    assert first_verdict["provider"] == "claude_code"
    assert first_verdict["model"] == "local-default"
    assert first_verdict["winner"] == "remotion"
    assert "Cleaner spacing" in first_verdict["reasons"][0]
    assert first_verdict["candidate_notes"]["ffmpeg"] == ["Feels more cramped at the readable frame."]
    assert first_verdict["candidate_notes"]["remotion"] == ["Cleaner and easier to scan in both frames."]
    assert {(item["candidate_id"], item["frame_role"]) for item in first_verdict["frame_refs"]} == {
        ("ffmpeg", "first_stable_readable"),
        ("ffmpeg", "midpoint"),
        ("remotion", "first_stable_readable"),
        ("remotion", "midpoint"),
    }
    assert first_scene["candidate_outputs"]["ffmpeg"]["review_status"] == "rejected"
    assert first_scene["candidate_outputs"]["remotion"]["review_status"] == "winner"
    assert first_scene["candidate_outputs"]["remotion"]["source_path"].endswith("scene_001_remotion.png")

    second_verdict = second_scene["judge_verdict"]
    assert second_verdict["winner"] == "primary"
    assert second_verdict["candidate_notes"]["primary"] == ["Single candidate remains acceptable."]
    assert second_scene["candidate_outputs"]["primary"]["review_status"] == "winner"
    assert {(item["candidate_id"], item["frame_role"]) for item in second_verdict["frame_refs"]} == {
        ("primary", "first_stable_readable"),
        ("primary", "midpoint"),
    }

    request_payload = json.loads((Path(result["review_dir"]) / "scenes" / "scene_001" / "request.json").read_text())
    assert request_payload["review_mode"] == "compare"


def test_normalize_scene_judge_response_keeps_structured_text_repairs():
    from core.scene_review import normalize_scene_judge_response

    normalized = normalize_scene_judge_response(
        {
            "winner": "primary",
            "reasons": ["Readable enough overall."],
            "candidate_notes": {"primary": ["Visible typo in the hero word."]},
            "text_repairs": [
                {
                    "candidate_id": "primary",
                    "wrong_text": "Mongogmery",
                    "correct_text": "Montgomery",
                    "reason": "Direct literal correction is safe.",
                }
            ],
        },
        candidate_ids=["primary"],
    )

    assert normalized["winner"] == "primary"
    assert normalized["text_repairs"] == [
        {
            "candidate_id": "primary",
            "wrong_text": "Mongogmery",
            "correct_text": "Montgomery",
            "reason": "Direct literal correction is safe.",
        }
    ]


def test_scene_review_schema_requires_every_declared_property():
    schema = _scene_review_schema()

    assert sorted(schema["required"]) == sorted(schema["properties"].keys())


def test_parse_scene_judge_json_output_extracts_wrapped_json():
    payload = _parse_scene_judge_json_output(
        """
        Final answer:

        ```json
        {
          "winner": "primary",
          "reasons": ["Readable slide."],
          "candidate_notes": {"primary": ["Text looks stable."]},
          "text_repairs": []
        }
        ```
        """
    )

    assert payload["winner"] == "primary"
    assert payload["text_repairs"] == []


def test_run_codex_scene_judge_uses_output_file_without_output_schema(monkeypatch, tmp_path):
    image_path = _write_png(tmp_path / "scene.png")
    seen: dict[str, object] = {}

    def fake_run(command, *, input, text, capture_output, check):
        seen["command"] = command
        seen["input"] = input
        assert text is True
        assert capture_output is True
        assert check is False
        output_path = Path(command[command.index("-o") + 1])
        output_path.write_text(
            """
            Here is the result.
            {
              "winner": "primary",
              "reasons": ["Readable slide."],
              "candidate_notes": {"primary": ["Text looks stable."]},
              "text_repairs": []
            }
            """,
            encoding="utf-8",
        )
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr("core.scene_review.subprocess.run", fake_run)

    response = _run_codex_scene_judge(
        {
            "provider": "codex",
            "model": "local-default",
            "binary_path": "/usr/local/bin/codex",
        },
        {
            "prompt": "Judge the attached slide images.",
            "attachments": [
                {
                    "absolute_path": str(image_path),
                    "candidate_id": "primary",
                    "candidate_label": "primary",
                    "frame_role": "first_stable_readable",
                    "timestamp_seconds": 0.0,
                }
            ],
        },
    )

    command = seen["command"]
    assert isinstance(command, list)
    assert command[:2] == ["/usr/local/bin/codex", "exec"]
    assert "--output-schema" not in command
    assert command.count("-o") == 1
    assert command.count("-i") == 1
    assert str(image_path) in command
    assert "Return a single valid JSON object only. Do not add commentary." in str(seen["input"])
    assert response["winner"] == "primary"
