---
title: Dispatch dropout investigation — instrumentation phase
date: 2026-04-22
status: PR-A1 (instrumentation); PR-A2 (observation report) and PR-A3 (fix) follow
related:
  - docs/superpowers/specs/2026-04-02-unified-semantic-recruitment-design.md
  - docs/research/2026-04-19-camera-hero-dispatch-audit.md
  - shared/affordance_pipeline.py
  - tests/test_affordance_dispatch_trace.py
---

## Question

`StudioCompositor.director_loop.py` emits `CompositionalImpingement` records
into the impingement bus, each carrying an `intent_family` (`camera.hero`,
`preset.bias`, `ward.highlight.*`, `gem.emphasis`, `overlay.dim.*`, etc.).
The `AffordancePipeline` consumes these and returns a winner capability set
that the runtime then dispatches.

In a 60-minute pre-reboot window on 2026-04-21 the operator-side audit on
`camera.hero`-tagged impingements showed an apparent dispatch rate around
2 % — most director intents emitted no observable winner. The cause is
not visible from the existing logs because every gate in `select()` that
yields zero candidates short-circuits with `return []`, leaving no record
of *which* gate killed the call. Both the per-frame `_log_cascade` writer
and the persistent `recruitment-log.jsonl` only fire when at least one
winner survives, so non-dispatched calls are invisible.

This document describes the instrumentation that closes that visibility
gap (PR-A1). Once the trace has accumulated ~30 minutes of production
data, PR-A2 will publish a per-gate dropout breakdown and PR-A3 will
implement a targeted fix.

## Context — what the recruitment log already shows

`~/hapax-state/affordance/recruitment-log.jsonl` (winner-only) over a
~4-hour window pre-reboot held 838 records sourced from
`studio_compositor.director.compositional`. The top winners by family:

| Capability | Wins |
|---|---|
| `fx.family.audio-reactive` | 188 |
| `ward.highlight.album.foreground` | 104 |
| `overlay.foreground.activity-header` | 94 |
| `ward.highlight.album.dim` | 64 |
| `overlay.dim.all-chrome` | 54 |
| `cam.hero.desk-c920.writing-reading` | 54 |
| `ward.highlight.music_candidate_surfacer.foreground` | 46 |

The asymmetry is what raises the question. `cam.hero.*` instances exist
in the catalog and are recruitable (54 wins on the desk-C920 instance
alone), so the issue is not "no catalog coverage" — it is something more
intermittent. Without a per-call dropout trace we cannot tell whether the
director is emitting too many `camera.hero` intents that the
`_retrieve_family` filter then sieves down to zero, or whether candidates
*are* surfacing but failing the `THRESHOLD = 0.05` cutoff after the
similarity / Thompson / recency / cost score composition.

## Gates that can silently drop a `select()` call

Reading `AffordancePipeline.select()` top-to-bottom, every early-return
of `[]` happens at one of these gates:

| Stage tag | Source line | Returns `[]` when |
|---|---|---|
| `interrupt_no_handler` | interrupt-token branch with no registered handler | `interrupt_token` set but `_interrupt_handlers` lookup empty |
| `inhibited` | `_is_inhibited()` | inhibition window active for this impingement signature |
| `no_embedding_fallback` | `_get_embedding()` returns None and `_fallback_keyword_match()` is empty | embedding service unavailable AND no keyword hit |
| `retrieve_family_empty` | `_retrieve_family(intent_family)` returns 0 candidates | family-restricted Qdrant search yields nothing |
| `retrieve_global_empty` | `_retrieve()` returns 0 candidates | global Qdrant search yields nothing (no `intent_family`) |
| `consent_filter_empty` | `_consent_allows` strips every candidate | every retrieved capability requires consent that no contract grants |
| `monetization_filter_empty` | `_MONET_GATE.candidate_filter` strips every candidate | every retrieved capability is high-risk or medium-risk-without-opt-in |
| `threshold_miss` | post-scoring `combined > effective_threshold` filter empties `survivors` | candidates survived but none scored above `THRESHOLD = 0.05` (`× 0.5` under SEEKING) |

