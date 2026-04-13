# Phase 4 — SCM metrics read-state + next signals

**Queue item:** 025
**Phase:** 4 of 6
**Date:** 2026-04-13 CDT
**Register:** scientific, neutral (per `feedback_scientific_register.md`)

## Headline

The SCM (Stigmergic Cognitive Mesh) has four live metric surfaces
— eigenform, sheaf restriction consistency, topology, and
stimmung — all reporting **near-zero or pinned-at-cold-start
values** in the live system.

| metric | live value | interpretation |
|---|---|---|
| eigenform convergence | `converged=True`, `eigenform_type="fixed_point"`, `max_delta=0.0`, `orbit_amplitude=0.0` | **pathological fixed point** — 951 log entries all identical |
| restriction residual rms | 0.2416 | moderate inconsistency; 4 of 6 restriction pairs disagree |
| h1_dimension | 4 | 4 independent inconsistency cycles (out of 6 residual pairs) |
| sheaf graph Betti-0 (components) | 1 (fully connected) | healthy — all 14 nodes reachable from each other |
| stimmung `overall_stance` | `"cautious"` | reference=0.0, perception=0.3, error=0.3 |
| stimmung health | 0.072 | **LOW** — system reports degraded health |
| exploration_deficit | 0.546 | **HIGH** — above the 0.35 SEEKING trigger |
| processing_throughput | 0.008 | near-zero — almost no work happening |
| perception_confidence | 0.068–0.092 | **LOW** |
| grounding_quality | 0.0 | floor, freshness 121 s stale |
| operator_stress | 0.0 | not observed |
| operator_energy | 0.7 | moderate |
| physiological_coherence | 0.5 | baseline |

The SCM is in a **convergent-but-degraded** state: the eigenform
says the system has reached a fixed point, but the fixed point is
"nothing is happening" — processing throughput near zero,
perception confidence low, grounding quality floored. The sheaf
restriction consistency says "4 independent inconsistencies
persist." The topology is fully connected but that is a
structural given from the static graph (`shared/sheaf_graph.py:8`);
it does not reflect live component activity.

**The SCM is a passive reader.** None of its metrics feed back
into control decisions that would move them off the floor. The
sheaf health is consumed by `visual_layer_aggregator.py:1154` for
a single stimmung dimension reporting. The eigenform log is
consumed by `chronicle_sampler.py` for session summaries. The
topology graph is not read by any runtime code — it exists only
as a development-time reference.

## Live data inventory

### 1. Eigenform state vector stream

**Location:** `/dev/shm/hapax-eigenform/state-log.jsonl`
**Writer:** `shared/eigenform_logger.py::log_state_vector`
**Called from:** `agents/visual_layer_aggregator/aggregator.py:58`
**Cadence:** per VLA tick (slow-tick, ~3 s based on observed log deltas)

**Live contents** (last 3 entries, all identical):

```json
{"t": 1776123575.31, "presence": 0.0019, "flow_score": 0.0,
 "audio_energy": 0.0, "stimmung_stance": "cautious",
 "imagination_salience": 0.0, "visual_brightness": 0.25,
 "heart_rate": 0.0, "operator_stress": 0.0, "activity": "",
 "e_mesh": 0.0429, "restriction_residual_rms": 0.2416}
```

**951 entries in the log.** All recent entries report **identical
state vectors** — presence 0.0019, flow_score 0.0, audio_energy
0.0, and so on. The eigenform analysis classifies this as
`fixed_point` with `max_delta=0.0` and `orbit_amplitude=0.0`.

**Problem: the fixed point is "nothing is moving"**, not a
meaningful attractor. The eigenform converges because none of its
inputs are changing, not because the system has reached any
interesting equilibrium. The classification is technically
correct but operationally vacuous.

### 2. Sheaf restriction consistency

**Location:** `shared/sheaf_health.py::compute_restriction_consistency`
**Live computation result:**

```python
{
  "consistency_radius": 0.2416,
  "h1_dimension": 4,
  "residual_count": 6,
  "residuals": [0.25, 0.25, 0.053, 0.4, 0.0, 0.25],
  "timestamp": 1776123597.29
}
```

