# Alpha LRR Epic Kickoff Handoff — 2026-04-14

**Session:** alpha (planning, 2026-04-13 → 2026-04-14, ~1.5 cycles)
**Closing:** 2026-04-14 CDT
**Scope:** Plan the LIVESTREAM RESEARCH READY (LRR) epic end-to-end, land it in git, hand off execution to future alpha sessions.

## Headline

LRR is a planned 11-phase epic that sequences the work from current state (Legomena Live on Qwen3.5-9B, partially wired) to the **end-state triad**:

1. **Substrate** — Hapax running on Hermes 3 70B SFT-only, dual-GPU layer-split, TabbyAPI-served
2. **Medium** — 24/7 Legomena Live, always-on
3. **Agency** — Hapax as continual research programmer, furthering research objectives indefinitely

The epic is landed in git as formal design docs + an execution companion plan + a minimal state CLI. Execution has **not started**. The next alpha session opens Phase 0.

## What this session shipped

- **Epic design doc:** `docs/superpowers/specs/2026-04-14-livestream-research-ready-epic-design.md` (~16,500 words)
- **Epic plan doc:** `docs/superpowers/plans/2026-04-14-livestream-research-ready-epic-plan.md` (~3,500 words, execution-focused companion)
- **Bootstrap CLI:** `scripts/lrr-state.py` (minimal state reader/writer; expanded in Phase 0)
- **PR:** #783

The epic absorbs scope from:
- Garage Door Open streaming design + Phase 2 epic (most stages shipped; Stage 3 hero-mode absorbed into Phase 8)
- Hermes 3 70B migration plan (absorbed as Phase 5 with pre-migration prerequisite set)
- livestream-performance-map research (#771 + #775) — delegated; PR #775 merged this session
- Round 5 findings (FINDING-R Qdrant gap, FINDING-Q imagination stability, FINDING-S SDLC dormant) — absorbed into Phase 0/6/10
- GDO token pole ethical engagement design — absorbed into Phase 7 persona spec
- GDO 36h stability checklist — absorbed into Phase 10 continuous-operation matrix

## Key decisions embedded (operator, 2026-04-13)

- **DF-1:** Hapax's posture/personality/role is a real problem, constrained by the Gemini-Flash-style assistant-default substrate; the 7 ethical-engagement principles from GDO are already-resolved audience-axis commitments. Phase 7.
- **D-1 Substrate-first:** persona spec deferred until Hermes 3 is live. Phase 7 follows Phase 5.
- **D-2 Option B:** the Hermes 3 swap is formalized as DEVIATION-037 + a new research claim (`claim-shaikh-sft-vs-dpo`) testing SFT-only vs DPO under identical grounding directives on hapax's production environment. The swap IS the claim, not a confound.
- **End-state triad:** substrate × medium × agency, all three simultaneously true.
- **I-1:** research is stationary/adaptive, append-only condition registry, conditions never close they branch.
- **I-2:** Hapax is research subject + instrument + programmer simultaneously; recursion is constitutive.
- **I-3:** content programming via research objectives is a new post-substrate workstream that unlocks only on Hermes 3.

## Audit provenance

The epic design doc was audited twice against the planning conversation transcript:

- **Audit 1** — 22 findings (missed scope items, buckets not landed in phases). All patched.
- **Audit 2** — 13 findings (3 critical α/β/γ partition naming inconsistencies, 5 exit criteria gaps, 5 Phase 6 privacy data-source gaps, 2 minor issues). All patched.

Both audit reports are in the planning conversation transcript; the final state reflects both patch passes.

## Branches cleaned up this session

- PR #775 (beta's research map) — admin-merged (docs-only, CI limbo); branch deleted; local worktree removed
- PR #782 (alpha's W1.8 JSON timestamp fix) — admin-merged (was BEHIND main after #775); branch deleted; local worktree removed
- New branch: `feat/lrr-epic-design` (this PR #783)

## What the next alpha session should do

1. **Standard relay onboarding** (read `onboarding-alpha.md`, `PROTOCOL.md`, peer status, inflections)
2. **Verify this PR (#783) has merged** before starting Phase 0. If not merged, wait or pick up in review mode.
3. **Run `scripts/lrr-state.py init`** to create `~/.cache/hapax/relay/lrr-state.yaml` at Phase 0
4. **Read the epic design doc** at `docs/superpowers/specs/2026-04-14-livestream-research-ready-epic-design.md` — at minimum: §0 Headline, §3 Guiding Principles, §4 Phase Summary, §5 Phase 0 section
5. **Read the execution plan** at `docs/superpowers/plans/2026-04-14-livestream-research-ready-epic-plan.md` — §1-9
6. **Re-verify the world state.** The epic design §2 has "Pre-epic verification findings (2026-04-14)". If > 1 week has passed, re-run the verifications. Things drift.
7. **Open Phase 0.** Follow the plan doc §2 pickup procedure. Write per-phase spec + plan. Execute. Verify exit criteria. Close with handoff.

## Phase 0 scope reminder (in case the next session doesn't have time to read the whole epic)

- Fix `chat-monitor.service` (auto-restart loop, exit code 1)
- Wire token ledger writers (album-identifier + chat-monitor)
- Resolve `/data` inode pressure (currently 88%)
- Ship FINDING-Q steps 2-4 (WGSL validation + rollback + counter)
- Verify Sierpinski performance resolution + capture CPU baseline
- Verify native RTMP is the production output path
- Install `huggingface-cli`
- Document current Phase A baseline state
- Locate voice transcript file permissions (`~/.local/share/hapax-daimonion/events-*.jsonl`)
- Capture Kokoro TTS latency baseline

Exit criteria + verification commands are in the epic design §Phase 0.

## Known blockers to watch

- **Sprint 0 G3 gate** — Phase 4 depends on it. Options documented in epic design Phase 4 preamble.
- **Branch discipline** — `no-stale-branches.sh` will block new branches if any unmerged branches exist. Use `scripts/lrr-state.py` and per-phase branch naming discipline.
- **Frozen-file enforcement** — not yet in place (Phase 1 work). Until then, the next session must manually avoid edits to `agents/hapax_daimonion/grounding_ledger.py`, `conversation_pipeline.py`, `persona.py`, `conversational_policy.py`. Condition A integrity depends on it.
- **Operator availability** — Phases 4, 5, 6, 7 have explicit operator-in-the-loop moments. See plan doc §4 for the list.

## Relay state

- Session retirement time: 2026-04-14 CDT (this session)
- No peer session active at retirement (beta retired mid-planning after PR #775 shipped)
- `alpha.yaml` updated with: completed planning, landed PR #783, next phase = Phase 0
- `~/.cache/hapax/relay/context/2026-04-13-livestream-as-research-medium-research-map.md` — predecessor research map (scope reference only, not authoritative)
- `~/.cache/hapax/relay/context/2026-04-14-livestream-research-ready-epic-design.md` — staging copy of the epic design doc (mirrors the git version at `docs/superpowers/specs/`); may be removed by a future cleanup pass

## Final note for the next session

The planning phase is dense but the execution phase is mechanical. The epic design doc is comprehensive; the execution plan is a checklist-driven pickup procedure; the state file tracks where you are. You don't need to re-plan anything. You need to open Phase 0, execute it, close it, and move to Phase 1. The epic will take weeks but each individual phase is a tight scope.

The operator's framing throughout was: "this is where we ultimately want to arrive at." That framing is captured. Every decision trail is in git. The research continues forever — the epic completes, the research doesn't.

End of kickoff handoff. Open Phase 0.
