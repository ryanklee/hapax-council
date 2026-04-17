#!/usr/bin/env python3
"""Continuous-Loop Research Cadence §3.6 — environmental-salience timer driver.

One-shot tick that:

1. Reads the current ``last_emphasis_at`` from
   ``/dev/shm/hapax-environmental-emphasis/state.json`` (atomic).
2. Calls :func:`recommend_emphasis` on the current IR + objectives
   state to see whether the compositor should promote a camera role.
3. If a recommendation is returned, writes the recommended hero role
   into the compositor's hero-override file and refreshes
   ``last_emphasis_at`` in the state file.

Intended to run from ``systemd/units/hapax-environmental-emphasis.timer``
at a 30-second cadence. Failures are logged + the process exits cleanly
so a single hiccup doesn't cascade — the timer will retry on the next
tick.

No CLI args. Environment overrides for test harnesses:

* ``HAPAX_ENV_EMPHASIS_STATE_FILE`` — override state JSON path
* ``HAPAX_ENV_EMPHASIS_HERO_FILE`` — override the hero-override file
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
from pathlib import Path

log = logging.getLogger("environmental-emphasis-tick")

STATE_FILE = Path("/dev/shm/hapax-environmental-emphasis/state.json")
HERO_OVERRIDE_FILE = Path("/dev/shm/hapax-compositor/environmental-hero-override.json")


def _read_last_emphasis_at(path: Path) -> float:
    if not path.exists():
        return 0.0
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return 0.0
    try:
        return float(data.get("last_emphasis_at", 0.0))
    except (TypeError, ValueError):
        return 0.0


def _write_last_emphasis_at(path: Path, ts: float) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps({"last_emphasis_at": ts}, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, path)


def _write_hero_override(path: Path, role: str, reason: str, salience: float, ts: float) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(
        json.dumps(
            {
                "hero_role": role,
                "reason": reason,
                "salience_score": salience,
                "ts": ts,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    os.replace(tmp, path)


def tick(*, now_monotonic: float | None = None, now_epoch: float | None = None) -> int:
    """Run one tick. Returns exit code (0 = fine, 1 = recoverable error)."""
    from agents.studio_compositor.environmental_salience_emphasis import recommend_emphasis

    state_file = Path(os.environ.get("HAPAX_ENV_EMPHASIS_STATE_FILE") or STATE_FILE)
    hero_file = Path(os.environ.get("HAPAX_ENV_EMPHASIS_HERO_FILE") or HERO_OVERRIDE_FILE)

    mono = now_monotonic if now_monotonic is not None else time.monotonic()
    epoch = now_epoch if now_epoch is not None else time.time()

    last_at = _read_last_emphasis_at(state_file)

    recommendation = recommend_emphasis(
        now_monotonic=mono,
        last_emphasis_at=last_at,
    )
    if recommendation is None:
        log.debug("no emphasis recommendation this tick")
        return 0

    try:
        _write_hero_override(
            hero_file,
            recommendation.camera_role,
            recommendation.reason,
            recommendation.salience_score,
            epoch,
        )
        _write_last_emphasis_at(state_file, mono)
    except OSError:
        log.exception("failed to write hero override / state file")
        return 1

    log.info(
        "environmental emphasis: camera_role=%s reason=%s salience=%.2f",
        recommendation.camera_role,
        recommendation.reason,
        recommendation.salience_score,
    )
    return 0


def main() -> int:
    logging.basicConfig(
        level=os.environ.get("HAPAX_LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    return tick()


if __name__ == "__main__":
    sys.exit(main())
