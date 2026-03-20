# Official Remotion Docs

Verified official links used during the 2026-03-14 motion-first 3D overhaul:

- Docs hub / main site: <https://www.remotion.dev/>
- Player: <https://www.remotion.dev/docs/player>
- Sequence: <https://www.remotion.dev/docs/sequence>
- TransitionSeries: <https://www.remotion.dev/docs/transitions/transitionseries>
- Three / `@remotion/three`: <https://www.remotion.dev/docs/three>
- AI system prompt: <https://www.remotion.dev/docs/ai/system-prompt>
- Prompt gallery: <https://www.remotion.dev/prompts>

## When To Use Which Doc

- Player
  - Use when debugging the Render workspace preview surface or any embedded Remotion player behavior.
- Sequence
  - Use when debugging scene timing, freeze/hold behavior, narration extension, or per-scene composition timing.
- TransitionSeries
  - Use when debugging scene-to-scene transitions and how Cathode chains scenes in the final composition.
- Three / `@remotion/three`
  - Use when building or debugging 3D scenes. Cathode's `surreal_tableau_3d` should use this integration, not an arbitrary standalone fiber canvas path.
- AI system prompt
  - Use when comparing Cathode's treatment-planner constraints against Remotion's own AI-oriented composition guidance.
- Prompt gallery
  - Use when you need examples of meaningful composition ideas or prompt framing, not just syntax reminders.

## Cathode-Specific Reading Order

1. Player
2. Sequence
3. TransitionSeries
4. Three / `@remotion/three`
5. AI system prompt
6. Prompt gallery

If a future session does not expose Context7, browse these official links directly.
