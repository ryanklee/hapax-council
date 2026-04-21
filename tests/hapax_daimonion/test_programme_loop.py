"""Tests for hapax_daimonion.programme_loop — B3 wire-up gap closer."""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock, patch

import pytest

from agents.hapax_daimonion.programme_loop import (
    PROGRAMME_TICK_INTERVAL_S,
    programme_manager_loop,
)


class _FakeDaemon:
    def __init__(self) -> None:
        self._running = True


def _make_decision(trigger_value: str = "none"):
    """Build a BoundaryDecision-shaped object the loop will read."""
    decision = MagicMock()
    decision.trigger.value = trigger_value
    # Default to None for the no-boundary case; tests overwrite to mocks
    # when they want the loop to surface the from/to programme IDs.
    decision.from_programme = None
    decision.to_programme = None
    return decision


def _decision_with_programmes(*, trigger: str, from_id: str | None, to_id: str | None):
    """Decision shape with from/to programme mocks."""
    decision = MagicMock()
    decision.trigger.value = trigger
    decision.from_programme = MagicMock(programme_id=from_id) if from_id else None
    decision.to_programme = MagicMock(programme_id=to_id) if to_id else None
    return decision


# ── Build path ────────────────────────────────────────────────────────


def test_constants_exist() -> None:
    assert PROGRAMME_TICK_INTERVAL_S == 1.0


# ── Loop behavior ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_loop_ticks_manager_until_daemon_stops() -> None:
    """Loop calls manager.tick() at least once before daemon._running flips."""
    daemon = _FakeDaemon()
    fake_manager = MagicMock()
    fake_manager.tick.return_value = _make_decision("none")

    with patch("agents.hapax_daimonion.programme_loop._build_manager", return_value=fake_manager):
        loop_task = asyncio.create_task(programme_manager_loop(daemon))
        # Give the loop one tick window
        await asyncio.sleep(PROGRAMME_TICK_INTERVAL_S + 0.3)
        daemon._running = False
        await asyncio.wait_for(loop_task, timeout=PROGRAMME_TICK_INTERVAL_S + 1.0)

    assert fake_manager.tick.call_count >= 1


@pytest.mark.asyncio
async def test_loop_logs_transition_when_trigger_fires(caplog) -> None:
    """A non-NONE trigger logs an INFO line so operator sees the boundary."""
    import logging as _logging

    daemon = _FakeDaemon()
    fake_manager = MagicMock()
    fake_manager.tick.return_value = _decision_with_programmes(
        trigger="planned", from_id="p_warmup", to_id="p_main"
    )

    with (
        patch("agents.hapax_daimonion.programme_loop._build_manager", return_value=fake_manager),
        caplog.at_level(_logging.INFO, logger="agents.hapax_daimonion.programme_loop"),
    ):
        loop_task = asyncio.create_task(programme_manager_loop(daemon))
        await asyncio.sleep(PROGRAMME_TICK_INTERVAL_S + 0.3)
        daemon._running = False
        await asyncio.wait_for(loop_task, timeout=PROGRAMME_TICK_INTERVAL_S + 1.0)

    transitions = [r for r in caplog.records if "programme transition" in r.message]
    assert transitions, "expected a programme transition log line"


@pytest.mark.asyncio
async def test_loop_swallows_tick_exceptions() -> None:
    """A buggy tick() must not crash the loop — log + continue."""
    daemon = _FakeDaemon()
    fake_manager = MagicMock()
    fake_manager.tick.side_effect = RuntimeError("plan corrupted")

    with patch("agents.hapax_daimonion.programme_loop._build_manager", return_value=fake_manager):
        loop_task = asyncio.create_task(programme_manager_loop(daemon))
        await asyncio.sleep(PROGRAMME_TICK_INTERVAL_S + 0.3)
        daemon._running = False
        await asyncio.wait_for(loop_task, timeout=PROGRAMME_TICK_INTERVAL_S + 1.0)

    # The loop kept ticking despite tick() raising every time
    assert fake_manager.tick.call_count >= 1


@pytest.mark.asyncio
async def test_loop_retries_after_construction_failure(caplog) -> None:
    """A persistent construction failure should warn (throttled) but not spin
    at 100% CPU — the loop sleeps the same interval between retries."""
    import logging as _logging

    daemon = _FakeDaemon()
    construct_calls = {"n": 0}

    def boom():
        construct_calls["n"] += 1
        raise ImportError("module missing")

    with (
        patch("agents.hapax_daimonion.programme_loop._build_manager", side_effect=boom),
        caplog.at_level(_logging.WARNING, logger="agents.hapax_daimonion.programme_loop"),
    ):
        loop_task = asyncio.create_task(programme_manager_loop(daemon))
        await asyncio.sleep(PROGRAMME_TICK_INTERVAL_S + 0.3)
        daemon._running = False
        await asyncio.wait_for(loop_task, timeout=PROGRAMME_TICK_INTERVAL_S + 1.0)

    # Construction was attempted once per tick — at least 1 attempt
    assert construct_calls["n"] >= 1
    warnings = [r for r in caplog.records if "construction failed" in r.message]
    # Throttled to at most one warning in this short window
    assert 1 <= len(warnings) <= 2


@pytest.mark.asyncio
async def test_loop_exits_when_daemon_running_false_at_start() -> None:
    """Daemon already shutting down → loop exits without ticking."""
    daemon = _FakeDaemon()
    daemon._running = False
    fake_manager = MagicMock()
    fake_manager.tick.return_value = _make_decision("none")

    with patch("agents.hapax_daimonion.programme_loop._build_manager", return_value=fake_manager):
        await asyncio.wait_for(programme_manager_loop(daemon), timeout=2.0)

    assert fake_manager.tick.call_count == 0
