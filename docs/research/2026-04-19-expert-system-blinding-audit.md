# Expert-System Blinding-Rule Audit — what is masking recruitment failures

**Date:** 2026-04-19
**Branch:** `hotfix/fallback-layout-assignment` (audit doc only; no code changes)
**Operator directive (verbatim):** *"Make sure NO expert-system rules are blinding us to directorial impingement → recruitment failures."*
**Architectural axiom (memory `feedback_no_expert_system_rules.md`):** Behavior emerges from
`impingement → recruitment (cosine × base_level × context × Thompson) → role/persona`. No
hardcoded cadence, threshold, counter, or `if X then Y` rule may make a behavior decision
that should come from recruitment.

---

## 1. Executive summary

This audit sweeps `agents/studio_compositor/`, `agents/hapax_daimonion/`, and `shared/` for
gates that intercept, override, mask, or fabricate behavior the unified semantic recruitment
pipeline (`shared/affordance_pipeline.py`) is supposed to own. Findings:

| Category | Definition | Count |
|----------|------------|-------|
| **A — Behavior gates that mask recruitment failure (MUST RETIRE)** | Rule makes a behavior decision the pipeline should own | **14** |
| **B — Observability / infrastructure intervals (LEGITIMATE)** | Sample / poll / refresh cadence; not a behavior choice | 9+ (catalogued; not enumerated below) |
| **C — Safety / governance invariants (LEGITIMATE)** | Hard constraints the recruitment pipeline relies on | 5 |
| **D — Ambiguous (REQUIRES REVIEW)** | Recruitment alternative is unclear or requires new impingement shape | 6 |

**Of the 14 Category A rules, 4 have direct live evidence of currently masking failures
in the last 12 hours of operation.** Counts are taken from `journalctl --user -u
{studio-compositor,hapax-daimonion} --since "12 hours ago"` against the running daemon as
of 2026-04-19 ~06:00 UTC.

**Headline live evidence (2026-04-18 ~13:00 → 2026-04-19 ~06:00 UTC, 12 h):**

- `camera.hero variety-gate` rejected **6,358** recruitment outcomes
  (vs **45,178** total compositional dispatch attempts → **14.1 %** of all compositional
  recruitments are silently overridden by the variety-gate).
- `camera.hero dwell-gate` rejected an additional **373** recruitments
  (~3.0 / minute).
- `director narrative too similar to recent — emitting micromove fallback` fired
  **dozens of times** (40+ in the same 12 h window) — every fire substitutes a
  hardcoded **7-step rotating canned dispatch** for what would otherwise be a
  recruitment-driven move.
- `activity rotation FORCED` (the `_maybe_rotate_repeated_activity` enforcer)
  fired ≥ 11 times, including the absurd no-op `music → music (after 3
  consecutive)` (compositor PID 3536974, 2026-04-19 05:37:43 UTC) — strong
  evidence that the rule is firing without the recruitment pipeline being asked
  whether the LLM's repeated activity choice was actually wrong.
- `family-restricted retrieval (ward.highlight, prefix=ward.highlight.) returned
  no candidates from 50-wide window` was emitted **10 times** in the 12 h
  window. This is the recruitment pipeline literally telling us a director
  intent was dropped — and the structural-intent fallback dispatch quietly
  papers over it (see §5 for the trace).

**Top 3 rules to retire FIRST for maximum unmasking effect:**

1. `compositional_consumer.dispatch_camera_hero` variety-gate +
   dwell-gate (lines 187-217). Hides every recruitment outcome that lands on a
   recently-used camera. Currently overrides 6 % of all camera recruitments
   per minute.
2. `director_loop._maybe_rotate_repeated_activity` (lines 1293-1335). Forces
   activity-label rotation when LLM repeats; the rule fires even when the
   "repeat" is the actually-grounded answer for the moment, and substitutes a
   round-robin from a hardcoded 4-element list.
3. `director_loop._narrative_too_similar` + `_emit_micromove_fallback` (lines
   1210-1464). Treats Jaccard ≥ 0.35 OR 1 shared 3-shingle OR 2 shared bigrams
   as failure, then emits a hardcoded 7-step micromove cycle that has zero
   relationship to the perceptual field.

**Recruitment-pipeline gaps that need wiring BEFORE rules can be retired:**

