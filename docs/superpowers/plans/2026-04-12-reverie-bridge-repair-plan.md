---
title: Reverie bridge repair — implementation plan
date: 2026-04-12
status: in_progress
author: delta
spec: docs/superpowers/specs/2026-04-12-reverie-bridge-repair-design.md
---

# Reverie bridge repair — implementation plan

Execution plan for
[`2026-04-12-reverie-bridge-repair-design.md`](../specs/2026-04-12-reverie-bridge-repair-design.md).
Three PRs, sequenced so each is shippable on its own and the critical
visual-chain fix is not blocked on any of the others.

## PR-1 — Core bridge fix (URGENT, this PR)

**Branch:** `fix/reverie-bridge-v2`
**Owner:** delta
**Scope:** core Finding A + Finding B unit hygiene + design/plan docs +
memory + CLAUDE.md. Everything deterministic and mergeable in one pass.

### Files

| Path | Change |
|---|---|
| `agents/reverie/_uniforms.py` | Add `_iter_passes()` helper; rewrite `_load_plan_defaults()` to walk v1 and v2; add `content.intensity` passthrough |
| `tests/reverie/test_uniforms_plan_schema.py` | New file — 5 cases (v1, v2 single, v2 multi, empty, live-shape regression) |
| `systemd/units/hapax-imagination-loop.service` | Move `StartLimitIntervalSec` + `StartLimitBurst` + `OnFailure` to `[Unit]`; add `Requires=hapax-dmn.service` |
| `hapax-council/CLAUDE.md` § Tauri-Only Runtime | Update "hosts the actuation loop as a concurrent async task" → "runs as an independent systemd daemon …" |
| `docs/superpowers/specs/2026-04-12-reverie-bridge-repair-design.md` | This design |
| `docs/superpowers/plans/2026-04-12-reverie-bridge-repair-plan.md` | This plan |

### Steps

1. ✅ Research complete — root causes localized, claims verified against
   source.
2. ✅ Worktree created at `~/projects/hapax-council--reverie-bridge`,
   branch `fix/reverie-bridge-v2` off `origin/main`.
3. Write design + plan (this document + its sibling spec).
4. Patch `agents/reverie/_uniforms.py`:
   a. Add `_iter_passes(plan)` helper at module scope.
   b. Rewrite `_load_plan_defaults()` body to use `_iter_passes()`.
   c. Add `uniforms["content.intensity"] = salience × silence` below the
      existing `content.salience` line.
5. Write `tests/reverie/test_uniforms_plan_schema.py` covering:
   - `_iter_passes` v1 flat
   - `_iter_passes` v2 single-target
   - `_iter_passes` v2 multi-target key merge
   - `_load_plan_defaults` on a tmpfile v2 plan
   - `_load_plan_defaults` empty / malformed (no raise)
6. Patch `systemd/units/hapax-imagination-loop.service` per § 2.3.
7. Update `hapax-council/CLAUDE.md` § Visual surface one-liner per § 2.5.
8. `uv run pytest tests/reverie/ -q`
9. `uv run ruff check agents/reverie/_uniforms.py tests/reverie/test_uniforms_plan_schema.py`
10. `uv run ruff format agents/reverie/_uniforms.py tests/reverie/test_uniforms_plan_schema.py`
11. `uv run pyright agents/reverie/_uniforms.py` (if clean-baseline)
12. Conventional commit:
    `fix(reverie): repair visual-chain → GPU bridge after plan schema v2 drift`
13. Push `fix/reverie-bridge-v2` → `origin`.
14. `gh pr create` with body linking design + plan.
15. Monitor CI (axiom gate, triage, adversarial review) through to green.
16. On merge, update local memory files
    (`project_reverie.md`, `project_reverie_autonomy.md`) to reflect fixed
    state + architectural ratification.

### Post-merge verification (run on host, not in CI)

Commands listed in design § 5. Operator can copy-paste.

### Rollback