**6 restriction pairs computed, 4 are inconsistent (≥0.05).** The
largest residual is 0.4 (out of an expected 0–1 range). `h1_dimension=4`
means there are 4 independent inconsistency cycles, which indicates
the restriction maps do not commute along the sheaf graph.

Per the Robinson (2017) reference in the module header, this is a
moderately inconsistent sheaf. A value of 0 would be fully
consistent; ≥0.5 would be highly inconsistent.

Consumed by: `visual_layer_aggregator.py:1154` (one dimension
reporting). No runtime behavior changes based on the value.

### 3. Sheaf graph topology

**Location:** `shared/sheaf_graph.py`

14 nodes, 24 edges, 1 weakly-connected component.

```python
SCM_NODES = [
    "ir_perception", "contact_mic", "voice_daemon", "dmn",
    "imagination", "stimmung", "temporal_bonds", "apperception",
    "reactive_engine", "compositor", "reverie", "voice_pipeline",
    "content_resolver", ...
]
```

Top 5 by degree:

```text
dmn            9
voice_daemon   8
stimmung       7
reverie        6
imagination    5
```

**The DMN is the most central node in the sheaf graph (degree 9).**
Voice daemon is a close second (8). Stimmung is third (7). This
matches the project memory's claim that "DMN is a topological
critical node."

**But the topology is static** — it is hard-coded in
`sheaf_graph.py:8`. It is not measured from runtime behavior. If
the DMN stopped emitting, the graph would still report
`degree_centrality["dmn"] = 9` because the graph is the
specification, not the observation.

### 4. Stimmung (the 12-dimensional inner state)

**Location:** `/dev/shm/hapax-stimmung/state.json` and
`/dev/shm/hapax-sensors/stimmung.json`

**Live values** (at 23:40:25 CDT):

| dimension | value | trend | freshness |
|---|---|---|---|
| health | 0.072 | stable | 0 s |
| resource_pressure | 0.0 | stable | 0 s |
| error_rate | 0.0 | stable | 0 s |
| processing_throughput | 0.008 | **falling** | 0 s |
| perception_confidence | 0.068 | stable | 0 s |
| llm_cost_pressure | 0.0 | stable | 0 s |
| grounding_quality | 0.0 | stable | **121 s stale** |
| exploration_deficit | 0.546 | stable | 0 s |
| operator_stress | 0.0 | stable | 0 s |
| operator_energy | 0.7 | stable | 0 s |
| physiological_coherence | 0.5 | stable | 0 s |
| **overall_stance** | `cautious` | — | — |

**Observations:**

- **`health = 0.072`** is very low. Per queue 024 Phase 4 the
  daimonion is actually healthy (running, CPU normal, memory
  stable). But stimmung reports 7% health. Either the dimension's
  thresholds are miscalibrated or it is reading a subsystem
  failure state that the daimonion itself does not surface.
- **`processing_throughput = 0.008`** is near-zero and trending
  down. During active voice use this should move toward 0.5–1.0.
  Near-zero means no utterances are flowing, which matches queue
  024 Phase 4's "zero TTS log lines" observation.
- **`perception_confidence = 0.068`** is very low. In a fully-
  instrumented session this should be 0.3–0.7. Low confidence
  indicates multiple perception backends are dormant or failing
  (Phase 4 of queue 024 listed 5 missing backends).
- **`grounding_quality = 0.0` with 121 s stale freshness**. The
  stale freshness means the grounding layer has not updated in 2
  minutes. `grounding_quality = 0.0` is the cold-start default;
  without a fresh update, the value reports floor.
- **`exploration_deficit = 0.546`** is above the **0.35 SEEKING
  trigger**. Per `CLAUDE.md § Exploration`, when deficit > 0.35
  and all dimensions are nominal, stance transitions to SEEKING.
  But the current stance is `cautious`, not SEEKING. Why? Because
  the dimensions are **NOT** all nominal: health is 0.072 (low),
  perception_confidence is 0.068 (low). The SEEKING stance is
  gated on nominal dimensions; the current state is degraded-
  cautious, not exploratory.