1. `structural_intent` is a ceremonial JSON field that is not present in any
   director-intent JSONL record from the last 12 h, despite being declared
   mandatory in the prompt and dispatched on every tick. Either the LLM is
   not emitting it (in which case the prompt isn't doing its job) or the
   schema is being silently stripped. Either way, every "structural intent
   ward emphasis" the prompt promises is currently zero. The downstream
   `dispatch_structural_intent` call in `_emit_intent_artifacts` is doing
   no actual work most ticks.
2. The `narrative-structural-intent.json` SHM file was last updated >1 h
   before this audit, despite the narrative director ticking every 30 s.
   The choreographer is reading a stale `homage_rotation_mode` override
   for >120 ticks running.
3. `_retrieve_family("ward.highlight", prefix="ward.highlight.")`
   regularly returns 0 candidates. The catalog seed is missing
   ward-highlight-family capabilities for the wards the LLM names most
   frequently, OR the embedding cosine is too narrow. Camera.hero has the
   inverse problem (catalog has 6 cameras but the variety-gate suppresses
   most of them).

---

## 2. Methodology

### 2.1 Sweep patterns

Ran the operator-supplied grep patterns plus four targeted variants:

```
grep -rnE "time\.(monotonic|time)\(\)\s*-\s*\w+\s*[<>]=?\s*[0-9]" agents/ shared/
grep -rnE "if .*\.(count|ticks)\s*%\s*[0-9]+" agents/ shared/
grep -rnE "HAPAX_\w+_S\s*=|HAPAX_\w+_INTERVAL|HAPAX_\w+_CADENCE|HAPAX_\w+_THRESHOLD|HAPAX_\w+_COOLDOWN" agents/ shared/
grep -rnE "MIN_INTERVAL|MAX_INTERVAL|COOLDOWN|THRESHOLD|_INTERVAL_S\s*=" agents/ shared/
grep -rnE "variety.gate|repetition|_recent_\w+\s*=|rotation_mode" agents/ shared/
grep -rnE "_PRESET_BIAS_COOLDOWN|_LAST_PICK|MIN_DWELL|_MIN_DWELL_S|_camera_role_history|_recent_activities|_activity_rotation_idx|_micromove_cycle|video_streak"
```

### 2.2 Files read in full

- `shared/affordance_pipeline.py` (849 LOC) — the recruitment ground truth.
- `agents/studio_compositor/director_loop.py` (2,673 LOC) — the narrative director.
- `agents/studio_compositor/compositional_consumer.py` (1,235 LOC) — the dispatcher.
- `agents/studio_compositor/homage/choreographer.py` (987 LOC) — the rotation arbiter.
- `agents/studio_compositor/preset_family_selector.py` (382 LOC) — within-family pick.
- `agents/studio_compositor/follow_mode.py` (455 LOC) — operator-tracking hero.
- `agents/studio_compositor/random_mode.py` (186 LOC) — preset cycling loop.
- `agents/studio_compositor/twitch_director.py` (300 LOC) — deterministic sub-5s
  modulations.
- `agents/studio_compositor/activity_scoring.py` (333 LOC) — stimmung-modulated
  activity override.
- `agents/studio_compositor/environmental_salience_emphasis.py` (first 80 LOC).
- `agents/hapax_daimonion/cpal/runner.py` (569 LOC) — CPAL conversation loop.
- `agents/hapax_daimonion/cpal/impingement_adapter.py` (117 LOC) — CPAL gain/surface.
- `agents/hapax_daimonion/run_loops_aux.py` (712 LOC) — affordance dispatch loop.
- `shared/director_intent.py` (398 LOC) — schema for compositional/structural intent.

### 2.3 Live evidence

Two live data sources, captured 2026-04-19 ~06:00 UTC:

- `~/hapax-state/stream-experiment/director-intent.jsonl` (994 lines, 945 KB).
- `~/hapax-state/stream-experiment/structural-intent.jsonl` (473 KB).
- `journalctl --user -u {studio-compositor,hapax-daimonion} --since "12 hours ago"`.
- `/dev/shm/hapax-compositor/{ward-properties,narrative-structural-intent,
  homage-pending-transitions}.json` snapshots.

### 2.4 Classification rubric

- **A — MUST RETIRE.** Rule makes a behavior decision that should come from
  recruitment (which capability fires, which surface state changes, what is
  said, when).
- **B — LEGITIMATE.** Rule governs how often something is sampled, refreshed,
  logged, polled; absent the rule the system would still behave the same
  way, just measure or store more or less. Examples: `_RESEARCH_MARKER_CACHE_TTL_S
  = 5.0` (cache TTL), `TICK_INTERVAL_S = 0.15` (CPAL tick rate), `STALENESS_THRESHOLD_S
  = 2.0` (how stale before a perception signal is dropped).
- **C — LEGITIMATE BUT CITE.** Hard architectural invariant the recruitment
  pipeline depends on. Examples: consent fail-closed timeout
  (`_CONSENT_CACHE_TTL_S = 60.0` in `affordance_pipeline.py:38`), face-obscure
  fail-closed at livestream egress (council `CLAUDE.md` § Unified Semantic
  Recruitment), `min_length=1` on `DirectorIntent.compositional_impingements`
  (`director_intent.py:373`).
- **D — REVIEW.** The recruitment-driven alternative requires new impingement
  shapes or new capability families that don't exist yet.

---

## 3. Category A rules — masking recruitment failures (RETIRE)

### A1. `compositional_consumer.dispatch_camera_hero` — variety-gate

| Field | Value |
|-------|-------|
| File:Line | `agents/studio_compositor/compositional_consumer.py:198-206` |
| Constant | `_CAMERA_VARIETY_WINDOW = 3` (line 93) |
| What it gates | When recruitment selects a camera role that appears in the last 3 applied roles, the dispatcher refuses the swap (returns False without writing the override file). |
| Current default | Skip if proposed role appears in `_CAMERA_ROLE_HISTORY[-3:]`. |
| Recruitment failure it masks | Recruitment was *asked* (`AffordancePipeline.select(...)` ran, scored cam.hero capabilities, returned a winner). The variety-gate then silently *throws away the winner*. The operator sees a different hero than recruitment chose; they cannot tell whether recruitment was wrong, the pipeline was empty, or the gate intercepted. |
| Live evidence | **6,358 hits in 12 h** = 14 % of all compositional dispatches (45,178). Sample log line: `Apr 18 13:04:40 ... camera.hero variety-gate: c920-desk in recent ['c920-desk', 'brio-operator'], skipping` then immediately `Compositional dispatch: cam.hero.desk-c920.writing-reading → unknown (score=0.37)` — the score and capability_name confirm recruitment ran and the gate threw the result away. |
| Replacement impingement shape | Variety should emerge from recruitment, not be enforced post-hoc. (a) Add `recent_use_penalty` to `AffordancePipeline.select()` — already partly there as `c.base_level` decay. Strengthen the decay so a just-used capability scores lower naturally. (b) Emit per-camera `impingement(kind="visual_evidence", source="camera.<role>", strength=...)` per tick driven by what each camera actually shows. Recruitment then competes on real visual evidence. (c) If multiple impingements arrive simultaneously and all recruit the same camera, that IS the right answer for that tick. |
| Scope | M (1 dispatcher rewrite + new impingement shape from camera-classifications consumer) |

### A2. `compositional_consumer.dispatch_camera_hero` — dwell-gate

| Field | Value |
|-------|-------|
| File:Line | `agents/studio_compositor/compositional_consumer.py:187-197` |
| Constant | `_CAMERA_MIN_DWELL_S = 12.0` (line 92) |
| What it gates | Refuses to re-apply the same camera role within 12 s. |
| Current default | 12 s. |
| Recruitment failure it masks | If recruitment legitimately re-selects the same camera (e.g. operator stays at desk and the desk camera is still the right answer), the gate refuses on the ground that we "just did that"; the override file decays to TTL → fallback layout. Strong signal-following recruitment is invisible. |
| Live evidence | **373 hits in 12 h.** |
| Replacement impingement shape | TTL on the `hero-camera-override.json` file already provides natural dwell — if recruitment keeps re-electing the same camera every few ticks, the TTL gets refreshed and the camera stays held. No additional cooldown needed. |
| Scope | S |

### A3. `compositional_consumer.dispatch_camera_hero` — vision-gate (HARDER CASE)

| Field | Value |
|-------|-------|
| File:Line | `agents/studio_compositor/compositional_consumer.py:212-217` |
| Constant | `HAPAX_VISION_HERO_GATE` env (default ON) |
| What it gates | Rejects a camera if `per_camera_person_count[role] == 0` in the latest perception-state snapshot. |
| Current default | ON. |
| Recruitment failure it masks | Recruitment chose a camera with no people. This is a legitimate "wait, recruitment shouldn't be picking empty rooms" guard… BUT it papers over the underlying bug: the compositional capability catalog should encode "this camera is for showing the operator's hands at the desk" / "this camera shows the room as a wide" — and the affordance pipeline's cosine match should prefer the camera whose Gibson-verb description matches the perceptual evidence. If the LLM says "cut to the overhead turntable" and recruitment picks an empty room camera, that's a catalog-quality failure, not a "we need a hard gate" failure. |
| Live evidence | Rare in the 12 h window (<10) but pattern present. |
| Replacement impingement shape | Emit `impingement(perceived_subject=person/turntable/empty/...)` per camera each second. Cosine match against the recruited cam.hero capability's description does the right thing. Vision-gate becomes redundant. |
| Scope | M (depends on per-camera scene classifier work in `scene_classifier.py`) |

### A4. `director_loop._maybe_rotate_repeated_activity` — activity rotation enforcer

| Field | Value |
|-------|-------|
| File:Line | `agents/studio_compositor/director_loop.py:1293-1335` |
| Constants | `_ACTIVITY_VARIETY_WINDOW = 3` (line 1310), `_ROTATION = ("observe", "music", "study", "chat")` (line 1311) |
| What it gates | If the LLM's last 3 activity labels are all the same AND the proposed activity is the same again, the rule REPLACES the activity with the next entry from a hardcoded 4-element rotation list. |
| Current default | Hardcoded round-robin through observe/music/study/chat. |
| Recruitment failure it masks | The LLM's repeated activity choice MIGHT be the right answer for the perceptual field (operator is doing focused desk work for 4 minutes → "study" is correct). The rule treats repeat as failure and substitutes a label from a list, but the JSONL record then carries this label — downstream consumers see "study" rotated to "chat" with no actual change to the chat affordance recruitment, so chat looks active when it isn't. |
| Live evidence | Sample log: `Apr 19 00:37:43 ... activity rotation FORCED: music → music (after 3 consecutive)` — the rule fired and rotated music to music (idx wrap) — categorically wrong: the rule fired without checking whether the "right answer" had actually changed. |
| Replacement impingement shape | If activity is over-uniform, emit `impingement(kind="exploration_deficit", strength=high)` to the affordance pipeline. The exploration tracker already does this (`shared/exploration_tracker.py`). Let SEEKING / boredom-noise widen the activity score distribution naturally. |
| Scope | M (delete enforcer + verify exploration tracker covers the case in tests) |

### A5. `director_loop.PERCEPTION_INTERVAL` — narrative cadence timer

| Field | Value |
|-------|-------|
| File:Line | `agents/studio_compositor/director_loop.py:503` |
| Constant | `HAPAX_NARRATIVE_CADENCE_S` (default 30.0) |
| What it gates | Director only runs an LLM tick once per 30 s; in between, it sleeps. |
| Current default | 30 s. |
| Recruitment failure it masks | This is the canonical case from `feedback_no_expert_system_rules.md` precedent (2026-04-19 incident). If speech-recruitment fails every tick, we wouldn't know — the gate makes silence look intentional. Even with the silence-hold + micromove fallbacks added later, the *cadence itself* is a "wait N seconds before considering speech again" rule that bypasses recruitment. The right model: the director should be *recruited* on every fresh impingement, with the LLM call gated by capability cost (Thompson cost weighting already exists). |
| Live evidence | 994 director-intent JSONL records over ~33 h ≈ one tick per ~120 s in practice (with timeouts) — well over the nominal 30 s, suggesting LLM latency is the real cadence. |
| Replacement impingement shape | (a) Recruit a `narrative_director_tick` capability in response to a perceptual_field summary impingement; (b) cost weight = 1.0 if local, 0.3 if cloud; (c) Thompson sampling naturally throttles. Replace `PERCEPTION_INTERVAL` with capability-cost gating. |
| Scope | L |

### A6. `director_loop._narrative_too_similar` + `_emit_micromove_fallback`

| Field | Value |
|-------|-------|
| File:Line | `agents/studio_compositor/director_loop.py:1210-1264` (similarity check) + `1337-1464` (micromove fallback). |
| Constants | `_NARRATIVE_DEDUP_HISTORY_LEN = 15`, `_NARRATIVE_DEDUP_JACCARD = 0.35`, `_NARRATIVE_DEDUP_SHINGLE_K = 3`, `_NARRATIVE_DEDUP_BIGRAM_MIN_MATCHES = 2`, `_MUSIC_NARRATIVE_HISTORY_LEN = 10`. |
| What it gates | Compares LLM narrative against last 15 narratives by Jaccard, 3-shingle overlap, and 2-bigram overlap. If similar → throw away the LLM tick output entirely and emit a `_emit_micromove_fallback`. Micromove cycles through a hardcoded 7-element list of `(intent_family, narrative, material, ward_emphasis, rotation_mode)` tuples. |
| Current default | History 15, Jaccard 0.35, hardcoded 7-step cycle. |
| Recruitment failure it masks | Two failures: (i) the rule discards LLM output without checking whether the perceptual field actually changed (similar narrative + same field = correct repeat); (ii) the micromove fallback's 7 entries have zero relationship to perceptual evidence — they cycle deterministically. Operator sees "Hapax is doing things" but the things are pre-baked. |
| Live evidence | Dozens per 12 h (40+ instances grepped). Sample: 2026-04-18 19:03–19:42 fired 8× in 40 minutes — every single time the next surface move was one of the 7 hardcoded micromoves, not a recruitment-driven move. |
| Replacement impingement shape | Anti-repetition belongs *in* recruitment. Add an `impingement(kind="recently_said", text=last_narrative)` and let recruitment cosine-distance penalize too-similar speech capabilities. If recruitment STILL re-selects the same speech text, the perceptual field genuinely calls for it. The 7-step micromove cycle should be deleted entirely; "do something visible" is what recruitment is for. |
| Scope | L (delete dedup + micromove cycle + add recently-said impingement) |

### A7. `random_mode._PRESET_BIAS_COOLDOWN_S` — fallback to `neutral-ambient`

| Field | Value |
|-------|-------|
| File:Line | `agents/studio_compositor/random_mode.py:76, 99` |
| Constant | `_PRESET_BIAS_COOLDOWN_S = 20.0` |
| What it gates | If a `preset.bias` family was recruited within 20 s, defer to that family. Otherwise pick from `"neutral-ambient"` (hardcoded). |
| Current default | 20 s cooldown; fallback to hardcoded family. |
| Recruitment failure it masks | When recruitment hasn't fired a preset.bias, the loop ignores recruitment entirely and picks from a hardcoded family. This is documented as "no shuffle feel" but it's expert-system substitution. The operator can't tell whether recruitment chose neutral-ambient (it didn't — there's no neutral-ambient impingement) or whether it failed. |
| Live evidence | The recent-recruitment.json mechanic IS the bypass — `random_mode.py` reads the file directly to learn what was last recruited and treats absence as fallback rather than as "recruitment had nothing to say". |
| Replacement impingement shape | Random_mode is itself an expert-system rule. Replace with: a `preset_cycling_pressure` impingement emitted every N seconds; recruitment scores `fx.family.*` capabilities; if no winner, the GPU does nothing (preset stays). The current "uniform random" anxiety is a leftover from before recruitment landed. |
| Scope | M |

### A8. `twitch_director._STANCE_CADENCE` + per-stance always-on emission

| Field | Value |
|-------|-------|
| File:Line | `agents/studio_compositor/twitch_director.py:56-62, 83-84, 233-238` |
| Constants | `_STANCE_CADENCE` ranges from 3 s (SEEKING) to 30 s (CRITICAL); `_PRESSURE_FORCE_THRESHOLD = 6`; `_IDLE_VARIATION_CADENCE_S = 12.0`. |
| What it gates | A separate, deterministic non-LLM "twitch director" emits compositional impingements every 3-30 s based on stance, plus an "idle variation" `overlay.foreground.grounding-ticker` every 12 s when nothing else fires. Plus `if active_signals >= 6: emit "preset.bias.pressure-discharge"`. |
| Current default | Always-on cadence regardless of whether anything has actually changed in the field. |
| Recruitment failure it masks | These emissions ARE recruitment (they go through `compositional_consumer.dispatch`), so technically they're not bypassing the pipeline. BUT the *trigger* is hardcoded: "every 12 s if nothing else fired, push grounding-ticker". This invents impingements rather than letting them arise from perceptual evidence. The operator sees activity that isn't grounded in anything that happened. |
| Live evidence | Twitch director emissions are visible in the daimonion log every few seconds. Many `attention.winner.goal-advance` / `fx.family.glitch-dense` lines without correlated perceptual changes. |
| Replacement impingement shape | The hand-zone-change rule (line 192-200) is good — that's a real perceptual shift. Idle variation, pressure-forcing, and stance-cadence emission should all delete. If the stream feels "static" with nothing else firing, that's information about the operator's state — it should NOT be papered over with synthetic emphasis. |
| Scope | M (carefully — twitch has good rules and bad rules mixed) |

### A9. `activity_scoring.choose_activity_with_override` — stimmung override gate

| Field | Value |
|-------|-------|
| File:Line | `agents/studio_compositor/activity_scoring.py:207-333` |
| Constants | `DEFAULT_OVERRIDE_MARGIN = 0.08`, `DEFAULT_PROPOSAL_FLOOR = 0.55`, `DEFAULT_OVERRIDE_COOLDOWN_S = 60.0`, `DEFAULT_STIMMUNG_STALENESS_S = 90.0`. |
| What it gates | Scores every candidate activity against weighted (momentary, objective_alignment, stimmung_term); if best alternate beats LLM's choice by 0.08 AND proposed score ≤ 0.55 AND cooldown elapsed → override. |
| Current default | Override at 0.08 margin, 60 s cooldown. |
| Recruitment failure it masks | This is a parallel scoring system that competes with the affordance pipeline's recruitment of activity-related capabilities. Two scoring systems, two answers. Cooldown gate hides override failures (when the override is wrong, you can't tell because the rule won't fire again for 60 s). |
| Live evidence | Searched journal for `activity_override` — no recent hits, suggesting override is rarely firing OR the cooldown is permanently active. Either way, the parallel scoring is dead weight masking what would be visible if recruitment owned the choice end-to-end. |
| Replacement impingement shape | Activity choice IS a recruitment problem. `react / chat / vinyl / music / study / observe / silence` are 7 capabilities; recruitment should score them with the same cosine-base-Thompson-context formula. Stimmung term becomes `context: dict[str, Any]` passed to `select()`. Delete the parallel scorer. |
| Scope | L |

### A10. `director_loop` — video-streak "scope nudge" rule

| Field | Value |
|-------|-------|
| File:Line | `agents/studio_compositor/director_loop.py:2048-2068` |
| Constant | `video_streak >= 3` (hardcoded). |
| What it gates | If last 3 narratives mention "video"/"deposition"/"footage"/"scene", inject a "Shift ground" prompt rider. |
| Current default | 3-narrative streak, hardcoded keyword list. |
| Recruitment failure it masks | The hardcoded keyword list is a substitute for "the LLM is repeating itself thematically". The actual signal — that recruitment of speech capabilities is converging on a single attractor — could come from the recruitment cascade log. |
| Replacement impingement shape | `impingement(kind="thematic_recurrence", recent_themes=...)` derived from cascade log; let prompt enrichment recruit a "shift ground" hint capability. |
| Scope | S (the rule itself is small) |

### A11. `compositional_consumer._STRUCTURAL_EMPHASIS_PROPS` — hardcoded ward emphasis envelope

| Field | Value |
|-------|-------|
| File:Line | `agents/studio_compositor/compositional_consumer.py:935-940` |
| Constants | `alpha=1.0, glow_radius_px=14.0, scale_bump_pct=0.12, border_pulse_hz=2.2`, TTL 4 s. |
| What it gates | When `dispatch_structural_intent` runs, every ward in `ward_emphasis` receives this fixed envelope. |
| Current default | Same envelope for every ward, every tick, every stance. |
| Recruitment failure it masks | The director's `salience` field (per impingement, 0..1) is supposed to drive emphasis depth; salience is partially honored (`_apply_emphasis(... salience=1.0)` always passes 1.0) but the envelope itself is hardcoded. This means even if recruitment ran perfectly, every ward emphasis looks identical. |
| Live evidence | Direct read of `/dev/shm/hapax-compositor/ward-properties.json`: `thinking_indicator` has `border_pulse_hz=2.0, scale_bump_pct=0.05` (default for thinking) but not modulated by salience. |
| Replacement impingement shape | Per-ward emphasis envelope should be a property OF the recruited capability (not a per-tick override). Each `ward.highlight.<id>.<modifier>` already encodes its envelope (see `_WARD_HIGHLIGHT_MODIFIERS`); structural-intent should recruit specific modifiers, not paint a fixed envelope. |
| Scope | S |

### A12. `director_loop._silence_hold_fallback_intent` — hardcoded "thinking + stance" emphasis

| Field | Value |
|-------|-------|
| File:Line | `agents/studio_compositor/director_loop.py:67-103` |
| Constants | `ward_emphasis=["thinking_indicator", "stance_indicator"]`, `homage_rotation_mode="weighted_by_salience"`. |
| What it gates | On parser failure / degraded mode, emit a hardcoded "thinking_indicator + stance_indicator" emphasis. |
| Current default | Always those two wards. |
| Recruitment failure it masks | Silence hold is a Category C invariant in shape (every tick must have ≥ 1 impingement) but the *content* of the silence-hold is expert-system: same two wards every time. Operator can't distinguish "director chose to highlight thinking_indicator" from "parser failed, fallback ran." |
| Replacement impingement shape | Silence-hold should emit `impingement(kind="director_silent", reason="parser_failure"|"degraded"|...)` and let recruitment pick a stance-appropriate fallback ward. The pipeline knows the catalog; the dispatcher shouldn't hardcode the answer. |
| Scope | S |

### A13. `cpal.impingement_adapter._GAIN_DELTAS` + `should_surface` thresholds

| Field | Value |
|-------|-------|
| File:Line | `agents/hapax_daimonion/cpal/impingement_adapter.py:34-41, 100-105` |
| Constants | `_GAIN_DELTAS` dict (6 hardcoded source→delta mappings), `should_surface` threshold `strength >= 0.7` OR specific interrupt_token list OR specific gain_key list. |
| What it gates | Whether a daimonion impingement is loud enough to fire spontaneous speech. |
| Current default | Hardcoded thresholds + source→delta table. |
| Recruitment failure it masks | The affordance pipeline IS recruiting `speech_production` (declared at `init_pipeline.py:137`), but `run_loops_aux.py:445-449` explicitly skips dispatching it because "CPAL owns it". Then CPAL's `should_surface` makes the surface decision via expert-system thresholds. Two systems both think they own speech-trigger; one recruits and discards; the other gates with hardcoded numbers. The discarded recruitment scores are not visible. |
| Live evidence | Inspect any line in `/dev/shm/hapax-daimonion/recruitment-log.jsonl` — `speech_production` recruitments are filtered out at `run_loops_aux.py:448` so they don't even appear there. The pipeline's recruitment decision is entirely invisible. |
| Replacement impingement shape | Let speech_production recruitment fully control surface. Move `_GAIN_DELTAS` table semantics into capability-base-level priors (impingement source → context boost). Delete `should_surface`. CPAL becomes the *runner* (T0/T1/T3 mechanics + barge-in detection); the *decision* belongs to recruitment. |
| Scope | L (CPAL is load-bearing and this is the most invasive replacement) |

### A14. `homage.choreographer._read_rotation_mode` default → hardcoded "weighted_by_salience"

| Field | Value |
|-------|-------|
| File:Line | `agents/studio_compositor/homage/choreographer.py:563-613` |
| Constants | Default `"weighted_by_salience"`, narrative-tier max age 60 s, structural file unbounded. |
| What it gates | The choreographer's rotation strategy when no fresh intent file exists. |
| Current default | `weighted_by_salience` (changed from `"sequential"` per cascade-delta directive). |
| Recruitment failure it masks | When neither the narrative tier nor the structural director has emitted a fresh `homage_rotation_mode`, the choreographer still chooses one. The director's silence on rotation mode is conflated with "default to weighted-by-salience" — operator can't tell if the director declined to recruit OR forgot OR the file is stale. |
| Live evidence | `/dev/shm/hapax-compositor/narrative-structural-intent.json` was last updated >1 h before this audit; choreographer is reading stale `weighted_by_salience` for >120 ticks. The structural-intent JSONL never carries a fresh `homage_rotation_mode` for any tick (see §5.1 for the trace). |
| Replacement impingement shape | Choreographer reconciliation should be a recruited capability — `homage.rotation_strategy.<sequential|random|salience|paused>` capabilities, recruited per tick from a `compositional_director_tick` impingement. Falling back to "do whatever was decided last" is fine if the file is fresh; falling back to a hardcoded mode is the bug. |
| Scope | M |

---

## 4. Category C — legitimate invariants (cite in retirement plan)

These rules are CORRECT and the recruitment-driven replacements depend on
them. They must NOT be retired.

| File:Line | Rule | Why it stays |
|-----------|------|--------------|
| `affordance_pipeline.py:38, 311-360` | `_CONSENT_CACHE_TTL_S = 60.0`, `_consent_allows()` fail-closed | Axiom `interpersonal_transparency` invariant. Failure mode is correct (cached "no", denial of recruitment). |
| `director_intent.py:373` | `compositional_impingements: min_length=1` | Operator no-vacuum invariant. Forces every director tick to have at least one impingement to recruit against. |
| `director_loop.py:31-49` | `_silence_hold_impingement()` (the SHAPE, not the content — see A12 for content critique) | Same no-vacuum invariant; needed so the parser fallback path doesn't violate the schema. |
| `compositional_consumer.py:985-1008` | `_VALID_WARD_IDS` allowlist | Schema enforcement. A typo'd ward_id legitimately drops without writing a stray entry. |
| `face_obscure_integration.py` (not read in this audit; cited in CLAUDE.md) | Face-obscure fail-closed at livestream egress | Visual privacy axiom; supersedes recruitment. |

---

## 5. Recruitment-pipeline health findings

### 5.1 `structural_intent` is ceremonial in the live system

**Evidence:** Sampled the last 50 records in
`~/hapax-state/stream-experiment/director-intent.jsonl`. **Zero** records contain a
`structural_intent` key. Sample (last record at audit time, 2026-04-19 ~01:04 UTC):

```json
{
  "grounding_provenance": ["context.recent_reactions", "album.title", "album.current_track"],
  "activity": "music",
  "stance": "cautious",
  "narrative_text": "...",
  "compositional_impingements": [
    {"narrative": "Highlight the album cover...", "intent_family": "ward.highlight", ...},
    {"narrative": "Set the visual theme...", "intent_family": "preset.bias", ...},
    {"narrative": "Focus the camera on the vinyl spinning...", "intent_family": "camera.hero", ...}
  ],
  "condition_id": "none",
  "emitted_at": 1776578585.3767006
}
```

The schema (`shared/director_intent.py:381-390`) declares `structural_intent` as a
required field with `default_factory=NarrativeStructuralIntent`. `model_dump_for_jsonl`
(line 392) calls `model_dump(mode='json')`. By Pydantic V2 default semantics, the empty
`NarrativeStructuralIntent` should serialize as `{"homage_rotation_mode": null,
"ward_emphasis": [], "ward_dispatch": [], "ward_retire": [], "placement_bias": {}}` —
never as a missing key. The fact that the field is missing entirely from JSONL means
**every tick in the last 12 h was constructed via the legacy parser path** (i.e.
`_silence_hold_fallback_intent`) which does *not* set the field, OR the JSONL writer is
older than the schema change. Either way:

- The director's "structural intent" prompt section (lines 1992-2041 of
  `director_loop.py`) is asking the LLM to populate a field that
  `_parse_intent_from_llm` is not validating. The legacy-shape branch
  (`director_loop.py:181-205`) calls `_silence_hold_fallback_intent` which
  sets a hardcoded structural intent (line 91-96), but the new-shape branch
  on full LLM output (`DirectorIntent.model_validate(obj)`) never gets reached
  for any of the last 50 records.
