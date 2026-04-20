# D-01 Director ImpingementConsumer Architecture

**Date:** 2026-04-20
**Author:** alpha (compositor zone)
**Register:** Scientific, scoped to one cross-zone wire and its tie-in to the LRR Phase 8 content-programming layer.
**Scope:** Specification for how `agents/studio_compositor/director_loop.py` should consume the `VoiceTierImpingement` payload that delta shipped on the producer side, and how that consumer interlocks with LRR Phase 8 content-programming-via-objectives.
**Status:** Architecture spec. No code changes. Justifies subsequent implementation work.
**Related:**
- `shared/typed_impingements.py:63` — `VoiceTierImpingement` payload shape
- `agents/hapax_daimonion/vocal_chain.py:424` — `emit_voice_tier_impingement()` producer
- `agents/studio_compositor/director_loop.py:208` — `_DMN_IMPINGEMENTS_FILE` path constant
- `shared/impingement_consumer.py:63` — `ImpingementConsumer` reusable utility
- `docs/research/2026-04-20-voice-tier-director-integration.md` — canonical Option-C voice-tier spec
- `docs/research/2026-04-20-mode-d-voice-tier-mutex.md` — granular-engine mutex
- `docs/research/2026-04-20-delta-queue-flow-organization.md` §7.1 — original cross-zone handoff
- `docs/superpowers/specs/2026-04-15-lrr-phase-8-content-programming-via-objectives-design.md` — Phase 8 design spec
- `docs/superpowers/plans/2026-04-15-lrr-phase-8-content-programming-via-objectives-plan.md` — Phase 8 plan
- `shared/programme.py` — Programme primitive, `voice_tier_band_prior`, `monetization_opt_ins`

---

## §1. Has the relationship been spec'd?

**Yes — the voice-tier ↔ Programme relationship is fully spec'd.** The
voice-tier ↔ objective relationship is **not spec'd** and Phase 8 does
not anticipate it; this document proposes the tie-in.

### §1.1 Voice-tier ↔ Programme — already canonical

`docs/research/2026-04-20-voice-tier-director-integration.md` is the
authority. Its §1.2 selects **Option C**: the structural director picks
the band; the narrative director picks a single tier inside that band
each tick. The Programme contributes the band prior via
`ProgrammeConstraintEnvelope.voice_tier_band_prior`
(`shared/programme.py:123`), and the per-`ProgrammeRole` default table
lives in `shared/voice_tier.py::_ROLE_TIER_DEFAULTS` (per the
integration spec §2.2). The narrative director never picks a band and
never overrides a Programme; both are upstream of the per-tick pick.

This is load-bearing for the consumer architecture. The director_loop
already owns the narrative tick (cadence ~30 s, `PERCEPTION_INTERVAL` at
`director_loop.py:543`). The structural director runs at ~150 s
(`structural_director.py:5-9`). The voice-tier integration spec §1.3
proposes a `VoiceTierSelector` *pure function* called once per
narrative tick that takes the structural band, the active Programme,
the stance, the impingements just composed, the operator override, the
stimmung, and the previous tier — and returns a tier. The selector is
the deterministic arbiter; the LLM contributes (a) composed
impingements and (b) an optional `excursion_request` (§4.4).

So the producer-side `emit_voice_tier_impingement()` is **not the
director's *input* for picking a tier** — the director picks the tier
itself via the selector. The producer-side impingement is the
*announcement* the daimonion's other consumers (CPAL, affordance loop)
need so they know which Kokoro pace and which voice-path the next
utterance will use. The director_loop's job in consuming it is
narrower than the original cross-zone handoff suggests.

### §1.2 Voice-tier ↔ objective — not spec'd

LRR Phase 8 §3.3 (the design spec) lists director scoring extension as
the third deliverable: extend `_call_activity_llm` so
`activity_score(a) = 0.7 × old + 0.3 × objective_advancement`. The
plan's item 3 wires the formula; the partial landing is already in
the codebase (`director_loop.py:597` `_render_active_objectives_block`,
`director_loop.py:1606` `_active_objective_activities`). Neither the
spec nor the partial implementation references voice tier.

