"""Structured review helpers for live demo capture bundles."""

from __future__ import annotations

import copy
from typing import Any

REVIEW_DECISIONS = {"accept", "warn", "retry"}
RETRY_ACTIONS = {
    "switch_theme",
    "expand_viewport",
    "collapse_sidebar",
    "pick_better_state",
    "refocus_crop",
}
DEFAULT_RETRY_ACTION_ORDER = [
    "switch_theme",
    "expand_viewport",
    "collapse_sidebar",
    "pick_better_state",
    "refocus_crop",
]

_STATUS_WEIGHTS = {
    "completed": 60,
    "succeeded": 60,
    "partial_success": 40,
    "running": 10,
    "queued": 5,
    "failed": -30,
    "cancelled": -40,
}


def _safe_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _review_frame_index(review_frames_manifest: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    items = review_frames_manifest.get("items") if isinstance(review_frames_manifest, dict) else []
    indexed: dict[str, dict[str, Any]] = {}
    for item in items or []:
        if not isinstance(item, dict):
            continue
        clip_id = str(item.get("clip_id") or "").strip()
        if not clip_id:
            continue
        indexed[clip_id] = item
    return indexed


def build_review_observation_template(
    bundle_manifest: dict[str, Any],
    *,
    review_frames_manifest: dict[str, Any] | None = None,
    raw_feedback_path: str = "",
) -> dict[str, Any]:
    """Seed a parent-agent editable observations template from bundle metadata."""
    manifest = bundle_manifest if isinstance(bundle_manifest, dict) else {}
    clips = manifest.get("clips") if isinstance(manifest.get("clips"), list) else []
    frame_index = _review_frame_index(review_frames_manifest)

    ordered_clip_ids: list[str] = []
    by_clip_id: dict[str, dict[str, Any]] = {}

    for clip in clips:
        if not isinstance(clip, dict):
            continue
        clip_id = str(clip.get("id") or clip.get("clip_id") or "").strip()
        if not clip_id:
            continue
        ordered_clip_ids.append(clip_id)
        by_clip_id[clip_id] = clip

    for clip_id in frame_index:
        if clip_id not in by_clip_id:
            ordered_clip_ids.append(clip_id)
            by_clip_id[clip_id] = {}

    assessments: list[dict[str, Any]] = []
    for clip_id in ordered_clip_ids:
        clip = by_clip_id.get(clip_id, {})
        frame_item = frame_index.get(clip_id, {})
        assessments.append(
            {
                "clip_id": clip_id,
                "label": str(frame_item.get("label") or clip.get("label") or clip_id).strip() or clip_id,
                "kind": str(frame_item.get("kind") or clip.get("kind") or "video_clip").strip() or "video_clip",
                "reference_frames": [str(path) for path in (frame_item.get("frame_paths") or []) if str(path).strip()],
                "recommended": False,
                "notes": "",
                "framing": "unknown",
                "legibility": "unknown",
                "theme": "unknown",
                "artifact_dominance": "unknown",
                "state_quality": "unknown",
                "crop_quality": "unknown",
            }
        )

    return {
        "decision": "retry",
        "summary": "",
        "recommended_clip_id": "",
        "raw_feedback_path": str(raw_feedback_path or "").strip(),
        "clip_assessments": assessments,
        "issues": [],
    }


def normalize_review_observations(payload: Any) -> dict[str, Any]:
    """Normalize a reviewer-authored payload into a stable schema."""
    raw = payload if isinstance(payload, dict) else {}
    decision = str(raw.get("decision") or "retry").strip().lower()
    if decision in {"yes", "ship", "good", "accept"}:
        decision = "accept"
    elif decision in {"warn", "caution", "salvageable"}:
        decision = "warn"
    elif decision in {"no", "reject", "bad", "retry"}:
        decision = "retry"
    if decision not in REVIEW_DECISIONS:
        decision = "retry"

    recommended_clip_id = str(raw.get("recommended_clip_id") or "").strip()
    assessments: list[dict[str, Any]] = []
    for item in raw.get("clip_assessments") or []:
        if not isinstance(item, dict):
            continue
        clip_id = str(item.get("clip_id") or "").strip()
        if not clip_id:
            continue
        verdict = str(item.get("verdict") or "").strip().lower()
        assessment_text = str(item.get("assessment") or item.get("notes") or "").strip()
        recommended = bool(item.get("recommended"))
        if not item.get("recommended") and recommended_clip_id and clip_id == recommended_clip_id:
            recommended = True

        if verdict == "reject":
            framing = legibility = artifact_dominance = state_quality = "weak"
        elif verdict == "salvageable":
            framing = legibility = "good"
            artifact_dominance = "mixed"
            state_quality = "good"
        else:
            framing = legibility = artifact_dominance = state_quality = "unknown"

        assessments.append(
            {
                "clip_id": clip_id,
                "recommended": recommended,
                "notes": assessment_text,
                "framing": str(item.get("framing") or framing).strip().lower() or "unknown",
                "legibility": str(item.get("legibility") or legibility).strip().lower() or "unknown",
                "theme": str(item.get("theme") or "").strip().lower() or "unknown",
                "artifact_dominance": str(item.get("artifact_dominance") or artifact_dominance).strip().lower() or "unknown",
                "state_quality": str(item.get("state_quality") or state_quality).strip().lower() or "unknown",
                "crop_quality": str(item.get("crop_quality") or "").strip().lower() or "unknown",
            }
        )

    issues: list[dict[str, str]] = []
    for item in raw.get("issues") or []:
        if not isinstance(item, dict):
            continue
        code = str(item.get("code") or "").strip()
        if not code:
            continue
        issues.append(
            {
                "code": code,
                "severity": str(item.get("severity") or "warn").strip().lower() or "warn",
                "message": str(item.get("message") or "").strip(),
            }
        )

    if not recommended_clip_id:
        recommended = next((item["clip_id"] for item in assessments if item.get("recommended")), "")
        recommended_clip_id = recommended

    return {
        "decision": decision,
        "summary": str(raw.get("summary") or "").strip(),
        "recommended_clip_id": recommended_clip_id,
        "clip_assessments": assessments,
        "issues": issues,
    }


def choose_retry_actions(
    review_payload: dict[str, Any],
    *,
    available_actions: list[str] | None = None,
    limit: int = 3,
) -> list[str]:
    """Map review issues into a bounded ordered retry action list."""
    allowed = [
        action
        for action in (available_actions or DEFAULT_RETRY_ACTION_ORDER)
        if action in RETRY_ACTIONS
    ]
    if not allowed or str(review_payload.get("decision") or "").lower() != "retry":
        return []

    desired: list[str] = []
    issue_codes = {str(issue.get("code") or "") for issue in review_payload.get("issues") or []}
    assessments = review_payload.get("clip_assessments") or []

    for assessment in assessments:
        if assessment.get("theme") in {"wrong", "mixed"}:
            desired.append("switch_theme")
        if assessment.get("framing") in {"poor", "weak"} or assessment.get("legibility") in {"poor", "weak"}:
            desired.extend(["expand_viewport", "refocus_crop"])
        if assessment.get("artifact_dominance") in {"weak", "mixed"}:
            desired.append("collapse_sidebar")
        if assessment.get("state_quality") == "weak":
            desired.append("pick_better_state")
        if assessment.get("crop_quality") == "worse":
            desired.append("refocus_crop")

    if any(code in issue_codes for code in {"wrong_theme", "mixed_theme"}):
        desired.append("switch_theme")
    if any(code in issue_codes for code in {"framing_bad", "legibility_bad"}):
        desired.extend(["expand_viewport", "refocus_crop"])
    if any(code in issue_codes for code in {"weak_primary_state", "failed_training_run_selected", "zero_metric_hero"}):
        desired.append("pick_better_state")
    if any(code in issue_codes for code in {"sidebar_noise", "weak_artifact_dominance"}):
        desired.append("collapse_sidebar")

    result: list[str] = []
    for action in desired:
        if action in allowed and action not in result:
            result.append(action)
        if len(result) >= limit:
            break
    return result


def rank_training_runs(runs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Rank generic training-run style candidates for use as demo evidence."""
    ranked: list[dict[str, Any]] = []
    for item in runs:
        run = copy.deepcopy(item if isinstance(item, dict) else {})
        metrics = run.get("metrics") if isinstance(run.get("metrics"), dict) else {}
        m_ap50 = _safe_float(metrics.get("mAP50"))
        m_ap50_95 = _safe_float(metrics.get("mAP50_95"))
        precision = _safe_float(metrics.get("precision"))
        recall = _safe_float(metrics.get("recall"))
        status = str(run.get("status") or "").strip().lower()

        score = _STATUS_WEIGHTS.get(status, 0)
        if m_ap50 is not None:
            score += min(35, int(round(m_ap50 * 100)))
        if m_ap50_95 is not None:
            score += min(20, int(round(m_ap50_95 * 100)))
        if precision is not None:
            score += min(10, int(round(precision * 10)))
        if recall is not None:
            score += min(10, int(round(recall * 10)))

        warnings: list[str] = []
        hero_ok = status in {"completed", "succeeded"}
        if m_ap50 is not None and m_ap50 <= 0:
            warnings.append("Validation metrics are zero.")
            hero_ok = False
            score -= 25
        if status in {"failed", "cancelled"}:
            warnings.append("Run did not complete successfully.")
            hero_ok = False
        if status in {"failed", "cancelled"} and (m_ap50 or 0) > 0:
            warnings.append("Metrics improved, but the run still failed and should not be the hero state without a caveat.")
        if status in {"completed", "succeeded"} and (m_ap50 or 0) <= 0:
            warnings.append("Completed successfully, but the visible metrics are too weak for a hero moment.")

        run["metrics"] = metrics
        run["score"] = score
        run["hero_ok"] = hero_ok and not warnings
        run["hero_warning"] = " ".join(warnings).strip()
        ranked.append(run)

    return sorted(ranked, key=lambda item: (int(item.get("score") or 0), str(item.get("run_id") or "")), reverse=True)


def build_review_report(bundle_manifest: dict[str, Any], observations: dict[str, Any]) -> dict[str, Any]:
    """Combine model observations with deterministic review and retry rules."""
    report = normalize_review_observations(observations)
    manifest = bundle_manifest if isinstance(bundle_manifest, dict) else {}
    clips = {
        str(item.get("id") or item.get("clip_id") or ""): item
        for item in (manifest.get("clips") or [])
        if isinstance(item, dict) and str(item.get("id") or item.get("clip_id") or "").strip()
    }

    selected_clip = clips.get(report["recommended_clip_id"])
    if isinstance(selected_clip, dict):
        training_runs = selected_clip.get("training_runs") or []
        if isinstance(training_runs, list) and training_runs:
            ranked = rank_training_runs(training_runs)
            selected_run = next((item for item in ranked if item.get("selected")), ranked[0] if ranked else None)
            if selected_run and selected_run.get("hero_warning"):
                report["issues"].append(
                    {
                        "code": "failed_training_run_selected" if "failed" in selected_run["hero_warning"].lower() else "zero_metric_hero",
                        "severity": "warn",
                        "message": str(selected_run["hero_warning"]),
                    }
                )
                if report["decision"] == "accept":
                    report["decision"] = "warn"
            report["training_runs_ranked"] = ranked

    report["retry_actions"] = choose_retry_actions(report)
    return report