- Consequently, `dispatch_structural_intent` is being called with the
  hardcoded silence-hold envelope on every parser-fallback tick and an
  empty container on every successful tick, never with the LLM's actual
  structural choice.

**This is a recruitment-pipeline gap.** The Family E retirement plan must
fix this before retiring rules A11/A12 (which would otherwise leave
structural-intent surface dispatch entirely unwired).

### 5.2 `family-restricted retrieval` is regularly returning empty

10 hits in 12 h for ward.highlight family producing 0 candidates from a
50-wide window. This is the recruitment pipeline LITERALLY telling us "the
director's impingement could not recruit anything." The fact that this
event is rare per family but still happens regularly suggests the
ward.highlight catalog is sparse compared to the wards the director names
(see `_VALID_WARD_IDS` — 20 wards but `ward.highlight.*` capabilities likely
exist for far fewer). Audit follow-up: enumerate registered
`ward.highlight.<id>.<modifier>` capabilities in Qdrant and cross-check
against `_VALID_WARD_IDS`.

### 5.3 Speech recruitment is short-circuited

Per A13, `run_loops_aux.py:445-449` filters `speech_production` out of the
dispatch loop with the comment "CPAL owns it." The recruitment pipeline
DOES score `speech_production` (it's registered in `init_pipeline.py:137`
and gets `population_critical` + `operator_distress` interrupt handlers).
Those scores are dropped on the floor. The CPAL adapter then makes the
surface decision on different criteria (`should_surface` in
`impingement_adapter.py:101-105`). The pipeline's view of "should
Hapax speak now" is invisible to the operator.

