# Architecture Overview

betTube Studio turns a written brief into a rendered explainer MP4. Everything is local-first: state lives in `projects/<name>/plan.json` plus generated asset files — no database.

## Surfaces

- **FastAPI server** (`server/app.py`, factory `create_app()`): serves `/api/*` and the built React SPA from one origin. Routers live in `server/routers/`: `bootstrap` (provider discovery + defaults), `projects`, `plans`, `scenes`, `media`, `jobs` (background job model), `footage`, `style_refs`, `short_form`, `settings`.
- **React SPA** (`frontend/`): Vite + React 19 + TanStack Query + Zustand. Routes: Home, Projects, Brief, Scenes, Render, Queue (project + global), Short Form, Settings. The API client (`frontend/src/lib/api/client.ts`) is env-driven via `VITE_API_BASE_URL` and defaults to same-origin `/api`.
- **MCP server** (`bettube_studio_mcp_server.py`): FastMCP tools (`make_video`, `get_job_status`, `cancel_job`, `rerun_stage`, `list_projects`) over stdio or Streamable HTTP. Converges on the same persisted job model as the web API.

## Pipeline (core/)

```
brief ──> director ──> treatment_planner ──> composition_planner ──> assets ──> render
```

1. **`core/director.py`** — LLM-driven storyboard generation (Anthropic/OpenAI/Claude Code print mode). Prompts live in `prompts/`; promoted examples in `prompts/director_examples/`.
2. **`core/treatment_planner.py`** — optional second LLM pass that refines native Remotion scene treatments within the fixed composition registry.
3. **`core/composition_planner.py`** — deterministic normalization: assigns composition families, enriches structured template props from `on_screen_text`/`data_points` (`_enrich_template_props`), reroutes families when the data shape mismatches (`_reroute_family_by_data_shape`).
4. **Asset generation** — `image_gen.py` (GPT Image / Replicate Qwen / local HF / DashScope), `voice_gen.py` (Kokoro local, OpenAI TTS, ElevenLabs), `video_gen.py` (Replicate or local command/endpoint).
5. **Render** — `video_assembly.py` (ffmpeg orchestration, default backend) or `remotion_render.py` (manifest build + Node subprocess via `scripts/render-remotion.mjs`) when the optional Remotion toolchain is installed.

Supporting modules: `project_schema.py` (plan.json schema, brief normalization, render-backend resolution), `project_store.py` (plan CRUD), `pipeline_service.py` (high-level job orchestration), `job_runner.py` (persisted background jobs + per-job logs), `runtime.py` (provider discovery and leak-safe credential routing), `costs.py` (estimates from public pricing — not real spend).

## Composition families

Scenes carry `composition.family`. Media families: `static_media`, `media_pan`, `software_demo_focus`. Native motion families: `kinetic_statements`, `bullet_stack`, `quote_focus`, `three_data_stage`, `surreal_tableau_3d`. Template deck families (deterministic Remotion overlays with `template_deck/backgrounds/` art): `cover_hook`, `orientation`, `metric_improvement`, `metric_comparison`, `timeline_progression`, `analogy_metaphor`, `synthesis_summary`, `closing_cta`.

### Legacy family fallback

Earlier versions shipped two domain-specific families (`clinical_explanation`, `brain_region_focus`) that have been removed. `_LEGACY_FAMILY_FALLBACKS` in `core/project_schema.py` maps them to `bullet_stack` / `three_data_stage` at load time so pre-removal `plan.json` files still open and render. Once no such plans remain in your `projects/`, that mapping (and its tests) can be deleted.

## plan.json

`core/project_schema.py:backfill_plan()` is the single entry point that normalizes any (possibly legacy) plan into the current schema: `meta` (brief, render/image/video/tts profiles, pipeline mode) and `scenes` (narration, visual_prompt, scene_type, composition, asset paths, timing). Background jobs persist under `projects/<name>/.bettube-studio/jobs/`.

## Remotion is optional and hidden by default

"Motion" in the GUI means Remotion. The entire motion surface (motion scene type, native motion + template deck families, motion preview, Remotion render backend) keys off one signal: `core/runtime.py:remotion_available()`, exposed to the frontend via `/api/bootstrap`. That signal requires BOTH the `BETTUBE_STUDIO_ENABLE_REMOTION=1` master switch and an installed Remotion toolchain in `frontend/node_modules`; by default it is false and the product is image/video + `ffmpeg` only.

The repo never depends on Remotion packages directly. `frontend/vite.config.ts` aliases the player surface to a stub when `@remotion/player` is absent, `tsconfig.app.json` excludes the Remotion sources from the no-Remotion build, and the backend resolves the render backend to `ffmpeg` when `remotion_available()` is false.
