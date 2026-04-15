# LRR Execution State Runbook

**Epic:** Livestream Research Ready (LRR)
**Scope:** All 11 phases (0–10)
**Status snapshot:** 2026-04-15
**Author:** alpha (queue #147)
**Refresh cadence:** operator-triggered or when a phase changes state; regeneration script is a proposed follow-up

> **Purpose.** A single document the operator can read in 2 minutes to understand where every phase is, what's shipping next, which decisions are waiting on operator judgment, and what to read next for any specific phase. Replaces parsing 30+ research drops + PR titles.

---

## §0. TL;DR

| Phases shipped or in motion | 8 of 11 (73%) |
|---|---|
| Phases with spec + plan on main | 9 of 11 (82%) |
| Phases still at gap | Phase 6 (no spec, no plan) |
| Current execution focus | Phase 10 stability matrix (§3.1–§3.14 per-section audit complete) |
| Blocking operator decisions | 3 — see §4 |
| Substrate state | Scenario 1 + scenario 2 ratified; scenario 2 execution pivoted to Option C (parallel backend) pending beta verification of scenario 2 Option A v0.0.28 alternative |

Phase 2 is complete (10 PRs shipped + full regression test coverage as of PR #925). Phase 10 is actively executing per-section work. Phase 3 has shipped Hermes-cleanup reconciliation but hardware validation pass-fails are still queued. Phases 4, 5, 7, 8, 9 have spec + plan staged and are time-gated on operator cadence or upstream prerequisites. Phase 0 is closed. Phase 1 is effectively complete (research registry live, items 10d+10e landed). Phase 6 is the one structural gap.

---

## §1. Per-phase status table

| Phase | Title | Status | Spec on main | Plan on main | Last meaningful change | Next execution step | Blockers |
|-------|-------|--------|---|---|---|---|---|
| 0 | Finding Q spike + verification | **closed** | ✓ | ✓ | 2026-04-14, PR #843 items 10d/10e landed upstream | none — phase closed | none |
| 1 | Research registry + condition_id plumbing | **closed (execution items done; integration gap flagged)** | ✓ | ✓ | 2026-04-15 — queue #164 PR #915 flagged a SHM marker hydration gap (55 orphan writes) | apply the proposed manual one-liner (operator) + ship systemd hydration hook (follow-up queue) | none for phase closure; gap documented |
| 2 | Archive + replay as research instrument | **closed (10 PRs + regression gap fills)** | ✓ | ✓ | 2026-04-15 — PR #925 filled top 3 coverage gaps (G4 integration + G2 purge atomicity + G1 stimmung errors) | none — phase closed with 142 tests passing | none |
| 3 | Hardware validation (post-Hermes reframe) | **execution in progress** | ✓ | ✓ | 2026-04-15 — PR #897 (Hermes cleanup) + PR #910 (plan refresh matching cleanup) | run the validation checklist against the Qwen3.5-9B + scenario 2 substrate envelope | operator availability for validation session |
| 4 | Phase A completion + OSF pre-registration | **spec staged; execution time-gated** | ✓ | ✓ | 2026-04-15 — PR #920 alignment patch picks up drop #62 §16+§17 framing | G3 resolution → voice session cadence → mid-collection integrity checks | Sprint 0 G3 gate (Option 1 default), ≥10 voice grounding sessions, OSF filing decision |
| 5 | Substrate scenario 1+2 (swap phase) | **spec staged** | ✓ | ✓ | 2026-04-15 — PR #900 plan under substrate-scenario-1+2 framing | scenario 1: RIFTS baseline run against Qwen3.5-9B. scenario 2: OLMo 3-7B × {SFT, DPO, RLVR} parallel arms | Scenario 2 Option A (v0.0.28 in-place) vs Option C (parallel :5001) decision — see §4.2 |
| 6 | (reserved) | **GAP — no spec, no plan** | ✗ | ✗ | never authored | phase-6 spec authoring session | phase description not yet extracted from epic |
| 7 | Persona spec authoring | **spec staged** | ✓ | ✓ | 2026-04-15 — delta pre-stage extraction | await Phase 4 closure for data-driven persona extraction | Phase 4 Condition A sample size |
| 8 | Content programming via objectives | **spec staged** | ✓ | ✓ | 2026-04-15 — delta pre-stage extraction | await Phase 5 substrate ship for objective-programming experiments | Phase 5 substrate decision |
| 9 | Closed-loop feedback | **spec staged** | ✓ | ✓ | 2026-04-15 — delta pre-stage extraction | await Phase 5 + Phase 7 closure | Phase 5 + Phase 7 upstream |
| 10 | Observability + stability matrix | **execution in progress** | — (lives in runbook) | — (runbook + per-section audit) | 2026-04-15 — PR #918 per-section status audit (§3.1–§3.14) | order per audit: §3.3 pins → §3.2 dashboards → §3.6 T3 caching → §3.12 exporters → §3.8+§3.9 audit trails | none (can execute in parallel with other phases) |

### §1.1. Legend

- **closed** — phase met its exit criteria; handoff filed; no new work expected under this phase number
- **execution in progress** — spec + plan + some PRs shipped; exit criteria not yet fully met
- **spec staged** — spec + plan on main but execution depends on upstream phase(s) or operator session cadence
- **GAP** — phase number claimed by the epic but no spec/plan authored yet

---

## §2. Substrate scenario 1 + 2 progress

**Canonical framing lives in:** `docs/research/2026-04-14-cross-epic-fold-in-lrr-hsea.md` §14 → §16 → §17 → §18.

### §2.1. Scenario 1 — Qwen3.5-9B + RIFTS baseline

| Aspect | Value |
|---|---|
| Model | Qwen3.5-9B EXL3 5.00bpw |
| Runtime | TabbyAPI :5000 (current production backend) |
| Dataset | RIFTS (beta owns download + preparation) |
| Phase touching | Phase 5 (baseline run); beta queue #210 active |
| Dependencies | None — runs on existing hardware + existing TabbyAPI process |
| ETA | gated on beta RIFTS dataset preparation + Phase 3 hardware validation closure |
| Blockers | beta #210 in progress |

### §2.2. Scenario 2 — OLMo 3-7B × {SFT, DPO, RLVR} parallel arms

| Aspect | Value |
|---|---|
| Model variants | OLMo 3-7B Hybrid in three variants: SFT, DPO, RLVR |
| Runtime (as ratified §16) | originally in-place TabbyAPI :5000 |
| Runtime (as pivoted §17) | parallel TabbyAPI :5001 — **Option C** |
| Dataset | OLMo weights (beta queue #211) + LiteLLM routing to :5001 (beta queue #212) |
| Dependencies | exllamav3 0.0.24+ (for `OlmoHybridForCausalLM`) |
| Blockers | beta #209 reported that exllamav3 0.0.29 upgrade breaks the pinned cu12 stack; Option C was adopted as the fallback |

**Active open question** (see §4.2): can scenario 2 return to Option A (in-place upgrade to v0.0.28) instead of Option C (parallel backend)? Queue #171 (PR #919) showed that v0.0.28 has OlmoHybrid support + the same torch>=2.6.0 pin + no xformers dep. Beta verification of this claim against the actual pinned cu12 stack is the unblocker.

### §2.3. Cross-phase impact

Scenario 1 closure unblocks Phase 5a (Condition A' swap execution). Scenario 2 closure unblocks Phase 5b (multi-arm comparison). Phase 4 is **substrate-independent on the Condition A side** (Condition A stays Qwen3.5-9B regardless) and can proceed in parallel with substrate ship.

---

## §3. Queue item cross-reference (which items are advancing which phase)

### §3.1. Currently in_progress (alpha)

| Queue | Title | Advances |
|---|---|---|
| #147 | LRR execution state runbook | meta (this document) |

### §3.2. Currently offered (alpha-pullable, low/normal priority)

| Queue | Title | Advances | Size |
|---|---|---|---|
| #160 | LRR + HSEA consolidated rollup | meta (depends on #147) | ~400 lines markdown |
| #178 | Prometheus + Grafana dashboards catalog | Phase 10 §3.2 | ~150 lines bulk catalog |

### §3.3. Currently offered (beta-only)

| Queue | Title | Advances |
|---|---|---|
| #209 | exllamav3 0.0.29 upgrade attempt (blocked, superseded by #171 finding) | Scenario 2 substrate |
| #210 | RIFTS dataset download + Qwen3.5-9B baseline | Scenario 1 |
| #211 | OLMo parallel TabbyAPI :5001 deploy (Option C) | Scenario 2 |
| #212 | OLMo LiteLLM routes + claim-shaikh cycle 2 run | Scenario 2 ship |
| #225 | CPAL loop telemetry integration | Phase 9 prep |

### §3.4. Recently closed (this multi-session push)

See §5 for the last-20 PR activity log. Notable closures directly advancing LRR:
- #170 → PR #918 (Phase 10 per-section status audit — 14 §3.N items)
- #164 → PR #915 (Phase 1 Qdrant integration check — SHM marker gap surfaced)
- #146 → PR #925 (Phase 2 regression test gap fills — top 3 from #117 audit)
- #157 → PR #910 (Phase 3 plan refresh matching #139 Hermes cleanup)
- #143 → PR #900 (Phase 5 plan under scenario 1+2 framing)
- #177 → PR #920 (Phase 4 spec+plan alignment patch post §16/§17)

---

## §4. Operator-gated decisions

Items that cannot advance without an operator judgment call. Listed in order of blocking severity.

### §4.1. Scenario 2 Option A vs Option C — decision triggered by PR #919

**Context:** Queue #171 research drop (PR #919) found that exllamav3 v0.0.28 has OlmoHybrid support (inherited from v0.0.26) + the same `torch>=2.6.0` pin + NO new xformers dep vs v0.0.23 baseline. This means scenario 2 Option A (in-place upgrade to v0.0.28) is potentially viable without the incompatibility that triggered the v0.0.29 → Option C pivot in drop #62 §17.

**Decision needed:** schedule a 15-minute beta verification — reproduce the #209 pip resolver trace on v0.0.29, then attempt `pip install exllamav3==0.0.28` against TabbyAPI's pinned torch. If clean, scenario 2 moves from Option C to Option A; queue #211 + #212 become simpler (in-place deployment on :5000 instead of parallel :5001).

**Who decides:** operator (to allocate a beta session to verification) + beta (to run the trace).

**What changes on each outcome:**
- Option A confirmed → retire Option C queue items, rewrite #211 + #212 for in-place
- Option A refuted → continue Option C as the shipping path; queue #919 becomes documentation for a future upstream upgrade

### §4.2. FINDING-S default-ship deadline 2026-04-22

**Context:** Phase 2 spec §Retention includes a finding (FINDING-S) with a `default-ship` date of 2026-04-22 — after which the finding auto-merges into the production retention policy without further operator review.

**Decision needed:** operator explicit sign-off OR explicit defer decision before 2026-04-22. Default action if no decision: ship.

**Status:** 7 calendar days from audit snapshot (2026-04-15 → 2026-04-22).

### §4.3. OSF pre-registration filing (Phase 4 item 3.4)

**Context:** Phase 4 spec §3.4 requires an operator-physical action — create an OSF project for `claim-shaikh-sft-vs-dpo`, upload the pre-registration document, and record the URL in the condition registry. This is a **one-way step**: once filed, the pre-registration is public.

**Decision needed:** operator sign-off on the pre-registration document content + execution of the OSF upload.

**Blocked on:** Phase 4 collection reaching ≥10 voice grounding sessions under Qwen3.5-9B with `cond-phase-a-baseline-qwen-001` tagging. Session cadence is time-gated by operator availability.

### §4.4. Phase 6 spec authoring

**Context:** Phase 6 is claimed in the epic's phase list but has no spec or plan on main. This is a pure authoring gap, not a decision gate, but it needs an operator triage step: should Phase 6 be authored now (to unblock ordering) or explicitly marked as "post-Phase 5 retrograde authoring"?

**Decision needed:** operator decides when to schedule the Phase 6 spec extraction session.

---

## §5. Recent PR activity (last 10 PRs touching LRR)

| PR | Commit | Queue | Phase | Title |
|---|---|---|---|---|
| #925 | e93bba955 | #146 | Phase 2 | test(lrr-phase-2): fill top 3 regression gaps from #117 audit |
| #920 | cabec58eb | #177 | Phase 4 | docs(lrr-phase-4): spec+plan alignment patch post-§16/§17 |
| #918 | a86dbd117 | #170 | Phase 10 | docs(research): LRR Phase 10 per-section status audit |
| #915 | 0918f6f2b | #164 | Phase 1 | docs(research): LRR Phase 1 Qdrant integration check |
| #912 | db7d43527 | #156 | epic | docs(drop-62): §18 draft — forward-looking post-scenario-1+2 ship |
| #910 | 4a22833d0 | #157 | Phase 3 | docs(lrr-phase-3): plan refresh matching #139 Hermes cleanup |
| #909 | a439a4a61 | #153 | Phase 10 | docs(research): LRR Phase 10 §3.3 CI pin integration check |
| #908 | 8d86afd58 | #154 | epic | docs(lrr-epic): Phase 5 cross-reference amendment to substrate scenario 1+2 spec |
| #900 | 2735c8800 | #143 | Phase 5 | docs(lrr-phase-5): plan under substrate scenario 1+2 framing |
| #897 | a5ee4ce4f | #139 | Phase 3 | docs(lrr-phase-3): Hermes reference cleanup — partition work preserved, substrate framing updated |

Full log: `git log --oneline origin/main --grep='lrr-phase' -20`.

---

## §6. What to read next

Pointed to the minimum reading path for catching up from cold on each phase.

| I want to catch up on... | Read this first | Then this |
|---|---|---|
| The big picture | `docs/research/2026-04-14-cross-epic-fold-in-lrr-hsea.md` §0 ToC | Epic spec: `docs/superpowers/specs/2026-04-14-livestream-research-ready-epic-design.md` |
| Substrate state | Drop #62 §14 → §16 → §17 → §18 | Queue #171 PR #919 v0.0.28 matrix |
| Phase 2 (archive) | `docs/superpowers/specs/2026-04-15-lrr-phase-2-archive-research-instrument-design.md` | `docs/research/2026-04-15-lrr-phase-2-test-coverage-audit.md` (post-ship coverage verdict) |
| Phase 3 (hardware validation) | `docs/superpowers/specs/2026-04-15-lrr-phase-3-hardware-validation-design.md` | `docs/superpowers/plans/2026-04-15-lrr-phase-3-hardware-validation-plan.md` |
| Phase 4 (Phase A completion) | `docs/superpowers/specs/2026-04-15-lrr-phase-4-phase-a-completion-osf-design.md` | drop #62 §16 note in the spec (T22:45Z update from queue #177) |
| Phase 5 (substrate swap) | `docs/superpowers/specs/2026-04-15-lrr-phase-5-substrate-scenario-1-2-design.md` | queue #171 PR #919 for the Option A/C decision context |
| Phase 10 (stability matrix) | `docs/superpowers/runbooks/lrr-phase-10-stability-matrix.md` | Per-section audit: `docs/research/2026-04-15-lrr-phase-10-per-section-audit.md` |
| Queue + protocol state | `~/.cache/hapax/relay/queue/*.yaml` (active items) + `~/.cache/hapax/relay/queue/done/2026-04-15/` (closed items) | `~/.cache/hapax/relay/alpha.yaml` / `beta.yaml` (session status) |
| Governance context | `axioms/registry.yaml` | `axioms/implications/*.yaml` + `axioms/precedents/sp-hsea-mg-001.yaml` |

---

## §7. Refresh mechanics

This runbook is **manually regenerated** on meaningful state changes, not on a timer. Triggers that should prompt a regeneration:

1. A phase changes status (closed → execution, execution → staged, etc.)
2. A substrate scenario pivots
3. An operator-gated decision is resolved
4. A new blocker is discovered
5. The last-10-PRs list is more than ~5 PRs stale

A scripted regenerator is a **proposed follow-up**: `scripts/render-lrr-runbook.py` that pulls phase status from queue state + `git log` + a phase-catalog YAML. Out of scope for queue #147 (which is the first-version authoring pass).

---

## §8. Cross-references

- Epic spec: `docs/superpowers/specs/2026-04-14-livestream-research-ready-epic-design.md`
- Epic plan: `docs/superpowers/plans/2026-04-14-livestream-research-ready-epic-plan.md`
- Cross-epic fold-in: `docs/research/2026-04-14-cross-epic-fold-in-lrr-hsea.md`
- Phase 10 stability matrix runbook: `docs/superpowers/runbooks/lrr-phase-10-stability-matrix.md`
- Phase 2 operator activation runbook: `docs/superpowers/runbooks/2026-04-15-lrr-phase-2-operator-activation.md`
- Queue #147 (this item)
- Queue #160 (depends on this — broader LRR + HSEA rollup)

---

## §9. Verdict

LRR is ~73% phase-progressed (8 of 11 in motion or closed). Two phases (0 + 2) are fully closed with exit criteria met. Phase 10 is actively executing and has a dedicated runbook. The primary unblocker on the epic is the **scenario 2 Option A vs Option C decision** — pending a 15-minute beta verification — which cascades into queue #211 + #212 scoping. The primary structural gap is **Phase 6**, which needs an authoring session to even enter the queue. The primary time-gated bottleneck is **Phase 4**'s ≥10 voice grounding sessions under operator cadence.

No immediate execution blockers beyond those above. The epic is in a healthy shippable state.

— alpha, queue #147