### 5.4 Compositor-origin impingements are correctly dispatched

The trace `director_loop._emit_compositional_impingements` →
`/dev/shm/hapax-dmn/impingements.jsonl` →
`run_loops_aux.impingement_consumer_loop` →
`AffordancePipeline.select(intent_family=...)` →
`compositional_consumer.dispatch(...)` works. The 45,178 dispatches in the
12 h window confirm the path is alive. The bug is in WHAT the dispatcher
does after recruitment hands it a winner (the variety/dwell/vision gates),
not in the recruitment path itself.

---

## 6. Category D — ambiguous (REQUIRES REVIEW)

These rules might be Category A but the recruitment-driven alternative
needs more design before retirement.

| File:Line | Rule | Why ambiguous |
|-----------|------|----------------|
| `follow_mode.py:61-64` | `_LOCATION_MATCH_BONUS=3.0`, `_OPERATOR_VISIBLE_BONUS=0.3`, `_REPETITION_PENALTY=3.0`, `_DEMO_DESK_OVERHEAD_BONUS=2.0` | Whole module is a parallel scoring system competing with cam.hero recruitment. Feature-flagged OFF by default but if turned on it overrides recruitment entirely. Decision: retire if the cam.hero affordance catalog has equivalent location-aware capabilities. |
| `twitch_director._SIGNIFICANT_MAGNITUDE=0.35`, `_PRESSURE_FORCE_THRESHOLD=6` | "If 6 perceptual signals are above magnitude 0.35, force a preset.bias.pressure-discharge" | Pressure-forcing is a meta-recruitment that the affordance pipeline could express as a `system_pressure_high` impingement. But "pressure" is a derived signal not currently emitted. Decision: ship the impingement first, then retire the rule. |
| `environmental_salience_emphasis.HYSTERESIS_SECONDS=30.0` | 30 s minimum between emphasis events | Pure hysteresis on a recommender. Whether this is recruitment-substituting depends on what `EmphasisRecommendation` consumers actually do. Needs trace. |
| `chat_reactor.COOLDOWN_SECONDS=30.0` (`RESEARCH_MODE` 90 s) | Per-keyword preset switch cooldown | Chat-reactor is a deterministic pre-recruitment shortcut (chat keyword → preset). Could be retired in favor of `impingement(kind="chat_keyword", text=...)` recruiting against a `fx.preset.<name>` capability — but this changes operator-facing behavior (viewers expect the keyword to "just work"). |
| `cpal.runner.TICK_INTERVAL_S=0.15` and `if self._tick_count % 10 == 0` | CPAL's 150 ms cognitive tick + 10-tick state publish | Tick interval is correct (Category B) but the "every 10 ticks publish state + check stimmung" has Category A flavor: stimmung-driven gain ceiling change is gated by an arbitrary 1.5 s polling cadence rather than by stimmung *change*. Decision: emit `impingement(kind="stimmung_change", new_stance=...)` and retire the polling. |
| `music_candidate_surfacer._DEFAULT_COOLDOWN_S=120.0` | 2-min cooldown on resurfacing the same music candidate | Could be Category B (anti-spam) or Category A (mask of "we'd recruit it again if salient"). Depends on whether re-recruitment is desired or always wrong. |

