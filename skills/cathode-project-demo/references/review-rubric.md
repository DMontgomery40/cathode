# Review Rubric

The reviewer is a spawned Codex/Claude sub-agent and is mandatory. Do not skip the review loop just because the capture technically succeeded.

Keep the reviewer prompt short. The whole point is to get a less-biased visual gut check, not another long planning document.
Do not hand the reviewer clip metadata, plan context, or a JSON schema. Give it frames and one blunt question.
Save the reviewer reply as raw text first. The parent agent can map that gut-check back into clip ids and Cathode's structured report afterward.

## Required Judgments

For each candidate clip, judge:

- framing
- legibility
- theme correctness
- whether the primary artifact dominates the frame
- whether the chosen state is actually a good demo state
- whether the crop helped or made things worse

## Decision Meanings

- `accept`: the clip is strong enough to use without caveat
- `warn`: the clip is usable, but needs a heads-up or should not be the hero moment
- `retry`: capture again before handing off to Cathode

## When To Warn

Warn when:

- the state is real but not the strongest proof available
- the clip is readable, but the main evidence is still weaker than it should be
- the run or panel shown is technically valid but visually underwhelming
- the only stronger state has a tradeoff that must be named explicitly

## When To Retry

Retry when:

- the theme is wrong or mixed
- framing or legibility is weak
- the app chrome dominates the result
- the chosen state is poor enough that narration would have to rescue it
- the crop made the UI harder to understand

## Training And Metrics Surfaces

When a product has training or benchmarking views:

- prefer completed runs over failed runs
- prefer non-zero, non-embarrassing metrics over zero-metric runs
- if the only stronger-looking metrics come from failed runs, do not hero them silently

The acceptable output in that case is usually `warn`, not `accept`.
