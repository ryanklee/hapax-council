#!/usr/bin/env bash
# install-units.sh — Copy systemd user units from repo to ~/.config/systemd/user/
# and reload the daemon. Safe to run idempotently.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/../units" && pwd)"
PROJECT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
DEST_DIR="${HOME}/.config/systemd/user"

# Ensure all optional dependency groups are installed.
# Services run via `uv run` which uses the default venv — if optional
# extras (sync-pipeline, logos-api, audio) aren't installed, agents
# crash with ModuleNotFoundError at runtime.
echo "Syncing venv with all extras..."
(cd "$PROJECT_DIR" && uv sync --all-extras --quiet)
echo "venv synced"

mkdir -p "$DEST_DIR"

copied=0
for unit in "$REPO_DIR"/*.service "$REPO_DIR"/*.timer; do
    [ -f "$unit" ] || continue
    name="$(basename "$unit")"
    if ! cmp -s "$unit" "$DEST_DIR/$name" 2>/dev/null; then
        cp "$unit" "$DEST_DIR/$name"
        echo "updated: $name"
        copied=$((copied + 1))
    fi
done

if [ "$copied" -gt 0 ]; then
    systemctl --user daemon-reload
    echo "daemon-reload done ($copied units updated)"
else
    echo "all units up to date"
fi
