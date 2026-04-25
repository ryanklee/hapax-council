# Workstream realignment v3 — delta update (Phase 0+1 + ops-critical landed) — 2026-04-25T01:55Z

**Author:** beta
**Appends:** `docs/operations/2026-04-24-workstream-realignment-v3.md` (does not supersede)
**Honest scope notice:** Tracks merged + in-flight PRs since v3-final's 23:15Z timestamp. Does not re-WSJF the queue or re-rank items; for that, the next full pass would be v4. This is a thin delta — what shipped + what's still open + what shifted ownership.

## 1. Shipped since v3-final (in chronological merge order)

| PR | Title | Owner | Merged | Phase / scope |
|---|---|---|---|---|
| #1341 | Bayesian Phase 0 STUB — frozen API surface | beta | <23:15Z (already shipped at v3-final) | n/a |
| #1342 | ef7b-165 Phase 9 — egress footer module | delta | 2026-04-24T23:17:10Z | governance, anti-personification |
| #1344 | Bayesian Phase 5 — refusal gate | epsilon | (within v3-final tail window) | gate consumer of Phase 4 envelope |
| #1345 | ef7b-165 Phase 9 Part 2 — EgressFooterCairoSource | delta | (within v3-final tail window) | governance, ward implementation |
| #1347 | Bayesian Phase 4 — prompt envelope | alpha | 2026-04-25T00:03Z | unblocks Phase 6 wiring |
| #1348 | Phase 5/4 surface-key alignment fix | epsilon | 2026-04-25T00:18Z | dependency cleanup |
| **#1350** | **Bayesian Phase 0 FULL — `ClaimEngine[T]` + kill-switch + HPX003/HPX004** | **beta** | **2026-04-25T00:45:29Z** | **keystone — unblocks Phase 1 + 6** |
| #1352 | AUTH-HOMAGE default flip (`bitchx` → `bitchx-authentic-v1`) | alpha | (post-Phase-0-FULL) | aesthetic, session-callable |
| **#1353** | **Bayesian Phase 1 — PresenceEngine refactored onto `ClaimEngine[bool]`** | **beta** | **2026-04-25T01:34:20Z** | **unblocks Phase 6 cluster waves** |
| **#1354** | **3499-004 gmail-sync inotify-flood fix (`_should_skip` filter)** | **beta** | **2026-04-25T01:46:50Z** | **operational-critical, WSJF 9** |

## 2. In-flight PRs (as of 01:55Z)

| PR | Title | Owner | State | Notes |
|---|---|---|---|---|
| #1349 | DURF Phase 2 — Hyprland window capture + scrim pull | beta | OPEN, auto-merge armed | Test fixes pushed at `cb8e60a74` (chrome→pre_fx pin update + Phase-2 test_durf_source rewrite). CI re-running; BEHIND main pending rebase. |
| #1351 | DURF Phase 10 + 2026-04-24 docs + bed-music rotation flip (scope-mixed) | delta | OPEN | Per v3-final note: drop docs (already on main), drop durf_source.py / z_plane / default.json overlap (already on main via #1349/#1350/#1352), keep bed-music rotation flip as actual focus. **Still scope-mixed at 01:55Z.** |
| **#1355** | **Bayesian Phase 6c-i.A SpeakerIsOperatorEngine** | **epsilon** | **OPEN** | New module + 18 tests + prior_provenance entry. 328 LOC additions, 0 deletions. Wire-in deferred to 6c-i.B. CI in-flight. **Acted on beta's scope-direction dispatch within 8 minutes.** |
| #1328/#1327/#1326/#1325 | dependabot bumps (jsdom, react-query, tailwindcss, tailwind/vite) | dependabot | OPEN | All blocked on main-CI-red `test` failures (pre-existing, not PR-caused). |

## 3. Ownership shifts since v3-final

- **Phase 1 PresenceEngine refactor**: shipped by beta as planned. **No shift.**
- **3499-004 gmail-sync inotify flood**: claimed by beta-as-coordinator (per v3-final §3.3 row 19 WSJF 9). Implemented as fix surface (c) — `_should_skip` filter. Surfaces (a) diff-before-write and (b) batch+debounce remain available as follow-ups if (c) proves insufficient. **Shipped same-tick as claim.**
- **AUTH-HOMAGE default-flip**: alpha shipped #1352. Earlier this run, beta had homage-flip changes staged on `main-red` worktree as part of stash recovery; alpha's PR superseded those staged changes (foreign-session intercept pattern documented in `feedback_worktree_persistence.md`). **Net: alpha owns this surface end-to-end.**
- **Phase 6c-i.A SpeakerIsOperatorEngine**: epsilon claimed + shipped as #1355 within 8 minutes of beta's scope-direction dispatch (`beta-to-epsilon-2026-04-25-phase-6c-scope-direction.md`). Phase 6c-i.B (perception_loop wire-in) and 6c-ii (chat_author multi-source) remain epsilon's scope.

