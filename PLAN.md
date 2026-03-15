# Restore Creative-Brief Quality First, Then Add a Remotion Treatment Planner

## Summary
Restore the old “masterpiece” behavior for pure creative briefs by making the default path image-first again and fixing the director prompt/example shelf so Claude leads with rich visual art direction instead of renderer-aware pseudo-structure.

Then add a second, optional Remotion treatment-planner stage that is informed by a repo-local adaptation of the official Remotion AI system prompt. That second stage may choose Cathode-supported motion treatments, transitions, timing, and 3D families, but it must stay inside Cathode’s fixed composition registry and must not generate arbitrary TSX.

## Key Changes
- Re-split planning into two stages:
  - `director`: creative, narrative, visual art direction only
  - `treatment planner`: Remotion-aware staging only, after storyboard generation
- Keep the director output thin and creative:
  - `scene_type`, `visual_prompt`, `on_screen_text`, `staging_notes`, `data_points`, `transition_hint`, and optional high-level treatment hints
  - Do not teach the director raw Remotion APIs or component mechanics
- Rewrite the default creative-brief prompt path so pure whimsical/editorial/storybook briefs are optimized for image-first visual richness again.
- Replace the current always-on default example bias:
  - stop using the abstract `static_image_control` / `pure_creative_concept` shelf as the universal fallback for all creative briefs
  - add a separate promoted example shelf for whimsical narrative / contradictory / storybook / surreal creative briefs
  - keep product-demo, quote, ranked-data, and software-demo examples behind explicit intent selection instead of defaulting them into unrelated briefs
- Add a new Remotion treatment-planner prompt under `prompts/` based on the official Remotion AI system prompt, but adapted to Cathode constraints:
  - fixed composition registry only
  - allowed families, transitions, timing rules, overlays, and R3F usage
  - deterministic behavior only
  - no arbitrary code generation
- Keep the main creative default image-first:
  - pure creative briefs should remain classic/image-led unless the brief explicitly asks for motion, exact staged text, demo treatment, or structured data
  - treatment upgrades should not silently convert whimsical briefs into generic motion beats
- Expand the composition registry with at least one non-data creative 3D family.
  - Current `three_data_stage` is data/ranking specific and cannot serve briefs like the cat/jellyfish example.
  - Add a generic creative 3D family for surreal hero-object / symbolic-duet / tableau-style scenes so Remotion has a real path for imaginative briefs.
- Preserve `scene.composition` as the canonical normalized output.
  - Keep the existing asset fields.
  - Keep legacy `scene.motion` and `composition_intent` read-compatibility.
  - Continue mapping everything into canonical `scene.composition` in core pipeline code, not in UI.
- Add operator visibility for why a project/scene was treated a certain way:
  - concise treatment rationale on scenes
  - concise resolved render-engine reason on render metadata
- Simplify the React brief flow:
  - remove or demote `Scene Engine` and `Text Strategy` from the main happy path
  - keep advanced overrides available in an operator-facing advanced area
  - React/FastAPI is the primary acceptance surface; Streamlit should consume the same backend behavior without needing a separate design pass

## Public Interfaces / Types
- Keep the existing normalized `scene.composition` contract as the canonical output.
- Add only minimal new metadata where needed:
  - scene-level treatment rationale string
  - render-level resolved backend reason string
- Do not introduce arbitrary Remotion code blobs, TSX payloads, or freeform component specs into `plan.json`.
- The treatment planner may add family/mode/props/transition/data choices only within the existing typed composition model plus the new creative 3D family.

## Test Plan
- Director tests:
  - a whimsical contradictory brief selects the new creative-intent/example shelf, not the abstract AI/product shelf
  - pure creative briefs stay image-first by default
  - product/demo/data prompts still select the existing specialized shelves
- Golden/example tests:
  - add promoted examples for whimsical narrative creative work
  - verify those examples parse, normalize, and produce valid plans without forcing irrelevant motion families
- Composition/treatment tests:
  - pure creative brief does not auto-route to `three_data_stage`
  - explicit motion/text/demo/data briefs still route into supported motion families
  - new creative 3D family normalizes cleanly into `scene.composition`
- Manifest/render-selection tests:
  - classic whimsical project stays ffmpeg-eligible unless it actually uses Remotion-only features
  - upgraded creative treatment project selects Remotion with a clear backend reason
  - new creative 3D family renders through the Remotion registry
- Frontend tests:
  - main brief flow no longer foregrounds engine/text knobs
  - scene and render previews still work with the treatment-planner output
  - generated creative brief shows image-first scenes unless explicit motion/treatment signals are present

## Assumptions And Defaults
- Default pure creative briefs remain image-first.
- Remotion treatment is a second planner layer, not the director’s primary job.
- The official Remotion AI system prompt is distilled into repo-local prompts and constraints; it is not fetched live at runtime.
- Cathode continues to use a fixed Remotion registry, not arbitrary model-authored TSX.
- v1 of this fix prioritizes restoring creative quality first; treatment-planner upgrades are additive and conservative, not automatic for every whimsical brief.

## Implementation Notes
- Status: in progress
- 2026-03-14: starting with guardrail updates in `AGENTS.md` and `prompts/AGENTS.md` before changing the planner pipeline.
- 2026-03-15: completed repo/prompt guardrail updates.
- 2026-03-15: completed director prompt reset plus intent-specific example selection, including a promoted `whimsical_storybook__v1` example harvested through the director-golden workflow.
- 2026-03-15: completed initial treatment-planner stage and wired it into create/rebuild flows with registry-only composition overrides.
- 2026-03-15: completed initial non-data creative 3D family (`surreal_tableau_3d`) plus operator-facing composition/render reasons.
- 2026-03-15: completed React Brief Studio advanced-control demotion and verified it in the live browser.
- 2026-03-15: verification completed
  - Python changed-surface tests: passing
  - Frontend build: passing
  - Playwright `brief.spec.ts`: passing
  - Playwright `render.spec.ts` plus `scenes.spec.ts`: changed-surface assertions pass after fixing a real `SceneInspector` hook-order bug; one separate prompt-refine e2e remains failing and appears unrelated to the creative-director/treatment-planner work.
- 2026-03-14: implementation order
  1. Fix repo guardrails and prompt guardrails.
  2. Repair director prompt/example selection for pure creative briefs.
  3. Add a Remotion-aware treatment planner that stays registry-based.
  4. Expand the Remotion registry with a non-data creative 3D family and operator-facing reasons.
  5. Simplify the React brief flow and lock behavior with tests.
