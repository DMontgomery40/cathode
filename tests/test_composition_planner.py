import pytest

from core.composition_planner import (
    plan_scene_compositions,
    _enrich_template_props,
    _has_temporal_progression,
    _expand_arrow_data_points,
    _expand_arrow_lines_for_data_stage,
    _infer_polarity,
    _three_data_stage_points,
    _three_data_stage_data,
)


def test_plain_ui_screenshot_stays_media_pan_without_overlay_callouts():
    scenes = [
        {
            "uid": "scene_ui",
            "id": 0,
            "title": "The React Control Room",
            "scene_type": "image",
            "narration": "The current React workspace shows the brief on the left and the project shell on the right.",
            "visual_prompt": "Clean dark-mode screenshot of the product UI with a wide workspace, side rail, and panel chrome.",
            "on_screen_text": ["Brief Studio", "Scenes", "Render"],
        }
    ]

    planned = plan_scene_compositions(scenes)
    scene = planned[0]

    assert scene["composition"]["family"] == "media_pan"
    assert scene["composition"]["mode"] == "none"


def test_non_native_brief_suppresses_transition_treatments():
    scenes = [
        {
            "uid": "scene_cover",
            "id": 0,
            "title": "Cover",
            "scene_type": "image",
            "narration": "Walk through the report clearly.",
            "visual_prompt": "Illustrated cover still.",
            "transition_hint": "fade",
            "composition": {"transition_after": {"kind": "fade", "duration_in_frames": 20}},
        }
    ]

    planned = plan_scene_compositions(
        scenes,
        brief={
            "video_goal": "Explain quarterly results clearly.",
            "audience": "Account holders reviewing their report.",
            "source_material": "Results across sessions with reference ranges and follow-up recommendations.",
        },
    )

    assert planned[0]["composition"]["transition_after"] is None
    assert planned[0]["transition_hint"] is None


def test_plain_screen_recording_stays_static_media_without_overlay_callouts():
    scenes = [
        {
            "uid": "scene_video",
            "id": 0,
            "title": "Watching the Job Run",
                "scene_type": "video",
                "narration": "A real screen recording shows the queue progressing through the job.",
                "visual_prompt": (
                    "Real browser recording of the dashboard and queue workspace while the render advances. "
                    "Decorative scan-line overlay and subtle glow are fine. Keep the product frame clean and uninterrupted."
                ),
                "on_screen_text": ["Queue", "Render"],
            }
        ]

    planned = plan_scene_compositions(scenes)
    scene = planned[0]

    assert scene["composition"]["family"] == "static_media"
    assert scene["composition"]["mode"] == "none"


def test_explicit_ui_callout_scene_defaults_to_media_without_native_opt_in():
    scenes = [
        {
            "uid": "scene_callout",
            "id": 0,
            "title": "What Goes Into a Brief",
            "scene_type": "image",
            "narration": "Overlay labels point at the main brief fields while the screenshot stays stable underneath.",
            "visual_prompt": "Dark-mode screenshot of the brief workspace with the main form visible.",
            "staging_notes": "Soft callout tags point to the brief input, goal field, and generate button.",
            "on_screen_text": ["Source Material", "Video Goal", "Generate"],
        }
    ]

    planned = plan_scene_compositions(scenes)
    scene = planned[0]

    assert scene["composition"]["family"] == "media_pan"
    assert scene["composition"]["mode"] == "none"


def test_explicit_ui_callout_scene_keeps_software_demo_overlay_when_native_requested():
    scenes = [
        {
            "uid": "scene_callout",
            "id": 0,
            "title": "What Goes Into a Brief",
            "scene_type": "image",
            "narration": "Overlay labels point at the main brief fields while the screenshot stays stable underneath.",
            "visual_prompt": "Dark-mode screenshot of the brief workspace with the main form visible.",
            "staging_notes": "Soft callout tags point to the brief input, goal field, and generate button.",
            "on_screen_text": ["Source Material", "Video Goal", "Generate"],
        }
    ]

    planned = plan_scene_compositions(scenes, brief={"text_render_mode": "deterministic_overlay"})
    scene = planned[0]

    assert scene["composition"]["family"] == "software_demo_focus"
    assert scene["composition"]["mode"] == "overlay"


