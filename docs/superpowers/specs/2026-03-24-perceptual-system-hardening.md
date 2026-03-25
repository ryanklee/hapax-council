# Perceptual System Hardening

**Date:** 2026-03-24
**Scope:** Correctness, consistency, and robustness fixes across the perception–stimmung–apperception–visual-layer–GQI stack.
**Baseline:** 239 tests passing across 5 test files.

---

## 1. Problem Statement

A full review of the perceptual system identified 20 findings across 6 subsystems. After research verification, 17 are confirmed real (1 withdrawn as not-a-bug, 2 reclassified). This document specifies the fix for each, grouped into implementation batches ordered by dependency and blast radius.

---

## 2. Verified Findings

### 2.1 Critical — Produce Wrong Results Silently

| ID | Subsystem | Summary |
|----|-----------|---------|
| C1 | stimmung | Biometric/cognitive dims structurally cannot reach DEGRADED/CRITICAL stance |
| C2 | aggregator | WS3 stores permanently disabled after single Qdrant failure |
| C3 | perception_ring | `trend()` catastrophic cancellation with POSIX timestamps |
| C4 | apperception | Depth-4 retention gate drops ~95% of events |
| C5 | apperception | Rumination breaker records fixed sentinel (-0.1) instead of actual valence |
| C6 | apperception_tick | TEMPORAL_FILE read twice per tick — contradictory events possible |

### 2.2 High — Correctness Issues with Practical Impact

| ID | Subsystem | Summary |
|----|-----------|---------|
| H1 | state_writer | Uncaught `int()` cast failure skips atomic write; consumers see stale state |
| H2 | perception | `replace_backend` orphans behaviors if new backend unavailable |
| H4 | state_writer | Module-level `_supplementary_content` list not thread-safe |
| H5 | primitives | `Event[T].emit()` iterates live subscriber list; self-unsubscribe skips callbacks |
| H6 | aggregator | `readiness = "collecting"` is dead code (`_last_ambient_fetch` init to -300, checked == 0) |
| H7 | grounding_ledger | IGNORE branch `acceptance_score >= threshold` near-dead code |

### 2.3 Moderate — Design Issues and Latent Risks

| ID | Subsystem | Summary |
|----|-----------|---------|
| M1 | aggregator | Cross-file `/dev/shm` timestamp inconsistency (stimmung 15s vs state 3s) |
| M2 | aggregator | `_infer_activity()` re-reads perception file from disk, ignoring cache |
| M3 | phenomenal_context | Module-level temporal cache shared across async render calls |
| M4 | visual_layer_state | De-escalation timer reset on same-state ticks |
| M5 | grounding_ledger | Effort hysteresis counter wrongly reset on same-rank turns |

### 2.4 Withdrawn

| ID | Original Summary | Reason |
|----|-----------------|--------|
| H3 | circadian_alignment semantics inverted | NOT A BUG — backend produces 0.1=peak, 0.8=worst, correctly used as pressure |

### 2.5 New Findings from Research

| ID | Subsystem | Summary |
|----|-----------|---------|
| N1 | state_writer | `circadian_alignment` never written to perception-state.json — aggregator always gets default 0.5 |
| N2 | stimmung | `SystemStimmung.timestamp` uses `time.monotonic()` but is serialized to JSON; latent cross-process time comparison bomb |
| N3 | perception | `_bval` typed as `-> float` but called with str/bool/None defaults; maintenance trap |
| M6 | visual_layer_state | PERFORMATIVE has no exit hysteresis — single-tick CRITICAL yanks out of live performance |

---

## 3. Design

### 3.1 C1 — Separate Stance Thresholds per Dimension Class

**Intent:** Biometrics nudge, never dominate. The weights are correct; the thresholds need to account for the weighting.

**Current behavior:** Biometric dim at raw 1.0 → effective 0.5 → max CAUTIOUS. Cognitive dim at raw 1.0 → effective 0.3 → barely CAUTIOUS.

