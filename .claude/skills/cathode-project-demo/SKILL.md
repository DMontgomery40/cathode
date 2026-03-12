---
name: cathode-project-demo
description: Turn a live product, localhost app, or software repository into a reviewed narrated demo video with Cathode. Use when Claude needs to capture fresh UI footage, critique it, and hand approved clips to Cathode for final render.
---

# Cathode Project Demo

This Claude-facing mirror points at the canonical Cathode skill resources in the repository root.

Use the canonical resources here:

- [`skills/cathode-project-demo/SKILL.md`](../../../skills/cathode-project-demo/SKILL.md)
- [`skills/cathode-project-demo/references/dev-demo-workflow.md`](../../../skills/cathode-project-demo/references/dev-demo-workflow.md)
- [`skills/cathode-project-demo/references/live-demo-capture.md`](../../../skills/cathode-project-demo/references/live-demo-capture.md)
- [`skills/cathode-project-demo/references/review-rubric.md`](../../../skills/cathode-project-demo/references/review-rubric.md)
- [`skills/cathode-project-demo/scripts/bootstrap_cathode.py`](../../../skills/cathode-project-demo/scripts/bootstrap_cathode.py)
- [`skills/cathode-project-demo/scripts/prepare_live_demo_session.py`](../../../skills/cathode-project-demo/scripts/prepare_live_demo_session.py)
- [`skills/cathode-project-demo/scripts/launch_target_app.py`](../../../skills/cathode-project-demo/scripts/launch_target_app.py)
- [`skills/cathode-project-demo/scripts/capture_live_demo.py`](../../../skills/cathode-project-demo/scripts/capture_live_demo.py)
- [`skills/cathode-project-demo/scripts/apply_retry_actions.py`](../../../skills/cathode-project-demo/scripts/apply_retry_actions.py)
- [`skills/cathode-project-demo/scripts/postprocess_capture.py`](../../../skills/cathode-project-demo/scripts/postprocess_capture.py)
- [`skills/cathode-project-demo/scripts/extract_review_frames.py`](../../../skills/cathode-project-demo/scripts/extract_review_frames.py)
- [`skills/cathode-project-demo/scripts/init_review_observations.py`](../../../skills/cathode-project-demo/scripts/init_review_observations.py)
- [`skills/cathode-project-demo/scripts/review_bundle.py`](../../../skills/cathode-project-demo/scripts/review_bundle.py)
- [`skills/cathode-project-demo/scripts/prepare_cathode_handoff.py`](../../../skills/cathode-project-demo/scripts/prepare_cathode_handoff.py)

Default workflow:

1. prepare a live demo session
2. launch or attach to the app
3. capture fresh footage in a real browser with the packaged capture driver
4. run the short-prompt spawned sub-agent review before handoff, save the raw reply, and translate it into the structured Cathode review bundle
5. feed reviewed clips into Cathode over MCP
