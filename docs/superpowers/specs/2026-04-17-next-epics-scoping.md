# Next-Epics Scoping — 2026-04-17

**Date:** 2026-04-17 (immediately post-LRR closure)
**Purpose:** operator-facing map of what's out there beyond LRR. Not a
work order — a survey so the operator can decide what opens next.

---

## 1. Bayesian Validation R&D schedule

**Status:** **DE FACTO CLOSED / SUPERSEDED.**

The 21-day schedule started on 2026-03-30 (Day 1). Today is Day 19.
Sprint 0 (Days 1–2) completed; Sprints 1–3 (Days 3–21) never started.
The LRR epic took priority and ran concurrently through 2026-04-17.

**Measures:** 27 total. Complete: 5 (4.1 PASS, 8.1, 3.2 test harness,
3.3 test harness, 7.2 deferred). Not started: 22.

**Gates:** G1 PASS (DMN hallucination 0% contradictions). G2 DEFERRED
(blocked on DEVIATION-025, activity-classifier starvation, and
activation_score telemetry absence). G3–G7 not evaluated.

**Blockers named in the schedule doc:**
1. DEVIATION-025 needs filing to unblock measure 7.1 (salience signal
   logging to `conversation_pipeline.py`). Cascades to measure 7.2.
2. `production_activity` classifier returns `idle` always; measure 3.2
   protention validation cannot run.
3. No `activation_score` in Langfuse traces; measure 7.2 requires
   N ≥ 50 with both `activation_score` + `context_anchor_success`.

**Recommendation:** formally close this schedule with a one-line
deprecation note in its spec. The live research instrument is now
LRR Phase A (`cond-phase-a-persona-doc-qwen-001`). If specific
Bayesian measures still matter, fold them into the Continuous-Loop
epic's validation drill (§3.7 of that spec) rather than reviving a
parallel schedule. LRR's per-condition Prometheus slicing already
covers the measurement layer; the Bayesian schedule added nothing
LRR doesn't now cover.

---

## 2. Tool capability model / queue #015

**Status:** **DEFERRED WITH CLEAR UNBLOCK CRITERIA.**

Model state: 31 tools registered in `agents/hapax_daimonion/
tool_affordances.py` (26 core + 5 phone). `ToolCapability` dataclass,
`ToolRegistry` for dynamic availability filtering, and
`ToolRecruitmentGate` bridging utterances to the AffordancePipeline
all operational. Degradation rules fire on critical/degraded stimmung,
backend unavailability, missing consent, working-mode restriction.

Queue #015 is "Full Tool Recruitment" — replace the current LLM
function-calling menu selection with semantic affordance-pipeline
recruitment. The scoring formula is already defined
(0.50·similarity + 0.20·base_level + 0.10·context_boost + 0.20·thompson
per CLAUDE.md §Unified Semantic Recruitment). The bridge code is in
`ToolRecruitmentGate`. What's missing is the flip that makes the
pipeline the sole tool-selection path rather than a parallel one.

**Deferral reason** (documented at `tool_capability.py:6` + the
unified-semantic-recruitment spec §3.0.1): recruitment quality
depends on reliable Thompson-learning signals. The deferral is
explicitly "until validation sprint telemetry demonstrates Thompson
has converged."

**Unblock criteria:**
- Success rate on recruited tools ≥ 75% over ≥ 50 tool invocations.
- Hebbian association confidence mature (no concrete metric given,
  but memory + spec imply "stops shifting on each update").
- No other technical blockers — registration, gating, degradation,
  Gibson-verb descriptions are all complete.

**Recommendation:** treat this as **USR Phase 3.5** (between the
shipped tool-recruitment gate and the open Phase 4 destination
recruitment). Wait for the Phase A MCMC window to produce the
Thompson-convergence data. Current session count: 2 of ≥ 8 target;
next trigger ≈ 2026-05-10. At that point the deferral unblocks
naturally.

---

## 3. Cross-repo backlogs (officium / mcp / watch / phone)

