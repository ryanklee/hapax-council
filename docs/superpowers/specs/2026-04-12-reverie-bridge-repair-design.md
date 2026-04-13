---
title: Reverie bridge repair — visual chain → GPU uniforms
date: 2026-04-12
status: approved
author: delta
related_prs: []
supersedes: []
---

# Reverie bridge repair — visual chain → GPU uniforms

## Summary

Reverie was rendering dimensionally flat: the 9 expressive visual dimensions
(`intensity, tension, depth, coherence, spectral_color, temporal_distortion,
degradation, pitch_displacement, diffusion`) were being computed by
`agents/visual_chain.py` and serialised to `visual-chain-state.json`, but none
of them were reaching the GPU. The shader graph was running on vocabulary
defaults plus stimmung plus the feedback trace — and nothing else.

Root cause is a single 4-line drift: `agents/reverie/_uniforms.py::_load_plan_defaults`
walks the v1 plan schema (`plan["passes"]`) while the live plan is v2
(`plan["targets"]["main"]["passes"]`). The defaults dict was silently empty,
the writer's merge loop had nothing to iterate over, and the 9-dim deltas never
appeared in `uniforms.json`. Reverie has been in this state since the Rust
DynamicPipeline adopted the v2 schema.

A second, independent failure was surfaced in the same investigation:
`hapax-imagination-loop.service` was `inactive (dead)` with no start attempts
in the journal — meaning the Bachelard Amendment 4 reverberation consumer
(`agents.imagination_daemon` → `ImaginationLoop._check_reverberation`) was
offline. The producer half (DMN evaluative tick writing
`/dev/shm/hapax-vision/observation.txt`) is alive, so the loop was
open-circuit. Manual `systemctl --user start` brings it up cleanly, which
proves the unit is well-formed; what the unit *lacks* is any durable guarantee
that it stays up across `daemon-reload` / boot-order races.

Several audit findings from the investigation prompt have been resolved
without code changes and are documented here so they do not get re-opened:

1. **Content layer Bachelard functions are not dead code.** The Rust audit
   agent reported that `materialization()`, `immensity_entry()`, `material_uv()`,
   `corner_incubation()`, `material_color()`, and `dwelling_trace_boost()` were
   defined but never called. Reading `agents/shaders/nodes/content_layer.wgsl`
   directly confirms they are all invoked inside `sample_and_blend_slot()`,
   which is called per-slot with `slot_index ∈ {0,1,2,3}`. Amendments 1, 3, 5
   are upheld.

2. **Colorgrade param order is not inverted.** The Rust audit agent reported
   that the vocabulary dict order (`brightness, saturation, ...`) did not
   match the WGSL struct order (`u_saturation, u_brightness, ...`). The
   compiled `plan.json` `color` node shows
   `param_order: ['saturation', 'brightness', 'contrast', 'sepia',
   'hue_rotate']` — the `wgsl_compiler` reorders dict keys to match the WGSL
   struct. The Rust side reads by this explicit `param_order` positionally
   (`dynamic_pipeline.rs:803-821`), so there is no inversion.

