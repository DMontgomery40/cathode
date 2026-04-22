# Dev Demo Workflow

Use this reference when the user wants a video about a software project, product repo, SDK, CLI, internal tool, or live web app.

## Fast Path

1. Confirm the repo to showcase.
2. Bootstrap Cathode with `scripts/bootstrap_cathode.py`.
3. Prepare a fresh live-capture session and capture walkthrough footage before you build the final Cathode payload.
4. Start Cathode over MCP when the whole flow should stay agent-driven.
5. Pass the target repo as `workspace_path`.
6. Add only the most useful `source_paths`.
7. Render first, then tighten scenes only if the first pass misses the story.

## What To Pull From The Repo

Prefer high-signal files that explain what the project does and why it matters:

- `README.md`
- `docs/*.md` or launch notes
- `package.json`, `pyproject.toml`, `Cargo.toml`, `go.mod`, or `requirements.txt`
- top-level app entrypoints such as `app.py`, `main.py`, `index.tsx`, or `server.ts`

Do not overload the brief with source files that only contain implementation detail. Cathode already uses bounded excerpts. The goal is product story, not architecture archaeology.

## Dev-Demo Defaults

- Audience: prospective users, internal stakeholders, or technical buyers
- Runtime: 1.0 to 2.0 minutes
- Tone: clear, technical, credible
- Visual style: clean editorial product demo
- CTA: try the repo, book a demo, approve rollout, or start a pilot

## Visual Strategy

Use `mixed_media` when the user has any of the following:

- screen recordings
- product walkthrough clips
- dashboard states
- terminal recordings
- interview or founder camera footage

Use `images_only` when the repo is still pre-launch, the UI is unstable, or the user only has notes and screenshots.

Use `video_preferred` when the footage itself is the story and still images should only bridge gaps.

For browser-based products, a strong default is:

- first half: narrated slides or motion-graphic explainers that frame the problem and value
- second half: live product walkthrough driven by real clicks, hovers, and state changes

This keeps the story clear while still proving the product is real.

## Live Product Capture

When the demo depends on showing a running app:

1. Inspect the target repo or running environment first so the walkthrough uses real states.
2. Capture the strongest interaction path with desktop-use in a real visible app window.
3. Use explicit viewport and explicit theme on every attempt.
4. Prefer short deliberate beats with meaningful state changes over a long raw session.
5. Postprocess raw capture video into focused clips, extract review frames, run a short-prompt spawned sub-agent gut check, save that raw reply, then feed only the approved clips into Cathode.

Use the older Playwright capture flow only when you explicitly need selector-driven replay, a trace zip, or headless/CI coverage.

Use this pattern for flows like:

- onboarding
- dashboard exploration
- code-to-result workflows
- settings or configuration changes
- before/after result states

## Brief Construction

Anchor the intent in business value and the main workflow. Good intents usually sound like:

- "Create a 90-second demo video for this open-source deployment tool."
- "Make a concise launch video for this SDK aimed at backend engineers."
- "Turn this internal product spec and repo into a walkthrough for the engineering org."

Include:

- who the video is for
- what problem the tool solves
- what workflow to show
- why it is better, faster, cheaper, or safer
- what action the viewer should take next

## MCP Pattern

This is a strong starting shape for `make_video`:

```json
{
  "intent": "Create a 75-second product demo for this repo.",
  "workspace_path": "/abs/path/to/repo",
  "source_paths": [
    "/abs/path/to/repo/README.md",
    "/abs/path/to/repo/package.json"
  ],
  "audience": "developers evaluating adoption",
  "target_length_minutes": 1.25,
  "tone": "clear, technical, grounded",
  "visual_style": "clean editorial product demo",
  "visual_source_strategy": "mixed_media",
  "available_footage": "Onboarding flow, dashboard tour, and one CLI recording.",
  "must_include": "Problem, setup moment, core workflow, differentiator, CTA.",
  "run_until": "render"
}
```

## Review Loop

After submission:

1. Poll `get_job_status` until the job completes or fails.
2. If the storyboard is weak, read `project://{project_name}/plan`.
3. If only visuals or narration need work, rerun the narrowest stage instead of rebuilding everything.
4. Report the final local MP4 path back to the user.
