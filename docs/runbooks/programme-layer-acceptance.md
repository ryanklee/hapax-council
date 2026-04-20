# Programme Layer Acceptance — operator walkthrough

Phase 12 (terminal) of the programme-layer plan
(`docs/superpowers/plans/2026-04-20-programme-layer-plan.md` §lines 1146-1212).
Walk through this checklist with a live 30-min stream + the synthetic
integration test before declaring the programme layer live.

## Auto-checkable acceptance (run before the live walk)

```sh
uv run pytest tests/integration/test_programme_layer_e2e.py -q
```

10 tests must be green:

- [ ] Planner emits a 3-programme plan (listening → work-block → wind-down)
- [ ] Plan persists to `ProgrammePlanStore`
- [ ] `ProgrammeManager` walks 3 transitions deterministically with an
      injected clock
- [ ] Each boundary emits 4 ritual impingements (`exit_ritual`,
      `boundary.freeze`, `palette.shift`, `entry_ritual`)
- [ ] `hapax_programme_start_total` fires 3+ across the lifecycle;
      `hapax_programme_end_total` fires 2+
- [ ] **Invariant**: `hapax_programme_candidate_set_reduction_total`
      stays at zero across all 3 programmes' bias applications
- [ ] **Invariant**: `hapax_programme_soft_prior_overridden_total` > 0
      for each programme that has negative bias entries
- [ ] Reverie `compute_substrate_saturation` lands at each programme's
      `reverie_saturation_target` value
- [ ] `StructuralDirector` stamps `programme_id` on every emitted
      `StructuralIntent` while a programme is active
- [ ] Abort + 5s veto + commit FSM works on a real Programme

## Operator-walked acceptance (live stream, 30 min)

Run the live system against the acceptance fixture (or a normal
operator session) and verify each item below. Operator may flag 1-2
cosmetic items without blocking; the invariant items (5, 6) MUST pass.

1. **Plan visible**: `~/hapax-state/programmes/<show_id>/plan.json`
   shows the 2-5 programme sequence Hapax authored at show-start.
2. **Programme 1 reads as its role**: A `listening` programme renders
   as a quiet, damped substrate. A `work-block` programme renders as
   moderately active. A `wind-down` programme renders dim and minimal.
3. **Boundary transitions visible**: At each boundary, observe the
   exit ritual → boundary freeze → palette shift → entry ritual cycle.
   Each step is recruited via the affordance pipeline (no scripted
   playback).
4. **Per-programme soft-prior override counter is > 0**:
   ```sh
   curl -s http://localhost:9482/metrics | grep hapax_programme_soft_prior_overridden_total
   ```
   For each `programme_id` label, the counter must be > 0. A counter
   stuck at zero indicates the soft prior is acting as a hard gate
   (`project_programmes_enable_grounding` violation).
5. **Candidate-set reduction counter is 0** (architectural invariant):
   ```sh
   curl -s http://localhost:9482/metrics | grep hapax_programme_candidate_set_reduction_total
   ```
   Every label must be exactly 0. A non-zero value indicates
   `_apply_programme_bias` is dropping candidates — a bug.
6. **JSONL outcome log full lifecycle per programme**: each programme
   has `start`, `tactical_summary` (every 60s), and `end` events in
   `~/hapax-state/programmes/<show_id>/<programme_id>.jsonl`.
7. **No scripted text leak**: Spot-check ward emissions during the
   stream. No line in any outcome log should trace back to a template
   string in a programme catalog (everything goes through the
   affordance pipeline as recruitment, not playback).
8. **Programme id stamped on director intent**: every record in
   `~/hapax-state/stream-experiment/structural-intent.jsonl` during
   the acceptance window has a `programme_id` field that matches the
   active programme at that timestamp.

## Operator sign-off

Operator records the result in the daily note + appends a line below.

```
- [ ] 2026-MM-DD: programme layer LIVE (operator: hapax)
```

## Failure paths

- **Synthetic integration tests red**: do NOT do the live walk.
  Investigate the test failure first (commit `84fb321b1`+ are the
  shipped Phase 1-11 surface; the e2e is a regression check on top).
- **Override counter stuck at zero**: the soft prior is hardening into
  a gate. Check `_apply_programme_bias` in `shared/affordance_pipeline.py`
  and verify the bias multiplier is being applied (the validator
  rejects zero, so the bias must have been silently dropped).
- **Candidate-set reduction counter > 0**: `_apply_programme_bias`
  shrunk the set. This is an INVARIANT VIOLATION — the helper must
  preserve list length exactly. Investigate before continuing the
  live walk.
- **Outcome log gaps**: `ProgrammeManager` lifecycle calls aren't
  reaching `programme_observability.emit_*`. Check that the manager
  was constructed with the correct paths.
