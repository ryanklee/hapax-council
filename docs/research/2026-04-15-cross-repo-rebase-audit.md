# Cross-repo feature branch rebase audit

**Date:** 2026-04-15
**Author:** alpha (AWB mode, queue/ item #110)
**Scope:** Survey feature branches behind `origin/main` across 4 workspace repos (hapax-council, hapax-mcp, hapax-constitution, hapax-officium). Per memory `feedback_rebase_alpha_after_merge`, stale branches cause the vite dev server to miss changes. Identify which branches need rebase + in what order.
**Register:** scientific, neutral

## 1. Headline

**32 feature branches across 4 repos are behind `origin/main`.** Of these:

- **3 are session-authored (non-dependabot)** — the only ones where rebase decisions matter for alpha/beta/epsilon operation
- **29 are dependabot-authored** — GitHub's own rebase logic handles these; alpha should not touch them manually

### Session-authored branches behind main (prioritized)

| Repo | Branch | Ahead / Behind | Owner | Action |
|---|---|---|---|---|
| hapax-council | `beta-phase-4-bootstrap` | **34 ahead, 89 behind** | beta (PR #819) | RISKY rebase (34 commits × 89 commits behind = wide merge surface); beta should decide |
| hapax-council | `feat/lrr-phase-2-item-2-hls-rotator-unblock` | 1 ahead, 11 behind | parallel session (closed duplicate of PR #858) | DELETE — already closed as duplicate of PR #859 |
| hapax-council | `docs/lrr-phase-2-operator-activation-runbook` | 1 ahead, 1 behind | parallel session (PR #864 OPEN) | RUNBOOK — waiting on PR #864 merge; rebase cost trivial when ready |

## 2. hapax-council detailed scan

```
origin/beta-phase-4-bootstrap: 34 ahead, 89 behind
origin/docs/lrr-phase-2-operator-activation-runbook: 1 ahead, 1 behind
origin/feat/lrr-phase-2-item-2-hls-rotator-unblock: 1 ahead, 11 behind
```

**Plus 9 dependabot branches** (all `dependabot/github_actions/*` or `dependabot/npm_and_yarn/*`), each 1–3 commits ahead, 359–375 commits behind. These are dependabot's concern, not alpha's — GitHub will auto-rebase + re-test when dependabot decides, or close them as stale.

### beta-phase-4-bootstrap (PR #819)

- **34 ahead** of main — this is beta's substantial overnight work (substrate research, Phase 6 + Phase 7 extractions, protocol evaluation drop, LRR Phase 10 extraction, consolidated audit, CLAUDE.md drift scan, etc.)
- **89 behind** main — alpha + the parallel sessions shipped 47+ PRs to main since beta branched off
- **Rebase risk: MEDIUM–HIGH.** The 89 commits behind include PR #855 which cherry-picked beta's HSEA Phase 6 + 7 extraction specs to main. Beta's branch has the originals; rebase will see the cherry-picked duplicates as conflicting adds. Clean via `git rebase -Xtheirs origin/main` or by dropping the cherry-picked commits from beta's branch during interactive rebase.
- **Additional risk:** the 89 commits include PR #857 (`archive-search.py` extensions) + PR #860 (`archive-purge.py` consent hook) which might conflict with any pre-existing scripts/* changes on the beta branch.
- **Recommendation:** **beta owns this rebase.** Alpha should not attempt it because (a) beta's commits are not in alpha's memory, (b) conflict resolution needs beta's judgment on which side wins, (c) the branch is the active workspace for beta's session. If beta's next refill cycle doesn't include a rebase item, delta should add one.

### docs/lrr-phase-2-operator-activation-runbook (PR #864)

- **1 ahead, 1 behind.** Trivial.
- The 1 behind is likely a single doc commit that landed on main between when the parallel session branched and when they pushed.
- **Recommendation:** auto-resolves on merge. If the merge surface is clean, GitHub's "Update branch" button fixes it. No alpha action.

### feat/lrr-phase-2-item-2-hls-rotator-unblock (CLOSED PR #858)

- This branch belongs to **PR #858** which alpha closed as a duplicate of PR #859 at 2026-04-15T~12:30Z.
- The branch still exists on origin because closing a PR doesn't delete the branch.
- **Recommendation:** **delete the branch.** Alpha can run `git push origin --delete feat/lrr-phase-2-item-2-hls-rotator-unblock` right now to clean it up, or leave for the next branch-audit sweep.

## 3. hapax-mcp detailed scan

```
origin/dependabot/github_actions/actions/create-github-app-token-3: 1 ahead, 15 behind
origin/dependabot/github_actions/anthropics/claude-code-action-1.0.93: 1 ahead, 4 behind
origin/dependabot/github_actions/dependabot/fetch-metadata-3: 1 ahead, 4 behind
origin/dependabot/pip/httpx-gte-0.28.1: 1 ahead, 4 behind
origin/dependabot/pip/pydantic-gte-2.12.5: 1 ahead, 4 behind
origin/dependabot/pip/pyright-gte-1.1.408: 1 ahead, 4 behind
origin/dependabot/pip/pytest-gte-9.0.3: 1 ahead, 4 behind
origin/dependabot/pip/ruff-gte-0.15.10: 1 ahead, 4 behind
```

**8 dependabot branches, zero session-authored.** No alpha action needed.

## 4. hapax-constitution detailed scan

```
origin/dependabot/github_actions/anthropics/claude-code-action-1.0.92: 1 ahead, 2 behind
origin/dependabot/github_actions/dependabot/fetch-metadata-3: 1 ahead, 2 behind
origin/dependabot/github_actions/pnpm/action-setup-5: 1 ahead, 6 behind
```

**3 dependabot branches, zero session-authored.** No alpha action needed.

## 5. hapax-officium detailed scan

```
origin/dependabot/github_actions/anthropics/claude-code-action-1.0.76: 53 ahead, 75 behind
origin/dependabot/github_actions/anthropics/claude-code-action-1.0.92: 1 ahead, 6 behind
origin/dependabot/github_actions/dependabot/fetch-metadata-3: 1 ahead, 6 behind
origin/dependabot/npm_and_yarn/officium-web/eslint-plugin-react-refresh-0.5.2: 1 ahead, 27 behind
origin/dependabot/npm_and_yarn/officium-web/lucide-react-0.577.0: 1 ahead, 27 behind
origin/dependabot/npm_and_yarn/officium-web/tailwindcss/vite-4.2.2: 1 ahead, 27 behind
origin/dependabot/npm_and_yarn/officium-web/types/node-25.5.0: 1 ahead, 27 behind
origin/dependabot/npm_and_yarn/officium-web/vitejs/plugin-react-5.2.0: 1 ahead, 27 behind
origin/dependabot/npm_and_yarn/vscode/esbuild-0.28.0: 1 ahead, 9 behind
origin/dependabot/npm_and_yarn/vscode/marked-18.0.0: 1 ahead, 6 behind
origin/dependabot/npm_and_yarn/vscode/types/node-25.5.2: 1 ahead, 6 behind
origin/dependabot/npm_and_yarn/vscode/types/vscode-1.115.0: 1 ahead, 6 behind
```

**12 dependabot branches, zero session-authored.** Note the `claude-code-action-1.0.76` outlier at **53 ahead, 75 behind** — it looks like dependabot attempted to force-push several cumulative commits but got stuck behind a long backlog. This is a dependabot health issue + will likely resolve when dependabot retries or when the 1.0.92 supersedes it. No alpha action.

## 6. hapax-logos scan

Could not check as a standalone repo — `hapax-logos/` lives inside `hapax-council/` as a subdirectory (Tauri app source + `hapax-logos/src-tauri/` backend). Its git state is the same as hapax-council's. Excluded from the per-repo count.

## 7. Recommendations

### 7.1 Immediate (alpha can do now)

**1. Delete the closed-PR branch.**

```bash
cd ~/projects/hapax-council && \
  git push origin --delete feat/lrr-phase-2-item-2-hls-rotator-unblock
```

This branch backed PR #858 which alpha closed at 2026-04-15T12:30Z as a duplicate of PR #859. Leaving the branch on origin clutters the `git branch -r` output but causes no functional harm. Safe to delete.

### 7.2 Session-scoped (beta decides)

**2. beta-phase-4-bootstrap rebase.**

The rebase is risky because (a) PR #855 already cherry-picked beta's HSEA Phase 6 + 7 spec extractions to main — the originals on the branch will conflict, (b) 89 commits behind includes 47+ PRs from alpha + parallel sessions touching scripts/, agents/studio_compositor/, shared/, config/, systemd/units/, docs/superpowers/ — high surface area for conflicts.

**Beta should own this rebase**, not alpha. Reasons:

- Beta's session has the cognitive context for beta's commits (substrate research, Phase 6/7 extractions, protocol evaluation, etc.)
- Beta's 16:30Z refill 6 closures batch was last-active at 12:36Z local time; beta's session has been idle since operator's 13:07Z ("I don't quite understand why beta and alpha aren't always working") observation
- Alpha force-pushing beta's branch would violate the "audit-don't-edit for cross-author work" protocol v1.5 rule that beta itself proposed

**Recommendation:** delta should add "rebase beta-phase-4-bootstrap onto origin/main" as a beta queue item (e.g., #204) when delta writes beta's next refill.

### 7.3 Operator-scoped

**3. Dependabot branches — leave alone.**

The 29 dependabot branches will self-resolve via:

- GitHub's auto-rebase button (`Update branch` on each PR)
- Dependabot retry cycles when upstream packages release new versions
- Manual close for stale branches (operator decision, not alpha's)

Alpha should NOT manually rebase dependabot branches — the bot's health checks + test runs handle the lifecycle. Touching them adds noise without value.

## 8. Protocol observations

**1. Branch hygiene drifts when sessions don't actively clean up.**

The `feat/lrr-phase-2-item-2-hls-rotator-unblock` branch was the first casualty of alpha's PR #858/#859 duplicate. Alpha closed the PR but the branch remained. A future branch-audit sweep (queue item #110 itself, or a `/branch-audit` skill) catches these, but the gap between "PR closed" and "branch deleted" is a recurring cleanup item.

**Recommendation:** whenever a session force-pushes over a parallel session's branch (like alpha did to PR #867 earlier), it's safer to switch to `git reset --soft` + re-commit on top than to overwrite. Alpha's PR #867 recovery is a good model.

**2. `beta-phase-4-bootstrap` is the primary cross-session dependency.**

Until PR #819 merges, many downstream items (HSEA Phase 6/7 plans, LRR Phase 10 re-extraction, beta's substrate research drops) live only on that branch. Alpha's per-item queue work can proceed without PR #819 merging, but the cumulative cherry-pick pattern (as in PR #855) is the only bridge. Delta should track PR #819 merge status as a blocker for Phase 6 + downstream work.

**3. Dependabot cohabitation is fine.**

None of the 29 dependabot branches conflict with alpha/beta/epsilon session work. They live in their own namespace + update lockfiles / workflow YAML, not session-touched files. The cross-repo branch count is high but the signal-to-noise is low — only 3 branches out of 32 are meaningful for session coordination.

## 9. Closing

No critical issues. 1 actionable cleanup (delete the closed-PR branch), 1 beta-scope rebase (add to beta queue), 29 dependabot branches to ignore. The cross-repo branch surface is healthy — session discipline is holding.

Branch-only commit per queue item #110 acceptance criteria.

## 10. Cross-references

- Memory: `feedback_rebase_alpha_after_merge.md` — rebase alpha after beta merges (the original rule)
- Memory: `feedback_no_stale_branches.md` — never leave branches unmerged
- Memory: `feedback_branch_discipline.md` — max one branch per session
- Hook: `hooks/scripts/no-stale-branches.sh` — enforces branch-creation gate
- PR #858 (closed duplicate of PR #859): `feat/lrr-phase-2-item-2-hls-rotator-unblock`
- PR #864 (runbook, open): `docs/lrr-phase-2-operator-activation-runbook`
- PR #819 (draft): `beta-phase-4-bootstrap`

— alpha, 2026-04-15T17:42Z
