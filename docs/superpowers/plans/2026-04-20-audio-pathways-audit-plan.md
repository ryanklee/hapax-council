# Audio Pathways Audit (Task #134) — Implementation Plan

**Status:** ready-to-execute
**Date:** 2026-04-20
**Author:** alpha (refining 2026-04-18 spec)
**Owner:** alpha (zone — daimonion crosses into delta-zone for input wiring; coordinate via relay)
**Spec:** `docs/superpowers/specs/2026-04-18-audio-pathways-audit-design.md`
**Origin:** D-31 unplanned-spec triage flagged HIGH priority — load-bearing prereq for Rode #133 integration; closes phantom-VAD ducking loop.
**WSJF:** 6.0 (HIGH per D-31 vault-task triage; livestream-affecting)
**Branch:** trio-direct (per existing burst pattern; ships in 4-5 small commits on main)
**Total effort:** ~5-7h focused work across 4 phases

## 0. Why this plan exists

D-31 unplanned-specs triage classified this as `still-relevant-needs-plan` (HIGH). The spec was authored 2026-04-18 + provisionally approved; no plan was filed. Per the gap-audit's systemic-pattern miss #2 ("research-doc-without-plan treated as planning"), this is a structural fix.

Phantom-VAD ducking is an active livestream defect: YouTube crossfeed through the Yeti triggers VAD → unintended duck fires → operator audio gets attenuated even when the operator is silent. The remediation requires three coordinated changes: PipeWire echo-cancel pass + voice-embedding gate on the ducking trigger + observable metrics for the trigger taxonomy.

This plan also UNBLOCKS Rode #133 (Wireless Pro integration) per spec §3.3 — Rode source priority can't be negotiated without an enumerated source list and the echo-cancel virtual source.

## 1. Pre-flight

- [ ] Verify Blue Yeti is the operator's primary input
      (`pactl list sources short | grep Yeti`)
- [ ] Verify `hapax-ytube-ducked` sink exists
      (`pactl list sinks short | grep ytube`)
- [ ] Verify pipewire is running + supports `module-echo-cancel-aec`
      (`pw-cli ls Module | grep -i echo`)
- [ ] Verify `agents/hapax_daimonion/audio_input.py` + `vad.py` paths
      still match spec §4
- [ ] Confirm operator voice-embedding state per spec §7 Q1:
      `find ~/.local/share/hapax-daimonion -name "operator_voice*"`. If
      missing → Phase 4 needs a fresh enrollment step (operator-driven).
- [ ] Confirm spec §7 Q2 (WebRTC AEC) + §7 Q3 (Kokoro TTS in echo
      reference) defaults are operator-acceptable. Defer override to
      operator if they object before Phase 1 lands.

## 2. Phase 1 — Runbook + topology check (~1.5h)

Spec §8 steps 1-2.

### 2.1 Tasks

**T1.1** New `docs/runbooks/audio-topology.md`:
- Topology diagram (ASCII art): inputs (Yeti, Studio 24c, Ambient
  derived) → echo-cancel virtual source → daimonion VAD; outputs
  (default sink, `hapax-ytube-ducked`, Kokoro TTS).
- Source/sink inventory with PipeWire node names + `hw:` aliases.
- Ducking rules: trigger gate, attack/release, sidechain key.
- Diagnostic commands: `pactl list sources short`,
  `pw-cli ls Node | grep echo`, `pw-top` interpretation.
- Rode #133 hand-off section: where Rode source plugs in per spec §3.3.

**T1.2** New `scripts/audio-topology-check.sh`:
- Enumerate live PipeWire graph via `pw-dump | jq`.
- Diff against expected topology JSON at
  `config/audio-topology.yaml` (existing per delta's audio-topology
  family work; cross-reference shape).
- Print deltas: missing nodes, extra nodes, unexpected connections.
- Exit code 0 on match, 1 on missing-required, 2 on extra-found
  (operator review needed for extras; missing is hard fail).

**T1.3** Tests at `tests/scripts/test_audio_topology_check.py`:
- Synthetic `pw-dump` JSON fixtures (healthy, missing-echo-cancel,
  extra-source).
- Assert correct exit codes per fixture.

### 2.2 Exit criterion

`bash scripts/audio-topology-check.sh` against the live system
returns exit 1 (current state lacks `echo_cancel_capture` virtual
source — that's Phase 2's job). Runbook renders cleanly in Obsidian.

### 2.3 Commit

```
docs(audio): #134 Phase 1 — audio topology runbook + diagnostic check
```

