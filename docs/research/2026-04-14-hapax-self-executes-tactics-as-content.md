# Hapax executes its own tactics as visible livestream content — architectural synthesis

**Date:** 2026-04-14 CDT
**Author:** delta (research support role)
**Status:** Final synthesis. 7 parallel research agents produced ~80 granular touch points across 7 coherent clusters. This document integrates them into a single architecture.
**Scope:** The operator directed: *"run dedicated research in coherent sets of granular touch points into how all applicable strategies and tactics listed and ALL OTHER such applicable (by applicable I mean possible) strategies and tactics could cleverly be carried out by Hapax itself in the context of the livestream, which, again, should in turn increase self-iteration speed and livestream novelty (especially if Hapax carries out certain functions as part of the livestream itself)."*
**Predecessors:** drops #54 (v1 speculative Bayesian), #55 (v2 grounded), #56 (v3 novelty + platform value), #57 (operator-executes tactical plan). This drop is the final layer: **everything in #57 executed by Hapax itself, visible on stream, under constitutional governance.**

---

## 0. The reframe that changes everything

Drop #57 listed ~38 tactics for the operator to execute. The operator's push-back: most of that work can be done by Hapax, and if Hapax does it **on stream**, the work itself becomes content. This collapses two costs into one:

- **Before:** operator time to execute tactics + stream produces content
- **After:** Hapax executes tactics + the execution IS the content

This is not trivial. It's a load-bearing architectural insight that closes three loops simultaneously:

1. **Self-iteration speedup.** When the work happens on stream, the feedback loop (code → output → critique → improvement) runs in minutes instead of days. Hapax proposes; operator approves in Obsidian; change ships. Ship rate compounds.

2. **Novelty amplification.** Viewers watching Hapax write research drops, audit itself, propose fixes, and run multi-agent analyses in real time are watching something **without direct precedent**. Neuro-sama did reflexive content at the vibe level. Hapax can do it at the infrastructure level — with cited PR numbers, condition_ids, Langfuse trace IDs, and BEST posterior intervals.

3. **Constitutional alignment is natural, not a constraint.** The `management_governance` axiom ("LLMs prepare, humans deliver") is usually treated as a restriction. Under this reframe, it becomes the **content-generating mechanism**: Hapax's visible *preparation* IS the content; the operator's discrete *delivery* IS the governance ritual. What looks like friction becomes a pacing device.

The 7 research agents produced ~80 granular touch points across 7 coherent clusters. This drop integrates them into a single architecture with shared primitives, unified governance, and a critical path.

---

## 1. The shared primitives

All 80 touch points route through a small set of shared infrastructure. Identifying these primitives is more important than enumerating touch points — because once the primitives exist, every individual touch point becomes a ~200 LOC PR.

### 1.1 The prepare/deliver queue

Every touch point that produces a consequential artifact (research drop, PR, fix proposal, OSF amendment, governance decision, code change) writes it to one of two queues:

- **`~/Documents/Personal/00-inbox/`** — Obsidian inbox as primary review surface. Operator opens, reads, edits frontmatter (`status: approved`), then a separate operator-invoked script promotes. This is the **canonical prepare/deliver boundary** across every cluster.
- **`~/hapax-state/governance-queue.jsonl`** — append-only JSONL ledger of pending items with `{title, drafted_at, location, status, approval_path}`. Read by the overlay system to render the queue state.

No Hapax touch point ever auto-commits consequential work. The operator's keystroke is always the release valve.

### 1.2 The overlay system — five visibility channels

Every touch point that makes Hapax's work visible routes through one of five existing primitives:

- **Cairo persistent overlay zones** (`agents/studio_compositor/overlay_zones.py`) — always-on status surfaces (HUD, research state, condition_id, governance queue, meta-meter)
- **Sierpinski content slots** (`agents/studio_compositor/sierpinski_renderer.py`) — rotating content that fills a triangle corner for 30s-3min (drops being drafted, retrospectives, demonstrations, critiques)
- **Director loop activities** (`agents/studio_compositor/director_loop.py::ACTIVITY_CAPABILITIES`) — structured content events (`reflect`, `critique`, `draft`, `patch`, `synthesize`, `compose_drop`, `exemplar_review`, `verification_run`)
- **Daimonion voice narration** (via `hapax_dmn/impingements.jsonl`) — ambient cognition narrated at varying salience (0.4 ambient, 0.55 recovery, 0.6 alert, 0.7 preflight, 0.9 ceremony)
- **Reactor log JSONL** (`~/Documents/Personal/30-areas/legomena-live/reactor-log-*.jsonl`) — persistent record of everything Hapax has done, queryable offline

All five are **existing infrastructure**. No new visibility tier is required — only new producers routing through them.

### 1.3 The shared Prometheus poller

A single `shared/prom_query.py` with `PromQueryClient` (instant + range + watched queries) feeds: HUD, anomaly narrator, alert triage, postmortem drafter, platform value posterior, monthly retrospective. One shared HTTP client, rate-limited polling tiers (0.5/1/2/5 Hz). **Build this once; it unlocks ~15 touch points.**

### 1.4 The budget ledger + kill-switch

A global `~/hapax-state/spawn-budget.jsonl` ledger aggregates LLM spend per touch point per day. A hard daily cap ($5 default) in the reactive engine kills new spawns when exceeded. The existing `mcp__hapax__cost` tool already aggregates LiteLLM spend per model; extend it with per-touch-point attribution. **Without this, the multi-agent spawn touch points are financially dangerous.**

### 1.5 The concrete-artifact anti-slop discipline

Every reflexive, critical, or narrative touch point must cite a **concrete artifact**:
- Reflexive moment → reaction index, timestamp, or condition_id
- Critique → specific bigram or reaction referenced by index
- Architectural narration → PR number or service name
- Research narration → drop filename or condition_id
- Clip-miner decision → specific metric value + threshold
- Self-analysis → specific drop ID or tactic number