## Cross-reference with project memory

`MEMORY.md § SCM` says:

> [SCM formalization](project_scm_formalization.md) — Stigmergic
> Cognitive Mesh: 6 properties, 16 PRs, 14 control laws, 7
> research docs. Sheaf/topology/eigenform metrics operational.

The memory claims these metrics are "operational." Phase 4
confirms the metrics are *computed* and *stored*, but they are:

1. **Pinned at degraded values** — the live readings are
   consistent with a system in a degraded-cautious state
2. **Not fed back into control** — no runtime behavior changes
   based on eigenform convergence, sheaf consistency, or topology
3. **Not consumed by Grafana** — per round-3 Phase 2, the
   compositor is not scraped, so any derived metrics are invisible
4. **Used for session summaries only** — chronicle_sampler.py
   reads them for post-hoc reporting

**"Operational" is a generous reading.** The metrics exist. They
produce numbers. The numbers are not used. They are development-
time instrumentation dressed as runtime signals.

## Ranked next-signal candidates

What would move the metrics off their current floor?

### 1. Fresh `grounding_quality` updates (currently 121 s stale)

The grounding layer writes the GQI (Grounding Quality Index) into
stimmung. The writer has not fired for 121 seconds. Either:

- The conversation pipeline has not processed an utterance in 2
  minutes (matches zero-TTS observation)
- The GQI writer is broken and no longer writes
- Stimmung's freshness polling is broken

Root cause investigation: `agents/visual_layer_aggregator/` that
writes grounding_quality. Would need a fresh utterance to
disambiguate "no work happening" from "writer broken."

### 2. Presence detection feeding eigenform

