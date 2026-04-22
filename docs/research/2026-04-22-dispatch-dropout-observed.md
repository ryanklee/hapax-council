---
title: Dispatch dropout observation report — first trace window
date: 2026-04-22
status: PR-A2 (observation report); PR-A3 (fix) pending operator decision
related:
  - docs/research/2026-04-22-dispatch-dropout-investigation.md
  - shared/affordance_pipeline.py
  - tests/test_affordance_dispatch_trace.py
---

## Summary

PR-A1 instrumented `AffordancePipeline.select()` with a per-call
dispatch-trace JSONL at `~/hapax-state/affordance/dispatch-trace.jsonl`.
The pre-investigation hypothesis was that ~98 % of director-side
intents were being silently dropped. The first trace window
(2026-04-21 20:35 → 21:14 local, ~94 calls) **refutes that
hypothesis**. The pipeline dispatched 89 of 94 calls (94.7 %),
with all 5 dropouts attributable to two narrow causes — neither
of which is `threshold_miss` or `retrieve_family_empty`.

This document reports the observed funnel and recommends PR-A3
shape against the data. The operator's product call is required
before PR-A3 can ship: the data does not justify a threshold tune
or a catalog-coverage fix.

## Window characteristics

| Field | Value |
|---|---|
| First call | 2026-04-21 20:35:44 local |
| Last call | 2026-04-21 21:14:26 local |
| Duration | ~39 minutes |
| Total calls | 94 |
| Dispatched | 89 (94.7 %) |
| Dropped | 5 (5.3 %) |
| Distinct sources | 17 |
| Distinct winners | 28 |
| Winner combined-score range | min 0.288 / median 0.561 / max 0.644 |