**Fix:** Keep the existing approach (multiply values by weight, compare against thresholds), but use separate threshold sets per dimension class that account for the weight compression. The intent "nudge but never dominate" means: biometrics at max severity should reach DEGRADED but not CRITICAL. Cognitive at max severity should reach CAUTIOUS but not DEGRADED.

**Threshold design (effective values, i.e., after weight multiplication):**

```python
# Infrastructure: standard thresholds on effective (= raw × 1.0)
_INFRA_THRESHOLDS = (0.30, 0.60, 0.85)

# Biometric: can reach DEGRADED at raw=1.0 (effective=0.5), never CRITICAL
# CAUTIOUS at effective 0.15, DEGRADED at effective 0.40
_BIOMETRIC_THRESHOLDS = (0.15, 0.40, 1.01)  # 1.01 = unreachable

# Cognitive: can reach CAUTIOUS at raw≥0.5 (effective=0.15), never DEGRADED
_COGNITIVE_THRESHOLDS = (0.15, 1.01, 1.01)
```

This gives:
- Biometric dim at raw 0.3 → effective 0.15 → CAUTIOUS ✓
- Biometric dim at raw 0.8 → effective 0.40 → DEGRADED ✓
- Biometric dim at raw 1.0 → effective 0.50 → DEGRADED (not CRITICAL) ✓
- Cognitive dim at raw 0.5 → effective 0.15 → CAUTIOUS ✓
- Cognitive dim at raw 1.0 → effective 0.30 → CAUTIOUS (not DEGRADED) ✓

**Implementation:** Replace `_compute_stance` with a version that looks up thresholds by dimension class.

**Blast radius:** All stance consumers (apperception cascade, phenomenal context, model routing, stimmung_sync) will see biometric-driven DEGRADED for the first time. The DEGRADED behaviors (reflection dampened 2x, voice brevity prompt, model downgrade if resource > 0.7) are proportional responses to high operator stress.

**Test additions:** Property test that biometric dims can reach DEGRADED but not CRITICAL. Cognitive dims can reach CAUTIOUS but not DEGRADED. Infrastructure dims can reach all levels.

---

### 3.2 C2 — WS3 Lazy-Init with Retry

**Problem:** `_ws3_initialized = True` set before connection attempt. No retry on failure.

**Fix:** Move the flag to after success. Add bounded retry: attempt re-init every 60s, max 5 attempts.

```python
_WS3_RETRY_INTERVAL_S = 60.0
_WS3_MAX_RETRIES = 5

def _init_ws3(self) -> None:
    if self._ws3_initialized:
        return
    if self._ws3_retries >= _WS3_MAX_RETRIES:
        return
    now = time.monotonic()
    if now - self._ws3_last_attempt < _WS3_RETRY_INTERVAL_S:
        return
    self._ws3_last_attempt = now
    self._ws3_retries += 1
    try:
        self._correction_store = CorrectionStore()
        self._correction_store.ensure_collection()
        self._episode_store = EpisodeStore()
        self._episode_store.ensure_collection()
        self._ws3_initialized = True  # only on success
    except Exception:
        log.warning("WS3 stores unavailable (attempt %d/%d)",
                    self._ws3_retries, _WS3_MAX_RETRIES)
        self._correction_store = None
        self._episode_store = None
    # PatternStore separately (same pattern)
    ...
```

**New init attributes:** `_ws3_retries: int = 0`, `_ws3_last_attempt: float = 0.0`.

---

### 3.3 C3 — Center Timestamps in `trend()` Regression

**Problem:** Raw POSIX timestamps (~1.7e9) cause catastrophic cancellation in the least-squares denominator.

**Fix:** Center timestamps by subtracting the mean before regression. Algebraically identical, numerically stable.

```python
def trend(self, key: str, window_s: float = 15.0) -> float:
    ...
    n = len(values)
    ts = [t for t, _ in values]
    vs = [v for _, v in values]
    t_mean = sum(ts) / n

    # Center timestamps to avoid catastrophic cancellation
    centered = [t - t_mean for t in ts]
    sum_ct = sum(centered)  # should be ~0
    sum_cv = sum(c * v for c, v in zip(centered, vs))
    sum_cc = sum(c * c for c in centered)

    denom = n * sum_cc - sum_ct * sum_ct
    if abs(denom) < 1e-12:
        return 0.0
    return (n * sum_cv - sum_ct * sum(vs)) / denom
```

