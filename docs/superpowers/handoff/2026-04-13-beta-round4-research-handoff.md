# Beta Session Retirement Handoff — Round-4 Forward-Looking Research (Queue 025)

**Session:** beta
**Worktree:** `hapax-council--beta` @ `research/round4-forward-looking` (off main `28b9f2cf3`)
**Date:** 2026-04-13, 18:30–18:55 CDT
**Queue item:** 025 — fourth-round-forward-looking-research
**Depends on:** PR #752 (queue 022), PR #756 (queue 023), PR #759 (queue 024)
**Inflection:** `20260413-232000-alpha-beta-round4-research-brief.md`
**Register:** scientific, neutral (per `feedback_scientific_register.md`)

## One-paragraph summary

Six-phase forward-looking research shipped. Three findings
cross the BETA-FINDING-K severity bar (fail-open governance
patterns analogous to the PR #761 consent fix). The biggest
single finding is **Phase 2's CRITICAL background-task
supervision gap**: the daimonion has no supervision of its 10
`asyncio.create_task` background tasks during normal operation.
`asyncio.gather(..., return_exceptions=True)` only runs in the
shutdown `finally` block. **A crashed `CpalRunner.run()` would be
invisible; the daimonion would appear alive while voice cognition
was dead.** This is the plausible root cause explanation for
queue 024 Phase 4's "alive but silent" voice pipeline observation.
Plus Phase 1 found 2 governance fail-open patterns
(`_no_work_data` + the missing `obsidian-hapax/src/providers/`
directory), and Phase 4 found the SCM metrics layer is
pinned-at-floor across the board.

## Phase ship record

| phase | doc | status |
|---|---|---|
| 1 — axiom enforcement landscape | `phase-1-axiom-enforcement-audit.md` | **shipped** — 5 findings, 2 HIGH governance-adjacent |
| 2 — data-flow silent-failure sweep | `phase-2-dataflow-silent-failure.md` | **shipped** — 1 CRITICAL + 8 High + 11 Medium, 20 sites classified |
| 3 — cognitive-loop continuity | `phase-3-cognitive-loop-continuity.md` | **shipped** — per-coroutine classification + gap analysis + memory refinement |
| 4 — SCM metrics read-state | `phase-4-scm-metrics-state.md` | **shipped** — all metrics at floor, 6 next-signal candidates |
| 5 — salience routing state | `phase-5-salience-routing-state.md` | **partial** — code state complete, 20-row live decision table blocked on operator utterance |
| 6 — rebuild-services gap | `phase-6-rebuild-services-coverage.md` | **shipped** — 26 daemons classified, 12 gaps named, unified diff proposed |

Plus an earlier-session note: **alpha beat beta to FINDING-G in
real time** (PR #757 fixed the UDS readuntil-with-shutdown bug
before beta's Phase 1 of queue 024 could dig into the root cause).
The queue 024 Phase 1 finding was a DIFFERENT root cause
(throughput mismatch) and got overlaid on the same symptom;
alpha's root cause was the underlying issue and beta's was a
secondary interaction. Both are noted in the convergence.log.

## Convergence-critical findings (this session)

### BETA-FINDING-L (CRITICAL): unsupervised background tasks in daimonion

**Source phase:** Phase 2
**Severity:** CRITICAL — the plausible root cause for "voice pipeline alive but silent"

**Location**
- `agents/hapax_daimonion/run_inner.py:135–228`

**Evidence**

```python
# Lines 135-180: 10 create_task calls, all fire-and-forget
daemon._background_tasks.append(asyncio.create_task(proactive_delivery_loop(daemon)))
daemon._background_tasks.append(asyncio.create_task(workspace_monitor.run()))
daemon._background_tasks.append(asyncio.create_task(audio_loop(daemon)))
daemon._background_tasks.append(asyncio.create_task(perception_loop(daemon)))
daemon._background_tasks.append(asyncio.create_task(ambient_refresh_loop(daemon)))
daemon._background_tasks.append(asyncio.create_task(daemon._cpal_runner.run()))
daemon._background_tasks.append(asyncio.create_task(_cpal_impingement_loop()))
daemon._background_tasks.append(asyncio.create_task(impingement_consumer_loop(daemon)))
daemon._background_tasks.append(asyncio.create_task(actuation_loop(daemon)))

# Lines 182-208: main control loop NEVER checks task state
while daemon._running:
    daemon.notifications.prune_expired()
    # wav sweep, workspace monitor analysis, etc.
    await asyncio.sleep(1)

# Lines 226-228: gather ONLY in shutdown finally
finally:
    for task in daemon._background_tasks:
        task.cancel()
    await asyncio.gather(*daemon._background_tasks, return_exceptions=True)
```

**If `CpalRunner.run()` raises**, `cpal/runner.py:156-157` catches
it, logs with `log.exception`, and exits the coroutine via the
`finally` block setting `_running = False`. The Task completes.
The exception is **held in the Task object but never observed**.
The main loop continues running (workspace monitor, proactive
delivery, audio loop still fire). The daimonion appears alive.
Voice cognition is dead.

**Queue 024 Phase 4 observed exactly this symptom** — zero TTS
log lines in a 10-minute window despite the daemon running. The
zombie interpretation was not named but is plausible.

**Fix options**

A. **TaskGroup restructure** (Python 3.11+): replace the list of
   create_task calls with `async with asyncio.TaskGroup() as tg:
   tg.create_task(...)`. TaskGroup propagates child exceptions
   automatically. Clean but requires restructuring the main loop.

B. **Supervisor loop**: in the main control loop, check every
   tick:

   ```python
   for task in daemon._background_tasks:
       if task.done() and not task.cancelled():
           exc = task.exception()
           if exc is not None:
               log.exception("background task %s crashed", task.get_name(), exc_info=exc)
               raise SystemExit(1)  # let systemd restart
   ```

   Minimal change, 30 lines. Immediately detects crashes.

**Recommendation:** Option B now (land fast), Option A in a
follow-up cleanup. Axiom weight: `executive_function` (95) —
silent voice-pipeline death is an executive-function regression.

### BETA-FINDING-M (HIGH): `_no_work_data` fail-open on missing metadata

**Source phase:** Phase 1
**Severity:** HIGH — analogous to BETA-FINDING-K, `corporate_boundary` weight 90

**Location**
`agents/_governance/agent_governor.py:56-88`

**Pattern**

```python
def _no_work_data(_agent_id: str, data: Labeled[Any]) -> bool:
    """Deny data categorized as work/employer data."""
    if hasattr(data, "metadata") and isinstance(data.metadata, dict):
        return data.metadata.get("data_category") != "work"
    return True  # No metadata = no category = allowed  ← FAIL-OPEN
```

**Impact:** any unlabeled data flows through the `corporate_boundary`
policy without being filtered. The enforcement is "deny known-unsafe,
allow everything else" instead of the fail-closed "allow
known-safe, deny everything else."

**Fix:** identical pattern to PR #761 — raise on missing metadata,
make callers attach labels explicitly.

### BETA-FINDING-N (HIGH): obsidian-hapax `providers/` directory missing

**Source phase:** Phase 1
**Severity:** HIGH — `corporate_boundary` weight 90

**Location**
- Expected: `obsidian-hapax/src/providers/anthropic.ts`, `openai-compatible.ts`, `index.ts`
- Actual: directory does not exist
- Sufficiency probe that checks for this: `shared/sufficiency_probes.py:430+` (`_check_plugin_direct_api_support`)

**Impact:** the plugin's only API path is `logos-client.ts` which
targets `http://localhost:8051`. On an employer-managed device,
this is unreachable. The axiom says the plugin should "degrade
gracefully" with employer-sanctioned providers — but the
graceful-degradation path doesn't exist.

**Fix:** out of scope for research; file as a missing-feature
backlog item.

### BETA-FINDING-O (HIGH): SCM metrics all pinned at floor, no control feedback

**Source phase:** Phase 4
**Severity:** HIGH — `project_scm_formalization` memory overclaims

**Evidence:**
- Eigenform `converged=True, max_delta=0.0, eigenform_type="fixed_point"` across 951 log entries (all identical state vectors)
- Sheaf restriction residual rms 0.2416, h1_dimension 4 — moderate inconsistency
- Stimmung `health=0.072, processing_throughput=0.008, perception_confidence=0.068, grounding_quality=0.0 stale 121s`
- All 12 stimmung dimensions stable; stance = `cautious`

**Interpretation:** the SCM layer is a **passive reader**. Nothing
uses the metrics to gate runtime behavior. The "sheaf/topology/
eigenform metrics operational" claim in the project memory is
technically true (values computed and stored) but operationally
vacuous (no feedback, all at floor).

**Next-signal candidates** (Phase 4 § Ranked):
1. Fix grounding_quality freshness (121 s stale → should tick)
2. Wire presence/activity/heart_rate into eigenform log (all zero)
3. Expose SCM metrics via Prometheus (depends on round-3 Phase 2)
4. Add `eigenform_state_velocity` gauge for fixed-point detection
5. Operator-utterance end-to-end validation

### BETA-FINDING-P: compositor `studio-compositor-reload.path` no branch check

**Source phase:** Phase 6
**Severity:** MEDIUM — operationally disruptive, was observed live in queue 023

**Location**
`~/.config/systemd/user/studio-compositor-reload.path`

**Impact:** the path unit fires on any file change in the
watched directories (`agents/studio_compositor/`, `agents/effect_graph/`,
`agents/shaders/nodes/`, `presets/`). No branch check. If alpha
edits compositor source on a feature branch, the path watcher
fires a restart immediately. This is why beta saw 3 unexplained
compositor restarts during queue 023 research.

**Fix:** migrate compositor to `hapax-rebuild-services.service`
which has a branch check in `rebuild-service.sh:99`. Delete the
path unit.

## Secondary findings

- **Phase 1:** `check_full` precedent store silent catch at DEBUG level (`shared/axiom_enforcement.py:307`). Same shape as BETA-FINDING-K but with less blast radius because fast rules still run.
- **Phase 1:** `management_governance` runtime governor regex is narrow (2 patterns covering `feedback/coaching/performance.review/1-on-1` + `draft.*(conversation/difficult/termination/pip)`). Synonyms bypass. Defense in depth is weak.
- **Phase 1:** SDLC commit hook `axiom-commit-scan.sh` fails open if `jq` is missing.
- **Phase 2:** CPAL `run()` on `_tick` exception silently stops the cognitive loop (H1, propagates from C1).
- **Phase 2:** CPAL goodbye TTS failure at DEBUG (H2), `_check_stimmung` bare swallow (H3), `_publish_state` DEBUG swallow (H4), spontaneous speech DEBUG swallow (H5).
- **Phase 2:** Compositor RTMP metric bare swallow (H6), layout persistence fail-non-fatal (H7), command server fail-non-fatal (H8).
- **Phase 3:** The `feedback_cognitive_loop` claim holds for the control layer (CPAL at 150 ms, impingement consumer at 0.5 s) but NOT for the T3 LLM formulation path. The LLM call is still cold-start per utterance. Memory should be refined.
- **Phase 5:** Salience router is live and called per-utterance but its output is structurally discarded in `conversation_pipeline.py:641-646` — every non-CANNED routing decision gets rewritten to CAPABLE. This matches `project_intelligence_first` intent. The `_seeking` flag and `set_seeking()` method exist but grep for callers returns zero. `stimmung_shed` is NOT implemented (memory says "intelligence is last thing shed under stimmung" — no code does this).
- **Phase 6:** 19 of 26 long-running daemons have no rebuild path. Most critical gaps: visual-layer-aggregator, hapax-content-resolver, hapax-watch-receiver, hapax-reverie, hapax-imagination-loop, studio-fx, studio-fx-output, studio-person-detector.

## Ranked fix backlog (items 89–132, continuing from queue 022/023/024)

Full list in each phase doc's "Backlog additions" section. Summary by severity:

### Critical (must ship first)

- **96**: `feat(daimonion): background task supervisor` [Phase 2 C1] — the single biggest fix
- **89**: `fix(governance): _no_work_data fail-closed on missing metadata` [Phase 1 F1]

### High

- **90**: obsidian-hapax `providers/` directory [Phase 1 F2] — multi-day implementation
- **91**: `check_full` precedent store loudify [Phase 1 F4]
- **92**: axiom-commit-scan.sh fail-loud [Phase 1 F5]
- **97-103**: CPAL + compositor silent catch upgrades [Phase 2 H2-H8]
- **108-112**: cognitive-loop continuity features [Phase 3]
- **114-117**: SCM metric fixes (grounding freshness, eigenform wiring, gauges) [Phase 4]
- **121-127**: salience routing + stimmung_shed [Phase 5]
- **128-132**: rebuild-services coverage + branch-check [Phase 6]

### Medium

- **93-95**: management_governance broadening, hook audit, governance counter
- **104-107**: CPAL presence/TPN/signal cache counters
- **113**: docs refinement of feedback_cognitive_loop memory
- **118-120**: Grafana SCM dashboard, operator-utterance validation, docs refinement

### Backlog cross-reference

| range | source |
|---|---|
| 1–16 | PR #752 (queue 022) |
| 17–41 | PR #756 (queue 023) |
| 42–88 | PR #759 (queue 024) |
| **89–132** | **PR #??? (queue 025, this handoff)** |

## What the next session should read first

1. **`phase-2-dataflow-silent-failure.md` § The Critical finding** — BETA-FINDING-L, unsupervised background tasks. This is the biggest fix in the entire round-4 backlog and likely explains queue 024's "voice alive but silent" observation.
2. **`phase-1-axiom-enforcement-audit.md` § Finding 1** — `_no_work_data` fail-open. Same fix shape as PR #761, should ship together as the next governance patch.
3. **`phase-4-scm-metrics-state.md` § Headline** — the SCM is pinned-at-floor, which explains why stimmung-gated features (SEEKING transitions, stimmung_shed) aren't firing.
4. **`phase-6-rebuild-services-coverage.md` § Headline** — 19 daemons with no rebuild path is a lot of friction; the unified diff in the doc is drop-in.
5. **`phase-5-salience-routing-state.md` § Gap analysis** — `stimmung_shed` is claimed in memory but not implemented. `_seeking` has no caller. Salience routing is more diagnostic than functional today.

## Coordination notes

- **Alpha's in-flight PRs** at session start: PR #760 (pool metrics IPC, merged during session) and PR #761 (BETA-FINDING-K consent fix, still open). Phase 1's `_no_work_data` finding is a direct follow-up pattern to PR #761 and should land together with it.
- **Phase 5 20-row table is deferred** — the session had zero voice activity. The reproduction command is embedded in the phase doc for the next session to run.
- **Phase 6 fixes are cross-repo** — the systemd user unit file is in `systemd/units/hapax-rebuild-services.service` in the hapax-council repo, but reloading requires `systemctl --user daemon-reload` which is operator action.
- **Background task supervisor (BETA-FINDING-L)** can be shipped as a local fix in `run_inner.py` without cross-repo coordination. Recommended to land this FIRST.

## Open questions

1. **(alpha)** Is BETA-FINDING-L Option B (supervisor loop) acceptable as a first pass, or should we jump to Option A (TaskGroup) immediately? Option B is 30 lines, Option A is ~100 lines but cleaner.
2. **(operator)** Phase 1 Finding 2 (obsidian-hapax providers) is a missing feature, not a bug fix. Should it go on the round-4 backlog or be separated into a multi-day scoping task?
3. **(operator)** Phase 4 SCM metrics are pinned-at-floor. Is the SCM layer expected to be dormant until the operator actively uses the system (e.g., speaks, uses tools), or is the current state a bug?
4. **(alpha)** Phase 5 found `stimmung_shed` is claimed in memory but not implemented. Should round-5 include a spec pass for it, or mark the memory as aspirational?
5. **(operator)** Phase 6 proposes adding 8 ExecStart entries to rebuild-services. Any of the 8 you want to skip or defer?

## Beta retirement status

Beta considers queue 025 complete. All 6 phases shipped, with
Phase 5 partially deferred (live decision table blocked on
zero-voice session). The retirement handoff consolidates items
89–132 of the ranked backlog continuing from PR #752 / #756 /
#759.

Beta will commit the research docs to
`research/round4-forward-looking`, push, open the PR, and stand
down.

`~/.cache/hapax/relay/beta.yaml` will point at this handoff doc
as the authoritative closeout. No other beta work is in flight.