The Programme primitive carries `voice_tier_band_prior`; the Objective
schema (`shared/objective_schema.py`, per Phase 8 §3.1) carries
`activities_that_advance` but no voice-tier field. The orthogonality is
deliberate — objectives drive *activity* selection ("study", "react",
"observe") and Programmes drive *voice register* selection
(LISTENING vs HOTHOUSE_PRESSURE vs WORK_BLOCK). They live on different
clocks (objectives are days-to-weeks; Programmes are minutes-to-hours;
voice tier is per-30s-tick).

**Proposal**: keep them orthogonal in the schema and couple them
through *director scoring*, not through new fields. §4 below shows how
voice-tier impingements feed the Phase 8 scorer as a contextual
modifier without making the Objective schema voice-aware.

---

## §2. Producer-side recommendation

### §2.1 Where in `vocal_chain.apply_tier()` should the emit fire?

`vocal_chain.apply_tier()` at `vocal_chain.py:365` already does three
things in order: (a) optionally route-switch via `_maybe_switch_route`,
(b) deactivate prior dim levels, (c) call `apply_tier_fn(...)` which
sends the per-dimension CC barrage.

The emit must land **after the route switch but before the CC barrage**
— the consumer has to know the new tier *before* the audio is
audibly different, so any compositor surface that tracks tier (HARDM
status overlay, monetization-risk indicator on chrome, active-programme
display) updates in lockstep with the audio shift rather than ~100 ms
behind it.

Concretely: insert the emit between `vocal_chain.py:419`
(`_maybe_switch_route(tier, path_override)`) and `vocal_chain.py:421`
(`self.deactivate()`). The route switch is the deterministic gate; if
it fails the emit must not happen (the audio path is wrong). Once the
route is committed, emit, then run the CC barrage. CC delivery is
~16 messages over <50 ms; the consumer's read-loop polling at 1 Hz
will not race the CC stream regardless of emit ordering relative to
deactivate/apply.

### §2.2 Every transition or only excursions?

**Every transition.** The consumer architecture in §3 reads from a
JSONL bus with cursor-tracked semantics; missing a steady-state
transition would leave the consumer's view of "current tier"
permanently stale. The producer cost is one fsync per ~30 s tick
(narrative cadence dominates the call rate); the bus already absorbs
~10× that volume from the compositor's compositional impingements
(`director_loop.py:246`). No throughput concern.

The `excursion: bool` field on `VoiceTierImpingement` (already shipped
at `typed_impingements.py:78`) lets the consumer treat excursions
differently *after* receiving them — e.g. not advancing the
"steady-state tier" overlay but still updating the live
monetization-risk indicator. The consumer branches on the field; the
producer always emits.

Special case: **no emit on a same-tier reapply.** If `apply_tier(t)`
fires twice with the same `t` and no impingement context change, the
second emit is noise that confuses cursor-stationary consumers. Add a
`previous_tier` check inside `apply_tier()`: if `tier == self._last_emitted_tier
and not excursion and clamped_from is None`, skip the emit. The CC
barrage is idempotent enough that suppressing the impingement does not
cause a state divergence.

### §2.3 Which bus?

**Reuse `/dev/shm/hapax-dmn/impingements.jsonl`** — the existing
daimonion-side bus the AffordancePipeline already reads. Three reasons:

1. The director_loop already *writes* to this bus
   (`director_loop.py:208`, `_emit_compositional_impingements`). Adding
   a director-side *read* of the same bus is symmetric and avoids
   inventing a parallel transport.
2. The daimonion's CPAL and affordance loops (CLAUDE.md §Daimonion
   impingement dispatch) already consume from this bus with
   per-consumer cursor files. The director becomes a third cursor on
   the same bus rather than a new file with a new rotation policy.
