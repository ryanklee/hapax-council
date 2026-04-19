# Dynamic Livestream Audit — Final Holistic Synthesis

**Date**: 2026-04-20
**Inputs**:
- Catalog: `docs/research/2026-04-20-dynamic-livestream-audit-catalog.md` (10,839 words, ~104 audits, 20 sections)
- Cascade 52-audit slice: `docs/research/2026-04-20-cascade-dynamic-audit-results.yaml`
  (20 pass / 25 warn / 1 fail / 7 indet)
- Alpha 52-audit slice: relay YAML `alpha-dynamic-audit-results-20260420.yaml`
  (per §3 rollups — mixed spec-pin + behavioral-pending)

Two catalog runs now complete:
- Catalog-1 (static, 104 audits) → `audit-synthesis-final.md` — 75 pass / 19 warn / 2 fail / 14 indet
- Catalog-2 (dynamic, ~104 audits) → this doc

---

## §0. Combined catalog-2 totals

| Outcome | Cascade (52) | Alpha (~52) | Total |
|---|---|---|---|
| pass / pass_spec | 20 | ~22 | ~42 |
| warn | 25 | 0 (alpha uses fail_spec) | 25 |
| fail / fail_spec | 1 | ~17 | ~18 |
| indeterminate | 7 | ~13 | ~20 |

**~42 of 104 dynamic audits have a detector / gauge / test surface
that actually exists.** The remaining ~62 are the Pattern-1 meta-fix
work — detectors that the catalog calls for but the system hasn't
built yet. This is not a regression on today's system; it's a map
of what must be built before the system is *audit-ready* for live
operation per operator's quality bar.

Alpha put it succinctly: **"Pattern 1 shows up MASSIVELY in this
dynamic catalog — most audits have 0 detector. The catalog is more
wishlist than current-state snapshot."**

This is the right way to read catalog-2: the authoritative
specification of what observability the livestream needs, not a
scorecard of what's in place.

---

## §1. Alpha's four incident flags

1. **10.8 MixQuality NOT IMPLEMENTED** — the operator's "mix ALWAYS
   good" invariant has no aggregate enforceable metric. Alpha
   shipping a skeleton design this pass.
2. **11.6 voice-over-ytube-duck.conf missing** — overlaps with
   catalog-1 alpha 4.4 incident flag. Known, operator-facing install
   step documented in `audit-synthesis-final.md §5`.
3. **1.3 / 3.7 layout invariants have no test** — overlaps with
   catalog-1 audit-closeout 3.2 (alpha bundle queued).
4. **§17 testing infrastructure absent** — no replay harness, no
   audio-spectral compare, no chaos test. Biggest meta-gap.

---

## §2. Cross-cutting patterns — catalog-2 + catalog-1 integration

### 2.1 Catalog-2 is catalog-1's Pattern 1 writ large

Catalog-1 identified the archetype: silent invariant break +
dormant observability. Catalog-2's 60%+ fail-spec rate IS the
realisation. The 14:08 TTS leak, the grounding_provenance
constitutional break, the reverie pool_reuse_ratio = 0 — these are
three instances of the same disease: the invariant exists on
paper, the system emits the violation every tick, and the
detector that should scream is missing.

**The work going forward is Pattern-1-codification as an engineering
convention**: every new invariant lands with its paired counter +
violation-log + regression test + dashboard row. Catalog-2 is the
acceptance criteria for that convention — it's done when all 104
audit rows have at least the detector built.

Cascade began this today:
- `hapax_compositional_consumer_dispatch_total{family,outcome}` — 7
  sites wired via `@observe_dispatch` decorator (`54a020ea5`)
- Prompt-level slur prohibition sentinel (`7c9df3848`) — fail-closed
  startup if clause missing
- Vinyl-playing hand-activity gate (`a0eeb4323`) — invariant:
  cover-only is insufficient for a playing claim

These three are **template commits** for the pattern. The remaining
~60 audit detectors should ship the same way: a counter + a guard
+ a test + a one-line startup log.

### 2.2 MixQuality is the cross-surface integrator

Catalog-2 §10.8 (MixQuality aggregate) ties to catalog-2 §13
(cross-surface coherence). When MixQuality ships, §13's AV-coherence
audits can consume it. Alpha is shipping the skeleton today; impl
is multi-PR.

**Operator-facing single answer** for "is the mix always good?"
requires:
1. LUFS loudness compliance (EBU R128)
2. Balance (operator-mic vs TTS vs music vs chat)
3. Clarity (no overlapping speech layers unless intentional)
4. Intentionality (director-dispatched, not accidental)
5. Dynamics (not-always-loud, not-always-quiet)
6. AV coherence (visual emphasis matches audio emphasis)

