# Why It Works

An exceptionally well-crafted pitch storyboard that functions simultaneously as a persuasive spouse pitch and a demonstration of Cathode's own capabilities. The multi-voice structure (Bella/Marcus/Jenna/Coop) is a clever meta-layer that proves the product while selling the idea. Scene architecture is tight, emotional pacing is deliberate, and deterministic anchors are consistently present across all 18 scenes. Minor weaknesses: a few scenes use 'motion' type without precise enough animation choreography for the planner, and pricing figures are vague in the narration vs. the on-screen text. Overall this is one of the strongest multi-speaker, hybrid-mode storyboards reviewed.

## Strengths
- Multi-speaker casting (Bella + Marcus + Jenna + Coop) is a meta-demonstration of the product concept — the storyboard proves its own thesis
- Every scene has populated on_screen_text and a speaker_name, giving the planner unambiguous deterministic inputs
- data_points fields are used correctly on scenes that need quantitative content (scenes 6, 14, 16) and intentionally left empty elsewhere
- Emotional arc is masterfully structured: hook → problem → solution → demos → math → objection-handling → close — mirrors a professional pitch deck
- Visual prompts are detailed and cinematically specific (lighting direction, color palette, mood) without being brittle renderer instructions
- Scene-type assignments (image vs. motion) are well-reasoned — motion scenes carry data reveals, image scenes carry atmosphere
- Transition hints (fade/wipe/null) are consistently assigned and contextually appropriate
- Objection-handling scene (13) with the comedic split layout is a rare and excellent beat that addresses audience psychology directly
- 30-day plan scene (16) provides a concrete timeline that converts emotional buy-in to actionable belief
- Staging notes are directing-quality — they specify animation order, hold timing, and emotional tone without micromanaging renderer specifics

## Prompting Notes
- TEACH: Multi-speaker storyboards should assign speaker_name per scene explicitly — this example does it correctly and consistently for a 4-voice cast
- TEACH: Using demo-ad scenes mid-storyboard (scenes 5, 7, 8) is a powerful technique for 'show don't tell' pitches — planner should recognize speaker switches as tonal/mode shifts
- TEACH: data_points should contain the actual quantitative strings that appear on screen — this example correctly mirrors data_points and on_screen_text on financial scenes
- TEACH: Staging notes should describe animation sequence order (first, then, last) as this example does — this is the closest proxy to a deterministic animation spec without a dedicated field
- TEACH: Transition hints should vary contextually — fade for emotional transitions, wipe for structural pivots — this example demonstrates the convention correctly
- IMPROVE: For grid/tile reveal scenes, on_screen_text items should be wrapped in a structured hint (e.g., a 'layout': 'grid' field) so the planner doesn't default to sequential text overlays
- IMPROVE: Motion scenes with multi-step reveals benefit from explicit step count in a dedicated field rather than prose staging_notes — consider a 'reveal_steps' array
- TEACH: Emotional arc labeling in scene titles (Hook, Problem, Solution, Demo, Math, Objection, Close) is a best practice that helps the planner understand scene function beyond visual content
- TEACH: The 'demo is the pitch' sales motion described in scene 12 is itself a model for how Cathode pitches should work — the storyboard embodies its own argument
- IMPROVE: Target duration per scene should be calculable from narration word count — future storyboards should include estimated_duration_seconds per scene for tighter pacing validation