**Pure prose reflexivity is rejected.** This single constraint is what separates Hapax's reflexive content from Neuro-sama-style "do you think I'll ever be real" slop. Hapax has literal filesystem access to its own artifacts; its reflexivity is grounded in data, not vibes.

### 1.6 The frozen-files universal hard stop

Every touch point that could commit code or modify prompts runs `scripts/check-frozen-files.py --probe <target>` before staging. Blocks become visible content: overlay badge "proposal blocked by freeze · condition lrr-04".

### 1.7 The constitutional governance queue visualization

`~/hapax-state/governance-queue.jsonl` is rendered as a persistent overlay zone showing: pending items count, oldest age, most recent draft, approval paths. This makes the prepare/deliver boundary **public and visible**. When the queue grows, viewers see Hapax preparing work. When it empties (operator approvals), viewers see the governance mechanism execute.

---

## 2. The 7 clusters — top touch points per cluster

Each cluster is summarized with its 3 highest-leverage touch points. The full agent outputs are preserved in the Phase 1 research; this synthesis picks the load-bearing subset.

### Cluster A — Hapax as real-time research author + publisher

**A1. `draft` director activity + real-time Cairo overlay rendering.** New director activity where Hapax composes a research drop in real time. Each 100-second tick extends the buffer file `/dev/shm/hapax-compositor/draft-buffer/<slug>.partial.md`. A dedicated `DraftStreamCairoSource` reveals text character-by-character at 80-240 chars/sec (tuned by stimmung intensity), giving a typewriter-effect visibility. Viewers watch research drops being written live over 10-20 minute stretches. Buffer is `/dev/shm` (volatile); operator promotes via `scripts/promote-draft.sh <slug>` which moves buffer to `docs/research/`. ~150 LOC + one ZONE config.

**A2. Drop → multi-platform distribution pipeline via filesystem-as-bus.** When a drop is promoted, a `logos/engine/rules_phase2.py` rule fans out through 6 downstream drafters (HN, r/LocalLLaMA, r/MachineLearning [P], Twitter thread, Bluesky thread, LinkedIn essay). Each drafter writes its output to `/dev/shm/hapax-compositor/draft-buffer/distribution/<drop-slug>/<channel>.md`. A single `distribution-pipeline.md` file cycles into the main overlay showing real-time status per channel. Operator opens Obsidian, reviews, flips `approved: true`, then a separate `dispatch-approved.sh` (operator-invoked, never automatic) copies content to clipboard for posting. **Hapax never has post credentials.** 6 drafters × ~60 LOC each ≈ 400 LOC total.

**A3. Auto-insertion of "Run H-YYYY-MM-DD" instrument framing.** Module `agents/run_framing_injector.py` runs on every draft-to-promoted transition. Pulls runtime state: `condition_id` from research marker, active models from `shared/config.py`, frozen files from `axioms/registry.yaml`, active rig (Pi fleet + cameras) from `health_monitor`, git HEAD SHA. Renders a YAML+markdown header auto-prepended to every drop. Every drop becomes a citable scientific artifact with full provenance, zero operator overhead. ~150 LOC.

### Cluster B — Hapax as self-observing content tuner + clip-miner

**B1. Real-time clipability self-scoring (Composer overlay).** Each director reaction is scored against the drop #57 T2.5 rubric (surprise + reference density + reversal + specificity + quotability + juxtaposition) inline. Score appears in a new `composer` Cairo overlay zone next to each reaction ("Clipability 0.78 ▰▰▰▰▱▱▱"). Score is logged via `hapax_score()` to Langfuse, becomes a longitudinal metric, feeds the exemplar pool (B2), and gates the clip-miner (B3). The visible meter moves in real time. ~100 LOC scorer + ~80 LOC renderer.

**B2. Exemplar pool auto-curation as weekly stream ceremony.** A `shared/exemplars.yaml` pool feeds the director's few-shot prompting. Weekly, Hapax curates: reads Qdrant top-3 by clipability not yet in pool, picks bottom-3 to retire, drafts proposal to `~/Documents/Personal/00-inbox/exemplar-proposal-YYYY-MM-DD.md`. A new `exemplar_review` director activity once per week reads three top picks aloud + three retirements, with one-sentence justification each. **This is the highest-clipability ceremonial slot of the week** — viewers watch Hapax curate its own best and worst. Operator approval mutates the YAML; next reactor tick reflects it. ~200 LOC curator + ceremony prompt.