3. **DMN-hosted actuation loop is not a regression, it is a refactor.** The
   original commitment ("DMN daemon hosts the reverie actuation loop as a
   concurrent async task") was broken by commit `17ccd547f` on 2026-03-26,
   which split reverie into its own systemd service. The structural-peer
   *spirit* (same perception → governance → actuation cascade, same 9-dim
   chain) is preserved; only the *process boundary* changed. This design
   formally ratifies the split — see §4 — so the memory and the CLAUDE.md
   reference are updated instead of the code being reverted.

Out of scope: the 5-channel adaptive mixer direction (dormant forward goal),
the Voronoi shader orphan, and the `dynamic_pipeline.rs:556-564` silent
shader-load-failure smell. Those are tracked as follow-ups, not blockers.

## 1 · Problem statement

### 1.1 Finding A — Empty plan-defaults cache

`_uniforms.write_uniforms` constructs `uniforms.json` by walking every
`{node_id}.{param_name}` key in the plan and emitting
`base + delta * reduction * silence`. The per-key base comes from
`_load_plan_defaults`, which parses the latest `plan.json` from shared memory.

The parser:

```python
# agents/reverie/_uniforms.py:32-44 (pre-fix)
defaults: dict[str, float] = {}
try:
    plan = json.loads(PLAN_FILE.read_text())
    for p in plan.get("passes", []):                   # ← v1 schema only
        node_id = p.get("node_id", "")
        for k, v in p.get("uniforms", {}).items():
            if isinstance(v, (int, float)):
                defaults[f"{node_id}.{k}"] = float(v)
except (OSError, json.JSONDecodeError):
    log.warning("Failed to load plan defaults", exc_info=True)
```

The live plan.json is v2:

```jsonc
{
  "version": 2,
  "targets": {
    "main": {
      "passes": [
        { "node_id": "noise", "uniforms": {...}, "param_order": [...] },
        ...
      ]
    }
  }
}
```

`plan.get("passes", [])` returns `[]`. `defaults == {}`. The writer's merge
loop at `_uniforms.py:120-125` has nothing to iterate. The only keys that
make it into `uniforms.json` are the five lines written unconditionally:
`fb.trace_*` (4) and `signal.stance` / `signal.color_warmth` (2) when
stimmung is present.

Observational evidence captured at 2026-04-12 16:47:

```json
{"fb.trace_center_x": 0.5, "fb.trace_center_y": 0.5,
 "fb.trace_radius": 0.0, "fb.trace_strength": 0.0,
 "signal.stance": 0.25, "signal.color_warmth": 0.067}
```

vs the matching `visual-chain-state.json` (same tick, live deltas present):

```json
{"levels": {"visual_chain.intensity": 0.404,
            "visual_chain.coherence": 0.235},
 "params":  {"noise.amplitude": 0.192,
             "post.vignette_strength": -0.081,
             "rd.feed_rate": -0.0023,
             "noise.frequency_x": -0.235,
             "fb.decay": 0.0235, ...}}
```

None of the nine dimension-keyed params are in `uniforms.json`. This is the
entire regression.

### 1.2 Finding B — Dead reverberation consumer

`hapax-imagination-loop.service` is the systemd wrapper for
`agents.imagination_daemon`, which is the only process that instantiates
`ImaginationLoop` and therefore the only consumer of
`/dev/shm/hapax-vision/observation.txt` via `_check_reverberation`.

At investigation time the service was `inactive (dead)` with zero start
attempts in the journal. The unit is `linked` (symlink from
`~/.config/systemd/user/` into the repo), `preset: enabled`, and is pulled
by `hapax-visual-stack.target` via `Wants=`. It nevertheless never
transitioned to active during this boot.

Three concrete weaknesses in the unit file made this state possible and
invisible:

1. `StartLimitIntervalSec=300` and `StartLimitBurst=5` are in `[Service]`.
   Both keys belong in `[Unit]`; systemd logs `Unknown key` warnings and
   silently ignores them. Without rate-limit protection a flap storm has no
   ceiling, and the warnings in the journal are the *only* trace the unit
   ever leaves — producing the false impression that "the service was never
   even tried".
2. `OnFailure=notify-failure@%n.service` is also in `[Service]`; same
   problem. No ntfy alert fires when the daemon crashes.
3. There is no liveness watchdog. `hapax-reverie-monitor.timer` exists for
   reverie but does not cover imagination-loop, so a dead loop will sit dead
   until a human notices the reverberation cadence has flattened.

A manual `systemctl --user start hapax-imagination-loop.service` brings the
daemon up in under 2 s with a clean journal (`Imagination daemon starting`).
The unit is not broken; it is under-specified.

## 2 · Design

### 2.1 Core fix (Finding A)

Replace `_load_plan_defaults` with a version that handles both v1 and v2
schemas. The v2 path iterates `plan["targets"][*]["passes"]`; the v1 path is
kept as a fallback for any pre-v2 snapshot that may still exist in `/dev/shm`
during a transition, and so that the function is robust to whichever format
the Rust compiler emits next.

```python
def _iter_passes(plan: dict) -> Iterable[dict]:
    """Yield pass dicts from either v1 (flat) or v2 (targets.*) plan schemas."""
    targets = plan.get("targets")
    if isinstance(targets, dict):
        for target in targets.values():
            if isinstance(target, dict):
                yield from target.get("passes", [])
        return
    yield from plan.get("passes", [])
```

This is purely additive: any caller that was broken by v2 is now correct; no
v1 caller regresses.

The test strategy is a unit test covering three inputs:

- **v1 flat** — `{"passes": [{"node_id": "noise", "uniforms": {"amplitude": 0.7}}]}`
  → `{"noise.amplitude": 0.7}`
- **v2 single-target** — the exact shape emitted by the live compiler →
  full `{node.param: value}` map
- **v2 multi-target** — two targets (main + aux), assert params from both
  are merged, later target wins on key collision
- **Empty** — `{}` and `{"version": 2}` → `{}` without raising

A regression test asserts that writing a v2 plan and reading it back through
`_load_plan_defaults` produces a non-empty dict that contains
`"noise.amplitude"`. This would have caught the bug.

### 2.2 Content-material one-liner (periphery)

`_uniforms.write_uniforms` currently writes `content.material` and
`content.salience` after the main merge loop but does not write
`content.intensity`, even though the vocabulary declares all three and the
plan.json emits them. With Finding A unfixed this gap was invisible; with
Finding A fixed, `content.intensity` will come through from `plan_defaults`
as the constant vocabulary default (0.0) and never move. That is not a new
regression — it's a pre-existing missing mapping — but because this PR is
the one that makes the gap observable, the fix slots in naturally here.

Add intensity as a passthrough in the imagination block:

```python
if imagination:
    uniforms["content.material"]  = float(MATERIAL_MAP.get(str(...), 0))
    uniforms["content.salience"]  = float(imagination.get("salience", 0.0)) * silence
    uniforms["content.intensity"] = float(imagination.get("salience", 0.0)) * silence
```

Intensity follows salience × silence for now; it can be decoupled into a
separate fragment field later without changing this pathway.

### 2.3 Unit hygiene (Finding B, part 1)

Rewrite `systemd/units/hapax-imagination-loop.service`:

- Move `StartLimitIntervalSec=300` and `StartLimitBurst=5` into `[Unit]`.
- Move `OnFailure=notify-failure@%n.service` into `[Unit]`.
- Tighten ordering: `After=hapax-secrets.service hapax-dmn.service`
  (unchanged), but also add `Requires=hapax-dmn.service` so the loop cannot
  be up without its observation producer.
- `BindsTo=hapax-dmn.service` is tempting but too strict — DMN restarts
  would take the loop down. `Requires=` + `After=` is enough.

### 2.4 Liveness watchdog (Finding B, part 2)

Extend `hapax-reverie-monitor.service` (which already tails reverie's health
signal) to also assert `hapax-imagination-loop.service` is active. If not,
`systemctl --user start` it and emit a chronicle event. This is cheaper than
creating a parallel monitor and keeps all "is the reverie stack alive?"
logic in one place.

Implementation shape (script-level; Python monitor lives at
`agents/reverie_monitor.py` or equivalent):

```python
UNITS = ("hapax-reverie.service", "hapax-imagination-loop.service")

for unit in UNITS:
    status = subprocess.run(
        ["systemctl", "--user", "is-active", unit],
        capture_output=True, text=True
    ).stdout.strip()
    if status != "active":
        log.warning("reverie-monitor: %s is %s, restarting", unit, status)
        subprocess.run(["systemctl", "--user", "start", unit], check=False)
        record_chronicle_event("reverie-monitor", f"restarted {unit}")
```

The monitor timer's existing 5-minute cadence is acceptable; the Bachelard
Amendment 4 loop is not latency-critical. A 5-minute gap in reverberation
feedback is recoverable.

### 2.5 Architectural ratification (DMN-hosted claim)

The `project_reverie_autonomy.md` memory and the
`hapax-council/CLAUDE.md § Tauri-Only Runtime` section both describe reverie
as "hosted inside DMN as a concurrent async task". The implementation has
been a separate systemd daemon since 2026-03-26. This design formally
records the shift and updates the memory + CLAUDE.md.

**Rationale.** Reverie has its own fragility profile (Qdrant I/O, graph
rebuilds, GPU-adjacent work) that benefits from an independent cgroup and an
independent `Restart=on-failure` lifecycle. Co-hosting with DMN would force
DMN restarts every time reverie's graph builder raises, and vice versa. The
*spirit* of the structural-peer claim is "same cascade, same types, same
governance composition" — and those are all preserved. The letter was an
over-committal to in-process coupling.

**What changes.** This PR updates:

- `hapax-council/CLAUDE.md § Visual surface` — replace "hosts the actuation
  loop as a concurrent async task" with "runs as an independent systemd
  daemon that reads DMN-produced impingements via `/dev/shm`".
- `~/.claude/projects/-home-hapax-projects/memory/project_reverie_autonomy.md`
  — replace the same claim.
- `~/.claude/projects/-home-hapax-projects/memory/project_reverie.md` —
  upgrade the "per-node param bridge wired" claim to include the v2 schema
  fix reference.

No code change. The commit `17ccd547f` stands.

### 2.6 What this design does **not** change

- The vocabulary graph stays 8-pass linear. The 5-channel adaptive mixer is
  still a dormant forward commitment; it gets its own design doc when work
  starts on it. Out of scope here.
- The `agents/shaders/nodes/voronoi_overlay.wgsl` orphan is left in place.
  Removing it is a separate housekeeping PR.
- `dynamic_pipeline.rs:556-564` silent shader-load-failure smell is a
  logging upgrade, not a correctness bug. Left for a follow-up.
- No change to `content_layer.wgsl`. It was misread by the audit agent;
  re-verified as correct.

## 3 · Acceptance criteria

1. **Dimensional expression visible.** After the fix lands, at least eight
   of the nine `{node_id}.{param}` keys emitted by
   `visual_chain.compute_param_deltas()` appear in `uniforms.json` within
   one reverie tick of a non-zero dimension level. Verified by a live
   snapshot compare: `python -m agents.reverie.debug_uniforms` (to be
   written as part of this PR) reports a row per plan-default key with
   current value, or a manual `jq 'keys' /dev/shm/hapax-imagination/uniforms.json`
   shows ≥ 25 keys instead of 6.
2. **Regression test green.** `tests/reverie/test_uniforms_plan_schema.py`
   passes for v1, v2 single-target, v2 multi-target, and empty inputs.
3. **Imagination loop stays up.** `systemctl --user is-active
   hapax-imagination-loop.service` returns `active` after boot *and* after
   `systemctl --user daemon-reload`.
4. **Monitor restarts a killed loop.** `systemctl --user kill
   hapax-imagination-loop.service` followed by ≤ 5 min wait returns the
   service to `active` state via `hapax-reverie-monitor.timer`.
5. **Reverberation pathway closes.** With imagination-loop running and the
   DMN evaluative tick active, `observation.txt` writes should produce a
   nonzero `_last_reverberation` within two imagination cadences.
6. **No visual regression.** The frame at
   `/dev/shm/hapax-visual/frame.jpg` remains non-black; frame_time stays
   under 25 ms. This is a smoke check, not a rigorous A/B.
7. **Memory/CLAUDE.md aligned.** The two memory files and the council
   CLAUDE.md no longer claim reverie is hosted inside DMN.

## 4 · Risks and mitigations

| Risk | Likelihood | Mitigation |
|---|---|---|
| v2 fix inadvertently doubles param delta magnitude because Rust already applies plan defaults | low | The Rust path at `dynamic_pipeline.rs:803-821` only writes per-pass `params_buffer` from uniforms.json keys it finds. Plan defaults are already baked into the buffer at build time and are *overwritten* per-key when uniforms.json contains the key. Writing `base + delta` matches Rust's "uniforms.json is an absolute override" contract. No doubling. |
| `content.intensity` passthrough changes visible rendering | low | vocabulary default is 0.0; passthrough writes `salience × silence` which is 0.0 when imagination is absent. No change in the silent case. When imagination is present, opacity already drives visibility via `slot_opacities`, so intensity adds a small, expected boost. |
| Monitor loop thrashes a flapping unit | low | `StartLimitBurst=5, StartLimitIntervalSec=300` (now in `[Unit]`) caps retries. If the loop actually cannot start, the monitor will see `failed` state and skip restart after the rate limit fires. |
| Architectural ratification contradicts the constitution | none | The single-user / executive-function / consent axioms are unaffected. This is a process-boundary decision, not a governance one. |
| Reverberation consumer misbehaves on first tick after 2h downtime | low | `_check_reverberation` returns 0.0 if `recent_fragments` is empty, which it is on restart. No panic, degraded to baseline cadence until the next fragment is produced. |

## 5 · Verification after deploy

Run these, in order, post-merge:

```bash
# 1. Unit hygiene
systemctl --user daemon-reload
systemctl --user is-active hapax-imagination-loop.service   # → active

# 2. Schema fix live
jq 'keys | length' /dev/shm/hapax-imagination/uniforms.json  # → ≥ 25
jq '"noise.amplitude"' /dev/shm/hapax-imagination/uniforms.json   # → numeric

# 3. Delta presence
python -c "
import json, time
u1 = json.loads(open('/dev/shm/hapax-imagination/uniforms.json').read())
time.sleep(2)
u2 = json.loads(open('/dev/shm/hapax-imagination/uniforms.json').read())
moving = sum(1 for k in u1 if u1[k] != u2.get(k))
print(f'keys moving across 2s: {moving}')  # → > 0 when dimensions are active
"

# 4. Reverberation
journalctl --user -u hapax-imagination-loop.service --since '5 min ago' \
  | grep -i 'reverberation\|imagination tick'
```

## 6 · Follow-ups (tracked, not in this PR)

- **F1.** Add a debug command `python -m agents.reverie.debug_uniforms` that
  prints the live uniforms.json alongside expected plan-default keys and
  highlights any missing entries. Would have caught this bug instantly.
- **F2.** Upgrade `dynamic_pipeline.rs:556-564` shader-load-failure path from
  `log::warn!` to `log::error!` plus a degraded-signal publish.
- **F3.** Remove the orphaned `agents/shaders/nodes/voronoi_overlay.wgsl`
  unless it is being reserved for the 5-channel mixer epic.
- **F4.** Re-open the 5-channel mixer design and decide scheduling; it has
  been dormant since 2026-03-31.
- **F5.** Add a Prometheus metric for `reverie_uniforms_key_count` so the
  Grafana reverie-predictions dashboard can page on "visual chain went
  silent".
