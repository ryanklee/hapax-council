# HSEA Phase 11 — Multi-Agent Spawner (Cluster G) — Design Spec

**Date:** 2026-04-15
**Author:** delta (pre-staging extraction)
**Status:** DRAFT pre-staging — awaiting UP-13 opening
**Epic reference:** `docs/superpowers/specs/2026-04-14-hsea-epic-design.md` §5 Phase 11 + drop #58 §3 Cluster G
**Plan reference:** `docs/superpowers/plans/2026-04-15-hsea-phase-11-multi-agent-spawner-plan.md`
**Branch target:** `feat/hsea-phase-11-multi-agent-spawner`
**Cross-epic authority:** drop #62 §5 UP-13
**Unified phase mapping:** UP-13 sibling — ~2,400 LOC across 11 G-deliverables

---

## 1. Phase goal

Ship the **G-series spawning infrastructure** — Hapax as a spawn-manager of sub-agents that execute bounded research questions, analysis tasks, anomaly investigations, and emergency responses. Every spawn gates through `shared/spawn_budget.py` (HSEA Phase 0 0.3) to prevent runaway LLM cost.

**Key constraint:** spawns are budget-capped per touch point. No spawn without `SpawnBudgetLedger.check_can_spawn()` allowance. `budget_exhausted` impingement on exhaustion.

**Substrate-sensitive:** spawns produce findings that get composed into research drops via `ComposeDropActivity`. Substrate must handle the compose synthesis well. Per drop #62 §14, post-Hermes substrate quality gate applies.

---

## 2. Dependencies + preconditions

1. HSEA UP-2 closed (spawn budget + governance queue)
2. HSEA UP-10 closed (ComposeDropActivity + patch activity)
3. LRR UP-9 closed (persona for spawn prompt assembly)
4. LRR Phase 5a closed with operator-ratified substrate
5. `hsea_spawn_heartbeat()` helper from HSEA Phase 1 1.4 Live orchestration strip

---

## 3. Deliverables (11 G-items)

### 3.1 G1 — `research_question` affordance via AffordancePipeline

- New affordance registered in the `AffordancePipeline`: "spawn a sub-agent to research question X"
- When recruited, spawns a sub-agent with a bounded research question, budget cap, wall-time cap
- Spawn ID + findings go to `/dev/shm/hapax-orchestration/active.jsonl` (HSEA Phase 1 1.4)
- **Target files:** `agents/affordances/research_question_affordance.py` (~200 LOC), registered in Qdrant `affordances` collection
- **Size:** ~260 LOC

### 3.2 G2 — Weekly self-analysis ritual (Sunday 04:00)

- Weekly systemd timer spawns a sub-agent that reviews the past week's Hapax state + produces a "self-analysis drop"
- Analysis includes: PRs shipped, drops authored, activities selected, stimmung trajectory, notable events
- **Target files:** `agents/hapax_daimonion/g_cluster/g2_self_analysis_ritual.py` (~300 LOC), timer unit
- **Size:** ~360 LOC

### 3.3 G4 — Drop draft from sub-agent consensus

- When 3+ sub-agents independently converge on a finding, a drop draft is auto-composed from the consensus
- Uses `ComposeDropActivity` with a findings_reader that queries `/dev/shm/hapax-orchestration/findings-*.jsonl`
- **Target files:** `agents/hapax_daimonion/g_cluster/g4_consensus_drop_composer.py` (~250 LOC)
- **Size:** ~310 LOC

### 3.4 G5 — Tactical re-evaluation on 30-day clock

- Every 30 days, a sub-agent spawns to re-evaluate drop #57 tactics + drop #58 Cluster proposals against the current research state
- Output: a "tactical update" drop noting which tactics have landed, which are stale, which need reframing
- **Target files:** `agents/hapax_daimonion/g_cluster/g5_tactical_reevaluation.py` (~280 LOC), monthly timer
- **Size:** ~340 LOC

### 3.5 G6 — Voice session parallel scoring

- During a voice grounding session, a parallel sub-agent scores each utterance against grounding criteria (Clark & Brennan repair sequences, etc.)
- Scores stream to `~/hapax-state/voice-session-scores.jsonl` for post-hoc analysis
- Consumes `ConsentGatedWriter` from LRR Phase 6 for Qdrant writes
- **Target files:** `agents/hapax_daimonion/g_cluster/g6_voice_session_scorer.py` (~300 LOC)
- **Size:** ~380 LOC

### 3.6 G7 — Anomaly analyst spawn

- On anomaly detection (stimmung critical + compositor failure + health monitor alert), spawn a sub-agent tasked with "what broke and why"
- Sub-agent reads recent journal + git log + CI state + compositor metrics
- Produces an incident analysis drop (not operator-delivered; surfaced in governance queue)
- **Target files:** `agents/hapax_daimonion/g_cluster/g7_anomaly_analyst.py` (~300 LOC)
- **Size:** ~380 LOC

