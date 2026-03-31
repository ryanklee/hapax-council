# IR Batch 3: Integration Wiring — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete the integration wiring between IR perception signals and their designed consumers: stimmung perception_confidence floor, 5 missing perception-state signals, ir_hand_zone signal, and contact mic cross-modal fusion.

**Architecture:** Council-side changes only. No Pi changes. Extends existing ir_presence backend with 1 new signal (ir_hand_zone), adds 5 missing signals to perception state writer, enriches stimmung, and adds IR cross-reference to contact mic activity classification.

**Tech Stack:** Python 3.12, pydantic-ai primitives (Behavior), unittest.mock

**Spec:** `docs/superpowers/specs/2026-03-31-ir-perception-remediation-design.md` §Batch 3

**Depends on:** Batch 1 (signal quality) and Batch 2 (person detection) delivering clean signals.

---

### Task 1: Add ir_hand_zone signal to backend

**Files:**
- Modify: `agents/hapax_daimonion/backends/ir_presence.py`
- Test: `tests/hapax_daimonion/test_ir_presence_backend.py`

- [ ] **Step 1: Write test for ir_hand_zone**

Add to `tests/hapax_daimonion/test_ir_presence_backend.py`:

```python
def test_hand_zone_from_overhead(tmp_path):
    _write_report(
        tmp_path,
        "overhead",
        hands=[{"zone": "mpc-pads", "bbox": [200, 300, 350, 420], "activity": "tapping"}],
    )
    backend = IrPresenceBackend(state_dir=tmp_path)
    behaviors: dict[str, Behavior] = {}
    backend.contribute(behaviors)
    assert behaviors["ir_hand_zone"].value == "mpc-pads"


def test_hand_zone_empty_when_no_hands(tmp_path):
    _write_report(tmp_path, "desk")
    backend = IrPresenceBackend(state_dir=tmp_path)
    behaviors: dict[str, Behavior] = {}
    backend.contribute(behaviors)
    assert behaviors["ir_hand_zone"].value == "none"
```

- [ ] **Step 2: Run test — expect FAIL**

```bash
uv run pytest tests/hapax_daimonion/test_ir_presence_backend.py::test_hand_zone_from_overhead -v
```

Expected: FAIL with `KeyError: 'ir_hand_zone'`

- [ ] **Step 3: Add ir_hand_zone to backend**

In `ir_presence.py`, add `"ir_hand_zone"` to `_SIGNALS` frozenset.

In `IrPresenceBackend.__init__`, add:

```python
            "ir_hand_zone": Behavior("none"),
```

In `_fuse`, in the no-reports early return, add:

```python
            self._behaviors["ir_hand_zone"].update("none", now)
```

After the hand activity line `self._behaviors["ir_hand_activity"].update(hand_activity, now)`, add:

```python
        hand_zone = self._pick_hand_zone(reports)
        self._behaviors["ir_hand_zone"].update(hand_zone, now)
```

Add the `_pick_hand_zone` method (mirrors `_pick_hand_activity` logic):

```python
    def _pick_hand_zone(self, reports: dict[str, dict[str, object]]) -> str:
        """Pick hand zone, preferring overhead Pi."""
        if "overhead" in reports:
            overhead = reports["overhead"]
            hands = list(overhead.get("hands", [])) if isinstance(overhead, dict) else []
            if hands and isinstance(hands[0], dict):
                return str(hands[0].get("zone", "none"))

        for report in reports.values():
            hands = list(report.get("hands", [])) if isinstance(report, dict) else []
            if hands and isinstance(hands[0], dict):
                return str(hands[0].get("zone", "none"))

        return "none"
```

- [ ] **Step 4: Update protocol test for signal count**

In `test_backend_protocol()`, change:

```python
    assert len(backend.provides) == 14
```

- [ ] **Step 5: Run all backend tests**

```bash
uv run pytest tests/hapax_daimonion/test_ir_presence_backend.py -v
```