# ---------------------------------------------------------------------------
# Template deck structured props from on_screen_text / data_points
# ---------------------------------------------------------------------------

_NATIVE_BRIEF = {
    "video_goal": "Explain progress across review sessions.",
    "audience": "Account holders reviewing their report.",
    "source_material": "Results across sessions.",
    "text_render_mode": "deterministic_overlay",
}


class TestTemplatePropsBuiltFromOnScreenText:
    """Verify each template deck family gets structured props from on_screen_text."""

    def test_cover_hook_gets_subtitle_and_kicker(self):
        props: dict = {"headline": "Your Quarterly Report"}
        _enrich_template_props(
            "cover_hook", props,
            ["Your Quarterly Report", "Session Overview", "betTube Studio"],
            [],
        )
        assert props["subtitle"] == "Session Overview"
        assert props["kicker"] == "betTube Studio"

    def test_orientation_gets_items(self):
        props: dict = {"headline": "What We Will Explore"}
        _enrich_template_props(
            "orientation", props,
            ["What We Will Explore", "Response Times", "Focus Metrics", "Action Plan"],
            [],
        )
        assert props["items"] == ["Response Times", "Focus Metrics", "Action Plan"]

    def test_timeline_progression_gets_markers(self):
        props: dict = {"headline": "Rollout Timeline"}
        _enrich_template_props(
            "timeline_progression", props,
            ["Rollout Timeline", "Session 1 -- Jan 15", "Session 2 -- Feb 20", "Session 3 -- Mar 10"],
            [],
        )
        assert len(props["markers"]) == 3
        assert props["markers"][0]["label"] == "Session 1"
        assert props["markers"][0]["date"] == "Jan 15"

    def test_metric_improvement_gets_stages_from_data_points(self):
        props: dict = {"headline": "Signal Strength"}
        _enrich_template_props(
            "metric_improvement", props,
            ["Signal Strength"],
            ["Session 1: 6.9 ms", "Session 2: 11.0 ms"],
        )
        assert len(props["stages"]) == 2
        assert props["stages"][0]["value"] == "6.9 ms"
        assert props["stages"][0]["label"] == "Session 1"
        assert props["stages"][1]["value"] == "11.0 ms"
        assert "delta" in props

    def test_metric_improvement_computes_delta(self):
        props: dict = {"headline": "Test"}
        _enrich_template_props(
            "metric_improvement", props,
            ["Test"],
            ["Before: 5.0", "After: 8.0"],
        )
        assert props["delta"] == "+3.0"
        assert props["direction"] == "improvement"

    def test_metric_comparison_gets_left_right(self):
        props: dict = {"headline": "Before vs After"}
        _enrich_template_props(
            "metric_comparison", props,
            ["Before vs After"],
            ["Low focus 3.2", "Poor uptime 4.1", "Good focus 7.8", "Better uptime 6.5"],
        )
        assert "left" in props
        assert "right" in props
        assert len(props["left"]["items"]) == 2
        assert len(props["right"]["items"]) == 2

    def test_synthesis_summary_gets_columns(self):
        props: dict = {"headline": "Summary"}
        _enrich_template_props(
            "synthesis_summary", props,
            ["Summary"],
            ["Focus improved", "Latency lower", "Errors down", "Coverage up"],
        )
        assert "columns" in props
        assert len(props["columns"]) >= 2

    def test_closing_cta_gets_bullets(self):
        props: dict = {"headline": "Next Steps"}
        _enrich_template_props(
            "closing_cta", props,
            ["Next Steps", "Schedule follow-up", "Continue training", "Track metrics"],
            [],
        )
        assert props["bullets"] == ["Schedule follow-up", "Continue training", "Track metrics"]

    def test_analogy_metaphor_gets_left_right(self):
        props: dict = {"headline": "Understanding the System"}
        _enrich_template_props(
            "analogy_metaphor", props,
            ["Understanding the System"],
            ["Orchestra", "Each section plays", "Your Pipeline", "Each stage contributes"],
        )
        assert props["left"]["title"] == "Orchestra"
        assert props["right"]["title"] == "Your Pipeline"