### 3.7 G8 — Constitutional decision proxy

- When a decision would require axiom-level precedent (e.g., new deviation, new consent contract), a sub-agent is spawned to propose the precedent text + rationale
- Operator reviews via governance queue
- **Target files:** `agents/hapax_daimonion/g_cluster/g8_constitutional_proxy.py` (~250 LOC)
- **Size:** ~320 LOC

### 3.8 G10 — Long-running research sessions with checkpoints

- Sub-agent can spawn in "long-running" mode (>30 min wall clock) with explicit checkpoints
- At each checkpoint (~10 min intervals), writes partial findings + takes a budget-usage snapshot
- Operator can cancel mid-session via governance queue `status: rejected`
- **Target files:** `agents/hapax_daimonion/g_cluster/g10_long_running_session.py` (~350 LOC)
- **Size:** ~430 LOC

### 3.9 G11 — Live Langfuse telemetry slot

- Cairo source showing live Langfuse span activity for currently-running sub-agents
- Zone: dedicated "spawn telemetry" slot
- Reads Langfuse via `hapax_span` bridge (existing observability)
- **Target files:** `agents/studio_compositor/g11_langfuse_telemetry_source.py` (~200 LOC)
- **Size:** ~260 LOC

### 3.10 G13 — Emergency analyst (Tier-1)

- On Tier-1 incident (e.g., stream down, compositor crash, auth failure), spawn an emergency analyst at highest priority (bypasses daily spawn budget if `emergency_flag` set)
- Operator can set emergency flag via Stream Deck button (LRR Phase 8 item 6)
- Produces an incident report within 5 minutes
- **Target files:** `agents/hapax_daimonion/g_cluster/g13_emergency_analyst.py` (~250 LOC)
- **Size:** ~320 LOC

### 3.11 G14 — Multi-agent consensus demonstration

- Meta: when multiple sub-agents from G1/G4/G7 converge, narrate the consensus on stream as a G-cluster content surface
- "Three parallel analyses agree that X is happening" — visible multi-agent agreement
- **Target files:** `agents/hapax_daimonion/g_cluster/g14_consensus_demo.py` (~200 LOC)
- **Size:** ~260 LOC

---

## 4. Phase-specific decisions

1. **All spawns gate through spawn budget** — no bypass except G13 emergency mode with explicit operator flag
2. **All G-drafters compose `ComposeDropActivity`** from HSEA Phase 2 3.6 for drop composition
3. **G10 checkpoints write to `active.jsonl`** (HSEA Phase 1 1.4 orchestration strip) so heartbeats are visible
4. **G13 emergency bypass requires a Stream Deck button** — not an API flag, to prevent silent emergencies
5. **Substrate-sensitive** — spawn synthesis quality matters; §14 reframing may require disabling G4/G14 consensus demonstrations if substrate can't articulate synthesis

---

## 5. Exit criteria

- All 11 G-deliverables registered + at least one test spawn verified per deliverable
- G1 research_question affordance recruited via `AffordancePipeline.select()`
- G2 weekly ritual fires + produces a self-analysis drop
- G4 consensus trigger tested with 3 synthetic findings
- G7 anomaly analyst fires on a simulated incident
- G13 emergency bypass verified with Stream Deck button
- G11 Langfuse telemetry slot renders live span activity
- All spawns gated through spawn budget (verified via overflow test)
- `hsea-state.yaml::phase_statuses[11].status == closed`

---

## 6. Risks

| Risk | Mitigation |
|---|---|
| Runaway spawn cost | Spawn budget hard-gates; `budget_exhausted` impingement |
| G13 emergency false-fire | Stream Deck button + 5-min cooldown between emergencies |
| G4 consensus based on hallucinated findings | Provenance-backed extraction (cite source sub-agent ids) |
| G10 long-running sessions hang | Wall-time cap + checkpoint cancellation via governance queue |
| G5 tactical re-eval drifts from research state | Bounded scope: read research drops only, not inferred state |

---

## 7. Open questions

1. G2 weekly ritual time (Sunday 04:00 default)
2. G10 wall-time cap default (~30 min)
3. G13 emergency budget bypass magnitude (2x daily cap? unlimited?)
4. G14 consensus threshold (3 agents? 5?)

---

## 8. Plan

`docs/superpowers/plans/2026-04-15-hsea-phase-11-multi-agent-spawner-plan.md`. Execution order: G1 affordance first → G10 long-running checkpoints → G2/G5 timers → G4 consensus → G7 anomaly → G8 constitutional → G11 telemetry → G13 emergency → G14 demo → G6 voice scoring.

---

## 9. End

Pre-staging spec for HSEA Phase 11 Multi-Agent Spawner / Cluster G. 11 G-deliverables with spawn budget enforcement. Substrate-sensitive for compose quality.

Sixteenth complete extraction in delta's pre-staging queue this session.

— delta, 2026-04-15
