---
name: cathode-remotion-development
description: Debug and extend Cathode's Remotion planning and renderer pipeline without rediscovering the architecture. Use when an agent needs to trace a scene from brief to plan to treatment to Remotion manifest to final render, fix a misclassified motion or 3D scene, or validate that a Remotion feature is real in the browser and final MP4.
---

# Cathode Remotion Development

Use this skill when the problem is inside Cathode's Remotion path, not just a generic frontend bug.

Start here:

1. Read [references/cathode-remotion-architecture.md](references/cathode-remotion-architecture.md).
2. Read [references/scene-family-contracts.md](references/scene-family-contracts.md).
3. Open [references/official-remotion-docs.md](references/official-remotion-docs.md) before redesigning a composition.
4. Use [references/remotion-ecosystem-starter.md](references/remotion-ecosystem-starter.md) only when you need an officially supported adjacent path such as the Next.js starter or Editor Starter.

## What This Skill Is For

- tracing a scene from brief to `projects/<project>/plan.json`
- debugging why a motion or 3D scene was misclassified
- extending a composition family in `frontend/src/remotion/index.tsx`
- validating whether the React Scenes and Render workspaces actually expose and render a Remotion family correctly
- preserving Cathode's rule that `scene.composition` is canonical and manual `plan.json` edits are not a feature path

## Guardrails

- Claude/Anthropic writes scenes. OpenAI handles machinery/treatment when the product workflow is used.
- Do not hand-author `projects/<project>/plan.json` to fake a capability.
- Do not ask the director for arbitrary TSX or renderer APIs.
- Keep `scene.composition` canonical. `scene.motion` is compatibility/mirroring only.
- A Remotion fix is not done until it is verified in the live browser and in a final render, not only by reading code.

## Quick Debug Flow

1. Inspect the saved project at `projects/<project>/plan.json`.
2. Trace the scene through:
   - `core/director.py`
   - `core/composition_planner.py`
   - `core/treatment_planner.py`
   - `core/project_schema.py`
   - `core/remotion_render.py`
   - `frontend/src/remotion/index.tsx`
3. Confirm whether the bug is:
   - wrong creative scene writing
   - wrong family assignment
   - wrong treatment override
   - wrong manifest projection
   - wrong renderer implementation
   - wrong UI/editor affordance
4. Run changed-surface tests first.
5. Verify the actual workspace in a real browser.
6. Render a fresh project through the real product flow.

## Validation Standard

- The saved `plan.json` shows the expected `scene.composition.family`.
- The Scenes workspace exposes the right editing controls for that family.
- The Render workspace player shows the right visual behavior.
- The final MP4 still reads as the same scene and not a fallback text card.