---

## 7. Family E retirement plan inputs

**Sequencing constraint:** the recruitment-pipeline gaps in §5 must close
BEFORE the rules can be retired, otherwise the surface goes silent. Order:

### Phase E.0 (prerequisites — must ship first)

1. **Fix the `structural_intent` JSONL omission** (§5.1). Either:
   - Verify `_parse_intent_from_llm` validates the new shape correctly when
     LLM emits structural_intent (add log + counter for which path was
     taken); OR
   - Migrate the parser fallback paths to populate structural_intent from
     a shared template the schema can validate.
2. **Audit the Qdrant `affordances` collection** (§5.2). Enumerate registered
   `ward.highlight.<id>.<modifier>`, `cam.hero.<role>.<context>`, and
   `fx.family.<family>` capabilities. Cross-check coverage against
   `_VALID_WARD_IDS`, the camera role map, and `FAMILY_PRESETS`. Add
   missing capabilities (do this BEFORE relaxing the variety-gate, so
   recruitment has a wider pool to draw from).
3. **Add cascade observability for dropped recruitments** (§5.3, §5.1). Make
   it possible to count, per family per minute: "recruitment scored a
   winner but the dispatcher rejected it" — broken out by reason
   (variety, dwell, vision, family-empty, structural-stripped).

### Phase E.1 (retire dispatcher gates; lowest blast radius)