## 4. Worktree-collision incident log

Per `feedback_worktree_persistence.md`, the multi-session relay continues to surface worktree-contention incidents:

- **Beta on main-red**: foreign session intercepted my checkout to `feat/bayesian-phase-1-presence-engine-refactor` mid-tick; stashed Phase 1 WIP as `foreign-session-presence-engine-wip`; checked out `feat/auth-homage-default-flip-bitchx-authentic-v1` and committed homage-flip work. Recovered: applied stash@{1} on Phase 1 branch, committed only the 3 Phase 1 files, dropped the redundant homage-flip stash@{0} after verifying it matched alpha's #1352 byte-for-byte.
- **Alpha on Phase 4 #1347**: prior session's "WORKTREE-COLLISION RECOVERY" line in alpha.yaml notes "foreign DURF commit landed on original branch ref + linter reverted imports during deletion of `shared/claim_prompt.py`. Recovered via fresh `feat/bayesian-phase-4-envelope` from origin/main + recreate-from-conversation-context."

**Pattern:** worktrees `main-red` (beta-leaning) and primary `hapax-council` (alpha-leaning) have started colliding when both sessions edit + commit during the same tick. Mitigation in place: `feedback_claim_before_parallel_work.md` requires pre-branch claim announcement in session yaml. **Not yet a hook-enforced rule.**

## 5. Critical-path now (post-Phase-1 unblocking)

Phase 6 cluster waves are CLEARED to start. Per Phase 1 #1353 PR description + this morning's broadcast inflection:

| Phase | Scope | Owner | State |
|---|---|---|---|
| 6a | activity claims | delta | NOT YET CLAIMED |
| **6b** | **mood / stimmung claims** | **alpha** | **NOT YET CLAIMED** |
| **6c-i.A** | **`speaker_is_operator` engine** | **epsilon** | **#1355 OPEN** |
| 6c-i.B | wire-in to `perception_loop._tick_consent` | epsilon | DEFERRED behind 6c-i.A |
| 6c-ii | chat-author multi-source noisy-OR | epsilon | DEFERRED, governance-sensitive |
| 6d | meta / system claims | beta | NOT YET CLAIMED |

**Recommended next pickups by lane priority:**
- **alpha**: open Phase 6b (mood/stimmung) since it's the lane-canonical wave + DEVIATION-025 P0 (WSJF 13, data-loss-critical) per v3-final §5.2 still highest-WSJF unclaimed alpha item.
- **delta**: rebase + scope-resolve #1351 (drop redundant Workstream A, keep bed-music rotation flip as Workstream B). Then Phase 6a activity claims.
- **epsilon**: ship #1355 to merge → land 6c-i.B wire-in same tick (single-surface change at `perception_loop.py:214`).
- **beta**: Phase 6d meta/system claims (lane-canonical) OR audit catchup on #1342/#1344/#1345/#1347 (slow post-merge, advisory).

## 6. Operational state

- **Main CI:** intermittent flake on `tests/studio_compositor/test_ward_fx_coupling.py::TestFxEventToWardProperties::test_audio_kick_onset_bumps_only_audio_reactive_wards`. Phase 1 #1353 first run passed (6m08s); rebase run failed; second re-run passed (5m39s). Not Phase-1-caused — this test is in `studio_compositor` which Phase 1 doesn't touch. Flake or pre-existing main-red regression that recovers on retry. Needs a `--rerun` flag in CI workflow if it persists.
- **Auto-merge:** working as expected on Phase 1 + 3499-004; armed on #1349.
- **270s tick cadence:** locked across all sessions per operator absolute rule.
- **HAPAX_BAYESIAN_BYPASS kill-switch:** ready as single rollback knob. Not exercised this run.

## 7. Outstanding from v3-final

| v3-final item | State |
|---|---|
| Audit catchup on #1342 / #1344 / #1345 / #1347 | beta queue, P1, slow post-merge |
| Workstream realignment delta-update | THIS DOC |
| Phase 7 research-spec-plan (τ_mineness + per-element provenance) | not started; co-authored alpha+beta |
| 17 unscheduled research drops + 4 spec triage items | unchanged |
| HOMAGE #162/#163/#176/#177/#186/#189 | delta queue per v3-final §5.3 |
| 60f6-021..027 chain (7 tasks) | epsilon parallel pickup |

## 8. Not addressed in this delta

- Re-WSJF of the full queue. Items shipped this run are off the queue; surviving items keep their v3-final WSJF until the next full pass.
- New research drop intake. None landed since v3-final.
- Hook policy changes. None proposed.
- Worktree-collision codification. Pattern documented; hook-enforcement is a follow-up cc-task candidate.

— beta, 2026-04-25T01:55Z