3. `VoiceTierImpingement` is genuinely useful to the daimonion's other
   consumers too — the affordance pipeline can score capability
   recruitment with knowledge of the active tier (a TIER_5 voice
   shouldn't co-recruit a Sierpinski satellite shader that flashes on
   syllable boundaries; the syllables are gone). So the bus must be
   shared anyway; the director just adds one more reader.

Cost: `/dev/shm/hapax-dmn/impingements.jsonl` is a tmpfs file. fsync
cost is negligible (<100 µs per append). Rotation policy is in
`agents/hapax_daimonion/run_loops_aux.py` and is independent of writer
identity.

### §2.4 Sequencing: emit BEFORE or AFTER the route switch?

**After** — see §2.1. The route switch is the gate. If the gate fails
(pactl returns nonzero, sink unknown), the emit must be skipped because
the audio path is no longer the path the impingement claims. Code
pattern:

```python
# pseudocode — actual edit lands in implementation PR, not this doc
if route_audio:
    route_ok = self._maybe_switch_route(tier, path_override)  # returns bool
    if not route_ok:
        log.warning("vocal_chain route switch failed; not emitting impingement")
        return  # ABORT; don't run CC barrage either
self._emit_voice_tier_impingement_to_bus(tier, ...)
self.deactivate()
_apply_tier_fn(...)
```

`_maybe_switch_route` currently returns `None` and tolerates pactl
failure silently (`vocal_chain.py:526`). The Phase 3b implementation PR
needs to thread a return value through it so the emit can gate on
success.

---

## §3. Consumer-side architecture — three options

### §3.1 Option A — Per-tick poll inside `DirectorLoop._loop()`

Add an `ImpingementConsumer` instance to `DirectorLoop.__init__`
(`director_loop.py:933`). Bootstrap it with a persisted cursor at
`/dev/shm/hapax-director/impingement-cursor-director.txt` (the third
cursor on the daimonion bus, alongside the two existing daimonion
cursors). Inside the main tick at `director_loop.py:1149`
(`if now - self._last_perception < PERCEPTION_INTERVAL`), call
`consumer.read_new()` once per tick, filter to `VoiceTierImpingement`
via `try_from()`, and dispatch.

| Property | Assessment |
|---|---|
| Latency | Up to one full `PERCEPTION_INTERVAL` (~30 s) before the consumer sees a new tier. Sufficient for cross-cadence visual updates (HARDM tier badge), insufficient for sub-tick reactions (e.g. excursion-driven hero-camera switch). |
| Complexity | Lowest. One field on `DirectorLoop`, one method call per tick, one cursor file. ~30 LOC of consumer wire. |
| Failure modes | Robust. `ImpingementConsumer` already handles file rotation, corrupt cursor, OSError. The director's tick-already-late tolerance dominates the consumer's IO cost. |
| Resource cost | One file read per ~30 s. JSONL parse for each new line. Negligible. |
| Threading | Stays on the director's main loop thread; no new locks. |

### §3.2 Option B — Background thread + queue

Spawn a daemon thread that polls the bus at higher cadence (1–5 Hz),
posts decoded `VoiceTierImpingement` payloads into a `queue.Queue`, and
the main tick drains the queue per pass.

| Property | Assessment |
|---|---|
| Latency | ~200–1000 ms (poll interval). Useful for sub-tick reactions (excursion → hero-camera promotion within one camera frame budget). |
| Complexity | Higher. Thread lifecycle, queue ownership, drain semantics, shutdown coordination. ~80 LOC plus join logic in `DirectorLoop.stop()`. |
| Failure modes | Adds a thread that can deadlock or starve. The director's existing thread (`director_loop.py:1037`) is daemon-mode; another daemon thread is fine but join behaviour at compositor shutdown needs care. |
| Resource cost | A polling thread that wakes 1–5×/s reading a tmpfs file. CPU cost negligible. Memory: one extra Python thread (~8 MB stack). |
| Threading | Two threads sharing the consumer cursor file. The cursor's atomic tmp+rename is single-writer-safe; not multi-writer-safe. **Must keep cursor writes on the polling thread only** — the main tick reads from the queue, never from the consumer directly. |