**Status:** **NO ACTIONABLE BACKLOG** across all four repos.

| Repo | Role | Active workstream | Open manual PRs |
|---|---|---|---|
| hapax-officium | Management decision support, :8050 | `working_mode` architecture migration; audit-followups branch | 0 (14 dependabot) |
| hapax-mcp | MCP server (36 tools) | `chronicle` + `working_mode` tool completion, recent cycle_mode→working_mode harmonization | 0 (8 dependabot) |
| hapax-watch | Wear OS biometrics | Documentation cleanup; last real feature Feb 2026 | 0 (9 dependabot) |
| hapax-phone | Android Health Connect companion | Stable post-bootstrap; last feature 2026-04-15 fallback port fix | 0 |

None of the four has a visible manual backlog, a stalled branch, or
a roadmap doc declaring next work. All open PRs are automated
dependency bumps. The design of the phone + watch companions appears
feature-complete for their v1 scope.

**Recommendation:** no cross-repo epic opens here. If the operator
wants to evolve any of these, that's a directed ask, not a latent
backlog waiting to be worked. The one area that might benefit from
review is the **14 dependabot PRs in officium** — bulk-merging the
safe ones would close a minor housekeeping gap.

---

## 4. SCM Formalization next phase

**Status:** **SPEC COMPLETE; MEASUREMENT→ACTION LOOP UNCLOSED.**

Spec + 14 control laws + sheaf/eigenform/topology metrics all shipped.
All 6 properties formalized. However: the metrics are computed and
stored but do not feed back into runtime behavior. Eigenform is
currently pinned at a fixed point (all-zeros), which is either a
pathological steady-state or a wiring artifact.

The agent's full scoping report identified 7 ranked next items (P1–P7)
and 5 operator questions. Summary:

**P1 — Unblock `grounding_quality` freshness** (small, 1–2 h). 121 s
stale; writer is unknown. First live utterance will disambiguate.

**P2 — Wire eigenform state vector to real sources** (medium, 4–8 h).
Presence, activity, heart_rate, operator_stress all have real sources
(PresenceEngine, contact mic, Pixel Watch, stimmung) but the VLA
writer reports zeros. Wiring disconnect.

**P3 — Expose SCM metrics on Prometheus** (medium, 2–3 h). Currently
`/dev/shm` only; not in Grafana.

**P4 — Eigenform velocity gauge** (small, 1–2 h). `||x_t − x_{t-1}||_2`
per tick. Detects fixed-point stalls automatically.

**P5 — Control-law feedback into visual response** (medium, ~1 week).
Reverie mixer reads degradation counts, modulates shader intensity.

**P6 — Stress-test live operator interaction** (small, 30 min).
One utterance validates the whole pipeline.

**P7 — Formalize observer-system circularity** (large, 3–4 weeks).
Theoretical; 4 formalism candidates identified.

**Operator questions** (summarized):
- Q1 Prometheus coverage policy (all metrics or actionable only?).
- Q2 System-wide degradation budget before operator notification?
- Q3 Is the current fixed-point eigenform a measurement artifact or
  correct idle-state?
- Q4 Consent-propagation upper bound (technical + ethical)?
- Q5 Multi-SCM composition (hypothetical officium SCM)?

**Recommendation:** **OPEN AS "SCM Phase 2: Observability & Feedback"**
if the operator wants the eigenform to reflect live activity and the
metrics to drive behaviour. Otherwise **HOLD** — the spec is final
and the system operates fine; this is about converting
instrumentation into a control layer.

**Scoping artefact:** `docs/research/2026-04-13/round4-forward-looking/
phase-4-scm-metrics-state.md` already contains the ranked P1–P7
candidates; promoting to an epic spec would take 1 session's work.

---

## 5. Unified Semantic Recruitment next phase

**Status:** **READY AS NEXT EPIC. PHASE 4 IN-FLIGHT.**