- Retire **A1** (variety-gate). Live impact: 6,358 recruitments/12h
  re-enabled.
- Retire **A2** (dwell-gate). Live impact: 373 recruitments/12h re-enabled.
- Retire **A11** (hardcoded structural emphasis envelope). Replace with
  per-capability envelopes already in `_WARD_HIGHLIGHT_MODIFIERS`.

### Phase E.2 (retire director-side enforcers)

- Retire **A4** (activity rotation enforcer). Verify exploration tracker
  surfaces the case in tests.
- Retire **A6** (narrative-too-similar + micromove cycle). Add
  `recently_said` impingement.
- Retire **A10** (video-streak scope nudge). Replace with
  `thematic_recurrence` impingement.

### Phase E.3 (retire scoring bypasses)

- Retire **A7** (random_mode). Recruitment-driven preset cycling.
- Retire **A8 partial** (twitch_director's idle-variation, pressure-force,
  stance-cadence; KEEP the hand-zone-change rule).
- Retire **A9** (activity_scoring stimmung override). Recruitment-driven
  activity choice.

### Phase E.4 (largest blast radius — defer)

- **A3** (vision-gate). Defer until per-camera scene-classifier
  impingement is wired.
- **A5** (PERCEPTION_INTERVAL). Defer until capability-cost gating is
  wired into the pipeline.