### §3.3 Option C — Reactive engine integration

Register the bus path with the existing `logos/engine/` inotify
reactor; when the file appends, the engine fires a rule that decodes
the impingement and posts it to a SHM file the director reads at the
top of each tick.

| Property | Assessment |
|---|---|
| Latency | inotify wakeup is ~5–50 ms; the director tick floor is the read-after-write delay. Effectively the same as Option B without the polling thread. |
| Complexity | Highest. Requires defining a rule in `logos/engine/`, ensuring the engine is running (it is — but the director then has a runtime dependency on a Tauri-side service to be up), and inventing a SHM hop just to get the data back into the director process. The engine is designed for *reactive cross-process cascade*, not for shoving structured data back into a single consumer. |
| Failure modes | If the engine is down (during compositor restart, during reactor rule reload), the director sees no tier impingements until the engine is back. The director should not depend on a downstream visual-cascade engine for reading its own daimonion-bus messages. |
| Resource cost | One inotify watch, one rule evaluation per impingement, one SHM file write per impingement. Engine is already paying the inotify cost for other watches; marginal cost is one watch + one rule. |
| Threading | None added on the director side — but the engine becomes a load-bearing dependency. |

### §3.4 Recommendation — Option A with an Option-B escape hatch

**Ship Option A first.** The director's existing pattern is per-tick
work on a 30 s cadence; adding one more per-tick file read is
idiomatic. The cross-zone handoff (`docs/research/2026-04-20-delta-queue-flow-organization.md`
§7.1) explicitly says "wire VoiceTierImpingement consumer into
director_loop main tick" — Option A is the literal interpretation.

The 30 s latency is acceptable for **all currently named consumer
side-effects**: HARDM tier badge update, monetization-risk chrome
indicator, programme-band display, scoring extension input (§4). None
of these need sub-tick reaction.

**Escape hatch for excursions.** If the Phase 8 hero-mode camera
switching (§3.5 of the LRR Phase 8 plan) wants to react to
*excursion* impingements within one camera frame (~33 ms), Option A is
insufficient. Migration path: keep the cursor + decode logic in a
helper module; the helper grows a `start_polling_thread()` method that
flips Option A → Option B without the director's call sites changing.
Defer this until the use case actually exists; YAGNI.

Option C is rejected. The reactive engine is a *cascade* mechanism
(filesystem-as-bus → cross-process reactions); reading messages back
into the same process that wrote them via a SHM hop is an architectural
inversion. The engine's strength is precisely *not* requiring the
producer or consumer to know about each other; the director consuming
voice-tier impingements is a known, in-process flow that doesn't
benefit from indirection.

---

## §4. Content-programming integration — Phase 8 tie-in

This is the load-bearing section. The voice-tier consumer must do more
than update overlays; it must feed the Phase 8 director scoring
extension (item 3 of the plan) so that **what Hapax does next is
informed by what voice tier the system is currently sustaining**.

### §4.1 Why couple here, not in the schema

The Objective schema is intentionally voice-tier-agnostic. Adding a
`preferred_tier` field on Objective would (a) require operator-author
maintenance of yet another field, (b) create an upstream coupling that
violates the soft-prior axiom (`shared/programme.py:6` —
"programmes EXPAND grounding opportunities; never REPLACE"), and
(c) miss the actual control surface, which is the *director's
per-tick scoring*, not the *objective's static metadata*.

The right place to couple is `_call_activity_llm`'s scoring extension
(LRR Phase 8 plan item 3, `director_loop.py` ~line 1865 — confirmed by
the existing `_active_objective_activities` helper at
`director_loop.py:1606`). The voice-tier impingement gives the scorer
a *contextual modifier*, not a hard constraint.

