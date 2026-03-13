#!/usr/bin/env bash
# pip-guard.sh — PreToolUse hook that blocks direct pip usage.
# Policy: NEVER use pip directly — always use uv for Python package management.
#
# Allowed: pip freeze, pip list (read-only), uv pip ... (going through uv)
# Blocked: pip install, pip uninstall, python -m pip, etc.
#
# Returns exit 2 to block the tool call with a message.
# Fails open on errors (any parse failure → allow).
set -euo pipefail

INPUT="$(cat)" || exit 0
TOOL="$(echo "$INPUT" | jq -r '.tool_name // empty' 2>/dev/null)" || exit 0

# Only act on Bash tool calls
[ "$TOOL" = "Bash" ] || exit 0

CMD="$(echo "$INPUT" | jq -r '.tool_input.command // empty' 2>/dev/null)" || exit 0
[ -n "$CMD" ] || exit 0

# Strip out "uv pip" so it doesn't false-positive on the pip patterns below.
# We do the check on a sanitised copy; the real command is untouched.
CHECK="$(echo "$CMD" | sed 's/uv pip/uv_pip/g')"

# Block direct pip / pip3 / python -m pip usage (install, uninstall, etc.)
# Allow read-only commands: pip freeze, pip list
if echo "$CHECK" | grep -qE '\bpip3?\s+(install|uninstall)\b'; then
    echo "BLOCKED: Direct pip usage is not allowed. Use 'uv pip install', 'uv add', or 'uv sync' instead." >&2
    exit 2
fi

if echo "$CHECK" | grep -qE '\bpython3?\s+-m\s+pip\b'; then
    echo "BLOCKED: Direct pip usage is not allowed. Use 'uv pip install', 'uv add', or 'uv sync' instead." >&2
    exit 2
fi

exit 0
