# Drop #62 — Cross-epic fold-in: LRR ↔ HSEA unified roadmap

**Date:** 2026-04-14
**Author:** delta (research support role, synthesizing cross-epic fold-in research agent)
**Status:** Draft synthesis. Operator decisions required at §4 (substrate swap), §6 (state file), §10 (open questions).
**Source documents:**
- LRR spec: `/home/hapax/projects/hapax-council/docs/superpowers/specs/2026-04-14-livestream-research-ready-epic-design.md` (1371 lines, 11 phases, alpha-authored)
- LRR plan: `/home/hapax/projects/hapax-council/docs/superpowers/plans/2026-04-14-livestream-research-ready-epic-plan.md`
- HSEA spec: `/home/hapax/projects/hapax-council/docs/superpowers/specs/2026-04-14-hsea-epic-design.md` (794 lines, 13 phases, delta-authored)
- HSEA plan: `/home/hapax/projects/hapax-council/docs/superpowers/plans/2026-04-14-hsea-epic-plan.md`
- Drop #57 (tactics), drop #58 (HSEA thesis), drop #59 (HSEA audit)

---

## 1. Executive summary

LRR and HSEA were authored independently the same day (2026-04-14) by two roles (alpha and delta). They are not duplicates — they have distinct purposes — but they collide on roughly a quarter of their scope. LRR is a **research-validity sequencing epic**: it ships the registry, archive, governance, persona, objectives, closed-loop, and observability that Legomena Live needs to remain a defensible research instrument. HSEA is a **content-execution layering epic**: it makes Hapax visibly draft research, code, governance, and revenue artifacts that then route through an operator-controlled approval queue, with the drafting itself becoming the stream content.

Five top findings:

1. **No fundamental conflict — one structural conflict.** The only hard incompatibility is LRR Phase 5 (Hermes 3 70B substrate swap) versus HSEA Phase 4 cluster I4 (Hermes 3 8B parallel-config pivot). Drop #56 already showed the 70B path is unreachable under the operator's own `interpersonal_transparency` consent-latency axiom; HSEA Phase 4 I4 is the reified fix. **Recommendation:** restructure LRR Phase 5 into Phase 5a (8B parallel, owned and shipped by HSEA Phase 4 I4) and Phase 5b (70B, deferred behind a hardware/quant gate, future epic).

2. **Five primitive families overlap and need single-owner declarations.** Frozen-files probe, research-marker SHM, condition_id tagging, research-registry CLI, and stats.py BEST port are touched by both epics. Each needs one owner, one consumer. **All five should be owned by LRR Phase 1**; HSEA reads them. HSEA Phase 0 should drop its `check-frozen-files.py --probe` extension as new work and instead **block on LRR Phase 1 frozen-files shipping** then add a thin probe wrapper.

3. **The "drafting visibility" axiom precedent (HSEA `sp-hsea-mg-001`) and LRR's `it-irreversible-broadcast` implication are the same governance work, split across two epics.** Both must land in `hapax-constitution` together, in one PR, with overlapping operator review. **Owner:** LRR Phase 6, with HSEA Phase 0 drafting the precedent text and contributing it as a sub-deliverable to LRR's Phase 6 PR.

4. **State files should be siblings under a shared index, not merged.** The two epics will run with overlapping active phases (HSEA Phases 5–9 parallelize while LRR is still in Phases 4–10). One unified file forces a single-writer constraint that destroys the parallelism. Sibling files (`lrr-state.yaml`, `hsea-state.yaml`) under a shared index file (`research-stream-state.yaml`) with cross-references is the correct design.

5. **Drop #57's 38 tactics are 60% LRR-owned, 30% HSEA-owned, 10% operator-only.** HSEA's Phase 4 cluster I attempts to cover several drop #57 tactics (T1.3, T1.7, T2.2, T2.6, T2.8, T4.8, T4.11) by drafting code patches. **All seven of those drafters generate code that is also LRR phase work.** The fold-in routes them: LRR phases own the *implementation*; HSEA Phase 4 I-drafters become *content surfaces that watch and narrate* the LRR work, not separate implementations. This eliminates duplicate substrate.

**Bottom-line recommendation:** Both epics ship. LRR is the substrate (research integrity, governance, content infrastructure). HSEA is the visibility/content layer that makes LRR's work into the stream itself. The fold-in is a **dependency reordering** — not a merger. The merged sequence has 14 unified phases (UP-0 through UP-13). Critical execution rule: every unified phase has one source-of-truth epic and one secondary-consumer epic; nothing has two owners.

---

## 2. Phase-by-phase overlap matrix

Rows = LRR phases (0–10). Columns = HSEA phases (0–12). Cells classify the relationship.

Key: `DUP` = duplicate scope; `PART` = partial/shared infrastructure; `DEP` = dependency (LRR → HSEA or HSEA → LRR); `COMP` = complement; `CONF` = conflict; `—` = no relationship.