### §4.2 Concrete integration

Three touch points in the Phase 8 director scoring path:

**T1. Active-tier read in the scorer.** The director's per-tick pass
calls `consumer.read_new()` and updates `self._current_voice_tier:
VoiceTier | None`. The Phase 8 scorer (item 3) reads this field
alongside `_active_objective_activities()`. The scoring formula is
extended:

```
activity_score(a) = (old_score * 0.7)
                  + (objective_advancement_score(a) * 0.3)
                  + (voice_tier_compatibility(a, current_voice_tier) * 0.0)
```

The voice-tier term ships with weight **zero** in the first
implementation. It is a passive observable visible to the operator via
Langfuse spans, not a scoring input. After two weeks of observation
the weight can move to 0.05–0.10 if there's a measurable correlation
between high-tier voice ticks and operator-preferred activities. This
matches the "verify before claiming done" feedback memory and the
Phase 8 plan's 70/30 tunability via `config/director_scoring.yaml`.

`voice_tier_compatibility(a, tier)` is a small lookup table — TIER_0
favours `study`/`chat`/`tutorial`; TIER_5–6 favours `observe`/`silence`
(the ineffable activities). The table lives in
`config/director_scoring.yaml` alongside the existing knobs.

**T2. Hero-mode camera switching (Phase 8 item 5,
`agents/studio_compositor/camera_profiles.py`).** Phase 8 §3.5 lists
five presets and an activity → preset mapping
(`vinyl → hero_turntable`, `study → hero_screen`, `react → hero_operator`).
Voice tier modulates this:

| Tier | Preset hint |
|---|---|
| TIER_0–TIER_1 | Use activity-driven preset verbatim |
| TIER_2–TIER_3 | Same as activity, but `display-side scaling` pass mutes the operator camera by 10% (slightly less foregrounded) |
| TIER_4 | Force `balanced` (less hero-mode lock-in; voice is colored, attention should diffuse) |
| TIER_5–TIER_6 | Force `sierpinski` (granular voice → granular composition; attention is on substrate, not subject) |

This is the **hand-in-hand** the operator named: the voice tier *is*
content shaping. The hero-mode preset is the visual half; the voice
tier is the audio half; both descend from the same Programme band /
stance / impingement signal. Reading the tier in the camera-profile
selector (rather than re-deriving from band/stance) keeps a single
source of truth.

**T3. Phase 8 item 11 (environmental salience emphasis,
`agents/hapax_daimonion/environmental_salience_emphasis.py`).** The
plan §11 specifies hysteresis + 30 s cooldown for promoting a camera
to hero mode based on IR + audio salience. Voice tier modulates the
emphasis threshold:

- Under TIER_5–6 (granular dissolution), high-salience IR signals are
  the dominant content because voice has receded; *raise* emphasis
  rate.
- Under TIER_0 (dry, intelligible), voice is the dominant content;
  *lower* emphasis rate so visual emphasis doesn't compete with the
  spoken track.

Mechanism: the salience emphasis loop reads
`/dev/shm/hapax-director/voice-tier-state.json` (which the consumer
writes after each `read_new()` pass) for the current tier, multiplies
its threshold by a tier-driven scalar, and proceeds. The state file is
produced by the consumer as a side-effect of consumption; no extra
thread, no API.

### §4.3 What the consumer writes

The consumer's per-tick pass produces:

1. `self._current_voice_tier: VoiceTier | None` — read by the scorer.
2. `self._current_programme_band: tuple[int, int] | None` — read by
   the camera-profile selector and emphasis loop.
3. `/dev/shm/hapax-director/voice-tier-state.json` — written atomically
   tmp+rename, contains `{tier, programme_band, voice_path,
   monetization_risk, since, excursion, clamped_from}`. Read by the
   environmental salience emphasis loop and any Cairo source that
   wants to render the live tier (HARDM badge candidate).