Phases 1–3 shipped (imagination purification, content recruitment,
tool recruitment). Phase 4 (destination recruitment) is partial —
medium fields exist, multi-modal dispatch not yet centralised. Phases
5 (novel discovery) and 6 (cleanup) not started.

**Phase 4 completion items:**
1. Unify `ExpressionCoordinator` to a single `pipeline.select()` call
   across all modalities (3–4 h).
2. Enrich expression capability descriptions with medium-specific
   affordance adjectives (2 h).
3. Multi-modal suppression calibration (1 h).

**Phase 5 novel discovery items:**
4. Register `capability_discovery` affordance with three
   sub-affordances (search, scan_local, acquire) (1 h).
5. Wire exploration tracker's empty-selection signal to the discovery
   handler (2 h).
6. Implement `DiscoveryResolver` — web search + structured findings +
   consent-gated acquisition (~4 h).

**Phase 6 cleanup items:**
7. Remove `can_resolve()` methods on 6 classes (3 h).
8. Remove dead `CapabilityRegistry.broadcast()` method (30 min).

**Operator questions:**
- Q1 Thompson sampling on discovery outcomes: record for discovery
  affordance, or only for the acquired tool? (Recommendation:
  discovery; new tool starts cold.)
- Q2 Discovery consent flow: async search vs interactive present-
  findings?
- Q3 Discovery exploration-budget priority.
- Q4 Multi-modal slot allocation under suppression.

**Recommendation:** **READY AS NEXT EPIC.** Estimated ~22 hours
serial (Phase 4: 10 h, Phase 5: 8 h, Phase 6: 4 h). Phase 4 has the
most carry-over value for the Continuous-Loop epic (unified dispatch
simplifies the captions + attention-bid + environmental-emphasis
integrations).

Main risk: Phase 5 discovery resolver is new code with no precedent;
UX question (Q2) should be answered before starting Phase 5.

---

## 6. Recommendation matrix

| Epic candidate | Ready now? | Blockers | Opens after |
|---|---|---|---|
| **Continuous-Loop Research Cadence** | ✅ YES | none | ratification |
| **USR Phase 4 + 5 + 6** | ✅ YES | Q2 UX decision for Phase 5 | ratification + Q2 answer |
| **SCM Phase 2: Observability & Feedback** | ✅ YES (but optional) | Q1–Q5 operator decisions | ratification + Q1 answer |
| **Bayesian Validation revival** | ❌ NO | superseded by LRR Phase A | close with deprecation note |
| **Tool Recruitment (queue #015)** | ⏳ data-gated | Thompson-convergence telemetry from Phase A | ≈ 2026-05-10 |
| **Cross-repo (officium/mcp/watch/phone)** | ❌ no backlog | n/a | operator-directed ask only |

Three live candidates (Continuous-Loop, USR 4+5+6, SCM Phase 2). Each
has its own spec draft either in flight or referenced above. The
operator picks the order.

**My default sequencing** if asked:
1. Continuous-Loop first (shortest path to proving LRR's Phase 9 modules actually close the loop)
2. USR Phase 4 in parallel (small, cleans up dispatch path used by Continuous-Loop §3.4 + §3.5)
3. USR Phase 5 + 6 + SCM Phase 2 as the operator prioritises

---

## 7. Artefact pointers

- Continuous-Loop epic spec: `docs/superpowers/specs/2026-04-17-continuous-loop-research-cadence-design.md`
- LRR closure handoff: `docs/superpowers/handoff/2026-04-17-lrr-epic-closure.md`
- USR main spec: `docs/superpowers/specs/2026-04-02-unified-semantic-recruitment-design.md`
- SCM main spec: `docs/research/stigmergic-cognitive-mesh.md`
- SCM Phase 4 metrics state: `docs/research/2026-04-13/round4-forward-looking/phase-4-scm-metrics-state.md`
- Voice grounding RESEARCH-STATE: `agents/hapax_daimonion/proofs/RESEARCH-STATE.md` (last refreshed this session)