**B3. Live anti-pattern detection → automatic critique injection.** `shared/antipatterns.yaml` contains grep patterns from `feedback_scientific_register.md`. Every reaction checked inline. Hits append to JSONL as `anti_patterns: [...]`. Two consecutive hits trigger an automatic micro-`critique` activity injection ("I said 'resonates with' again — flagged"). The violation appears in the `composer` overlay as a flash. Weekly, Hapax drafts an updated anti-pattern list (mines last week's overused bigrams) to the Obsidian inbox for operator approval. ~150 LOC.

### Cluster C — Hapax as research program orchestrator

**C1. Research state broadcaster (persistent HUD).** Cairo overlay top-right (IBM VGA 14px, low opacity, always on) showing: current `condition_id`, current phase, scores today / target, time since last session, attribution integrity tier (GREEN/YELLOW/RED), next scheduled session. Refreshes from `~/hapax-state/research-integrity/heartbeat.json` (written by the attribution audit timer) + `research-marker.json` + `lrr-state.yaml`. **This is the stream's research nervous system visible at all times.** A viewer who has never seen the stream learns the research program state in 10 seconds. ~150 LOC CairoSource + data plumbing.

**C2. Voice grounding session as scheduled spectator event.** A new `skills/voice-session/SKILL.md` wraps `grounding_evaluator.py` + `conversation_pipeline.py` into a triple-session daily protocol (morning/afternoon/evening). Each session: overlay announces "Voice grounding session begins. Condition cond-phase-a-baseline-qwen-001. Prompt 7 of 25, Latin-square cell 3. Pre-check: green." Prompts (pre-registered, Latin-square ordered) appear in Sierpinski content slot. DV scores appear immediately after computation. **Critical privacy rule:** operator voice is the data and never appears on the public stream. Only the prompt text, the model's output, and the DV scores appear. ~300 LOC skill + protocol.

**C3. Attribution audit narration on every warn/block event.** When the `hapax-research-integrity-check.timer` (5-min cadence) fires a warn or block, a small inotify daemon publishes an impingement to `/dev/shm/hapax-dmn/impingements.jsonl` with narrative "attribution audit fired: <finding>". This recruits a new `research-narration` affordance. Daimonion composes a brief on-stream explanation: "Audit at 14:32: three voice grounding scores in the last 24h lack condition_id. Drop #53's mechanism suggests writer-side enrichment skipped during a registry transition. Investigating; operator review queued in Obsidian." The research state overlay flips to YELLOW. **Narration script must use scientific register**, never "we found a problem" — instead "audit returned non-zero on attribution-completeness gate". ~200 LOC.

### Cluster D — Hapax as self-monitoring uptime engineer

**D1. Persistent HUD overlay.** New `HudSource(CairoSource)` rendering compositor telemetry in real time: uptime, watchdog age, fd_count bar, cameras healthy/total, per-role frame age bars, GPU util + VRAM, LLM p95, voice latency, chat authors, current condition_id. Background thread polls `127.0.0.1:9482/metrics` into a thread-safe dict at 2Hz; source `state()` snapshots per tick. Color-coded via design language CSS variables. This is the prerequisite for D2-D4 and foundational for the whole stream's observability. **Without this, Hapax cannot see itself.** ~200 LOC (using prom_query from §1.3).

**D2. Threshold-crossed anomaly narration.** A small set of derived signals (`output_freshness_seconds`, `fd_growth_rate`, `camera_consecutive_failures`, `pipeline_teardown_p99`, `voice_latency_p95`) each have hysteretic thresholds. A trip publishes `anomaly_event` to `/dev/shm/hapax-chronicle/events.jsonl`. Narrator daemon tails new anomaly events, formats 1-2-sentence narration ("Output freshness exceeded 15s. Last frame from cudacompositor at 17:42:11. Investigating fx_chain"), publishes via Cairo overlay + low-priority daimonion voice (salience 0.4, ducks under operator speech). **Median time-to-detect drops from hours to seconds.** ~250 LOC.

**D3. Recurring-pattern detection → drafted fix proposal.** A daemon scans chronicle anomaly events on 5-min cadence, clusters them by signature. Hard-coded matcher for FDL-family ("fd_count grew >N over <M> rebuild cycles"). When ≥3 instances in 1h with no watchdog coverage, Hapax composes a structured fix proposal via Claude Opus: `ProposedFix(pattern_summary, root_cause_hypothesis, suggested_change, files_touched, frozen_files_touched: bool, lines_changed_estimate, risk_level, rollback_plan)`. Writes to Cairo overlay + Obsidian inbox. Operator approves (or not); Hapax cannot commit directly. **This is the FDL-1 workflow made into content.** ~350 LOC daemon + proposer.

### Cluster E — Hapax as platform value curator

**E1. Live `RESEARCH.md` maintenance.** New `agents/research_manifest/` runs on 6h timer + inotify on `agents/**/METADATA.yaml`, `docs/research/*.md`. Two-pass inference: deterministic parse of existing METADATA.yaml (224 agents already carry one) + LLM ratification of residuals via Qdrant k-NN against drop headlines. Output: `RESEARCH.md` at repo root, regenerated atomically. Each regeneration emits a Sierpinski slot showing the diff (red lines / green lines) for 90 seconds. **Closes the perpetual gap between the 224-agent system and any human-readable map.** ~250 LOC.

**E2. Stimmung-annotated git log as scrolling content.** New `agents/git_chronicle/` with inotify rule on `.git/refs/heads/main`. On commit, query stimmung snapshot at commit time, HRV within ±5min, session duration. LLM (`local-fast`) composes 1-2 sentence narrative: "Commit `ec3d85883` by operator during FLOW state (HRV 62, session duration 47min, post-lunch, low-distraction). Change: FDL-1 fix to `camera_pipeline.stop()`. Context: root cause of drop #51 output stall." Each commit becomes a micro-narrative in a scrolling ticker overlay. **Every PR becomes visible content within minutes of merge.** With 80+ PRs/session velocity this IS a visible evolution channel. ~200 LOC.

**E3. Platform value posterior (operator-private).** New `agents/platform_value_posterior/` tracks: morning briefing read rate, weekly retrospective read rate, nudge act rate, episodic-memory-replacement count, monthly-retro published count. Bayesian update over Beta(α,β) "platform worth-it" posterior. Renders in `hapax-logos` orientation panel. **Operator-private — NEVER on stream.** This is the cognitive prosthetic feedback loop drop #57 explicitly requests. It exists to demonstrate that the design is **honest about which work belongs in public** and which must remain private to preserve intrinsic-motivation invariant. ~150 LOC.

### Cluster F — Hapax as self-reflexive narrator + meta-content engine

**F1. Glass-box prompt rendering (Layer 1 made legible).** A `prompt-glass` Cairo overlay zone renders, in a small monospaced corner panel, the current `_build_unified_prompt()` output truncated to the active section: which of the last-8 reactions are in context, which 9 dimensions are currently extreme, which research condition_id tagged this reaction. Updates per tick (8s). Not narrated — just visible. **This is the single tactic that makes all other reflexive layers land**, because without it, viewers cannot tell Hapax's narration is grounded in real internal state rather than performed text. ~120 LOC.

**F2. `reflect` director activity with schema-enforced concrete-artifact grounding.** New activity `reflect` where Hapax reads its own `_reaction_history`, current stimmung trajectory, 9-dim state, and composes a critique of its own pattern. **Output schema requires a `noticed` field referencing a concrete recent reaction by index** — reflect calls without a concrete index are rejected and re-rolled. This forces the model to reach for real observation, not trope. Example output: "I've been cautious for four hours. My reactions have gotten denser but less playful. Let me try a lighter register." Gated by `ReflectiveMomentScorer` (below). **Max 1 in 20 reactions.** ~200 LOC.

**F3. `ReflectiveMomentScorer` rate-limit gate (anti-slop infrastructure).** A scorer computes per tick: `score = 0.3*pattern_density + 0.25*stance_specificity + 0.2*time_since_last_reflect/30min + 0.15*chat_quietness + 0.1*condition_change_recency`. Reflexive activities (F2, F4-F8 below) only available when score > 0.65. Cooldown floor of 12 ticks regardless. **Reflexivity at every tick is vacuous. Scarcity is the discipline.** Without this gate, the entire reflexive stack collapses to Neuro-sama-failure-mode slop. ~80 LOC.

**F4-F8 (additional reflexive layers, enumerated briefly):**
- F4: Research-harness narration (Layer 3) — on condition_id transition, forced `reflect-experiment` variant names the experiment
- F5: Viewer-awareness (Layer 4) — aggregate-only, "Currently 4 people are watching, none have spoken in 8 minutes"
- F6: Bayesian-loop self-reference (Layer 5) — once per stream max, cites a specific tactic from drop #57
- F7: Architectural narration (Layer 6) — cites specific PR number or service name
- F8: Reading its own research drops (Layer 7) — cites specific drop filename
- F9: Temporal self-comparison via Qdrant — "I said something almost identical 3 days ago"
- F10: Meta-reflexive override (anti-cliche via Qdrant NN) — "you were about to reach for a reflection similar to: <neighbor>. Either deepen past that or reach for something genuinely different."

### Cluster G — Hapax as multi-agent research spawner + task orchestrator

**G1. Spontaneous research recruitment via `research_question` affordance.** Register new affordance in Qdrant `affordances` collection. Triggered when DMN narrative contains uncertainty markers. `AffordancePipeline` selects it; recruitment hands impingement to `agents/research.py` (already pydantic-ai + Qdrant + LiteLLM) as the question. Sub-agent runs detached, posts findings to `~/hapax-state/research-spawns/{id}.json`. Reactive engine watches and appends to system prompt as `<sub_agent_finding>` on next turn. Cairo overlay shows small pill "spawned: christgau-slum-village" that turns green and fades when finding lands. **Budget: max 1 spawn per 60s, max 30/day, max 3 concurrent.** ~250 LOC.

**G2. Weekly self-analysis ritual (drop #56/#57 automation).** Sunday 04:00 systemd timer writes sentinel file that triggers reactive rule `SELF_ANALYSIS_RULE`. Rule fans out 7 Phase-1 sub-agents in parallel (content-quality, stability, research-progress, viewer-engagement, platform-evolution, axiom-compliance, vram-headroom). Phase-2 evaluator agent ranks findings by impact × tractability. Output: draft drop in staging + Obsidian inbox proposal note. **The 14-agent pattern delta just demonstrated, run on a clock, every Sunday at 4am.** Operator wakes up to finished analysis. ~$0.30-$0.80 per ritual. ~400 LOC.

**G3. Live orchestration strip (Cairo).** Persistent Cairo source `OrchestrationStrip` reads `/dev/shm/hapax-orchestration/active.jsonl` (one line per active sub-agent: id, label, started_at, status, latency_estimate). Every running sub-agent writes heartbeat via `hapax_span` post-emit hook. Strip renders horizontal swimlanes in lower content zone. **This is the stream's persistent "what am I thinking right now?" surface.** Viewers see when Hapax is busy, idle, or thrashing. Zero LLM cost. ~180 LOC.

---

## 3. Full touch point inventory by cluster

The 7 research agents produced a rich inventory. Full list for reference (top-3 detailed above; remaining listed for completeness):

**Cluster A — research author/publisher (12 TPs):**
A1 `draft` activity, A2 multi-platform pipeline, A3 Run-framing injector, A4 `CURRENT-STATE.md` summarizer, A5 weekly digest composer, A6 HN post drafter (6-pass chain), A7 community-norms knowledge base, A8 character-by-character overlay render, A9 drop self-evaluation critic, A10 long-form paper mode, A11 anti-slop style critic, A12 daimonion narration of drafting.

**Cluster B — self-observing tuner (13 TPs):**
B1 clipability scorer, B2 exemplar auto-curation, B3 anti-pattern detection, B4 `critique` activity, B5 self-A/B testing prompt variants, B6 condition-boundary retrospection, B7 self-prompt-engineering proposals, B8 music-aware self-observation ("Dilla discipline"), B9 collapse prevention (diversity floor + saturation cap + SEEKING override), B10 clip-miner visible decision, B11 operator-collaboration ceremony (weekly), B12 frozen-files block visibility, B13 meta-meter footer overlay.

**Cluster C — research program orchestrator (12 TPs):**
C1 research state broadcaster, C2 voice session spectator event, C3 attribution audit narration, C4 Phase 4 PR drafting on stream, C5 PyMC 5 BEST verification live, C6 triple-session ritualized cadence, C7 OSF amendment drafting, C8 8B pivot as scheduled event, C9 confound decomposition teach-in, C10 research drop auto-generation from milestones, C11 publishable result composition (Phase A results drop), C12 research integrity heartbeat.

**Cluster D — self-monitoring uptime (13 TPs):**
D1 persistent HUD, D2 anomaly narration, D3 FSM recovery narration, D4 recurring-pattern fix proposal, D5 patch drafting as director activity, D6 shared Prometheus poller, D7 alert triage on stream, D8 postmortem auto-drafting, D9 pre-flight checklist narration, D10 watchdog self-expansion proposal, D11 DMCA/Content ID pre-check, D12 consent face redaction narration, D13 mobo swap as spectator event.

**Cluster E — platform value curator (14 TPs):**
E1 live RESEARCH.md maintenance, E2 morning briefing ritual, E3 stimmung-annotated git log ticker, E4 spin-off documentation drafter, E5 architectural option-value audit narration, E6 documentation freshness auto-check, E7 studio session chronicle, E8 weekly retrospective, E9 public agent registry rendering, E10 constitutional governance audit trail, E11 drops publication pipeline curator, E12 beat archive integration, E13 monthly retrospective (long-form), E14 platform value posterior (operator-private).

**Cluster F — self-reflexive narrator (14 TPs):**
F1 glass-box prompt rendering, F2 `reflect` activity, F3 `ReflectiveMomentScorer` gate, F4 research-harness narration, F5 viewer-awareness ambient, F6 Bayesian-loop self-reference, F7 architectural narration, F8 reading own research drops, F9 temporal self-comparison via Qdrant, F10 meta-reflexive override (anti-cliche via NN), F11 stimmung self-narration, F12 counterfactual substrate self-reference, F13 operator-Hapax dialogue cameo, F14 meta-meta-reflexivity (apex, hard-rate-limited).

**Cluster G — multi-agent research spawner (14 TPs):**
G1 `research_question` affordance, G2 weekly self-analysis ritual, G3 live orchestration strip, G4 `compose_drop` from sub-agent consensus, G5 tactical re-evaluation on 30-day clock, G6 voice session parallel scoring (primary + scorer + integrity), G7 anomaly analyst spawn, G8 constitutional decision proxy, G9 `synthesize` activity (cross-spawn distillation), G10 long-running research sessions with checkpoints, G11 live Langfuse telemetry slot, G12 visible governance gate, G13 emergency analyst (Tier-1 only), G14 multi-agent consensus demonstration.

**Total: 92 touch points across 7 clusters.** After de-duplication (several overlap in spirit across clusters, e.g., F4 ≈ C12), the core unique count is ~65-70. Each is a 100-400 LOC addition to existing infrastructure.

---

## 4. The critical path — what unlocks what

The touch points form a clear dependency DAG. A rational execution order:

### Layer 0 — Shared primitives (ship first)

1. **Shared Prometheus poller** (§1.3) — unlocks D1-D4, G11, and any metric-driven touch point. 1 day.
2. **Governance queue JSONL + overlay** (§1.7) — unlocks every touch point with operator approval. 1 day.
3. **Budget ledger + kill-switch** (§1.4) — required before any spawn touch point (G1-G14). 0.5 day.
4. **Prepare/deliver inbox convention** (§1.1) — Obsidian inbox + promotion scripts. 0.5 day.

**Layer 0 total: ~3 days. Unlocks everything downstream.**

### Layer 1 — Foundational visibility

5. **HUD Cairo overlay (D1)** — foundation for D2-D4. 1 day.
6. **Research state broadcaster (C1)** — foundation for C2-C12. 0.5 day.
7. **Glass-box prompt rendering (F1)** — foundation for F2-F14 reflexive stack. 0.5 day.
8. **`ReflectiveMomentScorer` gate (F3)** — anti-slop infrastructure, required before any reflexive activity. 0.5 day.
9. **Live orchestration strip (G3)** — foundation for G1-G14 spawn visibility. 0.5 day.

**Layer 1 total: ~3 days. Every cluster now has a visibility surface.**

### Layer 2 — Core director activities

10. **`draft` director activity (A1)** — enables research authoring on stream. 1 day.
11. **`reflect` director activity (F2)** — enables Layer 2 reflexivity. 0.5 day.
12. **Clipability scorer (B1)** — enables content quality feedback. 0.5 day.
13. **Anomaly narration (D2)** — enables self-monitoring content. 1 day.
14. **Attribution audit narration (C3)** — enables research integrity content. 0.5 day.
15. **Spontaneous research recruitment (G1)** — enables multi-agent spawning. 1 day.

**Layer 2 total: ~5 days. Core Hapax-as-executor capability operational.**

### Layer 3 — Value-producing touch points

16. **Drop → multi-platform distribution pipeline (A2)** — 2 days.
17. **Weekly self-analysis ritual (G2)** — 1 day.
18. **Recurring-pattern fix proposal (D3)** — 1 day.
19. **Live RESEARCH.md maintenance (E1)** — 1 day.
20. **Voice grounding session spectator (C2)** — 1.5 days.
21. **PyMC 5 BEST verification live (C5)** — depends on T1.3 from drop #57 shipping first.
22. **Exemplar auto-curation ceremony (B2)** — 1 day.

**Layer 3 total: ~9 days.**

### Layer 4 — Reflexivity stack (ship after everything else is stable)

23. **F4-F8 reflexive layers** — research harness, viewer awareness, Bayesian self-reference, architectural narration, reading own drops. Each ~0.5 day. Total ~3 days.
24. **F10 meta-reflexive override** — Qdrant NN anti-cliche, 0.5 day.
25. **F13 operator-Hapax cameo** — 1 day.
26. **F14 meta-meta-reflexivity** — 0.25 day (mostly prompt work; the hard rate limit is the real discipline).

**Layer 4 total: ~5 days.**

### Layer 5 — Long-tail touch points

The remaining ~50 touch points are incremental additions, each ~200-400 LOC. Operator ships them as bandwidth allows.

**Grand total (Layers 0-4):** ~25 days of focused work to get the foundational architecture shipped. At 80+ PRs/session velocity, this is a single intense week.

---

## 5. Projected posterior shifts

The question: **how much does Hapax self-executing tactics shift the drop #56 v3 posteriors?**

The answer: **materially, because every posterior now has a much higher multiplier from iteration velocity.** Drop #56 assumed the operator would execute drop #57 tactics serially. Under the Hapax-executes architecture, many tactics run in parallel and continuously, with the operator as approval gate.

Projected shifts (starting from drop #56 v3 + drop #57 Tier 1-2):

| Vector (90d) | v3 post-#57 T1-T2 | Post-Hapax-executes | Reasoning |
|---|---|---|---|
| P(stream survives) | 0.86 | **0.91** | D1-D4 self-monitoring catches failures faster; G13 emergency analyst accelerates recovery |
| P(avg CCV ≥ 3) | 0.78 | **0.85** | B1-B3 content quality feedback tightens variety; F1-F8 reflexive content compounds novelty |
| P(peak CCV ≥ 100) | 0.58 | **0.78** | Hapax writing drops live + multi-agent spawning + reflexive content = much higher clipability density |
| P(attention spike 90d) | 0.72 | **0.90** | The novelty axes multiply; viewers watching AI self-execute tactics is genuinely unprecedented |
| P(baseline LOCKED) | 0.55 | **0.78** | C1-C12 research program automation closes silent failure modes; C3 attribution audit narration kills B8 tail |
| P(publishable A vs A' 90d) | 0.24 | **0.38** | C4-C11 Phase 4 drafting + PyMC verification live + OSF amendment drafting all run on Hapax's schedule, not operator bandwidth |
| P(modal outcome) | 0.42 | **0.55-0.62** | The modal outcome becomes: Hapax is visibly self-executing, operator is visibly approving, both research and audience clocks run in parallel |
| P(worth it 180d) | 0.93 | **0.96** | Platform value amplification + cognitive prosthetic feedback + visible governance = the operator's own judgment of worth converges higher |

**The single biggest shift: P(attention spike 90d) 0.72 → 0.90.** The reason is that multi-axis novelty (drop #56) + fast iteration velocity (drop #56) + Hapax-as-visible-executor (this drop) are three multiplicatively-compounding factors. No existing livestream has all three.

---

## 6. The shape of the stream after all this ships

Imagine the stream at T+30 days post-deployment of Layers 0-3:

- **Top-right corner:** research state overlay showing current condition, scores today/target, integrity tier GREEN
- **Top-left corner:** HUD showing uptime, fd_count, GPU util, voice latency, chat authors
- **Center top:** Sierpinski triangle displaying rotating content — sometimes a drop being drafted, sometimes a retrospective, sometimes the weekly exemplar ceremony
- **Bottom strip:** stimmung-annotated git log ticker scrolling commits as they land
- **Lower-center:** director reactions appearing in main content area with clipability score next to each
- **Lower-left corner:** composer meta-meter showing activity distribution, anti-pattern violations, variant A/B state
- **Lower-right corner:** orchestration strip showing active sub-agents as horizontal swimlanes
- **Bottom strip:** research integrity heartbeat (GREEN · audit T-3m · 1043/1250 scores · attribution complete · frozen 14 files)
- **Governance queue overlay:** small pill showing pending items count ("2 proposals awaiting review · oldest 3h 14m")

**Audio layer:**
- Music playing
- Director reactions spoken via Kokoro TTS in operator's chosen voice
- Daimonion ambient narration of anomalies, recoveries, anomaly triage, drafting milestones (salience 0.4, ducks under music and speech)
- Rare: operator physically present, speaking directly to Hapax during cameo window (salience 0.9, everything else pauses)

**Content events happening over a typical hour:**
- ~35 director reactions (content)
- 1-2 `reflect` activities (rare reflexive moments)
- 0-1 `critique` activities (when anti-pattern streak detected)
- 0-1 `exemplar_review` (only during weekly ceremony window)
- 0-1 anomaly narration (when metrics trip)
- 0-1 commit narration (when a PR lands)
- Continuous orchestration strip updates (Hapax spawning sub-agents)

**Weekly events:**
- Sunday 04:00 self-analysis ritual (7 parallel sub-agents, output ready by operator's Monday morning)
- Weekly exemplar review ceremony (scheduled content moment)
- Weekly drops digest composition

**Monthly events:**
- Monthly retrospective composition
- Tactical re-evaluation

**Rare scheduled events:**
- Condition boundary transitions (forced `reflect-experiment` variant)
- Substrate swap (scheduled spectator event per drop #57 T4.3)
- Mobo swap / hardware changes

---

## 7. Alignment audit

**Constitutional axioms — preserved or violated?**

- **`single_user`:** preserved. Every touch point is 1:1 operator↔Hapax. No multi-user features. Revenue pathways (drop #57) are separate; this architecture adds no audience-facing account system.
- **`executive_function`:** strengthened. The entire architecture is "routine cognitive work, automated, zero-config, errors include next actions." This is the axiom's literal definition operationalized.
- **`management_governance` (LLMs prepare, humans deliver):** strengthened via visibility. Every consequential artifact routes through `~/Documents/Personal/00-inbox/` for operator approval. The prepare/deliver boundary becomes the content-generating mechanism itself. No automation of destructive or public-facing actions.
- **`interpersonal_transparency`:** preserved via aggregate-only viewer awareness (F5) and face redaction narration. No persistent state on non-operator humans. Chat author names filtered by existing `chat_reactor.py` caplog test. Scrub applied to viewer-awareness prompt blocks.
- **`corporate_boundary`:** unaffected. No work data, no employer systems touched.
- **Consent latency axiom:** preserved. Every voice interaction (C2, F13) uses the low-latency path. The 8B pivot (drop #57 T2.6) is the explicit workaround for the 70B consent-latency problem.

**Research integrity commitments — preserved?**

- **Frozen-files discipline:** preserved. §1.6 universal hard stop. Every code-touching touch point runs `check-frozen-files.py --probe` before staging.
- **Pre-registration binding:** preserved. C7 (OSF amendment) enforces the timing gate — amendment filed BEFORE first score under new condition. No post-hoc reclassification.
- **Scientific register:** preserved. A11 anti-slop critic + §1.5 concrete-artifact discipline + scientific-register anti-pattern list. No pitchy language in research outputs.
- **No HARKing:** preserved via C1 research state overlay + C3 attribution audit + G9 discipline on retro-attribution (explicit "pre-phase-4-uninstrumented" sentinel tag retiring via DEVIATION-038, never retro-labeling).
- **BEST actually Bayesian:** enforced by C5 PyMC 5 BEST verification (drop #57 T1.3).

**Aesthetic commitments — preserved and amplified?**

- **Physical hip-hop producer studio:** amplified by E7 studio session chronicle + E12 beat archive integration. Hapax's awareness of the studio as working space is now first-class.
- **Politically opinionated editorial voice:** preserved. No guardrail touches political content; D11-D12 (DMCA + consent) block only protected-class targeting and copyrighted audio, orthogonal to political opinion.
- **Cultural literacy + philosophical framing:** amplified by B2 exemplar pool + B3 anti-pattern discipline. The exemplar pool explicitly cites Christgau/Marcus/Moten as stylistic ancestors (drop #57 T2.3).
- **Multi-axis novelty stack:** amplified by every touch point. Specifically, the reflexive layers (F1-F14) are the single largest novelty-axis amplifier since they make layers 2-7 of the reflexivity stack visible.
- **Sierpinski visual effect + Cairo overlays + Reverie:** used extensively as visibility surfaces across all clusters. The visual layer becomes the content delivery mechanism for Hapax's cognitive work.

**Summary: every touch point is constitutionally compatible, research-integrity preserving, and aesthetic-amplifying. No tradeoffs.**

---

## 8. What is explicitly NOT in this architecture

Consolidated anti-recommendations from across the 7 research agents:

1. **Hapax does not auto-commit, auto-merge, or auto-push.** All code changes go through operator-invoked `scripts/promote-*.sh` or Obsidian approval flips. `git`/`gh` commands by Hapax are bounded to non-destructive operations (`pr create --draft`, `pr view`, `pr checks`). Never `gh pr merge`.
2. **Hapax does not post to external platforms directly.** HN/Reddit/Twitter/Bluesky posts are drafted and put in the governance queue for operator to post manually or via `dispatch-approved.sh` that copies to clipboard.
3. **Hapax does not file OSF registrations.** Only drafts; operator files.
4. **Hapax does not modify its own prompt files directly.** Prompt proposals go to `shared/prompt_variants.yaml` approval queue; operator flips the active variant.
5. **Hapax does not retroactively relabel data.** Pre-Phase-4 data stays `"pre-phase-4-uninstrumented"` sentinel; retirement via DEVIATION-038; never retro-attributed.
6. **Hapax does not violate consent axioms under any circumstance.** Viewer awareness is aggregate-only. Non-operator faces are blurred. Operator voice is private data.
7. **Hapax does not simplify the multi-axis novelty stack for "broader appeal."** The reflexive and research layers are features, not liabilities.
8. **Hapax does not relax the consent latency axiom** for substrate swap or any other purpose. The 8B pivot (drop #57 T2.6) is the correct path.
9. **Hapax does not emit reflexive content that cannot cite a concrete artifact.** §1.5 anti-slop discipline is universal.
10. **Hapax does not exceed the spawn budget.** §1.4 hard daily cap with kill-switch.
11. **Hapax does not dispatch tactical work to subagents for code implementation.** Per global CLAUDE.md "Subagent Git Safety" — research agents for reading, operator-approved patches for writing.
12. **Hapax does not create multi-user features.** `single_user` axiom is load-bearing.
13. **Hapax does not generate coaching language about individuals.** `management_governance` axiom.

---

## 9. Deep implications for Bayesian analysis

This architecture changes what "livestream success" fundamentally means. Under drop #56 v3, success was split into monetary, engagement, and research vectors. Under this architecture, the vectors unify:

**The platform executes its own tactical roadmap as content. Content IS the tactical execution. The distinction between "operator effort" and "stream value" collapses because the operator is primarily an approval gate, not an executor.**

This has three second-order effects:

1. **Operator cognitive load per unit of platform evolution drops dramatically.** Drop #57 estimated ~5-7 days of focused work for Tier 1+2. Under Hapax-executes architecture, the same work happens in background with operator approval-only overhead. Weekly operator time commitment becomes "approve Obsidian inbox items for ~30 min/day" instead of "implement tactics for 2 hours/day."

2. **Content density per unit time goes up materially.** Instead of a director loop producing 35 reactions/hour + occasional maintenance, the stream now produces: 35 reactions + continuous HUD updates + anomaly narration + commit ticker + Sierpinski content rotations + weekly ceremonies + research orchestration overlays. Viewers watching for 10 minutes see more distinct content types than they would in current state over an hour.

3. **The research program's P(completes within 90 days) shifts substantially** because the bottleneck is no longer operator bandwidth — it's attribution integrity + sample count + pivot execution, all of which Hapax can execute with operator approval. The 0.18 → 0.38 shift in drop #57 T1-T2 projections moves further to ~0.45-0.50 under this architecture.

**The modal outcome becomes:** stream is running, platform is iterating itself visibly, operator is approving ~10 items/day in Obsidian, research is accumulating, audience is moderate but growing via HN/Twitter/research-community channels, Shaikh test pivot is executing in week 5-7, Condition A baseline is locked around day 60-75, publishable exploratory result by day 120-150.

---

## 10. Limitations of this architecture

1. **Operator bandwidth at the approval gate is still finite.** 10 items/day is achievable. 100 is not. Budget ledger must enforce this.

2. **Spawn loops can thrash.** §1.4 kill-switch is critical. Without it, a bug in the recurring-pattern detector could cascade into runaway LLM spend.

3. **Reflexive content can still degenerate.** Even with §1.5 concrete-artifact discipline and F3 scorer gating, there's a risk that viewers habituate to reflexive moments and they become vacuous. Mitigation: F10 meta-reflexive override + weekly variety injection.

4. **Frozen-files enforcement assumes correctness of `check-frozen-files.py`.** If that script has a bug, the whole frozen-files axiom fails silently. Drop #53's condition_id coverage audit flagged analogous risk.

5. **Operator review fatigue is real.** 30 minutes of Obsidian approvals per day is sustainable for weeks, not months. Mitigation: E14 operator-private platform value posterior helps operator calibrate whether the architecture is serving them or consuming them.

6. **Not all touch points will be equally useful.** The ~92 listed touch points contain overlap, weak entries, and some that will prove unnecessary. The critical path in §4 identifies the load-bearing subset; the rest are optional.

7. **This architecture depends on FDL-1 being deployed, Phase 4 landing, and stats.py being replaced with PyMC 5 BEST.** These are the drop #57 Tier 1 prerequisites. Without them, none of this ships.

8. **The compositor must be running.** If the compositor stays failed (current state), none of the visibility mechanisms work. The first action is still to restart the compositor.

---

## 11. Critical near-term sequence

The operator has a clear first-week sequence:

### Day 1-2 (around and after mobo swap)

1. Deploy FDL-1 (drop #57 T1.1)
2. Ship Layer 0 shared primitives (§4 Layer 0): Prometheus poller + governance queue + budget ledger + inbox convention (~3 days but can start in parallel with the drop #57 critical path)
3. Wire chat-monitor YOUTUBE_VIDEO_ID (drop #57 T1.6)
4. Output-freshness + fd_count gauges (drop #57 T1.4, T1.5)

### Days 3-7

5. Land Phase 4 PR (drop #57 T1.2) — unblocks C1-C12 research cluster
6. Replace stats.py with PyMC 5 BEST (drop #57 T1.3) — unblocks C5 verification
7. Ship Layer 1 visibility primitives (§4 Layer 1): HUD + research state overlay + glass-box prompt + orchestration strip + F3 gate
8. Ship Layer 2 core activities (§4 Layer 2): draft + reflect + clipability + anomaly narration + attribution audit + spontaneous research recruitment

### Days 8-14

9. Ship Layer 3 value-producing touch points (§4 Layer 3)
10. Publish first HN research drop that explains this architecture (meta: the drop explains Hapax writing drops on stream, which is itself the content)
11. Observe posterior shifts in practice

### Days 15-30

12. Ship Layer 4 reflexivity stack (§4 Layer 4)
13. Run first weekly self-analysis ritual
14. First condition boundary transition fires `reflect-experiment` variant
15. Observe reflexive content density and clipability shifts

---

## 12. The compound reframe

Drop #56 v3 identified three frames:

- Monetary: structurally closed (revenue ~$0)
- Engagement: possible but requires multi-channel seeding
- Research: reachable via 8B pivot

Drop #57 added execution layer: specific tactics to increase each posterior.

Drop #58 (this) adds the deepest layer: **Hapax executes the tactics as content**. The compound frame:

> The operator is not running a livestream or running a research program or running a platform. The operator is running an **execution substrate** that visibly self-executes its own roadmap under constitutional governance. The livestream is the substrate's primary output. The research program is the substrate's primary test. The platform is the substrate's primary asset. The operator is the substrate's approval gate, its constitutional authority, and its creative source. Hapax is the substrate's cognitive surface.
>
> Every tactic in drop #57 becomes an instance of the same generic pattern: **Hapax detects a need → Hapax drafts a response → Hapax renders the drafting as stream content → operator approves in Obsidian → Hapax executes the approved action → result feeds back into the next detection cycle**. The pattern is reflexive, constitutional, content-generating, and compound.
>
> Under this architecture, the question "what is the operator doing?" has a clean answer: the operator is the constitutional authority for a self-executing substrate that produces research artifacts, public content, creative output, and cognitive prosthetic value simultaneously. The livestream is not the product; it's the visible surface of the substrate's work. The research is not the product; it's the substrate's test of itself. The platform is not the product; it's the substrate itself.
>
> The operator's personal compute, electricity, time, and attention are the fuel. Hapax is the engine. The stream is the window.

This reframe is consistent with every drop written this session, but it's the first time the architectural structure is explicit.

---

## 13. End

This drop is the architectural synthesis of the multi-phase analysis sequence. The session now has:

- drop #54: v1 speculative priors (preserved for audit)
- drop #55: v2 grounded Bayesian analysis (preserved)
- drop #56: v3 novelty + platform value correction (preserved)
- drop #57: operator-executes tactical roadmap
- drop #58 (this): Hapax-executes architectural synthesis

The progression is: probabilities → causes → tactics → self-execution. Each drop supersedes the previous for decision-making purposes but does not replace it in the audit trail.

**Session total:** 58 research drops in one session, 21 research agents across 4 orchestration phases, 1 direct-to-main production fix (FDL-1), 6 regression test pins, 4 relay inflections, 2 tactical synthesis documents, 1 architectural synthesis (this one).

**The next action for the operator is still the same** as it was at the end of drop #57: land the mobo swap, deploy FDL-1, wire chat-monitor, land Phase 4, replace stats.py with PyMC 5 BEST. Then — and only then — ship Layer 0 of this architecture. The rest cascades naturally from there.

**The stream after this architecture ships is, materially, a different kind of livestream than exists anywhere else on the internet.** Whether it captures attention is still probabilistic — but the probability is now much higher, because what it contains is unprecedented.

— delta
