# HOMAGE Scrim §5 — Choreographer FSM Extensions and Audio-Coupled Motion

**Status:** Research / design, operator-directed 2026-04-20.
**Authors:** cascade (Claude Opus 4.7, 1M).
**Governing anchors:**
- HOMAGE framework — `docs/superpowers/specs/2026-04-18-homage-framework-design.md`
- Nebulous Scrim system — `docs/research/2026-04-20-nebulous-scrim-design.md`
- Vocal chain — `agents/hapax_daimonion/vocal_chain.py:127`
- Vinyl chain — `agents/hapax_daimonion/vinyl_chain.py:1`
- Programme primitive — `shared/programme.py:1`
- Perceptual field — `shared/perceptual_field.py:83` (`MidiState`)
- Choreographer — `agents/studio_compositor/homage/choreographer.py:185`
- Substrate sources — `agents/studio_compositor/homage/substrate_source.py:53`
- Animation engine — `agents/studio_compositor/animation_engine.py:50` (`Transition`)
**Related prior art / memories:** `project_effect_graph`, `project_reverie_adaptive`, `feedback_no_expert_system_rules`, `project_programmes_enable_grounding`, `project_hardm_anti_anthropomorphization`, `feedback_director_grounding`, `feedback_grounding_exhaustive`.
**Scope:** Conceptual + algorithmic anchor for extending the HOMAGE choreographer FSM and coupling ward motion to audio. No code. No PR intent beyond a phased plan that downstream tickets will execute.

> "The wards must play in the scrim — never plopped, never pasted, but constantly dynamically interacting." — operator directive feeding this dispatch.

---

## §1 TL;DR

The HOMAGE choreographer today is a 4-state per-ward FSM (`ABSENT → ENTERING → HOLD → EXITING`, see `agents/studio_compositor/homage/transitional_source.py:44`) plus a per-tick reconciler that mediates concurrency, package-palette broadcast, and a 4-float coupling payload (`agents/studio_compositor/homage/choreographer.py:651-684`). It is conservative by design — every ward only renders content while in `HOLD`, transitions are paint-and-cut, and substrate sources skip the FSM entirely (`agents/studio_compositor/homage/substrate_source.py:53`). This is correct as a *baseline of restraint*. It is wrong as a *terminal aesthetic*, because it produces the "plopped or pasted" quality the operator's directive (`Scrim §5`) explicitly forbids: appear, sit, disappear, no inhabiting motion in between.

This dispatch proposes:

1. **Five new FSM states**, layered as a co-state on top of the existing four:
   - `TRANSITING` — the ward is sliding to a new Z-position behind the scrim.
   - `ORBITING` — the ward is caught in a slow circular drift while remaining HOLD-rendered.
   - `TRAPPED` — the ward is stuck inside the scrim's atmosphere, oscillating with low amplitude.
   - `ECHO` — a delayed phantom of a recent state, fading.
   - `WAKE` — a residual disturbance (scrim eddy) left by a recent ward exit.

2. **Three audio-coupled motion protocols** to commit to first, in priority order:
   - **P1 — Beat-locked transit:** when MIDI transport is `PLAYING` (`shared/perceptual_field.py:83`), wards quantize Z-axis `TRANSITING` to bar boundaries. Free-flow drift in between.
   - **P2 — Granular-wash drift current:** when `vinyl_source.spray > 0.30` (`agents/hapax_daimonion/vinyl_chain.py:111`), all wards inherit an ambient drift current applied as a small `position_offset_x/y` modulation per frame.
   - **P3 — Vocal-chain emphasis punch-through:** when `vocal_chain.intensity > 0.65` (`agents/hapax_daimonion/vocal_chain.py:128`), the *single* ward currently in `EMPHASIZED` (or the highest-salience ward in `HOLD`) briefly punches through scrim opacity (`alpha → 1.0`, `scale_bump_pct → +6%`) for ~700ms then decays.

3. **Programme integration** as soft priors via `ProgrammeConstraintEnvelope` (`shared/programme.py:85`): three new variants (`deep-water-mode`, `current-mode`, `still-pool-mode`) that bias ward state-distribution targets without ever pinning a specific ward.

