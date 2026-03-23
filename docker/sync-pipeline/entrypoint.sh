#!/usr/bin/env bash
set -euo pipefail

WORKING_MODE="${WORKING_MODE:-rnd}"
CRONTAB_DIR="/app/sync-pipeline"

echo "sync-pipeline: starting with WORKING_MODE=${WORKING_MODE}"

# Select crontab based on cycle mode
CRONTAB="${CRONTAB_DIR}/crontab.${WORKING_MODE}"
if [ ! -f "$CRONTAB" ]; then
    echo "sync-pipeline: ERROR — no crontab for mode '${WORKING_MODE}'" >&2
    exit 1
fi

# Verify Qdrant is reachable
QDRANT_URL="${QDRANT_URL:-http://127.0.0.1:6333}"
echo "sync-pipeline: waiting for Qdrant at ${QDRANT_URL} ..."
for i in $(seq 1 30); do
    if curl -sf "${QDRANT_URL}/healthz" >/dev/null 2>&1; then
        echo "sync-pipeline: Qdrant ready"
        break
    fi
    if [ "$i" -eq 30 ]; then
        echo "sync-pipeline: WARNING — Qdrant not reachable (continuing anyway)" >&2
        break
    fi
    sleep 1
done

# Log installed schedule
echo "sync-pipeline: schedule (${WORKING_MODE}):"
grep -v '^#' "$CRONTAB" | grep -v '^$'

# Run supercronic in foreground
# supercronic inherits the full process environment (unlike vixie-cron)
# and routes all job output to stdout/stderr (visible in docker logs)
echo "sync-pipeline: starting supercronic"
exec supercronic "$CRONTAB"
