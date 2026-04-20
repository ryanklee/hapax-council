---
date: 2026-04-21
author: delta
audience: operator + alpha + delta (execution)
register: scientific, engineering-normative
status: integration research — D-08 closeout candidate
related:
  - docs/research/2026-04-20-ladspa-pipewire-syntax.md (LADSPA node syntax)
  - docs/research/2026-04-20-audio-normalization-ducking-strategy.md (§4 ducking matrix, §5 enforcement)
  - docs/research/2026-04-20-unified-audio-architecture-design.md (descriptor model)
  - config/pipewire/voice-fx-loudnorm.conf (Phase A loudnorm filter-chain)
  - config/pipewire/voice-fx-chain.conf (biquad EQ chain)
  - config/wireplumber/50-hapax-voice-duck.conf (role-based Tier B)
  - docs/superpowers/handoff/2026-04-20-delta-l6-retargets-operator-runbook.md (L6 USB topology)
constraint: research only, no code, no implementation
---

# Audio Normalization + Ducking — Integration Research

## §1. Context

Phase A of the audio-normalization plan ships
`config/pipewire/voice-fx-loudnorm.conf` (SC4 + fast_lookahead_limiter,
LADSPA syntax per `docs/research/2026-04-20-ladspa-pipewire-syntax.md`
§4). The remaining Tier-B follower in
`docs/research/2026-04-20-audio-normalization-ducking-strategy.md` §4.2
that is *not* yet enforced is **TTS-active → music/SFX duck of broadcast-
path content the role-based loopback cannot reach**. The shipped
WirePlumber `role-based.duck-level = 0.3` (Tier B leader S1 → followers
S5/S7) handles app-side multimedia, but the L6 hardware path (vinyl ch 4,
operator Rode ch 1, YT-via-USB-playback) sits behind the multitrack and
is invisible to WP role policy. This doc decides whether and where a
PipeWire-side ducker can sit in the post-retarget graph
(`docs/superpowers/handoff/2026-04-20-delta-l6-retargets-operator-runbook.md`
§2.1) without colliding with the loudnorm chain or the L6 main-mix tap.

## §2. Where the ducking gate lives — pre-mix vs per-source

Two viable placements; one viable, one rejected.

### §2.1 Pre-mix master gate (REJECTED)

A single ducker on `hapax-l6-evilpet-capture` between L6 AUX10/11 and
`hapax-livestream-tap` (`config/audio-topology.yaml` lines 41–48)
attenuates the entire broadcast aggregate when TTS is active. This is
attractive because it requires one filter-chain instance and zero new
descriptor nodes. It is rejected because:

1. **TTS is inside the aggregate.** Ducking the L6 main mix during TTS
   ducks the TTS itself (Evil Pet return on L6 ch 3 →
   `config/pipewire/voice-fx-chain.conf` lines 73–80 dry path → AUX10/11
   sum). The follower must be the *non-TTS* slice of the mix, which
   pre-mix attenuation cannot isolate.
2. **Operator voice on Rode ch 1 also rides AUX10/11**, and §4.2 of the
   strategy doc explicitly *raises*, not lowers, operator priority over
   TTS — a master gate inverts that.

### §2.2 Per-source filter-chain duckers (VIABLE)

The duck is enforced per-follower, on each source-side filter-chain
*before* it sums into AUX10/11 at the L6 hardware. The strategy doc §5.2
already prescribes this shape ("envelope-follower filter-chain", lines
163–174). For the post-L6-retarget topology this means:

- **YT/SFX duck**: a `hapax-livestream` → L6 USB playback filter-chain
  with a `builtin` mixer node whose gain CC is driven by the TTS-active
  signal. (L6 USB playback target per L6 retargets runbook §2.1.)
- **Vinyl ch 4 duck**: not a PipeWire node — vinyl is analog into L6
  ch 4. Software ducking is impossible at this stage; remains operator-
  discipline + L6 fader (strategy doc §6.2 hardware rule table).
- **Rode ch 1**: do *not* duck; §4.2 leader, not follower.

Loudnorm chain (`config/pipewire/voice-fx-loudnorm.conf` lines 28–116)
remains the TTS *output* normalizer downstream of voice-fx; it sits
*upstream* of the duck signal generator (it doesn't consume the duck
state — it produces the audio whose presence drives ducking elsewhere).
No collision.

## §3. How TTS-active reaches the ducker

Three candidate carriers; one preferred, two rejected.

### §3.1 PipeWire stream-state introspection (REJECTED)

In principle WirePlumber could publish the `loopback.sink.role.assistant`
sink-input "ACTIVE" state and a Lua hook in WP could mutate a follower
filter-chain's gain control. In practice: the shipped role-based
`duck-level = 0.3` mechanism (`config/wireplumber/50-hapax-voice-duck.conf`
lines 18–26) *is* this carrier, and it already covers what it can cover.
What it cannot reach is the L6-hardware-aggregated portion of the mix.
WirePlumber has no way to attach a duck multiplier to a filter-chain
node that is downstream of an ALSA sink it doesn't own. Reusing the WP
mechanism for the L6 path is not viable.

### §3.2 Direct sub-callback from `PwAudioOutput` (REJECTED)

`agents/hapax_daimonion/pw_audio_output.py` lines 99–143 is the TTS
write path; a synchronous "TTS started / ended" hook around `write()`
could publish a duck signal. Rejected on two grounds:

