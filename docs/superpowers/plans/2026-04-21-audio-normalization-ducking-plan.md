# Audio Normalization + Ducking — Integration Plan

> **For agentic workers:** REQUIRED SUB-SKILL — superpowers:subagent-driven-development
> or superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax.

**Research basis:**
`docs/research/2026-04-21-audio-normalization-ducking-integration.md`
(viability: positive). Closes D-08; opens three LOC-sized PRs that
ship the broadcast-path TTS-driven ducker missing from
`docs/research/2026-04-20-audio-normalization-ducking-strategy.md` §4.2.

**Architecture summary:** TTS-active boolean published to
`/dev/shm/hapax-compositor/voice-state.json` (existing file, new key
`tts_active`) by a pipecat frame processor; consumer drives a new
PipeWire `filter_chain` ducker that sits on the broadcast-bound
`hapax-livestream` path before the L6 USB playback sink (per L6
retargets runbook §2.1). No new `NodeKind` required.

---

## PR-1 — `tts_active` SHM publisher

**Scope:** ~80 LOC across one new module + one pipeline edit + one test.

- [ ] Write failing test:
      `tests/hapax_daimonion/test_tts_state_publisher.py` — assert
      `TTSStartedFrame` writes `{"tts_active": true}` to the voice-state
      file; `TTSStoppedFrame` writes `{"tts_active": false}`; both
      preserve any existing `operator_speech_active` key (atomic
      read-modify-write, mirroring
      `agents/studio_compositor/vad_ducking.py` lines 45–51).
- [ ] Implement `agents/hapax_daimonion/tts_state_publisher.py`
      modelled on `agents/hapax_daimonion/vad_state_publisher.py`
      lines 1–50. Subscribes to `TTSStartedFrame` /
      `TTSStoppedFrame` (pipecat). Pure side-effect; passes frames
      through unmodified.
- [ ] Wire into the pipecat pipeline (sibling of `VadStatePublisher`,
      placed *after* the TTS stage so frame ordering is correct).
- [ ] Run tests, verify pass.
- [ ] Commit.

## PR-2 — Ducker filter-chain conf + descriptor entry

**Scope:** ~120 LOC across one new conf + one yaml edit + one test edit.

- [ ] Write failing test: extend
      `tests/shared/test_canonical_audio_topology.py` to assert
      presence of node `hapax-livestream-duck` with `kind: filter_chain`,
      `target_object` matching the L6 USB playback sink, and
      `params.duck_signal_path = /dev/shm/hapax-compositor/voice-state.json`,
      `params.duck_key = tts_active`.
- [ ] Add `config/pipewire/hapax-livestream-duck.conf` — filter-chain
      with a `builtin mixer` (gain control exposed via PipeWire
      control-interface socket) inserted between `hapax-livestream`
      virtual sink and the L6 USB playback target. Default gain 1.0;
      duck gain 0.316 (= -10 dB per
      `docs/research/2026-04-20-audio-normalization-ducking-strategy.md`
      §4.2 row 1). Reference comment to LADSPA syntax doc §4 for the
      builtin-vs-LADSPA mix pattern.
- [ ] Add the `hapax-livestream-duck` node + the
      `livestream-loopback → livestream-duck → ryzen-analog-out`
      edge rewrite to `config/audio-topology.yaml` (replaces the
      direct `livestream-loopback → ryzen-analog-out` edge at lines
      119–120; the duck node interposes).
- [ ] Run `hapax-audio-topology generate` to confirm conf round-trips
      cleanly through the descriptor (Phase 2 contract from
      `docs/superpowers/plans/2026-04-20-unified-audio-architecture-plan.md`).
- [ ] Run tests, verify pass.
- [ ] Commit.

## PR-3 — `DuckController` extension to drive the filter-chain

**Scope:** ~150 LOC across one module edit + one test.

- [ ] Write failing test:
      `tests/studio_compositor/test_tts_duck_controller.py` — assert
      that flipping `tts_active` true/false in the voice-state file
      causes the controller to emit gain commands to a mock filter-
      chain control socket, with 30 ms poll cadence + transition-only
      emission (no per-poll spam, mirrors `DuckController` lines
      66–80 invariants).
- [ ] Extend `agents/studio_compositor/vad_ducking.py` with a
      `TtsDuckController` class (sibling of `DuckController`) that
      reads the `tts_active` key. Choose between
      `pactl set-sink-volume` and a direct PipeWire control-interface
      socket write; prefer the latter for sub-50 ms latency (consent
      latency obligation, council MEMORY).
- [ ] Add fail-open path: if voice-state.json missing or stale > 2 s,
      controller forces gain to 1.0 (broadcast continues at full level
      rather than going silent).
- [ ] Wire `TtsDuckController` into the compositor's startup path
      next to the existing `DuckController` instantiation (one new
      thread, same lifecycle).
- [ ] Run tests, verify pass.
- [ ] Commit.

---

## Smoketest gate (post-PR-3)

Run the 3-utterance acceptance criteria from the integration research
doc §4 against the live system. All five rows must pass before D-08
is marked closed:

- [ ] Pre-utterance baseline: -14 ± 1 LUFS at L6 main-mix tap.
- [ ] Utterance #1: YT bed -24 ± 1 LUFS during TTS; TTS peak ≤ -1 dBTP;
      aggregate ≥ -16 LUFS.
- [ ] Utterance #2 (operator voice overlap): TTS duck -6 dB triggered;
      `tts_active` releases ≤ 250 ms after final TTS frame.
- [ ] Utterance #3 (TTS only, silence music): YT gain stays 1.0 (no
      false trigger).
- [ ] Post-utterance settle: YT recovers to -14 ± 1 LUFS within 250 ms.

Smoketest failure on any row reverts PR-2 + PR-3 (PR-1 is harmless on
its own — the SHM key has no consumer) and reopens D-08 with the
failing-row diagnosis as the next research target.

## Out of scope

- Vinyl-ch-4-driven TTS duck (strategy §4.2 row 3) — analog-to-
  filter-chain envelope follower is non-trivial and warrants its own
  research cycle.
- Master glue compressor at L6 main-mix tap (strategy §4.2 row 4) —
  separate Phase C work, MixQuality-coupled.
- Notification-loopback retarget (strategy §7 row 1) — independent
  D-09 candidate; does not block the broadcast-path duck.
