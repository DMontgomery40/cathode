# Scene Family Contracts

## Canonical Scene Contract

The canonical contract is `scene.composition` in `plan.json`:

- `family`
- `mode`
- `props`
- `transition_after`
- `data`
- `rationale`

`scene.motion` mirrors the same scene for compatibility. Do not treat it as the source of truth.

## Current Families

- `static_media`
  - plain still/video beat
- `media_pan`
  - still image with camera motion
- `software_demo_focus`
  - deterministic UI/demo callout beat
- `kinetic_statements`
  - animated text-led statement
- `bullet_stack`
  - stacked sequence/roadmap/list
- `quote_focus`
  - centered attribution/quote-style text beat
- `three_data_stage`
  - structured ranking/comparison/data staging
- `surreal_tableau_3d`
  - deterministic symbolic 3D tableau

## `surreal_tableau_3d`

This family exists for imaginative hero-object and symbolic 3D scenes. It is not a generic title card.

Expected props:

- `layoutVariant`
  - `orbit_tableau`
  - `symbolic_duet`
- `heroObject`
- `secondaryObject`
- `orbitingObject`
- `orbitCount`
- `environmentBackdrop`
- `ambientDetails`
- `paletteWords`
- `cameraMove`
- `copyTreatment`
- optional `motionNotes`

Defaults:

- `copyTreatment` should default to `none`.
- `orbit_tableau` is for scenes with explicit orbit/tableau/camera-circle language.
- `symbolic_duet` is for bounded two-object metaphor scenes.

## How To Debug A Misclassified 3D Scene

1. Open the saved scene in `projects/<project>/plan.json`.
2. Check whether the scene already has the wrong `composition.family`.
3. If yes, trace:
   - `core/director.py`
   - `core/composition_planner.py`
   - `core/treatment_planner.py`
4. If the family is correct in the plan but wrong on screen, trace:
   - `core/remotion_render.py`
   - `frontend/src/remotion/index.tsx`
   - `frontend/src/features/scenes/SceneInspector.tsx`

## Red Flags

- a 3D hero scene classified as `quote_focus`
- `surreal_tableau_3d` props flattened back into `headline/body` text-card props
- motion scenes edited only through a legacy template dropdown
- a Remotion backend reason that is technically true but visually meaningless
