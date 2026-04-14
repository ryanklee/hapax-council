# LRR Phase 0 — Verification & Stabilization (per-phase spec)

**Date:** 2026-04-14
**Phase:** 0 of 11
**Owner:** alpha
**Branch:** `feat/lrr-phase-0-verification`
**Parent epic:** `docs/superpowers/specs/2026-04-14-livestream-research-ready-epic-design.md` § Phase 0
**Plan companion:** `docs/superpowers/plans/2026-04-14-lrr-phase-0-verification-plan.md`
**Roadmap context:** `docs/superpowers/plans/2026-04-14-unified-execution-roadmap.md` Track A

## 0. Why this phase exists

Per the epic design §3 P-8 ("Verification before claiming done") and §3 P-2 ("Research validity is load-bearing"), every subsequent LRR phase assumes a known-good baseline. Phase 0 establishes that baseline by closing latent P0/P1 issues and capturing reference numbers that Phase 5 (Hermes 3 substrate swap) and Phase 10 (observability + drills) compare against.

This phase ships **no new features.** It is a stabilization + measurement pass.

## 1. Pre-phase verification — world state at 2026-04-14T06:38

Re-ran epic §2 verification before opening this phase. **No drift since the epic was authored ~6 hours earlier**, with one new finding (item 9 voice transcript permissions are 644 not 600).

### 1.1 Items closed before this PR

These items were satisfied by prior alpha work tonight and need only be marked done in this phase:

- **Item 1** (chat-monitor.service fix) — **shipped via PR #785, deployed live, verified `active (running)`**. The wait-loop replaces the `sys.exit(1)` crash path; the service polls every 30 s and throttles its "no video ID" warning to every 5 minutes. Verified post-merge: `systemctl --user is-active chat-monitor` returns `active`, journal no longer spams the No-video-ID line every 10 s.

### 1.2 Items closed in this PR

- **Item 7** (huggingface-cli install) — `huggingface-hub[cli]` already installed via `uv tool install`. The CLI binary is now `hf` (renamed by upstream from `huggingface-cli`); `which hf` returns the user's `~/.local/bin/hf`, version 1.9.0. Phase 3 download path will use `hf download <repo>` instead of `huggingface-cli download <repo>`.
- **Item 9** (voice transcript permissions) — `chmod 600` applied to all `~/.local/share/hapax-daimonion/events-*.jsonl` files. Verified `-rw-------`. **New finding pinned:** the daimonion daily rotation hook still creates new files at 644 by default. A Phase 6 follow-up must add a `chmod 600` step or `umask 077` to the rotation path so newly-created daily files are private. This is a **Phase 6 prerequisite** (stream-mode firewall).
- **Item 10** (Kokoro TTS latency baseline) — captured via `scripts/kokoro-baseline.py`, output at `~/hapax-state/benchmarks/kokoro-latency/baseline.json`. Numbers: cold synth 29.8 s (includes one-time `en_core_web_sm` spaCy download), warm p50 2253.9 ms, warm p95 2361.6 ms, warm RTF p50 0.415 (faster than realtime on CPU). Phase 5 substrate swap evaluation compares GPU TTS candidates against these numbers.
- **Item 8** (RESEARCH-STATE.md Phase A note) — added a 2026-04-14 entry noting Phase A is READY but not started, pre-registration written but not filed, OSF project not created. Phase 4 of the LRR epic will close these.

### 1.3 Items deferred to follow-up Phase 0 PRs (same branch)

Each of these gets its own commit on `feat/lrr-phase-0-verification`. Bundled where natural.

- **Item 2** (token ledger writers for `album-identifier.py` + `chat-monitor.py`) — medium effort. Needs to find the LLM call sites in each script and add `record_spend(component, prompt_tok, completion_tok, cost)` after each call. ~50 lines of code change across two files.
- **Item 3** (`/data` inode pressure fix + alerts) — operator-gated cross-repo (Langfuse MinIO lifecycle + `llm-stack/alertmanager-rules.yml` + sudo). Requires the same dance as Wave 1 W1.1.
- **Item 4** (FINDING-Q steps 2–4: WGSL manifest validation + previous-good rollback + counter) — large, multi-session, needs deep read of `hapax-imagination/src-imagination/dynamic_pipeline.rs`. Probably its own Phase 0 follow-up PR.
- **Item 5** (Sierpinski performance baseline) — small measurement script + run. ~30 min.
- **Item 6** (RTMP path documentation) — already partially audited in PR #781's W4.6 doc. Just needs a follow-up note documenting the `toggle_livestream` consent-gated detach behavior.

## 2. Exit criteria (verbatim from epic Phase 0)

Status as of this PR; checkboxes filled progressively across Phase 0's PRs.

