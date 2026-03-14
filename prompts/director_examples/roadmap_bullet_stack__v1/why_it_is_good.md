# Why It Works

A well-crafted, tonally consistent storyboard for a 3-step workflow explainer. The directing voice is confident and premium, scene pacing is deliberate and logical, and the motion language is coherent across the arc. Every scene carries clean on_screen_text arrays, clear staging_notes, and consistent transition_hint values. The reprise scene (id:8) uses data_points meaningfully. Minor weaknesses: no speaker_name or audio hints, color-shift cues (indigo→gold) are evocative but require renderer interpretation, and a couple of scenes are overly descriptive in visual_prompt without adding deterministic signal.

## Strengths
- Consistent motion language across all three step-reveal scenes (ids 2, 4, 6) — same rhythm described explicitly, enabling a reusable component pattern
- on_screen_text arrays are tightly scoped per scene and map cleanly to label/value pairs or headline/subline slots
- Transition hints alternate wipe/fade purposefully, signaling structural boundaries vs. content continuation
- Reprise scene (id:8) intelligently changes behavior (simultaneous vs. staggered reveal) and uses data_points to reinforce overlay text — good anchor duplication pattern
- Closing scene staging_notes distinguish this beat from prior scenes ('no punch, no type-on') — useful negative instruction for the renderer
- Scene count (10) maps well to a 60-second runtime with varied beat lengths
- Accent color shift to warm gold on Step 3 is a light, planner-legible signal for a themed variant without requiring complex branching

## Prompting Notes
- Teach: reusable motion component pattern — when multiple scenes share identical animation rhythm, staging_notes should call out the shared pattern by name so the planner can register a single component
- Teach: on_screen_text as label/value interleaved pairs (scenes 3 and 5) is a strong pattern for data cards — worth documenting as a 'definition list' surface type
- Teach: data_points field used in reprise scene to mirror on_screen_text — shows intentional duplication for planner indexing vs. renderer display
- Teach: closing-scene negative staging instruction ('no punch, no type-on — just a graceful arrival') as a valid directing verb that constrains rather than adds animation
- Warn: color accent changes should be expressed in a structured field (e.g., a scene-level theme_accent key) rather than only in prose, to be reliably deterministic
- Warn: 'beats' as a timing unit is underspecified — future storyboards should anchor at least one scene to a concrete duration (e.g., '2 seconds') so the planner can calibrate the beat unit
- Teach: the cover + overview + 3×(step+detail) + reprise + close structure is a reusable 10-scene template for any N-step process explainer
