# Daimonion backends test coverage check

**Date:** 2026-04-15
**Author:** beta (queue #234, identity verified via `hapax-whoami`)
**Scope:** map every file in `agents/hapax_daimonion/backends/` to its test coverage in `tests/`; rank gaps by correctness risk; flag untested signal paths. Follow-up to queue #204 drift audit.
**Branch:** `beta-phase-4-bootstrap`

---

## 0. Summary

**Verdict: 27 backend files (6708 LOC); 15 have BEHAVIORAL tests (2457 test LOC); 11 have ONLY protocol-conformance coverage via `test_backend_protocol.py`; 1 is dead code with dead tests.** Coverage concentrated around high-complexity backends (contact_mic, mixer_input, studio_ingestion, local_llm) while simpler phone + presence backends are largely uncovered.

**Counts:**

| Tier | Backends | LOC | Test coverage status |
|---|---|---|---|
| Full behavioral coverage | 14 | 2845 | Unit tests exist + import the backend |
| Protocol-only coverage | 11 | 1773 | Only `test_backend_protocol.py` shape checks; no behavior tests |
| Indirect coverage (integration) | 1 | 1864 | `vision.py` — only 58 LOC of indirect tests via `test_overhead_zones.py` |
| Dead code with dead tests | 1 | 29 | `contact_mic_ir.py` (per queue #233 — never called in production) |

**Critical findings:**

1. 🔴 **`vision.py` is the highest correctness risk:** 1864 LOC (largest backend), only 58 LOC of indirect tests (test_overhead_zones.py touches `_infer_cross_modal_activity`). 32:1 LOC ratio. Zero direct unit tests. Handles person detection, face detection, gaze estimation, hand zones, per-camera scene consensus — all critical presence + classification signals.
2. 🔴 **11 backends with ZERO behavioral tests** (1773 LOC total, 26.4% of backend surface):
   - `attention` (94 LOC) — gaze_zone, engagement_level, posture_state
   - `bt_presence` (108 LOC) — bt_watch_connected (2.33x LR in PresenceEngine)
   - `devices` (254 LOC) — usb_devices, bluetooth_nearby, network_devices
   - `input_activity` (160 LOC) — input_active, input_idle_seconds
   - `phone_awareness` (196 LOC) — legacy phone presence signals
   - `phone_calls` (171 LOC) — phone_call_active, phone_call_incoming
   - `phone_contacts` (156 LOC) — phone_kde_connected (3.2x LR)
   - `phone_media` (118 LOC) — phone_media_playing, phone_media_title, phone_media_artist
   - `phone_messages` (132 LOC) — phone_sms_unread, phone_sms_latest_sender, phone_sms_latest_text
   - `pipewire` (112 LOC) — sink_volume, midi_active
   - `speech_emotion` (272 LOC) — speech_emotion, audio_events, speech_language
3. 🟡 **`test_backend_protocol.py` (96 LOC) provides protocol-conformance coverage for 22 of 27 backends** — shape-only tests (name, provides, tier, available, contribute, start, stop). Shape pass does NOT validate signal-processing logic.
4. 🟡 **5 backends are MISSING from `test_backend_protocol.py`'s `_BACKENDS` list:** `vision`, `evdev_input`, `ambient_audio`, `phone_contacts`, `contact_mic_ir`. Of these, `evdev_input` and `ambient_audio` have dedicated unit tests; `vision` has indirect coverage; `phone_contacts` has neither; `contact_mic_ir` is dead code.
5. 🔴 **Dead-code test cluster:** `contact_mic_ir.py::_classify_activity_with_ir` is never called in production (established in queue #233), but `test_contact_mic_ir_fusion.py` (75 LOC) exercises it. 75 LOC of test ceremony for a dead feature.

**Severity:**
- **HIGH** for the vision.py gap (largest backend, zero direct unit tests, critical signal paths — classification, face, gaze, zones)
- **MEDIUM** for the 11 untested backends (each one is a potential silent-failure surface like queue #233's contact_mic_ir; without behavioral tests, regressions land silently)
- **LOW** for the dead-test cluster (it's test ceremony but doesn't cause harm beyond test runtime)

## 1. Full coverage matrix

Sorted by backend LOC (largest = highest complexity = highest risk first):

| Backend | LOC | Test files | Test LOC | Ratio | Notes |
|---|---|---|---|---|---|
| `vision` | 1864 | `test_overhead_zones.py` | 58 | 32:1 | INDIRECT ONLY — tests `_infer_cross_modal_activity()` helper, not the full backend |
| `contact_mic` | 520 | `test_contact_mic_backend.py` | 313 | 1.7:1 | Good unit coverage of DSP + cache + classification |
| `mixer_input` | 353 | `test_mixer_input_backend.py` | 274 | 1.3:1 | Good |
| `studio_ingestion` | 329 | `test_studio_ingestion_backend.py` | 270 | 1.2:1 | Good |
| `local_llm` | 313 | `test_local_llm_backend.py` + `test_local_llm_gate.py` | 303 | 1.0:1 | Good |
| `ir_presence` | 308 | `test_ir_presence_backend.py` + `test_ir_brightness.py` + `test_exploration_wiring.py` | 303 | 1.0:1 | Good |
| `speech_emotion` | 272 | **NONE** | 0 | ∞ | Unit-test GAP |
| `devices` | 254 | **NONE** | 0 | ∞ | Unit-test GAP |
| `phone_awareness` | 196 | **NONE** | 0 | ∞ | Unit-test GAP |
| `watch` | 193 | `test_watch_backend.py` | 117 | 1.7:1 | Plus `test_watch_signals.py` (341 LOC, tests signal layer separately) |
| `midi_clock` | 173 | `test_midi_clock_backend.py` | 133 | 1.3:1 | Good |
| `phone_calls` | 171 | **NONE** | 0 | ∞ | Unit-test GAP |
| `input_activity` | 160 | **NONE** | 0 | ∞ | Unit-test GAP (test_audio_input.py tests different module) |
| `phone_contacts` | 156 | **NONE** | 0 | ∞ | Unit-test GAP — also missing from `test_backend_protocol.py` |
| `ambient_audio` | 136 | `test_ambient_audio.py` | 36 | 3.8:1 | Thin coverage but present |
| `evdev_input` | 136 | `test_evdev_input.py` | 61 | 2.2:1 | Thin coverage but present |
| `circadian` | 132 | `test_circadian_backend.py` | 105 | 1.3:1 | Good |
| `phone_messages` | 132 | **NONE** | 0 | ∞ | Unit-test GAP |
| `clipboard` | 128 | `test_clipboard_backend.py` | 29 | 4.4:1 | Thin coverage but present |
| `phone_media` | 118 | **NONE** | 0 | ∞ | Unit-test GAP |
| `stream_health` | 115 | `test_stream_health_backend.py` | 70 | 1.6:1 | Good |
| `pipewire` | 112 | **NONE** | 0 | ∞ | Unit-test GAP |
| `bt_presence` | 108 | **NONE** | 0 | ∞ | Unit-test GAP |
| `health` | 106 | `test_health_backend.py` | 125 | 0.8:1 | Tests larger than impl — excellent |
| `hyprland` | 100 | (no direct test found) | 0 | ∞ | Likely covered indirectly via test_perception_* files |
| `attention` | 94 | **NONE** | 0 | ∞ | Unit-test GAP |
| `contact_mic_ir` | 29 | `test_contact_mic_ir_fusion.py` | 75 | 0.4:1 | **DEAD CODE** — tests exercise a function never called in production |

**Methodology:** used `grep -rlE 'from agents.hapax_daimonion.backends.{name}\b\|import agents.hapax_daimonion.backends.{name}\b' tests/` to find test files that actually import each backend module. Protocol-only coverage via `test_backend_protocol.py` is NOT counted in this column because it does not import any specific backend behaviorally — it uses `importlib.import_module` through a parametrized fixture.

## 2. Protocol-only coverage via `test_backend_protocol.py`

```
$ wc -l tests/hapax_daimonion/test_backend_protocol.py
97 tests/hapax_daimonion/test_backend_protocol.py
```

The file defines a `_BACKENDS` list of 22 (module_path, class_name) tuples and parametrizes 6 shape-checking test methods across all of them via a pytest fixture. Tests:

- `test_has_name_property` — backend.name is a non-empty str
- `test_has_provides_frozenset` — backend.provides is a frozenset
- `test_has_tier` — backend.tier is a PerceptionTier
- `test_available_returns_bool` — backend.available() returns bool
- `test_contribute_accepts_dict` — backend.contribute({}) does not raise
- `test_has_start_and_stop` — start + stop are callable

**6 test methods × 22 backends = 132 test invocations.** This is a valuable conformance net: if a backend breaks the PerceptionBackend protocol (wrong return type, missing method, constructor failure), this file fails fast. **But shape-pass is not behavior-pass.** A backend that returns bogus values from `available()` or an empty dict from `contribute()` passes protocol conformance while silently producing garbage signals.

### 2.1 Backends in `_BACKENDS`

```
pipewire, hyprland, watch, health, circadian, devices, input_activity,
contact_mic, mixer_input, ir_presence, bt_presence, midi_clock, phone_media,
phone_messages, phone_calls, stream_health, attention, clipboard,
speech_emotion, studio_ingestion, local_llm, phone_awareness
```

22 backends. **All of the "Unit-test GAP" backends in §1 (except `phone_contacts`)** are in this list. So they have SHAPE coverage but not BEHAVIOR coverage.

### 2.2 Backends MISSING from `_BACKENDS`

Five backend files are NOT in the protocol conformance list:

| File | Reason suggested |
|---|---|
| `vision.py` | 1864 LOC, may have been excluded because it doesn't subclass the same protocol shape (it's an aggregator over multiple camera sub-backends) |
| `evdev_input.py` | Helper module used by input_activity; may not be a standalone backend |
| `ambient_audio.py` | Helper module; may not be a standalone backend |
| `phone_contacts.py` | Unclear — this has `provides = frozenset()` and looks like a real backend |
| `contact_mic_ir.py` | Not a backend class at all; just a helper function (per queue #233) |

**`phone_contacts.py` is the concerning one** — 156 LOC, real backend class, completely absent from any test file. Full coverage gap.

**`vision.py` is the worst** — 1864 LOC of critical visual perception logic (person detection, face detection, gaze, zones, scene classification) with ONLY 58 LOC of cross-modal helper tests. Shape-wise absent from protocol tests too. **Highest correctness risk in the entire backend directory.**

## 3. Untested signal paths enumerated

For each "Unit-test GAP" backend, the signals it advertises via `provides`:

| Backend | Signals advertised | PresenceEngine LR? |
|---|---|---|
| `attention` | `gaze_zone`, `engagement_level`, `posture_state` | Not directly — feeds `operator_face` path |
| `bt_presence` | `bt_watch_connected` | **2.33x** (DEFAULT_SIGNAL_WEIGHTS["bt_phone_connected"]) |
| `devices` | `usb_devices`, `bluetooth_nearby`, `network_devices` | Not directly, but informs `phone_kde_connected` |
| `input_activity` | `input_active`, `input_idle_seconds` | Bridged via `keyboard_active` (17x LR) |
| `phone_awareness` | (legacy, unclear) | — |
| `phone_calls` | `phone_call_active`, `phone_call_incoming`, `phone_call_number` | Not directly |
| `phone_contacts` | (empty provides? suggests dead or wip backend) | Unclear |
| `phone_media` | `phone_media_playing`, `phone_media_title`, `phone_media_artist` | Not directly |
| `phone_messages` | `phone_sms_unread`, `phone_sms_latest_sender`, `phone_sms_latest_text` | Not directly |
| `pipewire` | `sink_volume`, `midi_active` | `midi_active` is **45x** (DEFAULT_SIGNAL_WEIGHTS["midi_active"]) |
| `speech_emotion` | `speech_emotion`, `audio_events`, `speech_language` | Not directly, but informs voice turn routing |
| `vision` (indirect) | person_count, face_count, gaze_direction, posture, hand_gesture, scene_type, ... | Multiple paths — feeds `operator_face` (9x LR), `room_occupancy` (4.25x LR) |

**Three of these are high-LR presence signals** with zero behavioral test coverage:

- `pipewire.py::midi_active` — 45x LR (strongest positive signal after `midi_playing`). If the backend silently regresses to always returning False, the PresenceEngine posterior drops by ~log(45) ≈ 3.8 log-odds on every midi event — a major signal loss with no test to catch it.
- `bt_presence.py::bt_watch_connected` — 2.33x LR. Queue #220 established that the Pixel Watch BLE has been offline for 9+ days. Without a behavioral test, it's impossible to distinguish "backend broken" from "hardware absent".
- `vision.py` (indirect via `room_occupancy`, `operator_face`) — 4.25x + 9x LRs. The highest-complexity backend with the thinnest test coverage.

## 4. Dead-test cluster

```
tests/hapax_daimonion/test_contact_mic_ir_fusion.py   75 LOC
```

Queue #233 established that `agents/hapax_daimonion/backends/contact_mic_ir.py::_classify_activity_with_ir` is NEVER called in production — `ContactMicBackend._capture_loop` at line 443 calls the base `_classify_activity()` directly, bypassing the IR fusion helper. The 75-LOC test file exercises the fusion helper in isolation, verifying its branching logic — but since the helper is never invoked from production code, passing these tests provides zero operator-visible correctness guarantee.

**Severity:** LOW. The tests aren't wrong; they accurately test what the helper does. The problem is that the helper is unused. Per queue #233 §7.1 proposed #240, the fix is to either wire the helper (Path A, preferred) or delete both the helper and its tests (Path B). Until then, `test_contact_mic_ir_fusion.py` is 75 LOC of dead ceremony.

## 5. Risk-ranked gaps

**Ranked by correctness-risk-to-fix-effort ratio:**

### 5.1 HIGH — vision.py direct unit tests

**Risk:** 1864 LOC of production visual perception, 58 LOC of indirect tests. Includes face detection, gaze estimation, person counting, hand zone classification, scene classification, per-camera consensus logic. Any silent regression in these code paths propagates to: operator presence posterior, voice turn routing, stimmung modulation, affordance recruitment, studio compositor metrics.

**Effort to close:** HIGH. Writing unit tests for vision.py requires mocking OpenCV + OpenVINO + onnxruntime + 6 cameras. Integration-style tests with fixture images would be more tractable but require fixture curation.

**Recommended approach:** start with cross-modal helper functions (the `_infer_cross_modal_activity` path that `test_overhead_zones.py` already exercises) and expand outward.

### 5.2 HIGH — pipewire.py midi_active coverage

**Risk:** 45x LR signal with zero behavioral tests. If the pw-dump subprocess call regresses, the signal silently fails (same pattern as queue #233's contact_mic).

**Effort to close:** LOW. ~50 LOC unit test mocking pw-dump subprocess output.

### 5.3 MEDIUM — 11 untested backends

**Risk:** each is a potential silent-failure surface. History shows (queue #233) that "it's fine because PipeWire loopback is running" is not sufficient — the backend can be "running" while producing zero signal.

**Effort to close:** scattered. Each backend is 100-300 LOC; a 100-LOC test file per backend would need ~1100 LOC total.

**Recommended approach:** prioritize by PresenceEngine LR: `pipewire` (45x) → `bt_presence` (2.33x) → the rest in priority order. Also prioritize `phone_contacts.py` because it has zero coverage AND is missing from protocol conformance.

### 5.4 LOW — `vision.py`, `phone_contacts.py`, `evdev_input.py`, `ambient_audio.py` missing from `_BACKENDS`

**Risk:** protocol regressions in these files are not caught by the conformance test. Adding them to the `_BACKENDS` list is a ~5-LOC patch per backend.

**Effort to close:** TRIVIAL. Just add the `(module_path, class_name)` tuples. The parametrized fixture handles the rest.

**Immediate blocker:** the fixture calls `cls()` (no args); if any of these backends has a required constructor arg, the test skips — confirming the gap but not actually testing it.

### 5.5 LOW — `test_contact_mic_ir_fusion.py` dead tests

**Risk:** trivial — 75 LOC of test ceremony that doesn't reflect production behavior.

**Effort to close:** bundled with queue #233 proposed #240. If #240 goes Path A (wire it), the tests become live. If #240 goes Path B (delete), the tests go away too.

## 6. Recommended follow-ups

### 6.1 #244 — vision.py unit test scaffolding

```yaml
id: "244"
title: "Scaffold vision.py unit tests (largest backend, 1864 LOC, 58 LOC tests)"
assigned_to: beta
status: offered
depends_on: []
priority: low
description: |
  Queue #234 found vision.py is the largest backend (1864 LOC) with
  only 58 LOC of indirect tests via test_overhead_zones.py. Highest
  correctness risk in the backend directory per the coverage audit.
  
  Scope Phase 1 (this item): scaffold a test_vision_backend.py file
  with unit tests for the pure helper functions + cross-modal logic.
  Do NOT attempt full camera-mock integration tests in this pass.
  
  Actions:
  1. Identify pure helper functions in vision.py (no subprocess,
     no camera, no onnxruntime)
  2. Write unit tests for each with plausible input fixtures
  3. Target: 150-200 LOC new test file covering ~10-15 functions
  4. Add vision.py to test_backend_protocol.py _BACKENDS list
  
  Does NOT include: full VisionBackend instantiation test (requires
  mocking all camera inputs + ML models).
size_estimate: "~2 hours"
```

### 6.2 #245 — pipewire backend midi_active test

```yaml
id: "245"
title: "Unit test pipewire.py backend midi_active path"
assigned_to: beta
status: offered
depends_on: []
priority: low
description: |
  pipewire.py exposes midi_active (45x LR in PresenceEngine
  DEFAULT_SIGNAL_WEIGHTS, the STRONGEST positive-tier signal). Zero
  behavioral test coverage today. Silent regression could drop the
  posterior by ~3.8 log-odds on every MIDI event.
  
  Actions:
  1. Write test_pipewire_backend.py
  2. Mock pw-dump subprocess with fixture JSON
  3. Test: midi_active=True when MIDI source is active
  4. Test: midi_active=False when no MIDI source
  5. Test: backend handles pw-dump failure gracefully
size_estimate: "~30 min"
```

### 6.3 #246 — Add missing backends to test_backend_protocol.py

```yaml
id: "246"
title: "Add vision, phone_contacts, evdev_input, ambient_audio to test_backend_protocol._BACKENDS"
assigned_to: beta
status: offered
depends_on: []
priority: low
description: |
  Queue #234 found 5 backend files absent from test_backend_protocol.py
  _BACKENDS list: vision, phone_contacts, evdev_input, ambient_audio,
  contact_mic_ir. Of these:
  - vision: full backend class, should be added
  - phone_contacts: full backend class, should be added
  - evdev_input: helper for input_activity, may not need protocol pass
  - ambient_audio: helper for input_activity, may not need protocol pass
  - contact_mic_ir: DEAD CODE (queue #233), DO NOT add
  
  Actions:
  1. Verify vision.VisionBackend exists + constructor signature
  2. Verify phone_contacts has a backend class (given provides=frozenset())
  3. Add both tuples to _BACKENDS list
  4. Run pytest test_backend_protocol.py + verify both pass or skip gracefully
size_estimate: "~20 min"
```

### 6.4 #247 — Untested presence-LR backends unit tests

```yaml
id: "247"
title: "Unit tests for 11 untested daimonion backends"
assigned_to: beta
status: offered
depends_on: []
priority: low
description: |
  Queue #234 found 11 backends with zero behavioral test coverage:
  attention, bt_presence, devices, input_activity, phone_awareness,
  phone_calls, phone_contacts, phone_media, phone_messages, pipewire,
  speech_emotion.
  
  Priority order (by PresenceEngine LR weight):
  1. pipewire (45x) — covered by #245 above
  2. bt_presence (2.33x) — this item
  3. input_activity (bridges 17x keyboard_active) — this item
  4. Others in any order
  
  Scope: ~100 LOC test file per backend, mocking external deps
  (subprocess, dbus, bluetooth APIs).
size_estimate: "~6 hours for all 11, or ~30 min per backend individually"
```

## 7. Non-drift observations

- **Top-5 backends have adequate coverage.** Contact_mic, mixer_input, studio_ingestion, local_llm, ir_presence all have 1.0-1.7:1 test-to-impl ratios with dedicated unit test files. These are the most complex non-vision backends and the ones most likely to have ongoing maintenance — they're well-defended.
- **`test_backend_protocol.py` is a good safety net.** 6 shape tests × 22 backends = 132 test invocations in a 96-LOC file. High-value, low-maintenance. Worth extending to cover all 27 backends (see #246).
- **Thin test files (36-75 LOC) for `ambient_audio`, `clipboard`, `evdev_input` signal the bare-minimum-coverage pattern.** They have tests, but not much more than "instantiate + contribute without crashing". Could be strengthened if any of these backends report drift findings in the future.
- **Dead-code tests don't cost much.** `test_contact_mic_ir_fusion.py` is 75 LOC of dead ceremony but the test suite doesn't care — it just runs quickly against a helper that nobody else calls. The real cost is the FALSE confidence the test gives: "we have tests for the cross-modal fusion" sounds like an assurance but refers to a feature that doesn't exist in production.
- **Queue #234 + #233 + #220 are the same coverage theme.** #220 (watch HR stale 9 days) could have been caught earlier by a watch backend test that asserts staleness > 120s → signal=None AND an alert. #233 (contact mic null audio) could have been caught by a backend test that asserts "if RMS has been 0.0 for N ticks, something is wrong". Both failures were silent because the tests don't assert "the backend is OBSERVING the expected signal", only "the backend returns the expected shape of output when fed mock input".
- **This is a classic "test the happy path, miss the silent degradation" gap.** Adding "silent-failure detection" tests is a category that's not yet represented in the test suite for any backend.

## 8. Cross-references

- Queue spec: `queue/234-beta-daimonion-backends-test-coverage-check.yaml`
- Predecessor audit: `docs/research/2026-04-15-daimonion-backends-drift-audit.md` (commit `ea832f7c4`)
- Sibling findings:
  - Queue #233 Cortado contact mic DSP drift: `docs/research/2026-04-15-contact-mic-dsp-drift-check.md` (commit `9cf6c388e`) — established the dead-code finding for `contact_mic_ir.py`
  - Queue #230 voice FX chain verification: `docs/research/2026-04-15-voice-fx-chain-pipewire-verification.md` (commit `e82c32840`)
  - Queue #220 PresenceEngine LR tuning blocked: `docs/research/2026-04-15-presence-engine-lr-tuning-live-data.md` — sibling silent-failure finding
  - Queue #206 PresenceEngine signal calibration audit (commit `cbd0264dc`)
  - Queue #224 PresenceEngine Prometheus observability (commit `954494ea5`)
- Backend files: `agents/hapax_daimonion/backends/*.py` (28 files, 6708 LOC)
- Test files: `tests/hapax_daimonion/test_*.py` (34481 LOC total across all test files — not all backend tests)
- Protocol conformance: `tests/hapax_daimonion/test_backend_protocol.py` (97 LOC)
- `PresenceEngine.DEFAULT_SIGNAL_WEIGHTS`: `agents/hapax_daimonion/presence_engine.py:27`

— beta, 2026-04-15T21:25Z (identity: `hapax-whoami` → `beta`)
