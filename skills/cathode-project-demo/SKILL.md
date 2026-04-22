---
name: cathode-project-demo
description: Turn a live product, localhost app, or software repository into a reviewed narrated demo video with Cathode. Use when Codex or Claude needs to demo a real UI or workflow from scratch, drive the real app with desktop-use, critique framing and state quality, and feed approved clips into Cathode for final render.
---

# Cathode Project Demo

Use this skill to build a demo video from a live product, not from README screenshots. The default path is:

1. inspect the target repo
2. launch or attach to the app
3. capture fresh footage with desktop-use
4. run a short-prompt spawned sub-agent review plus deterministic rules
5. hand approved clips to Cathode
6. render

Prefer the MCP path for repeatable agent-driven runs. Use the app only when a human wants scene-by-scene edits after the first render.

## Quick Start

1. Identify the demo target:
   - local repo path
   - app URL if already running
   - launch command and expected URL if it needs to boot locally
2. Bootstrap Cathode with `scripts/bootstrap_cathode.py`.
3. Prepare a capture session with `scripts/prepare_live_demo_session.py`.
4. Launch the target app with `scripts/launch_target_app.py` when the app is local.
5. Write a capture plan/checklist for the walkthrough, record the run while driving the app with desktop-use, then run `scripts/build_capture_manifest.py` so the skill keeps raw capture video, screenshots, and a step manifest.
6. Use `scripts/capture_live_demo.py` only when you specifically need the older Playwright fallback for headed browser automation, selector-driven retries, CI, or trace zips.
7. Postprocess the raw capture with `scripts/postprocess_capture.py`.
8. Extract review frames, send them to a spawned sub-agent with a deliberately short prompt, save its plain-language response, seed an observations template with `scripts/init_review_observations.py`, then turn your structured observations into a report with `scripts/review_bundle.py`.
9. Build the Cathode `make_video` payload with `scripts/prepare_cathode_handoff.py`.
10. Call `make_video`, then poll `get_job_status`.

Read these references before the first live run:

- [references/dev-demo-workflow.md](references/dev-demo-workflow.md)
- [references/live-demo-capture.md](references/live-demo-capture.md)
- [references/review-rubric.md](references/review-rubric.md)

## Guardrails

- Always capture fresh footage from a running app unless the user explicitly asks for an images-only concept video.
- Never rely on README screenshots or shipped stills as the default walkthrough source.
- Set theme explicitly on every attempt. Never trust ambient OS or browser theme.
- Set viewport explicitly on every attempt. Never use browser zoom as the main framing control.
- Keep the raw capture video, screenshots, capture manifest, and reviewer report on every attempt. Keep a trace too when the Playwright fallback is used.
- Use reviewed footage to steer the final storyboard. Clips marked `warn` can support the story, but should not become the hero proof moment without a clear caveat.
- The reviewer is not an external API distinction. If the skill is running, the reviewer is a spawned Codex/Claude sub-agent looking at extracted images.

## Workflow

### 1. Prepare Cathode

- Run `python3 scripts/bootstrap_cathode.py --repo-path /path/to/cathode` when Cathode is already checked out locally.
- Run `python3 scripts/bootstrap_cathode.py` only when no usable checkout exists.
- Treat missing `python3.10`, `ffmpeg`, or `espeak-ng` as blockers. Surface them instead of improvising around them.

### 2. Prepare A Live Capture Session

- Run `python3 scripts/prepare_live_demo_session.py --target-repo-path /abs/path/to/repo --output-dir /abs/path/to/output/live_demo/<slug>`.
- Pass `--app-url` when the app already exists.
- Pass `--launch-command` and `--expected-url` when local boot is required and inference is weak.
- Add `--flow-hint` notes for the interaction beats you want the walkthrough to cover.

The session manifest is the source of truth for:

- preferred capture driver
- explicit theme
- explicit viewport
- artifact directories
- retry policy
- launch expectations

### 3. Launch Or Attach To The App

- Use `python3 scripts/launch_target_app.py --session-json /abs/path/to/session.json` for local apps.
- If the app is already running, the script will just verify reachability and record attachment state.
- Stop a launched app with `python3 scripts/launch_target_app.py --session-json /abs/path/to/session.json --stop`.

### 4. Capture Fresh Footage

- Default path: use the desktop-use / Computer Use surface available in Codex or Claude Code to drive the real app in a visible window.
- Start a local screen recording before the walkthrough so the hero state and interactions are preserved as real proof footage.
- Capture checkpoint screenshots as you go. Use those screenshots plus your timing notes to build a `clips.json`, then run:

```bash
python3 scripts/build_capture_manifest.py \
  --session-json /abs/path/to/session.json \
  --raw-video-path /abs/path/to/raw_capture.mp4 \
  --clips-json /abs/path/to/clips.json
```

- The `clips.json` can be either a raw array or an object with `clips`. Each clip should include:
  - `id`
  - `label`
  - `start_seconds`
  - `end_seconds`
  - `screenshot_path`
  - optional `focus_box`, `text_excerpt`, `notes`, `review_status`
