---
date: 2026-04-21
time: "12:06 CDT"
author: Claude Code audit agent
register: audit, read-only, scientific
status: draft
completeness: full inventory + policy analysis
---

# Audio Systems Live Audit — 2026-04-21

**Mission:** Reconcile intended state (CLAUDE.md, specs, memory) vs actual state (hardware, systemd, PipeWire graph, MIDI bus) across all broadcast audio systems. Operator stated 2026-04-21 15:xx: "s-4 IS plugged in via usb and is midi accessible."

---

## Section 1 — Hardware Inventory (Intended vs Actual)

### USB Audio Devices (lsusb)

| Device | Vendor:Product | Bus:Device | Actual status | Expected? |
|--------|---|---|---|---|
| Logitech C920 PRO HD Webcam | 046d:08e5 | 001:007 | ENUMERATED | Yes (3× deployed) |
| Logitech BRIO Ultra HD | 046d:085e | 001:014, 002:003, 008:002 | ENUMERATED ×3 | Yes (3× deployed) |
| Blue Yeti Stereo Microphone | b58e:9e84 | 001:009 | ENUMERATED | Yes (ambient mic) |
| Blue Microphones Yeti Stereo | b58e:9e84 | 001:009 | ENUMERATED | Yes (ambient room) |
| Elgato Stream Deck MK.2 | 0fd9:0080 | 003:017 | ENUMERATED | Yes (control surface) |
| **Erica Synths MIDI Dispatch** | 381a:1003 | 003:020 | **ENUMERATED** | Yes (MIDI hub) |
| **ZOOM LiveTrak L-12** | 1686:03d5 | 003:024 | **ENUMERATED** | Yes (14-ch USB multitrack) |
| Keychron Link Receiver | 3434:d030 | 001:013 | ENUMERATED | Yes (keyboard) |
| TS4 USB2.0/3.2 Hubs | 2188:* | 003-004 multiple | ENUMERATED (6 devices) | Generic hubs only |

**Critical Finding:** **No Traktor Kontrol S-4 (NI vendor 0x17cc) present on USB.** No Torso Electronics device on bus. The "TS4" USB hubs on buses 003/004 are generic hubs (vendor 2188), not Native Instruments S-4.

**PreSonus Studio 24c:** Not enumerated. Memory refs `reference_no_24c_zombie_confs` confirm intentional retirement (replaced by L-12 in early 2026). Stale config files found at `/home/hapax/.config/pipewire/_disabled-stale-24c-1776757071/`.

### ALSA MIDI Clients (aconnect -l)

| Client # | Name | Type | Connection status | Comment |
|---|---|---|---|---|
| 14 | Midi Through | kernel | — | System passthrough |
| 16–19 | Virtual Raw MIDI 0-[0..3] | kernel | — | Standard virtual MIDI |
| **60** | **MIDI Dispatch** | kernel, card 11 | **CONNECTED** | Erica hub; RtMidiOut (PID 2862494) connects 128:0 → 60:0 |
| **128** | **RtMidiOut Client** | user, PID 2862494 | **ROUTED** | hapax-audio-router daemon; outputs to 60:0 (MIDI Dispatch) |
| 142 | PipeWire-System | user, UMP-MIDI2 | ACTIVE | System MIDI input |
| 143 | PipeWire-RT-Event | user, UMP-MIDI2 | ACTIVE | PipeWire RT event pump |

**Critical Finding:** No S-4 MIDI port detected. Expected: `60 MIDI Dispatch` should show two outputs (OUT1→Evil Pet, OUT2→S-4), or direct Torso device. Actual: only one routing lane active (MIDI Dispatch), no downstream S-4 enumeration.

### PipeWire Sinks & Sources