| LRR ↓ / HSEA → | H0 Foundation | H1 Visibility | H2 Activities | H3 Research orch | H4 Code drafting | H5 Biometric triad | H6 Content quality | H7 Self-monitor | H8 Platform value | H9 Revenue | H10 Reflexive | H11 Spawner | H12 Long-tail |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **L0 Verification** | PART (chat-monitor, Kokoro baseline, FINDING-Q) | — | — | — | — | — | — | DEP→ (anomaly narration consumes L0 alerts) | — | — | — | — | — |
| **L1 Research registry** | **PART** (frozen-files, condition_id, stats.py) | DEP→ (HUD reads condition_id) | DEP→ (activities read marker) | **DEP→** (C5/C6 wait on L1) | **DEP→** (I1 PyMC drafter watches L1) | DEP→ (M4 reads condition_id) | — | — | — | — | — | — | — |
| **L2 Archive instrument** | — | DEP→ (research state broadcaster reads archive) | — | DEP→ (C10 reads archive segments) | — | DEP→ (M4 reads 18-month archive) | DEP→ (clip-miner consumes archive) | DEP→ (postmortem reads segments) | DEP→ (chronicle reads archive) | — | DEP→ (F8/F9 read archive) | — | — |
| **L3 Hardware validation** | — | — | — | — | **CONF→ I4** (8B pivot vs 70B path) | — | — | DEP→ (D13 mobo swap watcher) | — | — | — | — | — |
| **L4 Phase A completion** | — | — | — | **DEP→** (C2 spectator event) | DEP→ (drafters wait on Phase A lock) | — | — | — | — | — | — | — | — |
| **L5 Hermes 3 swap (70B)** | — | — | — | DEP→ (C7 OSF amendment, C8 spectator) | **CONF** — supplanted by HSEA I4 (8B pivot); see §4 | — | — | — | — | — | — | — | — |
| **L6 Governance finalization** | **PART** (axiom precedent + irreversible-broadcast = same PR vehicle) | DEP→ (governance overlay reads queue) | — | — | DEP→ (drafter pre-emit consent scan) | DEP→ (M1 consent gate) | — | DEP→ (D12 face redaction narration) | DEP→ (E10 governance audit ticker) | DEP→ (H8 axiom-revenue gate) | — | DEP→ (G8 constitutional decision proxy) | — |
| **L7 Persona spec** | — | DEP→ (persona feeds glass-box prompt overlay) | DEP→ (activities adopt persona register) | — | — | — | DEP→ (B5 self-A/B compares against persona) | — | — | — | DEP→ (F11 stimmung self-narration) | — | — |
| **L8 Content programming via objectives** | — | DEP→ (orchestration strip = G3 = same surface) | **PART** (objectives ↔ activities) | DEP→ (objective-advancement scoring) | — | — | DEP→ (clipability drives objective scoring) | — | DEP→ (E1 RESEARCH.md surfaces objectives) | — | — | — | — |
| **L9 Closed-loop feedback** | — | — | DEP→ (chat → activities) | — | — | DEP→ (M2 voice-Qdrant retrieval) | DEP→ (B8 music-aware self-observation) | — | DEP→ (E3 stimmung-annotated git ticker) | — | — | — | — |
| **L10 Observability + drills + polish** | DEP→ (HSEA HUD reads same Prom series) | **PART** (HUD = D1 from drop #58) | — | — | — | DEP→ (M1 HRV strip = same Prom plumbing) | — | **PART** (anomaly narration = D2-D6 = same alerts) | — | — | — | — | DEP→ (H12 long-tail observability) |

**Read of the matrix:**
- **One conflict cell (L3↔H4 / L5↔H4):** the 70B-vs-8B substrate question. Resolved in §4.
- **Five PART cells:** L0↔H0, L1↔H0, L1↔H1, L6↔H0, L8↔H1, L10↔H1, L10↔H7. Each maps to a shared concept that must be single-owned (§3).
- **No duplicate cells.** Where work could collide, it is actually shared infrastructure, not duplicated implementation.
- **Heavy DEP traffic from LRR → HSEA.** HSEA is structurally a layer on top of LRR. This validates the fold-in: LRR ships the substrate; HSEA reads it.

---

## 3. Shared concept ownership table

For every primitive that both epics touch, a single owner-epic is declared. The other epic READs the primitive at the documented interface.

| # | Concept | Owner epic / phase | Consumer epic / phase | Resolution rule |
|---|---|---|---|---|
| 1 | `scripts/check-frozen-files.sh` (or `.py`) | **LRR Phase 1** (item 4: pre-commit hook) | HSEA Phase 0 (consumes; adds `--probe` mode as a thin extension PR within Phase 0 if and only if LRR Phase 1 has merged) | One tool, two callers. HSEA Phase 0 must NOT drop a parallel `check-frozen-files.py`. If LRR Phase 1 hasn't merged when HSEA Phase 0 opens, HSEA Phase 0 sequencing slips. |
| 2 | `~/hapax-state/research-registry/cond-*/condition.yaml` | **LRR Phase 1** (item 1) | HSEA Phase 1 (research state broadcaster), HSEA Phase 3 (C5/C6/C11), HSEA Phase 4 I1 (drafter waits), HSEA Phase 5 M4 | Append-only by definition. HSEA writes nothing under this path. |
| 3 | `/dev/shm/hapax-compositor/research-marker.json` | **LRR Phase 1** (item 3) | HSEA Phase 1 (1.2 research state broadcaster reads it), HSEA Phase 2 (`reflect`/`critique` activities tag with current condition_id) | LRR's `scripts/research-registry.py` is the only writer. HSEA reads via standard atomic-read pattern. |
| 4 | `scripts/research-registry.py` | **LRR Phase 1** (item 8) | HSEA Phase 3 C-cluster orchestration uses subcommands as-is; HSEA does not extend the CLI. New subcommands needed by HSEA must be PR'd into LRR Phase 1's source file, not forked. |
| 5 | `condition_id` tagging on Qdrant + JSONL + Langfuse | **LRR Phase 1** (item 2: per-segment metadata; item 5: Langfuse extension) | HSEA Phase 3 (C-cluster reads), HSEA Phase 5 M4 (drift detector reads), HSEA Phase 10 F-cluster (reflexive layers cite condition_id) | Same. Backfill is LRR's responsibility (Phase 1 item 9). |
| 6 | `stats.py` PyMC 5 BEST port (drop #57 T1.3) | **LRR Phase 1** (item 7: BEST verification) | HSEA Phase 4 I1 drafter | **Resolution:** HSEA Phase 4 I1 drafter does NOT write the PyMC 5 port from scratch. Instead, I1 becomes a *narration drafter* that watches LRR Phase 1's port commits, drafts a research drop summarizing the change for stream content, and routes the drop through governance queue. This converts I1 from "Hapax writes the canonical research code" to "Hapax narrates the canonical research code being written." See §4 for the same pattern applied to other I-drafters. |
| 7 | Hermes 3 substrate swap | **See §4 — substrate is split into 5a (HSEA-owned 8B) and 5b (LRR-owned 70B, deferred)** | — | Single most consequential ownership decision. |
| 8 | `chat-monitor.service` fix (LRR Phase 0 item 1) | **LRR Phase 0** | HSEA Phase 9 (closed-loop feedback consumes chat signal); HSEA Phase 7 D6 (alert triage reads chat-monitor reconnect metric) | Bug fix. Owner is whichever epic ships first, but LRR Phase 0 is structurally first. |
| 9 | `axioms/persona/hapax-livestream.yaml` | **LRR Phase 7** | HSEA Phase 1 (1.3 glass-box prompt renders it), HSEA Phase 2 activities adopt the register, HSEA Phase 10 F-cluster cites it | Persona is research-validity-load-bearing; LRR owns. HSEA renders it on stream. |
| 10 | `hapax-stream-mode` CLI + axis | **LRR Phase 6** (item 2) | HSEA Phase 6 (B-cluster checks mode for clipability publication), HSEA Phase 9 (H6 revenue overlay default-hidden in `public`) | LRR owns the axis. HSEA reads. |
| 11 | `it-irreversible-broadcast` implication + `sp-hsea-mg-001` precedent | **LRR Phase 6** (item 1) bundled with HSEA Phase 0 0.5 deliverable | Both epics consume | These are the same governance work split across two specs. Single PR vehicle to `hapax-constitution`. HSEA Phase 0 drafts the precedent YAML; LRR Phase 6 ships both as one PR. |
| 12 | `ConsentGatedWriter` for Qdrant (FINDING-R) | **LRR Phase 6** (item 3) | HSEA Phase 5 M2 (retrieval-augmented memory), HSEA Phase 11 G6 (voice-session parallel scoring) | LRR ships the gate. HSEA's later phases call it. |
| 13 | Per-condition Prometheus slicing | **LRR Phase 10** (item 1) | HSEA Phase 1 (1.1 HUD overlay) reads the same series; HSEA Phase 5 M1 (HRV strip) plumbed into the same scrape; HSEA Phase 7 D2 anomaly narration reads | Cardinality budget owned by LRR. HSEA queries via `shared/prom_query.py` (HSEA Phase 0 0.1 deliverable, no overlap). |
| 14 | Stream content surfaces (Cairo overlays, Sierpinski slots, content zones) | **HSEA owns the new surfaces; LRR Phase 8 owns objective-overlay + research-mode tiles** | LRR Phase 8 surfaces (objective overlay, Logos studio view tile, terminal capture tile, PR/CI status overlay) become HSEA-pluggable surfaces. HSEA Phase 1 uses LRR Phase 8's `OutputRouter`/`SourceRegistry` registration pattern. | LRR ships the registration mechanism (Phase 2 item 10 + Phase 8); HSEA writes new sources against it. |
| 15 | Daimonion code-narration / closed loop | **LRR Phase 9** (items 4, 9) — `/dev/shm/hapax-editor-state.json`, `git-state.json`, `ci-state.json` SHM publishers | HSEA Phase 7 D-cluster (FSM recovery narration consumes; alert triage reads); HSEA Phase 11 G15 CI-watch triager extends | LRR ships the publishers. HSEA's anomaly/recovery narration reads them. |
| 16 | `attention bid` mechanism | **LRR Phase 8** (item 10) | HSEA Phase 5 M1 (biometric proactive intervention reuses the attention-bid channel for HRV nudges) | One channel, multiple producers. LRR builds it. |
| 17 | Spawn budget ledger + governance queue | **HSEA Phase 0** (deliverables 0.2, 0.3) | LRR Phase 5 (Hermes swap rate-limited via `check_can_spawn`); LRR Phase 8 objective-driven LLM calls routed through ledger; LRR Phase 9 closed-loop reactor calls budgeted | HSEA owns. LRR consumes. This is the inverse of most other rows. |
| 18 | `promote-*.sh` scripts + `~/Documents/Personal/00-inbox/` flow | **HSEA Phase 0** (deliverable 0.4) | LRR Phase 4 (OSF pre-reg artifact routes through inbox); LRR Phase 6 (constitutional amendments use `promote-axiom-precedent.sh`); LRR Phase 8 (objective edits via inbox) | HSEA owns. LRR consumes. |
| 19 | Glass-box prompt rendering (HSEA 1.3) | **HSEA Phase 1** | LRR Phase 7 persona spec consumed *by* the glass-box renderer for visibility | HSEA owns surface; LRR owns content. |
| 20 | Research-mode tile inventory (Logos studio view, terminal capture, PR/CI status) | **LRR Phase 8** (item 9) | HSEA Phase 1 1.4/1.5/1.6 are different surfaces (HUD, research state broadcaster, governance queue overlay) — no overlap with LRR Phase 8 item 9 if naming kept distinct | Distinct surfaces; document separately to prevent re-implementation drift. |

**Anti-pattern to prevent:** any HSEA file that begins `# Owner: delta` and reimplements something LRR Phase 1 already declares as owned. Sessions picking up HSEA Phase 0 must read this table before writing any code.

---

## 4. 70B vs 8B substrate swap resolution

### The conflict

LRR Phase 5 (lines 531–629 of LRR spec) executes Hermes 3 70B EXL3 3.0bpw via dual-GPU layer split, drops `max_seq_len` to 4096, evicts `hapax-dmn` to GPU 0, and treats this as the canonical Condition A → A' transition. The exit criteria include consent-revocation latency drill (≤500ms over pre-migration envelope) and speech-continuity drill (zero dropped frames during long generation).

HSEA Phase 4 cluster I, sub-drafters I4a/I4b/I4c (drop #58 thesis, drop #59 audit), splits the **8B parallel-pivot** from drop #57 T2.6 into three independent code drafters:
- I4a `t2_6a_tabby_config` — second-instance TabbyAPI config
- I4b `t2_6b_litellm_routes` — additive `local-fast-hermes` / `coding-hermes` / `reasoning-hermes` routes
- I4c `t2_6c_pipeline_dispatch` — `conversation_pipeline.py` dispatch on `active_model_family` field

Drop #56 v3 already established that **the 70B path is unreachable under the operator's `interpersonal_transparency` consent-latency axiom**: 70B layer-split inference on Blackwell+Ampere cannot meet the <2s consent-revocation round-trip the constitutional axiom requires. Drop #57 T2.6 reified this as "8B parallel, not swap." HSEA Phase 4 I4 codifies the implementation. LRR Phase 5 was authored before delta absorbed drop #56 v3 into the LRR scope and still nominally targets 70B-as-swap.

### The three options

(a) **Replace LRR Phase 5 with the 8B pivot, defer 70B to a future epic.** Clean, but loses LRR Phase 5's exit criteria (which are the right exit criteria for *any* substrate change, not just 70B).

(b) **Keep LRR Phase 5 as written; HSEA Phase 4 I4 ships it with explicit axiom-precedent update.** Worst option — HSEA Phase 4 is not the right place to ship a substrate swap; it's a drafter, not a deployer. Also fails to acknowledge that the consent-latency axiom already says 70B is wrong.

(c) **Fork LRR Phase 5 into 5a (8B parallel) and 5b (70B, gated on hardware/quant changes).** Recommended.

### Recommendation: option (c) with HSEA Phase 4 I4 demoted to narration-only

- **Unified Phase 5a (was LRR Phase 5):** Hermes 3 8B parallel pivot. Owner: **LRR**, not HSEA. This is research-validity-load-bearing work; LRR is the authoritative epic. The 8B pivot is the *implementation* of T2.6 / drop #56 v3 inside the LRR sequence. LRR Phase 5a inherits all of LRR Phase 5's exit criteria (consent-revocation drill, speech-continuity drill, CAPABLE-tier preservation) but executes them against the 8B parallel config.
- **Unified Phase 5b (deferred):** Hermes 3 70B path. Gated on either (i) different hardware (PCIe Gen 5 dual-Blackwell, single-card 80GB Blackwell, or similar) or (ii) sub-2s 70B inference demonstrated empirically. Until then, 5b is a backlog item, not an LRR phase.
- **HSEA Phase 4 cluster I4:** rescoped from "Hapax drafts the 8B pivot code" to "Hapax narrates LRR Phase 5a's 8B pivot landing, drafts a research drop summarizing the substrate change, and routes the drop through the governance queue." The three sub-drafters become a single composite spectator narrator. Saves ~600 LOC of duplicate code.
- **Axiom precedent action:** LRR Phase 6 governance pass formalizes the rule: "any future 70B substrate decision must pre-register a consent-revocation drill and pass it before being authorized." Goes into the same `it-irreversible-broadcast` PR vehicle.
- **OSF pre-registration:** the OSF amendment (drop #57 T2.7, current LRR Phase 4 item 4) explicitly names the 8B arm as the C2 condition; the original 70B language is replaced or annotated.
- **DEVIATION-037:** still filed, but its content is the 8B pivot rationale + reference to drop #56 v3 + reference to the consent-latency axiom, not the 70B procedure.

**Why option (c):** it preserves LRR's research integrity machinery, surfaces drop #56 v3 as a binding axiom decision rather than buried research, eliminates the duplicate substrate code in HSEA Phase 4 I4, and leaves a clear path back to 70B if the hardware envelope changes. It also makes the LRR/HSEA boundary cleaner: LRR ships substrate, HSEA narrates it.

---

## 5. Unified phase sequence

The merged sequence has **14 unified phases (UP-0 through UP-13)**. Each phase declares its source phase(s), owner epic, shared state surfaces, and dependencies.

| Unified phase | Source phases | Owner epic | Shared state read/written | Dependencies | Sessions / LOC est. |
|---|---|---|---|---|---|
| **UP-0 Verification & primitives bootstrap** | LRR Phase 0 + HSEA Phase 0 deliverables 0.6 + 0.1 | LRR Phase 0 first; HSEA 0.6 (state file) and 0.1 (`prom_query.py`) ride along | Creates `lrr-state.yaml`, `hsea-state.yaml`, `research-stream-state.yaml` index | — | 2 sessions, ~700 LOC |
| **UP-1 Research registry foundation** | LRR Phase 1 (all 10 items) + HSEA Phase 0 deliverable 0.5 (axiom precedent draft, deferred submission to UP-7) | LRR Phase 1 | Owns `~/hapax-state/research-registry/`, frozen-files hook, condition_id, stats.py BEST | UP-0 | 2-3 sessions, ~1400 LOC |
| **UP-2 Foundation primitives (HSEA core)** | HSEA Phase 0 deliverables 0.2 (governance queue), 0.3 (spawn budget), 0.4 (promote scripts) | HSEA Phase 0 | Owns `governance-queue.jsonl`, `spawn-budget.jsonl`, `promote-*.sh`, `00-inbox/` schema | UP-0, UP-1 (frozen-files probe depends on UP-1) | 2 sessions, ~2100 LOC |
| **UP-3 Archive instrument** | LRR Phase 2 (all 10 items including layout-declared `video_out`) | LRR Phase 2 | Writes `~/hapax-state/stream-archive/`, segment sidecars, `OutputRouter` registration, archive-search CLI | UP-1 | 2-3 sessions, ~1500 LOC |
| **UP-4 Visibility surfaces** | HSEA Phase 1 (all 5 surfaces) | HSEA Phase 1 | Reads UP-1 condition data, UP-3 archive metadata, UP-2 governance queue, UP-0 prom_query | UP-1, UP-2, UP-3 | 2-3 sessions, ~1200 LOC |
| **UP-5 Hardware validation + Hermes 8B prep** | LRR Phase 3 (rescoped: gpu_split for 8B parallel, no eviction of `hapax-dmn` needed) | LRR Phase 3 | Updates systemd unit GPU pins, downloads Hermes 3 8B EXL3 5.0bpw quant, drafts TabbyAPI config | UP-1 | 1-2 sessions, ~300 LOC + systemd config |
| **UP-6 Phase A completion + OSF pre-reg** | LRR Phase 4 (all items, with OSF amendment naming 8B as C2 arm per drop #56 v3) | LRR Phase 4 | Locks Condition A data; writes OSF URL into condition.yaml | UP-1 (registry), UP-5 (hardware ready) | Time-gated: 1–2 weeks operator |
| **UP-7 Hermes 3 8B parallel substrate (resolved §4)** | **LRR Phase 5a** (was LRR Phase 5; 8B path); HSEA Phase 4 I4 demoted to narration-only | LRR Phase 5a | Opens `cond-phase-a-prime-hermes-8b-002` in registry; files DEVIATION-037; runs consent-revocation + speech-continuity drills | UP-5, UP-6 | 2 sessions |
| **UP-7' (deferred backlog)** | LRR Phase 5b (70B path) | Future epic | — | Hardware envelope change | — |
| **UP-8 Governance finalization** | LRR Phase 6 (all 11 items) + HSEA Phase 0 0.5 axiom precedent (`sp-hsea-mg-001`) bundled into one `hapax-constitution` PR | LRR Phase 6 | Ships `hapax-stream-mode` CLI, `it-irreversible-broadcast` + `sp-hsea-mg-001` + `mg-drafting-visibility-001` + `su-privacy-001` clarification + `corporate_boundary` clarification, `ConsentGatedWriter`, presence-detect closed loop, fortress retirement | UP-7 | 2-3 sessions |
| **UP-9 Persona spec** | LRR Phase 7 (all 7 items) | LRR Phase 7 | Writes `axioms/persona/hapax-livestream.yaml`; persona becomes part of frozen-files manifest; HSEA glass-box renders it | UP-7, UP-8 | 1-2 sessions, multi-iteration |
| **UP-10 Core director activities** | HSEA Phase 2 (`draft`, `reflect`, `critique`, `patch`, `compose_drop`, `synthesize`, `exemplar_review`); ReflectiveMomentScorer with 7-day calibration | HSEA Phase 2 | Extends `ACTIVITY_CAPABILITIES`; reads UP-9 persona; respects UP-2 budget | UP-2, UP-9 | 3 sessions, ~2500 LOC |
| **UP-11 Content programming + objectives + closed loop** | LRR Phase 8 + LRR Phase 9 + HSEA Phase 3 (research orchestration) | LRR Phases 8 + 9 own infra; HSEA Phase 3 owns C-cluster narration on top | Writes `~/Documents/Personal/30-areas/hapax-objectives/`; ships `objective-overlay`, hero mode, Stream Deck, YouTube description auto-update, attention bids; ships `chat-signals.json`, daimonion code-narration, async chat queue, scientific captions, voice-over-YouTube ducking, SHM editor/git/ci publishers | UP-3, UP-10 | 5–7 sessions, ~4000 LOC |
| **UP-12 HSEA execution clusters (parallelizable)** | HSEA Phase 4 (rescoped per §4: I1–I3, I5–I7 only; I4 is narration-only and folded into UP-7), Phase 5 (M-series biometric/studio/archival), Phase 6 (B clip mining), Phase 7 (D self-monitor), Phase 8 (E platform value), Phase 9 (H revenue) | HSEA owns each cluster | Each cluster reads UP-1 registry, UP-2 governance queue, UP-2 spawn budget, UP-11 objectives | UP-10 + UP-11 | Parallelizable across alpha + beta worktrees; ~10–15 sessions total, ~13000 LOC |
| **UP-13 Observability + reflexive + spawner + handoff** | LRR Phase 10 + HSEA Phase 10 (reflexive F-cluster) + HSEA Phase 11 (G spawner) + HSEA Phase 12 (long-tail handoff) | LRR Phase 10 owns observability; HSEA owns reflexive + spawner + handoff | Per-condition Prom slicing; stimmung dashboards; 18-item stability matrix; 6 drills + 2-hour stability; FINDING-S decision; T3 prompt caching; cross-repo scrape fixes; F2-F14 reflexive layers (F10 ships first per drop #59); G1-G16 spawn-based touch points; epic close handoff | UP-11, UP-12 | 6–8 sessions, ~6000 LOC |

**Total:** 14 unified phases, 30–45 sessions across 6–10 weeks, ~33,000 LOC. Most parallelism lives in UP-12 (which is intentionally a basket of independent clusters that beta and alpha can split).

**Critical execution note:** UP-7 is the only phase that has a hard predecessor chain. Everything else can be reordered locally if a session has reason to pick a different next phase. The unified state file (§6) supports that.

---

## 6. State file integration design

### Recommendation: sibling files under a shared index

```
~/.cache/hapax/relay/
├── research-stream-state.yaml      # NEW: shared index, single source of truth for which epics are live
├── lrr-state.yaml                  # owned by LRR sessions, cross-referenced from index
├── hsea-state.yaml                 # owned by HSEA sessions, cross-referenced from index
└── alpha.yaml | beta.yaml          # session-level state, unchanged
```

**Why not a single unified file:** LRR and HSEA can have simultaneously active phases (HSEA Phases 5–9 parallelize while LRR is still in Phase 4 collection or Phase 10 observability). A single file imposes a single-writer constraint that destroys the parallelism. Worse, sessions would have to merge concurrent edits, which the relay protocol does not support.

**Why not entirely separate files (current HSEA plan assumption):** sessions picking up either epic must read both files to know whether their work is blocked by cross-epic dependencies. The shared index encodes those dependencies machine-readably.

### `research-stream-state.yaml` schema

```yaml
schema_version: 1
authored_at: 2026-04-14T00:00:00Z

epics:
  lrr:
    state_file: ~/.cache/hapax/relay/lrr-state.yaml
    spec_doc: docs/superpowers/specs/2026-04-14-livestream-research-ready-epic-design.md
    plan_doc: docs/superpowers/plans/2026-04-14-livestream-research-ready-epic-plan.md
    status: active             # active | paused | retired
    current_phase_ref: lrr.current_phase    # path into lrr-state.yaml
  hsea:
    state_file: ~/.cache/hapax/relay/hsea-state.yaml
    spec_doc: docs/superpowers/specs/2026-04-14-hsea-epic-design.md
    plan_doc: docs/superpowers/plans/2026-04-14-hsea-epic-plan.md
    status: active
    current_phase_ref: hsea.current_phase

unified_sequence:
  # Mirrors §5 of drop #62. Sessions read this to understand cross-epic ordering.
  - id: UP-0
    name: Verification & primitives bootstrap
    sources: [lrr.phase_0, hsea.phase_0_deliverables_0_6_0_1]
    owner: lrr
    status: open                # open | in_progress | closed
  - id: UP-1
    name: Research registry foundation
    sources: [lrr.phase_1, hsea.phase_0_deliverable_0_5_draft]
    owner: lrr
    status: pending
    blocks: [UP-2, UP-4, UP-7, UP-12.hsea_phase_4]
  # ... through UP-13

cross_epic_dependencies:
  - producer: lrr.phase_1.frozen_files_hook
    consumer: hsea.phase_0.frozen_files_probe_extension
    interface: scripts/check-frozen-files.{sh,py}
    status: pending
  - producer: lrr.phase_1.condition_id_tagging
    consumer: hsea.phase_3.research_state_broadcaster
    interface: /dev/shm/hapax-compositor/research-marker.json
    status: pending
  - producer: hsea.phase_0.governance_queue
    consumer: lrr.phase_5.deviation_037_routing
    interface: ~/hapax-state/governance-queue.jsonl
    status: pending
  - producer: hsea.phase_0.spawn_budget
    consumer: lrr.phase_8.objective_llm_calls
    interface: shared/budget_ledger.check_can_spawn
    status: pending
  - producer: lrr.phase_6.it_irreversible_broadcast
    consumer: hsea.phase_4.code_drafter_consent_scan
    interface: hapax-constitution axiom registry
    status: pending
  - producer: lrr.phase_7.persona_yaml
    consumer: hsea.phase_1.glass_box_prompt
    interface: axioms/persona/hapax-livestream.yaml
    status: pending

substrate_decision:
  resolved: true
  resolution_doc: docs/research/2026-04-14-cross-epic-fold-in.md  # this drop
  active_substrate_path: hermes_3_8b_parallel
  deferred_paths:
    - hermes_3_70b_layer_split   # gated on hardware envelope change
  authoritative_phase: UP-7

last_modified: 2026-04-14T00:00:00Z
```

**Concurrency rules:**
1. Index file is read-only for execution sessions; only the cross-epic coordinator (alpha during fold-in, then operator) edits it.
2. Each `<epic>-state.yaml` is single-writer (the session that holds `current_phase_owner`), append-friendly via atomic tmp+rename.
3. `session-context.sh` reads all three files and surfaces a unified status line: `LRR: phase 4 (alpha) | HSEA: phase 5 (beta) | UP: 6,12 active`.
4. When either epic closes a phase, the closing session updates both that epic's state file AND the shared index `unified_sequence[N].status`.

**Backwards compatibility:** existing LRR plan and HSEA plan documents reference single state files. They continue to work — the index is a *new layer above*, not a replacement. Sessions that don't know about the index file are no worse off than they are today.

---

## 7. Resource conflict resolutions

| Resource | Conflict | Resolution |
|---|---|---|
| **Operator attention (review queue)** | HSEA budget projects 5–15 inbox items/day at steady state, peaking 20–30 during Phase 4 code-drafting weeks. LRR Phase 4 OSF pre-reg + Phase 5 substrate swap + Phase 6 governance amendments + Phase 7 persona iteration cycles add another ~10 items/week. Combined steady-state peak: ~40 items/day. | **Sequenced, not parallel.** UP-6 (Phase A collection, time-gated by operator voice sessions) is the natural "operator attention low" window for HSEA Phase 0 + UP-2 + UP-4 ramp. Defer UP-12's Cluster I drafters until UP-9 + UP-10 are stable so the operator isn't reviewing persona iterations and code patches in the same week. **Hard cap: 10 inbox items/day during UP-6 voice-collection window**, enforced via spawn-budget per-touch-point caps in HSEA Phase 0 0.3. |
| **Worktree slots (max 4 per hook policy)** | alpha + beta + delta + 1 spontaneous. LRR plan assumes serial single-worktree; HSEA plan assumes alpha + beta parallel on Phases 5–9. | **Allocation:** alpha = active LRR phase. beta = active HSEA UP-12 cluster (one at a time). delta = research-only, no code-writing per global CLAUDE.md subagent git safety. spontaneous = reserved for cross-cutting bug fixes, never for HSEA or LRR phases. |
| **Branch names** | `feat/lrr-phase-N-*` and `feat/hsea-phase-N-*` are already disambiguated. Risk: HSEA Phase 4 cluster I creates ~7 sub-branches; LRR Phase 8 has multiple sub-deliverables. | Add convention: every sub-branch must include the unified phase ID: `feat/up-7-lrr-phase-5a-hermes-8b`, `feat/up-12-hsea-i5-guardrail`. Sessions self-discover the ID from `research-stream-state.yaml::unified_sequence`. |
| **LLM budget ($5/day)** | HSEA Phase 0 0.3 ledger enforces global cap. But LRR Phases 5–10 also make LLM calls (Hermes 3 swap eval, persona testing, closed-loop reactor, weekly correlation report). LRR currently does NOT route through the ledger. | **Resolution:** during UP-2 (HSEA Phase 0 0.3 deliverable), retrofit LRR's LLM call sites to route through `check_can_spawn(touch_point="lrr-<phase>-<purpose>")`. This is one helper import line per call site; ~6–10 sites total. Spawn budget then reflects total epic spend, not just HSEA. **Per-epic sub-caps:** allocate $2/day to LRR (research, persona, closed loop), $3/day to HSEA (drafting). Operator-adjustable. |
| **Compositor deployment slots / Cairo sources** | LRR Phase 8 ships objective overlay, Logos studio view tile, terminal capture tile, PR/CI status overlay. HSEA Phase 1 ships HUD, research state broadcaster, glass-box prompt, orchestration strip, governance queue overlay. Total: 9 new Cairo sources. | LRR Phase 2 item 10 already mandates layout-declared `video_out` migration. Make Cairo source registration go through the new `SourceRegistry` from day one. Each new source is a JSON entry in `config/compositor-layouts/default.json`. **No conflict** as long as zone allocation is documented; add a "zones registry" file at `config/compositor-zones.yaml` that lists every zone and its source. UP-3 ships the registry; UP-4 and UP-11 add their entries. |
| **Director loop activity space** | HSEA Phase 2 expands `ACTIVITY_CAPABILITIES` from 6 → 13. LRR Phase 8 adds objective-advancement scoring on top of the existing 6 activities. LRR Phase 9 adds stimmung-modulated activity selection. | **Order:** UP-10 (HSEA Phase 2 activity expansion) lands before UP-11 (LRR Phase 8 objective scoring + LRR Phase 9 closed loop). LRR Phase 8 / 9 must be aware of the 13-activity taxonomy when computing `objective_advancement_score(a)`. The scoring formulas in LRR Phase 8 item 3 must include the new activities. |
| **Frozen-files manifest churn** | Every condition's frozen-files manifest grows when LRR Phase 7 adds the persona file. HSEA Phase 4 cluster I drafters must respect the active manifest, including the persona file. | **Hard rule:** any HSEA drafter that touches a file in the current condition's frozen-files manifest is required to draft a DEVIATION-NNN inline as part of the patch bundle, and the operator approves DEVIATION + patch as one inbox item, not two. Enforced by `promote-patch.sh`. |

---

## 8. Drop #57 ownership map

Drop #57 has 38 ranked tactics across 5 tiers. For each critical-path tactic, ownership is now declared. The convention:
- **LRR-OWNED:** the tactic is implementation work that LRR phases ship. HSEA may narrate but does not duplicate.
- **HSEA-OWNED:** the tactic is content-execution work that HSEA phases ship.
- **OPERATIONAL:** the tactic is operator-only or external (revenue, distribution, hardware).
- **SHARED:** the tactic spans both — both phases must coordinate.

| Tactic | Description | Owner | Notes |
|---|---|---|---|
| **T1.1** | Deploy FDL-1 fix | OPERATIONAL | Pre-epic; mobo swap recovery; not in scope of either epic. |
| **T1.2** | Phase 4 PR landing (beta worktree bootstrap) | LRR-OWNED → **UP-1** | This IS LRR Phase 1 + Phase 4 execution. HSEA references it but does not ship code. |
| **T1.3** | PyMC 5 BEST port | LRR-OWNED → **UP-1** (item 7) | LRR Phase 1 owns the port. HSEA Phase 4 I1 drafter is rescoped to narration only (drafts a research drop summarizing the port; the port itself is LRR work). |
| **T1.4** | output-freshness Prometheus gauge | LRR-OWNED → **UP-13** (Phase 10 observability) | Could ship earlier as Phase 0 polish. **Not** an HSEA touch point. |
| **T1.5** | fd_count + RSS Prometheus gauges | LRR-OWNED → **UP-13** | Same. |
| **T1.6** | Wire `YOUTUBE_VIDEO_ID` at stream start | LRR-OWNED → **UP-0** (LRR Phase 0 item 1 implicit fix; chat-monitor fix depends on it) | Cheap fix; ride along with chat-monitor repair. |
| **T1.7** | Stimmung-gated director activity prior | LRR-OWNED → **UP-11** (LRR Phase 9 closed loop) | HSEA Phase 4 I2 drafter is rescoped to narration only. The activity prior IS LRR Phase 9 item 2. |
| **T1.8** | AI content disclosure baked into broadcast | LRR-OWNED → **UP-8** (LRR Phase 6 governance) | Stream-start AI disclosure is a governance overlay; LRR Phase 6 ships it. |
| **T2.1** | Attribution integrity daily audit timer | LRR-OWNED → **UP-1** (closely related to Phase 1 backfill verification) or **UP-13** | Move into UP-1 because it is the integrity check that protects Condition A. |
| **T2.2** | Burst-with-gaps director cadence | LRR-OWNED → **UP-11** (LRR Phase 9 + Phase 10 PERCEPTION_INTERVAL tuning) | HSEA Phase 4 I3 drafter is rescoped to narration only. |
| **T2.3** | Director persona + exemplars + anti-patterns | LRR-OWNED → **UP-9** (LRR Phase 7 persona spec authoring) | Persona is LRR's domain. The exemplars + antipatterns YAML files are HSEA Phase 0 deliverables (`shared/exemplars.yaml`, `shared/antipatterns.yaml`); they are *populated* by LRR Phase 7. |
| **T2.4** | Visible research condition diegetic overlay | SHARED → **UP-4** (HSEA Phase 1 1.2 research state broadcaster) | HSEA owns the surface; LRR owns the underlying condition data. |
| **T2.5** | Clipability score per reaction + Obsidian export | HSEA-OWNED → **UP-12** (HSEA Phase 6 B-cluster) | New work, no LRR overlap. |
| **T2.6** | 8B pivot as parallel TabbyAPI config | **LRR-OWNED → UP-7 (was LRR Phase 5; resolved §4)** | Critical: rescoped from "swap" to "parallel pivot" per drop #56 v3. HSEA Phase 4 I4 demoted to narration. |
| **T2.7** | OSF pre-registration amendment | LRR-OWNED → **UP-6** (LRR Phase 4 item 4) | Operator action; LRR Phase 4 sequences it. |
| **T2.8** | LLM output guardrail layer | LRR-OWNED → **UP-9** (persona) or **UP-13** (Phase 10 polish) | Should land alongside the persona spec because both shape utterance behavior. HSEA Phase 4 I5 drafter is rescoped to narration only — actual guardrail code is LRR work because it touches `conversation_pipeline.py`, which is FROZEN under the current condition. The DEVIATION must be filed by the LRR session that opens the new condition. |
| **T3.1** | Zero-touch clip-mining pipeline | HSEA-OWNED → **UP-12** (HSEA Phase 6) | New work. |
| **T3.2** | Cross-platform auto-publish | HSEA-OWNED → **UP-12** (HSEA Phase 6) + **OPERATIONAL** (Publer setup) | HSEA owns the daemon; operator handles platform credentials. |
| **T3.3** | Reflexivity overlay | HSEA-OWNED → **UP-4** (HSEA Phase 1 1.3 glass-box prompt) | HSEA owns. |
| **T3.4** | HN research drop + live status page | HSEA-OWNED + OPERATIONAL → **UP-12** (HSEA Phase 6 / E-cluster) | HSEA Phase 8 E-cluster ships the live status page; operator writes the post. |
| **T3.5** | Sequenced community launches | OPERATIONAL | — |
| **T3.6** | Stimmung × activity preset routing | LRR-OWNED → **UP-11** (LRR Phase 9 closed loop) | LRR Phase 9 ships it. |
| **T3.7** | Scheduled scarce operator cameos | OPERATIONAL | — |
| **T3.8** | `reflect` director activity | HSEA-OWNED → **UP-10** (HSEA Phase 2 activity expansion) | New activity; HSEA Phase 2 owns. |
| **T3.9** | Session protocol batching | LRR-OWNED → **UP-6** (LRR Phase 4) | Phase A operator-collection cadence. |
| **T3.10** | GitHub Sponsors / Ko-fi / Nostr | OPERATIONAL + HSEA-OWNED → **UP-12** (HSEA Phase 9 H1 sponsor copy drafter) | HSEA drafts the copy; operator deploys. |
| **T3.11** | NLnet NGI0 grant | OPERATIONAL + HSEA-OWNED → **UP-12** (HSEA Phase 9 H2) | HSEA drafts the grant; operator submits. |
| **T4.1** | Weekly drops digest + lab notebook | HSEA-OWNED → **UP-12** (HSEA Phase 8 E-cluster) | New work. |
| **T4.2** | Reframe drops with run framing | OPERATIONAL (writing convention) | No code. |
| **T4.3** | Pre-announced substrate swap event | SHARED → **UP-7** (substrate swap) + HSEA Phase 3 C8 (spectator narration) | LRR ships the swap; HSEA narrates. |
| **T4.4** | RESEARCH.md top-level | HSEA-OWNED → **UP-12** (HSEA Phase 8 E1) | New work. |
| **T4.5** | Cognitive prosthetic surfaces | HSEA-OWNED → **UP-12** (HSEA Phase 5 M-series + Phase 8 E-cluster) | M1, M2, M5 cover this. |
| **T4.6** | Three-cell confound design | LRR-OWNED → **UP-6** (Phase 4 OSF amendment names the aux cell) | LRR Phase 4 item 4 must be extended to include the aux cell rationale. |
| **T4.7** | Music-aware commentary | LRR-OWNED → **UP-11** (LRR Phase 9) or HSEA-OWNED → **UP-12** (Phase 5 M3 studio creative-state) | Slight overlap. **Resolution:** HSEA Phase 5 M3 owns the studio creative-state daemon; LRR Phase 9 wires the music-aware reactor signal into stimmung. |
| **T4.8** | YouTube backup ingest URL | HSEA-OWNED → **UP-12** (HSEA Phase 4 I6 drafter) | But the actual `rtmp_output.py` is in `agents/studio_compositor/` and may be frozen. **Resolution:** I6 drafter is allowed if `rtmp_output.py` is not in the active condition's frozen-files manifest (verify in UP-1). If frozen, defer to a DEVIATION cycle. |
| **T4.9** | External watchdog classes | LRR-OWNED → **UP-13** (Phase 10 observability + drills) | New systemd units; LRR Phase 10 owns. |
| **T4.10** | Governance framework spin-off | OPERATIONAL + HSEA-OWNED → **UP-12** (HSEA Phase 8 E4 spin-off doc drafter) | HSEA drafts; operator publishes. |
| **T4.11** | Time-of-day rituals | HSEA-OWNED → **UP-12** (HSEA Phase 4 I7 drafter; the only I-drafter that survives §4 unchanged) | I7 actually writes new ritualized state code; not a duplicate of LRR. |
| **T4.12** | Consent-first face redaction | LRR-OWNED → **UP-8** (LRR Phase 6 governance) | Existing governance closed loop in LRR Phase 6. |

**Tally:**
- LRR-owned: 22 tactics
- HSEA-owned: 11 tactics
- Operational: 5 tactics

**Critical insight:** of HSEA Phase 4 cluster I's 7 sub-drafters (I1–I7), **only I7 (T4.11 ritualized states) survives §4 unchanged**. I1, I2, I3, I4, I5 all become narration-only spectator drafters because the underlying code work is LRR-owned. I6 (T4.8 YouTube tee) is conditional on whether `rtmp_output.py` is frozen. **HSEA Phase 4 should be rescoped from "Hapax drafts critical-path code" to "Hapax narrates LRR's critical-path code landings + drafts T4.11 + T4.8."** Rough LOC delta: ~−2400 from HSEA Phase 4.

---

## 9. Recommended HSEA spec edits

### Edits to `docs/superpowers/specs/2026-04-14-hsea-epic-design.md`

**Section 0 (Headline):** add a paragraph after the "End-state" sentence:

> **Cross-epic relationship.** HSEA does not own the research substrate, the persona spec, the governance amendments, the closed-loop wiring, the per-condition observability, or the substrate swap. Those are all LRR scope. HSEA's role is to (a) ship the shared content-execution primitives (governance queue, spawn budget, promote scripts), (b) ship the visibility surfaces that make LRR's work into stream content, and (c) ship the new work that LRR does not touch (clip mining, revenue preparation, M-series biometric/studio/archival, reflexive content). Drop #62 (cross-epic fold-in) is the authoritative dependency map.

**Section 1 (Prior art):** the row "LRR epic — Parallel, dependency-coupled" needs a stronger tie. Replace the existing description with:

> HSEA is structurally a content-execution layer above LRR. LRR ships the substrate (registry, archive, governance, persona, observability, closed loop). HSEA reads all of LRR's outputs and renders them as visible drafting work routed through an operator-controlled approval queue. The two epics share five primitive families (frozen-files, condition_id, research-marker, research-registry CLI, persona); LRR owns all five and HSEA reads them. See drop #62 §3 for the canonical ownership table.

**Section 2 (Pre-epic verification findings) → Missing primitives subsection:** add a note above the list:

> Several of these primitives are now LRR-owned per drop #62: `scripts/check-frozen-files.py` (LRR Phase 1 item 4) and the persona file (LRR Phase 7) are NOT HSEA Phase 0 deliverables. HSEA Phase 0 still owns: governance queue, spawn budget, promote scripts, axiom precedent draft, and epic state file. The frozen-files probe extension lands as a thin wrapper after LRR Phase 1 merges.

**Section 4 (Phase summary), Phase 4 row:** rewrite the goal:

> ~~Per-task drafters for T1.3 PyMC 5 BEST, T1.7 stimmung prior, T2.2 burst cadence, T2.6 8B pivot (3 sub-drafters), T2.8 guardrail, T4.8 YouTube tee, T4.11 ritualized states~~
>
> **Replacement:** Per-task drafters for the subset of drop #57 tactics that LRR does not own. After fold-in: I6 (T4.8 YouTube tee, if `rtmp_output.py` is not frozen) and I7 (T4.11 ritualized states). All other I-drafters become narration spectator agents that watch LRR phases and draft research drops summarizing the LRR work as it lands; the original code generation for I1, I2, I3, I4, I5 is owned by LRR phases 1, 9, 9, 5a, and 7 respectively.

**Section 5, Phase 4 spec:** rewrite 4.3 list (Per-task drafter subclasses) to reflect the rescoping. Drop I1 / I2 / I3 / I4a-c / I5 from the per-task drafter list; add a new subsection 4.3' "Spectator narrator drafters" that handles them as stream-content-only.

**Section 5, Phase 5 spec (M-series):** no edits needed; the M-series is genuinely additive and does not collide with LRR.

**Section 5, Phase 9 (Revenue):** no edits; entirely HSEA-owned.

**Section 6 (Constitutional axiom precedent):** add a note:

> **PR vehicle:** This precedent ships in the same `hapax-constitution` PR as LRR Phase 6's `it-irreversible-broadcast` implication, `su-privacy-001` clarification, and `corporate_boundary` clarification. HSEA Phase 0 deliverable 0.5 drafts the YAML; LRR Phase 6 (UP-8) opens the PR. Operator review is one cycle covering all three pieces, not two.

**Section 8 (Execution invariants):** add an invariant:

> - **Cross-epic dependency check.** Any HSEA phase that depends on an LRR phase output (per drop #62 §3 ownership table) MUST verify the LRR phase has reached `closed` status in `lrr-state.yaml` before opening. The `research-stream-state.yaml` index file is the canonical lookup.

### Edits to `docs/superpowers/plans/2026-04-14-hsea-epic-plan.md`

**Section 1 (Execution model):** add to the invariants list:

> - **Read `research-stream-state.yaml` before reading `hsea-state.yaml`.** The index file declares cross-epic dependencies that block phase opens.

**Section 3 (Phase dependency graph):** the diagram needs LRR cross-edges. Replace with:

```
                 LRR UP-0 (verification + state files) ─┐
                          │                              │
                          v                              │
                    LRR UP-1 (registry) ──────► HSEA UP-2 (foundation primitives)
                          │                              │
              ┌───────────┼──────────┐                   │
              v           v          v                   v
        LRR UP-3     LRR UP-5    LRR UP-6           HSEA UP-4 (visibility)
        (archive)    (HW prep)   (Phase A)               │
              │           │          │                   │
              └───────────┴──────────┴────► LRR UP-7 (8B substrate, resolved §4)
                                                     │
                                                     v
                                              LRR UP-8 (governance) [+HSEA precedent]
                                                     │
                                                     v
                                              LRR UP-9 (persona)
                                                     │
                                                     v
                                            HSEA UP-10 (activities) ──► UP-11 (objectives + closed loop)
                                                                              │
                                                                              v
                                              ┌───────────────────────────────┴─────────────────────────────┐
                                              │              UP-12 (parallelizable cluster basket)            │
                                              │  HSEA Phase 4 (rescoped)  HSEA Phase 5 (M)  HSEA Phase 6 (B) │
                                              │  HSEA Phase 7 (D)         HSEA Phase 8 (E)  HSEA Phase 9 (H) │
                                              └───────────────────────────────┬─────────────────────────────┘
                                                                              v
                                              UP-13 (LRR Phase 10 + HSEA Phase 10/11/12 + handoff)
```

**Section 4 (Per-phase execution briefs), Phase 4 brief:** change the duration from 5 sessions to 2–3 sessions, change the deliverable list per the spec rescoping, and add: "Phase 4 cannot open until LRR UP-7 has merged."

**Section 8 (Cross-epic coordination):** rewrite. The current text is too vague. Replace with a reference to drop #62 §3 ownership table and §6 state file design.

**Section 11 (Resource budget):** revise LOC estimate from ~29,000 to ~25,000–27,000 (subtracting the rescoped Phase 4 LOC). Revise daily inbox load estimate to reflect the dependency: 5–15 items/day at steady state, with hard cap 10/day during UP-6 voice-collection windows.

---

## 10. Open questions for operator review

1. **Substrate swap path:** confirm the recommendation in §4 (option c — fork into 5a 8B and deferred 5b 70B). The alternative is to keep LRR Phase 5 as written and treat HSEA Phase 4 I4 as either redundant or as an axiom-precedent-update PR. The recommendation here is the cleanest, but it requires accepting that the 70B path is deferred, possibly indefinitely, until hardware changes.

2. **Ownership of T2.8 LLM output guardrail layer:** the guardrail must touch `conversation_pipeline.py`, which is currently FROZEN under `cond-phase-a-baseline-qwen-001`. This means any guardrail change requires a DEVIATION and a new condition. Two options: (a) ship the guardrail under UP-7 (the substrate-swap-induced new condition naturally allows it), bundling it with the 8B pivot DEVIATION. (b) Open a separate condition for the guardrail alone before UP-7. Option (a) is cheaper; option (b) is cleaner research-validity-wise. Operator decision.

3. **HSEA Phase 4 rescoping:** confirm that HSEA Phase 4 should be rescoped from "code drafting" to "narration drafting" for I1–I5 (with I6 conditional and I7 unchanged). This drops ~2400 LOC of HSEA implementation. The alternative is to keep HSEA Phase 4 as code-drafting but route the patches into a separate condition that doesn't touch frozen files — which is unworkable because all the target files are frozen.

4. **State file design:** confirm sibling files under shared index (§6 recommendation) versus a single unified `research-stream-state.yaml`. The sibling design is favored here for parallelism, but if the operator prefers one source of truth, the shared index can be promoted to the only file with both epics' phase tables embedded.

5. **`hapax-constitution` PR strategy:** confirm that LRR Phase 6 and HSEA Phase 0 0.5 should ship as one constitutional PR (~5 amendments and 1 new precedent in one operator review cycle). Alternative: two PRs in close succession. One PR is faster but harder to review. Operator pref.

6. **Cluster H (revenue) timing:** HSEA Phase 9 Cluster H ships sponsor copy, NLnet drafter, consulting gate, etc. Drop #57 tier 3 says these should ship in days 15–21. The unified phase sequence puts them in UP-12, which lands in week 4–6. Two reasons: (a) they depend on UP-2 governance queue; (b) operator review bandwidth. Confirm acceptable, or accelerate by shipping Cluster H first within UP-12.

7. **Worktree allocation:** confirm that delta is research-only / no-code-writing per global CLAUDE.md. Both HSEA spec and HSEA plan are delta-authored; if delta cannot ship code, HSEA execution falls to alpha + beta. This compresses the parallel UP-12 cluster basket from 3 worktrees to 2.

8. **Index file maintenance:** who edits `research-stream-state.yaml::unified_sequence` over time? Recommendation: alpha during fold-in commit, then operator-only edits. Any session that wants to add an entry files a request via the governance queue. Confirm.

9. **Drop #62 itself:** does this drop become a docs/research/ artifact (`docs/research/2026-04-14-cross-epic-fold-in.md`), or does it land as a docs/superpowers/specs/ supplement (`docs/superpowers/specs/2026-04-14-lrr-hsea-fold-in-design.md`)? Recommendation: research drop, with a one-line reference from each of LRR spec §1 and HSEA spec §1.

10. **Phase ordering deviation tolerance:** the unified sequence is a recommended order, not a strict ordering. Within the constraint that UP-7 has hard predecessors, sessions should be allowed to pick a different "next phase" if they have local reason. Confirm this looseness is acceptable or whether the operator prefers strict serial execution.

---

## Closing

The fold-in is mostly mechanical once the substrate-swap question is resolved. The two epics were authored against largely complementary scopes and only collide in five primitive families and one substrate decision. The five primitives have a clear single-owner declaration (LRR owns all of them); the substrate decision is option (c) per §4 (8B parallel as UP-7, 70B deferred).

The downstream cleanup is concentrated in HSEA Phase 4 — that is the one HSEA phase that materially shrinks under the fold-in. Everything else in HSEA is genuinely additive. LRR is unchanged in scope; only its Phase 5 internal structure splits.

The merged sequence is realistic for a single operator: 14 unified phases, 30–45 sessions, 6–10 weeks, with UP-12's cluster basket providing the parallelism needed for alpha + beta to work simultaneously without colliding. The shared state index makes that parallelism legible to every session that picks up either epic.

**Files referenced (absolute paths):**
- `/home/hapax/projects/hapax-council/docs/superpowers/specs/2026-04-14-livestream-research-ready-epic-design.md` (LRR spec, 1371 lines)
- `/home/hapax/projects/hapax-council/docs/superpowers/plans/2026-04-14-livestream-research-ready-epic-plan.md` (LRR plan, 321 lines)
- `/home/hapax/projects/hapax-council/docs/superpowers/specs/2026-04-14-hsea-epic-design.md` (HSEA spec, 794 lines)
- `/home/hapax/projects/hapax-council/docs/superpowers/plans/2026-04-14-hsea-epic-plan.md` (HSEA plan, 375 lines)
- `/home/hapax/projects/hapax-council/docs/research/2026-04-14-tactics-and-strategies-to-increase-success-probabilities.md` (drop #57, 737 lines)
- `/home/hapax/projects/hapax-council/docs/research/2026-04-14-hapax-self-executes-tactics-as-content.md` (drop #58, 480 lines)
- `/home/hapax/projects/hapax-council/docs/research/2026-04-14-drop-58-audit-critical-evaluation.md` (drop #59, 444 lines)

— End of drop #62 fold-in analysis.