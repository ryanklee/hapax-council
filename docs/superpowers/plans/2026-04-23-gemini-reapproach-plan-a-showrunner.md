# Plan A — Content Programming Layer ("Showrunner") Re-Approach

**Design:** `docs/superpowers/specs/2026-04-23-gemini-reapproach-epic-design.md` §Epic A
**Extends:** `docs/superpowers/plans/2026-04-20-programme-layer-plan.md`
**Task:** #164 (pending) — Content programming layer ABOVE director_loop

5 phases. Each leaves the live system in a coherent state. Gemini's reverted `content_programmer.py` stays at `/tmp/gemini-salvage/content_programmer.py` for reference.

## Phase A1 — Segment + Beat primitive + persistence

**Branch:** `feat/showrunner-a1-segment-primitive`
**No runtime impact.**

- [ ] `shared/segment.py` — `Segment` + `Beat` pydantic models. `Segment`: `segment_id`, `parent_programme_id`, `format`, `thesis`, `media_vectors[]`, `reusable: bool`, `segment_author: Literal["hapax"]`, `beats: list[Beat]`, `capability_bias_positive: dict[str, float]`, `capability_bias_negative: dict[str, float]`. `Beat`: `beat_id`, `narrative_goal`, `verbal_script: str` (guidance, not mandatory), `screen_directions_prior: dict[str, float]` (capability→bias multiplier, NEVER a dispatch), `planned_duration_s`, `min_duration_s`, `max_duration_s`, `cadence_archetype: Literal["clinical_pause","freeze_frame_reaction","percussive_glitch"] | None`.
- [ ] Validators: `segment_author="hapax"` literal; `capability_bias_positive` ≥1.0; `capability_bias_negative` in (0.0, 1.0]; `beats` non-empty; `planned_duration_s ∈ [min, max]`.
- [ ] `shared/segment_store.py` — `SegmentStore`, JSONL at `~/hapax-state/segments.jsonl`, atomic tmp+rename, one-ACTIVE invariant per parent programme, `activate`/`deactivate` with status + timestamp, 10MiB size warning.
- [ ] Tests: pydantic round-trip, validator guard rails, store concurrency, `segment_author` pin regression.
- [ ] Local verify: `uv run pytest tests/shared/test_segment.py tests/shared/test_segment_store.py -q`
- [ ] Commit + push + PR + admin-merge

## Phase A2 — SegmentPlanner + prompt (companion to ProgrammePlanner)

**Branch:** `feat/showrunner-a2-segment-planner`
**No runtime integration yet — planner callable but not invoked.**