`git revert <merge SHA>` is safe. The change is purely additive on the read
path. No data migration, no state change.

## PR-2 — Reverie monitor extension (can ship after PR-1)

**Branch:** `feat/reverie-monitor-imagination-loop`
**Owner:** delta (or beta if picked up from queue)
**Depends on:** nothing; orthogonal to PR-1 but only becomes valuable
once PR-1 is merged so that a restart actually produces correct output.

### Files

| Path | Change |
|---|---|
| `agents/reverie_monitor.py` (or wherever the monitor lives) | Extend unit list from `[hapax-reverie]` → `[hapax-reverie, hapax-imagination-loop]`; restart if inactive; chronicle event |
| `tests/reverie/test_reverie_monitor.py` | Cover both units; mock `subprocess.run`; assert restart attempt fires |

### Steps

1. Locate the current monitor script — likely `agents/reverie_monitor.py`
   or a shell script under `scripts/monitoring/`. First grep target.
2. Parameterise the unit list.
3. Add structured chronicle emission on restart (non-fatal if chronicle is
   unreachable).
4. Test with a killed loop; monitor should restart within the timer
   cadence.
5. Ship as a tiny, one-file PR.

## PR-3 — Observability follow-ups (nice to have)

**Branch:** `feat/reverie-uniform-observability`
**Owner:** unassigned; picked up at next R&D slot
**Depends on:** PR-1 merged

### Files

| Path | Change |
|---|---|
| `agents/reverie/debug_uniforms.py` | New CLI — `python -m agents.reverie.debug_uniforms` prints current keys, expected keys, diff |
| `logos/api/routes/predictions.py` | Add `reverie_uniforms_key_count` Prometheus metric |
| `grafana/dashboards/reverie-predictions.json` | Add panel "Uniforms keys written" with alert `< 20` |

### Steps

1. Write the debug CLI using the same `_iter_passes` + `_load_plan_defaults`
   already fixed in PR-1. Import, don't duplicate.
2. Add the metric endpoint; scrape config already covers
   `localhost:8051/metrics`.
3. Import the dashboard panel; set alert threshold to `< plan_default_count - 5`
   rather than a hardcoded value, so it doesn't need updating with new
   dimensions.

## Coordination

- **Alpha (Stream A, compositor)** — no overlap. Alpha's `hapax-logos/crates/`
  work does not touch `agents/reverie/` or the imagination-loop unit.
  Status file note so alpha does not also try to fix a visual symptom.
- **Beta (Stream B, reverie + voice)** — overlap risk. Beta is currently
  executing `B4 — wire TransientTexturePool into DynamicPipeline`. B4 is
  Rust-side; it does not touch `agents/reverie/_uniforms.py`. No merge
  conflict expected. Beta should *pick up PR-2 and PR-3* from its queue once
  PR-1 ships.
- **Convergence** — PR-1 fixes a symptom beta was probably going to blame on
  their own wiring during B4 ("dimensions not responding"). Log as
  COMPLEMENTARY.

## Open questions

- Does the Python wgsl compiler always emit v2, or is there a codepath
  that still writes v1? Impact: if v1 is still possible, the fallback in
  `_iter_passes` is real coverage rather than belt-and-braces. Low priority
  to answer — the fix is robust either way.
- Is the `hapax-reverie-monitor` script already checking
  `hapax-imagination-loop`? If so, PR-2 collapses to a one-line change.
  If not, PR-2 is ~20 lines. Either way, small.

## Definition of done

PR-1:

- [ ] `_uniforms.py` patch lands
- [ ] New test file passes
- [ ] ruff + pyright green
- [ ] Unit file patch lands
- [ ] CLAUDE.md updated
- [ ] PR merged
- [ ] Post-merge verification commands run on host and output captured
- [ ] Memory files updated (local; no commit needed)
- [ ] Relay status files (`alpha.yaml`, `beta.yaml`) updated with
      completion note