- **A12** (silence-hold ward content). Defer until structural_intent
  pipeline is fully alive.
- **A13** (CPAL `should_surface`). Defer; CPAL is load-bearing.
- **A14** (choreographer rotation default). Defer until structural intent
  recruitment exists.

---

## 8. Open questions for the planning subagent

The planning subagent (writing
`docs/superpowers/plans/2026-04-19-homage-completion-plan.md`) needs the
following inputs FROM this audit:

1. **The structural_intent path is broken** (§5.1). Any plan that relies
   on `dispatch_structural_intent` working correctly must include a
   verification step that the LLM's structural choice actually round-trips
   to ward-properties.json + homage-pending-transitions.json. Currently
   it does not.
2. **The variety-gate is destroying ~14 % of all compositional
   recruitments** (§3 A1). Any plan that benchmarks recruitment quality
   should disable the variety-gate first or numbers will be misleading.
3. **`narrative-structural-intent.json` writes are stale** (§5.1
   evidence: file last updated >1 h before this audit). Any plan that
   relies on narrative-tier rotation-mode override is currently using the
   structural director's slow path even when it claims to use the fast
   path.
4. **The 7-step micromove cycle is firing dozens of times per 12 h**
   (§3 A6). Plans that assume director tick output is recruitment-driven
   are wrong for those ticks. Either the dedup threshold is too tight
   (Jaccard 0.35 is aggressive) or the micromove cycle should not exist.
5. **`speech_production` recruitment is filtered out before it reaches the
   dispatch loop** (§5.3). Any plan that wants to make speech timing
   recruitment-driven needs to re-enable the dispatch path AND retire
   `should_surface` simultaneously.

---

## 9. Per-rule live-evidence appendix

### 9.1 Variety-gate evidence

```
$ journalctl --user -u hapax-daimonion --since "12 hours ago" | grep -c "camera.hero variety-gate"
6358
$ journalctl --user -u hapax-daimonion --since "12 hours ago" | grep -c "Compositional dispatch:"
45178
```

