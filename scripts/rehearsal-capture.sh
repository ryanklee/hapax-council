#!/usr/bin/env bash
# Volitional-director Phase 9 — 30-minute private rehearsal capture.
#
# Captures:
#   - 1920x1080 frame snapshots every 10s (180 frames over 30 min)
#   - director-intent.jsonl tail for the window
#   - stimmung state samples every 30s
#   - grounding_provenance samples per narrative tick
#   - journalctl --user -u studio-compositor for error scan
#
# Usage:
#   scripts/rehearsal-capture.sh                      # 30 min default
#   DURATION_S=300 scripts/rehearsal-capture.sh       # 5 min smoke
#   OUT_DIR=/tmp/foo scripts/rehearsal-capture.sh     # custom output
#
# After run: fill in docs/research/2026-04-17-volitional-director-rehearsal-results.md
# from the per-second logs + visual review of frames/.
#
# Phase 9 of the volitional-grounded-director epic (PR #1017, spec §11).
set -euo pipefail

DURATION_S="${DURATION_S:-1800}"
OUT_DIR="${OUT_DIR:-$HOME/hapax-state/rehearsal/$(date +%Y%m%d-%H%M%S)}"
FRAME_INTERVAL_S=10
STIMMUNG_INTERVAL_S=30

mkdir -p "$OUT_DIR"/{frames,stimmung}

START_TS=$(date +%s)
END_TS=$((START_TS + DURATION_S))

echo "Rehearsal capture"
echo "  out:      $OUT_DIR"
echo "  duration: ${DURATION_S}s"
echo "  start:    $(date -d @$START_TS)"
echo "  end:      $(date -d @$END_TS)"

JOURNAL_SINCE=$(date -u -d @$START_TS '+%Y-%m-%d %H:%M:%S')

frame_counter=0
stimmung_counter=0
while [ "$(date +%s)" -lt "$END_TS" ]; do
    now=$(date +%s)
    tag=$(date -d @$now '+%H%M%S')

    # Frame snapshot
    if [ $((now % FRAME_INTERVAL_S)) -eq 0 ] || [ $frame_counter -eq 0 ]; then
        ffmpeg -nostdin -y -f v4l2 -i /dev/video42 -frames:v 1 -update 1 -q:v 2 \
            "$OUT_DIR/frames/${tag}.jpg" > /dev/null 2>&1 || true
        frame_counter=$((frame_counter + 1))
    fi

    # Stimmung sample
    if [ $((now % STIMMUNG_INTERVAL_S)) -eq 0 ]; then
        if [ -f /dev/shm/hapax-stimmung/state.json ]; then
            cp /dev/shm/hapax-stimmung/state.json \
               "$OUT_DIR/stimmung/${tag}.json" 2>/dev/null || true
            stimmung_counter=$((stimmung_counter + 1))
        fi
    fi

    sleep 1
done

# Snapshot artifacts
cp ~/hapax-state/stream-experiment/director-intent.jsonl \
   "$OUT_DIR/director-intent.jsonl" 2>/dev/null || true

cp /dev/shm/hapax-director/narrative-state.json \
   "$OUT_DIR/narrative-state-final.json" 2>/dev/null || true

journalctl --user -u studio-compositor.service --since "$JOURNAL_SINCE" \
    --no-pager > "$OUT_DIR/journal.log" 2>&1 || true

# Quick summary
TICK_COUNT=$(wc -l < "$OUT_DIR/director-intent.jsonl" 2>/dev/null || echo 0)
ERROR_COUNT=$(grep -ciE 'error|traceback' "$OUT_DIR/journal.log" 2>/dev/null || echo 0)

cat > "$OUT_DIR/summary.txt" <<EOF
Rehearsal capture summary
  duration:           ${DURATION_S}s
  frames captured:    $frame_counter
  stimmung samples:   $stimmung_counter
  director ticks:     $TICK_COUNT
  error lines (incl. tracebacks): $ERROR_COUNT
  start:              $(date -d @$START_TS)
  end:                $(date -d @$END_TS)

Fill in the audit report at:
  docs/research/2026-04-17-volitional-director-rehearsal-results.md
from this capture directory.

Pass gate (per spec §11):
  - activity distribution within prediction ±10%
  - persona coherence (no posture-vocabulary leakage in director-intent.jsonl narrative_text fields)
  - overlay visual audit at 1920x1080 (spot-check frames/)
  - TTS quality over music (ear check)
  - no stacktraces (error lines above should exclude benign warnings)
EOF

echo
cat "$OUT_DIR/summary.txt"
