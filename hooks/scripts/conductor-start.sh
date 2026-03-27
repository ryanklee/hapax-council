#!/usr/bin/env bash
# conductor-start.sh — SessionStart hook: launch conductor sidecar
set -euo pipefail

INPUT="$(cat)"
SESSION_ID="$(echo "$INPUT" | jq -r '.session_id // empty' 2>/dev/null)"
[ -z "$SESSION_ID" ] && exit 0

COUNCIL_DIR="$HOME/projects/hapax-council"
PID_DIR="$HOME/.cache/hapax/conductor"

# Detect role from worktree
ROLE="alpha"
CWD="$(pwd)"
if echo "$CWD" | grep -q "\-\-beta"; then
    ROLE="beta"
fi

# Don't launch if already running for this session
if [ -f "$PID_DIR/$SESSION_ID.pid" ]; then
    EXISTING_PID="$(cat "$PID_DIR/$SESSION_ID.pid")"
    if kill -0 "$EXISTING_PID" 2>/dev/null; then
        exit 0
    fi
fi

# Launch conductor as background process in a systemd scope
systemd-run --user --scope --quiet \
    --unit="conductor-${SESSION_ID:0:8}" \
    --description="Session Conductor for $SESSION_ID" \
    "$HOME/.local/bin/uv" run \
    --directory "$COUNCIL_DIR" \
    python -m agents.session_conductor start \
    --session-id "$SESSION_ID" \
    --cc-pid "$PPID" \
    --role "$ROLE" \
    &>/dev/null &

# Wait for socket to appear (up to 3 seconds)
SOCK="/run/user/$(id -u)/conductor-${SESSION_ID}.sock"
for i in $(seq 1 30); do
    [ -S "$SOCK" ] && break
    sleep 0.1
done

# Inject spawn context if this is a child session
CONTEXT_FILE="$PID_DIR/$SESSION_ID.spawn-context"
if [ -f "$CONTEXT_FILE" ]; then
    cat "$CONTEXT_FILE"
    rm -f "$CONTEXT_FILE"
fi
