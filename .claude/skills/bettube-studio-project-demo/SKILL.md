---
name: bettube-studio-project-demo
description: Turn a live product, localhost app, or software repository into a reviewed narrated demo video with betTube Studio. Use when Claude needs to drive the real app with desktop-use, critique fresh UI footage, and hand approved clips to betTube Studio for final render.
---

# betTube Studio Project Demo

This Claude-facing mirror points at the canonical betTube Studio skill resources in the repository root.

Use the canonical resources here:

- [`skills/bettube-studio-project-demo/SKILL.md`](../../../skills/bettube-studio-project-demo/SKILL.md)
- [`skills/bettube-studio-project-demo/references/dev-demo-workflow.md`](../../../skills/bettube-studio-project-demo/references/dev-demo-workflow.md)
- [`skills/bettube-studio-project-demo/references/live-demo-capture.md`](../../../skills/bettube-studio-project-demo/references/live-demo-capture.md)
- [`skills/bettube-studio-project-demo/references/review-rubric.md`](../../../skills/bettube-studio-project-demo/references/review-rubric.md)
- [`skills/bettube-studio-project-demo/scripts/bootstrap_bettube_studio.py`](../../../skills/bettube-studio-project-demo/scripts/bootstrap_bettube_studio.py)
- [`skills/bettube-studio-project-demo/scripts/prepare_live_demo_session.py`](../../../skills/bettube-studio-project-demo/scripts/prepare_live_demo_session.py)
- [`skills/bettube-studio-project-demo/scripts/launch_target_app.py`](../../../skills/bettube-studio-project-demo/scripts/launch_target_app.py)
- [`skills/bettube-studio-project-demo/scripts/build_capture_manifest.py`](../../../skills/bettube-studio-project-demo/scripts/build_capture_manifest.py)
- [`skills/bettube-studio-project-demo/scripts/capture_live_demo.py`](../../../skills/bettube-studio-project-demo/scripts/capture_live_demo.py)
- [`skills/bettube-studio-project-demo/scripts/apply_retry_actions.py`](../../../skills/bettube-studio-project-demo/scripts/apply_retry_actions.py)
- [`skills/bettube-studio-project-demo/scripts/postprocess_capture.py`](../../../skills/bettube-studio-project-demo/scripts/postprocess_capture.py)
- [`skills/bettube-studio-project-demo/scripts/extract_review_frames.py`](../../../skills/bettube-studio-project-demo/scripts/extract_review_frames.py)
- [`skills/bettube-studio-project-demo/scripts/init_review_observations.py`](../../../skills/bettube-studio-project-demo/scripts/init_review_observations.py)
- [`skills/bettube-studio-project-demo/scripts/review_bundle.py`](../../../skills/bettube-studio-project-demo/scripts/review_bundle.py)
- [`skills/bettube-studio-project-demo/scripts/prepare_bettube_studio_handoff.py`](../../../skills/bettube-studio-project-demo/scripts/prepare_bettube_studio_handoff.py)

Default workflow:

1. prepare a live demo session
2. launch or attach to the app
3. capture fresh footage by driving the real app with desktop-use, then build the standard capture manifest
4. run the short-prompt spawned sub-agent review before handoff, save the raw reply, and translate it into the structured betTube Studio review bundle
5. feed reviewed clips into betTube Studio over MCP
