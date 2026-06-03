# betTube Studio Remotion Architecture

## What betTube Studio Is

betTube Studio is a local-first explainer-video pipeline with three user-facing surfaces:

- React + FastAPI control room
- legacy Streamlit app
- MCP server

The product creates a local project under `projects/<project>/`, persists `plan.json`, generates scene media and narration, then renders a final MP4 through `ffmpeg` or Remotion.

## Read These Files First

- `AGENTS.md`
- `CLAUDE.md`
- `README.md`
- `docs/PLAN.md`
- `core/director.py`
- `core/composition_planner.py`
- `core/treatment_planner.py`
- `core/project_schema.py`
- `core/workflow.py`
- `core/remotion_render.py`
- `frontend/src/remotion/index.tsx`
- `frontend/src/features/scenes/SceneInspector.tsx`

## Canonical Data Flow

1. Brief capture:
   - React Brief Studio, Streamlit, or MCP gathers the brief.
2. Workflow orchestration:
   - `core/pipeline_service.py`
3. Creative scene writing:
   - `core/workflow.py`
   - `core/director.py`
   - In product workflow mode, Claude/Anthropic is the creative writer for scene content.
4. Deterministic composition assignment:
   - `core/composition_planner.py`
5. Deterministic treatment override:
   - `core/treatment_planner.py`
   - In product workflow mode, OpenAI is the machinery/treatment layer when available.
6. Normalization and persistence:
   - `core/project_schema.py`
   - `projects/<project>/plan.json`
7. Manifest projection:
   - `core/remotion_render.py`
8. Player + final renderer:
   - `frontend/src/remotion/index.tsx`
   - `frontend/scripts/render-remotion.mjs`

## Core Contract

- `scene.composition` is canonical.
- `scene.motion` is a compatibility mirror of the same intent for older paths and runtime helpers.
- `projects/<project>/plan.json` is the source of truth for saved storyboard state.
- Manual editing of a project plan is for debugging only and must never be used to fake product capability.

## Product Rules That Matter

- Pure creative briefs stay image-first by default.
- Remotion treatment is a second planner layer, not the director's main job.
- Remotion remains registry-based. No arbitrary model-authored TSX.
- A scene family is only real if:
  - the planner can assign it
  - the Scene inspector can edit it
  - the Remotion manifest can project it
  - the player/final render visibly express it
