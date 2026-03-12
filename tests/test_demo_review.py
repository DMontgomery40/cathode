from __future__ import annotations

from core.demo_review import (
    build_review_observation_template,
    build_review_report,
    choose_retry_actions,
    normalize_review_observations,
    rank_training_runs,
)


def test_normalize_review_observations_returns_stable_schema():
    report = normalize_review_observations(
        {
            "decision": "warn",
            "summary": "Readable, but the chosen run is not ideal.",
            "recommended_clip_id": "review_clip",
            "clip_assessments": [
                {
                    "clip_id": "review_clip",
                    "recommended": True,
                    "notes": "Good frame, weak state.",
                    "framing": "good",
                    "legibility": "good",
                    "theme": "good",
                    "artifact_dominance": "strong",
                    "state_quality": "weak",
                    "crop_quality": "better",
                }
            ],
            "issues": [{"code": "weak_primary_state", "severity": "warn", "message": "Pick a stronger run."}],
        }
    )

    assert report["decision"] == "warn"
    assert report["recommended_clip_id"] == "review_clip"
    assert report["clip_assessments"][0]["state_quality"] == "weak"
    assert report["issues"][0]["code"] == "weak_primary_state"


def test_build_review_observation_template_seeds_clip_metadata_and_frames():
    template = build_review_observation_template(
        {
            "clips": [
                {"id": "run_review", "label": "Run review overlay", "kind": "video_clip"},
                {"id": "final_render", "label": "Final render", "kind": "final_video"},
            ]
        },
        review_frames_manifest={
            "items": [
                {
                    "clip_id": "run_review",
                    "label": "Run review overlay",
                    "kind": "video_clip",
                    "frame_paths": ["/tmp/run_review/frame_01.jpg", "/tmp/run_review/frame_02.jpg"],
                },
                {
                    "clip_id": "final_render",
                    "label": "Final render",
                    "kind": "final_video",
                    "frame_paths": ["/tmp/final_render/frame_01.jpg"],
                },
            ]
        },
        raw_feedback_path="/tmp/reports/subagent_qc_raw.md",
    )

    assert template["decision"] == "retry"
    assert template["raw_feedback_path"] == "/tmp/reports/subagent_qc_raw.md"
    assert [item["clip_id"] for item in template["clip_assessments"]] == ["run_review", "final_render"]
    assert template["clip_assessments"][0]["reference_frames"] == [
        "/tmp/run_review/frame_01.jpg",
        "/tmp/run_review/frame_02.jpg",
    ]
    assert template["clip_assessments"][1]["kind"] == "final_video"


def test_choose_retry_actions_maps_review_failures_to_bounded_actions():
    actions = choose_retry_actions(
        {
            "decision": "retry",
            "clip_assessments": [
                {
                    "clip_id": "review_clip",
                    "framing": "weak",
                    "legibility": "good",
                    "theme": "mixed",
                    "artifact_dominance": "weak",
                    "state_quality": "weak",
                    "crop_quality": "worse",
                }
            ],
            "issues": [{"code": "weak_primary_state", "severity": "warn", "message": "Pick a better run."}],
        }
    )

    assert actions == ["switch_theme", "expand_viewport", "refocus_crop"]


def test_rank_training_runs_prefers_completed_nonzero_and_warns_on_bad_states():
    ranked = rank_training_runs(
        [
            {"run_id": "completed_zero", "status": "completed", "metrics": {"mAP50": 0.0, "mAP50_95": 0.0}},
            {"run_id": "failed_stronger", "status": "failed", "metrics": {"mAP50": 0.24, "mAP50_95": 0.13}},
            {"run_id": "completed_good", "status": "completed", "metrics": {"mAP50": 0.21, "mAP50_95": 0.11}},
        ]
    )

    assert ranked[0]["run_id"] == "completed_good"
    failed = next(item for item in ranked if item["run_id"] == "failed_stronger")
    zero = next(item for item in ranked if item["run_id"] == "completed_zero")
    assert "failed" in failed["hero_warning"].lower()
    assert "zero" in zero["hero_warning"].lower()


def test_build_review_report_downgrades_accept_for_weak_training_hero():
    report = build_review_report(
        {
            "clips": [
                {
                    "id": "training_clip",
                    "training_runs": [
                        {
                            "run_id": "completed_zero",
                            "selected": True,
                            "status": "completed",
                            "metrics": {"mAP50": 0.0, "mAP50_95": 0.0},
                        }
                    ],
                }
            ]
        },
        {
            "decision": "accept",
            "recommended_clip_id": "training_clip",
            "summary": "Looks good.",
            "clip_assessments": [{"clip_id": "training_clip", "recommended": True}],
            "issues": [],
        },
    )

    assert report["decision"] == "warn"
    assert any(issue["code"] == "zero_metric_hero" for issue in report["issues"])
