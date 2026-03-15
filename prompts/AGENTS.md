# Prompt Agent Rules

- Do not hand-author storyboard examples for Cathode prompts.
- Promoted prompt examples must come from the Anthropic-harvested director-golden workflow.
- Raw Anthropic corpus artifacts stay in ignored `experiments/director_golden/`; only curated winners belong in `prompts/director_examples/`.
- Prompt work must preserve both halves of Cathode:
  - the raw-brief creative drafting path
  - the deterministic Remotion/planner realization path
- The default director prompt should stay art-direction-first for pure creative briefs. Remotion mechanics belong in a downstream treatment planner prompt, not in the main creative director voice.
- Use intent-specific promoted example shelves. Do not let an abstract AI or product-demo example become the default anchor for unrelated whimsical/storybook prompts.
- Prompt variants should be evaluated through the existing director prompt-versioning hook instead of editing one live prompt in place without comparison.
- Judge prompt changes by the outputs Cathode can actually normalize and preview, not by prose quality alone.
- Brief-selected capability blocks and promoted examples may change what the director sees, but they must not replace the full normalized brief or the raw user input.