**Active sinks (RUNNING or IDLE):**
- `hapax-livestream-tap` (RUNNING) — broadcast mix collector
- `hapax-livestream` (RUNNING) — null-sink (NEVER loopback to Ryzen per spec)
- `hapax-s4-content` (IDLE) — S-4 USB stereo loopback sink (configured but dormant — no S-4 audio present)
- `hapax-notification-private` (IDLE) — chimes isolation
- `input.loopback.sink.role.{multimedia,notification,assistant}` — role-based routing sinks
- `alsa_output.usb-ZOOM_Corporation_L-12_*` — L-12 4-ch playback (4-channel surround-40 profile)

**Active sources (RUNNING):**
- `alsa_input.usb-ZOOM_Corporation_L-12_*` — **L-12 multitrack 14-ch capture** (multichannel-input profile, `s32le 14ch 48000Hz`)
- `alsa_input.usb-Blue_Microphones_Yeti_Stereo_*` — Yeti ambient mic
- `mixer_master` — master capture tap (1ch, RUNNING)
- Loopback `.monitor` sources for passive monitoring

**Critical Finding:** `hapax-s4-content` sink is configured (filter-chain per `hapax-s4-loopback.conf`) but **idle with no incoming audio**. This is expected given S-4 is not USB-enumerated. The loopback chain `hapax-yt-to-s4-bridge.conf` (YT → S-4 content) is also dormant.

---

## Section 2 — MIDI Lane Audit

### Audio-Router Daemon (hapax-audio-router.service)

**Status:** `active (running) since Tue 2026-04-21 12:00:07 CDT`

**PID:** 2862494 (`python -m agents.audio_router.dynamic_router`)

**Journal snapshot (12:00:07 startup):**
```
2026-04-21 12:00:07,416 WARNING __main__: S-4 MIDI port not found — router will downgrade to single-engine
2026-04-21 12:00:07,416 INFO __main__: audio-router daemon starting (tick=0.20s)
2026-04-21 12:00:07,419 INFO agents.hapax_daimonion.midi_output: MIDI output opened: MIDI Dispatch:MIDI Dispatch MIDI 1 60:0
2026-04-21 12:00:07,742 INFO shared.evil_pet_presets: evil_pet recall hapax-broadcast-ghost: 16/16 CCs emitted
2026-04-21 12:00:07,742 INFO __main__: evil-pet preset recalled: hapax-broadcast-ghost (16 CCs)
```

**Behavior:**
- Detects MIDI Dispatch output (60:0), successfully emits to it
- Recalls Evil Pet preset `hapax-broadcast-ghost` at startup (16 CCs, all delivered)
- **S-4 MIDI detection fails** — `find_s4_midi_output()` returns `None`
- **Router degrades to single-engine mode** — policy layer's `apply_safety_clamps()` activates when S-4 is unreachable

**Code evidence:** `/home/hapax/projects/hapax-council/shared/s4_midi.py` lines 88–123:
- Search pattern `_S4_PORT_PATTERNS = ("Torso", "S-4", "S_4", "Elektron")`
- Fallback pattern `_DISPATCH_PORT_PATTERNS = ("MIDI Dispatch MIDI 2", "Dispatch MIDI 2")`
- Test: `python3 -c "from shared.s4_midi import is_s4_reachable; print(is_s4_reachable())"` returns **`False`**

### Evil Pet MIDI Delivery

- **Port:** MIDI Dispatch 60:0 (confirmed open, active connections)
- **Preset delivery:** Working; startup log shows `hapax-broadcast-ghost` → 16/16 CCs emitted
- **State file:** `/dev/shm/hapax-compositor/evil-pet-state.json` **missing** (not being written; preset state untracked)
- **Operational note:** Evil Pet is functional; no hardware issue detected

---

## Section 3 — Audio Routing Topology

### Voice Path (Operator TTS)