- Use `python3 scripts/capture_live_demo.py --session-json ... --capture-plan ...` only when you need the Playwright fallback for selector-driven replay, trace capture, or headless/CI execution.

### 5. Review Before Handoff

- Extract representative frames with `python3 scripts/extract_review_frames.py`.
- Spawn a worker sub-agent and attach only those images. Do not front-load repo context, clip ids, or JSON schema into the reviewer prompt.
- In Codex, prefer `spawn_agent` with a `text` item for the short prompt plus `local_image` items from `review_frames.json`. The parent agent stays responsible for clip mapping and final judgment.
- Use this prompt shape:

```text
Hey, check out my demo vid.
If this were your software, would you want to blast it on Hacker News?
Carefully inspect every image and tell me bluntly what feels strong, weak, embarrassing, unreadable, or not ready.
```

- Read the sub-agent response yourself, convert it into structured review observations JSON, then run `python3 scripts/review_bundle.py`.
- Save the raw response into `reports/subagent_qc_raw.md` before you summarize it.
- Seed a parent-agent working file with:

```bash
python3 scripts/init_review_observations.py \
  --bundle-manifest /abs/path/to/processed_manifest.json \
  --review-frames-manifest /abs/path/to/review_frames/review_frames.json \
  --raw-review-path /abs/path/to/reports/subagent_qc_raw.md \
  --output-json /abs/path/to/reports/review_observations.template.json
```

- Fill that template yourself after reading the raw sub-agent feedback, save the finished JSON as `review_observations.json`, then run:

```bash
python3 scripts/review_bundle.py \
  --bundle-manifest /abs/path/to/processed_manifest.json \
  --observations-json /abs/path/to/reports/review_observations.json \
  --raw-review-path /abs/path/to/reports/subagent_qc_raw.md \
  --output-json /abs/path/to/reports/review_report.json
```
- The report must end in one of:
  - `accept`
  - `warn`
  - `retry`
- If the report says `retry`, follow only the bounded retry actions it recommends.
- Build the next plan with `python3 scripts/apply_retry_actions.py --capture-plan /abs/path/to/capture_plan.json --review-report /abs/path/to/review_report.json --output-json /abs/path/to/capture_plan.retry.json`.
- If you are on the Playwright fallback, rerun `capture_live_demo.py`.
- If you are on the desktop-use path, rerun the walkthrough with a fresh local recording, then rebuild the manifest with `build_capture_manifest.py`.
- If the best available result is still imperfect, ship `warn` with a concrete heads-up instead of pretending it looks ideal.
- After the final MP4 is rendered, extract final-render frames and run the same sub-agent review one more time before calling the demo finished.

### 6. Hand Off To Cathode

- Run `python3 scripts/prepare_cathode_handoff.py` with the bundle manifest, review report, target repo path, and demo brief fields.
- Feed the generated JSON into `make_video`.
- Cathode now accepts `footage_paths` and `footage_manifest`; prefer `footage_manifest` so reviewed clip status and notes survive into the project.

### 7. Drive Cathode

Use `make_video` with repo context plus reviewed footage. Typical fields:

```json
{
  "intent": "Create a 90-second product demo for this local web app.",
  "workspace_path": "/abs/path/to/repo",
  "source_paths": [
    "/abs/path/to/repo/README.md",
    "/abs/path/to/repo/docs/getting-started.md"
  ],
  "audience": "technical buyers evaluating the product",
  "target_length_minutes": 1.5,
  "tone": "clear, technical, grounded",
  "visual_style": "clean editorial product demo",
  "visual_source_strategy": "mixed_media",
  "footage_manifest": [
    {
      "id": "run_review",
      "path": "/abs/path/to/processed/run_review.mp4",
      "label": "Run review overlay",
      "notes": "Saved overlay playback with diagnostics cards visible.",
      "review_status": "accept"
    }
  ],
  "run_until": "render"
}
```

## Resources

- `scripts/bootstrap_cathode.py`: prepare or reuse a Cathode checkout
- `scripts/prepare_live_demo_session.py`: create a deterministic capture bundle
- `scripts/launch_target_app.py`: boot or attach to the target app
- `scripts/build_capture_manifest.py`: turn a desktop-use recording plus clip notes into the standard capture manifest
- `scripts/capture_live_demo.py`: run the packaged Playwright fallback capture flow from a capture plan
- `scripts/apply_retry_actions.py`: mutate a capture plan using bounded retry actions
- `scripts/postprocess_capture.py`: trim and crop raw capture clips into Cathode-ready footage
- `scripts/extract_review_frames.py`: extract review frames for the spawned QC sub-agent
- `scripts/init_review_observations.py`: seed a parent-editable observations template from the frame bundle
- `scripts/review_bundle.py`: validate structured review observations and compute retry actions
- `scripts/prepare_cathode_handoff.py`: build the `make_video` payload from the reviewed bundle
