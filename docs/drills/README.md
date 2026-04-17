# LRR Phase 10 item 4 — operational drill results

Each drill is run via `uv run python scripts/run_drill.py <drill-name>` and
writes a timestamped markdown doc in this directory. The harness captures
pre-checks, steps executed, post-checks, and leaves an "Operator notes"
section for you to fill in.

The six drills that must run at least once per LRR Phase 10 §3.4:

- `pre-stream-consent` — broadcast-consent coverage before going public
- `mid-stream-consent-revocation` — re-run of Phase 6 §7 revocation drill
- `stimmung-breach-auto-private` — critical stimmung → auto-private transition
- `failure-mode-rehearsal` — RTMP / model OOM / MediaMTX / v4l2loopback / Pi-6
- `privacy-regression-suite` — redaction + consent tests under load
- `audience-engagement-ab` — research-mode chat-reactor A/B window comparison

Dry-run (default) reports steps without touching live services. `--live`
executes the side-effectful steps — use with intent and make sure the
pre-stream state is snapshotted first.
