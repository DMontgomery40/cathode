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
- 2026-03-14: active implementation restarted for the motion-first 3D failure. Root cause confirmed from `/Users/davidmontgomery/cathode/projects/moth_orrery_api_1773538729/plan.json`: `_apply_composition_mode_to_scenes()` pre-seeds `motion.template_id` from `infer_motion_template()`, long narration pushes the hero tableau into `quote_focus`, and `plan_scene_compositions()` then preserves that weak family instead of re-evaluating the 3D/tableau/orbit cues.
- 2026-03-14: official doc set locked for this overhaul because future agents should not have to rediscover it:
  - <https://www.remotion.dev/docs/player>
  - <https://www.remotion.dev/docs/sequence>
  - <https://www.remotion.dev/docs/transitions/transitionseries>
  - <https://www.remotion.dev/docs/three>
  - <https://www.remotion.dev/docs/ai/system-prompt>
  - <https://www.remotion.dev/prompts>
- 2026-03-14: execution order tightened:
  1. Write active project-local memory and keep it updated during implementation.
  2. Fix planner classification so explicit 3D/tableau scenes stop becoming text cards.
  3. Rebuild `surreal_tableau_3d` into a semantic deterministic renderer.
  4. Unify motion-scene editing on canonical `scene.composition`.
  5. Add a repo skill pack and handoff references so future agents have a zero-search Cathode/Remotion path.
- 2026-03-14: planner-side fix completed and verified.
  - `_apply_composition_mode_to_scenes()` now seeds motion scenes neutrally instead of pre-classifying them from narration length.
  - `core/composition_planner.py` now has explicit 3D/tableau/orbit heuristics and semantic `surreal_tableau_3d` props.
  - `core/project_schema.py` now mirrors generic `kinetic_title` seeds back to canonical `scene.composition.family`.
  - Python changed-surface verification: `50 passed`.
- 2026-03-14: frontend and workflow contract updates completed.
  - Added `@remotion/three`.
  - Rebuilt `surreal_tableau_3d` into a semantic deterministic scene family in `frontend/src/remotion/index.tsx`.
  - Unified motion-scene editing on canonical `scene.composition` in `frontend/src/features/scenes/SceneInspector.tsx`.
  - Added workflow role split so the product path uses Claude/Anthropic for scene writing and OpenAI for deterministic treatment/machinery when available.
  - Added repo skill pack at `skills/cathode-remotion-development/` plus Claude mirror.
- 2026-03-14: live validation surfaced two real classifier false positives that unit tests had missed.
  - Software-demo hints were matching raw substrings (`screen` in `widescreen`, `form` in `performs`).
  - Bullet-stack hints were matching the generic word `sequence`.
  - Both were tightened after replaying a real UI-created observatory brief.
- 2026-03-14: live validation still shows a separate operator bug in the async one-click `make_video` path.
  - Background job can remain `running` at `storyboard` with no visible progress change.
  - That is tracked as a real gap from this turn, not hand-waved away.
- 2026-03-15: live validation against the fresh UI-created observatory brief completed.
  - Project: `/Users/davidmontgomery/cathode/projects/moth_observatory_ui_1773542716609`
  - Hero scene now persists as `surreal_tableau_3d` and exposes semantic 3D controls in the browser.
  - Audio generation completed for all scenes and final render completed at `/Users/davidmontgomery/cathode/projects/moth_observatory_ui_1773542716609/final_video.mp4`.
  - Captured validation artifacts live under `/tmp/cathode-remotion-validation/`.
- 2026-03-15: Projects library sorting no longer relies on alphabetical order alone.
  - `/api/projects` now exposes `created_utc` and `updated_utc`.
  - `updated_utc` prefers real plan lifecycle timestamps (`updated_utc`, `rendered_utc`, `created_utc`) and only falls back to `plan.json` mtime when a project has no stored dates, to avoid git-checkout noise masquerading as activity.
  - The React Projects index now defaults to creation-date order and exposes `Newest first`, `Oldest first`, `Recently updated`, and `A to Z` controls.
  - Coverage added in `tests/test_server_api.py` and `frontend/e2e/projects.spec.ts`.
- 2026-03-15: compacted the Scenes inspector header to reclaim vertical space for actual controls.
  - `Scene controls`, the scene chip, and save state now share the same horizontal band instead of stacking in a tall utility column.
  - `Collapse Panel` stays available but no longer burns a full extra header tier.
  - Coverage added in `frontend/e2e/scenes.spec.ts` to keep the header compact.
- 2026-03-15: investigated Remotion's full-video Three.js ranking prompt as a benchmark Cathode does not currently meet.
  - Official benchmark prompt: `https://www.remotion.dev/prompts/threejs-top-20-games-sold-ranking-1`
  - The prompt target is a single full 1920x1080 60fps 3D video with a programmed camera journey from rank 20 to rank 1, not a small per-scene 3D treatment.
  - Cathode's current `three_data_stage` is not that. It is a four-item bar stage with overlay labels and a mild turntable camera.
  - Cathode currently lacks a reusable registry family for a full-video 3D ranking world with structured item records, environment components, and timeline-driven camera stops.
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