- [ ] `agents/programme_manager/segment_planner.py` — `SegmentPlanner`. Inputs: active `Programme`, perception snapshot, vault read-state, operator profile, recent segment history (deque(maxlen=10) for anti-repetition).
- [ ] `agents/programme_manager/prompts/segment_plan.md` — external prompt. Lift "relatable YouTube format BUT TWISTED AROUND" constraint verbatim from Gemini's salvaged prompt. Include cadence-archetype hint as optional field. Enforce soft-prior dict shape.
- [ ] LLM routing: `balanced` via LiteLLM (claude-sonnet). Env override `HAPAX_SEGMENT_PLANNER_MODEL`. Timeout 60s, 1 corrective retry.
- [ ] `response_format={"type": "json_object"}` + markdown-fence fallback parser (preserve Gemini's robustness).
- [ ] Tests: planner emits valid Segment list, empty-on-LLM-failure, soft-prior validator catches hard-dispatch attempts, history deque suppresses format repeats.
- [ ] Commit + PR + admin-merge

## Phase A3 — Segment activation + beat transitions + director-prompt context

**Branch:** `feat/showrunner-a3-segment-activation`
**First runtime integration.**

- [ ] Extend `ProgrammeManager` with `_active_segment`, `_active_beat` state. Transitions tick-driven; Beat advances at `planned_duration_s` bounded by `[min, max]`.
- [ ] Write `/dev/shm/hapax-daimonion/active-beat.json` (read-only signal, not a recruitment-log write). Schema: `{segment_id, beat_id, format, thesis, narrative_goal, verbal_script, screen_directions_prior}`.
- [ ] Extend `director_loop._build_unified_prompt` with a `## Current segment context` section rendering `format | thesis | beat.narrative_goal | beat.verbal_script` as **soft guidance** preceded by the sentence "This is a prior for grounding, not a mandatory script — recruit capabilities freely."
- [ ] Extend AffordancePipeline scorer to consume `screen_directions_prior` as capability-bias multiplier (composes with Programme's `capability_bias_positive`). Fail-closed: missing file → priors default 1.0 (neutral).
- [ ] Tests: `test_director_can_override_segment_prior` (grounding-first invariant — prove director recruits a capability with prior 0.5 when perceptual salience demands it); `test_segment_writes_active_beat_json` (SHM contract); `test_no_mandatory_script_injection` regression (existing, must still pass).
- [ ] Commit + PR + admin-merge

## Phase A4 — Cadence archetype lookup + ffmpeg-safe visual-pause

**Branch:** `feat/showrunner-a4-cadence-archetypes`

- [ ] `shared/cadence_archetypes.py` — deterministic map:
  ```python
  ARCHETYPES = {
      "clinical_pause": CadenceHints(preset_family_hint="ambient_neutral", homage_rotation_mode_hint="held", beat_length_range_s=(45, 60)),
      "freeze_frame_reaction": CadenceHints(preset_family_hint="glitch_soft", homage_rotation_mode_hint="stable", beat_length_range_s=(20, 40), visual_pause_layout="operator-brio.conversing"),
      "percussive_glitch": CadenceHints(preset_family_hint="glitch_dense", homage_rotation_mode_hint="burst", beat_length_range_s=(10, 15)),
  }
  ```
- [ ] Beat-tick logic reads archetype, emits `preset_family_hint` + `homage_rotation_mode_hint` as soft priors into AffordancePipeline.
- [ ] **Freeze-Frame Reaction visual-pause pattern:** emit a `layout.switch` prior toward `operator-brio.conversing` when active. NEVER `SIGSTOP` ffmpeg (preserves `feedback_never_drop_speech`). Test: `test_freeze_frame_does_not_sigstop_ffmpeg` — asserts `subprocess.run(["kill", "-STOP", ...])` is not invoked from the SegmentManager path.
- [ ] Commit + PR + admin-merge

## Phase A5 — Observability + operator veto + SegmentOutcomeLog

**Branch:** `feat/showrunner-a5-observability`

- [ ] Grafana dashboard: active segment, active beat, beat elapsed, cadence archetype distribution, segment-repetition rate, operator-veto counts.
- [ ] Operator-triggered transitions: impingement family `segment.transition.<id>` + `beat.transition.<id>` mirroring existing `programme.transition.*`.
- [ ] `segment.abort.veto` (5s window via AbortEvaluator pattern).
- [ ] `SegmentOutcomeLog` JSONL at `~/hapax-state/segments/<show>/<programme-id>/<segment-id>.jsonl`.
- [ ] Prometheus metrics: `segment_active{segment_id,format,cadence}`, `segment_beat_transitions_total`, `segment_aborts_total`.
- [ ] Commit + PR + admin-merge + epic closeout runbook

## Phase A6 (optional) — Opus 3.6 / `showrunner` alias routing

**Branch:** `feat/showrunner-a6-opus-alias`
**Operator-ratified model upgrade.**

- [ ] Add `"showrunner": "claude-opus-3.6"` to `shared/config.py::MODELS`.
- [ ] SegmentPlanner reads `HAPAX_SEGMENT_PLANNER_MODEL` env; default `"showrunner"`.
- [ ] Feature-flag rollout: A/B with `balanced` on latency + output-quality metrics for 48h before flipping default.
- [ ] Commit + PR + admin-merge post-operator-ratification.

## Rollback

Each phase is a separate merge-commit. `git revert <sha>` rolls back cleanly. Phase A3 is the first phase with runtime integration — if it destabilizes the stream, revert A3 and A1/A2 remain as library code with no consumer.