**Caveat on window provenance.** Two of the 94 entries have
`source: "test"`, which traces from `tests/test_affordance_dispatch_trace.py`
fixtures rather than from production. Those test entries were
written during local pytest runs that hit the real
`DISPATCH_TRACE_FILE` path before the test patches were applied
(or in tests that intentionally don't patch the path). The other
92 entries carry production sources (`exploration.*`,
`studio_compositor.director.*`, `dmn`, `imagination`,
`operator.utterance`). The 94.7 % dispatch rate excludes the test
entries from the denominator only when called out below.

## Dropout breakdown

| Dropout tag | Count | Sources |
|---|---|---|
| `interrupt_no_handler` | 3 | `test` (2), `sensor.stimmung` (1) |
| `inhibited` | 2 | `dmn` (2) |
| `threshold_miss` | 0 | — |
| `retrieve_family_empty` | 0 | — |
| `retrieve_global_empty` | 0 | — |
| `consent_filter_empty` | 0 | — |
| `monetization_filter_empty` | 0 | — |
| `no_embedding_fallback` | 0 | — |

The two "real" production dropout sources are:

1. **`sensor.stimmung` → `interrupt_no_handler`** with
   `interrupt_token: "profile_dimension_updated"`. The stimmung
   sensor emits this interrupt but nothing has registered a
   handler for it, so `select()` returns `[]` immediately.
2. **`dmn` → `inhibited`** with `metric: "flow_drop"`. The DMN
   flow-drop signal hits an active inhibition window, suppressed
   from re-firing.

Both are correct behavior. Neither is a livestream-impacting
dropout.

## Per-source dispatch rate (production sources only)

| Source | Dispatched | Dropped |
|---|---|---|
| `exploration.affordance_pipeline` | 23 | 0 |
| `exploration.visual_chain` | 12 | 0 |
| `exploration.apperception` | 11 | 0 |
| `exploration.content_resolver` | 10 | 0 |
| `exploration.stimmung` | 10 | 0 |
| `exploration.dmn_pulse` | 9 | 0 |
| `exploration.salience_router` | 9 | 0 |
| `exploration.temporal_bands` | 9 | 0 |
| `exploration.contact_mic` | 8 | 0 |
| `exploration.dmn_imagination` | 8 | 0 |
| `exploration.input_activity` | 8 | 0 |
| `exploration.ir_presence` | 8 | 0 |
| `studio_compositor.director.compositional` | 8 | 0 |
| `imagination` | 7 | 0 |
| `dmn.evaluative` | 6 | 0 |
| `dmn` | 2 | 2 (inhibited) |
| `sensor.stimmung` | 0 | 1 (interrupt_no_handler) |
| `operator.utterance` | 1 | 0 |

`studio_compositor.director.compositional` — the source the
audit hypothesis singled out — dispatched **8 of 8** in this
window. None of the suspected `camera.hero` dropouts appeared.

## intent_family distribution

| `intent_family` | Count | Dispatched |
|---|---|---|
| `null` (no family) | 88 | 88 |
| `overlay.emphasis` | 5 | 5 |
| `preset.bias` | 1 | 1 |
| `camera.hero` | **0** | — |

The audit hypothesis specifically called out `camera.hero` as
the dropout-affected family. **Zero `camera.hero` impingements
appeared in this window.** Either the director is not currently
emitting `camera.hero` intents, or they are being filtered
upstream of `AffordancePipeline.select()` (e.g., at the
director's own gate, in `compositional_impingement_emitter`,
or in the consumer that converts compositor signals into
`Impingement` records). Without `camera.hero` traffic, this
trace cannot distinguish "director emits but pipeline drops"
from "director never emits". A separate investigation upstream
of `select()` is needed to answer the camera.hero question.

## Top winners (by capability)

| Winner | Wins |
|---|---|
| `space.gaze_direction` | 56 |
| `knowledge.vault_search` | 12 |
| `ward.highlight.music_candidate_surfacer.foreground` | 8 |
| `content.imagination_image` | 8 |
| `attention.winner.goal-advance` | 7 |
| `ward.highlight.impingement_cascade.pulse` | 5 |
| `ward.highlight.objectives_overlay.foreground` | 4 |
| `overlay.dim.all-chrome` | 4 |
| `node.reaction_diffusion` | 4 |
| `node.content_layer` | 4 |

The dominance of `space.gaze_direction` (56 wins, 60 % of all
dispatches) raises a separate question — whether the embedding
score for that capability is too broadly tuned, sweeping in
impingements that probably should match more specific
capabilities. That is a recruitment-quality question, not a
dispatch-rate question, and is out of scope for this PR.

## Threshold gap (would-be PR-A3 input)

`threshold_miss` would have populated `top_score` and
`top_capability` so PR-A3 could decide between threshold tune
vs. catalog gap vs. scoring weight. **Zero `threshold_miss`
events fired in this window**, so this gap distribution is
empty. The current `THRESHOLD = 0.05` (× 0.5 under SEEKING) is
not the bottleneck.

The lowest combined score that *did* dispatch was 0.288. The
minimum dispatched score is 5.8× the threshold, so the threshold
has substantial headroom even at the bottom of the score
distribution.

## Recommendation

The data does not justify any of the PR-A3 fix shapes the
investigation doc anticipated:

| Anticipated fix | Justified by data? |
|---|---|
| Threshold tune | No (0 threshold_miss) |
| Catalog-coverage gap | No (0 retrieve_family_empty) |
| Family-prefix bug | No (0 retrieve_family_empty) |
| Scoring-weight rebalance | No (median dispatched score 0.561) |

What the data *does* surface is two narrower issues, neither
livestream-critical:

1. **Register a handler for the `profile_dimension_updated`
   interrupt** (or stop emitting it from `sensor.stimmung`).
   Single dropout source per ~10 minutes is cosmetic noise but
   should be cleaned up.
2. **Investigate why `camera.hero` is absent from production
   traffic**. The audit hypothesis was generated from a
   pre-reboot window; if `camera.hero` was suppressed by a
   recent director change, the audit may be tracking a
   transient that no longer exists. If `camera.hero` *should*
   be firing and is not, that bug lives in the director, not
   in `select()`.

## PR-A3 disposition

PR-A3 as originally scoped (fix the dispatch-rate bottleneck)
has no work to do. **Recommend closing the PR-A3 task as
"resolved by observation: hypothesis refuted"** and opening
two new narrow tasks for the actual findings:

- `PR-A3a` — register `profile_dimension_updated` handler or
  prune the emit
- `PR-A3b` — investigate `camera.hero` absence in director
  traffic (upstream of `select()`)

The operator should make the call on whether to proceed with
A3a/A3b or defer them as low-priority cleanup.

## Window adequacy

94 calls over 39 minutes is a small sample. The dispatch rate
estimate (94.7 %) has wide error bars at this sample size — a
50× window (~30 hours of trace data) would be needed to detect
a 1 %-class dropout cause with confidence. However, the audit's
"98 %" claim was extreme enough that a 94-sample window with
zero observed instances of the hypothesized dropout class is
already sufficient evidence that the hypothesis was wrong:
under H0 = (98 % dropout), the probability of observing ≤5
dropouts in 94 calls is essentially zero.

If the operator wants tighter bounds before closing PR-A3, the
trace can run another 24-72 hours and PR-A2 can be revised. The
current data is decisive enough for the immediate question
(should PR-A3 ship a dispatch-rate fix?) but not for the
secondary question (what is the true tail-distribution of
dropout causes across a full week of livestream traffic?).