The state file is the *external* surface; the in-process fields are
the *internal* surface. Both live or die together based on consumer
freshness.

### §4.4 What the consumer does NOT do

- **Does not pick the tier.** The selector pure function
  (`agents/hapax_daimonion/voice_tier_selector.py` per the integration
  spec §1.3 + §11 Phase 3) is the picker. The director's job is to
  *read* the picked tier, not derive it.
- **Does not write the bus.** The producer is `vocal_chain.apply_tier`.
  The director_loop already writes its own compositional impingements
  to the same bus (`director_loop.py:246`), but those are a separate
  source string (`studio_compositor.director.compositional`) and the
  consumer filters on `VOICE_TIER_IMPINGEMENT_SOURCE` per
  `typed_impingements.py:59`.
- **Does not gate audio.** Audio flows whether the consumer is alive or
  dead. The consumer is a *visibility layer*; a dead consumer means
  stale chrome, not silent audio.

---

## §5. Test plan

### §5.1 Minimum acceptance test (Phase 3b PR scope)

Three pytest cases in
`tests/studio_compositor/test_director_voice_tier_consumer.py`:

1. **Producer round-trip.** Construct a `VoiceTierImpingement` payload,
   wrap via `to_impingement()`, append to a temporary impingements file,
   construct an `ImpingementConsumer` against that file, call
   `read_new()`, verify `VoiceTierImpingement.try_from(imp)` returns the
   original payload field-for-field.
2. **Cursor persistence.** Same setup, two `read_new()` calls separated
   by a process-restart simulation (close consumer, reopen with same
   `cursor_path`). Verify the second call returns only impingements
   appended between the two opens.
3. **Source filter.** Append one `VoiceTierImpingement`, one
   `EngineAcquireImpingement`, one compositional impingement (different
   source). Verify the consumer's tier-extraction helper returns only
   the voice-tier payload.

These confirm the wire is alive end-to-end without exercising the
director's scoring path.

### §5.2 Integration test (verifies behavior change)

`tests/studio_compositor/test_director_tier_behavior.py`:

Single scenario: instantiate a `DirectorLoop` with a fake LLM that
returns a known `DirectorIntent`, append a `VoiceTierImpingement(tier=
TIER_5, ...)` to the bus, run one `_loop()` iteration, verify:

1. `self._current_voice_tier == TIER_5`.
2. `/dev/shm/hapax-director/voice-tier-state.json` exists and parses to
   the expected payload.
3. The Phase 8 scoring formula's voice-tier term was evaluated (assert
   via Langfuse span metadata or a `_call_activity_llm` mock counter).
4. If Phase 8 item 5 (camera profiles) is shipped, verify the camera
   profile selector observed `tier=TIER_5` and chose `sierpinski`.

This is the first test that proves *behavior changes* on tier
transition. Without it, the wire is alive but provides no observable
director response — exactly the failure mode the operator's "verify
before claiming done" feedback memory warns against.

### §5.3 Live smoketest

`scripts/director-voice-tier-smoketest.sh` (new, ~50 LOC):

1. Start hapax-daimonion + hapax-logos.
2. Issue `hapax-voice-tier 5` via the operator CLI.
3. Tail `/dev/shm/hapax-director/voice-tier-state.json`.
4. Within one narrative cadence (~30 s), the file's `tier` field must
   read `5`. If Phase 8 item 5 is live, the active camera profile must
   read `sierpinski` within the same window.
5. Issue `hapax-voice-tier 0`. Within one cadence, the file must read
   `0` and the camera profile (if live) must read the
   activity-appropriate hero preset.

Records pass/fail to `~/hapax-state/smoke-tests/director-voice-tier.jsonl`.

### §5.4 Replay regression (LRR Phase 2 hook)