class TestTemplatePropsPreserveDirectorProps:
    """Verify director-populated props aren't overwritten by enrichment."""

    def test_director_stages_preserved(self):
        props: dict = {
            "headline": "Response Time",
            "stages": [{"value": "6.9 ms", "label": "Baseline"}, {"value": "11.0 ms", "label": "Post"}],
        }
        _enrich_template_props(
            "metric_improvement", props,
            ["Response Time", "Session 1: 6.9 ms"],
            ["Session 1: 6.9 ms"],
        )
        # stages should remain unchanged
        assert props["stages"][0]["label"] == "Baseline"

    def test_metric_improvement_filters_target_lines_and_computes_delta(self):
        """Real data: 'Target: 43–83 sec' must NOT become a stage."""
        props: dict = {"headline": "Completion Time"}
        _enrich_template_props(
            "metric_improvement", props,
            ["Completion Time"],
            ["Session 1: 96 sec", "Session 2: 44 sec", "Session 3: 47 sec", "Target: 43–83 sec"],
        )
        # Target line excluded from stages
        assert len(props["stages"]) == 3
        assert props["stages"][-1]["label"] == "Session 3"
        # Target stored as caption
        assert "Target" in props.get("caption", "")
        # Delta: 47 - 96 = -49 (decline, since completion time dropped)
        assert props["delta"] == "-49.0"

    def test_director_markers_preserved(self):
        props: dict = {
            "headline": "Timeline",
            "markers": [{"label": "Start", "date": "Jan 1", "status": "completed"}],
        }
        _enrich_template_props(
            "timeline_progression", props,
            ["Timeline", "Session 1 -- Jan 1"],
            [],
        )
        assert len(props["markers"]) == 1
        assert props["markers"][0]["label"] == "Start"


# ---------------------------------------------------------------------------
# Data-shape rerouting: arrow progressions reroute to three_data_stage
# ---------------------------------------------------------------------------


class TestHasTemporalProgression:
    """Unit tests for _has_temporal_progression."""

    def test_unicode_arrow(self):
        assert _has_temporal_progression(["Latency Ratio: 0.8 → 1.0 → 1.0"]) is True

    def test_ascii_arrow(self):
        assert _has_temporal_progression(["Cache Ratio: 0.8 -> 1.0"]) is True

    def test_fat_arrow(self):
        assert _has_temporal_progression(["Metric: 5 => 8"]) is True

    def test_no_arrows(self):
        assert _has_temporal_progression(["Throughput: 12.5 rps improved"]) is False

    def test_empty(self):
        assert _has_temporal_progression([]) is False

    def test_mixed_lines(self):
        assert _has_temporal_progression(["Throughput: 12.5", "Ratio: 0.8 -> 1.0"]) is True


class TestExpandArrowDataPoints:
    """Unit tests for _expand_arrow_data_points."""

    def test_three_stage_unicode_arrow(self):
        result = _expand_arrow_data_points(["Cache Hit Ratio: 0.8 → 1.0 → 1.0"])
        assert result == ["Session 1: 0.8", "Session 2: 1.0", "Session 3: 1.0"]

    def test_two_stage_ascii_arrow(self):
        result = _expand_arrow_data_points(["Signal: 6.9 -> 11.0"])
        assert result == ["Session 1: 6.9", "Session 2: 11.0"]

    def test_non_arrow_lines_pass_through(self):
        result = _expand_arrow_data_points(["Target: 0.9-1.1", "Ratio: 0.8 -> 1.0"])
        assert result[0] == "Target: 0.9-1.1"
        assert result[1] == "Session 1: 0.8"
        assert result[2] == "Session 2: 1.0"

    def test_no_colon_prefix(self):
        result = _expand_arrow_data_points(["0.8 -> 1.0 -> 1.2"])
        assert result == ["Session 1: 0.8", "Session 2: 1.0", "Session 3: 1.2"]


