# Stimmung aggregate signal drift verification

**Date:** 2026-04-15
**Author:** beta (queue #236, identity verified via `hapax-whoami`)
**Scope:** verify the visual-layer-aggregator → stimmung → /dev/shm pipeline is live + flag any drift against the module docstring baseline.
**Branch:** `beta-phase-4-bootstrap`

---

## 0. Summary

**Verdict: pipeline LIVE + corroborates the silent-failure theme from queues #220/#233.** Three findings:

1. ✅ **VLA pipeline is live and fresh.** `visual-layer-aggregator.service` active; `/dev/shm/hapax-stimmung/state.json` and `/dev/shm/hapax-visual/visual-chain-state.json` both 0-2 seconds old at read time.
2. 🟡 **Documentation drift in `shared/stimmung.py` module docstring.** Line 9 says "10 dimensions (6 infrastructure + 1 cognitive + 3 biometric)" but the `SystemStimmung` class has **11 dimensions (6 + 2 + 3)** — `exploration_deficit` was added alongside `grounding_quality` in the cognitive group, and the docstring was never updated.
3. 🔴 **Perception confidence is catastrophically low: 0.037 (3.7%).** Cross-references queue #220 (watch HR stale 9 days) + queue #233 (contact mic null audio for 98+ min). The aggregate stimmung dimension is correctly detecting the silent failures, AND the `overall_stance` has transitioned from `nominal` → `cautious` in response. But no operator-facing alert fires on this — the cautious stance only modulates the visual surface.

Plus two dimensions (`resource_pressure`, `grounding_quality`) are stale at 121s, just past the 120s `_STALE_THRESHOLD_S`. They are excluded from the stance computation per design.

**Severity:** LOW for (1) — pipeline is healthy. LOW for (2) — comment-only. MEDIUM for (3) — same root cause as #220/#233, this is corroborating evidence that the stance-based alerting gap is worth fixing.

## 1. Pipeline liveness

```
$ systemctl --user is-active visual-layer-aggregator
active

$ ls -la /dev/shm/hapax-visual/
-rw-r--r-- 1 hapax hapax   82312 Apr 15 16:48 frame.jpg
-rw-r--r-- 1 hapax hapax 8294400 Apr 15 16:48 frame.rgba
-rw-r--r-- 1 hapax hapax     589 Apr 15 16:48 visual-chain-state.json

$ ls -la /dev/shm/hapax-stimmung/
-rw-r--r-- 1 hapax hapax 109 Apr 15 16:47 health.json
-rw-r--r-- 1 hapax hapax 827 Apr 15 16:47 state.json
```

File-freshness test at now=1776289696:

| File | mtime | Age |
|---|---|---|
| `/dev/shm/hapax-visual/visual-chain-state.json` | 1776289696 | **0 s** |
| `/dev/shm/hapax-stimmung/state.json` | 1776289694 | **2 s** |
| `/dev/shm/hapax-stimmung/health.json` | 1776289694 | **2 s** |

**All three primary output files are live, updated every ~1-2 seconds.** VLA is writing faithfully.

## 2. Stimmung dimension state (snapshot)

```json
{
  "health":                  {"value": 0.031, "trend": "stable",  "freshness_s": 0.0},
  "resource_pressure":       {"value": 0.0,   "trend": "stable",  "freshness_s": 121.0},  // STALE
  "error_rate":              {"value": 0.0,   "trend": "stable",  "freshness_s": 0.0},
  "processing_throughput":   {"value": 0.002, "trend": "falling", "freshness_s": 0.0},
  "perception_confidence":   {"value": 0.037, "trend": "falling", "freshness_s": 0.0},   // LOW
  "llm_cost_pressure":       {"value": 0.0,   "trend": "stable",  "freshness_s": 0.0},
  "grounding_quality":       {"value": 0.0,   "trend": "stable",  "freshness_s": 121.0},  // STALE
  "exploration_deficit":     {"value": 0.546, "trend": "stable",  "freshness_s": 0.0},
  "operator_stress":         {"value": 0.0,   "trend": "stable",  "freshness_s": 0.0},
  "operator_energy":         {"value": 0.7,   "trend": "stable",  "freshness_s": 0.0},
  "physiological_coherence": {"value": 0.5,   "trend": "stable",  "freshness_s": 0.0},
  "overall_stance": "cautious",
  "timestamp": 1776289679.2088616
}
```

**11 dimensions + overall_stance + timestamp.** Breakdown:

| Category | Dimensions | Count |
|---|---|---|
| Infrastructure (weight 1.0) | health, resource_pressure, error_rate, processing_throughput, perception_confidence, llm_cost_pressure | 6 |
| Cognitive (weight 0.3) | grounding_quality, exploration_deficit | 2 |
| Biometric (weight 0.5) | operator_stress, operator_energy, physiological_coherence | 3 |
| **Total** | | **11** |

## 3. Drift: docstring says 10, reality is 11

`shared/stimmung.py:9-10`:

```python
"""VLA self-state modeling.

10 dimensions (6 infrastructure + 1 cognitive + 3 biometric), each a
DimensionReading with value/trend/freshness. Overall stance derived from
...
```

**Actual class** (`shared/stimmung.py:55-73`):

```python
class SystemStimmung(BaseModel):
    """Unified self-state vector — 10 dimensions + derived stance."""

    # Infrastructure dimensions (weight 1.0)
    health: DimensionReading = Field(...)                  # 1
    resource_pressure: DimensionReading = Field(...)       # 2
    error_rate: DimensionReading = Field(...)              # 3
    processing_throughput: DimensionReading = Field(...)   # 4
    perception_confidence: DimensionReading = Field(...)   # 5
    llm_cost_pressure: DimensionReading = Field(...)       # 6

    # Cognitive dimensions (weight 0.3 — epistemic state, lighter than infrastructure)
    grounding_quality: DimensionReading = Field(...)       # 7
    exploration_deficit: DimensionReading = Field(...)     # 8  ← ADDED, docstring not updated

    # Biometric dimensions (weight 0.5 — softer thresholds, operator changes slowly)
    operator_stress: DimensionReading = Field(...)         # 9
    operator_energy: DimensionReading = Field(...)         # 10
    physiological_coherence: DimensionReading = Field(...) # 11
```

**The docstring on line 9 AND the class docstring on line 56 both say "10 dimensions" but the actual field count is 11.** The cognitive group has `grounding_quality` + `exploration_deficit` = 2 fields, not 1. `exploration_deficit` was added (probably during the queue #528-#536 exploration signal system epic per CLAUDE.md) and the docstring was never updated.

**Severity:** LOW (comment-only drift, doesn't affect behavior). Fix: update both docstrings to say "11 dimensions (6 infrastructure + 2 cognitive + 3 biometric)". Proposed as part of the next CLAUDE.md rotation pass.

## 4. Perception confidence catastrophe + silent-failure cross-ref

**`perception_confidence: 0.037`** — the aggregate perception confidence is **3.7%**. Per `_compute_aggregate_confidence()` in `agents/hapax_daimonion/_perception_state_writer.py:188-204`:

```python
def _compute_aggregate_confidence(perception: PerceptionEngine) -> float:
    """Compute aggregate confidence from registered backend availability.

    Returns 1.0 when all backends are contributing fresh data,
    lower when backends are missing or stale.
    """
    try:
        backends = perception.registered_backends
        if not isinstance(backends, dict) or not backends:
            return 0.5
        available_count = sum(
            1 for b in backends.values() if getattr(b, "available", lambda: True)()
        )
        return round(available_count / len(backends), 3)
    except Exception:
        return 1.0
```

**Interpretation:** 0.037 means `available_count / total_count ≈ 3.7%`. If there are ~27 registered backends (per queue #234 audit), that implies **~1 backend is currently reporting `available=True`**. The other ~26 are returning `False` from their `available()` check.

This is an extraordinary signal that:

- Queue #220 watch HR stale 9 days → watch backend `available=False`
- Queue #233 contact mic null audio → contact_mic backend may still return `available=True` but produces zero signal (the true `chronic_error` is caught by the exploration tracker, not the `available()` method)
- Queue #230 Studio 24c absent → contact_mic + mixer_input backends' upstream hardware is broken
- Multiple other backends may be reporting unavailable due to cascading failures

**And the stimmung dimension IS catching it** — `perception_confidence: 0.037` is correctly reflecting the degraded state.

**BUT: no operator-facing alert fires.** The stance has transitioned to `cautious`, but per `shared/stimmung.py:31` the Stance enum maps stances to visual-surface modulation, NOT to operator notifications:

- `nominal` → no visual modulation
- `seeking` → modulation for SEEKING stance
- `cautious` → modulation (what we have now)
- `degraded` → modulation
- `critical` → modulation

The operator would need to be actively watching the visual surface OR running `cat /dev/shm/hapax-stimmung/state.json` to see that `perception_confidence = 0.037` and `overall_stance = cautious`. Same root-cause alerting gap as queue #242 (proposed in queue #233 §7.3) — the system KNOWS but doesn't TELL.

**This corroborates the #242 proposal precisely.** Adding a generic health-monitor rule that watches for:

- `perception_confidence < 0.1` for >60s → ntfy push
- `overall_stance != nominal` for >60s → ntfy push
- Any `chronic_error >= 1.0` in `/dev/shm/hapax-exploration/*.json` for >60s → ntfy push

would have surfaced today's degraded state directly.

## 5. Stale dimensions

Two dimensions are at exactly **121.0 seconds** of staleness, just past the 120s `_STALE_THRESHOLD_S`:

- `resource_pressure` (stable, value=0.0) — suggests the resource pressure collector has stopped ticking. Should normally update every <60s.
- `grounding_quality` (stable, value=0.0) — suggests the grounding quality collector has stopped ticking.

Per `shared/stimmung.py:84`:

```python
if dim.freshness_s > _STALE_THRESHOLD_S:
    lines.append(f"  {name}: stale ({dim.freshness_s:.0f}s)")
```

AND per `shared/stimmung.py:109`:

```python
if dim.value >= 0.3 and dim.freshness_s <= _STALE_THRESHOLD_S:
```

Stale dimensions are excluded from `non_nominal_dimensions()` and from stance computation (`_compute_stance()` at line 596+). So these two dimensions are NOT contributing to the current `cautious` stance — the stance is being driven entirely by `perception_confidence` (value=0.037 with `trend: falling`) and `exploration_deficit` (value=0.546, above SEEKING threshold).

**The 121s freshness is right on the boundary.** At 120 seconds the dimensions are considered fresh; at 121 seconds they're considered stale. The collectors for these two dimensions are ticking roughly once every 2 minutes — at the edge of the allowed window. A tick cadence of 90s or less would keep them in the "fresh" regime.

**Non-urgent.** The stance is correctly detecting system state even without these two dimensions. But the 121s edge-case is suspicious — worth a follow-up to investigate whether the collectors are intentionally ticking at 2 min or just missing their cadence.

## 6. Visual-chain-state snapshot

```json
{
  "levels": {
    "visual_chain.intensity": 0.579,
    "visual_chain.coherence":  0.379
  },
  "params": {
    "noise.amplitude":         0.329,
    "post.vignette_strength": -0.132,
    "rd.feed_rate":           -0.004,
    "noise.frequency_x":      -0.379,
    "fb.decay":                0.038,
    ...
  },
  "timestamp": 1776289688.0512495
}
```

The visual chain writer is emitting per-parameter deltas that feed the reverie shader pipeline. Cross-references CLAUDE.md § Reverie Vocabulary Integrity:

> "Visual chain → GPU bridge has two paths, both must be alive:
> 1. Shared 9-dim uniform slots.
> 2. Per-node `params_buffer`. `visual_chain.compute_param_deltas()` emits `{node_id}.{param_name}` → `uniforms.json` → `dynamic_pipeline.rs` walks `pass.param_order` positionally."

The `visual-chain-state.json` snapshot shows 15 param deltas being emitted, all for recognized WGSL node parameters (noise, post, rd, fb, drift, color). Path 2 is alive; path 1 flows through `current.json` (separate file, not inspected here).

**No drift on the visual chain side.** The aggregator is correctly computing + publishing parameter deltas to feed the GPU.

## 7. Recommendations / follow-ups

### 7.1 Docstring fix — queue #250

```yaml
id: "250"
title: "Fix shared/stimmung.py docstring dimension count (10 → 11)"
assigned_to: beta
status: offered
depends_on: []
priority: low
description: |
  Queue #236 found two docstrings in shared/stimmung.py that state
  "10 dimensions" when the SystemStimmung class has 11 fields
  (exploration_deficit added, docstring never updated).
  
  Fix:
  - Line 9-12 module docstring: "10 dimensions (6 infrastructure +
    1 cognitive + 3 biometric)" → "11 dimensions (6 infrastructure +
    2 cognitive + 3 biometric)"
  - Line 56 class docstring: "10 dimensions + derived stance" →
    "11 dimensions + derived stance"
  
  Comment-only drift; zero behavior change.
size_estimate: "~2 min"
```

### 7.2 Stale-dimension follow-up — queue #251

```yaml
id: "251"
title: "Investigate resource_pressure + grounding_quality 121s staleness"
assigned_to: beta
status: offered
depends_on: []
priority: low
description: |
  Queue #236 found resource_pressure and grounding_quality dimensions
  at exactly 121s freshness — just past the 120s _STALE_THRESHOLD_S.
  Both collectors appear to be ticking roughly every 2 minutes, at the
  edge of the "fresh" window.
  
  Investigate:
  1. Which collectors feed these two dimensions?
  2. Is the ~2-min cadence intentional or accidental?
  3. If accidental (cadence regression), fix to <60s
  4. If intentional, either raise _STALE_THRESHOLD_S or document the
     expected cadence in shared/stimmung.py
size_estimate: "~30 min"
```

### 7.3 Cross-reference with proposed #242 (from queue #233)

Queue #233 §7.3 proposed a generic "chronic_error stagnation alert" for `/dev/shm/hapax-exploration/*.json`. This drop corroborates the need with a THIRD silent-failure surface:

- Queue #220: watch HR stale 9 days, no alert
- Queue #233: contact mic null audio 98+ min, no alert
- Queue #236 (this): perception_confidence = 0.037, overall_stance = cautious for some unknown duration, no alert

**Extend proposed #242 to cover stimmung dimensions** in addition to exploration components:

- Monitor `/dev/shm/hapax-stimmung/state.json` for `overall_stance != nominal` lasting >60s
- Monitor individual dimensions for `value > 0.3 AND freshness_s < _STALE_THRESHOLD_S` persisting >60s
- Push ntfy + log warning + emit Prometheus counter

## 8. Non-drift observations

- **The aggregator is doing its job correctly.** VLA is live, writing fresh data every 1-2 seconds, correctly detecting the degraded state, correctly transitioning the stance out of nominal. The pipeline itself is not drifted.
- **The silent-failure theme is now cross-referenced in FOUR queue items** (#220, #230, #233, #236). Every audit in this session that touches presence-adjacent state has surfaced the same pattern: signals are degraded, the system is DETECTING the degradation internally, but no operator notification fires.
- **exploration_deficit = 0.546** is above the 0.35 SEEKING threshold per CLAUDE.md § Unified Semantic Recruitment. This should drive the reverie mixer to halve the recruitment threshold for dormant capabilities. Not verified in this audit — out of scope — but a testable prediction.
- **No test exists for `_compute_aggregate_confidence()`** that I could find in a quick grep. The 0.037 value I'm reading could be a bug in the counter rather than a true reflection of available backends. A unit test that mocks `perception.registered_backends` with N available + M unavailable and asserts the ratio would catch accidental denominator errors. Proposed as part of queue #247's "untested backends" epic.
- **CLAUDE.md mentions "perception → Stimmung → /dev/shm" in the Shared Infrastructure section.** That claim is accurate. The pipeline is exactly as documented.

## 9. Cross-references

- Queue spec: `queue/236-beta-stimmung-aggregate-signal-drift.yaml`
- Aggregator source: `agents/visual_layer_aggregator/aggregator.py`
- Stimmung model: `shared/stimmung.py` (SystemStimmung, StimmungCollector, 11 dimensions + Stance)
- Perception writer: `agents/hapax_daimonion/_perception_state_writer.py::_compute_aggregate_confidence`
- CLAUDE.md § Shared Infrastructure — VLA pipeline claim
- Queue #220 watch HR stale: `docs/research/2026-04-15-presence-engine-lr-tuning-live-data.md` (commit `a5349edd8`) — sibling silent failure
- Queue #230 voice FX chain + Studio 24c absent: `docs/research/2026-04-15-voice-fx-chain-pipewire-verification.md` (commit `e82c32840`)
- Queue #233 contact mic DSP drift: `docs/research/2026-04-15-contact-mic-dsp-drift-check.md` (commit `9cf6c388e`) — proposed #242 covers the alert layer
- Queue #224 PresenceEngine Prometheus (commit `954494ea5`) — precedent for adding stimmung metrics to the scrape
- Queue #234 backends test coverage (commit `55f18815d`) — notes the absence of `_compute_aggregate_confidence` unit tests

— beta, 2026-04-15T21:35Z (identity: `hapax-whoami` → `beta`)