## 3. Phase 2 — Echo-cancel PipeWire module (~1.5h)

Spec §3.1 + §8 steps 3-4.

### 3.1 Tasks

**T2.1** New `/etc/pipewire/pipewire.conf.d/hapax-echo-cancel.conf`:
- WebRTC AEC backend per spec §7 Q2 default.
- Capture target: Blue Yeti (operator primary).
- Reference signal: default sink (room ambience) + Kokoro TTS sink
  (per spec §7 Q3 default — merged into reference so Hapax doesn't
  echo-cancel its own voice).
- Virtual source name: `echo_cancel_capture`.

**T2.2** Modify `agents/hapax_daimonion/audio_input.py`:
- Consume `echo_cancel_capture` virtual source instead of raw Yeti.
- Fallback: if virtual source missing (echo-cancel module failed to
  load), warn + fall back to raw Yeti so daimonion stays bootable.
  Failure-mode parity with the existing `_FALLBACK` patterns in the
  module.

**T2.3** Modify `agents/hapax_daimonion/config.py`:
- `audio_input_source` becomes `list[str]` per spec §4 line 106 —
  ordered priority list. Defaults to `["echo_cancel_capture", "Yeti"]`.
- Backward compat: a single string is accepted + auto-wrapped to a
  list (warn-once for the deprecated form).

**T2.4** Tests at `tests/hapax_daimonion/test_echo_cancel_input.py`:
- Mock pw-cli output: virtual source present → `audio_input.py`
  consumes it.
- Mock virtual source missing → falls back to Yeti + warning logged.
- `audio_input_source` legacy-string path warns + works.

### 3.2 Exit criterion

`pactl list sources short | grep echo_cancel_capture` shows the
virtual source after pipewire reload. `audio-topology-check.sh`
returns 0. Daimonion smoketest still recognizes operator speech with
echo-cancel active (regression).

### 3.3 Commit

```
feat(audio): #134 Phase 2 — PipeWire echo-cancel + daimonion virtual source consumer
```

## 4. Phase 3 — Voice-embedding ducking gate (~2h)

Spec §3.2 + §8 steps 5-7.

### 4.1 Tasks

**T3.1** Voice embedding enrollment (operator-driven):
- Add `scripts/enroll-operator-voice.sh` calling
  `agents/hapax_daimonion/speaker_id.py` (or whichever speaker-ID
  module is shipped per CLAUDE.md § Bayesian Presence Detection
  `voice_id`).
- Save embedding to `~/.local/share/hapax-daimonion/operator_voice.npy`.
- Per spec §7 Q1: fresh enrollment if no existing embedding.

**T3.2** Modify `agents/hapax_daimonion/vad.py`:
- Add embedding-match gate to ducking trigger.
- New helper `_voice_embedding_match(audio_window) -> float` —
  computes cosine similarity between window's voice embedding and the
  enrolled operator embedding.
- Threshold: 0.75 per spec §6 line 124.
- Decision logic:
  - VAD fires + embedding_match ≥ 0.75 → duck (reason: `vad_and_embedding`)
  - VAD fires + embedding_match < 0.4 → no duck (reason:
    `vad_only_fallback`); increment `phantom_vad_detected_total`
  - VAD fires + 0.4 ≤ embedding_match < 0.75 → duck with caveat
    (reason: `vad_only_fallback`)

**T3.3** Add Prometheus metrics in `shared/director_observability.py`:
- `hapax_audio_ducking_triggered_total{reason}` (Counter)
- `hapax_audio_echo_cancel_active` (Gauge)
- `hapax_audio_phantom_vad_detected_total` (Counter)
- `hapax_audio_source_active{source_name}` (Gauge)

**T3.4** Tests at `tests/hapax_daimonion/test_ducking_trigger.py`:
- VAD=True + embedding_match=0.9 → duck fires
- VAD=True + embedding_match=0.3 → duck does NOT fire (phantom)
- VAD=True + embedding_match=0.55 → duck fires with `vad_only_fallback`
  reason
- VAD=False + embedding_match=0.9 → duck does NOT fire (no speech)

### 4.2 Exit criterion

`uv run pytest tests/hapax_daimonion/test_ducking_trigger.py -q`
green. Prometheus metrics expose values via daimonion's `:9483`
endpoint.

### 4.3 Commit

```
feat(audio): #134 Phase 3 — voice-embedding ducking gate + metrics
```

## 5. Phase 4 — Regression smoke + Rode #133 hand-off (~1h)

Spec §6 line 127 + §8 step 8-9.