class TestDataShapeRerouting:
    """Integration tests for data-shape rerouting through plan_scene_compositions."""

    def test_metric_improvement_with_arrows_reroutes_to_chart(self):
        """metric_improvement with arrows reroutes to three_data_stage."""
        scene = {
            "uid": "scene_metric",
            "id": 0,
            "title": "Task Completion",
            "scene_type": "motion",
            "narration": "Completion times improved.",
            "on_screen_text": ["Task Completion"],
            "composition": {
                "family": "metric_improvement",
                "mode": "native",
                "props": {"headline": "Task Completion"},
                "data": {"data_points": ["Time: 75 -> 63 -> 58"]},
            },
        }
        planned = plan_scene_compositions([scene], brief=_NATIVE_BRIEF)
        assert planned[0]["composition"]["family"] == "three_data_stage"

    def test_metric_improvement_with_session_labels_reroutes_to_chart(self):
        scene = {
            "uid": "scene_metric_sessions",
            "id": 0,
            "title": "Signal Strength",
            "scene_type": "motion",
            "narration": "Signal grew across sessions.",
            "on_screen_text": ["Signal Strength"],
            "composition": {
                "family": "metric_improvement",
                "mode": "native",
                "props": {"headline": "Signal Strength"},
                "data": {"data_points": ["Session 1: 6.9", "Session 2: 11.0"]},
            },
        }
        planned = plan_scene_compositions([scene], brief=_NATIVE_BRIEF)
        assert planned[0]["composition"]["family"] == "three_data_stage"

    def test_metric_improvement_without_progression_stays_put(self):
        scene = {
            "uid": "scene_metric_static",
            "id": 0,
            "title": "Uptime",
            "scene_type": "motion",
            "narration": "Current uptime reading.",
            "on_screen_text": ["Uptime"],
            "composition": {
                "family": "metric_improvement",
                "mode": "native",
                "props": {"headline": "Uptime"},
                "data": {"data_points": ["Before: 95%", "After: 99%"]},
            },
        }
        planned = plan_scene_compositions([scene], brief=_NATIVE_BRIEF)
        assert planned[0]["composition"]["family"] == "metric_improvement"


class TestThreeDataStageNullYFix:
    """Verify that director-provided series with y=null are replaced with extracted values."""

    def test_null_y_series_replaced_with_extracted_values(self):
        """When director pre-populates series with y=null, _three_data_stage_data replaces them."""
        scene = {
            "uid": "scene_signal",
            "id": 0,
            "title": "Signal Strength: Growing Into Range",
            "scene_type": "motion",
            "narration": "Signal amplitude grew from 6.9 to 11.0",
            "data_points": [
                "Session 1: 6.9 ms (below target)",
                "Session 2: 11.0 ms (within target)",
                "Session 3: 11.0 ms (within target)",
                "Target: 8–20 ms",
            ],
            "on_screen_text": ["Signal Strength"],
        }
        # Simulate director pre-populated data with y=null
        existing_data = {
            "series": [
                {
                    "id": "series_1",
                    "label": "Signal Strength",
                    "type": "bar",
                    "points": [
                        {"x": "Session 1: 6.9 ms (below target)", "y": None},
                        {"x": "Session 2: 11.0 ms (within target)", "y": None},
                        {"x": "Session 3: 11.0 ms (within target)", "y": None},
                    ],
                }
            ]
        }
        intent = {"data_points": [], "family_hint": "three_data_stage", "mode_hint": "", "transition_after": None}
        result = _three_data_stage_data(scene, intent, existing_data, {"layoutVariant": "bars_with_band"})

        series = result.get("series", [])
        assert len(series) == 1
        points = series[0]["points"]
        assert len(points) == 3
        assert points[0]["y"] == 6.9
        assert points[1]["y"] == 11.0
        assert points[2]["y"] == 11.0
        # Reference band should also be populated
        bands = result.get("referenceBands", [])
        assert len(bands) >= 1
        assert bands[0]["yMin"] == 8.0
        assert bands[0]["yMax"] == 20.0

    def test_real_y_values_not_overwritten(self):
        """When director provides real y values, they are preserved."""
        scene = {
            "uid": "scene_ok",
            "id": 0,
            "title": "Good Data",
            "scene_type": "motion",
            "narration": "...",
            "data_points": ["A: 10", "B: 20", "C: 30"],
            "on_screen_text": ["Good Data"],
        }
        existing_data = {
            "series": [
                {
                    "id": "series_custom",
                    "label": "Custom",
                    "type": "line",
                    "points": [
                        {"x": "A", "y": 10.0},
                        {"x": "B", "y": 20.0},
                        {"x": "C", "y": 30.0},
                    ],
                }
            ]
        }
        intent = {"data_points": [], "family_hint": "three_data_stage", "mode_hint": "", "transition_after": None}
        result = _three_data_stage_data(scene, intent, existing_data, {"layoutVariant": "line_with_band"})

        # Original series preserved (not overwritten)
        assert result["series"][0]["id"] == "series_custom"
        assert result["series"][0]["points"][0]["y"] == 10.0


