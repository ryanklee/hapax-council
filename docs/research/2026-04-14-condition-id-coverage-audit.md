# condition_id coverage audit — Phase 4 voice-pipeline scope sufficiency + engine-side gaps

**Date:** 2026-04-14
**Author:** delta (research/beta support role)
**Scope:** Full audit of every production `hapax_trace` /
`hapax_span` / `hapax_event` / `hapax_score` callsite in the
council codebase, assessed against LRR Phase 4's voice-pipeline
condition_id plumbing scope. Verifies whether the Phase 4 scope
is sufficient to make voice-grounding DVs filterable by
`metadata.condition_id`, and identifies which telemetry is **not**
covered — specifically, the logos engine and its rule subsystems.
**Register:** scientific, neutral.
**Status:** investigation — no code changed. Ring 1/2 fixes
proposed; operator decision deferred.
**Companion drops:** #50, #51, #52 (cam/OBS/FD-leak); this drop
pivots the session from cam-stability research to research-
validity research.
**Prompts:** operator directive to "research and evaluate the
best use of [delta's] time to support LRR and alpha and beta";
ranked #1 in the evaluation because it is the only candidate
capable of producing a novel research-design finding without
conflicting with beta's Phase 4 bootstrap.

## 0. Headline

**Phase 4's voice-pipeline condition_id scope is sufficient for
the primary DVs.** Langfuse's `propagate_attributes` context
manager (used inside `shared/telemetry.py::hapax_trace` +
`agents/_telemetry.py::hapax_trace`) automatically inherits
metadata onto every child observation created within its
context — verified directly in the langfuse source
(`.venv/lib/python3.12/site-packages/langfuse/_client/propagation.py:85-149`)
and documented as the mechanism for trace-level attribute
propagation. Every `hapax_event` / `hapax_span` / `hapax_score`
fired inside `conversation_pipeline._process_utterance_inner`
inherits `condition_id` for free once Phase 4's commit
`faad34e16` lands.

**But there is a research-validity gap at the subsystem boundary.**
Telemetry fired **outside** the voice utterance trace — in
particular from the logos reactive engine (`logos/engine/*`) —
does **not** carry `condition_id`. The following callsites
produce observations that the Phase 4 scope does not cover:

| File | Line | Name | Level |
|---|---|---|---|
| `logos/engine/__init__.py` | 429 | `engine.event` (hapax_trace) | root |
| `logos/engine/__init__.py` | 439 | `engine.evaluate_rules` (hapax_span) | child |
| `logos/engine/__init__.py` | 569 | `engine.execute` (hapax_span) | child |
| `logos/engine/__init__.py` | 644 | `prediction.novel_pattern` (hapax_event) | root |
| `logos/engine/__init__.py` | 662 | `prediction.distribution_shift` (hapax_event) | root |
| `logos/engine/executor.py` | 52 | `engine.action.{name}` (hapax_span) | child |
| `logos/engine/rules_phase0.py` | 235 | `presence.operator_away` (hapax_event) | root |
| `logos/engine/rules_phase0.py` | 237 | `presence.operator_returned` (hapax_event) | root |
| `logos/engine/rules_phase0.py` | 318 | `consent.phase_{to_phase}` (hapax_event) | root |
| `logos/engine/rules_phase0.py` | 399 | `biometric.stress_transition` (hapax_event) | root |
| `logos/engine/rules_phase0.py` | 447,453 | `biometric.health_summary_received` (hapax_event) | root |
| `agents/hapax_daimonion/eval_grounding.py` | 417 | `voice.grounding_eval` (hapax_event) | root |

Plus `shared/chronicle.py` JSONL records written from
`logos/engine/__init__.py:448+584` and `agents/reverie/mixer.py:
206+352`, whose `payload` dicts do not include `condition_id`.

**Impact on Phase A baseline research:** none for primary DVs
(voice grounding scores). The engine-side gap shows up during
**confounder analysis**, where a researcher wants to check
whether operator presence, stress transitions, consent-phase
changes, or engine-rule load correlate with condition switches.
Currently a time-range join is required to merge engine events
with voice scores; a direct `metadata.condition_id` filter is
not available for engine observations.

**Proposed remediation:** 12 engine-side callsite edits + 2
Reverie-mixer chronicle records = **~30 lines total** across 5
files. All edits use beta's pre-staged `shared/research_marker
.read_research_marker()` helper from commit `3d9be7da9` (beta
worktree, PR #819 pending). Ring 1 fix — purely additive
metadata, no architectural change, zero risk to the DV pipeline.

## 1. Propagation mechanism: verification

Phase 4 scope item 1 (per the Phase 4 spec beta drafted at
`docs/superpowers/specs/2026-04-14-lrr-phase-4-phase-a-completion-design.md`,
§3.1) says:

> **Score-level attribution is stronger than trace-level.**
> Langfuse's query API can filter scores directly by
> `metadata.condition_id` without needing a two-step trace-then-
> score lookup.

This implies — without explicitly stating it — that child
observations automatically inherit trace metadata. Beta's
pre-staged commits back this up (trace gets condition_id in
`hapax_trace` metadata, child scores are queried via
`metadata_filter={"condition_id": ...}` on the scores, not on
the scores' explicit metadata).

**Direct verification** in the installed langfuse package:

```python
# .venv/lib/python3.12/site-packages/langfuse/_client/propagation.py:85
"""Propagate trace-level attributes to all spans created within this context.

This context manager sets attributes on the currently active span AND
automatically propagates them to all new child spans created within the
context. This is the recommended way to set trace-level attributes like
user_id, session_id, and metadata dimensions that should be consistently
applied across all observations in a trace.
"""
```

And the example:

```python
# :134-149
with langfuse.start_as_current_span(name="user_workflow") as span:
    with langfuse.propagate_attributes(
        user_id="user_123",
        session_id="session_abc",
        metadata={"experiment": "variant_a", "environment": "production"}
    ):
        # All spans created here will have user_id, session_id, and metadata
        with langfuse.start_span(name="llm_call") as llm_span:
            # This span inherits: user_id, session_id, experiment, environment
            ...
```

**Mechanism:** langfuse's `propagate_attributes` pushes attributes
onto the OpenTelemetry baggage context. When a new observation
is created via `client.start_as_current_observation(...)`,
langfuse reads the baggage and merges it with the observation's
explicit metadata. Inheritance is automatic, asynchronous-safe
(via `contextvars`), and only applies to observations created
**within** the context manager's active span.

**What this means for Phase 4:**

- `hapax_trace("voice", "utterance", metadata={"condition_id": cid, ...})` opens a `propagate_attributes` context.
- Every `hapax_event`, `hapax_span`, and `hapax_score` called from the same asyncio task while that context is active — i.e. inside `_process_utterance_inner` — inherits `condition_id` automatically without an explicit metadata kwarg.
- When `_utt_trace_cm.__exit__` runs at the end of `_process_utterance` (line 497), the context unwinds and subsequent telemetry loses the inheritance.

**Verification of the inheritance for voice sub-events** is
already in beta's pre-staged Phase 4 test plan (§3.1 step 4
calls `langfuse_client.get_scores(metadata_filter={"condition_id":
"cond-phase-a-test-stream-NNN"})` and expects ≥5 scores per DV
name to return). Implicitly, this test validates that scores
carry condition_id — and the only way they can is via metadata
inheritance from the parent trace.

## 2. Coverage map

### 2.1 Telemetry sites that carry condition_id *after* Phase 4

**Directly tagged (explicit metadata kwarg):**

| File:Line | Call | Tag mechanism |
|---|---|---|
| `agents/studio_compositor/director_loop.py:648` | `hapax_span("stream", "reaction", metadata={"condition_id": ...})` | Phase 1 shipped — reads `/dev/shm/hapax-compositor/research-marker.json` via `_read_research_marker()` |
| `agents/hapax_daimonion/conversation_pipeline.py:482` | `hapax_trace("voice", "utterance", metadata={"condition_id": ...})` | Phase 4 pending — beta's commit `faad34e16` (in beta worktree, PR #819) |
| `agents/hapax_daimonion/grounding_evaluator.py:~199` | `hapax_score(..., metadata={"condition_id": ...})` | Phase 4 pending — same commit |

**Inherited via `propagate_attributes` (Phase 4 automatic):**

| File:Line | Call | Inherited because |
|---|---|---|
| `agents/hapax_daimonion/conversation_pipeline.py:538` | `hapax_event("voice", "stt_done", metadata={"stt_ms": ...})` | Inside `_process_utterance_inner` → inside `hapax_trace("voice", "utterance")` propagate_attributes context |
| `agents/hapax_daimonion/conversation_pipeline.py:665` | `hapax_event("voice", "routed", metadata={"tier": ...})` | Same |
| `agents/hapax_daimonion/conversation_pipeline.py:810` | `hapax_score(_utt_trace, "sentinel_retrieval", ...)` | Score is attached directly to `_utt_trace` |
| `agents/hapax_daimonion/conversation_pipeline.py:895-926` | `hapax_score(_utt_trace, "frustration_score", ...)` + 6 other scores | Same — direct trace attachment |
| `agents/hapax_daimonion/conversation_pipeline.py:1706` | `hapax_event("voice", "tts_synth", metadata={"tts_ms": ...})` | Inside the utterance trace (assuming trace is still active at this point — needs verification) |
| `agents/hapax_daimonion/conversation_pipeline.py:1867` | `hapax_event(...)` (unclear from grep alone) | TBD — may or may not be inside the trace |

**Compositor-side non-Langfuse paths (Phase 2 shipped):**

| File:Line | Write target | condition_id source |
|---|---|---|
| `agents/studio_compositor/hls_archive.py:243` | HLS segment sidecar | `_load_condition_id()` reads `current.txt` |
| `agents/studio_compositor/hls_archive.py:265` | Qdrant stream-reactions | Same |
| `agents/studio_compositor/research_marker_overlay.py:83` | Cairo overlay banner | Reads marker file directly |
| `shared/stream_archive.py` | Archive sidecar struct field | Attribute of the ArchiveEntry model |
| `shared/vault_note_renderer.py:59` | Vault note frontmatter | Rendered from sidecar |

This covers the **LRR research data plane** for the livestream
condition (Phase 2) and the voice grounding condition (Phase 4).

### 2.2 Telemetry sites that do **not** carry condition_id

All callsites outside the compositor and outside the voice
utterance trace fall through to "no condition_id".

**Logos reactive engine (`logos/engine/__init__.py`):**

- **Line 429:** `hapax_trace("engine", "event", metadata={"path", "event_type", "doc_type"})` — root trace, one per inotify event. This is the engine's **main trace**. Every inotify-triggered rule evaluation creates one, regardless of whether the operator is speaking. These cross all condition boundaries.
- **Line 439 (nested):** `hapax_span("engine", "evaluate_rules", metadata={"rule_count"})` — runs inside the engine trace; inherits nothing because the parent has no `propagate_attributes` context holding condition_id.
- **Line 569 (nested):** `hapax_span("engine", "execute", metadata={"action_count", "actions"})` — same.
- **Line 644 (root):** `hapax_event("prediction", "novel_pattern", metadata={"pattern", "occurrence"})` — WARNING level. One per observed novel event pattern.
- **Line 662 (root):** `hapax_event("prediction", "distribution_shift", metadata={"shift_score"})` — WARNING level. Every 10 events if shift > 0.5.

**Executor (`logos/engine/executor.py`):**

- **Line 52:** `hapax_span("engine", f"action.{action.name}", metadata={"phase", "priority"})` — one span per action execution. Child of the engine trace.

**Rules phase 0 (`logos/engine/rules_phase0.py`):**

- **Line 235:** `hapax_event("presence", "operator_away", metadata={"from_state"})` — fired on perception-state.json transitions. Decoupled from voice session; can fire mid-condition.
- **Line 237:** `hapax_event("presence", "operator_returned", metadata={"from_state"})` — same.
- **Line 318:** `hapax_event("consent", f"phase_{to_phase}", metadata={"from_phase", "to_phase"})` — guest detection, consent resolution.
- **Line 399:** `hapax_event("biometric", "stress_transition", metadata={"from", "to"})` — fires on Pixel Watch stress field transitions.
- **Line 447, 453:** `hapax_event("biometric", "health_summary_received", metadata={"path", "facts"})` — phone health sync events.

**Daimonion offline eval (`agents/hapax_daimonion/eval_grounding.py`):**

- **Line 417:** `hapax_event("voice", "grounding_eval", metadata={"session_id", "turn_count", "acceptance_rate", ...})` — fired from `push_scores` when the eval harness runs. **Offline**, not in an active trace context.

**Chronicle records** (separate persistence path — `shared/chronicle.py`,
written to `/dev/shm/hapax-chronicle/events.jsonl`):

- **`logos/engine/__init__.py:448`** — `chronicle_record(ChronicleEvent(event_type="rule.matched", payload={"rules", "event_path", "doc_type"}))` — NO condition_id in payload.
- **`logos/engine/__init__.py:584`** — `chronicle_record(event_type="action.executed", payload={"action_name", "event_path"})` — same.
- **`agents/reverie/mixer.py:206`, :352** — reverie chronicle records; payload omitted in audit but verified by grep to not reference condition_id.

### 2.3 What *is not* a gap

- **`conversation_pipeline.py` hapax_event calls inside `_process_utterance_inner`** inherit condition_id automatically via propagate_attributes. Verified above.
- **Compositor director_loop reactions** are explicitly tagged from Phase 1.
- **HLS archive + stream archive + vault rendering** are tagged from Phase 2.
- **Daimonion background tasks** (grep confirmed: no `hapax_event` calls in daimonion outside conversation_pipeline/grounding_evaluator/eval_grounding).
- **Affordance pipeline** has no Langfuse instrumentation at all (separate observability gap, out of scope for this audit).

## 3. Research-validity impact

The question this audit answers: **does the engine-side coverage
gap represent a research-validity threat to the Phase A baseline
collection?**

### 3.1 Primary DV attribution: not affected

The Phase 4 spec (§4 acceptance criteria) defines success as:

> ≥M voice grounding DVs in Langfuse with
> `metadata.condition_id=cond-phase-a-baseline-qwen-001`
> covering `turn_pair_coherence`, `context_anchor_success`,
> `activation_score`, `acceptance_type`, and `sentinel_retrieval`.

Each of these 5 DVs is a `hapax_score` called on `_utt_trace`
directly. Via inheritance, each inherits `condition_id` from the
`hapax_trace("voice", "utterance")` metadata. **Phase 4's
bootstrap commits cover this — no gap.**

### 3.2 Confounder attribution: partially affected

A clean analysis of Phase A requires not just DV attribution but
**confounder control**. Common confounders for a voice grounding
experiment include:

| Confounder | Source | Telemetry | condition_id tagged? |
|---|---|---|---|
| Operator stress state | Pixel Watch → VLA → perception-state.json | `biometric.stress_transition` | ❌ not tagged |
| Operator presence | perception engine → perception-state.json | `presence.operator_away`, `presence.operator_returned` | ❌ not tagged |
| Guest presence | Same | `consent.phase_*` | ❌ not tagged |
| Session load | Engine event rate | `engine.event` trace count | ❌ not tagged |
| System novelty | Distribution-shift signal | `prediction.distribution_shift` | ❌ not tagged |
| Time of day | Implicit in timestamps | N/A — computable from any event | N/A |

For confounder analysis during Phase A, a researcher currently has
two options:

**Option A — time-range join.** Query engine events in
Langfuse's time range matching the condition window from the
research registry (`~/hapax-state/research-registry/<cid>/
condition.yaml` `opened_at` to `closed_at`). Then correlate
engine events to voice DVs by timestamp proximity.

- **Pros:** works today with zero code change. Research registry
  already records open/close timestamps.
- **Cons:** error-prone for boundary events (events at the
  instant of condition switch could belong to either condition).
  Requires the analyst to manually align windows. No categorical
  join key means all analysis scripts must use timestamp logic.
  Langfuse's metadata filter index is faster than its timestamp
  scan for large volumes.

**Option B — explicit condition_id tagging on engine events.**
Add `metadata={"condition_id": read_research_marker()}` to each
engine callsite. The existing `shared/research_marker.py`
module (pre-staged by beta in PR #819) provides the helper
with built-in 5-second caching.

- **Pros:** categorical join across subsystems. Analysis scripts
  become single-query lookups. No boundary ambiguity. Faster
  Langfuse queries.
- **Cons:** requires engineering work (~30 lines across 5
  files). Requires Phase 4 (shared/research_marker.py) to land
  first.

**Does Option A's error rate matter for Phase A baseline?**

Probably not, for three reasons:

1. **Condition A runs for a long time** (likely weeks, per the
   Phase 4 spec's "time-gated" note). Boundary events are a
   small fraction of total observations. A 1-second ambiguous
   window around each switch is a rounding error.
2. **Confounder analysis is post-hoc and exploratory,** not a
   pre-registered primary analysis. The pre-registration
   (CYCLE-2-PREREGISTRATION.md) commits to the 5 DVs listed
   above. Confounder checks are secondary QA.
3. **The research-registry marker-change log** (`~/hapax-state/
   research-registry/research_marker_changes.jsonl`) records
   exact transition times, so even if a boundary event's
   attribution is ambiguous, the researcher can reconstruct the
   ambiguity window post-hoc.

**Does Option A's error rate matter for Phase A-vs-A' comparison?**

Potentially yes. Phase A → A' is a substrate swap (Qwen → Hermes
3). The comparison is the Shaikh claim test. If a confounder
(e.g., operator stress) happens to correlate with the substrate
swap by coincidence — say the swap happens during a stressful
week for the operator, which is not implausible — the confounder
will appear as an effect of the substrate in any un-corrected
analysis. To detect and correct for this, the analyst MUST be
able to slice engine events by condition_id post-hoc. Option A
makes this harder; Option B makes it trivial.

**My read:** Option B is strongly desirable **for the A-vs-A'
comparison**. Option A is fine for Phase A baseline in
isolation, which is what Phase 4 is collecting. A
Phase-B engineering follow-up that ships Option B before Phase
5 execution would be the cleanest path.

### 3.3 Chronicle records: separate observability, separate gap

`shared/chronicle.py` is a distinct persistence layer from
Langfuse. It writes JSONL to `/dev/shm/hapax-chronicle/events
.jsonl` with a 12-hour retention, and is used by the
chronicle-query tool (`/api/chronicle/*` routes in the logos
API). Engine events recorded via `chronicle_record` carry a
payload dict that does **not** include condition_id. The same
remediation pattern applies (read_research_marker + payload
merge), but the fix is in `shared/chronicle.py`'s producer sites
rather than the Langfuse wrappers.

The chronicle gap is lower-priority than the Langfuse gap
because chronicle events have a 12-hour retention — they're not
used for long-horizon research analysis. But for real-time
dashboards showing "what is hapax doing under this condition",
the gap still matters.

## 4. Proposed Ring 1 remediation

The fix is a pattern-level edit: at each of the 12 engine-side
Langfuse callsites listed in §2.2, add a `condition_id` key to
the metadata dict, sourced from `shared.research_marker.
read_research_marker()`.

### 4.1 Prerequisites

- Beta's Phase 4 bootstrap must land first (PR #819 or equivalent). Specifically, `shared/research_marker.py` must exist on main.
- This remediation is therefore Phase 4.5 or early Phase B work — it cannot ship before Phase 4 item 1 is merged.

### 4.2 Ring 1 engine-side callsite edits

Each edit follows the same pattern:

```python
# Before:
hapax_event(
    "presence",
    "operator_away",
    metadata={"from_state": from_state},
)

# After:
from shared.research_marker import read_research_marker
hapax_event(
    "presence",
    "operator_away",
    metadata={
        "from_state": from_state,
        "condition_id": read_research_marker() or "none",
    },
)
```

The helper reads `/dev/shm/hapax-compositor/research-marker.json`
with a 5-second in-memory cache, so the filesystem hit amortizes
to essentially free on the engine's event-driven cadence.

**Per-file edit list (Ring 1):**

| # | File:Line | Call | Metadata keys to add |
|---|---|---|---|
| **CID-1** | `logos/engine/__init__.py:429` | `hapax_trace("engine", "event", ...)` | `"condition_id": read_research_marker() or "none"` |
| **CID-2** | `logos/engine/__init__.py:644` | `hapax_event("prediction", "novel_pattern", ...)` | Same |
| **CID-3** | `logos/engine/__init__.py:662` | `hapax_event("prediction", "distribution_shift", ...)` | Same |
| **CID-4** | `logos/engine/executor.py:52` | `hapax_span("engine", "action.{name}", ...)` | Same |
| **CID-5** | `logos/engine/rules_phase0.py:235` | `hapax_event("presence", "operator_away", ...)` | Same |
| **CID-6** | `logos/engine/rules_phase0.py:237` | `hapax_event("presence", "operator_returned", ...)` | Same |
| **CID-7** | `logos/engine/rules_phase0.py:318` | `hapax_event("consent", "phase_*", ...)` | Same |
| **CID-8** | `logos/engine/rules_phase0.py:399` | `hapax_event("biometric", "stress_transition", ...)` | Same |
| **CID-9** | `logos/engine/rules_phase0.py:447,453` | `hapax_event("biometric", "health_summary_received", ...)` | Same |

**Note:** CID-1 is the most important. By adding condition_id to
the **root** `hapax_trace("engine", "event")` call, propagate_
attributes automatically propagates it to the child spans at
lines 439 and 569 — so CID-2/CID-3 for those children are not
needed. The same applies to CID-4 (executor.py action spans) —
but the executor is called from `await self._executor.execute(
plan)` **inside** the engine trace context, so propagate_
attributes should already cover it.

**Revised minimal edit list (after accounting for propagation):**

| # | File:Line | Reason |
|---|---|---|
| **CID-1** | `logos/engine/__init__.py:429` | Root trace — propagates to children of `evaluate_rules` and `execute` |
| **CID-2** | `logos/engine/__init__.py:644` | Root `novel_pattern` event fired OUTSIDE the engine.event trace (grep required to confirm — line 642 shows it inside the async handler after the trace context ended) |
| **CID-3** | `logos/engine/__init__.py:662` | Same — `distribution_shift` fired after the trace context |
| **CID-5** | `logos/engine/rules_phase0.py:235` | Fired from handler called via `await self._executor.execute(...)` which runs INSIDE the engine trace — may already inherit via propagate_attributes. Needs verification. |
| **CID-6** | Same | Same |
| **CID-7** | `logos/engine/rules_phase0.py:318` | Same |
| **CID-8** | `logos/engine/rules_phase0.py:399` | Same — but fired from `_handle_biometric_state_change` which runs in an asyncio.to_thread — context propagation boundary. **Likely does not inherit.** |
| **CID-9** | `logos/engine/rules_phase0.py:447,453` | `_handle_phone_health_summary` runs async; propagation status depends on whether `_handle_*` runs within the engine trace. Needs verification. |

**Open question (requires a 30-minute experimental verification
against a running logos-api):** does the engine's `hapax_trace`
context survive across `await self._executor.execute(plan)` into
the action handlers? The asyncio contextvar propagation rules
suggest **yes**, because `execute` is awaited directly in the
same task. But handlers that internally use `asyncio.to_thread`
or `run_in_executor` cross a task boundary and **lose** the
propagated context. Several rules_phase0 handlers use
`asyncio.to_thread(send_notification, ...)` or call async work
that may cross task boundaries.

**If propagation covers most of the engine** (hypothesis to
verify): **CID-1, CID-2, CID-3 are the minimum necessary edits**.
The rest inherit automatically.

**If propagation does not cover rules_phase0 handlers** (pessimistic
case): **CID-5 through CID-9 are also required**.

**Conservative recommendation:** ship **all** edits in CID-1
through CID-9 to be defensive. The extra 6 `metadata["condition_id"]
= ...` lines are trivial cost for removing the propagation
uncertainty from the analyst's mental model.

**Effort estimate:** 30 lines total, ~45 minutes for
implementation + ~30 minutes for test verification = **~1.5
hours** of Ring 1 work. Blocked by Phase 4 bootstrap landing.

### 4.3 Ring 2 chronicle-side remediation

For the `shared/chronicle.py` payload dicts (§2.2 last block):

| # | File:Line | Fix |
|---|---|---|
| **CID-10** | `logos/engine/__init__.py:448` | Add `"condition_id": read_research_marker() or "none"` to the `rule.matched` payload dict. |
| **CID-11** | `logos/engine/__init__.py:584` | Same for `action.executed` payload. |
| **CID-12** | `agents/reverie/mixer.py:206,352` | Same for reverie satellite rebuild events. |

**Effort:** 3 lines, ~15 minutes.

**Priority:** lower than Ring 1 (chronicle is for 12-hour
real-time dashboards, not long-horizon research analysis).

### 4.4 Ring 3 architectural suggestion

Instead of threading `condition_id` through every callsite
manually, introduce a **process-wide default** that gets
injected by a wrapper around `shared/telemetry.py::hapax_trace`
and `agents/_telemetry.py::hapax_trace` at the module level.
Specifically:

```python
# In shared/telemetry.py near the top:
def _default_condition_id_metadata() -> dict[str, str]:
    from shared.research_marker import read_research_marker
    cid = read_research_marker()
    return {"condition_id": cid} if cid else {}

# In hapax_trace and hapax_span, merge _default_condition_id_metadata()
# into the metadata dict BEFORE passing to propagate_attributes:
merged_metadata = {**_default_condition_id_metadata(), **(metadata or {})}
```

This makes every root-level trace automatically carry condition_id
without the per-callsite edit. **But** it couples
`shared/telemetry.py` to `shared/research_marker.py`, which
inverts the current dependency direction (research_marker
documents its consumers in its own docstring — this would
change the mental model).

**Recommendation:** do **not** ship Ring 3 unless Phase B's
operator explicitly wants it. Ring 1's per-callsite edits are
more auditable and don't change the shared telemetry module's
contract. Ring 3 is a refactor that should be an explicit
design decision, not a side effect of closing this gap.

## 5. Shared pattern: one helper, one precedent

All of the proposed edits follow the exact same pattern the
compositor already uses in `director_loop.py:646`:

```python
_condition_id = _read_research_marker() or "none"
```

In Phase 4, that inline helper migrates to
`shared.research_marker.read_research_marker()` and is re-used
by both the compositor and the voice pipeline (per beta's
docstring at `shared/research_marker.py:16-31`).

The engine-side remediation would be a **third consumer** of
the same helper. Beta's design explicitly enumerates the three
consumers in the module docstring:

> Consumers who stamp telemetry with the active condition_id:
> - `agents/studio_compositor/director_loop.py` — livestream director
>   reactions are stamped with `condition_id` on every JSONL + Qdrant +
>   Langfuse write (LRR Phase 1 shipped this path via an inlined helper).
> - `agents/hapax_daimonion/conversation_pipeline.py` — voice pipeline
>   grounding DVs (LRR Phase 4 scope item 1 adds this path).
> - `agents/hapax_daimonion/grounding_evaluator.py` — grounding DV
>   scorers called from `conversation_pipeline` (same LRR Phase 4 scope
>   item — one DEVIATION covers the frozen-file edit).

**Proposed amendment to beta's docstring** (for the Phase B
follow-up, not to interrupt beta's in-flight work):

> - `logos/engine/*` — reactive engine events (presence, consent,
>   biometric, rule matches, action executions) need condition_id
>   tagging so that confounder analysis can slice engine events
>   by condition alongside voice grounding DVs. Added in Phase B
>   item N.

## 6. Cross-reference for beta's audit trajectory

- **Pass-N (future) observation:** this drop surfaces a
  research-validity observation that is orthogonal to beta's
  pass-1 through pass-5 audits. Beta's passes focused on
  Phase 4 correctness; this drop focuses on Phase 4 scope
  sufficiency for the A-vs-A' comparison.
- **Graduation status:** new OBS-class finding (not a CRIT or
  HIGH), tracked under Phase B engineering candidates.
- **No conflict with beta's Phase 4 bootstrap work.** The
  engine-side remediation is strictly Phase 4.5+ work and
  depends on beta's commits landing first.
- **Beta's Phase 4 spec (§7 "open questions for operator
  review"):** consider adding an item 7: "Phase B scope —
  engine-side condition_id tagging for confounder analysis
  completeness. Shipping this before Phase 5 execution is
  strongly desirable for the A-vs-A' comparison; shipping
  it after Phase 5 forces time-range joins in the primary
  substrate comparison analysis."

## 7. Open verifications (not blocking this drop)

1. **Context propagation across `await self._executor.execute(
   plan)`**: does the engine's `hapax_trace("engine", "event")`
   propagate_attributes context reach `rules_phase0.py`
   handlers? Verify by opening a test condition and triggering
   a presence transition while logos-api is running, then
   querying Langfuse for the `presence.operator_away` event's
   metadata.

2. **Context propagation across `asyncio.to_thread`**: same
   test but for `_handle_consent_transition` which calls
   `send_notification` via `asyncio.to_thread`. Expected to
   **lose** context.

3. **`conversation_pipeline.py:1706`** (`tts_synth`): is this
   called inside the utterance trace? The code flow is
   `_process_utterance_inner → _stream_speech → _speak_sentence →
   hapax_event("voice", "tts_synth")`. If the utterance trace
   has already been `.__exit__()`-ed by the time TTS completes
   (speech is fire-and-forget after the LLM response), then
   `tts_synth` events may **not** carry condition_id. Needs
   verification; potential Phase 4 gap that beta should know
   about.

4. **`conversation_pipeline.py:1867`** (unclear from grep):
   needs file read to confirm whether it's inside or outside
   the utterance trace.

**These verifications are cheap to run once Phase 4 lands.**
They would convert §4.2's "likely does not inherit" hypotheses
into concrete empirical findings, which would refine the
CID-5 through CID-9 edit list.

## 8. Recommendation summary

**Phase 4 voice-pipeline scope is sufficient for the DVs.** Ship
it unchanged (beta's bootstrap commits).

**Phase B should include engine-side condition_id tagging** via
the CID-1 through CID-9 edit list. ~30 lines across 5 files,
~1.5 hours of Ring 1 work, blocked only by Phase 4 landing.

**Priority for Phase B:** moderate. The analyst can work around
the gap via time-range joins for Phase A baseline collection,
but the A-vs-A' comparison analysis would be materially cleaner
with engine-side condition_id tagging. Ship before Phase 5
execution if the 1.5 hours can be fit into the Phase 4.5 /
Phase B bootstrap window.

**Do not ship Ring 3 (process-wide default metadata injection)**
unless the operator explicitly requests it. The refactor is
tempting but changes the shared telemetry module's contract and
the research_marker consumer enumeration, neither of which
should be a side effect of closing this gap.

**Delta is not shipping any of these edits this session.** Beta
owns the Phase 4 bootstrap workstream, and the Phase B follow-up
is naturally alpha's or a future delta's lane once Phase 4
lands. This drop is research-only.

## 9. Cross-references

- Phase 4 spec: `docs/superpowers/specs/2026-04-14-lrr-phase-4-phase-a-completion-design.md` (in beta's worktree pending commit)
- LRR epic spec: `docs/superpowers/specs/2026-04-14-livestream-research-ready-epic-design.md`
- Phase 1 research registry spec: `docs/superpowers/specs/2026-04-14-lrr-phase-1-research-registry-design.md`
- Phase 2 archive-research-instrument spec: `docs/superpowers/specs/2026-04-14-lrr-phase-2-archive-research-instrument-design.md`
- `shared/research_marker.py`: beta's pre-staged module (in `hapax-council--beta/shared/research_marker.py`, commit `3d9be7da9`)
- `shared/telemetry.py`: canonical hapax_span/event/trace/score wrappers
- `agents/_telemetry.py`: daimonion-scoped variant (same API)
- `logos/_telemetry.py`: logos-engine-scoped variant (same API)
- `.venv/lib/python3.12/site-packages/langfuse/_client/propagation.py:75-206`: upstream `propagate_attributes` implementation + docstring
- Drop #41: BT-5 / BT-7 compositor observability
- Drop #48: API-1/API-2 effect-graph mutation bus (noted to also not carry condition_id, out of scope here but same remediation pattern)

## 10. End

**Session status update:** delta has now produced the last
meaningful research drop for this session. The
condition_id coverage audit completes the sequence of research
walks (drops #32-#51 covered cam + effect + OBS + FD leak) by
answering the research-design-level question that complements
beta's engineering-level Phase 4 work: *is Phase 4's scope
sufficient for Phase A research validity, and if not, where is
the gap?* The answer is: **sufficient for the DVs, needs Phase B
extension for confounder attribution completeness.**

**Cumulative session output:** 22 research drops (#32-#53), 2
direct-to-main production fixes (Ring 1 cam-stability via alpha
+ FDL-1 camera_pipeline stop() fix), 3 relay inflections,
3 incident drops (#33, #41, #51), 1 root cause trace + fix
(drop #52 + FDL-1). The compositor is thoroughly audited at
cam, effect, and output layers. The voice pipeline is covered by
beta's Phase 4 work. The engine-side telemetry gap is
documented with a concrete fix list.

**End of drop #53.**

— delta