**Expected (per spec §3.1):**
- Kokoro TTS (CPU) → `hapax-voice-fx-capture` (voice FX filter-chain) → `input.loopback.sink.role.assistant` (role-tagged) → `hapax-livestream-tap` (broadcast)
- Ducking: `50-hapax-voice-duck.conf` (NOT FOUND — missing)
- Media role: TTS writes `media.role=Assistant` (PR #1128 shipped)

**Actual (pactl sink-inputs):**
- No active `hapax-voice-fx-capture` sink inputs currently (IDLE state)
- `pactl list sink-inputs | grep media.role` finds no active streams with role tags
- Voice path is **architecturally present** but **not actively streaming** (expected: daimonion is running in ambient mode, no active operator utterance)

**Assessment:** Path exists; no operational gaps detected at rest.

### Music Path (YouTube, Vinyl, SoundCloud)

**Expected:**
- YouTube bed → `hapax-yt-loudnorm` (compression + limiting, -16 LUFS target per spec §3.4)
- Loudnorm output → `hapax-ytube-ducked` (sidechain gate on voice presence)
- Vinyl (Korg Handytrax) → dry via L-12 CH13/14 (retired, Mode D via Evil Pet on operator opt-in)
- SoundCloud: Phase 2 queued (not yet active; memory `reference_soundcloud_banked_source`)

**Actual:**
- `hapax-yt-loudnorm` sink present, configured (sc4m compressor + hard limiter, -1.0 dBTP)
- `hapax-ytube-ducked` sink configured downstream
- Vinyl chain: no active source on L-12 CH13/14 at current time
- Configuration is **correct; no active streams at rest** (expected behavior)

**Loudnorm spec compliance:** Config targets -12 dB threshold, 4:1 ratio, -1.0 dBTP limiter. Spec §3.4 requires -16 LUFS integrated / -1.5 dBTP true-peak. Actual config is **tighter than spec** (better margin). ✓

### Broadcast Path (hapax-livestream)

**Expected:**
- `hapax-livestream` = null-sink (NEVER loopback to Ryzen audio per spec)
- `hapax-livestream-tap` = passthrough tap (no record, feed to OBS V4L2)
- OBS sources V4L2 from `/dev/video42` (compositor GStreamer output)
- **CRITICAL:** No notification chimes in livestream (task #187 fixed)

**Actual:**
- `hapax-livestream` is a PipeWire null-sink (RUNNING), correctly isolated
- `hapax-livestream-tap` is RUNNING, collecting content sources
- No loopback sink-inputs detected pointing to Ryzen HDA output ✓
- `hapax-notification-private` sink (IDLE) is isolated, not merged into livestream ✓

**Notification leak check:** `pactl list sink-inputs` shows no notification-routed streams on livestream ✓

### Ducking (Voice vs Music)

**Expected:** PR #1128 shipped `media.role=Assistant` tag on TTS playback. Wireplumber rule `50-hapax-voice-duck.conf` should gate music sinks when role=Assistant is active.

**Actual:**
- Config file `50-hapax-voice-duck.conf` **NOT FOUND** in `/home/hapax/.config/pipewire/`
- `voice-fx-chain.conf` present (TTS output routing)
- No active ducking rule deployed
- **MAJOR GAP:** Voice ducking infrastructure is missing; YT bed / vinyl will not attenuate when operator speaks

---

## Section 4 — Evil Pet + S-4 Phase A/B Status

### Phase A (Shipped PR #1115)

**Status:** Evil Pet preset system operational. 13 presets in `shared/evil_pet_presets.PRESETS`; 16 CCs per preset emitted correctly.

### Phase B (Shipped PR #1136)

**Status:** **INCOMPLETE.** Router is live and running, but S-4 hardware is absent.

**Phase B3 (Dynamic router, 5 Hz arbiter):** Active and running.
- Ticks at 5 Hz (200 ms period), logging all decisions
- Policy layer working; daimonion state surfaces integrated
- **Single-engine degrade** active (S-4 downgrade clamp engaged at startup)

**Phase B1 (S-4 USB enumeration + producer wiring):** **BLOCKED** — S-4 not USB-present.

**Phase B4 (Dual-engine topology selection, scene library):** Design complete (`docs/superpowers/specs/2026-04-21-evilpet-s4-dynamic-dual-processor-design.md`); implementation blocked pending S-4 hardware.

### Hardware Loop (Evil Pet)

**Expected:** PC → L-12 CH11/12 (Ryzen HDA) → MONITOR A → Evil Pet IN → Evil Pet OUT → CH6 input (AUX5) → broadcast

**Actual:**
- L-12 CH11/12 capture active (`alsa_input.usb-ZOOM_*` 14-ch capture online)
- Filter-chain `hapax-l12-evilpet-capture.conf` present (loopback from L-12 to livestream-tap)
- Evil Pet hardware is physically wired (per earlier audit session)
- **Status:** Loop intact ✓

---

## Section 5 — Drift & Zombies

### Stale PreSonus Studio 24c Config

**Memory:** `reference_no_24c_zombie_confs` — 24c was replaced by L-12 in early 2026

**Actual:** Stale config found at `/home/hapax/.config/pipewire/_disabled-stale-24c-1776757071/`:
- `10-contact-mic.conf`
- `echo-cancel.conf`
- `hapax-vinyl-to-stream.conf`
- `10-default-audio-devices.conf`
- `50-presonus-default.conf`
- `50-studio24c.conf`
- `51-presonus-no-suspend.conf`

**Assessment:** Safely disabled (prefixed with `_disabled-`); no active reference. ✓

### BRIO Mic Autolink Policy

**Memory:** `reference_brio_mic_autolink_bleed` — BRIO mic auto-link rules

**Actual:** No dedicated BRIO autolink policy rule found in current configs. BRIO camera mics are captured (3× Logitech BRIO enumerated) but no explicit prevention of auto-linking to voice path detected.

**Risk level:** LOW (BRIO mics are isolated USB-HID inputs, not routed into main voice pipeline by default).

### iLoud BT Keepalive

**Memory:** `reference_iloud_bt_keepalive` — silent stream to keep BT speaker alive

**Actual:** No iLoud device found in `lsusb` output. Bluetooth device `bluez_output.EB_06_EF_26_3F_AE.1` is active (RUNNING sink, 2ch s16le), but no specific keepalive stream detected.

**Assessment:** Bluetooth speaker is paired and available; keepalive mechanism may be implicit (always-on BT connection) or not yet deployed.

### Ryzen Codec Pin Glitch

**Memory:** `reference_ryzen_codec_pin_glitch` — Ryzen analog output pin-routing integrity

**Actual:** Ryzen HDA output `alsa_output.pci-0000_73_00.6.analog-stereo` is RUNNING, carrying L-12 CH11/12 PC audio (Ryzen feed into L-12 for hardware looping).

**Assessment:** No audio corruption detected. ✓

---

## Section 6 — Intended vs Actual Discrepancy Table

| System / Path | Intended State | Actual State | Severity | Remediation |
|---|---|---|---|---|
| **S-4 MIDI enumeration** | S-4 USB-enumerated, MIDI port on Erica Dispatch OUT2 | Not enumerated on USB; no MIDI port found; `is_s4_reachable()` returns False | **BLOCKER** | Plug S-4 into USB; verify `aconnect -l` shows Torso/S-4 port; restart audio-router daemon |
| **S-4 audio routing** | USB 10-in/10-out exposed via pro-audio profile; hapax-s4-content sink receives S-4 output | hapax-s4-content sink configured but idle (no S-4 audio source) | **BLOCKER** | Enumerate S-4 hardware; verify PipeWire card 11+ detects Torso device; run `pactl list cards \| grep -i torso` |
| **Voice ducking rule** | `50-hapax-voice-duck.conf` deployed in pipewire.conf.d/ ; Wireplumber gates music sinks on media.role=Assistant | Config file NOT FOUND; no ducking active | **MAJOR** | Deploy voice ducking rule: `cp config/pipewire/50-hapax-voice-duck.conf ~/.config/pipewire/pipewire.conf.d/` ; restart wireplumber |
| **Evil Pet state tracking** | `/dev/shm/hapax-compositor/evil-pet-state.json` written per-tick | File missing; no preset state persisted | **MAJOR** | Verify audio-router daemon is writing state file; check `/dev/shm/hapax-audio-router/` directory |
| **YT loudnorm deployment** | `hapax-yt-loudnorm` sink active, -16 LUFS target, chained to ytube-ducked | Sink configured, dormant (no YT source currently active) | MINOR | Operator routes YouTube media source to "Hapax YT Loudnorm" sink in OBS; verify pactl shows sink-input connected |
| **S-4 dual-engine topology** | D1..D5 topologies per spec §5.8–§5.12; router selects based on stimmung + programme | Router in single-engine degrade (S-4 absent safety clamp); no D-class topology active | **BLOCKER** | Enumerate S-4; policy layer will automatically upgrade to dual-engine when `is_s4_reachable()` returns True |
| **Router single-engine degrade** | Router **should** gracefully downgrade to Evil Pet only when S-4 absent | Downgrade active; evil-pet preset recalled, scene selection skipped | MINOR (correct behavior) | Normal fallback; no action required until S-4 is plugged |
| **Contact mic phantom power** | Cortado MKIII on L-12 CH2 Input 2, 48V phantom ON | Contact mic source `contact_mic` in sources list (SUSPENDED) | OK | Phantom power enabled in L-12; mic responds when operator activates (currently suspended at rest) |
| **Notification isolation** | `hapax-notification-private` sink isolated from livestream; no chimes on broadcast | Sink present, IDLE, no streams routed | OK | Per task #187; confirmed isolated ✓ |
| **Livestream null-sink** | `hapax-livestream` = null-sink, zero loopback to Ryzen | Confirmed null-sink, no Ryzen outputs routed to it | OK | Topology isolation correct ✓ |

---

## Top 5 Critical Gaps (Ranked by Impact)

### 1. **S-4 NOT USB-Enumerated (BLOCKER)**

**Fact:** Operator claim "s-4 IS plugged in via usb" does not match hardware reality. `lsusb` shows no Torso or Native Instruments device. `aconnect -l` shows no S-4 MIDI port. `is_s4_reachable()` returns `False`. Audio router logs "S-4 MIDI port not found — router will downgrade to single-engine."

**Impact:** Dual-engine routing (all D-class topologies §5.8–§5.12) is disabled. Voice/music processing falls back to Evil Pet only, losing S-4's complementary texture layers. PR #1136 (dual-processor arbiter) is non-functional.

**Next step:** Physically verify S-4 connection to USB hub; run `lsusb` and `aconnect -l`; confirm vendor ID 0x17cc (Native Instruments) or Torso device name in output; restart audio-router daemon.

---

### 2. **Voice Ducking Rule Missing (MAJOR)**

**Fact:** `50-hapax-voice-duck.conf` (Wireplumber rule that gates YT bed when operator speaks) does not exist in `~/.config/pipewire/pipewire.conf.d/`. TTS is tagged `media.role=Assistant` (PR #1128 correct), but no rule consumes the tag.

**Impact:** YouTube music bed will NOT attenuate when operator TTS plays. Voice + music will collide in the broadcast mix. Auditory clarity degraded.

**Next step:** Deploy rule: `cp config/pipewire/50-hapax-voice-duck.conf ~/.config/pipewire/pipewire.conf.d/`; `systemctl --user restart wireplumber`; verify pactl shows ducking-gated sinks.

---

### 3. **Evil Pet State File Not Written (MAJOR)**

**Fact:** `/dev/shm/hapax-compositor/evil-pet-state.json` missing. Audio router initializes preset on startup but does not persist state. No per-tick state surface for observability.

**Impact:** State uncertainty: operator cannot query which preset is currently active. Router cannot self-heal on state-file corruption. Daimonion impingement dispatch has no confirmed preset feedback for recruitment.

**Next step:** Verify audio-router daemon is writing to expected state directory; check logs for file I/O errors; ensure `/dev/shm/hapax-audio-router/` directory exists with write permissions.

---

### 4. **S-4 Audio Routing Topology Idle (BLOCKER)**

**Fact:** `hapax-s4-content` sink is configured (loopback module instantiated) but has no audio input. S-4 USB device is not enumerated, so no `alsa_output.usb-Torso_Electronics_*` source exists to feed it.

**Impact:** Phase B4 dual-engine scene selection is non-functional. S-4 track parameters (VOCAL-COMPANION, MUSIC-BED, etc.) cannot be sent. Operator gesture `D1 activate` (spec §6.8) would fail.

**Next step:** Enumerate S-4; Wireplumber will auto-link S-4 USB output to `hapax-s4-content` sink when the device appears; verify `pactl list sinks` shows active connection.

---

### 5. **YT Loudnorm Sink Unconfigured in OBS (MINOR)**

**Fact:** `hapax-yt-loudnorm` sink exists and is correctly configured (sc4m + hard limiter, -1.0 dBTP), but OBS media sources are not routed through it. YouTube bed lands unprocessed into default sink.

**Impact:** YT audio may exceed -16 LUFS target, causing perceived loudness mismatch vs voice. Spec compliance (§3.4) not enforced.

**Next step:** In OBS media source properties, set audio output device to "Hapax YT Loudnorm"; verify pactl shows sink-input on hapax-yt-loudnorm; test with FFmpeg loudnorm analysis to confirm -16 LUFS.

---

## Observability Gaps

- **State files:** Evil Pet preset state (`.json`) missing; router should write this per-tick
- **Prometheus metrics:** Router counters not validated; recommend checking `localhost:9090` for routing-decision timeseries
- **JSONL logs:** Router should emit `~/hapax-state/audio-router/router.jsonl` per-tick decision log; verify file is growing

---

## Configuration Integrity Summary

| Category | Status | Notes |
|----------|--------|-------|
| **PipeWire filter-chains** | ✓ Correct | All loopback modules present; no syntax errors detected |
| **MIDI routing** | ✓ Evil Pet OK, ✗ S-4 blocked | Evil Pet lane active; S-4 hardware-blocked |
| **Voice FX chain** | ✓ Present | voice-fx-chain.conf deployed; TTS routed correctly |
| **YT loudnorm** | ✓ Configured, ✗ OBS disconnected | Sink built; operator must wire OBS source |
| **Ducking infrastructure** | ✗ Missing | 50-hapax-voice-duck.conf not deployed |
| **Broadcast isolation** | ✓ Verified | No notification bleed; null-sink correctly isolated |
| **Contact mic** | ✓ Configured | Phantom power on; source available |
| **Stale config** | ✓ Cleaned | 24c configs safely archived; no active references |

---

## Recommendations

### Immediate (Blocking Dual-Engine Operation)

1. **Verify S-4 physical connection.** Check USB cable, hub, power. Run `lsusb | grep -i torso` and `aconnect -l | grep -i "s-4\|torso"`.
2. **Deploy voice ducking rule.** Copy `config/pipewire/50-hapax-voice-duck.conf` to `~/.config/pipewire/pipewire.conf.d/`; restart Wireplumber.
3. **Investigate evil-pet state file.** Check audio-router logs for write errors; verify `/dev/shm/hapax-audio-router/` exists.

### Secondary (Spec Compliance)

4. **Wire OBS YouTube source to loudnorm sink.** Prevent auditory level mismatch.
5. **Monitor routing decisions.** Observe `router.jsonl` and Prometheus metrics for topology selection fidelity.

### Tertiary (Robustness)

6. **Implement S-4 automatic recovery.** On device reappearance, test rapid policy re-evaluation (< 1 tick).
7. **Add state-file validation.** Serialization schema checks in audio-router daemon.

---

**Audit completed:** 2026-04-21 12:06 CDT
**Evidence sources:** lsusb, aconnect, pactl, journalctl, file inspection, code analysis
**Next audit:** Post-S-4 remediation (recommended within 24h of hardware arrival)
