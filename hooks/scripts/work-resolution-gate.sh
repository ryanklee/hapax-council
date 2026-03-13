#!/usr/bin/env bash
# work-resolution-gate.sh — PreToolUse hook
#
# Blocks Edit/Write tool calls when the current session is on a feature branch
# with commits ahead of main but no open PR. Forces the session to submit a PR
# before starting new work.
set -euo pipefail

# --- 1. Read tool invocation from stdin ---
input="$(cat)"
tool_name="$(printf '%s' "$input" | jq -r '.tool_name // empty')"

# --- 2. Only gate file-mutating tools ---
case "$tool_name" in
  Edit|Write|MultiEdit|NotebookEdit) ;;
  *) exit 0 ;;
esac

# --- 3. Determine git context from CWD ---
if ! git rev-parse --is-inside-work-tree &>/dev/null; then
  # Not inside a git repo — nothing to gate.
  exit 0
fi

# --- 4. Get current branch (handle detached HEAD) ---
branch="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || true)"
if [[ -z "$branch" || "$branch" == "HEAD" ]]; then
  # Detached HEAD — no branch to gate.
  exit 0
fi

# --- 5. Skip if on main/master ---
if [[ "$branch" == "main" || "$branch" == "master" ]]; then
  exit 0
fi

# --- 6. Count commits ahead of main ---
# Determine the default branch (main or master).
if git show-ref --verify --quiet refs/heads/main; then
  default_branch="main"
elif git show-ref --verify --quiet refs/heads/master; then
  default_branch="master"
else
  # No main or master branch found — can't compare, don't block.
  exit 0
fi

ahead="$(git rev-list --count "${default_branch}..HEAD" 2>/dev/null || echo 0)"
if [[ "$ahead" -eq 0 ]]; then
  exit 0
fi

# --- 7. Check for an open PR on this branch ---
# If gh is unavailable or fails, don't block — fail open.
if ! command -v gh &>/dev/null; then
  exit 0
fi

pr_count="$(gh pr list --head "$branch" --state open --json number --jq 'length' 2>/dev/null || echo "error")"
if [[ "$pr_count" == "error" ]]; then
  # gh failed (no auth, no network, etc.) — fail open.
  exit 0
fi

if [[ "$pr_count" -gt 0 ]]; then
  # PR already exists — work is tracked.
  exit 0
fi

# --- 8. Block: unpushed feature work with no PR ---
echo "BLOCKED: Branch '${branch}' has ${ahead} commit(s) ahead of ${default_branch} with no PR. Submit a PR before starting new work."
exit 2