Sample sequence (PID 3579006, 2026-04-18 18:04:40 UTC):
```
... Compositional dispatch: attention.winner.code-narration → attention.winner (score=0.45)
... camera.hero variety-gate: c920-desk in recent ['c920-desk', 'brio-operator'], skipping
... Compositional dispatch: cam.hero.desk-c920.writing-reading → unknown (score=0.37)
... Compositional dispatch: attention.winner.goal-advance → attention.winner (score=0.48)
... camera.hero variety-gate: brio-operator in recent ['c920-desk', 'brio-operator'], skipping
... Compositional dispatch: cam.hero.operator-brio.conversing → unknown (score=0.36)
... camera.hero variety-gate: c920-desk in recent ['c920-desk', 'brio-operator'], skipping
... Compositional dispatch: cam.hero.desk-c920.writing-reading → unknown (score=0.35)
```

Two distinct cam.hero capabilities (`desk-c920.writing-reading` and
`operator-brio.conversing`) recruited and rejected within 4 ms. The pipeline
is doing its job; the variety-gate is throwing the answers away.

### 9.2 Dwell-gate evidence

```
$ journalctl --user -u hapax-daimonion --since "12 hours ago" | grep -c "camera.hero dwell-gate"
373
```

### 9.3 Activity rotation enforcer evidence

11 events in 12 h. Sample:
```
Apr 19 00:37:43 ... activity rotation FORCED: music → music (after 3 consecutive)
Apr 19 00:40:29 ... activity rotation FORCED: music → study (after 3 consecutive)
Apr 19 00:49:01 ... activity rotation FORCED: music → chat (after 3 consecutive)
Apr 19 00:57:07 ... activity rotation FORCED: music → observe (after 3 consecutive)
```

Within 20 minutes the rule rotated `music` to four different labels —
including `music → music`, which is the rule firing on its own previous
output. The operator is at the deck spinning vinyl; "music" is the right
answer; the rule is fighting reality.

### 9.4 Narrative-too-similar evidence

40+ events grepped over 12 h. Sample (compressed):
```
Apr 18 19:03:58 ... director narrative too similar to recent — emitting micromove fallback
Apr 18 19:04:55 ... director narrative too similar to recent — emitting micromove fallback
Apr 18 19:12:48 ... director narrative too similar to recent — emitting micromove fallback
Apr 18 19:21:44 ... (8 more in next 40 min)
```

Each substitutes one of 7 hardcoded micromoves for what would be
recruitment-driven output.

### 9.5 family-restricted retrieval empty evidence

10 events in 12 h. Sample:
```
Apr 18 14:15:12 ... family-restricted retrieval (ward.highlight, prefix=ward.highlight.)
  returned no candidates from 50-wide window — director impingement will not
  recruit anything this tick
```

The pipeline is announcing a recruitment failure. There is no fallback;
the director's intent is silently dropped for that tick. This is the
ONLY existing rule that correctly observes a recruitment failure and
declines to mask it — but it logs as INFO, so dashboard visibility is
near-zero.

### 9.6 Structural intent omission evidence

```
$ tail -50 ~/hapax-state/stream-experiment/director-intent.jsonl |
    python3 -c "import json,sys; n=have=0
for line in sys.stdin:
    if not line.strip(): continue
    n+=1
    if 'structural_intent' in json.loads(line): have+=1
print(f'last 50 records: total={n} with_structural_intent={have}')"
last 50 records: total=50 with_structural_intent=0
```

Field is declared mandatory in `DirectorIntent` and serialized via
`model_dump(mode='json')`; either the parser-fallback path skips it or
the JSONL writer predates the schema change. Either way, every
`dispatch_structural_intent` call in the last 50 ticks operated on an
empty container.

---

## 10. Recommendations

### 10.1 Three-rule first-pass retirement (maximum unmasking, minimum risk)

1. **Retire A1 (variety-gate).** Single-line delete in
   `compositional_consumer.py`. Recovers 6,358 recruitment outcomes /
   12 h. If recruitment converges on one camera, that's diagnostic
   information about the pipeline + perceptual field, not a defect to
   patch.
2. **Retire A11 (hardcoded structural emphasis envelope).** Replace fixed
   `_STRUCTURAL_EMPHASIS_PROPS` with a lookup into the recruited
   `ward.highlight.<modifier>` modifier table. Already-existing data;
   small edit.
3. **Retire A6 (narrative-too-similar + micromove cycle).** Largest
   single source of pre-baked surface activity. Replace with a `recently_said`
   impingement; let recruitment handle anti-repetition naturally.

### 10.2 What NOT to retire in the first pass

- **A12 (silence-hold ward content)** — needs the structural-intent path
  fixed first or the silence-hold becomes blank.
- **A13 (CPAL should_surface)** — CPAL is the conversational loop's
  beating heart; surgical replacement with recruitment-driven surface
  needs its own design pass.
- **Anything in §6 Category D** — those need the recruitment-side
  primitives (new impingement shapes, new capability families) to ship
  first.

### 10.3 Permanent observability changes (orthogonal to retirement)

- Promote `family-restricted retrieval ... returned no candidates` from
  INFO to WARNING. Add a counter `hapax_recruitment_empty_total{family,
  prefix}`.
- Add a counter `hapax_dispatcher_rejection_total{family, reason}` for
  every gate (variety, dwell, vision, etc.). Even if rules stay, the
  rejection rate becomes visible.
- Add a counter `hapax_structural_intent_path_total{path}` where path ∈
  {parser_fallback, llm_emitted, micromove_cycle, silence_hold,
  degraded_hold} so we can see what fraction of director ticks come from
  recruitment vs. fallback.

---

## 11. Closing note

The recruitment pipeline is the most-articulated, best-instrumented
subsystem in the council codebase. It is also the most-bypassed: every
rule in §3 was added because someone observed a surface symptom (operator
sees same camera too long, narrative repeats, structural intent silent)
and patched the symptom rather than fixing the recruitment path that
allowed it.

The operator's directive — "NO expert-system rules blinding us to
directorial impingement → recruitment failures" — is not a request to
delete code. It is a request to make the recruitment path's failure modes
*visible* by removing the rules that hide them. After the unmasking, real
gaps in the catalog, the impingement vocabulary, and the dispatcher will
become operator-actionable.

This audit is the inventory. The Family E plan is the surgery.
