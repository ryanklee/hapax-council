---
date: 2026-04-20
author: alpha (Claude Opus 4.7, 1M context, cascade worktree)
audience: delta (execution dispatcher) + operator
register: scientific, neutral
status: dispatchable plan — multi-phase, parallel-safe, operator-gated
task: "#165 — demonetization safety (post-live iteration)"
branch: hotfix/fallback-layout-assignment
related:
  - docs/research/2026-04-19-demonetization-safety-design.md (research source)
  - docs/research/2026-04-19-content-programming-layer-design.md (programmes, task #164)
  - docs/research/2026-04-19-youtube-content-visibility-design.md (adjacent YouTube surface)
  - docs/governance/consent-safe-gate-retirement.md (sibling fail-closed gate precedent)
  - shared/governance/consent.py (capability-level axiom-gate precedent)
  - shared/governance/consent_gate.py (runtime candidate filter precedent)
  - agents/studio_compositor/face_obscure_integration.py (egress-level fail-closed precedent)
  - scripts/lint_personification.py (build-time governance gate precedent, task #155)
  - shared/affordance.py (OperationalProperties — declaration site)
  - shared/compositional_affordances.py (capability catalog)
  - scripts/youtube-player.py (half-speed hack retirement target, task #66)
  - docs/superpowers/plans/2026-04-19-homage-completion-plan.md (format reference)
  - memories: feedback_no_expert_system_rules, project_programmes_enable_grounding,
    feedback_hapax_authors_programmes, feedback_grounding_exhaustive
operator-directive-load-bearing: |
  "at no point should any content ever be a red-flag for de-monetization"
  (2026-04-19)
---

# De-monetization Safety Gate — Implementation Plan

## §0. Scope, intent, and what this plan IS NOT

This plan implements the architectural design in
`docs/research/2026-04-19-demonetization-safety-design.md` as a sequence
of dispatchable phases under delta orchestration. The work lands
post-live — this is the iteration that follows the HOMAGE go-live — and
closes the §165 directive "at no point should any content ever be a
red-flag for de-monetization."

### 0.1 What this plan IS

A **governance-axiom-level fail-closed filter**, implemented as a sibling
to `shared/governance/consent.py::contract_check` and
`agents/studio_compositor/face_obscure_integration.py`. Concretely the
gate occupies the same architectural tier as the existing consent filter
and the egress face-obscure invariant — it operates at the
**axiom-enforcement layer**, removing whole capability classes from the
candidate set before the decision-making layer scores anything.

The architecture is **three concentric rings** (research §4):

- **Ring 1 — capability-level filter.** Runs inside
  `AffordancePipeline.select()` adjacent to the consent filter. Reads
  `OperationalProperties.monetization_risk` and removes `high`
  capabilities unconditionally + `medium` capabilities unless the
  active programme has explicitly opted in. Capabilities never enter
  the score competition.
- **Ring 2 — pre-render classifier.** Runs on LLM-emitted text
  destined for externally visible surfaces. Produces a `RiskAssessment`;
  if `score >= 2` the render is withheld and a `content.flagged`
  impingement is emitted. The pipeline's next tick re-recruits on the
  signal. The classifier is itself a grounded LLM call — it does not
  make the next decision, it emits a perceptual signal.
- **Ring 3 — egress audit log.** Append-only JSONL at
  `~/hapax-state/programmes/egress-audit/<date>/<hour>.jsonl` recording
  every render decision with sampling rate configurable per
  surface-kind.

Programme-layer interaction is restricted to Ring 1 via an explicit
`monetization_opt_ins: frozenset[str]` field on `Programme` — soft priors
that expand `medium`-risk candidacy only. `high` is permanently
excluded; no programme can opt in. Ring 2 classifier ALWAYS runs
regardless of programme state.

### 0.2 What this plan is NOT

**This is NOT a post-hoc deny-list.** There is no code path of the
shape:

```
if "fuck" in rendered_text and count > threshold:
    withhold(rendered_text)
```

Such a gate sits at the decision-making layer and violates
`feedback_no_expert_system_rules`. This plan architects the safety
boundary at the **candidate-filter** layer (Ring 1) — capabilities are
REMOVED from the recruitment-set before the pipeline scores anything,
the same structural move consent performs. Ring 2 runs on top of that
after the LLM has already produced rendered text, and it still does
not decide: it emits an impingement carrying the risk signal, and the
pipeline's next tick recruits an alternative capability against that
impingement in the usual grounded way. The gate **removes**, it does
not **score away**. That is the architectural pattern that preserves
the no-expert-system-rules axiom while providing governance-level
fail-closed safety.

Similarly, this plan does NOT:

- hardcode guideline text into source (guidelines live in a cached
  prompt fragment refreshed via `WebFetch` every 24 h with stale-fallback
  behavior — research §5)
- introduce per-word lists, regex deny-patterns at runtime, or
  threshold counters ("if 3+ profanities then withhold") anywhere in
  the scoring or rendering path
- replace the recruitment pipeline's narrative choice with a
  pre-written "safe alternative" library — the alternative is
  whatever the pipeline recruits next tick from the
  `content.flagged` impingement, grounded in the live moment
- add cadence overrides, interval gates, or timer-based suppression
  (the `suppression_until` window on per-capability false-positive
  recovery is a capability-local base-level decay, not a global
  timer gate)

This plan also does NOT prescribe the music policy in §7 — that is one
of two operator-gated open questions (0.4) and is implemented only
after the operator answers.

### 0.3 Relationship to parallel work

- **Programme layer (task #164).** Phase 5 and Phase 11 of this plan
  depend on the `Programme` primitive landing from that epic. Until
  it lands, Phase 5 ships as a no-op stub with the field declared but
  unwired; Phase 11 is sequenced after #164 Phase 1 (the
  `Programme` + `ProgrammeRegistry` primitives).
- **YouTube content visibility (adjacent design doc).** Phase 7 (music
  provenance) and Phase 8 (music policy) interact with the
  YouTube-visibility surface. Neither blocks the other; the
  interaction is that YouTube reaction content has
  `music_provenance = "youtube-react"` and its audio-bus handling is
  subject to Phase 8's operator-gated policy.
- **Homage completion (parallel cascade epic).** Anti-personification
  footer (Phase 9 here) composes with the chronicle + captions wards
  that Phase A3 of the homage-completion plan rewrites. Phase 9 here
  is sequenced AFTER homage Phase A3 lands on main.

### 0.4 Required operator inputs (blocking)

Two open questions from research §11 are **required-operator-input
gates** for specific phases in this plan. Neither is resolved here;
both are flagged explicitly so delta does not attempt to prescribe
them.

1. **Music policy (research §11 Q1).** Research §7.2 recommends
   YouTube reaction audio MUTED with transcript overlay as default,
   retiring the half-speed DMCA-evasion hack (task #66). Operator
   must confirm or counter-propose before Phase 8 ships. Viability of
   the muted model vs. the §7.2 alternative 2 (≤30 s fair-use clips
   with operator-transformative narration) is part of the same
   decision — operator picks one.
2. **False-negative tolerance (research §11 Q3).** Operator input
   sets the target classifier FNR; governs Ring 2 score cutoff and
   `MAX_OPT_INS`. Phase 3 can ship with a conservative default
   (score cutoff at 2, `MAX_OPT_INS = 3`) pending operator
   confirmation.

Phases 8 and (optionally) 3's cutoff tuning BLOCK on these. All other
phases proceed without operator input.

---

## §1. Success definition — what "done" looks like

The acceptance test is a 30-minute live test stream with instrumented
telemetry, combined with static-analysis gates. The stream runs in
nominal stance with HOMAGE Phase A+B surface active. Below are the
pixel-level and instrument-level criteria every phase below must
ultimately contribute to.

### 1.1 Capability declaration coverage

Every `CapabilityRecord` in `shared/compositional_affordances.py` (and
every capability JSON under `affordances/`) declares an explicit
`monetization_risk: Literal["none", "low", "medium", "high"]` value via
`OperationalProperties.monetization_risk`. Zero capabilities carry the
field's implicit default — the audit commit (Phase 2) makes every
declaration explicit. A CI-blocking test asserts 100 % field presence
across the catalog; a separate test asserts `high`-risk capabilities
have a non-empty `risk_reason`.

### 1.2 Candidate-set filter behavior

A recruitment dry-run over a representative impingement batch
(fixtures: `tests/fixtures/recruitment_impingements.json`) shows:

- `monetization_risk == "high"` capabilities are never in the
  candidate set regardless of programme state
- `monetization_risk == "medium"` capabilities are in the candidate
  set ONLY when the active programme's `monetization_opt_ins`
  contains the capability name
- `monetization_risk == "none"` or `"low"` capabilities are in the
  candidate set unconditionally (subject to existing consent +
  governance filters)
- The filter runs before the score competition — assertions in
  `test_affordance_pipeline_monetization_filter` verify candidates
  are excluded at `_filter_candidates`, not demoted at score time

### 1.3 Ring 2 classifier round-trip

`MonetizationRiskGate.content_classify` against the TabbyAPI
`local-fast` route (Qwen3.5-9B EXL3) completes in **p50 ≤ 10 ms**,
**p99 ≤ 50 ms** over a benchmark of 500 rendered-text samples spanning
the surface-kind taxonomy (TTS, captions, chronicle, activity-header,
director-commentary). The benchmark script lives in
`scripts/benchmark_monetization_classifier.py` and emits results to
`~/hapax-state/benchmarks/monetization-classifier/`.

### 1.4 Fail-closed on classifier unavailable

A chaos test that disables TabbyAPI (simulated via
`HAPAX_TABBYAPI_DISABLE=1` in a test harness or by `systemctl stop
tabbyapi.service` in the staging run) demonstrates:

- All LLM-generated external-surface text (TTS, chronicle, captions,
  director commentary) is withheld
- Template-only emission proceeds for surfaces that have templates
  (activity header gloss, signature artefacts)
- TTS goes silent (Kokoro receives no text)
- The control law triggers: 3 consecutive classifier failures emit
  `classifier.degraded` impingement + `ntfy` priority=high; 5
  consecutive successes restore nominal
- Mirrors the consent-gate-unavailable path in
  `shared/governance/consent_gate.py`

### 1.5 Zero high-risk capabilities in a live candidate set

Over a 30-minute post-live test stream instrumented with
`hapax_monetization_candidates_total{risk="high"}` Prometheus counter,
the value remains **0** for the full duration. A single non-zero
observation fails the acceptance gate.

### 1.6 Egress audit JSONL populated

`~/hapax-state/programmes/egress-audit/2026-XX-XX/HH.jsonl` contains
one entry per rendered external-surface payload across the 30-minute
window. Sampling: 100 % during the first 48 hours of post-live, 10 %
steady-state after (configurable via `HAPAX_EGRESS_AUDIT_SAMPLE`).
Each entry has `timestamp`, `surface_kind`, `capability`,
`rendered_text` (truncated 512 chars), `classifier_score`, `guideline`,
`music_provenance`, `youtube_source`, `decision`, `decision_reason`.
Daily gzip rotation + 90-day retention configured via systemd timer
`hapax-egress-audit-rotate.timer`.

### 1.7 Half-speed hack removed

`scripts/youtube-player.py` contains no `_playback_rate` function and
no references to `HAPAX_YOUTUBE_PLAYBACK_RATE`. CI test
`tests/scripts/test_youtube_player_no_playback_rate.py` asserts both
(regression pin for task #66 retirement). The retirement is coupled
to Phase 8 landing — if operator selects alternative 2 (fair-use
clips), the half-speed hack is replaced by the clip-windowing
mechanism instead of by the mute path.

### 1.8 Anti-personification egress footer present

Chronicle and captions ward layouts show the muted-grey low-prominence
footer "Council research instrument — experimental cognitive
architecture (operator: <name>, research home: <url>)" persistent
across all stream modes. Footer text passes Ring 0 + Ring 2 once at
startup and is cached. A layout-snapshot regression test captures the
footer's presence, grey tone, and low-prominence alpha.

### 1.9 Observability

Prometheus metrics under `hapax_monetization_*` emit to the running
council Prometheus scrape (already wired for `hapax_homage_*` and
`hapax_cpal_*`). Grafana dashboard
`localhost:3001/d/monetization-gate/` shows:

- `hapax_monetization_candidates_total{risk, filtered}` — counter
  of filter decisions per risk class
- `hapax_monetization_classifier_seconds` — histogram of Ring 2
  latency
- `hapax_monetization_classifier_score_total{surface_kind, score}` —
  counter of Ring 2 outcomes
- `hapax_monetization_classifier_degraded` — gauge (0/1)
- `hapax_monetization_egress_audit_entries_total` — counter of
  audit log writes
- `hapax_monetization_whitelist_entries` — gauge (Phase 10)

Dashboard panels show strictly-increasing counters during the test
stream and a zero-bar on `risk="high"`.

---

## §2. Phase list

Eleven phases. Each phase has: scope (file paths bounded), blocking
dependencies, parallel-safe siblings, success criteria, test strategy,
LOC range, commit-message template, and (where relevant) operator-gate
marker.

All phases commit directly to `hotfix/fallback-layout-assignment`. Do
NOT switch branches. Do NOT use `isolation: "worktree"` (operator-
mandated subagent git safety per workspace CLAUDE.md). Each commit is
self-contained and ends with the standard
`Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>`
trailer.

Size legend: **S** ≤ 200 LOC, **M** 200-500, **L** 500-1500.

### Phase 1 — `MonetizationRiskGate` primitive + field declaration

**Scope:**

- `shared/governance/monetization_safety.py` — NEW module hosting
  `MonetizationRiskGate`, `RiskAssessment` (Pydantic frozen),
  `SurfaceKind` enum, `MonetizationRisk` Literal type alias
- `shared/affordance.py` — EXTEND `OperationalProperties` with
  `monetization_risk: Literal["none", "low", "medium", "high"] = "none"`
  and `risk_reason: str | None = None`
- `agents/hapax_dmn/pipeline.py` (or wherever `AffordancePipeline.select`
  + `_filter_candidates` live — confirm at dispatch time) — WIRE
  `MonetizationRiskGate.candidate_filter` into `_filter_candidates`
  adjacent to the existing consent filter
- Tests: `tests/governance/test_monetization_safety.py` +
  `tests/pipeline/test_affordance_pipeline_monetization_filter.py`

**Description.** Ship the primitive and the field. The module owns
the single-source of truth for risk enums and the Ring-1 filter. The
filter is pure: signature
`candidate_filter(capabilities: list[Capability], programme: Programme
| None) -> list[Capability]`. `monetization_risk == "high"` removed
unconditionally; `"medium"` removed unless programme is not-None AND
its `monetization_opt_ins` contains the capability name; `"low"` and
`"none"` pass through. The Ring-1 wire inserts a call in
`_filter_candidates` next to the consent call. Existing consent test
fixtures are copied-and-adapted as the pattern template. No
Ring-2 classifier yet (Phase 3).

**Blocking dependencies:** None. Leaf module.

**Parallel-safe siblings:** Phase 2 (catalog audit) reads Phase 1's
field declaration; dispatch Phase 2 only AFTER Phase 1's field is
merged to main (serial). Phases 4, 5, 6 can land in parallel with
Phase 1.

**Success criteria:**

- `uv run pytest tests/governance/test_monetization_safety.py -q`
  passes (≥ 8 tests: field-default, filter-high-always-out,
  filter-medium-gated-by-opt-in, filter-low-passes, filter-none-passes,
  programme-None-excludes-medium, programme-with-opt-in-includes-medium,
  filter-is-pure)
- `uv run pytest tests/pipeline/test_affordance_pipeline_monetization_filter.py -q`
  passes (≥ 4 tests: filter-runs-before-score, consent+monetization-
  compose, high-never-in-candidates, medium-present-when-opted-in)
- `uv run ruff check shared/governance/monetization_safety.py` clean
- `uv run pyright shared/governance/monetization_safety.py` clean
- Importable: `from shared.governance.monetization_safety import
  MonetizationRiskGate, RiskAssessment` at REPL
- Existing `consent.py` + `consent_gate.py` tests still pass (no
  regression on the sibling filter)

**Test strategy.** Pure unit tests for the primitive. Pipeline
integration test uses a fake `AffordancePipeline.select` harness with
a fixture capability set spanning all four risk classes. Golden
assertion: filter is run at the `_filter_candidates` stage, verified
by inserting a capture-side-effect into a mocked scorer that asserts
it never sees `risk="high"` capabilities.

**Estimated LOC:** 250-350 module + 200-300 tests. **Size: M.**

**Commit message template:**

```
feat(governance): MonetizationRiskGate primitive + OperationalProperties.monetization_risk

Phase 1 of demonetization-safety-plan. Introduces
shared/governance/monetization_safety.py hosting MonetizationRiskGate
and RiskAssessment, and extends OperationalProperties with a
monetization_risk field. Ring-1 candidate filter wired into
AffordancePipeline._filter_candidates adjacent to the consent filter.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
```

### Phase 2 — Capability catalog audit + risk classification

**Scope:**

- `shared/compositional_affordances.py` — one-time survey pass:
  annotate every `CapabilityRecord` with an explicit
  `monetization_risk` + `risk_reason` (where non-`none`) in its
  `operational` field
- All capability JSONs under `affordances/` — same annotation pass;
  loader at `shared/affordance_loader.py` confirms field round-trips
- `docs/governance/monetization-risk-classification.md` — NEW
  governance doc recording the classification rubric + per-capability
  rationale, with the research §1.1 category table as its citation
  base
- Tests: `tests/governance/test_capability_catalog_complete.py` —
  CI-blocking assertion that every registered capability carries a
  non-default (explicit) `monetization_risk` annotation

**Description.** One-time survey commit. Every capability in the
catalog — currently on the order of 200 — is classified against the
research §1.1 YouTube advertiser-friendly categories, and the result
written back as the `monetization_risk` + `risk_reason` pair on its
declaration. The classification rubric is written first as the
governance doc, then applied systematically. Categories triggering
`high`: unfiltered profanity-eligible speech capabilities, raw-audio
broadcast capabilities for non-provenanced music, anything emitting
graphic violence / sexual / hate content (the catalog shouldn't have
any; this phase verifies). Categories triggering `medium`: narrative
registers that permit occasional-strong-profanity, reaction-content
capabilities whose input is third-party, album-art-splattribution
narrative registers. Everything else: `none` or `low`.

**Blocking dependencies:** Phase 1 (field declaration must be merged
to main before annotation).

**Parallel-safe siblings:** Phases 4, 5, 6 can run alongside.

**Success criteria:**

- `test_capability_catalog_complete` asserts `monetization_risk` is
  explicitly set (not implicit default) for every registered
  capability
- `test_capability_catalog_high_risk_has_reason` asserts every
  `high` capability has `risk_reason` non-empty
- Catalog loads cleanly; no Pydantic validation errors
- Governance doc published + cross-linked from
  `docs/governance/README.md`

**Test strategy.** Catalog iteration tests. Governance doc reviewed
via operator-read; its classification rubric becomes the reference
document for future capability authors. Author a `CONTRIBUTING`-style
note in the doc: "new capabilities default `none`, promote to `low` /
`medium` / `high` per rubric §3".

**Estimated LOC:** 400-700 (mostly annotations + governance doc).
**Size: M.**

**Commit message template:**

```
chore(governance): capability catalog — classify monetization_risk per rubric

Phase 2 of demonetization-safety-plan. Every registered capability
now carries an explicit monetization_risk annotation. Governance doc
docs/governance/monetization-risk-classification.md records the
classification rubric and per-capability rationale.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
```

### Phase 3 — Ring 2 pre-render classifier + `content.flagged` impingement

**Scope:**

- `shared/governance/monetization_safety.py` — ADD
  `content_classify(rendered_text, surface_kind) -> RiskAssessment`
  method to `MonetizationRiskGate`
- `agents/hapax_dmn/cognitive/director.py` (or wherever the
  `local-fast` LiteLLM client lives for the grounded director) —
  re-use the existing model client; no new VRAM
- `agents/cpal/production_stream.py` — INSERT classifier call after
  TTS text generation, before TTS synthesis
- `agents/studio_compositor/captions_source.py` — INSERT classifier
  call after LLM-generated caption text is received
- `agents/studio_compositor/chronicle_*.py` (where chronicle LLM
  emissions land) — same insertion
- `shared/impingements.py` (or equivalent) — ADD
  `ContentFlaggedImpingement` + `ContentIncidentImpingement` types
- `tests/governance/test_monetization_classifier.py`
- `tests/integration/test_content_flagged_impingement_roundtrip.py`
- `scripts/benchmark_monetization_classifier.py` (benchmark harness)

**Description.** Ring 2 lands. The classifier is a structured JSON-only
sub-prompt against the grounded director's model (`local-fast` →
TabbyAPI Qwen3.5-9B). Prompt structure per research §5: cached YouTube
guidelines (24 h WebFetch refresh, stale-fallback), surface kind,
rendered text, JSON output `{score, guideline, redaction_suggestion}`.
Score semantics: 0 none, 1 low (audit-only), 2 medium (withhold +
`content.flagged`), 3 high (withhold + `content.incident` +
`suppression_until = now + 5 ticks` on the capability).

On `score >= 2`:

1. Do NOT render (no TTS synth, no caption paint, no chronicle push).
2. Emit `ContentFlaggedImpingement` (score 2) or
   `ContentIncidentImpingement` (score 3) to the impingement bus
   carrying `{surface_kind, score, guideline, original_capability,
   redaction_suggestion}`.
3. The pipeline's next tick reads the impingement as perceptual
   ground and recruits an alternative capability. No retry logic;
   recovery is grounded in the usual recruitment loop.

LRU cache `(rendered_text → RiskAssessment, maxsize=1024)` on the
classifier call reduces repeated-text load (chronicle headers,
attribution lines).

**Operator gate.** Score cutoff (default 2) and MAX_OPT_INS (default
3) stay at conservative defaults until operator answers §11 Q3
(false-negative tolerance). Default ships; operator can tighten.

**Blocking dependencies:** Phase 1 (primitive). Phase 2 (field
coverage is audited before Ring 2 starts classifying emissions from
capabilities that should never emit in the first place).

**Parallel-safe siblings:** Phase 4 (fail-closed path) — Phase 3's
classifier wiring surfaces the failure mode Phase 4 handles. Phases
5, 6, 7 parallel-safe.

**Success criteria:**

- `test_monetization_classifier` passes (≥ 10 tests: score parsing,
  prompt construction, guideline cache, LRU reuse, surface-kind
  discrimination, JSON-error handling)
- `test_content_flagged_impingement_roundtrip` passes: classifier
  emits impingement → next-tick pipeline consumes → recruits
  alternative capability (integration test with mock pipeline)
- Benchmark `scripts/benchmark_monetization_classifier.py` records
  p50 ≤ 10 ms, p99 ≤ 50 ms over 500 samples against running TabbyAPI
- `uv run ruff check`, `uv run pyright` clean on all touched files
- Post-deploy test-stream smoke: send a deliberately flagged
  synthetic utterance via test injection, observe withhold +
  impingement + alternative recruitment in
  `~/hapax-state/daimonion-cpal.jsonl`

**Test strategy.** Unit tests with a mocked LiteLLM client. One
integration test with a real TabbyAPI call behind a pytest marker
`@pytest.mark.llm` (excluded from default test run). Benchmark is a
standalone script, not a pytest.

**Estimated LOC:** 400-600 (classifier method + 3 call-sites + 2
impingement types + benchmark + tests). **Size: M-L.**

**Commit message template:**

```
feat(governance): Ring-2 pre-render classifier + content.flagged impingement

Phase 3 of demonetization-safety-plan. MonetizationRiskGate.content_classify
runs on LLM-emitted text for external surfaces (TTS, captions, chronicle).
Score >= 2 withholds render and emits ContentFlaggedImpingement for
pipeline next-tick re-recruitment. Uses the grounded director model
(local-fast -> TabbyAPI); no new VRAM.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
```

### Phase 4 — Classifier unavailable → fail-closed template-only path

**Scope:**

- `shared/governance/monetization_safety.py` — ADD
  `ClassifierDegradedController` mirroring
  `shared/governance/consent_gate.py`'s degradation controller
  (3-failure-degrade, 5-success-restore)
- `agents/cpal/production_stream.py`,
  `agents/studio_compositor/captions_source.py`, and chronicle
  emission path — INSERT `if gate.classifier_degraded(): withhold`
  wrappers
- `shared/notify.py` — existing API, no change
- Tests: `tests/governance/test_classifier_degraded_controller.py` +
  `tests/chaos/test_fail_closed_on_classifier_unavailable.py`

**Description.** Implement the control law from research §9 row 3.
The controller tracks a rolling window of classifier call outcomes;
`degrade` state triggers when ≥ 3 consecutive calls fail (timeout,
exception, malformed JSON). In `degrade` state, ALL external-surface
emissions from LLM-generated text are withheld — TTS goes silent,
captions stop updating, chronicle holds its last frame. Templates
still emit (activity header gloss, signature artefacts, ward labels
— all hand-authored and Ring-0-covered). `ntfy priority=high` fires
on entry to `degrade`. Five consecutive successful calls restore
nominal. Pattern matches consent-gate-unavailable exactly.

**Blocking dependencies:** Phase 3 (classifier exists to be
degraded).

**Parallel-safe siblings:** Phase 5, 6, 7.

**Success criteria:**

- `test_classifier_degraded_controller` passes (≥ 6 tests:
  3-failures-degrade, 5-successes-restore, hysteresis, thread-safe
  invocation, ntfy-on-degrade, ntfy-on-restore)
- `test_fail_closed_on_classifier_unavailable` chaos test: stop
  TabbyAPI via systemd (in CI container this is a mocked client
  that raises); observe TTS silent, captions stop updating,
  chronicle holds frame, templates still render, ntfy fired
- Existing control-law tests on `consent_gate.py` still pass

**Test strategy.** Controller unit tests use a fake clock + fake
classifier invocation. Chaos test uses a pytest fixture that
monkeypatches the classifier to raise, then asserts downstream
behavior (TTS not called, caption text unchanged, chronicle not
appended).

**Estimated LOC:** 250-350. **Size: M.**

**Commit message template:**

```
feat(governance): classifier-degraded fail-closed path

Phase 4 of demonetization-safety-plan. ClassifierDegradedController
mirrors consent_gate's degradation pattern (3-fail -> degrade, 5-success
-> restore). In degrade state all external-surface LLM emissions are
withheld; templates proceed. ntfy priority=high on entry/exit.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
```

### Phase 5 — Programme `monetization_opt_ins` field + Ring 1 programme wiring

**Scope:**

- `shared/programmes.py` (or wherever the `Programme` primitive lands
  from task #164 Phase 1) — EXTEND `Programme` with
  `monetization_opt_ins: frozenset[str] = frozenset()`
- `shared/governance/monetization_safety.py` — Ring 1 already accepts
  `programme: Programme | None`; wire the opt-ins set into its
  decision
- `shared/programmes_validation.py` — ENFORCE: Hapax-authored
  programmes with non-empty `monetization_opt_ins` fail validation;
  operator-authored programmes allowed up to `MAX_OPT_INS = 3`
- `tests/governance/test_programme_monetization_opt_ins.py`

**Description.** The programme-layer interaction surface per research
§6. `Programme.monetization_opt_ins` is a `frozenset[str]` naming
capability names whose `monetization_risk == "medium"` the programme
accepts. `high` is permanently out (validation enforced). Operator-
authorship is the authorship axis (per
`feedback_hapax_authors_programmes`, programmes are Hapax-authored —
but the `monetization_opt_ins` field is the one exception where
operator-authored programmes bypass the Hapax-only rule because it
expands capability candidacy beyond the default safe set, and such
expansion requires operator consent). Hard cap `MAX_OPT_INS = 3`
prevents opt-in abuse. Ring 2 classifier ALWAYS runs regardless of
opt-in — opt-in expands candidacy, does not bypass classification.

**Dependency note.** This phase depends on the `Programme` primitive
from task #164. Until #164 Phase 1 lands, Phase 5 ships as a
no-op stub: the field is declared but no programme is ever active, so
Ring 1 always sees `programme=None` and filters all medium-risk
capabilities out. When #164 lands, a follow-up commit wires the
live `programme` lookup.

**Blocking dependencies:** Phase 1 (Ring 1 primitive). Task #164
Phase 1 (`Programme` primitive) for the non-stub wiring.

**Parallel-safe siblings:** 4, 6, 7.

**Success criteria:**

- `test_programme_monetization_opt_ins` passes (≥ 6 tests:
  hapax-authored-with-opt-in-fails-validation,
  operator-authored-with-opt-in-passes, max-opt-ins-3-enforced,
  high-risk-never-opted-in, ring-1-respects-opt-ins,
  ring-2-runs-regardless-of-opt-in)
- `test_affordance_pipeline_monetization_filter` extended to cover
  the programme-active-with-opt-in path

**Estimated LOC:** 150-250. **Size: S.**

**Commit message template:**

```
feat(governance): Programme.monetization_opt_ins + Ring-1 wiring

Phase 5 of demonetization-safety-plan. Programme gains a frozenset
of capability names whose medium-risk monetization gate the programme
expands. Hapax-authored programmes with opt-ins fail validation;
operator-authored cap MAX_OPT_INS = 3. Ring 2 classifier unaffected.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
```

### Phase 6 — Egress audit JSONL + sampling + rotation

**Scope:**

- `shared/governance/monetization_safety.py` — ADD
  `EgressAuditWriter` + `egress_log(payload, decision, reason)` method
  on `MonetizationRiskGate`
- `agents/cpal/production_stream.py`,
  `agents/studio_compositor/captions_source.py`, chronicle emission
  path — call `egress_log` after render decision (both `rendered`
  and `withheld` branches)
- `config/defaults.py` — ADD `HAPAX_EGRESS_AUDIT_SAMPLE_LOW = 0.1`,
  `HAPAX_EGRESS_AUDIT_SAMPLE_HIGH = 1.0`, post-live-48h toggle
- `systemd/user/hapax-egress-audit-rotate.service` + `.timer` —
  daily gzip rotation + 90-day prune
- Tests: `tests/governance/test_egress_audit_writer.py`,
  `tests/systemd/test_hapax_egress_audit_rotate_timer.py`

**Description.** Ring 3 lands. JSONL path:
`~/hapax-state/programmes/egress-audit/<YYYY-MM-DD>/<HH>.jsonl`. Per
entry: `timestamp`, `surface_kind`, `capability`, `rendered_text`
(truncated 512 chars), `classifier_score`, `guideline`,
`music_provenance` (nullable), `youtube_source` (nullable),
`decision` (`rendered` | `withheld`), `decision_reason` (ring that
triggered). Sampling: configurable per surface-kind; post-live 48 h
runs at 100 % sampling across all surfaces, then
high-risk-surface-only stays at 100 % while low-risk drops to 10 %.
Atomic append via a single-writer `EgressAuditWriter` backed by a
queue + background thread (avoid blocking the render path). Daily
gzip rotation + 90-day retention via systemd timer. Rotation failure
ntfys but the writer continues to log (log-integrity > disk hygiene
per research §9 row 5).

**Blocking dependencies:** Phase 1 (gate primitive exists). Can
land parallel to 3, 4, 5 — gate is hollow until Ring 2 emits, but
the writer itself is ready to receive calls from Phase 3/4 when
they land.

**Parallel-safe siblings:** Phases 3, 4, 5, 7, 9.

**Success criteria:**

- `test_egress_audit_writer` passes (≥ 8 tests: append atomicity,
  sampling correctness, truncation, directory rotation on hour
  boundary, thread-safety, queue overflow policy, gzip-rotation
  invocation, 90-day prune)
- Systemd timer test: `systemctl --user start
  hapax-egress-audit-rotate.service` succeeds; rotated files appear
  under `egress-audit/<date>/<hour>.jsonl.gz`
- Post-deploy smoke: 30 s test stream produces N log entries where
  N ≥ 3 (at least one TTS + one caption + one chronicle)
- `du -sh ~/hapax-state/programmes/egress-audit/` stays < 100 MiB
  after a 4-hour stream

**Test strategy.** Writer unit tests use a tmp-path JSONL dir. Timer
test invokes the rotation script in dry-run mode against a fixture
tree.

**Estimated LOC:** 300-450 (writer + systemd unit + tests).
**Size: M.**

**Commit message template:**

```
feat(governance): Ring-3 egress audit JSONL + sampling + rotation

Phase 6 of demonetization-safety-plan. EgressAuditWriter appends every
render decision to ~/hapax-state/programmes/egress-audit/<date>/<hour>.jsonl.
Sampling 100% post-live-48h, 10% steady-state for low-risk surfaces.
Daily gzip rotation + 90-day retention via hapax-egress-audit-rotate.timer.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
```

### Phase 7 — Music provenance tagging

**Scope:**

- `shared/music/provenance.py` — NEW module hosting `MusicProvenance`
  Literal type + per-track metadata schema
- `agents/studio_compositor/album_overlay.py` — ADD provenance tag
  rendered in the splattribution (muted-grey BitchX register, bottom
  line)
- SoundCloud ingestion path (confirm location at dispatch; likely
  `agents/music/soundcloud_ingest.py` or similar) — ENUMERATE
  license at ingestion, default `unknown` excluded from queue
- Vinyl playlist loader — ANNOTATE every track
  `provenance="operator-vinyl"`
- Future Hapax-pool ingestion path — stub accepting only `cc-by`,
  `cc-by-sa`, `public-domain`, `licensed-for-broadcast`
- Ring 3 egress log already carries `music_provenance` field
  (added in Phase 6); wire the value through
- Tests: `tests/music/test_provenance_loader.py`

**Description.** Schema-first. Provenance values:
`operator-vinyl`, `soundcloud-licensed`, `hapax-pool`,
`youtube-react`, `unknown`. `unknown` fail-closed: audio muted,
`music.provenance.unknown` impingement fires for operator review.
SoundCloud ingestion reads license metadata from the SoundCloud API
at ingest time; tracks without a clear license stay `unknown` and
are excluded from the play queue. Vinyl annotations are trivially
`operator-vinyl` (operator owns the physical record; HIGH DMCA risk
on broadcast accepted). Hapax-pool ingestion is a stub in this
phase — the full pool curation path lands separately (task #130).
YouTube-react provenance is the Phase 8 interaction surface.

**Operator gate touch.** This phase does NOT implement the
audio-mute-on-YouTube policy (that is Phase 8). But it does
establish the data shape Phase 8 consumes.

**Blocking dependencies:** Phase 6 (egress log schema has
`music_provenance` slot).

**Parallel-safe siblings:** 3, 4, 5, 6, 9.

**Success criteria:**

- `test_provenance_loader` passes (≥ 6 tests: vinyl-annotation,
  soundcloud-licensed-parsing, soundcloud-unknown-excluded,
  hapax-pool-accepts-cc-by, hapax-pool-rejects-proprietary,
  youtube-react-annotation)
- Egress audit log entries for any music emission carry the
  correct `music_provenance` value
- Album-overlay splattribution visible-read post-deploy shows
  provenance line in muted-grey

**Estimated LOC:** 300-400. **Size: M.**

**Commit message template:**

```
feat(music): per-track provenance tagging (operator-vinyl | soundcloud-licensed | hapax-pool | youtube-react | unknown)

Phase 7 of demonetization-safety-plan. Every music emission carries
a MusicProvenance tag. SoundCloud ingestion enumerates license at
ingest; unknown excluded from queue. Vinyl annotated operator-vinyl.
Hapax-pool stub accepts only license-cleared families. Egress audit
log records provenance per entry.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
```

### Phase 8 — OPERATOR-GATED music policy implementation

**OPERATOR GATE.** This phase DOES NOT dispatch until the operator
answers research §11 Q1 (mute + transcript overlay vs. §7.2
alternative 2 fair-use clips). The plan documents both paths; the
operator picks one.

**Scope (path A — mute + transcript overlay, research recommendation):**

- `scripts/youtube-player.py` — REMOVE `_playback_rate` function
  + `HAPAX_YOUTUBE_PLAYBACK_RATE` env var + all calls; the
  half-speed hack (task #66) dies here. Mute the audio output
  via ffmpeg `-af volume=0` or pipeline-level audio tee drop
- `agents/studio_compositor/youtube_turn_taking.py` (or dedicated
  YouTube-embed-ward renderer) — ADD transcript overlay surface
  that renders source captions (when available from YouTube's
  `--write-subs` data) in BitchX register over the video
- `tests/scripts/test_youtube_player_no_playback_rate.py` —
  regression pin ensuring `_playback_rate` stays dead

**Scope (path B — ≤ 30 s fair-use clips, if operator prefers):**

- `scripts/youtube-player.py` — REPLACE `_playback_rate` with
  `_clip_windower`: enforces ≤ 30 s contiguous playback, ≥ 60 s
  operator-transformative narration gap before same-source replay
- `agents/cpal/production_stream.py` — wire the windower signal
  into the recruitment surface so the pipeline is aware of
  same-source cooldown
- Regression pin drops

**Description.** Per research §7.2. The operator makes the choice.
Whichever path ships, the half-speed rate manipulation is retired.
Path A is the research recommendation (Content ID is audio-only; muted
audio cannot match). Path B carries higher strike risk but keeps the
audio signal for reaction framing. Both paths preserve the Phase 7
`youtube-react` provenance tag.

**Blocking dependencies:** Phase 7 (provenance shape). OPERATOR
ANSWER on research §11 Q1.

**Parallel-safe siblings:** 9.

**Success criteria (both paths):**

- `scripts/youtube-player.py` no longer defines `_playback_rate`
- `HAPAX_YOUTUBE_PLAYBACK_RATE` env var unreferenced in the
  codebase
- Regression pin `test_youtube_player_no_playback_rate` green

**Success criteria (path A only):**

- YouTube audio output muted on the post-deploy test stream
- Transcript overlay visible in the YouTube embed ward when source
  captions are present
- Egress audit log shows `music_provenance: "youtube-react"` +
  `decision: "audio_muted"` for YouTube plays

**Success criteria (path B only):**

- Playback automatically cuts at 30 s contiguous window
- Same-source replay blocked until ≥ 60 s narration gap observed
  via director emissions

**Estimated LOC:** 150-300 (both paths are small). **Size: S-M.**

**Commit message template (path A):**

```
feat(youtube): mute audio + transcript overlay (task #66 retirement)

Phase 8A of demonetization-safety-plan. Retires _playback_rate half-
speed DMCA-evasion hack per research §7.2 recommendation. YouTube
audio muted; transcript overlay renders source captions in the
YouTube embed ward. Regression pin asserts _playback_rate stays dead.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
```

**Commit message template (path B):**

```
feat(youtube): 30s fair-use clip windower (task #66 retirement)

Phase 8B of demonetization-safety-plan. Retires _playback_rate half-
speed DMCA-evasion hack per research §7.2 alternative 2. Playback
capped at 30s contiguous; ≥60s operator-transformative narration
gap required before same-source replay.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
```

### Phase 9 — Anti-personification egress footer

**Scope:**

- `agents/studio_compositor/chronicle_source.py` — ADD persistent
  footer row at bottom of chronicle ward, muted-grey low-prominence,
  BitchX register:
  `>>> Council research instrument — experimental cognitive architecture (operator: <name>, research home: <url>)`
- `agents/studio_compositor/captions_source.py` — ADD same footer as
  a permanent low-prominence line beneath the caption strip
- Footer text through Ring 0 + Ring 2 validation ONCE at startup, then
  cached (avoid per-frame classifier overhead on static text)
- `config/defaults.py` — ADD `HAPAX_OPERATOR_NAME`,
  `HAPAX_RESEARCH_HOME_URL` config keys
- Tests: `tests/studio_compositor/test_chronicle_footer.py`,
  `tests/studio_compositor/test_captions_footer.py`

**Description.** Per research §8. Frames the channel for advertiser
review without claiming AI sentience. Operator name + research URL
contextualize the channel as operator-driven research. Footer text is
cached at startup; its passing Ring 2 validation once suffices
because it is static.

**Blocking dependencies:** HOMAGE Phase A3 (legibility family emissive
rewrite) must land on main first — the chronicle and captions wards
get Pango-Px437 rendering from A3, and the footer composes onto that
rendering path.

**Parallel-safe siblings:** 3, 4, 5, 6, 7, 10.

**Success criteria:**

- Chronicle ward layout snapshot shows the footer bottom-row,
  muted-grey alpha ≤ 0.55
- Captions ward snapshot shows the footer beneath the caption strip
- Footer text matches operator config (not hardcoded)
- Startup log records the one-time Ring 2 validation pass result

**Estimated LOC:** 150-220. **Size: S.**

**Commit message template:**

```
feat(homage): anti-personification "research instrument" egress footer

Phase 9 of demonetization-safety-plan. Persistent muted-grey BitchX-
register footer on chronicle + captions wards: "Council research
instrument — experimental cognitive architecture (operator: <name>,
research home: <url>)". Frames channel for advertiser review per
research §8. Footer text Ring-0+Ring-2 validated once at startup.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
```

### Phase 10 — Operator review + whitelist CLI

**Scope:**

- `scripts/review-flagged.sh` — NEW CLI wrapper; invokes
  `uv run python -m agents.monetization_review`
- `agents/monetization_review/` — NEW module (Tier 3, deterministic,
  no LLM): reads `~/hapax-state/monetization-flagged/`, presents
  one flagged payload at a time via `fzf` or `rich`, operator selects
  `a`ccept (render proceeds on next pattern match),
  `r`eject (pattern stays flagged), or `w`hitelist (regex or exact
  pattern added to allow-list)
- `~/hapax-state/monetization-whitelist.yaml` — operator-curated
  whitelist file, loaded by `MonetizationRiskGate` on startup +
  on SIGHUP
- Tests: `tests/monetization_review/test_review_cli.py`

**Description.** False-positive recovery surface. Flagged payloads
time-window at 7 days in
`~/hapax-state/monetization-flagged/<date>/<capability>.jsonl`. CLI
presents operator with context (capability name, surface kind,
rendered text, classifier rationale) and accepts a decision. Whitelist
entries are regex by default; research §11 Q6 flags regex-vs-exact
as an open question — plan ships with both forms supported and
operator-config default. Whitelist narrows Ring 2 only — never
bypasses Ring 1 high-risk filter.

**Blocking dependencies:** Phase 3 (flagged impingements exist to
review). Phase 6 (egress log provides audit trail).

**Parallel-safe siblings:** 9, 11.

**Success criteria:**

- `scripts/review-flagged.sh` runnable end-to-end
- Whitelist entries persist across restart (loaded from YAML)
- SIGHUP reloads whitelist without restart
- Whitelist NEVER bypasses high-risk filter (test asserts)

**Estimated LOC:** 350-500. **Size: M.**

**Commit message template:**

```
feat(monetization): operator review + whitelist CLI

Phase 10 of demonetization-safety-plan. scripts/review-flagged.sh
presents flagged payloads to the operator with accept/reject/whitelist
decisions. Whitelist lives at ~/hapax-state/monetization-whitelist.yaml,
loaded on startup + SIGHUP. Narrows Ring 2; never bypasses Ring 1
high-risk filter.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
```

### Phase 11 — Incident-recovery "quiet-frame" programme

**Scope:**

- `shared/programmes/quiet_frame.py` — NEW programme definition
  (vinyl-only music, no TTS, no chronicle narrative; only templates
  + ward emphasis on biometric-rest signals)
- `agents/hapax_dmn/programme_switcher.py` (or wherever programme
  transitions live from task #164) — ADD `content.incident` →
  quiet-frame programme auto-entry for 20 ticks + auto-exit
- Tests: `tests/programmes/test_quiet_frame_transitions.py`

**Description.** Per research §9 row 1 + §10 Phase 8. On
`ContentIncidentImpingement` (classifier score 3), the programme
switcher auto-enters `quiet-frame` for 20 ticks. Quiet-frame disables
all LLM-emitted external-surface text, keeps vinyl-only music,
preserves ward-emphasis-on-biometric-rest (breathing, stillness),
keeps the anti-personification footer. Auto-exits after 20 ticks to
the prior programme. Operator can manually force an earlier exit via
Stream Deck cue.

**Blocking dependencies:** Phase 3 (incident impingement type).
Task #164 Phase 1 (programme primitive).

**Parallel-safe siblings:** 10.

**Success criteria:**

- `test_quiet_frame_transitions` passes: incident → programme entry
  observed within ≤ 2 ticks; auto-exit after 20 ticks; operator
  forced exit works
- Post-deploy injection test: synthetic score-3 flagged utterance
  triggers quiet-frame entry; observe TTS silent, vinyl continuing,
  ward emphasis on rest for 20 ticks

**Estimated LOC:** 200-300. **Size: M.**

**Commit message template:**

```
feat(programmes): quiet-frame incident-recovery programme

Phase 11 of demonetization-safety-plan. ContentIncidentImpingement
(classifier score 3) triggers 20-tick auto-entry to quiet-frame:
vinyl-only music, no LLM-emitted external text, ward emphasis on
biometric rest. Auto-exits after 20 ticks; operator can force earlier.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
```

---

## §3. Dependency DAG + critical path

### 3.1 Dependency graph

```
Phase 1 (primitive + field) ─── BLOCKER
       │
       ├─> Phase 2 (catalog audit)
       ├─> Phase 3 (Ring 2) ─── BLOCKER for 4, 11
       │       │
       │       └─> Phase 4 (fail-closed)
       │
       ├─> Phase 5 (programme opt-ins, needs task #164 P1 for non-stub)
       ├─> Phase 6 (egress audit) ─── feeds 7, 10
       │       │
       │       └─> Phase 7 (music provenance)
       │                   │
       │                   └─> Phase 8 (OPERATOR-GATED music policy)
       │
       └─> Phase 9 (footer) ─── depends on HOMAGE A3 on main

Phase 10 (review CLI) depends on Phase 3 + Phase 6
Phase 11 (quiet-frame) depends on Phase 3 + task #164 P1
```

### 3.2 Critical path

**Phases 1 → 3 → 4** is the minimum-viable safety surface and the
critical path. Rough LOC:

- Phase 1: 450-650 LOC (~4-6 dispatch-hours)
- Phase 3: 600-900 LOC (~6-9 hours)
- Phase 4: 250-350 LOC (~2-3 hours)

Serial critical path: **~12-18 dispatch-hours**. With parallel
dispatch on Phase 2 + 5 + 6 landing in the same window, the full
Phases 1-7 + 9 + 10 deploy is **~18-24 dispatch-hours** end-to-end.

Phase 8 blocks on operator answer; cannot be critical-pathed from
the plan.

Phase 11 blocks on task #164 Phase 1 external to this plan; target
sequencing is "after task #164 primitive lands on main".

### 3.3 Blockers summary

- **External:** task #164 (programme primitive) for Phases 5 (non-stub)
  and 11. HOMAGE A3 (legibility emissive rewrite) on main for Phase 9.
- **Operator:** §11 Q1 answer gates Phase 8. §11 Q3 answer (optional)
  gates tuning of Phase 3 cutoffs.
- **Phase-internal:** Phase 2 serial after Phase 1. Phase 4 serial
  after Phase 3. Phase 7 serial after Phase 6.

---

## §4. Per-phase risk register

| # | Phase | Highest-consequence failure mode | Mitigation |
|---|---|---|---|
| 1 | Primitive + field | Field added but `_filter_candidates` wiring subtly wrong (e.g., runs after scoring) | Pipeline integration test `test_filter_runs_before_score` asserts via capture-side-effect into mocked scorer |
| 2 | Catalog audit | Miscategorised capability (high-risk declared as low) | Governance doc rubric is the reference; a second operator-review pass recommended before merging the catalog commit |
| 3 | Ring 2 classifier | Classifier latency blows p99 > 50 ms under real load | Benchmark script pre-merge + LRU cache + operating-envelope control law in Phase 4 |
| 4 | Fail-closed | Controller fires on transient errors (single timeout), TTS goes silent unnecessarily | 3-failure hysteresis, 5-success restore, matches proven consent-gate pattern |
| 5 | Programme opt-ins | Hapax-authored programme sneaks in opt-ins via validation bypass | Validation is Pydantic `model_validator`; tests enforce both paths |
| 6 | Egress audit | Log fills disk, rotation race condition drops entries | Daily gzip rotation + 90-day prune; rotation failure ntfys but writer continues to log (research §9 row 5) |
| 7 | Music provenance | SoundCloud metadata missing license field → everything lands `unknown` → queue empty | Ingestion error path surfaces `music.provenance.unknown` impingement for operator review per track |
| 8 | Music policy (gated) | Wrong path chosen; strike risk remains | Operator picks the path — plan does not prescribe |
| 9 | Footer | HOMAGE A3 reverts; footer floats orphan above JetBrains Mono text | Phase 9 depends explicitly on A3 being on main; dispatch gate checks |
| 10 | Whitelist | Regex pattern too broad, re-opens risk surface | Whitelist narrows Ring 2 only; high-risk Ring 1 filter never bypassed; hard-coded in `test_whitelist_never_bypasses_ring_1` |
| 11 | Quiet-frame | Auto-entry loop (incident during quiet-frame → re-entry) | Suppression on the `content.incident` impingement source during active quiet-frame window; tested |

---

## §5. Branch / PR strategy

**One branch.** All phases commit to `hotfix/fallback-layout-assignment`.
No new branches. No branch switching. Subagent git-safety directive
(verbatim): "You are working in the cascade worktree. Branch is
`hotfix/fallback-layout-assignment`. Commit directly to this branch.
Do NOT create branches. Do NOT run `git checkout` or `git switch`. Do
NOT switch branches under any circumstances." This appears in every
dispatch prompt.

**Per-phase PR.** The gate touches many files (capability catalog
annotations alone span dozens) and involves governance-axiom-level
policy decisions. Per-phase PRs are cleaner than one mega-PR for
three reasons:

1. **Review surface.** A 200-LOC governance primitive PR reviews
   faster than a 2 000-LOC mixed-concern PR. Each phase's
   commit-message template (above) frames the review.
2. **Partial landing.** If Phase 3 (Ring 2) benchmarks poorly, it
   can hold in PR while Phases 4, 5, 6, 7 continue — they depend
   only on Phase 1's primitive, which landed in its own PR.
3. **Operator gates.** Phase 8 blocks on operator answer. It cannot
   sit mid-PR alongside Phase 7 content; separating PRs keeps each
   at a ready-to-merge state.

**Merge order per critical path:** 1 → 2 → 3 → 4 → (6 → 7 → 8) || 5
|| 9 || 10 || 11. Parallel-merge-capable: 2, 5, 6 after 1; 4 after 3;
7 after 6; 9 after HOMAGE A3; 10 after 3+6; 11 after 3 + task #164.

**Squash-merge.** Each PR squash-merges to keep `main` history linear
with one commit per phase, matching the HOMAGE plan convention.

**CI.** All PRs pass `uv run pytest tests/ -q`, `uv run ruff check .`,
`uv run ruff format --check .`, `uv run pyright`. Phase 3 gate:
benchmark script results posted as PR comment with p50/p99 table.
Phase 6 gate: systemd timer passes `systemd-analyze verify`.

---

## §6. Acceptance checklist

Work is NOT done until every item below is ticked. This runs after the
final phase merges; it is the go-no-go for declaring the §165
directive closed.

### 6.1 Static analysis

- [ ] `uv run pytest tests/ -q` passes (full suite, not just
  governance/)
- [ ] `uv run ruff check .` clean
- [ ] `uv run ruff format --check .` clean
- [ ] `uv run pyright` clean
- [ ] `scripts/lint_personification.py` extended per research §4.4
  (Ring 0); CI-blocking on hand-authored surfaces
- [ ] `test_capability_catalog_complete` passes (every capability
  has explicit `monetization_risk`)
- [ ] `test_youtube_player_no_playback_rate` passes (task #66
  retirement pin)

### 6.2 Live stream observation (30-minute test stream)

- [ ] `hapax_monetization_candidates_total{risk="high"}` remains
  0 for the full 30-minute window
- [ ] `hapax_monetization_classifier_seconds` p50 ≤ 10 ms, p99 ≤
  50 ms
- [ ] `hapax_monetization_classifier_degraded == 0` for the full
  window
- [ ] Egress audit JSONL populated for every external-surface
  emission in the window
- [ ] At least one synthetic-injected score-≥2 payload is
  withheld + recovery observed on next tick (Phase 3 end-to-end
  validation)
- [ ] Anti-personification footer visibly present on chronicle +
  captions wards
- [ ] YouTube embed ward shows muted audio + transcript overlay
  (path A) OR ≤ 30 s clip windower (path B), per operator choice
- [ ] Album overlay splattribution shows provenance tag
  (`operator-vinyl` on vinyl, etc.)

### 6.3 Chaos + recovery

- [ ] `systemctl --user stop tabbyapi.service` → classifier
  degrades within 3 failed attempts; TTS silent; templates still
  emit; `ntfy priority=high` fires
- [ ] `systemctl --user start tabbyapi.service` → 5 successful
  classifier calls → nominal restored; TTS resumes
- [ ] Whitelist SIGHUP reload works without restart
- [ ] Whitelist entry cannot bypass high-risk filter (regression
  test green)

### 6.4 Governance

- [ ] `docs/governance/monetization-risk-classification.md`
  published, cross-linked from `docs/governance/README.md`
- [ ] Operator-reviewed capability catalog classification
- [ ] Operator answer on §11 Q1 (music policy) recorded + Phase 8
  merged
- [ ] Operator answer on §11 Q3 (FNR tolerance) recorded + cutoff
  tuned (optional)

### 6.5 Observability

- [ ] Grafana dashboard `monetization-gate` shows strictly-
  increasing counters during the test stream
- [ ] Zero-bar on `risk="high"` candidate counter
- [ ] 90-day retention timer `hapax-egress-audit-rotate.timer`
  active + tested

---

## §7. Notes for execution subagents

### 7.1 Dispatch order

Delta dispatches in this order, honoring the DAG:

1. **Wave 1 (serial on Phase 1):** Phase 1 alone. Merge to main.
2. **Wave 2 (parallel after Phase 1 on main):** Phase 2, 5 (stub
   form), 6 in parallel.
3. **Wave 3 (serial on Phase 3):** Phase 3 after Phase 2 merges.
4. **Wave 4 (parallel after Phase 3 on main):** Phase 4, 7, 9
   (Phase 9 gates on HOMAGE A3 being on main). 10 after 3+6 merge.
5. **Wave 5 (blocked on operator + external):** Phase 8 on operator
   answer; Phase 11 on task #164 Phase 1.

### 7.2 Per-dispatch prompt skeleton

Each dispatch to an execution subagent includes verbatim:

```
You are working in the cascade worktree
(/home/hapax/projects/hapax-council--cascade-2026-04-18). Branch is
hotfix/fallback-layout-assignment. Commit directly to this branch.
Do NOT create branches. Do NOT run `git checkout` or `git switch`.
Do NOT switch branches under any circumstances.

Implement Phase <N> of docs/superpowers/plans/2026-04-20-demonetization-safety-plan.md
exactly as specified. Do not introduce any expert-system-style rules:
the gate REMOVES capabilities at the candidate-filter layer; it does
NOT score away or threshold-gate at the decision layer. If tempted to
add a regex match, a threshold counter, or a timer gate anywhere in
the scoring or rendering path, stop and re-read §0.2 of the plan.

Commit message: follow the phase's commit-message template verbatim.
```

### 7.3 Common failure mode to reject

If a dispatch returns a diff containing any of:

- `if <token/phrase> in rendered_text`
- `if count > N` on risk words
- hardcoded regex deny-list
- `if ticks % N == 0` gating on risk
- `HAPAX_*_INTERVAL_S` env var on risk-related cadence

— reject the diff. These are decision-layer patterns and violate the
no-expert-system-rules axiom. The correct architectural move is
always: (a) declare `monetization_risk` on the capability (Ring 1),
or (b) emit an impingement and let the pipeline re-recruit
(Ring 2).

### 7.4 Test-data fixtures

Phase 3 benchmark requires a 500-sample rendered-text corpus. Source
fixtures are:

- Recent chronicle emissions from
  `~/hapax-state/daimonion-cpal.jsonl` (tail last 72 hours)
- Recent TTS text from `~/hapax-state/tts-queue.jsonl`
- Synthetic injections spanning all five §1.1 categories (borderline
  profanity, violence reference, controversial issue discussion,
  graphic detail attempt, slur attempt)

Collect the corpus as `tests/fixtures/classifier_corpus_500.json`,
checked in under test fixtures. Corpus generation script:
`scripts/build_classifier_corpus.py`.

### 7.5 Operator-gate signaling

When a phase blocks on operator answer, delta updates the relay
status to include a `monetization-plan-blocked-on-operator` field
naming the specific question. Operator visibility surface:
`hapax-council` orientation panel domain = "research",
sprint-measure surfaced via vault frontmatter on
`20-projects/hapax-research/2026-04-20-demonetization-gate.md`.

### 7.6 Rebase discipline

Every phase dispatch begins with:

```
cd /home/hapax/projects/hapax-council--cascade-2026-04-18
git fetch origin
git rebase origin/hotfix/fallback-layout-assignment  # or main after merge
```

and ends with:

```
git rebase origin/hotfix/fallback-layout-assignment
git push origin hotfix/fallback-layout-assignment
```

if the feature branch is still live, or `origin/main` after merge.
Concurrent planning subagents may have pushed; rebase-before-push is
mandatory.

### 7.7 Research condition

HOMAGE opens research condition `cond-phase-a-homage-active-001`.
Demonetization-gate opens its own research condition when Phase 1
merges: `cond-monetization-gate-active-001`. Director-intent records
after Phase 3 carry it; the Bayesian validation pipeline can slice
pre/post-gate. Phase 1 dispatch includes the condition open call as
its final sub-step.

### 7.8 Post-live window

Per task #165 scoping, this plan is "post-live iteration." HOMAGE
goes live first. The Ring 1 filter (Phase 1) ships immediately after
HOMAGE merges — it is cheap and the governance exposure of running
post-live without Ring 1 is material. Phases 3-11 land over the
subsequent 48-72 hours. The 30-minute acceptance test stream is run
after all non-gated phases land (everything except 8 if operator has
not yet answered).

---