The integration test from §5.2 also runs in the LRR Phase 2 replay
harness against a snapshot containing one TIER_0 → TIER_5 → TIER_0
sequence. The replay's tier timeline is diffed against
`tests/data/director_consumer_golden_timeline.jsonl`. Drift flags the
regression. Same pattern as the voice-tier integration spec §10.4.

---

## §6. Sequencing relative to LRR Phase 8 work

### §6.1 Hard prerequisites

- **Voice-tier integration spec Phase 3 must ship first.** That phase
  introduces the `VoiceTierSelector` and writes
  `DirectorIntent.voice_tier`. Until it ships, the producer's
  `emit_voice_tier_impingement` has no caller in `apply_tier` because
  `apply_tier` doesn't yet know which tier to emit (the selector hasn't
  picked one). The cross-zone handoff is dependent on the selector;
  the selector is delta-zone work.
- **Programme primitive Phase 1 already shipped** (`f6cc0b42b`). The
  consumer can read `voice_tier_band_prior` from the active programme
  immediately.

### §6.2 Soft prerequisites

- **LRR Phase 8 item 1 (Objective schema) shipped** — needed for §4.2 T1
  scoring extension. The schema is already partially landed (per
  `_render_active_objectives_block` at `director_loop.py:597`).
  Confirm with one Glob over `shared/objective_schema.py`.
- **LRR Phase 8 item 3 (Director scoring extension) shipped** — needed
  for §4.2 T1 to add the voice-tier-zero term. If item 3 is not yet
  shipped, the consumer ships first as a passive observer (writes the
  state file, populates internal fields, no scoring use); item 3 then
  references the field when it lands.

### §6.3 Dependents

- **LRR Phase 8 item 5 (Hero-mode camera switching)** wants to read the
  voice-tier from the consumer per §4.2 T2. Item 5 should ship *after*
  the consumer wire to avoid item 5 implementing its own bus read.
- **LRR Phase 8 item 11 (Environmental salience emphasis)** wants to
  read the state file per §4.2 T3. Same ordering.
- **Mode D × voice-tier mutex Phase 3** (delta's parallel cross-zone
  seam, see `docs/research/2026-04-20-delta-queue-flow-organization.md`
  §7.2) wires `EnginePool.acquire_engine()` into `director_loop`. That
  PR also lands in the director_loop's main tick. Sequencing per the
  delta queue flow doc §7.4: **ship voice-tier 3b first** (smaller,
  lower-risk); rebase Mode D mutex Phase 3 on top to avoid conflicts in
  `director_loop.py`'s `_loop()` body.

### §6.4 Recommended ship order

1. Voice-tier integration spec Phase 3 (delta) — `VoiceTierSelector`
   + `DirectorIntent.voice_tier` field.
2. **This PR** — producer-side `emit_voice_tier_impingement` call site
   in `apply_tier`, consumer-side wire in `DirectorLoop._loop()`,
   passive state-file write, acceptance tests §5.1.
3. LRR Phase 8 item 3 final — extend scoring formula with voice-tier
   term at weight zero (passive observable).
4. LRR Phase 8 item 5 — hero-mode camera profiles read consumer state.
5. LRR Phase 8 item 11 — emphasis loop reads consumer state.
6. After two weeks of operator observation: tune voice-tier scoring
   weight from 0.0 to 0.05–0.10 in `config/director_scoring.yaml`.

---

## §7. LOC estimate