**Test addition:** Property test with realistic POSIX timestamps verifying slope matches expected direction and magnitude.

---

### 3.4 C4 — Relax Retention Gate for High-Signal Events

**Problem:** `_step_retention` requires `cascade_depth >= 5` (needs action or reflection), dropping ~95% of events including those with high relevance or strong valence.

**Design intent (preserved):** The cascade should not retain noise. But events with significant relevance OR strong valence should not require an action or reflection to be retained.

**Fix:** Add an escape hatch for high-signal events at depth 4:

```python
def _step_retention(self, cascade_depth, relevance, valence, reflection, source):
    if source == "correction":
        return True
    if cascade_depth >= 5:
        return relevance > 0.3 or abs(valence) > 0.2 or bool(reflection)
    # Depth 4: retain only high-signal events (strong relevance AND valence)
    if cascade_depth == 4:
        return relevance > 0.5 and abs(valence) > 0.3
    return False
```

This retains depth-4 events only when BOTH relevance is high (> 0.5) AND valence is meaningful (|v| > 0.3). This is a tighter gate than depth-5 (which needs only one of relevance/valence/reflection), preserving the noise-filtering intent while allowing significant events through.

**Test addition:** Explicit test for depth-4 high-signal retention. Test for depth-4 low-signal filtering.

---

### 3.5 C5 — Record Actual Valence in Rumination Breaker

**Problem:** For `likely_negative` sources, `_check_rumination` is called with a fixed `-0.1` sentinel before actual valence is computed.

**Fix:** Restructure to compute valence first, then check rumination with the real value. The rumination check was placed before valence computation to short-circuit expensive work, but `_step_valence` is a pure lookup (not expensive).

```python
# Step 4: Valence (compute BEFORE rumination check)
valence = self._step_valence(event)

# Rumination check — single call for ALL sources with actual valence.
# This replaces the two-call pattern (gate for likely_negative, record for others).
# Both gating and recording now happen in one call with the real valence.
if self._check_rumination(target, valence):
    return None
```

This removes the `likely_negative` guard entirely — all sources get both rumination tracking AND gating with their real valence. The rumination gate still only fires on 5 consecutive negatives, regardless of source.

**Behavior change:** Previously, non-`likely_negative` sources (e.g., `pattern_shift`, `cross_resonance`) were tracked but never gated — `_check_rumination` was called for recording only, with its return value discarded. Now all sources are subject to the 5-consecutive-negative gate. This is the correct behavior: a dimension receiving 5 consecutive negative signals from ANY source type indicates rumination that should be dampened.

**Test addition:** Test that rumination gate uses real valence, not a sentinel. Test that a positive-valence event from a `prediction_error` source does NOT count as negative in rumination history.

---

### 3.6 C6 — Read TEMPORAL_FILE Once per Tick

**Problem:** `_collect_events` in `apperception_tick.py` reads `bands.json` twice (once for surprise, once for staleness), allowing contradictory events.

**Fix:** Read once at the top of `_collect_events`, pass the parsed dict to both collectors.

```python
def _collect_events(self) -> list[CascadeEvent]:
    events: list[CascadeEvent] = []
    now = time.time()

    # Read temporal file once
    temporal_data = self._read_file(TEMPORAL_FILE)

    # Collector 1: temporal surprise
    if temporal_data is not None:
        ts = temporal_data.get("timestamp", 0)
        if (now - ts) <= 30:
            surprise = temporal_data.get("max_surprise", 0.0)
            if surprise > 0.3:
                events.append(CascadeEvent(source="prediction_error", ...))

    # ... other collectors ...

    # Collector 4: staleness (reuse temporal_data)
    if temporal_data is not None:
        perception_age = now - temporal_data.get("timestamp", 0)
        if perception_age > 30.0:
            events.append(CascadeEvent(source="absence", ...))

    return events
```