Each sub-score is a gauge. MixQuality = weighted composite. Target
(per alpha's skeleton): mean > 0.7 for 95% of seconds, > 0.85 for
90% of 5-min windows. Operator re-calibrates the weights quarterly.

### 2.3 §17 testing infrastructure gap blocks behavioural audits

Most "behavioral" audits (long-term rotation fairness, programme
exhaustion, director drift) can only be evaluated against a recorded
session. §17.1 replay harness doesn't exist. Without it, these
audits are stuck at "infrastructure pending" forever.

**Cheapest path to replay harness**: HLS fragments already land at
`/tmp/hls/` during livestream. Add a capture-into-cold-storage
script (7-day rotation). Build a playback tool that re-runs catalog
audits against each 5-min HLS fragment. Weekly retro uses it.

### 2.4 Operator action-items (§19) are the governance layer

Catalog-2 §19 enumerates 8 items only the operator can verify (eye,
ear, aesthetic judgment). These are NOT automation gaps; they are
the necessary human-in-the-loop feedback channel. The system cannot
self-audit for: aesthetic quality, mix ear-check, programme flow
feel, director utterance veto, package-choice taste, subjective
intentionality, eye-gut coherence, camera framing.

**Proposed**: a weekly operator-review ritual (15 min) where these 8
are scored. Stored as a JSON file the research chronicle consumes.

---

## §3. Staged rollout — from detector-wishlist to monitoring-ready

Given the scale (60+ detectors to build), staged priority:

**Wave A (this week — defensive, monetization)**:
- 6.3 grounding_provenance counter + UNGROUNDED log (alpha queued)
- 6.4 compositional_consumer_dispatch counter (cascade shipped `54a020ea5`)
- 15.8 slur-variant emergence detector (cascade shipped `303e5fd2a`)
- 5.2 face-obscure fail-closed gauge (alpha queued)

**Wave B (next — director/content-programming)**:
- 6.2 intent-frequency-vs-stimmung gauge
- 6.7 Kokoro truncation rate
- 7.6 intent-to-realisation conversion ratio
- 12.3/12.4 affordance + dispatch counters (alpha queued)
- 15.1-15.6 emergent misbehavior detector pack (preset cycling,
  flashing, stuck-frame, silent compositor, overlap-cascade,
  director monoculture)

**Wave C (MixQuality foundation)**:
- 10.1-10.8 per-sub-score + aggregate
- 13.1-13.5 cross-surface coherence counters
- §17.3 audio-spectral harness

**Wave D (replay + retro)**:
- §17.1 replay harness (HLS → re-run audits)
- §17.2 frame-by-frame goldens extension
- Weekly audit-retrospective systemd timer
- §19 operator-review ritual JSON

**Wave E (programmes + long-term)**:
- 8.x/9.x content-programme detectors (after task #164 lands)
- 14.x research-instrument integrity
- 16.x short/long observability split dashboard

---

## §4. Pre-live gate — dynamic addendum to catalog-1 §17

Catalog-1's 30-row pre-live gate adds dynamic rows:
- MixQuality aggregate > 0.7 across 15-min warmup
- §15.x emergent-misbehavior detectors show no fires in warmup
- §18.1 warmup protocol executes clean
- Compositional-consumer veto rate < 10% of dispatches
- Grounding-provenance UNGROUNDED rate < 1%
- Director-monoculture detector shows ≥ 2 preset-families in 15 min

None of these are currently gating (they can't, because the
detectors don't all exist yet). Post-rollout-Waves A-C, these
become enforceable.

---

## §5. Headline single-sentence operator read

**We now have an exhaustive specification (~208 audits across two
catalogs) for what observability the livestream needs; about 60% of
the detectors are missing; cascade has started the Pattern-1
decorator convention (`54a020ea5`) that lets every future emitter
ship with its own paired counter/violation-log/test; operator's
"mix ALWAYS good" invariant is now a named deliverable (MixQuality
aggregate, alpha skeleton this pass); the rest of the work is
disciplined counter-plumbing across the catalog rows.**

---

## Cross-reference appendix

- Catalog-1 final: `docs/research/2026-04-20-audit-synthesis-final.md`
- Catalog-2 raw: `docs/research/2026-04-20-cascade-dynamic-audit-results.yaml` + alpha relay YAML
- Audit-closeout plan: `docs/superpowers/plans/2026-04-20-audit-closeout-plan.md`
- Grounding-provenance fix: `docs/research/2026-04-20-grounding-provenance-invariant-fix.md`
- Prompt-level slur prohibition: `docs/research/2026-04-20-prompt-level-slur-prohibition-design.md`
