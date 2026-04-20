# Dual-FX S-4 USB-Direct Routing Plan

> **For agentic workers:** REQUIRED SUB-SKILL — superpowers:subagent-driven-development.

**Goal:** retarget the S-4 to its USB pro-audio class-compliant path
so voice can route to S-4 directly, bypassing the Evil Pet. Enables
operator-requested selectivity: not every TTS pass needs to pass
through granular DSP.

**Architecture:** current topology forces all PC audio through Ryzen
analog → L6 ch 5 → AUX 1 → Evil Pet → S-4 → L6 ch 3. Dual-FX adds a
parallel path: PC audio → PipeWire USB class-compliant sink →
S-4 track N → L6 direct. Voice-tier selects which path (Evil Pet
granular / S-4 pitched FX / both / neither) based on the tier's
character budget.

**Tech stack:** PipeWire class-compliant USB sink config,
WirePlumber routing policy, voice-tier selection hooks.

**Research reference:** `docs/research/2026-04-20-dual-fx-routing-design.md`.

---

## Phase 1 — S-4 USB sink descriptor

- [ ] Write failing test: `pw-dump | jq` locates an `alsa_output.usb-Torso_Electronics_S-4`
      node when the S-4 is plugged in USB.
- [ ] Author `config/pipewire/s4-usb-sink.conf` — enable pro-audio
      profile, expose 10 channels (L+R inputs → Tracks 1–4 on MIDI
      ch 2–5).
- [ ] Commit.

## Phase 2 — Routing map

- [ ] Write a routing-map YAML describing:
      `voice-path.evil-pet` = Ryzen → L6 ch 5 → AUX 1 → Evil Pet → …
      `voice-path.s4-direct` = S-4 USB sink track 1
      `voice-path.both` = duplicate stream to both paths
      `voice-path.dry` = Ryzen analog only, no DSP
- [ ] Commit as `config/voice-paths.yaml`.

## Phase 3 — Path-selection hook

- [ ] Write failing test: `select_voice_path(tier)` returns
      `voice-path.dry` for UNADORNED, `voice-path.s4-direct` for RADIO
      (pitched FX without granular), `voice-path.evil-pet` for
      BROADCAST_GHOST/MEMORY, `voice-path.both` for UNDERWATER,
      `voice-path.evil-pet` for GRANULAR_WASH/OBLITERATED (granular
      engine required).
- [ ] Implement in `agents/hapax_daimonion/voice_path.py`.
- [ ] Wire into `vocal_chain.apply_tier` as a pre-CC-emission hook.
- [ ] Commit.

## Phase 4 — PipeWire route switcher

- [ ] Write failing test: switching from `voice-path.evil-pet` to
      `voice-path.s4-direct` updates `metadata.default.audio.sink` to
      the S-4 USB sink and the prior link is torn down cleanly.
- [ ] Implement `shared/audio_topology/switch.py` using `pw-cli` +
      `pactl move-sink-input`.
- [ ] Commit.

## Phase 5 — Voice-tier integration

- [ ] Extend `VocalChainCapability` with a `voice_path` field set from
      the router output.
- [ ] Apply route switch before CC emission so the Evil Pet CCs land
      on the right bus.
- [ ] Commit.

## Phase 6 — S-4 firmware upgrade gate

- [ ] Before enabling Track-5 (R input) as a separate destination,
      operator runs the S-4 OS 2.1.4 upgrade per
      `docs/research/2026-04-20-fx-firmware-upgrade-procedures.md` §2.
- [ ] Verify Program Change receives after upgrade (S-4 2.1.4 adds
      PC support). Phase 5 routing becomes finer-grained with PC
      available.

## Rollout gate

Phase 1–5 ship as pure config + Python. Phase 6 requires operator
firmware flash.

## Dependencies

- S-4 plugged in USB with pro-audio profile active (already live).
- No new Python deps.

## Deferred

- Multi-track S-4 assignment (R input → Track 5) until firmware flash.
- Elektron Analog Heat / other pedal-loop FX returning via same
  topology.