Expected: all 9 tests pass (7 existing + 2 new).

- [ ] **Step 6: Commit**

```bash
git add agents/hapax_daimonion/backends/ir_presence.py tests/hapax_daimonion/test_ir_presence_backend.py
git commit -m "feat(ir): add ir_hand_zone signal to IR presence backend

New signal #14: reports the zone name (mpc-pads, turntable, desk-center,
synth-left) of the most prominent hand detection, preferring overhead Pi.
Enables contact mic cross-modal fusion."
```

---

### Task 2: Add 5 missing signals to perception state writer

**Files:**
- Modify: `agents/hapax_daimonion/_perception_state_writer.py`

- [ ] **Step 1: Add missing IR signals to perception state dict**

After the existing IR block (line 434, after `"ir_brightness"`), add:

```python
            "ir_person_count": _safe_int(_bval("ir_person_count", 0)),
            "ir_motion_delta": _safe_float(_bval("ir_motion_delta", 0.0)),
            "ir_head_pose_yaw": _safe_float(_bval("ir_head_pose_yaw", 0.0)),
            "ir_posture": str(_bval("ir_posture", "unknown")),
            "ir_heart_rate_conf": _safe_float(_bval("ir_heart_rate_conf", 0.0)),
            "ir_hand_zone": str(_bval("ir_hand_zone", "none")),
```

This adds the 5 signals identified in the audit plus the new `ir_hand_zone` from Task 1.

- [ ] **Step 2: Verify perception state writer still constructs**

