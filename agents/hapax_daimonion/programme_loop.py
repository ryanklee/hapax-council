"""ProgrammeManager tick loop — daimonion background task.

Closes B3 critical #4 + #5 wire-up gap from the 2026-04-20 audit.

The ProgrammeManager (``agents/programme_manager/manager.py``) is fully
implemented but had no production runner — its lifecycle metrics
(``hapax_programme_start_total`` / ``_end_total`` / ``_active``), the
JSONL outcome log under ``~/hapax-state/programmes/<show>/<id>.jsonl``,
and the 5 named abort predicates (``operator_left_room_for_10min``,
``impingement_pressure_above_0.8_for_3min``, ``consent_contract_expired``,
``vinyl_side_a_finished``, ``operator_voice_contradicts_programme_intent``)
all stayed dormant because nothing ticked the manager.

This loop wires it. Spawned from ``run_inner._make_task`` like every
other daimonion background task; supervised under RECREATE policy so
crashes are restarted with backoff. Cadence is 1 Hz — programmes are
minutes-long; faster ticks are wasted work.

When the store has no scheduled programmes, ``tick()`` returns a
no-boundary decision and the loop sleeps. This is the steady state
when the operator hasn't authored any plans yet — the loop must NOT
make programmes its own concern.
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agents.hapax_daimonion.daemon import VoiceDaemon

log = logging.getLogger(__name__)

PROGRAMME_TICK_INTERVAL_S = 1.0


def _build_manager():
    """Construct the production ProgrammeManager.

    Late imports keep daimonion startup fast when programmes aren't
    in use — the heavy programme_manager + shared.programme_store
    modules only load when this loop fires.
    """
    from agents.programme_manager.abort_predicates import (
        DEFAULT_ABORT_PREDICATES,
    )
    from agents.programme_manager.manager import ProgrammeManager
    from agents.programme_manager.transition import TransitionChoreographer
    from shared.programme_store import default_store

    return ProgrammeManager(
        store=default_store(),
        choreographer=TransitionChoreographer(),
        abort_predicates=dict(DEFAULT_ABORT_PREDICATES),
    )


async def programme_manager_loop(daemon: VoiceDaemon) -> None:
    """Tick the ProgrammeManager at 1 Hz while the daemon runs.

    Errors are logged but never propagate — a bad programme plan must
    never take the daemon down. The loop also tolerates a lazy
    construction failure (missing dependency, broken import) and
    re-attempts on the next tick rather than spinning at full CPU.
    """
    manager = None
    construction_warned_at: float | None = None
    log.info("programme_manager_loop starting (tick interval %.1fs)", PROGRAMME_TICK_INTERVAL_S)

    while daemon._running:
        if manager is None:
            try:
                manager = _build_manager()
                log.info("programme_manager_loop: ProgrammeManager constructed")
            except Exception:
                # Throttle the warning so a persistent construction
                # failure doesn't flood the log; once per minute is
                # enough for the operator to notice.
                import time as _time

                now = _time.monotonic()
                if construction_warned_at is None or now - construction_warned_at > 60.0:
                    log.warning("programme_manager construction failed", exc_info=True)
                    construction_warned_at = now
                await asyncio.sleep(PROGRAMME_TICK_INTERVAL_S)
                continue

        try:
            decision = manager.tick()
            if decision.trigger.value != "none":
                log.info(
                    "programme transition: %s (%s → %s)",
                    decision.trigger.value,
                    getattr(decision.from_programme, "programme_id", None),
                    getattr(decision.to_programme, "programme_id", None),
                )
        except Exception:
            log.warning("programme_manager.tick raised", exc_info=True)

        await asyncio.sleep(PROGRAMME_TICK_INTERVAL_S)


__all__ = ["PROGRAMME_TICK_INTERVAL_S", "programme_manager_loop"]
