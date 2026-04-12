# Repository Agents (Cathode)

This file is for AI agents working in this repo.

## Start Here

0. **You MUST read ~/.codex/this/project/MEMORY.md and all links within to understand this repo and it's components**
   It is CRITICAL AND MANDATORY THAT YOU UPDATE MEMORY.md with anything that a future agent would need to know
    *The MEMORY.md file for this project should be treated as a TABLE OF CONTENTS, linking to other consisely worded well-named .md files*
1. Read `CLAUDE.md` 
2. Treat `projects/<project>/plan.json` as the source of truth for storyboard state.
3. Keep pipeline behavior generic and product-facing. Do not reintroduce domain-specific workflows.

## What Cathode Is

Cathode has two main surfaces:

- `app.py`: the local Streamlit app
- `cathode_mcp_server.py`: the MCP server for agent/client integrations

Both rely on the same underlying pipeline services and project store.

## Core Contract

- Input is brief-driven.
- The brief wizard / Brief Studio is the canonical product entrypoint.
- Source modes:
  - `ideas_notes`
  - `source_text`
  - `final_script`
- Scene types:
  - `image`
  - `video`
  - `motion`
- Output is a local project folder plus a rendered MP4.

## Important Files

- `projects/<project>/plan.json`: normalized storyboard, metadata, and asset paths
- `projects/<project>/.cathode/jobs/*.json`: persisted background job state
- `core/director.py`: storyboard generation logic and source-mode behavior
- `prompts/`: director and refiner prompts
- `core/pipeline_service.py`: shared app/batch/MCP execution helpers
- `core/project_store.py`: project persistence
- `core/job_runner.py`: background execution
- `core/runtime.py`: provider discovery and profile resolution

## Pipeline Integrity Rules

- Do not bypass the brief -> director -> normalized plan pipeline for product work.
- Do not bypass, demote, or misdescribe the brief wizard / Brief Studio. It is how Cathode captures intent, source material, and constraints before the pipeline runs.
- Preserve the one-click raw-brief flow that powers the primary Brief Studio button. New prompt or planner work must keep the `make_video` path capable of turning a raw user dump into a finished project without hand-authored scene content.
- Do not describe storyboard generation as fake, optional, or something the product should skip past. Storyboard planning is a core product step, even when later stages run automatically in the background.
- If the brief flow is missing fields or cannot express a needed behavior, extend the brief schema and wiring instead of inventing side channels or per-project overrides.
- If Cathode needs to support a new storytelling pattern, scene shape, or media-planning behavior, update the real pipeline:
  - `core/director.py`
  - the relevant prompts under `prompts/`
  - normalization/schema code when required
- Do not hand-author one-off storyboard copy, scene lists, motion cards, or `plan.json` content inside `projects/<project>/` to simulate a feature that the pipeline does not actually support.
- Do not treat a manually written project folder as an acceptable implementation of new product behavior, even for demos or urgent user requests.
- If the requested output cannot be produced cleanly through the existing pipeline, stop and fix the pipeline or explicitly report the gap. Do not paper over it with custom per-project content.
- `projects/<project>/plan.json` is the persisted result of the pipeline, not a scratchpad for ad hoc authored scenes.
- When working from `final_script`, preserve the user's script and let the director do the segmentation/planning work. Do not replace that flow with a manually assembled project.

## Paid Generation Guardrails

- Before making paid image, video, or TTS calls for a new capability, first verify that the director/prompt/schema path is producing the right storyboard structure.
- Keep paid-cost logic centralized. Price hints, preflight estimates, and actual-cost recording should come from a shared catalog/ledger layer rather than hardcoded UI strings or one-off provider checks.
- Do not hand-author prompt examples or fake “golden” storyboard outputs. Prompt examples must be harvested from Anthropic through the director-golden workflow, then curated and promoted.
- Prefer local inspection, tests, dry runs, or storyboard-only regeneration before spending paid generation calls on assets.
- Do not spend paid generation calls on a one-off bypass path that would be thrown away instead of improving the product.
- If the pipeline behavior is still wrong, pause before more paid calls and fix the pipeline first.

## Director Contract Rules

- Claude gets the full normalized brief plus the full raw user input.
- In Cathode's product workflow, Claude/Anthropic is the creative scene writer. OpenAI may handle downstream deterministic machinery or treatment planning, but should not replace Claude as the scene author.
- Brief options select capability blocks and examples for the director prompt; they do not replace the core prompt or the raw user dump.
- Remotion is not “extra UI stuff.” It is Cathode’s deterministic manifestation layer for scenes that Claude dreams up.
- Pure creative briefs should remain image-first by default. Do not silently drag whimsical, editorial, surreal, or storybook briefs into generic motion treatment unless the brief clearly asks for motion/data/demo structure or a downstream treatment planner has an explicit product reason to do so.
- Keep the model-facing scene contract thin. Avoid forcing Claude to emit brittle nested renderer schemas when Cathode can map creative signals into deterministic composition internally.
- The director owns narrative and art direction. If Cathode needs Remotion-aware staging, transitions, timing, or 3D treatment selection, add a second planner stage after storyboard generation rather than bloating the director prompt with renderer mechanics.
- Do not ask the director to generate arbitrary Remotion TSX or freeform component code. Cathode remains registry-based.
- Preserve backward compatibility for stored plans that still carry older composition-hint fields.

## Prompt Example Rules

- Raw corpus artifacts belong under ignored `experiments/director_golden/`.
- Promoted examples belong under tracked `prompts/director_examples/`.
- Do not move raw Anthropic transcripts into `prompts/`.
- A promoted example is not valid unless it parsed, normalized through Cathode’s planner, produced a valid Remotion manifest, and yielded at least a preview/frame.
- Match promoted examples to the brief intent. Do not let one abstract or product-oriented example shelf become the implicit default for unrelated whimsical/storybook briefs.

## Memory Rules

- Update project-local Codex memory as material repo truths are discovered.
- For this repo, use `/Users/davidmontgomery/.codex/projects/-Users-davidmontgomery-cathode/MEMORY.md` and its sibling `memory/` directory.
- Do not write repo-specific memory into global cross-project memory locations.

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

## Remotion Development Skill

Cathode now ships a packaged Remotion-development skill:

- canonical path: `skills/cathode-remotion-development/`
- Claude mirror: `.claude/skills/cathode-remotion-development/`

Use it when tracing or extending the Cathode Remotion path so future agents do not have to rediscover:

- the planner -> schema -> treatment -> manifest -> renderer flow
- the canonical `scene.composition` contract
- the repo's Remotion family contracts
- the official Remotion docs that matter first

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
- When provider/model choice materially changes spend, surface the cost basis where the choice is made and again where the resulting plan is estimated. Do not hide meaningful price deltas behind one default label.
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
- Do not solve product gaps by manually authoring project-specific output. Solve them in the reusable pipeline.

**It is CRITICAL AND MANDATORY THAT YOU UPDATE MEMORY.md with anything that a future agent would need to know**