1. **Granularity**. `write()` is per-PCM-chunk (~1 audio frame at 24 kHz);
   wrapping it would either flap the duck per chunk (false trigger
   between chunks) or require utterance-boundary state TTS doesn't
   currently emit. The existing utterance-boundary signal lives on the
   pipecat side (`agents/hapax_daimonion/vad_state_publisher.py` lines
   39–50, frame-driven), not at the pw-cat layer.
2. **Coupling**. A direct callback hard-couples ducker liveness to
   daimonion process liveness; if daimonion crashes mid-utterance, the
   duck never lifts. A file-based signal degrades gracefully (stale
   timestamp = restore).

### §3.3 SHM file signal mirroring `voice-state.json` (PREFERRED)

`agents/studio_compositor/vad_ducking.py` lines 36–80 already establishes
the pattern: `/dev/shm/hapax-compositor/voice-state.json` carries
`operator_speech_active`, written atomically (lines 45–51), polled at
30 ms by `DuckController` (lines 66–80). The same pattern, with key
`tts_active`, is the right carrier:

- **Producer**: pipecat TTS-output frame processor (sibling of
  `VadStatePublisher`), writing on `TTSStartedFrame` /
  `TTSStoppedFrame` boundaries — utterance-granular, not chunk-granular.
- **Consumer**: a small daemon (or extension of `DuckController`)
  reading the file and driving the L6-USB-playback filter-chain's gain
  control via `pactl set-sink-input-volume` or the filter-chain's own
  control-interface socket.
- **Failure mode**: file stale > 2 s ⇒ assume TTS inactive, gain = 1.0
  (fail-open to broadcast, never fail-closed to silence). Mirrors the
  fail-open posture VAD ducking already uses.

This avoids the impingement bus (`/dev/shm/hapax-dmn/impingements.jsonl`,
council CLAUDE.md "Daimonion impingement dispatch") because impingements
are coarser than utterance boundaries and have other consumers; adding
a duck consumer there would mix concerns.

## §4. 3-utterance smoketest acceptance criteria

Adapt `scripts/smoke_test_daimonion.sh` (existing harness) plus
`scripts/studio-smoke-test.sh` (broadcast path). Three TTS utterances
emitted with YouTube playing at -14 LUFS through `hapax-livestream`:

1. **Pre-utterance baseline** (5 s before TTS). Capture `pw-cat --record`
   on the L6 main-mix tap; compute integrated LUFS over the window.
   Expectation: -14 ± 1 LUFS (broadcast target, strategy §3.2).
2. **Utterance #1** (3 s, mid-sentence). During TTS:
   - YT/SFX bed integrated LUFS drops to -24 ± 1 LUFS (-10 dB duck per
     §4.2 row 1).
   - TTS path peak through loudnorm chain stays ≤ -1 dBTP (limiter
     ceiling, `config/pipewire/voice-fx-loudnorm.conf` line 82).
   - Aggregate L6-tap LUFS stays ≥ -16 (TTS fills the duck pocket).
3. **Utterance #2** (overlapping operator voice via Rode ch 1, simulated
   with a -18 LUFS sine on ch 1). TTS path duck of -6 dB triggers per
   §4.2 row 2; `tts_active` SHM goes false within 250 ms of TTS frame
   end (release).
4. **Utterance #3** (TTS only, no music). YT bed gain = 1.0 throughout
   (no false trigger from silence; verifies the gain controller's
   restore path).
5. **Post-utterance settle** (2 s after final TTS frame). YT bed back to
   -14 ± 1 LUFS within the 200 ms release envelope (§4.2 row 1) plus
   30 ms poll cadence; total recovery ≤ 250 ms.

Pass = all five rows green; fail on any row regresses to operator-
discipline-only ducking and flags D-08 as not-shippable in this cycle.

## §5. Does `config/audio-topology.yaml` need a new node-kind?

**No.** The five existing kinds in `shared/audio_topology.py` lines
62–66 (`alsa_source`, `alsa_sink`, `filter_chain`, `loopback`, `tap`)
already cover the duck node. The L6-USB-playback ducker is a
`filter_chain` whose `params` carry duck-specific knobs (attack,
release, target gain, signal-source path). Concretely, one new node
would land in `config/audio-topology.yaml` between `livestream-loopback`
(lines 61–68) and `ryzen-analog-out` — a `filter_chain` named
`hapax-livestream-duck` whose `target_object` is the L6 USB playback
sink (per L6 retargets runbook §2.1) and whose `params` include
`duck_signal_path: /dev/shm/hapax-compositor/voice-state.json` and
`duck_key: tts_active`. The descriptor schema is open enough
(`Node.params: dict[str, Any]`) that the duck semantics ride in
`params` without a kind extension. The CI pin
(`tests/shared/test_canonical_audio_topology.py`, per L6 retargets
runbook §4) will need a new expected-id entry.

The alternative — a new `NodeKind.DUCKER` — was considered and rejected
because (a) it adds a kind for a single instance, (b) the generator
code path would diverge from `filter_chain` for ~15 LOC of extra
templating, and (c) a future second ducker (§4.2 row 3 vinyl-driven
TTS duck) would need the same params-carried discriminator regardless.

## §6. Viability verdict

Integration is **viable**. Three concrete, LOC-bounded follow-ons land
in the plan stub: (1) add `tts_active` SHM publisher in pipecat TTS
frame processor, (2) ship the `hapax-livestream-duck` filter-chain
conf + descriptor entry, (3) extend `vad_ducking.DuckController` (or
spawn a sibling) to drive the new filter-chain's control. D-08 closes
on plan stub merge; implementation lands across the three follow-on
PRs in subsequent sessions.