- [x] `systemctl --user is-active chat-monitor` returns `active` (not activating/failing) — **verified post-PR #785 deploy**
- [ ] `cat /dev/shm/hapax-compositor/token-ledger.json | jq '.components | keys'` includes `album-identifier` and `chat-monitor` (not just `hapax`) — **deferred to follow-up PR**
- [ ] `df -i /data` shows ≤ 85 % — **deferred (operator-gated)**
- [ ] FINDING-Q steps 2–4 shipped; next wgpu shader reload failure triggers rollback path; counter increments — **deferred to follow-up PR (large)**
- [ ] Sierpinski CPU baseline documented in a context artifact — **deferred to follow-up PR**
- [ ] `toggle_livestream` path documented; production output confirmed — **deferred (build on PR #781 W4.6 audit)**
- [x] `huggingface-cli` available — **satisfied, CLI is now named `hf`**
- [x] `RESEARCH-STATE.md` Phase A state noted — **this PR**
- [x] voice transcript files have permissions `600` — **this PR (existing files); Phase 6 prerequisite for new files via rotation hook**
- [x] `~/hapax-state/benchmarks/kokoro-latency/baseline.json` exists — **this PR**

**This PR closes 5 of 10 exit criteria** (items 1, 7, 8, 9, 10). The remaining 5 (items 2, 3, 4, 5, 6) are scheduled for follow-up commits on the same branch.

## 3. PR boundary policy

This phase ships across multiple PRs on branch `feat/lrr-phase-0-verification`:

**This PR (Phase 0 PR #1):** spec + plan + items 1✓ + 7 + 8 + 9 + 10 + the Kokoro baseline script + the baseline JSON output

**Phase 0 PR #2 (next session):** items 2 + 5 + 6 (medium-sized, no big code dives)

**Phase 0 PR #3 (likely two sessions):** item 4 FINDING-Q steps 2–4

**Phase 0 PR #4 (operator-gated):** item 3 /data inode pressure cross-repo work

The branch stays open until all 10 items are closed. `lrr-state.yaml::current_phase_branch` stays pointed at it.

## 4. Risks (epic-noted + tonight's additions)

- **chat-monitor downstream** — the wait-loop fix unblocks the *no-video-ID* failure mode but `chat-downloader` library may still fail on YouTube innertube changes if the operator points it at a real stream. That's a Phase 9 concern, not Phase 0.
- **Voice transcript chmod is retroactive** — privacy posture is now correct for the existing files. New daily files inherit the rotation hook's umask. Filed as Phase 6 prerequisite.
- **Kokoro baseline cold-synth includes spaCy download** — the cold number (~30 s) is a one-time worst case. Future cold runs (with `en_core_web_sm` cached) will be much faster. Phase 5 comparisons should be apples-to-apples against equivalent first-call vs warm scenarios.
- **FINDING-Q deep dive** — explicitly multi-session. The next alpha session opening Phase 0 PR #3 should spike `dynamic_pipeline.rs` first and write a mini-design before implementing.

## 5. Cross-track context

Per the unified roadmap doc:

- **Track B (Hardware Window):** X670E motherboard install ~2026-04-16. Phase 3 prerequisites partially shift after install. No Phase 0 dependency.
- **Track C (Performance Orphans):** W5.5 + W5.6. Independent of Phase 0.
- **Track D (Wave 5 absorbed):** items pre-folded into LRR phases. None apply to Phase 0.
- **Track E (Operator-Gated):** item 3 (/data inodes) is operator-gated. No other Phase 0 items need operator input.

## 6. Beta drops queued for later phases (do not consume in Phase 0)

Per `~/.cache/hapax/relay/beta.yaml`, beta is doing parallel research. Two artifacts already dropped under `~/.cache/hapax/relay/context/`:

- `2026-04-14-lrr-bundle-1-substrate-research.md` (Phase 3 + 5: Hermes 3 70B EXL3, Blackwell sm_120, TabbyAPI dual-GPU, gpu_split ordering recipe)
- `2026-04-14-lrr-bundle-4-governance-drafts.md` (Phase 6: governance drafts)

These are noted in `lrr-state.yaml::beta_drops_queued` and should be consumed when their target phase opens, not before.

## 7. Handoff implications

If Phase 0 ships in 4 PRs, the Phase 1 open is gated on the last Phase 0 PR completing. The branch stays alive across sessions. Each PR commit advances the exit-criteria checklist.

## 8. Decisions made writing this spec

- **Bundle the deferred-to-follow-up structure into one branch with multiple PRs**, rather than one mega-PR or four separate branches. Reasoning: branch discipline allows one branch open at a time, and Phase 0 work is naturally serial enough that follow-up PRs to the same branch are clean.
- **Skip the "wait until all 10 items done" framing.** Phase 0 ships value in increments. Each PR satisfies a subset of exit criteria. The phase closes (and Phase 1 opens) only when all 10 are checked, but progress is visible at every PR merge.
- **Note the Phase 6 prerequisite from the chmod 600 finding.** Don't try to fix the rotation hook in Phase 0 — that's Phase 6 stream-mode work. Just document that it's required.