The writer has no unit tests (it's integration code). Verify the service starts:

```bash
uv run python -c "from agents.hapax_daimonion._perception_state_writer import write_perception_state; print('import OK')"
```

Expected: `import OK`

- [ ] **Step 3: Commit**

```bash
git add agents/hapax_daimonion/_perception_state_writer.py
git commit -m "feat(ir): export 6 missing IR signals to perception-state.json

Adds ir_person_count, ir_motion_delta, ir_head_pose_yaw, ir_posture,
ir_heart_rate_conf, ir_hand_zone. All 14 IR backend signals now flow
to VLA/stimmung/profile consumers."
```

---

### Task 3: Stimmung perception_confidence floor from IR

**Files:**
- Modify: `agents/visual_layer_aggregator/stimmung_methods.py`

- [ ] **Step 1: Verify existing IR confidence logic**

The VLA already has IR confidence boosting at lines 72-75 (from the audit). Read the current code to confirm exact location and logic:

The block at lines 72-78 currently reads:

```python
    ir_detected = agg._last_perception_data.get("ir_person_detected", False)
    ir_hands = agg._last_perception_data.get("ir_hand_activity", "idle")
    if ir_detected or ir_hands not in ("idle", ""):
        confidence = max(float(confidence), 0.7)
```

This already implements the design spec's "perception_confidence floor" from IR. The audit found "Stimmung has zero IR signal references" — but this code IS the stimmung pathway (it calls `agg._stimmung_collector.update_perception()` on line 76-78).

- [ ] **Step 2: Verify this is working end-to-end**

No code change needed — the integration already exists. The audit missed it because the VLA code is the stimmung feeder, not the stimmung module itself.

Mark this as already implemented. No commit needed.

---

### Task 4: Contact mic cross-modal fusion with IR hand zone

**Files:**
- Modify: `agents/hapax_daimonion/backends/contact_mic.py`
- Test: `tests/hapax_daimonion/test_contact_mic_ir_fusion.py` (new)

- [ ] **Step 1: Write test for IR-enhanced activity classification**

Create `tests/hapax_daimonion/test_contact_mic_ir_fusion.py`:

```python
"""Test contact mic + IR hand zone cross-modal fusion."""

from agents.hapax_daimonion.backends.contact_mic import _classify_activity_with_ir


def test_tapping_plus_mpc_pads():
    result = _classify_activity_with_ir(
        energy=0.3, onset_rate=2.0, centroid=200.0, autocorr_peak=0.0,
        ir_hand_zone="mpc-pads", ir_hand_activity="tapping",
    )
    assert result == "pad-work"


def test_energy_plus_turntable():
    result = _classify_activity_with_ir(
        energy=0.2, onset_rate=0.5, centroid=100.0, autocorr_peak=0.5,
        ir_hand_zone="turntable", ir_hand_activity="sliding",
    )
    assert result == "scratching"


def test_typing_plus_desk_center():
    result = _classify_activity_with_ir(
        energy=0.2, onset_rate=1.2, centroid=300.0, autocorr_peak=0.0,
        ir_hand_zone="desk-center", ir_hand_activity="tapping",
    )
    assert result == "typing"


def test_no_ir_falls_back_to_base():
    result = _classify_activity_with_ir(
        energy=0.2, onset_rate=1.2, centroid=300.0, autocorr_peak=0.0,
        ir_hand_zone="none", ir_hand_activity="none",
    )
    assert result == "typing"


def test_idle_stays_idle():
    result = _classify_activity_with_ir(
        energy=0.05, onset_rate=0.0, centroid=0.0, autocorr_peak=0.0,
        ir_hand_zone="mpc-pads", ir_hand_activity="resting",
    )
    assert result == "idle"


def test_drumming_plus_mpc_pads():
    result = _classify_activity_with_ir(
        energy=0.5, onset_rate=2.5, centroid=140.0, autocorr_peak=0.0,
        ir_hand_zone="mpc-pads", ir_hand_activity="tapping",
    )
    assert result == "drumming"
```

- [ ] **Step 2: Run tests — expect FAIL**

```bash
uv run pytest tests/hapax_daimonion/test_contact_mic_ir_fusion.py -v
```

Expected: FAIL with `ImportError: cannot import name '_classify_activity_with_ir'`

- [ ] **Step 3: Add IR-enhanced activity classifier**

In `contact_mic.py`, add a new function after `_classify_activity`:

```python
def _classify_activity_with_ir(
    energy: float,
    onset_rate: float,
    centroid: float,
    autocorr_peak: float = 0.0,
    ir_hand_zone: str = "none",
    ir_hand_activity: str = "none",
) -> str:
    """Classify desk activity with IR hand zone disambiguation.

    Base classification from DSP metrics, then refine with IR context:
    - turntable zone + energy → scratching (camera is primary detector)
    - mpc-pads zone + tapping energy → pad-work
    - desk-center zone + typing rate → typing (high confidence)
    """
    base = _classify_activity(energy, onset_rate, centroid, autocorr_peak)

    if base == "idle":
        return "idle"

    if ir_hand_zone == "turntable" and ir_hand_activity in ("sliding", "tapping"):
        return "scratching"

    if ir_hand_zone == "mpc-pads" and base in ("tapping", "active"):
        return "pad-work"

    return base
```

- [ ] **Step 4: Run tests — expect PASS**

```bash
uv run pytest tests/hapax_daimonion/test_contact_mic_ir_fusion.py -v
```

Expected: all 6 tests pass.

- [ ] **Step 5: Wire IR signals into contribute()**

In `ContactMicBackend.contribute()`, read the IR hand signals from the shared behaviors dict and pass to the enhanced classifier. Replace the activity classification in the cache update.

The contact mic's `_capture_loop` runs in a daemon thread and cannot access the perception behaviors dict directly. Instead, add a thread-safe IR state cache that `contribute()` writes and `_capture_loop` reads.

Add to `_ContactMicCache`:

```python
        self._ir_hand_zone: str = "none"
        self._ir_hand_activity: str = "none"

    def update_ir(self, *, ir_hand_zone: str, ir_hand_activity: str) -> None:
        with self._lock:
            self._ir_hand_zone = ir_hand_zone
            self._ir_hand_activity = ir_hand_activity

    def read_ir(self) -> tuple[str, str]:
        with self._lock:
            return self._ir_hand_zone, self._ir_hand_activity
```

In `ContactMicBackend.contribute()`, after reading the cache, update the IR state:

```python
    def contribute(self, behaviors: dict[str, Behavior]) -> None:
        now = time.monotonic()
        data = self._cache.read()

        # Feed IR hand context into the cache for the capture loop
        ir_zone_b = behaviors.get("ir_hand_zone")
        ir_act_b = behaviors.get("ir_hand_activity")
        if ir_zone_b is not None and ir_act_b is not None:
            self._cache.update_ir(
                ir_hand_zone=str(ir_zone_b.value),
                ir_hand_activity=str(ir_act_b.value),
            )

        self._b_activity.update(data["desk_activity"], now)
        self._b_energy.update(float(data["desk_energy"]), now)
        self._b_onset_rate.update(float(data["desk_onset_rate"]), now)
        self._b_gesture.update(data["desk_tap_gesture"], now)
        self._b_spectral_centroid.update(float(data["desk_spectral_centroid"]), now)
        self._b_autocorr_peak.update(float(data["desk_autocorr_peak"]), now)

        behaviors["desk_activity"] = self._b_activity
        behaviors["desk_energy"] = self._b_energy
        behaviors["desk_onset_rate"] = self._b_onset_rate
        behaviors["desk_tap_gesture"] = self._b_gesture
        behaviors["desk_spectral_centroid"] = self._b_spectral_centroid
        behaviors["desk_autocorr_peak"] = self._b_autocorr_peak
```

In `_capture_loop`, replace the activity classification line:

```python
                    # Activity classification (with IR cross-modal fusion)
                    ir_zone, ir_act = self._cache.read_ir()
                    activity = _classify_activity_with_ir(
                        smoothed_energy, onset_rate, centroid, autocorr_peak,
                        ir_hand_zone=ir_zone, ir_hand_activity=ir_act,
                    )
```

- [ ] **Step 6: Run all contact mic tests**

```bash
uv run pytest tests/hapax_daimonion/test_contact_mic_ir_fusion.py -v
```

Expected: all 6 tests pass.

- [ ] **Step 7: Run existing IR backend tests (regression)**

```bash
uv run pytest tests/hapax_daimonion/test_ir_presence_backend.py tests/hapax_daimonion/test_ir_signals.py -v
```

Expected: all tests pass.

- [ ] **Step 8: Commit**

```bash
git add agents/hapax_daimonion/backends/contact_mic.py tests/hapax_daimonion/test_contact_mic_ir_fusion.py
git commit -m "feat(ir): contact mic cross-modal fusion with IR hand zone

Contact mic now reads ir_hand_zone and ir_hand_activity to disambiguate
desk activity. turntable+sliding=scratching, mpc-pads+tapping=pad-work.
Cross-modal fusion as specified in design Component 8."
```

---

### Task 5: PR and verify end-to-end

- [ ] **Step 1: Run full test suite**

```bash
uv run pytest tests/hapax_daimonion/test_ir_presence_backend.py tests/hapax_daimonion/test_ir_signals.py tests/hapax_daimonion/test_contact_mic_ir_fusion.py -v
```

Expected: all tests pass.

- [ ] **Step 2: Verify perception-state.json has all 14 IR signals**

After restarting logos-api:

```bash
python3 -c "
import json
d = json.load(open('$HOME/.cache/hapax-daimonion/perception-state.json'))
ir_keys = sorted(k for k in d if k.startswith('ir_'))
print(f'IR signals in perception-state.json: {len(ir_keys)}')
for k in ir_keys:
    print(f'  {k}: {d[k]}')
"
```

Expected: 14 IR signals (13 original + ir_hand_zone).

- [ ] **Step 3: Create PR**

Create PR with all Batch 3 commits. Reference the design spec and audit findings.
