---
name: subagent worktree persistence
description: Subagent git commits are lost when worktrees are cleaned up. Use explicit patterns to prevent data loss.
type: feedback
---

Subagent commits are routinely lost because of worktree lifecycle issues. This burned an entire session's worth of rework.

**Root cause:** Two failure modes:
1. WITHOUT `isolation: "worktree"`: Subagent shares the working directory but creates new branches (forced by no-stale-branches hook). Main session doesn't track which branch the subagent ended up on. Branch gets cleaned up later.
2. WITH `isolation: "worktree"`: Worktree is preserved if commits exist, but the main session doesn't know WHERE the worktree is. Cherry-picking requires finding the commit SHA.

**Why:** The no-stale-branches hook blocks branch creation when unmerged branches exist. Subagents create new branch names to work around this. The resulting branches are not tracked by the main session.

**How to apply — THREE SAFE PATTERNS:**

1. **Direct implementation (preferred for small tasks):** Write files directly in the main session. Don't dispatch subagents for code that must persist. Use subagents only for research/exploration.

2. **Subagent on current branch (for larger tasks):** Dispatch WITHOUT `isolation: "worktree"`. Tell the subagent explicitly: "Do NOT create branches. Do NOT run git checkout. Commit to the current branch. The branch is `{branch_name}`." This avoids the hook trigger.

3. **Subagent with push (for parallel work):** Dispatch WITH `isolation: "worktree"`. Tell the subagent: "Push your branch to origin before completing. Report the remote branch name." Then cherry-pick from the remote branch.

**NEVER:** Dispatch a subagent, assume its commits persisted, and continue without verifying files exist on disk.