**Note:** With a single read, the surprise and staleness checks on the same data are now mutually exclusive by construction (age ≤ 30 XOR age > 30), which is the correct invariant.

---

### 3.7 H1 — Wrap State-Building in Try/Except

**Problem:** A non-numeric behavior value in `heart_rate_bpm` or `phone_battery_pct` raises `ValueError` from `int()` cast, skipping the entire atomic write.

**Fix:** Wrap individual field extractions with safe defaults, and add an outer guard on the full state dict construction.

```python
def _safe_int(val: object, default: int = 0) -> int:
    try:
        return int(float(val) if val is not None else default)
    except (ValueError, TypeError):
        return default

def _safe_float(val: object, default: float = 0.0) -> float:
    try:
        return float(val) if val is not None else default
    except (ValueError, TypeError):
        return default
```

Replace all `int(_bval(...))` with `_safe_int(_bval(...))` and all `float(_bval(...))` with `_safe_float(_bval(...))`.

Add an outer try/except around the state dict construction that logs and writes a minimal valid state on failure (timestamp + error flag), so consumers never see indefinitely stale data.

---

### 3.8 H2 — Check Availability Before Stopping Old Backend

**Problem:** `replace_backend` stops the old backend before checking if the new one is available. If new backend is unavailable, behaviors are orphaned.

**Fix:** Check first, swap second.

```python
def replace_backend(self, backend: PerceptionBackend) -> None:
    if not backend.available():
        log.warning("Replacement backend %s unavailable, keeping current", backend.name)
        return
    old = self._backends.pop(backend.name, None)
    if old is not None:
        old.stop()
        for name in old.provides:
            self._provided_by.pop(name, None)
    self.register_backend(backend)
```

---

### 3.9 H4 — Thread-Safe Supplementary Content

**Problem:** Module-level `_supplementary_content` list mutated from multiple threads.

**Fix:** Replace with `collections.deque(maxlen=5)` which has atomic append under CPython's GIL. Replace slice assignment with `deque.clear()` + extend pattern.

```python
_supplementary_content: deque[dict] = deque(maxlen=5)

def push_supplementary_content(item: dict) -> None:
    _supplementary_content.append(item)

def _get_live_content() -> list[dict]:
    now = time.time()
    # Filter expired items atomically by rebuilding
    live = [c for c in _supplementary_content if now - c.get("ts", 0) < c.get("ttl", 300)]
    return live  # Don't mutate the deque; let maxlen handle eviction
```

---

### 3.10 H5 — Snapshot Subscriber List in `emit()`

**Problem:** Self-unsubscribe during `emit()` mutates the list mid-iteration.

**Fix:** Iterate a snapshot.

```python
def emit(self, timestamp: float, value: T) -> None:
    for cb in list(self._subscribers):
        cb(timestamp, value)
```

---

### 3.11 H6 — Fix Readiness State Logic

**Problem:** `_last_ambient_fetch` initialized to `-300.0` but checked against `== 0.0`. The `"collecting"` state is dead code.

**Fix:** Use a boolean flag for clarity.

```python
self._ambient_fetch_done: bool = False

# In readiness check:
if self._last_perception_data is None:
    state.readiness = "waiting"
elif not self._ambient_fetch_done:
    state.readiness = "collecting"
else:
    state.readiness = "ready"

# Set flag after first successful fetch:
def poll_ambient_content(self):
    ...
    self._ambient_fetch_done = True
```

---

### 3.12 H7 — Simplify IGNORE Branch in Grounding Ledger

**Problem:** IGNORE acceptance_score (fixed 0.3) compared against threshold (minimum 0.3) — condition is near-dead code.

**Fix:** Remove the meaningless threshold comparison. IGNORE grounding depends only on concern overlap.

```python
# In update_from_acceptance, IGNORE case:
if acceptance == "IGNORE":
    if concern_overlap < 0.3:
        du.state = DUState.GROUNDED  # low-concern, ignore is fine
        return "advance"
    du.state = DUState.UNGROUNDED
    return "ungrounded_caution"
```

---

### 3.13 M1 — Add Epoch Counter to `/dev/shm` Files

