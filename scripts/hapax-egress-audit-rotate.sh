#!/usr/bin/env bash
# hapax-egress-audit-rotate — daily rotate + prune of the demonet
# egress audit JSONL. Runs as a oneshot under
# hapax-egress-audit-rotate.timer at 04:00 local (off-peak, after
# the systemd-reconcile daily sweep at 03:15).
#
# Calls the Python module's rotate() + prune_old_archives(30) so
# the retention logic stays in Pydantic-land, not shell.
#
# Exit codes:
#   0 — rotate + prune completed (possibly no-op on empty live file)
#   1 — Python module raised
#   2 — interpreter not reachable
#
# Reference:
#   docs/superpowers/handoff/2026-04-20-delta-wsjf-reorganization.md §4.11 D-23
#   shared/governance/monetization_egress_audit.py

set -euo pipefail

REPO_ROOT="${HAPAX_COUNCIL_DIR:-/home/hapax/projects/hapax-council}"
VENV_PY="$REPO_ROOT/.venv/bin/python"

if [ ! -x "$VENV_PY" ]; then
    echo "error: $VENV_PY not executable — venv not bootstrapped?" >&2
    exit 2
fi

exec "$VENV_PY" -c "
from shared.governance.monetization_egress_audit import default_writer
writer = default_writer()
archive = writer.rotate()
if archive is None:
    print('egress-audit-rotate: nothing to rotate (live file empty/missing)')
else:
    print(f'egress-audit-rotate: rotated to {archive.name}')
pruned = writer.prune_old_archives(retention_days=30)
print(f'egress-audit-rotate: pruned {len(pruned)} archive(s) older than 30 days')
"