class TestArrowExpansionForDataStage:
    """Test arrow data_point expansion for three_data_stage charts."""

    def test_expand_arrow_with_target(self):
        """Arrow data with embedded (target ...) expands correctly."""
        dp = ["Task A: 33s → 41s → 42s (target 38–65s)"]
        expanded, extra_bands = _expand_arrow_lines_for_data_stage(dp)
        assert len(expanded) == 3
        assert "33" in expanded[0]
        assert "41" in expanded[1]
        assert "42" in expanded[2]
        assert len(extra_bands) == 1
        assert "38" in extra_bands[0]
        assert "65" in extra_bands[0]

    def test_non_arrow_passthrough(self):
        """Non-arrow data_points are passed through unchanged."""
        dp = ["Session 1: 6.9 ms (below target)", "Target: 8–20 ms"]
        expanded, extra_bands = _expand_arrow_lines_for_data_stage(dp)
        assert expanded == dp
        assert extra_bands == []

    def test_dual_metric_arrow_produces_panel_split(self):
        """Two arrow data_points with incompatible scales produce dual panels."""
        scene = {
            "uid": "scene_dual",
            "id": 0,
            "title": "Two Metrics",
            "scene_type": "motion",
            "narration": "Both metrics stable.",
            "data_points": [
                "Task A: 33s → 41s → 42s (target 38–65s)",
                "Response Time: 296ms → 293ms → 321ms (target 252–362ms)",
            ],
            "on_screen_text": ["Two Metrics"],
        }
        intent = {"data_points": [], "family_hint": "three_data_stage", "mode_hint": "", "transition_after": None}
        result = _three_data_stage_data(scene, intent, {}, {"layoutVariant": "bars_with_band"})

        # Should produce panels (not single series) due to scale gap
        assert "panels" in result
        panels = result["panels"]
        assert len(panels) == 2
        # Each panel should have reference bands
        for panel in panels:
            assert len(panel["referenceBands"]) >= 1
            pts = panel["series"][0]["points"]
            assert all(pt["y"] is not None for pt in pts)


# ---------------------------------------------------------------------------
# Polarity inference
# ---------------------------------------------------------------------------

