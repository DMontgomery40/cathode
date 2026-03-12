# Live Demo Capture

Use this reference when the product story depends on a running app, local URL, or live browser workflow.

## Capture Defaults

- Use a real browser in headed mode.
- Set viewport explicitly for every attempt.
- Set theme explicitly for every attempt.
- Record raw browser video, screenshots, and trace.
- Keep a structured step manifest with timestamps, action notes, and focus selectors.
- Keep the raw artifacts even when the processed clip looks good.

## Recommended Attempt Order

1. Dark theme, standard landscape viewport, default sidebar state.
2. If readability is weak, retry with a larger viewport before changing the flow.
3. If the product surface is visually dominated by sidebars or controls, retry with a cleaner panel state.
4. If the chosen app state is weak, retry with a better state before spending more time on crop polish.

## Focus Cropping

Use FFmpeg crop/scale after capture, not browser zoom during capture.

Record a focus box when:

- the most important evidence is only one panel
- the whole page is readable but not persuasive
- a smaller area proves the product better than the full frame

Do not crop when:

- the overall layout is the product value
- the crop would hide the state transition
- the crop makes the user lose context

## What To Capture

Prefer clips that prove:

- the app is real
- the main workflow is understandable
- the key result is visible without narration rescuing it
- the UI state is not embarrassing or misleading

Avoid clips where:

- the state is technically valid but visually weak
- the primary evidence is tiny or off to the side
- the metrics or outputs look obviously bad for a hero shot
- the theme is mixed, washed out, or incorrectly applied

After extraction, hand only frames to the reviewer sub-agent. Keep its raw reply in the bundle before you translate it into the structured Cathode review report.

## Capture Plan Shape

The packaged capture driver expects a plan JSON with:

- `theme`
- optional `viewport`
- `steps`

Each step can include:

- `id`
- `label`
- `actions`
- `checkpoint_selector`
- `focus_selector`
- `text_selector`
- `hold_ms`
- `clip`

Use actions like:

- `click`
- `select_option`
- `fill`
- `press`
- `wait_for_selector`
- `wait_for_timeout`
- `evaluate`
- `scroll_into_view`

When review says `retry`, mutate the plan with `scripts/apply_retry_actions.py` instead of hand-editing random new attempts.