The eigenform log shows `presence = 0.0019` (near zero), yet the
operator is clearly present (this research is running on the
operator's machine). The `presence_engine.py` Bayesian model
outputs a different number (queue 024 Phase 4 confirmed it works).
**The eigenform log is reading a different presence source.** Grep
for the call site:

```bash
grep -rn "presence=.*log_state_vector\|presence_val\|state_vector.*presence" \
  agents/visual_layer_aggregator/aggregator.py
```

Likely the VLA is reading from a different `presence_score` field
that is not wired to the presence engine's actual output. This is
a broken wiring candidate worth chasing.

### 3. Activity field (currently empty string)

`"activity": ""` across all 951 log entries. Someone wired the
activity dimension into the log but nothing populates it. The
compositor's contact mic has an `activity` classification
(`desk_activity`: idle/typing/tapping/drumming/active) — is that
the intended source? Grep:

```bash
grep -rn "activity_mode\|desk_activity" agents/visual_layer_aggregator/
```

### 4. Heart rate (currently 0.0)

`"heart_rate": 0.0` — the operator's Pixel Watch feeds biometric
data via `hapax-watch-receiver.service`. The value should be
60–80 bpm during normal work. Zero indicates either the watch is
out of range, the receiver is broken, or the VLA is not reading
the feed. Per CLAUDE.md § Bayesian Presence, `watch_hr` is a
primary signal. Cross-reference against a live query to the
watch receiver.

### 5. Operator stress (always 0.0)

Stress is supposed to come from voice tone + heart-rate variability
+ keyboard dynamics. All three sources have feeding paths in the
codebase, but the dimension stays pinned at 0.0. Without a
real-world probe (operator saying something stressful), cannot
distinguish "no stress" from "stress calculation broken."

## Mapping: next-signal candidates → what metrics would move

| candidate | feeds metric | expected movement |
|---|---|---|
| grounding_quality fresh writer | stimmung.grounding_quality | 0.0 → 0.3–0.7 |
| presence wiring fix | eigenform.presence | 0.0019 → 0.6–0.9 (when present) |
| activity dimension wiring | eigenform.activity | "" → "typing" / "active" / ... |
| watch_hr pipeline validation | eigenform.heart_rate, stimmung.physiological_coherence | 0.0 → 60–80 |
| stress calculation probe | stimmung.operator_stress | 0.0 → 0.1–0.5 |

Moving any one of these would make the eigenform a moving target
again (not a fixed point), the sheaf restriction residual would
have new inputs to propagate, and the stimmung stance could
exit `cautious` into SEEKING or NOMINAL.

## Gap analysis

### What the SCM layer has

- A computed sheaf restriction residual RMS
- A computed sheaf restriction h1_dimension (cohomology)
- A static 14-node sheaf graph with network-x analysis available
- An eigenform state vector stream (951 entries)
- A stimmung dimension publisher (12 dimensions)

### What the SCM layer lacks

1. **Runtime feedback**: nothing uses the metrics to gate behavior.
   The whole layer is instrumentation dressed as control.
2. **Dynamic topology**: the sheaf graph is hand-written, not
   measured from runtime component activity.
3. **Freshness enforcement**: grounding_quality is 121 s stale;
   nothing alerts on this.
4. **Derivative metrics**: no gauge for "is the eigenform actually
   moving," "is the sheaf becoming more or less consistent,"
   "is the topology's critical node healthy."
5. **Correlation with axiom outcomes**: no link between SCM
   state and axiom compliance events (BETA-FINDING-K type
   violations).
6. **Prometheus exposition**: the sheaf / eigenform / stimmung
   metrics are not on any Prometheus endpoint (queue 024 Phase 6
   + round 3 Phase 2). They live only in SHM files.

## Ranked next-signal investments

1. **Fix the grounding_quality freshness** — 1 hour, unblocks
   the primary stimmung input. Investigate whose writer is stuck.
2. **Wire the eigenform state vector inputs** — medium effort
   (several grep + fix passes). Presence, activity, heart_rate,
   stress are all populated elsewhere but the VLA→eigenform
   writer is disconnected from their real values.
3. **Expose SCM metrics on the compositor Prometheus exporter** —
   requires round 3 Phase 2 scrape fix first. Then one new
   series per metric.
4. **Add a "moving eigenform" gauge** — `eigenform_state_velocity`
   measures the L2 distance between consecutive state vectors.
   A flat 0.0 current value would identify fixed-point stalls.
5. **Grafana dashboard for SCM health** — post-FINDING-H fix.
   Panel for each dimension + the sheaf consistency + the
   eigenform type.
6. **Stress-test with operator input** — validate that a live
   operator utterance moves throughput, perception_confidence,
   grounding_quality off the current floor.

## Backlog additions (for retirement handoff)

114. **`fix(vla): grounding_quality writer unblocking`** [Phase 4 candidate 1] — 121 s stale at measurement. Identify the writer, confirm it's firing, fix the freshness gap.
115. **`fix(eigenform): presence + activity + heart_rate wiring`** [Phase 4 candidate 2] — VLA writes zeros to the eigenform log despite real sources existing. Trace the aggregator path and reconnect.
116. **`feat(compositor+vla): SCM metrics on Prometheus endpoint`** [Phase 4 candidate 3] — depends on round 3 Phase 2 FINDING-H fix. 1 new series per stimmung dimension, 1 for consistency_radius, 1 for h1_dimension.
117. **`feat(vla): eigenform_state_velocity gauge`** [Phase 4 candidate 4] — L2 distance between consecutive state vectors. Detects fixed-point stalls (current live value is the textbook stall case).
118. **`feat(grafana): SCM health dashboard`** [Phase 4 candidate 5] — depends on #116. One dashboard showing all 12 stimmung dimensions + sheaf consistency + eigenform type.
119. **`research(scm): does a live operator utterance actually move these metrics?`** [Phase 4 candidate 6] — end-to-end validation. Operator says something, watch stimmung.processing_throughput go from 0.008 to 0.5, confirm writer → reader → gauge path is alive.
120. **`docs(project_scm_formalization): refine 'operational' to 'instrumented but not control-feeding'`** [Phase 4 interpretation] — the current memory overclaims. A refined version would say "the metrics are computed and stored; they do not yet feed back into runtime control."