The two stages most plausibly responsible for the director dropout are
`retrieve_family_empty` (intent-family routing was added 2026-04-18 to
prevent cross-family hijacking) and `threshold_miss` (the absolute
cutoff is independent of the intent's source).

## What the instrumentation captures

`AffordancePipeline.select()` now builds a single `trace` dict at entry
and writes one JSONL line per call to
`~/hapax-state/affordance/dispatch-trace.jsonl`. The schema:

```json
{
  "timestamp": 1776821753.917572,
  "impingement_id": "<uuid>",
  "source": "studio_compositor.director.compositional",
  "metric": "",
  "intent_family": "camera.hero",
  "dropout_at": "retrieve_family_empty",
  "stages": {
    "retrieve_family": 0
  }
}
```

When a winner emerges:

```json
{
  "timestamp": 1776821753.917572,
  "impingement_id": "<uuid>",
  "source": "studio_compositor.director.compositional",
  "metric": "",
  "intent_family": "camera.hero",
  "dropout_at": null,
  "stages": {
    "retrieve_family": 5,
    "after_consent": 5,
    "after_monetization": 5,
    "normal_candidates": 5,
    "effective_threshold": 0.05
  },
  "winner": "cam.hero.desk-c920.writing-reading",
  "winner_combined": 0.342,
  "winner_similarity": 0.461,
  "survivors": 1
}
```

`dropout_at == null` is the dispatched-successfully marker. Every other
value names the stage that returned `[]`. The `stages` dict carries the
candidate count after each filter so PR-A2 can plot the funnel.

`threshold_miss` records the `top_capability` and `top_score` so PR-A2
can answer: "when the threshold killed the call, by how much did the
top score fall short, and which capability would have won at a lower
threshold?" That distinguishes "catalog coverage problem" from
"composed-score weighting problem" without further code changes.

## Operational characteristics

- **Default-on.** `HAPAX_DISPATCH_TRACE=0` disables. The recruitment
  hot path is sacred — write failures are caught and dropped silently
  (same fail-open contract as `_persist_recruitment_winner`).
- **Volume.** Each line is ~250 bytes. At ~5 select() calls/sec
  (the same order as the recruitment-log) the trace grows ~100 MB/day.
  Operator rotates manually; the doc trail for that lives next to the
  recruitment-log convention.
- **Disk path.** `~/hapax-state/affordance/dispatch-trace.jsonl`
  alongside the existing `recruitment-log.jsonl`.
- **Test coverage.** `tests/test_affordance_dispatch_trace.py` pins all
  eight dropout tags, the `null`-on-success marker, the
  `threshold_miss` top-score capture, and the fail-open writer
  contract.

## What PR-A2 will produce

After the trace has run for ~30 minutes against live director traffic,
PR-A2 publishes `docs/research/2026-04-22-dispatch-dropout-observed.md`
with:

1. Per-gate dropout counts overall and broken down by `source` and
   `intent_family`. Direct answer to "where does the 98 % go?".
2. For `threshold_miss` events: the distribution of (top score –
   threshold) gaps. If most misses are within ε of the bar, PR-A3 is a
   threshold tune. If they cluster far below, PR-A3 is a catalog-
   coverage or scoring-weight problem.
3. For `retrieve_family_empty` events: the set of `intent_family` values
   that retrieve zero candidates. If `camera.hero` shows up here and
   the catalog *does* register `cam.hero.*` capabilities, the bug is
   in `_canonical_family_prefix` or the family-prefix mapping.
4. A recommendation for the PR-A3 fix shape (threshold tune /
   catalog-coverage gap / scoring-weight rebalance / family-prefix
   correction). One PR per recommendation; multiple if PR-A2 reveals
   independent failure modes.

## Non-goals for PR-A1

- No fix. The instrumentation is evidence-gathering only. Shipping a
  fix before the trace runs would be cherry-picking — see the
  `feedback_systematic_plans` operator memory.
- No alerting. PR-A2 may add Prometheus counters once the dropout
  taxonomy is stable; PR-A1 deliberately stays at JSONL append.
- No retroactive analysis. The pre-reboot 98 % figure is a hypothesis
  that PR-A2's data either confirms or refutes; it is not a baseline
  to reproduce.