4. **No conductor**: cross-ward coordination is boids-style ([Reynolds 1987](https://www.red3d.com/cwr/boids/)) plus Conway-style local-rule emergence (the choreographer remains a scheduler, not a director-with-intent). Composite-emergence is detected post-hoc and amplified for ≤4 beats only.

5. **HARDM stays anti-anthropomorphic**. None of the new motion vocabulary uses biological language (no swim, no breathe, no school, no hunt). Motion is *physical* — drift, eddy, attractor, advect — and described as such.

The doc below builds these claims out.

---

## §2 Choreographer Audit (Current State)

### §2.1 What the choreographer does today

`agents.studio_compositor.homage.choreographer.Choreographer.reconcile()` is the single arbiter of "nothing plopped or pasted." Per-tick lifecycle:

1. **Feature-flag check** (`choreographer.py:282`). `HAPAX_HOMAGE_ACTIVE=0` short-circuits to a zero-energy payload — emergency rollback path.
2. **Consent-safe swap** (`choreographer.py:292`). If `/dev/shm/hapax-compositor/consent-safe-active.json` exists, the package is swapped to its consent-safe variant (grey palette, empty corpus). Same downstream code path; wards inherit the restricted palette.
3. **Read pending transitions** from `/dev/shm/hapax-compositor/homage-pending-transitions.json` (`choreographer.py:468-508`). These are `PendingTransition(source_id, transition, enqueued_at, salience)` records (`choreographer.py:117-131`).
4. **HARDM anchor synthesis** (`choreographer.py:308`, `choreographer.py:519-559`): if HARDM bias > unskippable threshold and no real HARDM entry is pending, synthesize one at the current bias salience. This is the only built-in "always-recruit" override.
5. **Read rotation mode** (`choreographer.py:563-603`). Cascade: narrative-tier per-tick override (≤60s old) → slow structural director → default (`weighted_by_salience`, cascade-delta 2026-04-18, `choreographer.py:613`).
6. **Substrate filter** (`choreographer.py:322-326`): drop pending entries for `SUBSTRATE_SOURCE_REGISTRY` ids (`reverie_external_rgba`, `reverie`, `album` — `substrate_source.py:53`). Reverie's vocabulary graph is permanent generative substrate; never enters FSM.
7. **Package-palette broadcast** (`choreographer.py:331`, `choreographer.py:940-982`): write `homage-substrate-package.json` so Reverie can tint without an FSM transition.
8. **Voice-register broadcast** (`choreographer.py:337`, `choreographer.py:986-1016`).
9. **`paused` rotation early return** (`choreographer.py:347-351`).
10. **Partition pending into `_ENTRY` / `_EXIT` / `_MODIFY`** (`choreographer.py:180-182`, `choreographer.py:353-362`). Unknown transitions are rejected.
11. **Salience sort** (`choreographer.py:372-374`) when `weighted_by_salience`.
12. **Concurrency cap** (`choreographer.py:376-389`): `max_simultaneous_entries`, `max_simultaneous_exits` from `package.transition_vocabulary`.
13. **Netsplit-burst gate** (`choreographer.py:392-400`): only one burst per `netsplit_burst_min_interval_s`.
14. **Metrics** (`choreographer.py:403`).
15. **Publish `WardEvent` per planned transition** (`choreographer.py:410`, `choreographer.py:422-464`) to the ward↔FX bus for shader-side reactions.
16. **Compute + publish coupling payload** (`choreographer.py:415-416`, `choreographer.py:651-711`). The 4-float payload is `(active_transition_energy, palette_accent_hue_deg, signature_artefact_intensity, rotation_phase)`.

### §2.2 The per-source FSM

Per-ward FSM lives in `HomageTransitionalSource` (`transitional_source.py:44`):

```
ABSENT  --apply_transition(default_entry)-->  ENTERING  --internal-->  HOLD
HOLD    --apply_transition(exit-class)----->  EXITING   --internal-->  ABSENT
```

Plus an implicit `EMPHASIZED` reading: `_MODIFY` transitions (`topic-change`, `mode-change`, `netsplit-burst`) map to `HOLD_TO_EMPHASIZED` on the ward↔FX bus (`choreographer.py:451-452`). `EMPHASIZED` is not a separate state; it is a transient brightening of `HOLD` — a `WardEvent` with `intensity=0.75` that the FX bus reacts to.

Substrate sources skip the FSM entirely. They render continuously and receive only the package-palette broadcast.

### §2.3 What triggers each transition?

| Transition | Trigger | Source |
|---|---|---|
| Pending `_ENTRY` | Producer (compositional consumer, chat reactor, narrative director, structural director) writes to `homage-pending-transitions.json` | `compositional_consumer.py:1` and structural director |
| Pending `_EXIT` | Same producers, or symmetric exit on rotation cadence | as above |
| Pending `_MODIFY` (`topic-change` etc.) | Programme transitions, narrative beats | narrative director |
| `netsplit-burst` | Glitch / impingement / chaos accent | rate-limited at `netsplit_burst_min_interval_s` |
| HARDM synthetic anchor | `hardm_source.current_salience_bias() > UNSKIPPABLE_BIAS` | `choreographer.py:519-559` |

Cooldowns: `netsplit_burst_min_interval_s` (in `package.transition_vocabulary`). Hysteresis: none currently — the FSM is one-shot per pending entry. Compositional consumer alpha-modulation (`agents/studio_compositor/animation_engine.py`) is a separate channel: ward `alpha`, `scale`, `glow_radius_px`, `position_offset_x/y` flow through `Transition` records appended to `ward-animation-state.json` (`animation_engine.py:28`, `animation_engine.py:36-47`). The choreographer does *not* author those transitions today — it only schedules FSM moves.

### §2.4 Gaps relative to "wards play in scrim"

| Gap | Today | Required |
|---|---|---|
| **Z-position motion** | Ward sits at fixed assignment | Z-axis drift between front-of-scrim and back-of-scrim |
| **Inter-state drift** | Ward in `HOLD` is geometrically static (only its content is alive) | Ward in `HOLD` slowly orbits / drifts according to scrim currents |
| **Audio coupling** | Coupling payload reads ward-side state into shader uniforms | Shader / audio-side state needs to flow *back* into ward motion |
| **Beat-quantized scheduling** | Pending entries fire on the next reconcile tick (~10–30 Hz) | Beat-quantized transit fires on bar / 2-bar / 4-bar boundaries when `transport_state == PLAYING` |
| **Cross-ward coordination** | Per-ward decisions; concurrency cap is the only coordination | Boids-style alignment + attractor/repulsor fields |
| **Echo / wake** | Exit is destructive — ward goes from `HOLD` to `EXITING` to `ABSENT` | Exit leaves a fading `ECHO` and a scrim `WAKE` ripple |
| **Idle-period self-motion** | If no producer enqueues, the scrim is dead apart from rotation_phase | Even with no pending, 1–2 wards in slow `ORBITING` and scrim self-motion |
| **Cap on simultaneous transit** | Concurrency caps cover entries/exits, not transit | Need a separate `max_simultaneous_transit` so the scrim never feels frantic |

These gaps are what §3–§10 address.

---

## §3 State-Space Extensions

**Architectural choice:** the new states are a *co-state*, not replacements. Every ward has an `(fsm_state, motion_state)` tuple. `fsm_state ∈ {ABSENT, ENTERING, HOLD, EMPHASIZED, EXITING}` (the existing five, with `EMPHASIZED` promoted to a real state). `motion_state ∈ {STILL, TRANSITING, ORBITING, TRAPPED, ECHO, WAKE}`. The tuple ranges are constrained — `ABSENT` wards must be `STILL`, `EXITING` wards may only be `STILL` or `WAKE`-emitting, etc. (matrix in §3.7).

This is conventional [hierarchical FSM design](https://www.gameaipro.com/GameAIPro3/GameAIPro3_Chapter12_A_Reusable_Light-Weight_Finite-State_Machine.pdf) — the lifecycle FSM (existing) is the *outer* HFSM; the motion FSM (new) is a sub-FSM that runs inside non-`ABSENT` states. The pattern keeps complexity at O(states_outer + states_inner) rather than the O(states_outer × states_inner) flat-FSM blowup ([Inspiaaa/UnityHFSM](https://github.com/Inspiaaa/UnityHFSM)).

### §3.1 `TRANSITING` — Z-axis motion

**Definition.** Ward is moving from one Z-position behind the scrim to another. Z is depth into the scrim ([0.0, 1.0] where 0 = pressed against the audience-side surface, 1 = lost in the deepest atmospheric haze). Transit happens at a finite velocity (typically ~0.20 Z-units/sec at base tempo), interpolated by `_ease_in_out_cubic` (`animation_engine.py:78`).

**Entry triggers (any of):**
- Beat-locked transit (P1, §4.1) on bar boundary while `transport_state == PLAYING`.
- Programme-driven transit when the active programme's `current-mode` envelope (§7.2) sets `ward_emphasis_target_rate_per_min ≥ 6.0`.
- Stimmung `exploration_deficit > 0.35` (`shared/stimmung` → `Stance.SEEKING`) — when boredom signal aggregates per `feedback_grounding_over_giq`, scrim wants to "show new thing" via more transits.
- Operator override (§8).

**Exit triggers:**
- Z-target reached. State transitions to `STILL` (default) or `ORBITING` (if Programme bias is `deep-water-mode`).

**Hysteresis.** No new transit may be initiated within `min_transit_interval_s` (default 4.0s) of the same ward's last transit completion. Prevents oscillating between two Z-positions every bar.

**Cooldown.** Global `max_simultaneous_transit` (default 2). One bar's worth of transits cannot exceed this even at high tempo.

### §3.2 `ORBITING` — slow circular drift

**Definition.** Ward in `HOLD` is rendering content while its `position_offset_x/y` are modulated by a slow Lissajous (orbit radius ≤ 18px at standard density, ≤ 36px at Programme `deep-water-mode`). Period: 12–20s. Phase is per-ward, randomized at orbit entry.

**Entry triggers:**
- Default for `HOLD` wards under `deep-water-mode` (§7.1).
- Long-`HOLD` ambient default: any ward in `HOLD` for > `orbit_idle_threshold_s` (default 8.0s) without a `_MODIFY` event drifts into `ORBITING`.
- After-`TRANSITING` settle: the receiving Z-position can declare "settle to orbit" instead of "settle to still."

**Exit triggers:**
- Outgoing `EXITING` transition cancels orbit (orbit decays to current center).
- `EMPHASIZED` event freezes orbit phase (ward "stops to speak") for the emphasis duration.
- Programme switches away from `deep-water-mode`.

**Hysteresis.** Orbit radius decays linearly over `orbit_decay_s` (default 1.2s) on exit so the ward doesn't snap to its center.

### §3.3 `TRAPPED` — low-amplitude oscillation

**Definition.** Ward is "stuck" inside the scrim's atmosphere — `position_offset_x/y` oscillate with low amplitude (≤ 6px) at audio-rate-coupled frequency. Trapped wards do not transit until released. This is the scrim-as-medium speaking back to the ward; the medium *holds* the ward.

**Entry triggers:**
- Granular-wash drift current is *very* high (`vinyl_source.density > 0.85` AND `vinyl_source.spray > 0.6`) — the medium is so thick that wards cannot transit through it.
- Stimmung `tension > 0.75` AND `valence < 0.3` — the medium is anxious and grips.
- Hysteresis floor: must persist ≥ 2.0s before entry to prevent oscillation.

**Exit triggers:**
- Releasing audio condition lifts (and 3.0s have passed — release hysteresis).
- Operator override.

**Programme veto.** `still-pool-mode` programme reduces `TRAPPED` entry probability by 0.5× (the still pool is too quiet for the scrim to grip — it just holds without trapping).

### §3.4 `ECHO` — delayed fading phantom

**Definition.** When a ward exits `EMPHASIZED` (or completes a `topic-change` `_MODIFY`), an `ECHO` is left at the ward's pre-emphasis Z-position with the ward's content snapshot, alpha-decaying linearly over `echo_decay_s` (default 800ms). The echo is rendered *behind* the live ward — the audience sees a brief afterimage of where the ward was when it spoke.

**Entry triggers:**
- `HOLD → EXITING` (exit class, not modify-class) — leaves an `ECHO` at the exit point.
- `EMPHASIZED → HOLD` (after `_MODIFY` punch-through) — leaves an `ECHO` at the punch-through peak Z-position.

**Exit triggers:**
- Time-based: alpha reaches 0.

**Lineage.** Maya Deren's *Meshes of the Afternoon* (1943) double-exposure as temporal layering vocabulary — the same space seen through itself at different moments, cited in scrim §2.2.4. ([Meshes of the Afternoon](https://en.wikipedia.org/wiki/Meshes_of_the_Afternoon).) Also: Kubrick/Trumbull slit-scan (scrim §2.2.5) — temporal smearing as scrim grammar.

**Cap.** `max_simultaneous_echoes` (default 4) — caps the GPU cost. Oldest echo evicted on overflow.

### §3.5 `WAKE` — scrim disturbance from exit

**Definition.** When a ward fully exits (`EXITING → ABSENT`), the scrim itself ripples in the ward's recent neighborhood for `wake_decay_s` (default 1.5s). This is *not* a ward state — it's a state the scrim atmosphere holds, attached to a screen-space coordinate. It modulates `noise.amplitude` and `drift.direction` on Reverie's substrate locally. Implementation: a `ScrimWake` record published to a new `/dev/shm/hapax-compositor/scrim-wakes.json` SHM file; the wgpu pipeline samples it as a small additional uniform array.

**Entry triggers:**
- Any ward `EXITING → ABSENT` boundary.
- `ECHO` fade-out (smaller wake than a fresh exit; "ghost wake").

**Exit triggers:**
- Time-based decay to imperceptible amplitude.

**Cap.** `max_simultaneous_wakes` (default 6 — wakes are cheap; just a small uniform array).

### §3.6 State transition diagram (combined)

```
                              [ STILL ] ─── orbit_idle_threshold_s ───► [ ORBITING ]
                                  │                                          │
                       beat boundary │                                          │ EMPHASIZED
                       OR           │                                          │ event
                       programme    ▼                                          ▼
                       bias    [ TRANSITING ]                              (orbit pause)
                                  │                                          │
                                  │ Z-target reached                         │
                                  ▼                                          ▼
                              [ STILL ] ◄──────────────────────── [ ORBITING ]
                                  │                                          ▲
                                  │ density+spray very high                  │
                                  ▼                                          │
                              [ TRAPPED ]                                    │
                                  │                                          │
                                  │ release condition + hysteresis           │
                                  ▼                                          │
                              [ STILL ] ──────────────────────────────────────┘

   Exit-class transition         ┌─► [ ECHO ]   (at pre-exit Z, fades)
   from any motion state ───────┤
                                  └─► [ WAKE ]   (scrim atmosphere ripples at exit screen-space)
```

### §3.7 `(fsm_state, motion_state)` matrix

| `fsm_state` \ `motion_state` | `STILL` | `TRANSITING` | `ORBITING` | `TRAPPED` | `ECHO` | `WAKE` |
|---|---|---|---|---|---|---|
| `ABSENT` | ✓ default | — | — | — | — | — |
| `ENTERING` | ✓ default | — | — | — | — | — |
| `HOLD` | ✓ | ✓ | ✓ | ✓ | — | — |
| `EMPHASIZED` | ✓ default | — | — | — | — | — |
| `EXITING` | ✓ default | — | — | — | emits ECHO | emits WAKE |

`ECHO` and `WAKE` are *emitted* by exit (they live as separate records in their own SHM files), not occupied as ward motion states. The matrix above shows valid current ward motion. The grid is sparse on purpose — most `(fsm, motion)` cells should be illegal so the choreographer can validate.

### §3.8 Hysteresis and flapping prevention

Every motion-state transition implements [bang-bang hysteresis](https://en.wikipedia.org/wiki/Bang%E2%80%93bang_control) with explicit thresholds, mirroring the [thermostat pattern](https://en.wikipedia.org/wiki/Hysteresis):

- `STILL → TRANSITING`: requires *upward* threshold crossing. No reverse transit until `min_transit_interval_s` elapses.
- `STILL → ORBITING`: requires `orbit_idle_threshold_s` of continuous quiet `HOLD` time.
- `* → TRAPPED`: requires entry condition for ≥ `trapped_entry_dwell_s` (default 2.0s) of continuous true.
- `TRAPPED → STILL`: requires release condition for ≥ `trapped_release_dwell_s` (default 3.0s).

The two-threshold (entry vs release) hysteresis prevents the ward from oscillating around a single decision boundary — the same engineering principle that prevents thermostats from clicking on and off rapidly when ambient temperature sits at the setpoint.

---

## §4 Audio-Driven Motion Protocols

All four couplings below are **soft priors**, never hard gates, per `feedback_no_expert_system_rules`. They modulate transition probabilities, never override the choreographer's existing concurrency / Programme / consent logic. Architectural axiom from `feedback_grounding_exhaustive`: every ungrounded "couple X to Y" is either grounded (right) or should be deterministic code (also right — the couplings here are deterministic, with grounded LLM directors providing the *meaning* behind the bias values via Programme).

### §4.1 P1 — Beat-locked transit (HIGHEST PRIORITY)

**When.** `MidiState.transport_state == "PLAYING"` (`shared/perceptual_field.py:88`) AND `MidiState.tempo` is fresh AND working_mode is not `fortress` (livestream gating).

**What.** Pending `TRANSITING` entries are *not* fired immediately by the choreographer's reconcile tick. Instead, they accumulate in a per-ward "next-bar queue" and fire on the next bar boundary. The bar boundary is computed from `MidiState.bar_position` modulo 1.0 crossing zero with a small lookahead (~50ms scheduling jitter cushion).

**Quantization grain matrix:**

| Transition phase | Quantization | Rationale |
|---|---|---|
| `_ENTRY` (ward appears) | 1-bar | Entries must land on the downbeat — Pina Bausch motif-on-the-beat anchor ([Bausch tanztheater motif repetition](https://en.wikipedia.org/wiki/Pina_Bausch)). |
| `_EXIT` (ward disappears) | 2-bar | Exits feel "finished" if they land 2 bars after entry; gives the ward a perceptible duration. |
| `_MODIFY` (`topic-change`, `mode-change`) | 1-bar | Modifications respect the bar so they don't smear the rhythm. |
| `netsplit-burst` | unquantized | Bursts are accents — quantizing them would defang the shock. |
| `ORBITING` enter / orbit phase | none | Orbit period is independent of bar (subjective scrim time, not bar time). |
| `TRANSITING` Z-motion | duration matches `n × bar_length_s` for `n ∈ {1, 2, 4}` | Transit feels musical when its envelope aligns to the bar. |

**Algorithm sketch (Python pseudocode, pure):**

```python
def schedule_pending_with_beat_quantization(
    pending: list[PendingTransition],
    midi: MidiState,
    now: float,
) -> tuple[list[PendingTransition], list[PendingTransition]]:
    """Return (fire_now, defer_to_next_bar) split."""
    if midi.transport_state != "PLAYING" or midi.tempo is None:
        return pending, []  # free-flow
    bar_length_s = 4.0 * 60.0 / midi.tempo  # 4/4 default
    bar_pos = midi.bar_position or 0.0
    # Time until next bar boundary
    s_to_next_bar = (1.0 - bar_pos) * bar_length_s
    # Quantization windows per phase
    quant_window_bars = {"entry": 1, "exit": 2, "modify": 1}
    fire_now: list[PendingTransition] = []
    defer: list[PendingTransition] = []
    for p in pending:
        phase = phase_of(p.transition)
        if phase == "burst":
            fire_now.append(p)
            continue
        # Defer to next bar boundary
        defer.append(p)
    return fire_now, defer
```

The deferred entries persist in a small per-tick list; on the next reconcile tick whose `now` crosses the bar boundary, they fire.

**Grounding bridge.** The grounded narrative director (`agents/studio_compositor/director_loop.py`) sees `MidiState.transport_state` in its `<perceptual_field>` block. It can choose to bias the *next* transitioning ward via `salience` so the bar-locked fire chooses the right one. This is grounding-flexibility-over-IQ per `feedback_grounding_over_giq`.

**Reference.** Beat-tracking literature: [librosa's beat_track](https://deepwiki.com/librosa/librosa/5.2-beat-tracking-and-tempo-estimation) uses dynamic programming + onset detection function ([Mercity audio analysis](https://books.mercity.ai/books/Audio-Analysis-and-Synthesis---Introduction-to-Audio-Signal-Processing/audio_analysis_techniques/07_Onset_Detection_and_Beat_Tracking)) — but Hapax has a stronger signal: OXI One transport_state is *known* tempo, not estimated, so quantization is exact. ([An Interactive Beat Tracking and Visualisation System](https://www.researchgate.net/publication/2382205_An_Interactive_Beat_Tracking_and_Visualisation_System) for the visualizer-side coupling theory; [Real-Time Beat Tracking with Zero Latency](https://transactions.ismir.net/articles/10.5334/tismir.189) for ISMIR-side state of art.)

### §4.2 P2 — Granular-wash drift current (SECOND PRIORITY)

**When.** `vinyl_source.spray > 0.30` (`agents/hapax_daimonion/vinyl_chain.py:111`) — the granular wash is sufficiently spread that it reads as ambient atmosphere, not a discrete sound. Mode D (Granular wash) per the broadcast safety doc.

**What.** A global drift current vector `(dx_per_s, dy_per_s)` is computed from `(vinyl_source.spray, vinyl_source.density, vinyl_source.stereo_width)`. All `HOLD`-state wards receive an additive `position_offset_x/y` per frame applied as a slow `Transition` (`animation_engine.py:50`) appended to `ward-animation-state.json`. Magnitude is small (≤ 8 px/s base, scaled by `spray`).

**Direction vector.** From `stereo_width`: when `stereo_width > 0.5`, drift is left-to-right or right-to-left depending on the spectral skew sign. When `stereo_width < 0.3`, drift is mostly vertical (top-down "settle" or bottom-up "rise" depending on `position_drift`). The direction is *one* per scrim, not per ward — boids alignment trivially achieved.

**Velocity scaling.** `drift_speed = base_speed × (0.5 + 0.5 × spray)`. So `spray=0.30` gives 65% of base speed; `spray=1.0` gives 100%. Below `spray=0.30`, no drift — the medium is too clean to have a current.

**Boundary condition.** Wards that drift past the layout's bounding rect wrap to the opposite edge with a small `WAKE` ripple at the wrap point (so the wrap doesn't look like a teleport). The wake is what sells the wrap as "passing through the scrim" rather than "snapping to the other side."

**Programme veto.** `still-pool-mode` programme zeroes drift speed regardless of spray — the still pool refuses to be carried by a current. This is a Programme prior, not a hard gate; the multiplier is set to 0.05 (not 0.0) so a true Mode D burst can still impart minimal motion.

### §4.3 P3 — Vocal-chain emphasis punch-through (THIRD PRIORITY)

**When.** `vocal_chain.intensity > 0.65` (`agents/hapax_daimonion/vocal_chain.py:128`) AND there is exactly one ward currently in `EMPHASIZED` (or, if none, the highest-salience ward in `HOLD`).

**What.** That ward briefly punches through scrim opacity:

```python
# In response to vocal_chain.intensity > 0.65 spike:
append_transitions([
    Transition(ward, "alpha", current_alpha, 1.0, 0.15, "ease-out-quad", now),
    Transition(ward, "scale_bump_pct", 0, 6.0, 0.20, "ease-out-quad", now),
    Transition(ward, "glow_radius_px", current_glow, current_glow + 12, 0.25, "ease-out-quad", now),
])
# Then 700ms later, decay back:
append_transitions([
    Transition(ward, "alpha", 1.0, default_alpha, 0.45, "ease-in-out-cubic", now + 0.70),
    Transition(ward, "scale_bump_pct", 6.0, 0, 0.50, "ease-in-out-cubic", now + 0.70),
    Transition(ward, "glow_radius_px", current_glow + 12, current_glow, 0.55, "ease-in-out-cubic", now + 0.70),
])
```

**Decay timing rationale.** Vocal intensity peaks last ~150–300ms in normal speech; the punch-through holds slightly longer (~700ms total) so the audience can register the visual emphasis. Decay is `ease-in-out-cubic` so the return to scrim feels like "settling back into the medium" rather than "snapping back to base."

**Cap.** Only one ward punches through per second. Hysteresis: `vocal_chain.intensity` must drop below 0.45 before another punch-through is allowed (re-arm threshold).

**Anti-anthropomorphization invariant.** This is *not* "the ward speaks louder when Hapax speaks louder." It is "vocal energy is an audio signal that modulates scrim opacity, and the most-salient ward is the surface that local change registers on." The grounded director may interpret it as the former; the deterministic code remains the latter. Per `project_hardm_anti_anthropomorphization`.

### §4.4 Stimmung-driven scrim density

**When.** Continuously, every reconcile tick.

**What.** `stimmung.tension` modulates the *base* `ORBITING` orbit period and `TRANSITING` velocity:

| `tension` band | `orbit_period_s` multiplier | `transit_velocity_z_per_s` multiplier |
|---|---|---|
| < 0.3 (calm) | 0.85× (faster orbits — playful) | 1.0× |
| 0.3 – 0.55 (neutral) | 1.0× | 1.0× |
| 0.55 – 0.75 (rising) | 1.20× (slower orbits — drift) | 0.85× (transits feel weighted) |
| > 0.75 (high) | 1.50× (slowest orbits — stuck) | 0.70× (transits drag) |

`stimmung.energy` modulates `Z` target distribution: low energy → wards prefer deep Z (back of scrim); high energy → wards prefer shallow Z (closer to audience-side). This is *not* a per-ward decision — it shifts the prior distribution from which the structural director draws Z targets.

### §4.5 Exploration-deficit pulse

**When.** `stance == SEEKING` (set when `exploration_deficit > 0.35` per VLA aggregation per `project_exploration_signal`).

**What.** Increase the rate of `TRANSITING` decisions by 1.5×. Rationale: under SEEKING, recruitment threshold halves (`project_exploration_signal`) so more wards appear; the choreographer's complementary move is more *motion among those wards* so the audience reads the scene as searching. The Programme primitive controls the upper bound: `current-mode` programme tolerates up to 12 transits/min; `still-pool-mode` caps at 2/min.

This is the same pattern as the Reverie mixer's recruitment-threshold halving: a stance-driven multiplier on a continuous prior, never a hard switch.

---

## §5 Beat-Quantized vs Free-Flow Motion

Different operator postures want different relations to time. The four routing modes from the broadcast safety doc map directly:

| Operator mode | Audio character | Motion grammar | Quantization |
|---|---|---|---|
| **A — Selector** | Discrete vinyl drops, bar-aligned mixing | Light, rare beat-quantized accents over otherwise still scrim | 4-bar `_ENTRY`, 8-bar `_EXIT` (sparse). `ORBITING` long period (24s+). |
| **B — Turntablist** | Active manipulation, tempo-locked scratching | Strong beat-quantized — every transit on a downbeat | 1-bar `_ENTRY`, 2-bar `_EXIT`. Punch-through bound to `vocal_chain.intensity`. |
| **C — Bed-panic-mute** | Bed track + mic + selective mute | Hybrid: beat-quantized for entries; free-flow for exits | 1-bar `_ENTRY`, free-flow `_EXIT`. |
| **D — Granular-wash** | Continuous granular, no rhythm | All free-flow. P2 (granular drift) dominates. P1 silent. | None. Drift current is continuous. |

These routing modes are operator-driven, not LLM-decided. The Programme primitive selects which mode is active per `monetization_opt_ins` and `consent_scope`. The choreographer reads the active Programme via the existing structural-director cascade (`choreographer.py:563-603`) — Programmes set a soft prior for which quantization grid is active.

**Hybrid rule.** Even in Mode A (Selector), a single `_MODIFY` per minute is allowed unquantized — this is the "operator gesture" channel. The operator's intent (a deliberate accent) overrides the bar grid, with a small `WAKE` ripple to soften the unquantized arrival.

**Reference for the quantization-vs-free-flow tradeoff.** Lucinda Childs' minimalist work ([early choreography](https://en.wikipedia.org/wiki/Lucinda_Childs); [A Steady Pulse](http://danceworkbook.pcah.us/asteadypulse/texts/refusal.html)) is the load-bearing precedent for *strict quantization yielding emergent richness via tiny variation* — Mode B aspires to this discipline. Anna Halprin's RSVP-cycles ([Halprin biography](https://en.wikipedia.org/wiki/Anna_Halprin); [Halprin task scores](https://annahalprindigitalarchive.omeka.net/biography)) are the load-bearing precedent for *task-based free-flow within rule envelopes* — Mode D approximates this: the rule is "drift with the granular wash"; the actuation is free.

---

## §6 Cross-Ward Coordination (No Conductor)

The choreographer remains a scheduler, not a director-with-intent (per anti-anthropomorphization invariants, §11). Cross-ward coordination is *emergent* from local rules, never centrally orchestrated. Three mechanisms compose:

### §6.1 Boids-style flocking ([Reynolds 1987](https://www.red3d.com/cwr/boids/))

For wards in `ORBITING`, the per-tick orbit-center delta is influenced by the three boids rules:

- **Separation:** if any neighbor ward is within `boid_separation_radius_px` (default 80px), this ward's orbit center repels by a small force.
- **Alignment:** this ward's orbit phase is nudged toward the average orbit phase of neighbors within `boid_alignment_radius_px` (default 200px). Tiny effect — phase nudge ≤ 5°/sec.
- **Cohesion:** this ward's orbit center is nudged toward the centroid of `HOLD` neighbors within `boid_cohesion_radius_px` (default 400px). Even tinier — ≤ 1 px/sec.

These three forces compose multiplicatively with the granular drift current (P2) and the stimmung scrim-density modulator. Per [Reynolds' original formulation](https://www.csc.kth.se/utbildning/kth/kurser/DD143X/dkand11/Group5Lars/carl-oscar_erneholm.pdf), the emergent character of the flock comes from local-only rules with no global coordinator. ([Boids Wikipedia](https://en.wikipedia.org/wiki/Boids); [emergent-behaviour visualisation](https://www.doc.ic.ac.uk/~nuric/posts/ai/boids/).)

**Anti-anthropomorphization compliance.** The boids rules are described in physics terms (separation force, alignment angle, cohesion centroid), not biological terms (no "schools," no "friends," no "wants to be near"). The math is fish; the description is electromagnetism. See §11.

### §6.2 Attractor / repulsor fields

Certain ward families have *family-level* attraction or repulsion:

| Family A | Family B | Force | Rationale |
|---|---|---|---|
| BitchX wards | BitchX wards | weak attraction (cohesion bonus) | Same package, same lineage — they "collect" |
| BitchX wards | HARDM wards | strong repulsion | HARDM is anti-anthropomorphic; BitchX is conversational. They compete for register. |
| Camera wards | Camera wards | strong separation | Two cameras side-by-side defeat their hero-frame purpose |
| Album wards | Camera wards | weak attraction (alignment bonus) | Album cover + camera-of-vinyl form a natural compound |

Implementation: a `WARD_FAMILY_FORCES` matrix in a new `agents/studio_compositor/homage/coordination.py` module, consulted per-tick by the orbit-center update. Forces compose with boids rules (§6.1).

This is the standard force-field-flocking approach Susan Amkraut pioneered and which underlies particle-system flocking in commercial tools today ([Amkraut force-field flocking](https://ohiostate.pressbooks.pub/graphicshistory/chapter/19-2-flocking-systems/); [Particle Flocker for Maya](https://www.particleflocker.com/); [Babylon.js particle attractors](https://forum.babylonjs.com/t/particle-attractors/58176)).

### §6.3 Composite-emergence detection and amplification

A *composite* is a moment when 2–3 wards' states align coincidentally (without any centralized choreography). E.g., three BitchX wards all enter `EMPHASIZED` within a 200ms window; or a camera ward and an album ward arrive at adjacent Z-positions during the same bar.

The choreographer post-hoc detects composites by scanning the `WardEvent` bus output (`choreographer.py:422`) per tick. When a composite is detected, it AMPLIFIES the alignment for ≤ 4 beats: the involved wards' orbit phases lock to a shared phase, then drift apart again. The lock is *brief* and *bounded* — the choreographer is not authoring the composite, only noticing and accentuating it.

This is the "phrase structure" the operator's directive calls for: a ward emphasis triggers a 4-beat coordinated event involving 2–3 neighbors.

**Reference.** Conway's Game of Life ([Wikipedia](https://en.wikipedia.org/wiki/Conway's_Game_of_Life); [Scholarpedia](http://www.scholarpedia.org/article/Game_of_Life)) — gliders, oscillators, and other persistent patterns *emerge* from local rules without a designer specifying them. The composite-detection-and-amplification approach treats the ward grid as a Class-4 [Wolfram cellular automaton](https://en.wikipedia.org/wiki/Cellular_automaton): repetitive structures emerge unpredictably; we notice them and let them bloom slightly before re-randomizing. ([Wolfram's classification](https://ics.uci.edu/~eppstein/ca/wolfram.html); [Rule 30](https://en.wikipedia.org/wiki/Rule_30).)

**Stigmergy.** The whole system is stigmergic: producers leave traces (pending transitions, salience scores) in a shared medium (`/dev/shm/hapax-compositor/*.json`), and the choreographer + animation engine respond to those traces without any central plan. ([Stigmergy Wikipedia](https://en.wikipedia.org/wiki/Stigmergy); [stigmergy as universal coordination](https://www.researchgate.net/publication/279058749_Stigmergy_as_a_Universal_Coordination_Mechanism_components_varieties_and_applications); [stigmergic optimization for multi-agent AI](https://medium.com/@jsmith0475/collective-stigmergic-optimization-leveraging-ant-colony-emergent-properties-for-multi-agent-ai-55fa5e80456a).) This is consistent with the council's broader filesystem-as-bus architecture and with the SCM (Stigmergic Cognitive Mesh) per `project_scm_formalization`.

---

## §7 Programme Primitive Integration

The Programme primitive (`shared/programme.py:85`) gives Hapax-authored programmes a soft-prior surface that the choreographer reads. The fields below extend `ProgrammeConstraintEnvelope` with motion-state biases. Per `feedback_hapax_authors_programmes`, the operator does not write these — Hapax authors them.

### §7.1 `deep-water-mode` Programme variant

**Purpose.** "We are far inside the scrim — slow, deep, atmospheric. Listening, not speaking."

**Constraint envelope additions:**
```yaml
constraint_envelope:
  motion_state_biases:
    transiting_weight: 0.4   # multiplier on TRANSITING entry probability
    orbiting_weight: 1.6     # prefer ORBITING
    trapped_weight: 1.2      # slightly more TRAPPED
    still_weight: 0.7        # less STILL
  orbit_period_s_multiplier: 1.4   # slower orbits
  transit_velocity_multiplier: 0.7  # slower transits
  z_target_bias: 0.65               # bias Z targets toward back of scrim
  beat_quantization_strictness: 0.3 # mostly free-flow
```

**Use cases.** `LISTENING`, `AMBIENT`, `WIND_DOWN` programme roles (`shared/programme.py:64`).

### §7.2 `current-mode` Programme variant

**Purpose.** "We are riding a current — beat-driven, transitive, flowing."

**Constraint envelope additions:**
```yaml
constraint_envelope:
  motion_state_biases:
    transiting_weight: 1.8    # prefer TRANSITING
    orbiting_weight: 0.6      # less ORBITING
    trapped_weight: 0.3       # rarely TRAPPED
    still_weight: 0.7
  orbit_period_s_multiplier: 0.85  # faster orbits when they happen
  transit_velocity_multiplier: 1.2  # faster transits
  z_target_bias: 0.40               # mid-scrim
  beat_quantization_strictness: 0.95 # strict quantization
  ward_emphasis_target_rate_per_min: 8.0
```

**Use cases.** `SHOWCASE`, `EXPERIMENT`, `HOTHOUSE_PRESSURE`.

### §7.3 `still-pool-mode` Programme variant

**Purpose.** "Wards rest. The scrim is a pool, not a current."

**Constraint envelope additions:**
```yaml
constraint_envelope:
  motion_state_biases:
    transiting_weight: 0.15   # very rare transits
    orbiting_weight: 0.5      # gentle orbits only
    trapped_weight: 0.05      # almost never trapped
    still_weight: 1.8         # mostly still
  orbit_period_s_multiplier: 1.8   # slowest orbits
  transit_velocity_multiplier: 0.5
  z_target_bias: 0.55              # mid-scrim, neutral
  beat_quantization_strictness: 1.0 # if it transits, on the bar
  ward_emphasis_target_rate_per_min: 1.5
  drift_current_multiplier: 0.05    # near-immune to granular drift (P2)
```

**Use cases.** `RITUAL`, `INTERLUDE`, `WIND_DOWN`.

### §7.4 Validator extension

`ProgrammeConstraintEnvelope`'s field validators must reject negative or zero weights to maintain the architectural axiom (`shared/programme.py:115` already does this for capability biases). The new `motion_state_biases.*_weight` and `*_multiplier` fields must inherit the same `(0.0, ∞)` constraint — zero would be a hard gate, which is forbidden.

### §7.5 Hapax-authored programme synthesis

Per `feedback_hapax_authors_programmes`, Programmes are Hapax-authored. The choreographer does not synthesize Programmes; it consumes them. The narrative director (`agents/studio_compositor/director_loop.py`) selects an active Programme variant per its 30s tick based on `<perceptual_field>` (current music genre, contact-mic activity, vocal chain state, stimmung, watched note context). The structural director (90s tick) confirms or overrides at the slower cadence.

---

## §8 Operator Override Path

### §8.1 Per-ward state pin

**Surface.** A new `command_server` UDS command: `homage.ward_pin {ward_id, motion_state, ttl_s}`. Pins the named ward to a motion state for `ttl_s` seconds, then auto-releases. Only `STILL`, `ORBITING`, `TRANSITING` (with a target Z) are pinnable; `TRAPPED`, `ECHO`, `WAKE` are emergent and cannot be operator-forced.

**Implementation note.** The existing `command_server` (`agents/studio_compositor/command_server.py`) does not currently expose ward-state commands. This is a small extension — register a new domain `homage` with a `ward_pin` command. Mirror the exposure in the Logos `commandRegistry` (`hapax-logos/src/lib/commands/`) so the operator can issue it from keyboard / Stream Deck / `window.__logos.execute("homage.ward_pin", {...})`.

### §8.2 Stream Deck "freeze all motion" panic

**Surface.** A dedicated Stream Deck button writes a sentinel file `/dev/shm/hapax-compositor/homage-freeze-motion.json` (atomic tmp+rename). The choreographer checks for this file every reconcile tick; when present, all motion-state transitions are suppressed until the file is removed. `TRANSITING` wards complete their current motion and settle to `STILL`. `ORBITING` wards decay to their orbit centers. `TRAPPED` wards release.

**Recovery.** A second press of the button removes the sentinel. Wards resume normal Programme-biased behavior.

**Rationale.** Per `feedback_consent_latency_obligation`, operator stop-signal must be honored within one reconcile tick. The freeze button is the visual analogue of the audio panic-mute (Mode C).

### §8.3 Programme override via post-merge-queue G3 degradation

**Surface.** When the system enters `DEGRADED-STREAM` mode (per `project_homage_go_live_directive`), the active Programme is force-swapped to a `still-pool-mode` variant (§7.3) so the scrim self-quiets while the operator addresses the degradation. This is *not* a panic-mute — Hapax keeps producing — but the scrim's motion vocabulary collapses to its quietest mode.

---

## §9 Animation Engine Integration

### §9.1 Cadence relationship

| Engine | Tick rate | Owner |
|---|---|---|
| Choreographer reconcile | ~10 Hz (compositor tick rate) | `Choreographer.reconcile()` |
| Animation engine evaluate | per-frame (~30–60 Hz) | `evaluate_transition()` (`animation_engine.py:116`) |
| MIDI clock readback | ~24 PPQN (~96 Hz at 120 BPM) | `MidiState.beat_position` |
| Vocal chain CC update | impingement-driven (~5–20 Hz) | `vocal_chain.py:127` `DIMENSIONS` |
| Vinyl chain CC update | impingement-driven, programme-gated | `vinyl_chain.py:184` `DIMENSIONS` |

The choreographer publishes *intentions* at its rate (10 Hz). The animation engine *interpolates* the intentions per-frame. This is the standard scheduler / animator split.

### §9.2 New `Transition` types

`animation_engine.py:36` `SUPPORTED_PROPERTIES` already covers `alpha`, `scale`, `scale_bump_pct`, `glow_radius_px`, `border_pulse_hz`, `position_offset_x/y`, `border_radius_px`. The new motion states require:

- **`ScrimTransit`**: a `Transition` on `position_offset_x` + `position_offset_y` + a new `z_position` property. Requires adding `z_position` to `SUPPORTED_PROPERTIES` and threading it through the wgpu compositor pipeline so the substrate shader can read per-ward depth (drift-pass parameter modulation, blur kernel scaled by depth).
- **`Orbit`**: not a single `Transition` — a *parameterized* loop. Implementation choice: either (a) emit a stream of short `Transition` records that re-up every ~200ms with the next Lissajous step, or (b) extend the engine to support a new `OrbitTransition` type with `(center_x, center_y, radius, period_s, phase, started_at)` fields and an `evaluate_orbit()` function. Option (b) is cleaner.
- **`EchoFade`**: a `Transition` on `alpha` from current value to 0.0 over `echo_decay_s` on a *snapshot* of the ward's content. Requires the compositor to snapshot ward content on `EXITING → ABSENT` and treat the snapshot as a separate render target. Not trivial — needs a small ECHO renderer in the compositor.
- **`WakeRipple`**: not a ward transition — a *scrim* transition. Lives in a new `/dev/shm/hapax-compositor/scrim-wakes.json` SHM file consumed by the wgpu pipeline.

### §9.3 Choreographer → animation engine handoff

The choreographer's `reconcile()` already publishes `WardEvent` records to the bus and the 4-float coupling payload. To author per-frame motion, it additionally calls `animation_engine.append_transitions([...])` with the new `Transition` records. Today the choreographer does not author `Transition` records — `compositional_consumer.dispatch_ward_choreography` does. This dispatch proposes the choreographer becomes a *producer* of `Transition` records as well, for the motion-state vocabulary.

Conflict resolution: per-property last-write-wins (already documented at `animation_engine.py:160-164`). The choreographer's motion-state transitions and the compositional consumer's narrative-driven transitions occupy disjoint property surfaces (motion state owns `position_offset_x/y`, `z_position`; compositional consumer owns `alpha`, `glow_radius_px`, `scale_bump_pct`).

---

## §10 The "Constant Dynamic Interaction" Cadence

The operator's directive: the scrim must NEVER be static. Even at idle, something subtly moves. But never frantic. "Always alive at a controlled pulse."

**The four-layer pulse:**

| Layer | Source | Rate | Always-on? |
|---|---|---|---|
| **L0 — Substrate self-motion** | Reverie's `noise → rd → drift → breath → feedback` 8-pass graph | Per-frame (60 Hz) | YES — independent of FSM |
| **L1 — Ward orbit** | At least 1 `HOLD` ward in `ORBITING`, default-on after `orbit_idle_threshold_s` | 12–20s period | YES (when ≥1 ward in `HOLD`) |
| **L2 — Ward transit** | Beat-locked `TRANSITING` when transport playing; programme-biased when not | 1–4 bar quantum, or programme-biased free-flow rate | Conditional |
| **L3 — Composite events** | Detected by composite-emergence scan (§6.3); rare | ~once per 30–90s expected | Emergent |

**Cap on simultaneous active transitions** (the "noise floor"):

- `max_simultaneous_transit` = 2 (per §3.1)
- `max_simultaneous_emphasized` = 1 (only one ward speaks at a time)
- `max_simultaneous_echoes` = 4
- `max_simultaneous_wakes` = 6 (wakes are cheap; just shader uniforms)
- Total motion-event budget per 4 bars ≤ 8 events. Above this, the choreographer rejects with `motion-budget-exceeded` and emits a Prometheus counter.

**Idle-period handling.** When `pending == []` for ≥ `idle_threshold_s` (default 15s):

- L0 substrate self-motion continues (Reverie unaffected).
- The choreographer synthesizes a single `ORBITING → STILL → ORBITING` transition for one randomly-chosen `HOLD` ward every `idle_orbit_refresh_s` (default 30s). This is the "ambient pulse" — barely perceptible, but signals continued aliveness.
- HARDM anchor (`choreographer.py:519-559`) continues to fire if its bias exceeds threshold — independent of idle handling.
- After `deep_idle_threshold_s` (default 90s), one of the existing wards is encouraged to `TRANSITING` to a deeper Z position to mark "we are settling deeper." This is a soft prior; if no producer fires, no transit happens.

**The aesthetic floor.** Borrowing Brian Eno's generative-music vocabulary: the scrim is "ever-different and changing" without being eventful. Eno's *Bloom* and *Reflection* ([generativemusic.com](https://www.generativemusic.com/); [Reflection](https://www.generativemusic.com/reflection.html); [Bloom](https://generativemusic.com/bloom.html)) are the load-bearing precedent — a system that listens to itself and is endlessly varied without being agitated. ([Eno generative-music overview](https://en.wikipedia.org/wiki/Generative_music); [How Generative Music Works](https://teropa.info/loop/); [Voyage into Eno's generative music](https://www.soundoflife.com/blogs/people/brian-eno-generative-music).)

---

## §11 Anti-Anthropomorphization Invariants (HARD)

Per `project_hardm_anti_anthropomorphization` and `feedback_hapax_authors_programmes`, this dispatch is governed by hard invariants on language and behavior. These are non-negotiable.

### §11.1 Wards do not "want" anything

Every motion described above is a *physical response to a field*. The boids rules are *forces*. The granular drift is a *current*. The orbit is a *Lissajous trajectory parameterized by audio*. There is no per-ward intent. The choreographer is a scheduler that recruits motion via the affordance pipeline (per `project_unified_recruitment` — every recruitment passes through the single `AffordancePipeline`).

### §11.2 Motion language is physics, not biology

Forbidden words in code, comments, dispatch messages, metrics labels, log lines, and user-facing surfaces:

- `swim`, `swimming` (the operator's brief uses "swim" but the *implementation* must avoid it; metaphor stays in design docs only)
- `breathe`, `breathing`, `inhale`, `exhale` (Bachelard amendments did breathe — that was rejected for substrate-side; here even more so for wards)
- `school`, `flock` (the algorithm is `boids` but ward families are not "schools")
- `friend`, `companion`, `crowd`
- `wiggle`, `dance`, `play` (operator's brief uses "play" but the implementation describes it as "modulate motion state per audio coupling")
- `scared`, `excited`, `happy`, `sad` (no affect attribution to wards; affect is operator-side stimmung, ward motion is a downstream consequence)

Allowed: `drift`, `transit`, `orbit`, `oscillate`, `advect`, `displace`, `attract`, `repel`, `decay`, `propagate`, `ripple`, `eddy`, `current`, `field`, `force`.

### §11.3 Cross-ward coordination is not "schools of friends"

The boids algorithm is biologically inspired but the implementation describes it in terms of *separation distance*, *alignment angle*, *cohesion centroid*. Reynolds himself ([red3d.com](https://www.red3d.com/cwr/boids/)) used the term "boids" precisely because it abstracted the implementation away from "birds." This dispatch follows that abstraction discipline.

### §11.4 The choreographer is a scheduler, not a director-with-intent

Per the existing `Choreographer` docstring (`choreographer.py:1`): "single arbiter of 'nothing plopped or pasted'." It is a deterministic reconciler — it reads pending transitions and applies concurrency rules. The grounded *director* (narrative director, structural director) is where intent lives. This dispatch does not change that boundary; it gives the scheduler more vocabulary, not more autonomy.

### §11.5 Composite-emergence is detected, not authored

§6.3's composite-emergence amplification *notices* alignments and briefly accentuates them. It does not *cause* alignments. The accentuation is bounded (≤ 4 beats) and silent on the alignment's content (the choreographer doesn't know *why* three wards aligned, only that they did). This preserves the Cunningham/Cage chance-operations principle ([Merce Cunningham chance method](https://en.wikipedia.org/wiki/Merce_Cunningham); [chance choreography study](https://fiveable.me/dance-american-cultures/unit-10/merce-cunningham-chance-choreography/study-guide/3dYfk6ajdtEOM3rx); [MerceDay 8 — chance operations](https://www.alastairmacaulay.com/all-essays/2lexwxwjlae73euk2wfe8amds6njls); [Cunningham SFU thesis on chance](https://www.sfu.ca/~tschipho/publications/Schiphorst_M.A.Thesis.pdf)): *the structure emerges from independent processes; the choreographer simply lets the audience see it*.

### §11.6 HARDM stays raw

The HARDM communicative-anchor synthesis (`choreographer.py:519-559`) bypasses the affordance-pipeline gate when bias exceeds the unskippable threshold. It does *not* gain motion-state vocabulary in this dispatch. HARDM remains `STILL` always — raw signal-density on a grid, no orbit, no transit, no echo, no wake. This is the "visual twin of CVS #16 persona anti-personification" per the HARDM memory.

---

## §12 Concrete Code-Shapes

### §12.1 `WardChoreographerState` Pydantic model

```python
# new file: agents/studio_compositor/homage/ward_state.py
from __future__ import annotations
from enum import StrEnum
from pydantic import BaseModel, ConfigDict, Field

class FsmState(StrEnum):
    ABSENT = "absent"
    ENTERING = "entering"
    HOLD = "hold"
    EMPHASIZED = "emphasized"
    EXITING = "exiting"

class MotionState(StrEnum):
    STILL = "still"
    TRANSITING = "transiting"
    ORBITING = "orbiting"
    TRAPPED = "trapped"

class OrbitParams(BaseModel):
    model_config = ConfigDict(frozen=True)
    center_x: float
    center_y: float
    radius_px: float = Field(gt=0.0, le=64.0)
    period_s: float = Field(gt=4.0, le=40.0)
    phase_rad: float = 0.0

class TransitParams(BaseModel):
    model_config = ConfigDict(frozen=True)
    target_z: float = Field(ge=0.0, le=1.0)
    velocity_z_per_s: float = Field(gt=0.0, le=0.6)
    started_at: float

class WardChoreographerState(BaseModel):
    """Per-ward motion state held by the choreographer.

    The lifecycle FSM (`fsm_state`) and the motion FSM (`motion_state`)
    are independent axes. Validity matrix per §3.7.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    ward_id: str
    fsm_state: FsmState
    motion_state: MotionState

    current_z: float = Field(ge=0.0, le=1.0, default=0.5)
    target_z: float = Field(ge=0.0, le=1.0, default=0.5)

    orbit: OrbitParams | None = None
    transit: TransitParams | None = None

    last_motion_transition_t: float = 0.0
    last_emphasis_t: float | None = None

    boid_neighbors: tuple[str, ...] = ()  # for cross-ward coordination
```

### §12.2 Programme YAML for `current-mode` variant

```yaml
# 50-templates/programme-current-mode.yaml
name: current-mode
status: pending
role: showcase
duration_s: 1800
constraint_envelope:
  capability_bias_positive:
    "fx.family.audio-reactive": 1.4
  capability_bias_negative:
    "fx.family.calm-textural": 0.6
  preset_family_priors:
    - audio-reactive
    - glitch-dense
  homage_rotation_modes:
    - weighted_by_salience
  homage_package: bitchx
  ward_emphasis_target_rate_per_min: 8.0
  motion_state_biases:
    transiting_weight: 1.8
    orbiting_weight: 0.6
    trapped_weight: 0.3
    still_weight: 0.7
  orbit_period_s_multiplier: 0.85
  transit_velocity_multiplier: 1.2
  z_target_bias: 0.40
  beat_quantization_strictness: 0.95
  display_density: standard
```

### §12.3 Beat-quantized transit decision pseudocode

```python
def maybe_quantize_transit(
    pending: list[PendingTransition],
    midi: MidiState,
    now: float,
    deferred: list[tuple[PendingTransition, float]],  # (entry, fire_at)
) -> tuple[list[PendingTransition], list[tuple[PendingTransition, float]]]:
    """Return (fire_now, new_deferred).

    Fires deferred entries whose fire_at has elapsed. Defers new entries
    to next bar boundary when transport is playing.
    """
    fire_now: list[PendingTransition] = []
    next_deferred: list[tuple[PendingTransition, float]] = []

    # 1. Fire any deferred entries whose time has come
    for entry, fire_at in deferred:
        if fire_at <= now:
            fire_now.append(entry)
        else:
            next_deferred.append((entry, fire_at))

    # 2. Decide each new pending: fire now or defer
    if midi.transport_state != "PLAYING" or midi.tempo is None:
        fire_now.extend(pending)
        return fire_now, next_deferred

    bar_length_s = 4.0 * 60.0 / midi.tempo
    bar_pos = midi.bar_position or 0.0
    s_to_next_bar = (1.0 - bar_pos) * bar_length_s

    for p in pending:
        phase = phase_of(p.transition)  # entry / exit / modify / burst
        if phase == "burst":
            fire_now.append(p)
        elif phase == "entry":
            next_deferred.append((p, now + s_to_next_bar))
        elif phase == "exit":
            # 2-bar quantization for exits
            s_to_next_2bar = s_to_next_bar + bar_length_s if bar_pos > 0.5 else s_to_next_bar
            next_deferred.append((p, now + s_to_next_2bar))
        elif phase == "modify":
            next_deferred.append((p, now + s_to_next_bar))

    return fire_now, next_deferred
```

### §12.4 Updated FSM diagram (combined lifecycle + motion)

```
LIFECYCLE FSM (existing 5 states):

  ABSENT --apply_transition(entry)--> ENTERING --internal--> HOLD
                                                              │
                          ┌────────────_MODIFY event──────────┤
                          ▼                                   │
                   EMPHASIZED ──decay──> HOLD                 │
                                                              │
  HOLD --apply_transition(exit)--> EXITING --internal--> ABSENT
                                       │             │
                                       │             └─emits WAKE
                                       └─emits ECHO

MOTION FSM (new 4 occupied states + 2 emitted):

  Within { HOLD }:

    STILL ─orbit_idle_threshold─> ORBITING ─emphasis event─> STILL
       │                              │
       │ beat boundary OR programme   │ Z-target reached
       │ bias OR seeking pulse        │
       ▼                              ▼
    TRANSITING ─arrival─> STILL ─density+spray very high+dwell─> TRAPPED
                                                                    │
                                                                    │ release condition + dwell
                                                                    ▼
                                                                  STILL

  Emitted-on-exit (not occupied): ECHO (per ward), WAKE (per scrim region)
```

### §12.5 New SHM files introduced by this dispatch

| Path | Writer | Reader | Purpose |
|---|---|---|---|
| `/dev/shm/hapax-compositor/ward-motion-state.json` | `Choreographer` | compositor render | per-ward `WardChoreographerState` snapshot |
| `/dev/shm/hapax-compositor/scrim-wakes.json` | `Choreographer` | wgpu Reverie pipeline | array of `(x, y, t_started, decay_s, amplitude)` |
| `/dev/shm/hapax-compositor/scrim-echoes.json` | `Choreographer` | compositor render | array of `(ward_id, content_snapshot_id, z, t_started, decay_s)` |
| `/dev/shm/hapax-compositor/homage-freeze-motion.json` | operator (Stream Deck / command_server) | `Choreographer` | freeze-all-motion sentinel |
| `/dev/shm/hapax-compositor/beat-deferred-transitions.json` | `Choreographer` | `Choreographer` | persists deferred quantized entries across reconcile ticks (so a process restart doesn't lose them) |

### §12.6 Prometheus metric additions

- `hapax_homage_ward_motion_state{ward_id, motion_state}` — gauge, one-hot per ward
- `hapax_homage_motion_transition_total{from_state, to_state, trigger}` — counter
- `hapax_homage_beat_quantization_defer_total{phase}` — counter (entries deferred to next bar)
- `hapax_homage_composite_emergence_detected_total` — counter
- `hapax_homage_motion_budget_exceeded_total` — counter
- `hapax_homage_scrim_wake_active` — gauge (count of active wakes)
- `hapax_homage_scrim_echo_active` — gauge (count of active echoes)
- `hapax_homage_freeze_motion_active` — gauge (0/1)

All emitted from `shared/director_observability.py` via `emit_homage_*` functions following the existing pattern (`choreographer.py:729-739`).

---

## §13 Open Questions

1. **Z-axis rendering.** Does the wgpu compositor pipeline currently support per-ward depth modulation (drift-pass parameter scaled by depth, blur kernel scaled by depth)? §9.2 assumes yes. If not, that's a separate spec.

2. **Echo-snapshot rendering cost.** Each `ECHO` requires a snapshot of the ward's content at exit time. For Cairo wards this is a `cairo.ImageSurface` copy (~1–4 MB depending on ward size). Capping at `max_simultaneous_echoes=4` keeps memory bounded but the snapshot+blit cost on the GStreamer streaming thread is unknown. May need to push echo rendering to a background thread per the existing `CairoSourceRunner` pattern (`cairo_source.py`).

3. **Boids per-frame cost.** With ~12 active wards in `HOLD`, boids is O(n²) — 144 distance comparisons per frame. Likely fine. With operator chat-recruited bursts up to 30+ wards, it's 900 comparisons. Probably fine. With pathological 100+ wards (denial-of-service via chat reactor), it's 10000. Need a `boid_neighbors` spatial-hash index if that's a real risk.

4. **Beat-deferred persistence on restart.** §12.5 proposes `/dev/shm/hapax-compositor/beat-deferred-transitions.json` to persist deferred entries across reconcile ticks. On compositor restart, do we replay deferred entries? Probably yes for ones whose `fire_at` is within the next 4 bars; drop the rest. Needs a TTL.

5. **Programme cross-fade.** When the active Programme switches from `current-mode` to `still-pool-mode`, do `motion_state_biases` cross-fade or hard-swap? Hard-swap risks "everything stops at once." Cross-fade over `programme_transition_s` (default 8.0s) is the safer default. Spec needs §7.6.

6. **`EMPHASIZED` formal promotion.** Today `EMPHASIZED` is implicit (a `WardEvent` intensity bump in `HOLD`). This dispatch promotes it to a real lifecycle state. Migration needs to update `transitional_source.py:44` `TransitionState` enum and ensure no consumer bug-breaks on the new value.

7. **Composite-emergence false-positive rate.** §6.3's detection scans `WardEvent` output per tick. What's the baseline coincidence rate at 6 wards × 10 Hz reconcile? May fire spuriously. Needs an empirical sweep — probably need a minimum 200ms-window-of-3-events threshold to suppress noise.

8. **Stream Deck button mapping.** The "freeze all motion" panic button needs a Stream Deck binding. This is operator-side configuration, not code. Document the mapping in `docs/studio/stream-deck-bindings.md` (does not yet exist — separate spec).

9. **Audio coupling under DEGRADED-STREAM.** When `DEGRADED-STREAM` mode is active per `project_homage_go_live_directive`, P1 (beat-locked transit) and P2 (granular drift) are effectively suppressed by the `still-pool-mode` programme override (§8.3). But P3 (vocal-chain emphasis) is independent. Should it also suppress under degradation? Probably yes — the operator is occupied, the scrim should not be punching through.

10. **Forsythe parametrization.** William Forsythe's "improvisation technologies" ([williamforsythe.com](https://www.williamforsythe.com/); [Improvisation Technologies academia](https://www.academia.edu/102620440/William_Forsythe_Improvisation_Technologies_and_beyond)) treat dance as a parameterized system over body-point relations. Could the orbit / transit parameters be exposed to the structural director as a Forsythe-style "parameter space" the LLM tunes per Programme? Worth a follow-on spec.

---

## §14 Sources

### Hapax codebase

- HOMAGE choreographer — `agents/studio_compositor/homage/choreographer.py:185`
- HOMAGE substrate sources — `agents/studio_compositor/homage/substrate_source.py:53`
- HOMAGE transitional source FSM — `agents/studio_compositor/homage/transitional_source.py:44`
- HOMAGE package — `shared/homage_package.py:1`
- Homage coupling — `shared/homage_coupling.py`
- Animation engine — `agents/studio_compositor/animation_engine.py:50`
- Vocal chain — `agents/hapax_daimonion/vocal_chain.py:127`
- Vinyl chain — `agents/hapax_daimonion/vinyl_chain.py:1`
- Programme primitive — `shared/programme.py:85`
- Perceptual field (`MidiState`) — `shared/perceptual_field.py:83`
- Compositional consumer — `agents/studio_compositor/compositional_consumer.py:1`
- Sibling: nebulous scrim design — `docs/research/2026-04-20-nebulous-scrim-design.md`
- Sibling: vinyl broadcast Mode B turntablist — `docs/research/2026-04-20-vinyl-broadcast-mode-b-turntablist-craft.md`
- Sibling: vinyl broadcast Mode D granular — `docs/research/2026-04-20-vinyl-broadcast-mode-d-granular-instrument.md`
- Sibling: vinyl collection broadcast safety — `docs/research/2026-04-20-vinyl-collection-livestream-broadcast-safety.md`

### Memory anchors (architectural axioms / feedback)

- `project_hardm_anti_anthropomorphization` — HARDM is anti-anthropomorphic
- `feedback_no_expert_system_rules` — soft priors only, no hard cadence/threshold gates
- `project_programmes_enable_grounding` — programmes EXPAND, never REPLACE
- `feedback_hapax_authors_programmes` — operator does not write programmes
- `feedback_grounding_exhaustive` — every move is grounded or deterministic
- `project_unified_recruitment` — single `AffordancePipeline` gates all expression
- `project_scm_formalization` — Stigmergic Cognitive Mesh
- `feedback_director_grounding` — director on grounded model under speed pressure
- `feedback_grounding_over_giq` — grounding flexibility over raw IQ

### Choreography theory

- Merce Cunningham — chance operations and dance composition
  - [Merce Cunningham — Wikipedia](https://en.wikipedia.org/wiki/Merce_Cunningham)
  - [How Cunningham reinvented dance — Dazed](https://www.dazeddigital.com/art-photography/article/44033/1/merce-cunningham-reinvented-radical-chance-technique-john-cage-dance)
  - [SFU thesis on Cunningham chance](https://www.sfu.ca/~tschipho/publications/Schiphorst_M.A.Thesis.pdf)
  - [Chance choreography study guide](https://fiveable.me/dance-american-cultures/unit-10/merce-cunningham-chance-choreography/study-guide/3dYfk6ajdtEOM3rx)
  - [MerceDay 8 — Macaulay on chance operations](https://www.alastairmacaulay.com/all-essays/2lexwxwjlae73euk2wfe8amds6njls)

- William Forsythe — choreographic objects, improvisation technologies
  - [William Forsythe — choreographicobjects.com](https://www.williamforsythe.com/)
  - [William Forsythe — Wikipedia](https://en.wikipedia.org/wiki/William_Forsythe_(choreographer))
  - [Improvisation Technologies — academia.edu](https://www.academia.edu/102620440/William_Forsythe_Improvisation_Technologies_and_beyond)
  - [Forsythe biography — Synchronous Objects](https://synchronousobjects.osu.edu/media/inside.php?p=forsythebio)
  - [Forsythe choreographic objects — ICA Boston](https://www.icaboston.org/exhibitions/william-forsythe-choreographic-objects/)

- Lucinda Childs — minimalist repetition with mathematical structure
  - [Lucinda Childs — Wikipedia](https://en.wikipedia.org/wiki/Lucinda_Childs)
  - [A Steady Pulse — restaging Childs](http://danceworkbook.pcah.us/asteadypulse/texts/refusal.html)
  - [Game Plan — Childs early works review](https://brooklynrail.org/2018/12/dance/Game-Plan-Lucinda-Childss-Early-Works-1963-1978/)

- Anna Halprin — task-based scores, RSVP cycles
  - [Anna Halprin — Wikipedia](https://en.wikipedia.org/wiki/Anna_Halprin)
  - [Halprin biography — digital archive](https://annahalprindigitalarchive.omeka.net/biography)
  - [Halprin moving legacy — SFMOMA Open Space](https://openspace.sfmoma.org/2017/10/anna-halprin-a-moving-legacy/)

- Pina Bausch — motif repetition, audience-direct address
  - [Pina Bausch — Wikipedia](https://en.wikipedia.org/wiki/Pina_Bausch)
  - [Audience manipulation in Kontakthof](https://research-repository.st-andrews.ac.uk/bitstream/handle/10023/5589/Weir_2014_SJoP_Audience.pdf?sequence=1&isAllowed=y)

### Generative-music systems

- Brian Eno — generative music
  - [GenerativeMusic.com — Eno + Chilvers apps](https://www.generativemusic.com/)
  - [Reflection (Eno generative app)](https://www.generativemusic.com/reflection.html)
  - [Bloom (Eno + Chilvers)](https://generativemusic.com/bloom.html)
  - [Generative music — Wikipedia](https://en.wikipedia.org/wiki/Generative_music)
  - [Overview of generative processes in Eno's work — HAL](https://hal.science/hal-03398725/document)
  - [How Generative Music Works — teropa](https://teropa.info/loop/)
  - [A Voyage Into the World of Brian Eno's Generative Music](https://www.soundoflife.com/blogs/people/brian-eno-generative-music)
  - [Eno's endless music machines — gorillasun](https://www.gorillasun.de/blog/brian-enos-endless-music-machines/)

### Boids and flocking

- Craig Reynolds — Boids (1987)
  - [Boids (Reynolds' authoritative page)](https://www.red3d.com/cwr/boids/)
  - [Boids — Wikipedia](https://en.wikipedia.org/wiki/Boids)
  - [Simulation of Boids — KTH](https://www.csc.kth.se/utbildning/kth/kurser/DD143X/dkand11/Group5Lars/carl-oscar_erneholm.pdf)
  - [On emergent behaviour, visualising boids — Imperial](https://www.doc.ic.ac.uk/~nuric/posts/ai/boids/)
  - [History of CG bird flocking — befores & afters](https://beforesandafters.com/2022/04/07/a-history-of-cg-bird-flocking/)
  - [Boids algorithm — Medium primer](https://medium.com/@tufayl/boids-a-flocking-algorithm-23039ff254a6)

### Force-field flocking and particle systems

- [Susan Amkraut force-field flocking — OSU graphics history](https://ohiostate.pressbooks.pub/graphicshistory/chapter/19-2-flocking-systems/)
- [Particle Flocker for Maya](https://www.particleflocker.com/)
- [Babylon.js particle attractors](https://forum.babylonjs.com/t/particle-attractors/58176)
- [Unity Particle System Force Field](https://docs.unity3d.com/Manual/class-ParticleSystemForceField.html)
- [Nature of Code — particle systems](https://natureofcode.com/particles/)

### Cellular automata and emergence

- Conway's Game of Life
  - [Conway's Game of Life — Wikipedia](https://en.wikipedia.org/wiki/Conway's_Game_of_Life)
  - [Game of Life — Scholarpedia](http://www.scholarpedia.org/article/Game_of_Life)
  - [Game of Life — LifeWiki](https://conwaylife.com/wiki/Conway's_Game_of_Life)

- Wolfram cellular automata
  - [Cellular automaton — Wikipedia](https://en.wikipedia.org/wiki/Cellular_automaton)
  - [Wolfram's classification — UCI](https://ics.uci.edu/~eppstein/ca/wolfram.html)
  - [Rule 30 — Wikipedia](https://en.wikipedia.org/wiki/Rule_30)
  - [Cellular automata — Stanford Encyclopedia of Philosophy](https://plato.stanford.edu/entries/cellular-automata/)
  - [Nature of Code — cellular automata](https://natureofcode.com/cellular-automata/)

### L-systems

- [L-system — Wikipedia](https://en.wikipedia.org/wiki/L-system)
- [L-systems intro — Wooster](https://csweb.wooster.edu/dbyrnes/cs220/lectures/pdffiles/LSystems.pdf)
- [L-systems for procedural generation — UMD CMSC 425](https://www.cs.umd.edu/class/fall2018/cmsc425/Lects/lect13-L-systems.pdf)

### Stigmergy and self-organization

- [Stigmergy — Wikipedia](https://en.wikipedia.org/wiki/Stigmergy)
- [Stigmergy and information cascades — Cornell INFO 2040](https://blogs.cornell.edu/info2040/2020/11/13/stigmergy-swarm-behavior-and-information-cascades/)
- [Expert assessment of stigmergy — Carleton](https://people.scs.carleton.ca/~arpwhite/stigmergy-report.pdf)
- [Stigmergy as universal coordination](https://www.researchgate.net/publication/279058749_Stigmergy_as_a_Universal_Coordination_Mechanism_components_varieties_and_applications)
- [Automatic design of stigmergy-based behaviours for robot swarms — Nature](https://www.nature.com/articles/s44172-024-00175-7)

### FSM design (game AI)

- [A Reusable, Light-Weight FSM — Game AI Pro 3](http://www.gameaipro.com/GameAIPro3/GameAIPro3_Chapter12_A_Reusable_Light-Weight_Finite-State_Machine.pdf)
- [Hierarchical FSM in Unity — UnityHFSM](https://github.com/Inspiaaa/UnityHFSM)
- [State pattern — Game Programming Patterns](https://gameprogrammingpatterns.com/state.html)
- [Tech Breakdown: AI with FSMs — Little Polygon](https://blog.littlepolygon.com/posts/fsm/)
- [HFSM for 2D character animation — ResearchGate](https://www.researchgate.net/publication/377277052_Implementation_of_Hierarchical_Finite_State_Machine_for_Controlling_2D_Character_Animation_in_Action_Video_Game)

### Hysteresis and control

- [Hysteresis — Wikipedia](https://en.wikipedia.org/wiki/Hysteresis)
- [Bang–bang control — Wikipedia](https://en.wikipedia.org/wiki/Bang%E2%80%93bang_control)
- [Hysteresis in digital control systems](https://www.hwe.design/theories-concepts/hysteresis)

### Beat tracking and music visualizers

- [Beat tracking and tempo estimation — librosa DeepWiki](https://deepwiki.com/librosa/librosa/5.2-beat-tracking-and-tempo-estimation)
- [Beat detection and BPM tempo estimation — Essentia](https://essentia.upf.edu/tutorial_rhythm_beatdetection.html)
- [Onset Detection and Beat Tracking — Mercity audio analysis](https://books.mercity.ai/books/Audio-Analysis-and-Synthesis---Introduction-to-Audio-Signal-Processing/audio_analysis_techniques/07_Onset_Detection_and_Beat_Tracking)
- [An Interactive Beat Tracking and Visualisation System — ResearchGate](https://www.researchgate.net/publication/2382205_An_Interactive_Beat_Tracking_and_Visualisation_System)
- [Real-Time Beat Tracking with Zero Latency — TISMIR](https://transactions.ismir.net/articles/10.5334/tismir.189)
- [Audio Analysis Techniques for Music Visualization](https://audioreactivevisuals.com/audio-analysis.html)

### Film / temporal-layering precedent

- [Meshes of the Afternoon (Maya Deren) — Wikipedia](https://en.wikipedia.org/wiki/Meshes_of_the_Afternoon)
