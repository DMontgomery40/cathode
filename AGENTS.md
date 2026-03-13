# Repository Agents (Cathode)

This file is for AI agents working in this repo.

## Start Here

1. Read `CLAUDE.md` first.
2. Treat `projects/<project>/plan.json` as the source of truth for storyboard state.
3. Keep pipeline behavior generic and product-facing. Do not reintroduce domain-specific workflows.

## What Cathode Is

Cathode has two main surfaces:

- `app.py`: the local Streamlit app
- `cathode_mcp_server.py`: the MCP server for agent/client integrations

Both rely on the same underlying pipeline services and project store.

## Core Contract

- Input is brief-driven.
- Source modes:
  - `ideas_notes`
  - `source_text`
  - `final_script`
- Scene types:
  - `image`
  - `video`
- Output is a local project folder plus a rendered MP4.

## Important Files

- `projects/<project>/plan.json`: normalized storyboard, metadata, and asset paths
- `projects/<project>/.cathode/jobs/*.json`: persisted background job state
- `prompts/`: director and refiner prompts
- `core/pipeline_service.py`: shared app/batch/MCP execution helpers
- `core/project_store.py`: project persistence
- `core/job_runner.py`: background execution
- `core/runtime.py`: provider discovery and profile resolution

## Live Demo Skill

Cathode now ships a packaged live-demo skill:

- canonical path: `skills/cathode-project-demo/`
- Claude mirror: `.claude/skills/cathode-project-demo/`

Treat this as a generic product-demo workflow, not a repo-specific shortcut. It is for:

- booting or attaching to a live app
- capturing fresh footage
- reviewing the capture through a spawned reviewer sub-agent before handoff
- passing reviewed clips into Cathode as `footage_paths` or `footage_manifest`

Do not assume README screenshots exist or are good enough. Fresh captured footage is the default.
The reviewer sub-agent should be given frames and a short gut-check prompt, not a long JSON-heavy briefing.
Save the raw reviewer reply in the bundle, then have the parent agent translate it into the structured observations/report that Cathode uses for retry logic and handoff.
Use the packaged `capture_live_demo.py` script for deterministic browser capture and `apply_retry_actions.py` when the review report recommends another bounded attempt.

## Provider UX

- Keep provider selection env-driven.
- Only surface providers in the UI when they are actually configured.
- Preserve the local/manual visual path when cloud image generation is unavailable.
- Do not turn the UI into a giant provider control panel.

## Frontend Parity Rules

- Do not call the React/FastAPI app "done" or "parity" unless the real user-facing controls are wired, placed sensibly, and verified in the browser.
- A feature does not count if the button exists in code but is hidden in an unrelated panel, route, collapsed section, or header slot that users would not reasonably use for that task.
- Scene-level work must stay in the Scenes workspace. Image generation, image editing, audio generation, preview generation, and direct scene media replacement should be accessible from the scene inspector and/or media stage, not only from some distant project page.
- Project-level media libraries are allowed, but they do not replace the need for scene-level upload/replace controls that actually work.
- If a route claims Streamlit parity, verify the actual Streamlit affordance exists in the React app with a comparable outcome, not just a vaguely related control somewhere else.
- Do not treat "backend endpoint exists" or "Playwright route interception passed" as sufficient proof that the feature is genuinely usable.

## Frontend Verification Rules

- For important UI claims, verify in a real browser against the live app, not only with static code inspection.
- When fixing upload/generation actions, verify the full loop:
  - trigger control
  - network request
  - persisted `plan.json` update
  - visible UI update in the relevant workspace
- When fixing layout or placement, verify at realistic desktop widths and at least one narrower width where panels compress or scroll.
- If a control is moved, update or add browser coverage so the test asserts the new expected location and behavior.

## Operator UX Rules

- Long-running or failure-prone operations need visible operator feedback in the app: pending state, useful error text, and enough context to understand what Cathode tried to do.
- Prefer showing the effective request parameters for provider-backed actions when they materially affect output quality.
- Persisted job logs should be surfaced through the product where practical; do not hide them as backend-only artifacts.
- Unexpected API failures should return structured JSON with a concise operator hint rather than a blank 500 page or generic browser error.

## Image Actions

These are intentionally different:

- `Generate/Regenerate Image`: create a new image from prompt
- `Edit Image`: surgically modify an existing image
- `Refine Prompt`: rewrite prompt text with the LLM

## Guardrails

- Keep docs, prompts, and UI labels domain-agnostic.
- Favor the fast default workflow first; present fine-tuning as optional power.
- Keep MCP tool behavior practical and bounded.
- Do not add external publish/QC systems or work-specific automations to this fork.
- Keep reviewed footage plumbing generic. Do not add domain-specific capture or review logic to core Cathode.