**Problem:** Stimmung (15s) and visual state (3s) have different write cadences; consumers reading both see inconsistent timestamps.

**Fix:** Add a monotonic `epoch` field to each `/dev/shm` JSON file, set from a shared counter in the aggregator. Consumers can detect cross-file staleness by comparing epochs. This is informational — no behavior change, but enables future consistency checks.

```python
# In aggregator:
self._epoch: int = 0

# On each state tick:
self._epoch += 1
state_payload["epoch"] = self._epoch
# Stimmung gets the epoch at write time too
stimmung_payload["epoch"] = self._epoch
```

---

### 3.14 M2 — Use Cached Perception Data in `_infer_activity()`

**Problem:** `_infer_activity()` re-reads `perception-state.json` from disk, ignoring `self._last_perception_data`.

**Fix:** Pass `self._last_perception_data` as a parameter.

```python
def _infer_activity(self, perception_data: dict | None = None) -> str:
    data = perception_data or self._last_perception_data or {}
    ...
```

Update both call sites in `_run_scheduler()` and `compute_and_write()`.

---

### 3.15 M3 — Snapshot Isolation for Phenomenal Context Render

**Problem:** Module-level temporal cache shared across async renders; layers read different files at different times.

**Fix:** Read all three sources (stimmung, temporal, apperception) at the start of `render()`, pass the snapshot dict into each `_render_*` function.

```python
def render(tier: str = "CAPABLE") -> str:
    # Snapshot all sources once
    stimmung = _read_json(STIMMUNG_FILE)
    temporal = _read_json(TEMPORAL_FILE)
    apperception = _read_json(APPERCEPTION_FILE)

    lines = []
    if s := _render_stimmung(stimmung):
        lines.append(s)
    ...
```

Remove module-level cache globals.

---

### 3.16 M4 — Fix De-escalation Timer for Same-State Ticks

**Problem:** Targeting the current state resets `_deescalation_timer`, preventing cooldown from ever elapsing.

**Fix:** Only reset the timer on escalation, not on same-state ticks.

```python
def _apply_transition(self, target: DisplayState, now: float) -> DisplayState:
    if target == self.state:
        # Same state — do NOT reset de-escalation timer
        return self.state
    ...
```

The timer should only be set when the state actually changes (either escalation or de-escalation).

---

### 3.17 M5 — Preserve Effort Hold Counter on Same-Rank Turns

**Problem:** `_effort_hold_turns` reset to 0 when effort level stays the same, preventing de-escalation.

**Fix:** Only reset on escalation. Same-rank preserves the counter.

```python
if new_rank > current_rank:
    # Escalation: immediate, reset hold
    self._effort_hold_turns = 0
    return new_effort
elif new_rank < current_rank:
    # De-escalation: require 2 consecutive lower turns
    self._effort_hold_turns += 1
    if self._effort_hold_turns >= 2:
        self._effort_hold_turns = 0
        return new_effort
    return current_effort  # hold
else:
    # Same rank: no change, preserve hold counter
    return current_effort
```

---

### 3.18 M6 — PERFORMATIVE Exit Hysteresis

**Problem:** Single-tick CRITICAL signal yanks out of PERFORMATIVE with full cooldown needed to return.

**Fix:** Add a 3-second cooldown before exiting PERFORMATIVE. Only ALERT state (triggered by CRITICAL severity signals) can break through.

```python
_PERFORMATIVE_EXIT_COOLDOWN_S = 3.0

if self.state == DisplayState.PERFORMATIVE:
    if target == DisplayState.ALERT:
        # Critical signal: exit with brief cooldown
        if now - self._performative_enter_time >= _PERFORMATIVE_EXIT_COOLDOWN_S:
            return target
        return self.state  # hold performative briefly
    if target == DisplayState.PERFORMATIVE:
        return self.state
    # Non-critical de-escalation: immediate (flow ended)
    return target
```

---

### 3.19 N1 — Write `circadian_alignment` to Perception State

**Problem:** Circadian backend produces the value but it's never serialized. Aggregator always uses 0.5.