class TestInferPolarity:
    """Unit tests for _infer_polarity."""

    def test_lower_is_better_completion_time(self):
        """Completion time: 96 → 44 → 47 sec, target 43-83.  First above band, last in band."""
        points = [{"x": "S1", "y": 96}, {"x": "S2", "y": 44}, {"x": "S3", "y": 47}]
        bands = [{"yMin": 43, "yMax": 83}]
        assert _infer_polarity(points, bands) == "lower_is_better"

    def test_higher_is_better_signal(self):
        """Signal: 6.9 → 11 → 11 ms, target 8-20.  First below band, last in band."""
        points = [{"x": "S1", "y": 6.9}, {"x": "S2", "y": 11}, {"x": "S3", "y": 11}]
        bands = [{"yMin": 8, "yMax": 20}]
        assert _infer_polarity(points, bands) == "higher_is_better"

    def test_in_range_when_all_in_band(self):
        """All values within band → in_range_is_better."""
        points = [{"x": "S1", "y": 50}, {"x": "S2", "y": 55}, {"x": "S3", "y": 52}]
        bands = [{"yMin": 40, "yMax": 60}]
        assert _infer_polarity(points, bands) == "in_range_is_better"

    def test_no_polarity_without_bands(self):
        """No reference band → None."""
        points = [{"x": "S1", "y": 10}, {"x": "S2", "y": 20}]
        assert _infer_polarity(points, []) is None

    def test_no_polarity_with_single_point(self):
        """Single point → None (need >= 2)."""
        points = [{"x": "S1", "y": 10}]
        bands = [{"yMin": 5, "yMax": 15}]
        assert _infer_polarity(points, bands) is None

    def test_both_above_band_trending_down(self):
        """Both out high, last < first → lower_is_better."""
        points = [{"x": "S1", "y": 100}, {"x": "S2", "y": 90}]
        bands = [{"yMin": 40, "yMax": 60}]
        assert _infer_polarity(points, bands) == "lower_is_better"

    def test_both_below_band_trending_up(self):
        """Both out low, last > first → higher_is_better."""
        points = [{"x": "S1", "y": 5}, {"x": "S2", "y": 8}]
        bands = [{"yMin": 20, "yMax": 40}]
        assert _infer_polarity(points, bands) == "higher_is_better"

    def test_both_above_not_improving(self):
        """Both out high, last >= first → None (no clear direction)."""
        points = [{"x": "S1", "y": 90}, {"x": "S2", "y": 95}]
        bands = [{"yMin": 40, "yMax": 60}]
        assert _infer_polarity(points, bands) is None

    def test_polarity_in_three_data_stage_data(self):
        """End-to-end: _three_data_stage_data populates polarity."""
        scene = {
            "uid": "scene_completion",
            "id": 0,
            "title": "Completion Time: Improvement",
            "scene_type": "motion",
            "narration": "...",
            "data_points": [
                "Session 1: 96 sec",
                "Session 2: 44 sec",
                "Session 3: 47 sec",
                "Target: 43–83 sec",
            ],
            "on_screen_text": ["Completion Time"],
        }
        intent = {"data_points": [], "family_hint": "three_data_stage", "mode_hint": "", "transition_after": None}
        result = _three_data_stage_data(scene, intent, {}, {"layoutVariant": "bars_with_band"})
        assert result.get("polarity") == "lower_is_better"

    def test_director_override_polarity(self):
        """Explicit polarity in data is not overwritten by inference."""
        scene = {
            "uid": "scene_custom",
            "id": 0,
            "title": "Custom Metric",
            "scene_type": "motion",
            "narration": "...",
            "data_points": [
                "Session 1: 6.9 ms",
                "Session 2: 11.0 ms",
                "Target: 8–20 ms",
            ],
            "on_screen_text": ["Custom Metric"],
        }
        existing_data = {"polarity": "lower_is_better"}
        intent = {"data_points": [], "family_hint": "three_data_stage", "mode_hint": "", "transition_after": None}
        result = _three_data_stage_data(scene, intent, existing_data, {"layoutVariant": "bars_with_band"})
        # Director said lower_is_better; inference would say higher_is_better, but it must be preserved
        assert result["polarity"] == "lower_is_better"

    def test_dual_panel_polarity(self):
        """Dual-panel scenes get per-panel polarity."""
        scene = {
            "uid": "scene_dual",
            "id": 0,
            "title": "Two Metrics",
            "scene_type": "motion",
            "narration": "Both metrics improved.",
            "data_points": [
                "Task A: 33s → 41s → 42s (target 38–65s)",
                "Response Time: 296ms → 293ms → 321ms (target 252–362ms)",
            ],
            "on_screen_text": ["Two Metrics"],
        }
        intent = {"data_points": [], "family_hint": "three_data_stage", "mode_hint": "", "transition_after": None}
        result = _three_data_stage_data(scene, intent, {}, {"layoutVariant": "bars_with_band"})
        panels = result.get("panels", [])
        assert len(panels) == 2
        # At least one panel should have polarity inferred
        polarities = [p.get("polarity") for p in panels]
        assert any(p is not None for p in polarities)
