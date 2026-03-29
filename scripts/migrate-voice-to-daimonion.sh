#!/usr/bin/env bash
# One-shot migration: move hapax-voice runtime data to hapax-daimonion.
# Run once after deploying the rename. Idempotent — safe to re-run.
set -euo pipefail

echo "=== Migrating hapax-voice → hapax-daimonion runtime data ==="

# Stop the old daemon
systemctl --user stop hapax-voice.service 2>/dev/null || true

# 1. Cache directory
if [ -d "$HOME/.cache/hapax-voice" ]; then
    mkdir -p "$HOME/.cache/hapax-daimonion"
    cp -a "$HOME/.cache/hapax-voice/"* "$HOME/.cache/hapax-daimonion/" 2>/dev/null || true
    echo "  copied ~/.cache/hapax-voice → ~/.cache/hapax-daimonion"
fi

# 2. Local share directory (speaker embeddings, wake word models, chimes, etc.)
if [ -d "$HOME/.local/share/hapax-voice" ]; then
    mkdir -p "$HOME/.local/share/hapax-daimonion"
    cp -a "$HOME/.local/share/hapax-voice/"* "$HOME/.local/share/hapax-daimonion/" 2>/dev/null || true
    echo "  copied ~/.local/share/hapax-voice → ~/.local/share/hapax-daimonion"
fi

# 3. Config directory
if [ -d "$HOME/.config/hapax-voice" ]; then
    mkdir -p "$HOME/.config/hapax-daimonion"
    cp -a "$HOME/.config/hapax-voice/"* "$HOME/.config/hapax-daimonion/" 2>/dev/null || true
    echo "  copied ~/.config/hapax-voice → ~/.config/hapax-daimonion"
fi

# 4. Shared memory (ephemeral — just ensure new dir exists)
mkdir -p /dev/shm/hapax-daimonion

# 5. Clean up old socket and PID file
rm -f "/run/user/$(id -u)/hapax-voice.sock"
rm -f "/run/user/$(id -u)/hapax-voice.pid"

# 6. Install new systemd unit, disable old
echo "  Installing hapax-daimonion.service..."
UNIT_SRC="$HOME/projects/hapax-council/systemd/units/hapax-daimonion.service"
UNIT_DST="$HOME/.config/systemd/user/hapax-daimonion.service"
if [ -f "$UNIT_SRC" ]; then
    cp "$UNIT_SRC" "$UNIT_DST"
fi
systemctl --user disable hapax-voice.service 2>/dev/null || true
rm -f "$HOME/.config/systemd/user/hapax-voice.service"

# 7. Update dependency units from repo
for unit in visual-layer-aggregator.service studio-compositor.service; do
    src="$HOME/projects/hapax-council/systemd/units/$unit"
    dst="$HOME/.config/systemd/user/$unit"
    [ -f "$src" ] && cp "$src" "$dst"
done

# 8. Update overrides
OVERRIDE_DIR="$HOME/.config/systemd/user/studio-compositor.service.d"
OVERRIDE_SRC="$HOME/projects/hapax-council/systemd/overrides/studio-compositor.service.d/ordering.conf"
if [ -f "$OVERRIDE_SRC" ]; then
    mkdir -p "$OVERRIDE_DIR"
    cp "$OVERRIDE_SRC" "$OVERRIDE_DIR/ordering.conf"
fi

# 9. Update rebuild-services unit
REBUILD_SRC="$HOME/projects/hapax-council/systemd/hapax-rebuild-services.service"
REBUILD_DST="$HOME/.config/systemd/user/hapax-rebuild-services.service"
[ -f "$REBUILD_SRC" ] && cp "$REBUILD_SRC" "$REBUILD_DST"

# 10. Reload and start
systemctl --user daemon-reload
systemctl --user enable hapax-daimonion.service
systemctl --user start hapax-daimonion.service

echo ""
echo "=== Migration complete ==="
echo "Old directories preserved (remove manually when confirmed working):"
echo "  rm -rf ~/.cache/hapax-voice"
echo "  rm -rf ~/.local/share/hapax-voice"
echo "  rm -rf ~/.config/hapax-voice"