**Fix:** Add `circadian_alignment` to the state dict in `write_perception_state()`.

```python
# In _perception_state_writer.py, state dict:
"circadian_alignment": _safe_float(_bval("circadian_alignment", 0.5)),
```

---

### 3.20 N2 — Use Wall-Clock Time for Stimmung Timestamp

**Problem:** `SystemStimmung.timestamp` set from `time.monotonic()`, serialized to JSON. Latent cross-process comparison bomb.

**Fix:** Use `time.time()` for the serialized timestamp field. Keep `time.monotonic()` for internal freshness calculations (the `_record` and `snapshot` methods).

```python
def snapshot(self) -> SystemStimmung:
    now = time.monotonic()
    ...
    return SystemStimmung(
        **dimensions,
        overall_stance=stance,
        timestamp=time.time(),  # wall-clock for serialization
    )
```

Internal freshness tracking (`_last_update` dict) continues to use `time.monotonic()`.

---

### 3.21 N3 — Type-Safe Behavior Value Access

**Problem:** `_bval` in `perception.py` typed as `-> float` but called with str/bool/None defaults.

**Fix:** Split into typed accessors.

```python
def _fval(self, name: str, default: float = 0.0) -> float:
    """Read a float Behavior value."""
    b = self.behaviors.get(name)
    return float(b.value) if b is not None else default

def _sval(self, name: str, default: str = "") -> str:
    """Read a string Behavior value."""
    b = self.behaviors.get(name)
    return str(b.value) if b is not None else default

def _boolval(self, name: str, default: bool = False) -> bool:
    """Read a boolean Behavior value."""
    b = self.behaviors.get(name)
    return bool(b.value) if b is not None else default

def _optval(self, name: str) -> object | None:
    """Read an optional Behavior value (may be None)."""
    b = self.behaviors.get(name)
    return b.value if b is not None else None
```

---

## 4. Implementation Batches

### Batch 1: Pure Functions (no state, no I/O)

Zero blast radius — only changes internal computation. Tests can be written and run in isolation.

| Fix | File | Risk |
|-----|------|------|
| C3 | `perception_ring.py` | Numerical only, no API change |
| H5 | `primitives.py` | One-line change |
| H7 | `grounding_ledger.py` | Simplify dead branch |
| M5 | `grounding_ledger.py` | Fix hold counter logic |
| N3 | `perception.py` | Type safety, no behavior change |

### Batch 2: Safety and Robustness (error handling, thread safety)

Guards against failure modes. No behavior change under normal operation.

| Fix | File | Risk |
|-----|------|------|
| H1 | `_perception_state_writer.py` | Add safe casts + fallback write |
| H2 | `perception.py` | Reorder check in `replace_backend` |
| H4 | `_perception_state_writer.py` | `deque` instead of list |
| C2 | `visual_layer_aggregator.py` | Add WS3 retry (new attributes) |
| N1 | `_perception_state_writer.py` | Add one field to state dict |
| N2 | `stimmung.py` | `time.time()` for serialized timestamp |

### Batch 3: Apperception Cascade (interconnected changes)

These three fixes interact — C5 (real valence in rumination) must land before C4 (relaxed retention gate) because C4's new depth-4 branch retains events based on `abs(valence) > 0.3`. If C5 hasn't landed, the rumination breaker's `-0.1` sentinel could poison valence-based retention decisions. C6 is independent but in the same subsystem.

| Fix | File | Risk |
|-----|------|------|
| C5 | `apperception.py` | Restructure valence/rumination order |
| C4 | `apperception.py` | Relax retention gate |
| C6 | `apperception_tick.py` | Read temporal file once |

### Batch 4: State Machine and Display (visual behavior changes)

Observable behavior changes — test with visual inspection.

| Fix | File | Risk |
|-----|------|------|
| M4 | `visual_layer_state.py` | Fix de-escalation timer |
| M6 | `visual_layer_state.py` | PERFORMATIVE exit hysteresis |
| H6 | `visual_layer_aggregator.py` | Fix readiness state |
| M2 | `visual_layer_aggregator.py` | Use cached perception data |
| M1 | `visual_layer_aggregator.py` | Add epoch counter |

