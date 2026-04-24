#!/usr/bin/env bash
# asset-provenance-gate.sh — PreToolUse hook (Bash commands)
#
# AUTH2 governance gate: when the operator commits or pushes, verify that
# every manifest-listed asset source under assets/aesthetic-library/ has
# a sibling provenance.yaml. Without attribution metadata, an asset
# cannot lawfully ship to the public CDN at ryanklee.github.io/hapax-assets.
#
# Delegates to scripts/verify-aesthetic-library.py for the actual check —
# same logic as the CI `Aesthetic library verify` step, so pre-commit and
# CI stay in lock-step.
#
# Only fires when:
#   - The command is `git commit` / `git push`
#   - The repo has assets/aesthetic-library/ in the working tree
#
# Fail-open on any setup error (script missing, uv not available): prefer
# CI to catch the gap rather than block the operator's workflow unrelated.
set -euo pipefail

INPUT="$(cat)"
TOOL="$(echo "$INPUT" | jq -r '.tool_name // empty' 2>/dev/null)" || exit 0

[ "$TOOL" = "Bash" ] || exit 0

CMD="$(echo "$INPUT" | jq -r '.tool_input.command // empty' 2>/dev/null)" || exit 0
[ -n "$CMD" ] || exit 0

# Only gate commit + push commands.
if ! echo "$CMD" | grep -qE '^\s*git\s+(commit|push)(\s|$)'; then
  exit 0
fi

# Only relevant when we're inside this repo's tree (has the script + assets).
if ! git rev-parse --is-inside-work-tree &>/dev/null; then
  exit 0
fi

REPO_ROOT="$(git rev-parse --show-toplevel)"
VERIFY_SCRIPT="$REPO_ROOT/scripts/verify-aesthetic-library.py"
ASSETS_ROOT="$REPO_ROOT/assets/aesthetic-library"

[ -f "$VERIFY_SCRIPT" ] || exit 0
[ -d "$ASSETS_ROOT" ] || exit 0

# Only gate if the current commit / push actually touches the aesthetic-library
# tree. For `git commit`, stage-diff is the relevant delta; for `git push`,
# any outstanding changes vs origin HEAD.
if echo "$CMD" | grep -qE '^\s*git\s+commit'; then
  if ! git diff --cached --name-only 2>/dev/null | grep -q '^assets/aesthetic-library/'; then
    exit 0
  fi
elif echo "$CMD" | grep -qE '^\s*git\s+push'; then
  branch="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || true)"
  [ -n "$branch" ] || exit 0
  if ! git diff "origin/main...HEAD" --name-only 2>/dev/null \
    | grep -q '^assets/aesthetic-library/'; then
    exit 0
  fi
fi

# Run the verify script. uv run keeps us inside the council venv.
cd "$REPO_ROOT"
if ! command -v uv &>/dev/null; then
  # Dev-env sanity: if uv isn't on PATH the operator is likely in a shell
  # that hasn't loaded direnv; skip rather than block.
  exit 0
fi

if ! uv run python "$VERIFY_SCRIPT" >/dev/null 2>/tmp/asset-provenance-gate.err; then
  echo "BLOCKED: aesthetic-library provenance gate failed." >&2
  echo "  $(echo "$CMD" | head -c 120)" >&2
  echo "" >&2
  cat /tmp/asset-provenance-gate.err >&2
  echo "" >&2
  echo "  Fix:" >&2
  echo "  - Regenerate manifest: uv run python scripts/generate-aesthetic-manifest.py" >&2
  echo "  - Add provenance.yaml for any new source group" >&2
  echo "  - Or run scripts/verify-aesthetic-library.py locally for details" >&2
  exit 2
fi

exit 0
