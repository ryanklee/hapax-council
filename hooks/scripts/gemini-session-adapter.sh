#!/usr/bin/env bash
# gemini-session-adapter.sh — Wraps a Claude Code SessionStart/Stop hook
# for Gemini CLI's SessionStart/SessionEnd protocol.
#
# Claude Code SessionStart hooks output plain text to stdout.
# Gemini CLI SessionStart hooks must output JSON:
#   {"hookSpecificOutput": {"additionalContext": "<text>"}}
#
# Usage (in ~/.gemini/settings.json):
#   "command": "/path/to/gemini-session-adapter.sh /path/to/claude-hook.sh"
set -euo pipefail

DELEGATE="$1"
[ -x "$DELEGATE" ] || { echo "gemini-session-adapter: delegate not executable: $DELEGATE" >&2; exit 0; }

# Pipe stdin to delegate, capture stdout
OUTPUT="$(echo '{}' | "$DELEGATE" 2>/dev/null)" || true

if [ -n "$OUTPUT" ]; then
  # Escape the output for JSON embedding
  ESCAPED="$(printf '%s' "$OUTPUT" | jq -Rs .)"
  printf '{"hookSpecificOutput":{"additionalContext":%s}}' "$ESCAPED"
fi

exit 0