| Component | LOC | Files |
|---|---|---|
| Producer call site + same-tier suppression + return-value plumbing through `_maybe_switch_route` | ~40 | `agents/hapax_daimonion/vocal_chain.py` |
| Consumer wire in `DirectorLoop` (init + per-tick `read_new`/`try_from` + state-file write + internal field) | ~80 | `agents/studio_compositor/director_loop.py` |
| `voice_tier_compatibility` lookup + scoring-formula edit (T1) | ~50 | `agents/studio_compositor/director_loop.py`, `config/director_scoring.yaml` |
| Camera-profile tier hint (T2) | ~40 | `agents/studio_compositor/camera_profiles.py` (Phase 8 item 5 file; coupling lives there, not in director) |
| Salience emphasis tier modifier (T3) | ~30 | `agents/hapax_daimonion/environmental_salience_emphasis.py` (Phase 8 item 11 file) |
| Acceptance tests §5.1 | ~150 | `tests/studio_compositor/test_director_voice_tier_consumer.py` |
| Integration test §5.2 | ~120 | `tests/studio_compositor/test_director_tier_behavior.py` |
| Smoketest script §5.3 | ~50 | `scripts/director-voice-tier-smoketest.sh` |
| **Total Phase 3b PR scope (lines 1–2 + §5.1 only)** | **~270** | 3 files |
| **Total with Phase 8 integration (lines 1–7)** | **~560** | 7 files |

### §7.1 Phase split

**PR-1 (this work, ~270 LOC, 3 files):**
- Producer call site + emit suppression
- Consumer wire + state-file write
- Acceptance tests

This PR ships independently. It produces a passive observable surface;
no behavior change in the director, no scoring-formula change. The
state file becomes available for downstream consumers.

**PR-2 (LRR Phase 8 item 3 final, ~50 LOC):**
- `voice_tier_compatibility` lookup + scoring edit (weight 0.0)
- Integration test §5.2
- Smoketest §5.3

Ships after PR-1 lands and after Phase 8 item 3's first cut is in
(the 0.7 × old + 0.3 × objective formula). This PR adds the third term.

**PR-3 (LRR Phase 8 item 5, ~40 LOC of voice-tier coupling among the ~550 LOC of camera profiles):**
- Camera-profile selector reads tier from state file.
- Tier → preset table per §4.2 T2.

Ships when Phase 8 item 5 ships. Voice-tier coupling is a small slice
of that PR, not its own PR.

**PR-4 (LRR Phase 8 item 11, ~30 LOC of voice-tier coupling among the ~320 LOC of emphasis loop):**
- Emphasis threshold reads tier from state file.
- Tier → threshold scalar per §4.2 T3.

Ships when Phase 8 item 11 ships.

### §7.2 Risk and rollback

PR-1 is reversible by reverting the producer call site
(`apply_tier` returns to its prior CC-only behavior; the emit method
exists but is never called) and the consumer wire (`DirectorLoop`
returns to a per-tick pass that does not read the bus). The state file
is best-effort; consumers are tolerant to its absence.

PR-2's scoring-extension term ships at weight 0.0; rollback is a single
config edit to remove the term entry from `config/director_scoring.yaml`.

PR-3 and PR-4 each isolate the voice-tier coupling to a small section
of their host file; reversible without disturbing the surrounding
Phase 8 work.

---

## §8. Summary

The cross-zone wire D-01 has two halves:

1. **Mechanical wire (PR-1).** Producer call site in `vocal_chain.apply_tier`,
   consumer wire in `DirectorLoop._loop()` using the existing
   `ImpingementConsumer` (Option A). Latency ~30 s, complexity ~30 LOC
   of consumer plumbing, robust failure modes. Ships independently as
   a passive observable surface.

2. **Phase 8 tie-in (PR-2 / PR-3 / PR-4).** Voice tier becomes a
   first-class signal feeding the Phase 8 director scoring extension
   (item 3), the hero-mode camera switching (item 5), and the
   environmental salience emphasis (item 11). Coupling lives in those
   items' files, not in the director or the consumer. Voice tier
   modulates *visual content shaping* — this is the "hand in hand"
   relationship the operator named.

The consumer **does not pick the tier** (the
`VoiceTierSelector` does, per the canonical integration spec §1.3); it
**reads, exposes, and propagates** tier transitions so downstream
content-programming surfaces respond coherently with the audio. The
Objective schema stays voice-tier-agnostic; coupling lives in the
director's per-tick scoring, not in any data primitive's metadata.

— alpha, 2026-04-20
