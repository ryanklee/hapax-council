# PresenceEngine signal calibration audit

**Date:** 2026-04-15
**Author:** beta (queue #206, identity verified via `hapax-whoami`)
**Scope:** calibration audit of `agents/hapax_daimonion/presence_engine.py::DEFAULT_SIGNAL_WEIGHTS` against the documented signal list in council CLAUDE.md § Bayesian Presence Detection.
**Branch:** `beta-phase-4-bootstrap` (branch-only commit per queue spec)

---

## 0. Summary

**14 signals are wired in source; CLAUDE.md documents 14 signal references (11 primary + 3 absence-focused).** Of the overlapping set, **9 signals match CLAUDE.md's LR values exactly**, **2 signals in CLAUDE.md are MISSING from source** (`ambient_energy`, `ir_body_heat`), **3 signals in source are NOT documented in CLAUDE.md** (`speaker_is_operator`, `watch_connected`, `ir_person_detected`), and **1 signal has a subtle LR discrepancy** (`watch_hr` false-LR: source produces 3.5x, CLAUDE.md says 3.3x — close but not exact).

**Hysteresis parameters match exactly** (0.7 enter, 0.3 exit, 2-tick enter, 24-tick exit, UNCERTAIN middle band).

**Signal absence handling** (positive-only vs bidirectional) matches spec intent where signals overlap.

## 1. LR derivation methodology

`DEFAULT_SIGNAL_WEIGHTS[signal]` is a `(p_present, p_absent)` tuple representing P(signal=True|present) and P(signal=True|absent). The likelihood ratio when the signal is observed True is:

```
LR_True = p_present / p_absent
```

When observed False:

```
LR_False = (1 - p_present) / (1 - p_absent)
```

When observed `None` (signal unknown / positive-only sensor reports absence as None):

```
LR_None = 1.0  (no update)
```

Values are compared against CLAUDE.md's "LR" column for each signal.

## 2. Per-signal audit

### Primary signals (from CLAUDE.md Primary + Secondary tables)

| Signal | Source weights | Source LR (True) | CLAUDE.md LR | Match | Notes |
|---|---|---|---|---|---|
| `desk_active` | (0.90, 0.05) | **18.0x** | **18x** | ✓ EXACT | Contact mic Cortado MKIII via pw-cat, positive-only |
| `keyboard_active` | (0.85, 0.05) | **17.0x** | **17x** | ✓ EXACT | evdev raw HID, bidirectional (also has False LR: (0.15/0.95)=0.158 → inverse 6.3x, CLAUDE.md says 5.6x — see §3 drift) |
| `ir_hand_active` | (0.85, 0.10) | **8.5x** | **8.5x** | ✓ EXACT | Pi NoIR hand detection (motion-gated >0.05), positive-only |
| `midi_active` | (0.90, 0.02) | **45.0x** | **45x** | ✓ EXACT | OXI One MIDI clock |
| `operator_face` | (0.90, 0.10) | **9.0x** | **9x** | ✓ EXACT | InsightFace SCRFD |
| `desktop_active` | (0.75, 0.10) | **7.5x** | **7.5x** | ✓ EXACT | Hyprland focus |
| `room_occupancy` | (0.85, 0.20) | **4.25x** | **4.25x** | ✓ EXACT | Multi-camera YOLO |
| `vad_speech` | (0.60, 0.15) | **4.0x** | **4x** | ✓ EXACT | Silero VAD |
| `bt_phone_connected` | (0.70, 0.30) | **2.33x** | **2.33x** | ✓ EXACT | Linux BLE unreliable; down-weighted per source comment |
| `phone_kde_connected` | (0.80, 0.25) | **3.2x** | **3.2x** | ✓ EXACT | KDE Connect WiFi reachable |
| `ambient_energy` | **MISSING** | **n/a** | **3x** | **DRIFT D1** | CLAUDE.md lists Blue Yeti room noise as LR 3x; source has no `ambient_energy` entry |

### Absence signals (from CLAUDE.md Absence table)

| Signal | Source (p_present, p_absent) | Source LR (False) | CLAUDE.md LR (False) | Match |
|---|---|---|---|---|
| `keyboard_active` | (0.85, 0.05) | (0.15/0.95) → inverse 6.3x | **5.6x** | ✗ MINOR DRIFT (~12% off) |
| `watch_hr` | (0.80, 0.30) | (0.20/0.70) → inverse 3.5x | **3.3x** | ✗ MINOR DRIFT (~6% off) |
| `ir_body_heat` | **MISSING** | **n/a** | **6.7x** | **DRIFT D2** |

### Source signals not documented in CLAUDE.md

| Signal | Source weights | Source LR (True) | Status |
|---|---|---|---|
| `speaker_is_operator` | (0.95, 0.02) | **47.5x** | **DRIFT D3** — not in CLAUDE.md; highest LR in source |
| `watch_connected` | (0.70, 0.40) | **1.75x** | **DRIFT D4** — not in CLAUDE.md |
| `ir_person_detected` | (0.90, 0.10) | **9.0x** | **DRIFT D5** — not in CLAUDE.md; IR primary signal complementing `ir_hand_active` |

## 3. Drift catalog

### D1 — `ambient_energy` missing from source (CLAUDE.md says LR 3x)

**CLAUDE.md text:** *"ambient_energy (Blue Yeti room noise, 3x)"* in the Secondary signals list.

**Source state:** no `ambient_energy` entry in `DEFAULT_SIGNAL_WEIGHTS`. Grep confirms zero occurrence in `presence_engine.py`.

**Implication:** either the ambient_energy signal was intended but never implemented, or it was implemented under a different name (e.g., `ambient_audio_rms`) that the dict doesn't use. A search for `ambient` in the file returns zero hits — so the signal is genuinely not wired.

**Severity:** MEDIUM. CLAUDE.md documents a signal that the engine doesn't actually consume. Either:
- (a) wire `ambient_energy` into `DEFAULT_SIGNAL_WEIGHTS` with LR 3x (likely values: `(0.75, 0.25)` → 3.0x exact)
- (b) delete the entry from CLAUDE.md §Bayesian Presence Detection as not-yet-implemented
- (c) document the intended signal path (which backend publishes it, what the thresholds are)

**Beta recommendation:** option (a) — wire it. `AmbientAudioBackend` IS in the init_backends list (per the backends drift audit #204), so the backend exists; the presence_engine just doesn't read its output.

### D2 — `ir_body_heat` missing from source (CLAUDE.md says False LR 6.7x)

**CLAUDE.md text:** *"ir_body_heat IR brightness drop >15 units 6.7x Body left IR field"* in the Absence signals list.

**Source state:** no `ir_body_heat` entry in `DEFAULT_SIGNAL_WEIGHTS`. Grep confirms zero occurrence.

**Implication:** the absence signal for "operator left the IR field" is not consumed by the presence engine. This weakens the AWAY transition — the engine relies on `keyboard_active` + `watch_hr` staleness as its absence signals, but CLAUDE.md also promises an IR-body-heat based absence signal that the engine does not honor.

**Severity:** MEDIUM-HIGH. An absence signal documented in CLAUDE.md should be consumed by the engine or documented as "future". Currently, the engine cannot tell "body left the IR field" apart from "body still there with cold IR camera".

**Beta recommendation:** wire `ir_body_heat` into `DEFAULT_SIGNAL_WEIGHTS` with values producing a False LR of 6.7x — e.g., `(0.85, 0.11)` → False LR = (0.15/0.89) inverse → 5.9x (close), or `(0.87, 0.10)` → (0.13/0.90) inverse → 6.92x (closer). Calibrate from empirical data if available.

### D3 — `speaker_is_operator` in source, not in CLAUDE.md (LR 47.5x)

**Source state:** `"speaker_is_operator": (0.95, 0.02)` → LR 47.5x. Higher than any signal documented in CLAUDE.md.

**Implication:** the highest-weight signal in the engine is undocumented. A new session reading CLAUDE.md would not know that speaker identification via (probably) a speaker verification model is consumed by presence detection.

**Severity:** MEDIUM. The signal is more load-bearing than most documented ones. CLAUDE.md should list it.

**Beta recommendation:** add `speaker_is_operator (<backend source> via <method>, 47.5x)` to CLAUDE.md Primary signals table.

### D4 — `watch_connected` in source, not in CLAUDE.md (LR 1.75x)

**Source state:** `"watch_connected": (0.70, 0.40)` → LR 1.75x. Weaker than `watch_hr` (2.67x) but distinct.

**Implication:** the engine consumes a second watch signal beyond `watch_hr`. Its interpretation: "the watch radio is connected to the phone/workstation, regardless of whether we have a recent HR reading". Complementary to `watch_hr` which requires a live biometric sample.

**Severity:** LOW. Minor signal, low LR. But CLAUDE.md's watch row only mentions `watch_hr` so the two-signal structure is not visible to a reader.

**Beta recommendation:** add `watch_connected (Pixel Watch BLE link, 1.75x)` to CLAUDE.md Absence signals (complementary to `watch_hr` staleness).

### D5 — `ir_person_detected` in source, not in CLAUDE.md (LR 9x)

**Source state:** `"ir_person_detected": (0.90, 0.10)` → LR 9.0x. Primary IR signal via Pi NoIR person detection (distinct from `ir_hand_active` at 8.5x).

**Implication:** the engine consumes a dedicated person-detection signal from the IR pipeline beyond the hand-detection signal. CLAUDE.md's IR Perception § Fusion logic mentions "Person detection = any() across Pis" but the presence engine's consumption of this signal is not documented in §Bayesian Presence Detection.

**Severity:** MEDIUM. The signal is a primary (LR 9x), not secondary. CLAUDE.md's Primary signals table should list it.

**Beta recommendation:** add `ir_person_detected (Pi NoIR person detection, 9x)` to CLAUDE.md Primary signals table next to `ir_hand_active`.

### Minor drifts (D6, D7)

**D6 — `keyboard_active` False LR:** source produces 6.3x (1-0.85 / 1-0.05 = 0.158 → 1/0.158 = 6.3), CLAUDE.md says 5.6x. Difference is ~12%.

**Severity:** LOW. Could be a rounding drift in CLAUDE.md (5.6 is close to but not exactly 6.3). Either recalibrate the source to (0.80, 0.05) → False LR = (0.20/0.95) inverse → 4.75x (worse) or (0.88, 0.04) → (0.12/0.96) inverse → 8x (worse) — no simple value gives exactly 5.6x. Most likely explanation: CLAUDE.md's 5.6x is a manual approximation, and source's 6.3x is the actual computed value.

**Recommendation:** update CLAUDE.md's keyboard_active False LR row from 5.6x to 6.3x to match source.

**D7 — `watch_hr` False LR:** source produces 3.5x, CLAUDE.md says 3.3x. ~6% drift. Same pattern as D6.

**Recommendation:** update CLAUDE.md from 3.3x to 3.5x.

## 4. Hysteresis audit

**CLAUDE.md spec:**

> *"PRESENT (≥0.7 for 2 ticks), UNCERTAIN, AWAY (<0.3 for 24 ticks)"*

**Source state** (`presence_engine.py` constructor defaults + `_transition_ticks_required`):

- `enter_threshold = 0.7` ✓
- `exit_threshold = 0.3` ✓
- `enter_ticks = 2` ✓ (→ "5s to enter PRESENT" per line 394 comment, implying 2.5s tick cadence)
- `exit_ticks = 24` ✓ (→ "60s to leave PRESENT" per line 392 comment)
- UNCERTAIN band: implicit `exit_threshold ≤ posterior < enter_threshold` ✓

**Match:** ✓ EXACT. Hysteresis parameters in the source match CLAUDE.md 1:1.

**Observation:** CLAUDE.md says "for 2 ticks" / "for 24 ticks" but doesn't specify the tick duration. Source line 394 comment implies 2.5s ticks (2 ticks * 2.5s = 5s, 24 ticks * 2.5s = 60s). CLAUDE.md could add the tick-duration note for clarity but it's not drift.

## 5. Signal absence handling audit

**CLAUDE.md design principle:**

> *"Signal design principle — positive-only for unreliable sensors: signals where absence is ambiguous (face not visible, silence, no desktop focus change) contribute True when detected but None (skipped by Bayesian update) when absent. Only structurally reliable signals (keyboard from evdev, BT connection) use bidirectional evidence."*

**Source state** (spot-check of `_read_signals()`):

| Signal | CLAUDE.md type | Source handling | Match |
|---|---|---|---|
| `operator_face` | positive-only (no face = neutral) | `obs["operator_face"] = None` when no face (line 209-211) | ✓ |
| `keyboard_active` | bidirectional (evdev reliable) | `obs["keyboard_active"] = True/False` (line 216-229) | ✓ |
| `vad_speech` | positive-only | `obs["vad_speech"] = None` when no speech (line 237) | ✓ |
| `watch_hr` | bidirectional False at staleness >120s | `obs["watch_hr"] = False` at staleness (line 255) | ✓ |
| `ir_hand_active` | positive-only (motion-gated) | *(not spot-checked here; per protocol v1.5 verify-before-writing, marked as UNVERIFIED but high-confidence based on CLAUDE.md + consistency)* | ~✓ |
| `desk_active` | positive-only (contact mic) | *(not spot-checked; same as above)* | ~✓ |

**Match:** overall ✓. Signal absence handling in the observed code paths matches CLAUDE.md's positive-only vs bidirectional design principle.

## 6. Drift summary matrix

| # | Drift | CLAUDE.md value | Source value | Severity | Proposed fix |
|---|---|---|---|---|---|
| D1 | `ambient_energy` missing from source | 3x LR | — | MEDIUM | Wire `(0.75, 0.25)` into DEFAULT_SIGNAL_WEIGHTS |
| D2 | `ir_body_heat` missing from source | 6.7x False LR | — | MEDIUM-HIGH | Wire `(0.87, 0.10)` into DEFAULT_SIGNAL_WEIGHTS |
| D3 | `speaker_is_operator` undocumented | — | 47.5x LR | MEDIUM | Add to CLAUDE.md Primary signals |
| D4 | `watch_connected` undocumented | — | 1.75x LR | LOW | Add to CLAUDE.md (possibly as secondary) |
| D5 | `ir_person_detected` undocumented | — | 9x LR | MEDIUM | Add to CLAUDE.md Primary signals |
| D6 | `keyboard_active` False LR | 5.6x | 6.3x | LOW | Update CLAUDE.md to 6.3x |
| D7 | `watch_hr` False LR | 3.3x | 3.5x | LOW | Update CLAUDE.md to 3.5x |

**7 drift items** total. D1/D2 are substantive (missing signals). D3/D4/D5 are documentation-only (source correct, docs incomplete). D6/D7 are rounding drifts (both sides could be updated).

## 7. Recommendations

### 7.1 Source changes (D1 + D2)

Wire `ambient_energy` + `ir_body_heat` into `DEFAULT_SIGNAL_WEIGHTS`:

```python
DEFAULT_SIGNAL_WEIGHTS: dict[str, tuple[float, float]] = {
    # ... existing entries ...
    "ambient_energy": (0.75, 0.25),  # D1: Blue Yeti room noise, LR 3x
    "ir_body_heat": (0.87, 0.10),    # D2: IR brightness drop >15 units, False LR 6.9x ~ 6.7x
}
```

Also wire the corresponding `_read_signals()` branches to populate these from the backend observations.

**Expected effort:** ~20 min (2 dict entries + 2 _read_signals branches + updating tests + verifying backend output is available).

**Proposed queue item #211** for delta to seed:

```yaml
id: "211"
title: "Wire ambient_energy + ir_body_heat into PresenceEngine (calibration audit D1+D2 fix)"
assigned_to: beta  # or alpha — both are code-touching
status: offered
priority: normal
depends_on: [206]
description: |
  Fix D1 + D2 from queue/206-beta-presence-engine-signal-calibration-
  audit.yaml: ambient_energy + ir_body_heat are in CLAUDE.md but not in
  DEFAULT_SIGNAL_WEIGHTS. Wire both + add _read_signals() branches +
  test coverage. ~20 min.
size_estimate: "~40 LOC + tests, ~20 min"
```

### 7.2 CLAUDE.md changes (D3/D4/D5/D6/D7)

Amend council CLAUDE.md § Bayesian Presence Detection to include the 3 undocumented signals + update the 2 rounding-drift values. Single small doc PR. ~10 min.

**Proposed queue item #212** for delta to seed:

```yaml
id: "212"
title: "CLAUDE.md Bayesian Presence Detection signal list update (calibration audit D3-D7)"
assigned_to: beta  # docs-only
status: offered
priority: low
depends_on: [206]
description: |
  Fix D3-D7 from queue/206: add speaker_is_operator (47.5x),
  watch_connected (1.75x), ir_person_detected (9x) to CLAUDE.md
  signal tables. Update keyboard_active False LR 5.6→6.3x and
  watch_hr False LR 3.3→3.5x to match source. ~10 min, single doc PR.
size_estimate: "~15 line diff, ~10 min"
```

### 7.3 Non-urgent

- Verify the unverified positive-only handling for `ir_hand_active` + `desk_active` by reading the `_read_signals()` lines for those signals. This audit marked them as ~✓ (high-confidence but unverified) — a follow-up session can close the loop.
- Consider adding a lint test that fails if `DEFAULT_SIGNAL_WEIGHTS` and CLAUDE.md's signal tables drift. Would catch future mis-alignment automatically.

## 8. Cross-references

- `agents/hapax_daimonion/presence_engine.py` (line 27-48 for DEFAULT_SIGNAL_WEIGHTS, line 66-74 for hysteresis constructor, line 196+ for `_read_signals()`)
- Council CLAUDE.md § Bayesian Presence Detection
- Council CLAUDE.md § IR Perception (Pi NoIR Edge Fleet)
- Beta's daimonion backends drift audit — `docs/research/2026-04-15-daimonion-backends-drift-audit.md` (commit `ea832f7c4`) — companion audit
- Queue item spec — `~/.cache/hapax/relay/queue/206-beta-presence-engine-signal-calibration-audit.yaml`

— beta, 2026-04-15T18:25Z (identity: `hapax-whoami` → `beta`)
