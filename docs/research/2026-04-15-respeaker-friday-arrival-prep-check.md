# ReSpeaker Friday arrival prep verification

**Date:** 2026-04-15
**Author:** beta (queue #216, identity verified via `hapax-whoami`)
**Scope:** verify that pre-staged scaffolding on `beta-phase-4-bootstrap` is ready to receive the ReSpeaker USB Mic Array v2.0 arriving Friday 2026-04-17 without additional setup work. Checks 6 items per queue spec + flags gaps as operator-facing action items.
**Branch:** `beta-phase-4-bootstrap`

---

## 0. Summary

**Verdict: MOSTLY READY with 2 blockers + 1 integration gap.** Pre-staging covers the Pi-side hardware setup completely (udev, PipeWire, systemd units, verification script). Two pre-existing blockers flagged by epsilon's 16:21Z inflection remain open (libroc not in Debian Bookworm repos + hapax-ai currently has no Hailo HAT physically installed). One integration gap: the daimonion audio backend does NOT yet consume the room-vad SHM signal that the Pi will publish.

## 1. Pre-staging inventory (6 check items)

### Check 1 — systemd unit drop-ins for ReSpeaker audio capture ✓ PRESENT

Location: `pi-edge/hapax-ai/`

- **`hapax-room-vad.service`** — Silero VAD on ReSpeaker DSP output (ch0 post-XVF-3000 AEC+beamforming+noise-suppression). Publishes 1 Hz SHM signal to `/dev/shm/hapax-ai/room-vad.json`. Tentative LR for presence engine: 3.0 (positive-only, matches contact mic + ir_hand_active pattern).
- **`hapax-ai-asr.service`** — Whisper streaming ASR consuming operator voice-back via roc-source from workstation (Yeti post-AEC). Depends on Hailo encoder offload for ~250ms latency target.
- **`hapax-ai-coprocessor.service`** — shell service for other Hailo workloads (face identity, pose tracking, hand tracking).
- **`hapax-ai.env`** — env template with SHM paths + thresholds.
- **`README.md`** — unit catalog + activation notes.

All 4 units are `enable --now`-ready but DISABLED pre-arrival (correct state; missing `/dev/hailo0` would ExecStartPre-fail if enabled).

### Check 2 — PipeWire config for ReSpeaker routing ✓ PRESENT

Location: `config/pipewire/respeaker-room-mic.conf`

- Pins ReSpeaker as default capture via `/dev/respeaker-mic-array` (via udev symlink from Check 3)
- Publishes cleaned 1-channel DSP output to LAN via `libpipewire-module-roc-sink`
- Target: workstation at 192.168.68.80, data port 10001, FEC repair port 10002, RS8M FEC code
- Optional RNNoise filter chain (XVF-3000 already does AEC+beamforming+noise-suppression; RNNoise is belt-and-suspenders)
- Also has `module-roc-source` for workstation → Pi voice-back routing (Yeti post-AEC → hapax-ai-asr)

Install path (documented in header): `~/.config/pipewire/pipewire.conf.d/51-respeaker.conf` on the Pi.

### Check 3 — udev rules for ReSpeaker USB device identification ✓ PRESENT

Location: `scripts/pi-fleet/respeaker-udev.rules`

- VID:PID `2886:0018` (Seeed, XMOS XVF-3000)
- Creates `/dev/respeaker-mic-array` symlink (raw USB device)
- Creates `/dev/respeaker-pcm` symlink (PCM subdevice for capture apps)
- GROUP=audio, MODE=0660, `uaccess` tag
- Install instructions embedded in the file header:
  ```
  sudo cp respeaker-udev.rules /etc/udev/rules.d/99-respeaker.rules
  sudo udevadm control --reload
  sudo udevadm trigger
  ```

### Check 4 — Pre-flash scripts for the intended deployment Pi ✓ PRESENT (but for Thursday, not Friday)

Location: `scripts/pi-fleet/pi5-first-boot.yaml` + `scripts/pi-fleet/dhcp-reservation-notes.md` + `scripts/pi-fleet/rename-runbook.sh`

- **`pi5-first-boot.yaml`** — Raspberry Pi Imager userconfig for the `hapax-ai` host (Pi 5, 8 GB). Hostname, SSH pre-auth, first-boot apt list (hailo-all, pipewire-module-roc-*, rnnoise, node-exporter), `/boot/firmware/config.txt` additions for PCIe Gen3 + cooling fan. **This was used for THURSDAY arrival (Pi 5 first boot), NOT Friday.** The Pi 5 is already booted per epsilon's 16:21Z provisioning inflection.
- **`dhcp-reservation-notes.md`** — router reservation instructions: .79 for hapax-ai, lock hapax-hub at .81.
- **`rename-runbook.sh`** — parametrized hostnamectl + /etc/hostname + /etc/hosts + avahi restart. Dry-run by default; `--execute` + `--pi <N>` to flip. For the weekend rename window — not Friday.

**ReSpeaker is a plug-and-play USB device; no pre-flash work is needed for Friday.** The check 4 items above are for the Pi 5 boot (Thursday) and weekend rename (not this Friday). Not a gap — just scope clarification.

### Check 5 — Integration with hapax_daimonion audio backend ⚠ GAP

**Pre-staging publishes** the room-vad signal at `/dev/shm/hapax-ai/room-vad.json` at 1 Hz (per `hapax-room-vad.service` environment variables).

**Daimonion backend does NOT yet consume** this signal. Grep of `agents/hapax_daimonion/` for `room-vad`, `HAPAX_ROOM_VAD`, or `/dev/shm/hapax-ai/` returns **zero hits**. Neither a backend nor a presence engine signal entry.

**Implication:** on Friday after the ReSpeaker is plugged in, the Pi will start publishing room-vad signals at 1 Hz, but the workstation's daimonion won't read them. No crash, no error — the signal will just sit in SHM unconsumed.

**Recommended fix:** add a `room_vad` backend to `agents/hapax_daimonion/backends/` following the existing `ir_presence.py` pattern:

- `room_vad.py` → `RoomVadBackend` class
- Reads `/dev/shm/hapax-ai/room-vad.json` (with staleness cutoff ~10s)
- Publishes `room_voice_active` signal to the `Behaviors` dict
- `init_backends.py` wires it in alongside the existing 21 backends
- `presence_engine.py::DEFAULT_SIGNAL_WEIGHTS` adds `room_voice_active: (0.70, 0.15)` → LR ~4.67 (tentative; calibrate from live data after a week of signal flow)

**Estimated size:** ~60 LOC backend + ~20 LOC signal entry + ~30 LOC test. ~45 min.

**Proposed follow-up queue item #220 (or similar):**

```yaml
id: "220"
title: "Wire room_vad signal from hapax-ai into daimonion presence engine"
assigned_to: beta  # or alpha
status: offered
priority: low
depends_on: []
description: |
  ReSpeaker Friday arrival prep check (queue #216) flagged an
  integration gap: /dev/shm/hapax-ai/room-vad.json will be published
  by hapax-room-vad.service on the Pi but no daimonion backend
  consumes it. Wire a RoomVadBackend following the ir_presence.py
  pattern + add room_voice_active signal to presence_engine.py with
  tentative LR 4.67 (calibrate later).
size_estimate: "~110 LOC across 3 files, ~45 min"
```

Note: this doesn't need to ship BEFORE Friday — the Pi can publish signals without a consumer. The consumer can be wired afterward without any urgency. Low priority.

### Check 6 — Council CLAUDE.md § IR Perception documents the plan ✓ PRESENT

Council CLAUDE.md lines 215-224 (§IR Perception + wider Pi fleet):

> *"5 Raspberry Pi 4s online (3 IR + sentinel + rag + hub, verified live 2026-04-15); 1 additional Raspberry Pi 5 arriving 2026-04-16 as `hapax-ai` (Hailo AI coprocessor + ReSpeaker audio ingest)."*

And specifically for ReSpeaker:

> *"ReSpeaker USB Mic Array v2.0 arriving Friday 2026-04-17 plugs into the same Pi for room ambient capture → Silero VAD → PipeWire ROC stream to workstation. Unblocks LRR Phase 6 §6 presence-detect-without-contract per-person identity, Phase 8 §11 environmental perception emphasis, Phase 9 §4 daimonion code-narration. Systemd user units + env template at `pi-edge/hapax-ai/`; PipeWire drop-in at `config/pipewire/respeaker-room-mic.conf`; first-boot + rename + verify scripts at `scripts/pi-fleet/`."*

**Cross-references are accurate:** `pi-edge/hapax-ai/` ✓, `config/pipewire/respeaker-room-mic.conf` ✓, `scripts/pi-fleet/` ✓ (all verified present in this audit).

## 2. Pre-existing blockers (from epsilon's 16:21Z inflection)

### Blocker 1: libroc not in Debian Bookworm repos

Per epsilon's 2026-04-15T16:21Z inflection §"Deferred":

> *"libroc unavailable in Debian Bookworm repos — only `librocksdb` and `librocm-smi` match `libroc*`. Friday ROC audio streaming (the whole `module-roc-sink`/`module-roc-source` approach I specced) will need source-build from `roc-streaming/roc-toolkit` or an alternative network audio transport. Flagging this now so it doesn't surprise us Friday."*

**Impact:** Check 2's PipeWire config references `libpipewire-module-roc-sink` and `libpipewire-module-roc-source`. If libroc isn't installed (because the Bookworm package doesn't exist), these modules won't load and the ReSpeaker stream won't reach the workstation.

**Options:**

- **Option A (recommended):** source-build `roc-streaming/roc-toolkit` on hapax-ai before Friday afternoon. ~30 min compile + install.
- **Option B:** swap ROC for RTSP via `rtsp-server` or similar. Different architecture; PipeWire config would need rewriting.
- **Option C:** fall back to wired USB capture through a USB-over-IP bridge. Non-starter; latency too high.

**Beta's preference:** Option A. Epsilon flagged it early specifically to allow a source build window.

**Proposed follow-up:** queue item for epsilon OR a proxy session to source-build roc-toolkit on hapax-ai before Friday. ~30 min. Should happen Thursday afternoon or Friday morning.

### Blocker 2: Hailo HAT not yet installed

Per epsilon's 16:21Z inflection: *"Hailo AI HAT+: not in hand yet — provisioning excluded all Hailo-specific steps"*.

**Impact:** the `hapax-ai-asr.service` targets `~250ms latency` via Hailo encoder offload. Without Hailo, Whisper runs on CPU — likely 1-2 seconds latency instead. The ReSpeaker Friday plug-in will still work for the room-vad signal (Silero VAD on the Pi CPU is fast enough), but the ASR portion will be degraded until Hailo arrives.

**Not a Friday-blocker for room-vad scope.** The room-vad backend (Check 1 unit `hapax-room-vad.service`) doesn't need Hailo. Only the ASR path does.

**Operator action:** operator already knows per epsilon's inflection; no additional prep beyond waiting for Hailo HAT delivery.

## 3. Friday morning setup runbook

Per queue spec "Operator-facing 'Friday morning setup' runbook appendix":

### Step 1 — Pre-arrival verification (Thursday evening, optional)

On workstation:

```bash
# Verify pre-staging files exist
ls pi-edge/hapax-ai/
ls config/pipewire/respeaker-room-mic.conf
ls scripts/pi-fleet/respeaker-udev.rules
ls scripts/pi-fleet/respeaker-verify.sh
```

On hapax-ai:

```bash
# Verify libroc is installed or build it
dpkg -l | grep libroc || {
  echo "libroc not installed — source build required"
  # Follow Blocker 1 Option A
}
```

### Step 2 — ReSpeaker physical install (Friday AM)

1. Unbox ReSpeaker USB Mic Array v2.0
2. Plug into a USB 3.0 port on hapax-ai (avoid USB 2.0 — XVF-3000 DSP benefits from USB 3.0 bandwidth even though the endpoint is USB 2.0 class)
3. Wait ~5 seconds for USB enumeration

### Step 3 — Install udev rules + PipeWire config

On hapax-ai (via ssh):

```bash
# Copy udev rules
scp scripts/pi-fleet/respeaker-udev.rules hapax@hapax-ai.local:/tmp/
ssh hapax@hapax-ai.local 'sudo cp /tmp/respeaker-udev.rules /etc/udev/rules.d/99-respeaker.rules && sudo udevadm control --reload && sudo udevadm trigger'

# Copy PipeWire config
scp config/pipewire/respeaker-room-mic.conf hapax@hapax-ai.local:~/.config/pipewire/pipewire.conf.d/51-respeaker.conf
ssh hapax@hapax-ai.local 'systemctl --user restart pipewire wireplumber'
```

### Step 4 — Run verification script

```bash
ssh hapax@hapax-ai.local 'bash ~/hapax-council/scripts/pi-fleet/respeaker-verify.sh'
```

Expected output:
- OK: ReSpeaker visible on USB bus (lsusb 2886:0018)
- OK: /dev/respeaker-mic-array symlink present
- OK: ALSA sees the ReSpeaker capture device
- OK: PipeWire sees the ReSpeaker source
- OK: captured N bytes to /tmp/*.wav
- Peak amplitude: ~0.01..0.5 (expected range)

### Step 5 — Enable hapax-room-vad.service

```bash
ssh hapax@hapax-ai.local 'systemctl --user enable --now hapax-room-vad.service'
ssh hapax@hapax-ai.local 'systemctl --user status hapax-room-vad.service'
```

Expected: Active (running). First SHM write at `/dev/shm/hapax-ai/room-vad.json` within ~1 second.

### Step 6 — Verify roc-sink stream reaches workstation

On workstation:

```bash
# Should see a roc-source capture source when the Pi's roc-sink is streaming
pactl list sources short | grep -i roc
```

Expected: a source named `roc-source.room-respeaker` (or similar) appears. Capture it briefly to confirm:

```bash
pw-record --target 'roc-source.room-respeaker' --format s16 --rate 16000 --channels 1 /tmp/respeaker-workstation-test.wav &
sleep 3
kill $!
sox /tmp/respeaker-workstation-test.wav -n stat  # peak amplitude check
```

### Step 7 — (deferred post-Friday) Wire daimonion backend

See §1 Check 5 gap. Room-vad signal will be flowing at 1 Hz but not yet consumed. File queue item #220 for wiring. Non-urgent.

## 4. Summary matrix

| Check | Status | Notes |
|---|---|---|
| 1. systemd unit drop-ins | ✓ | 4 units at `pi-edge/hapax-ai/` |
| 2. PipeWire config | ✓ | `config/pipewire/respeaker-room-mic.conf`, depends on libroc |
| 3. udev rules | ✓ | `scripts/pi-fleet/respeaker-udev.rules` |
| 4. Pre-flash scripts | ~ | Not applicable — ReSpeaker is plug-and-play; pre-flash was for Thursday Pi 5 first boot |
| 5. Daimonion backend integration | ⚠ GAP | No `room_vad` backend yet; flag #220 |
| 6. CLAUDE.md documentation | ✓ | Lines 215-224 of council CLAUDE.md |
| **Blocker 1: libroc** | ⚠ | Not in Bookworm repos; source build required |
| **Blocker 2: Hailo HAT** | ⚠ | Not on Pi yet; ASR path degraded; room-vad path unaffected |

**Net verdict:** READY for the ReSpeaker plug-in on Friday morning. Blocker 1 (libroc) needs operator action Thursday evening or Friday morning before enabling PipeWire ROC modules. Blocker 2 (Hailo) is pre-existing and not a Friday-specific concern. Integration gap (Check 5) can be wired post-Friday without blocking the ReSpeaker deployment.

## 5. Operator action items

### Thursday evening (before Friday)

1. **Source-build roc-toolkit on hapax-ai** (Blocker 1 mitigation). See epsilon's 16:21Z inflection §"Deferred" for rationale. ~30 min. OR accept Option B (RTSP fallback) if ROC is too much hassle.

### Friday morning (ReSpeaker arrival)

2. Run Step 2 — Step 6 from §3 in sequence
3. Report any deviation from "expected" output via an inflection
4. Leave room-vad SHM signal publishing even if daimonion doesn't consume yet (harmless)

### Post-Friday (non-urgent)

5. File queue item #220 for wiring room_vad backend into daimonion presence engine
6. Evaluate Hailo HAT delivery status (no Friday impact)

## 6. Cross-references

- Epsilon's Pi fleet provisioning inflection — `20260415-162117-epsilon-alpha-hapax-ai-live.md`
- Alpha's hapax-ai ratification inflection — `20260415-170500-alpha-epsilon-plus-delta-hapax-ai-ratification.md`
- Beta's queue #206 PresenceEngine calibration audit — `docs/research/2026-04-15-presence-engine-signal-calibration-audit.md` (commit `cbd0264dc`) — for context on signal-adding protocol
- Beta's queue #215 hapax-whoami edge case — `docs/research/2026-04-15-hapax-whoami-edge-case-verification.md` (commit `7b77e5ad3`) — preceding beta queue item
- Council CLAUDE.md § IR Perception (Pi NoIR Edge Fleet) + wider Pi fleet (lines 215-224)
- Queue item spec: queue/`216-beta-respeaker-friday-arrival-prep.yaml`

— beta, 2026-04-15T19:15Z (identity: `hapax-whoami` → `beta`)