### Batch 5: Stimmung Thresholds (highest blast radius)

Most impactful change — biometric dims will reach DEGRADED for the first time. Deploy last so all other fixes are stable.

| Fix | File | Risk |
|-----|------|------|
| C1 | `stimmung.py` | New threshold computation — affects all stance consumers |

### Batch 6: Context Rendering (voice pipeline)

Isolated to voice context. Low blast radius but changes LLM prompt content.

| Fix | File | Risk |
|-----|------|------|
| M3 | `phenomenal_context.py` | Snapshot isolation for render |

---

## 5. Testing Strategy

### New Tests per Batch

**Batch 1:**
- `test_perception_ring.py`: Property test — `trend()` with POSIX timestamps produces bounded, correct slopes
- `test_perception_ring.py`: Regression test — 20 points at t≈1.7e9 with known linear trend
- `test_primitives.py`: `Event[T].emit()` with self-unsubscribing callback does not skip subsequent subscribers
- `test_grounding_ledger.py`: IGNORE branch simplified — verify low-concern IGNORE grounds, high-concern ungrounds
- `test_grounding_ledger.py`: Effort hold counter preserved on same-rank turns
- `test_perception.py`: `_fval`/`_sval`/`_boolval`/`_optval` return correct types and defaults

**Batch 2:**
- `test_perception_state_writer.py`: `_safe_int`/`_safe_float` handle None, "unknown", NaN
- `test_perception_state_writer.py`: Outer try/except writes minimal valid state on construction failure
- `test_perception_state_writer.py`: `circadian_alignment` appears in written state dict
- `test_perception_state_writer.py`: Thread-safe deque — concurrent append does not corrupt
- `test_perception.py`: `replace_backend` with unavailable new backend keeps old
- `test_visual_layer_aggregator.py`: WS3 retry — fails first attempt, succeeds second
- `test_stimmung.py`: Serialized stimmung timestamp is wall-clock (within 1s of `time.time()`)

**Batch 3:**
- `test_apperception.py`: Rumination uses actual valence, not sentinel
- `test_apperception.py`: Depth-4 high-signal events retained (relevance > 0.5 AND |valence| > 0.3)
- `test_apperception.py`: Depth-4 low-signal events still filtered
- `test_apperception_events.py`: Single temporal file read — no contradictory surprise+absence

**Batch 4:**
- `test_visual_layer_state.py`: Same-state tick does NOT reset de-escalation timer
- `test_visual_layer_state.py`: PERFORMATIVE holds for 3s against ALERT-triggering signals
- `test_visual_layer_state.py`: ALERT breaks through PERFORMATIVE after 3s cooldown
- `test_visual_layer_aggregator.py`: Readiness transitions waiting → collecting → ready
- `test_visual_layer_aggregator.py`: `_infer_activity()` uses cached data, not fresh disk read
- `test_visual_layer_aggregator.py`: Epoch counter monotonically increases across ticks

**Batch 5:**
- `test_stimmung.py`: Biometric dim at raw 1.0 → DEGRADED (not CAUTIOUS)
- `test_stimmung.py`: Biometric dim at raw 1.0 → NOT CRITICAL
- `test_stimmung.py`: Cognitive dim at raw 1.0 → CAUTIOUS (not DEGRADED)
- `test_stimmung.py`: Infrastructure thresholds unchanged

**Batch 6:**
- `test_phenomenal_context.py`: Render reads all files once at start, not per-layer

### Regression Gate

All 239 existing tests must pass after each batch. Run full suite between batches.

---

## 6. Rollback

Each batch is an independent commit. If a batch causes issues, revert the single commit. Batch ordering ensures earlier batches are stable before later ones land.

---

## 7. Out of Scope

- Known wiring gaps (GQI → stimmung, watch → stimmung end-to-end, voice → scheduler pause) — tracked separately in the data audit.
- `Behavior[T]` equal-timestamp semantics (M7 from original review) — documented behavior, not a bug.
- Display state machine PERFORMATIVE instant entry (intentional — entering performance mode should be immediate).
