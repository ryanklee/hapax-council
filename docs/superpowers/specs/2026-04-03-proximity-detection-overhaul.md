# Proximity Detection Overhaul

**Date:** 2026-04-03
**Status:** Spec complete, implementation pending
**Author:** Alpha session + operator
**Scope:** Presence engine signal quality — accurate proximity at all times

## Problem

The Bayesian presence engine holds `presence_probability=0.999` even when the operator leaves the room for 20+ minutes. Root causes identified:

1. **Virtual input devices** (`RustDesk UInput Keyboard`, `mouce-library-fake-mouse`) generate fake HID events that keep logind's `IdleHint=no` permanently. Claude Code tool calls trigger these virtual devices.
2. **BT presence** checks paired device list (permanent) not active connection or RSSI.
3. **IR hand detection** false-positives on static objects (cables, equipment) with motion <0.05.
4. **No bidirectional decay signals** — all reliable sensors are positive-only, so nothing actively drives the posterior DOWN when the operator leaves.

## Signal Inventory (from 2026-04-03 audit)

24 signal sources across 8 modalities. Current state:

| Signal | LR | Reliability | Issue |
|--------|-----|------------|-------|
| keyboard_active (logind) | 17x | BROKEN | Virtual input devices keep it True |
| desk_active (contact mic) | 18x | Good | Positive-only, goes idle when quiet |
| ir_hand_active | 8.5x | BROKEN | Static false positives, motion gate insufficient |
| operator_face (RGB) | 9x | Moderate | Positive-only, angle-dependent |
| watch_hr | 2.67x | Good | Positive-only, staleness = out of range |
| bt_phone_connected | 2.33x | BROKEN | Paired list ≠ proximity |
| room_occupancy (YOLO) | 4.25x | Good | Positive-only, 12s cadence |
| ir_person_detected | 9x | BROKEN | 30-frame training set |

## Fixes (Priority Order)

### Fix 1: Raw keyboard input via evdev (replaces logind)

Read directly from `/dev/input/event11` (Keychron Link physical keyboard), not logind. This bypasses virtual input devices entirely.

**Implementation:** New `evdev_input.py` backend:
- Open `/dev/input/event11` (Keychron) + `/dev/input/event4` (Logitech USB Receiver mouse)
- Track `last_real_keystroke_ts` and `last_real_mouse_ts`
- Provide `real_keyboard_active` (True if keystroke <5s ago) and `real_idle_seconds`
- Replace logind-based `input_active` in presence engine

**Device identification:** Match by name (`Keychron Keychron Link`) not by event number (can change across reboots). Use `evdev.list_devices()` + filter by name.

**Why this works:** The physical Keychron and Logitech receiver only generate events from actual human input. RustDesk UInput and mouce-library-fake-mouse are filtered out by device name.

### Fix 2: Watch HR staleness as absence signal (bidirectional)

Convert watch_hr from positive-only to **bidirectional with staleness decay**:
- HR data fresh (<30s): True (presence evidence, 2.67x)
- HR data stale 30-120s: None (neutral — watch may be syncing)
- HR data stale >120s: **False** (absence evidence — watch out of BLE range)

This is the first **bidirectional absence signal** that's actually reliable. If the watch can't send HR data for 2 minutes, the operator is physically far away.

**Current state:** Watch connection.json and heartrate.json are 215s stale. The watch IS sending data (heartrate 86bpm) — staleness is from the sync timer, not distance. Need to verify the staleness boundary by having operator walk away and timing when HR stops updating.

### Fix 3: Blue Yeti ambient energy as room presence

The Blue Yeti is always powered (USB). Its ambient noise floor changes with room occupancy:
- Occupied room: HVAC + keyboard clicks + chair creaks + breathing → RMS > 0.001
- Empty room: Pure HVAC → RMS < 0.0005
- Nobody home: Silence → RMS ≈ 0

**Implementation:** Capture Yeti via pw-cat (same as contact mic migration), compute RMS energy. Positive-only signal: energy above ambient baseline = presence evidence.

### Fix 4: IR brightness delta as body-heat proxy

IR brightness changes when a body is in the camera field:
- Body present: IR reflectance increases (skin reflects 850nm)
- Body absent: IR brightness drops to ambient

**Implementation:** Track `ir_brightness` delta over 30s window. Significant drop (>15 units) = body left. Significant rise = body arrived. This is a crude thermal proxy but available from all 3 Pi cameras.

### Fix 5: BLE RSSI proximity (requires re-pair or watch MAC)

If the Pixel Watch BLE MAC can be identified, scan for its RSSI during active BLE discovery:
- At desk: -40 to -55 dBm
- In room: -55 to -70 dBm
- Hallway: -70 to -85 dBm
- Gone: absent from scan

**Calibration protocol:** Operator sits at desk (baseline), moves to room center, hallway, then leaves. Record RSSI at each position. Set thresholds at midpoints.

**Blocking issue:** Need to identify watch BLE MAC. Current BT config only has Pixel 10 phone (classic, not BLE-advertising).

## Implementation Sequence

1. Fix 1 (evdev) — unblocks presence decay during CC sessions
2. Fix 2 (watch staleness) — first reliable bidirectional absence signal
3. Fix 3 (Yeti ambient) — room-level occupancy
4. Fix 4 (IR brightness) — body-heat proxy
5. Fix 5 (BLE RSSI) — precision proximity (blocked on watch MAC)

## Calibration Walk Protocol

After implementation, operator performs calibration walk:
1. Sit at desk 5 min (baseline: all signals active)
2. Stand in room center 2 min (keyboard/contact mic go idle, IR motion present)
3. Walk to hallway 2 min (IR motion absent, watch HR may stale)
4. Leave building 5 min (all signals decay)
5. Return (verify recovery time)

Record all signal values at each position. Set presence thresholds from data.

## Expected Outcome

| Location | Posterior | Primary signals |
|----------|-----------|----------------|
| At desk | >0.95 | keyboard + contact mic + watch HR |
| In room | 0.5-0.8 | watch HR + IR motion + room occupancy |
| Hallway | 0.2-0.5 | watch HR (staling) + phone KDE |
| Gone | <0.1 | all neutral/absent, prior decays |