### 5.1 Tasks

**T4.1** YouTube crossfeed regression (manual):
- Play YouTube at audible room level via speakers
- Speak over it briefly → assert duck fires
- Stop speaking, wait 3s
- Speak again → assert no residual phantom ducking
- Capture before/after Prometheus metrics for the operator to verify

**T4.2** Phantom-VAD baseline measurement:
- Pre-Phase-3: count VAD trigger rate during 30s of YouTube-only
  playback. Should be N>0 (baseline showing the bug).
- Post-Phase-3: same measurement should yield 0 (or N classified as
  `vad_only_fallback` and NOT triggering duck).

**T4.3** Hand-off doc for Rode #133:
- Append to `docs/runbooks/audio-topology.md` a Rode #133 section:
  - Source priority order: Rode > Yeti (when Rode is connected)
  - `audio_input_source` config: `["echo_cancel_capture",
    "Rode_Wireless_Pro", "Yeti"]`
  - Echo-cancel: needs to consume Rode as capture target when present
  - Bayesian presence: ir_body_heat + Rode-RSSI cross-check

**T4.4** Spec footer (D-31 audit-loop closure):
- Append "Shipped in <commit-SHAs>" line to spec footer per D-31
  recommendation.

### 5.2 Exit criterion

Manual regression passes. Prometheus baselines captured. Rode
hand-off doc renders cleanly.

### 5.3 Commit

```
docs(audio): #134 Phase 4 — regression smoke + Rode #133 hand-off
```

## 6. Risk register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Echo-cancel module fails to load (kernel/driver) | M | Phase 2 blocked | Fallback to raw Yeti shipped in T2.2; warn loudly |
| Voice embedding enrollment fails for operator | L | Phase 3 has no enrolled embedding | Spec §7 Q1: fall back to fresh enrollment; daimonion startup notifies |
| WebRTC AEC degrades operator voice quality | M | Operator complaint | Spec §7 Q2: tunable in .conf; default WebRTC; can switch to Speex |
| Embedding-match threshold 0.75 is wrong for room ambience | M | Phantom VAD persists OR legitimate speech rejected | Test with operator voice across 3 distances; tune threshold per spec metrics |
| Kokoro TTS in reference signal causes Hapax to never hear itself | L | Echo-cancel over-correction | Spec §7 Q3 default YES; if cross-talk issues, remove from reference |

## 7. Acceptance criteria

- [ ] `audio-topology.md` runbook in repo
- [ ] `audio-topology-check.sh` returns 0 on healthy live system
- [ ] `echo_cancel_capture` virtual source exists in production
      pipewire after Phase 2 deploy
- [ ] Daimonion consumes virtual source (or falls back loudly)
- [ ] All 4 ducking-trigger tests pass
- [ ] 4 Prometheus metrics expose live values
- [ ] YouTube crossfeed regression: duck fires when operator speaks,
      doesn't fire on silence
- [ ] Phantom VAD count drops to 0 (or all classified as
      `vad_only_fallback` without firing duck)
- [ ] Rode #133 hand-off section in runbook
- [ ] Spec footer updated with shipped commit SHAs

## 8. Sequencing relative to other in-flight work

- **UNBLOCKS** Rode #133 (Wireless Pro integration) — per spec §3.3
- **Independent of** D-30 (CC-task SSOT)
- **Independent of** HSEA Phase 0
- **Independent of** OQ-02 Phase 1 oracles
- **Cross-zone with** delta — daimonion vad.py / audio_input.py edits
  cross into the daimonion zone. Coordinate via relay before Phase 2
  starts.
- **Adjacent to** D-08 audio-ducking research (already shipped per
  agent's `2026-04-21-audio-normalization-ducking-integration.md`) —
  this audit's voice-embedding gate complements D-08's loudnorm
  ducking; they're orthogonal axes (gate vs. attenuation curve).

## 9. References

- Spec: `docs/superpowers/specs/2026-04-18-audio-pathways-audit-design.md`
- D-31 triage: `docs/research/2026-04-20-d31-unplanned-specs-triage.md`
- D-08 research: `docs/research/2026-04-21-audio-normalization-ducking-integration.md`
- Rode #133 spec: `docs/superpowers/specs/2026-04-18-rode-wireless-integration-design.md`
  (also unplanned per D-31 — should be sequenced AFTER this plan ships)
- CLAUDE.md § Bayesian Presence Detection (voice-id signal)
- Existing PipeWire conf: `config/pipewire/voice-over-ytube-duck.conf`
