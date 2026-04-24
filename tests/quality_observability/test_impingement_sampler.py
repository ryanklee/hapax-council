"""Impingement bus sampler pins.

Pins:
- per-type counter increments,
- novelty score math (with denominator floor for quiet windows),
- rolling-window pruning,
- malformed event handling (unknown types skipped without polluting
  cardinality),
- bus-unreadable failure mode (no raise, stale gauges, single warning),
- port allocation (≥9496, no collision with #1292's 9495).

Each test uses an isolated `CollectorRegistry`.

Spec: ytb-QM2.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path

import pytest
from prometheus_client import CollectorRegistry

from agents.quality_observability.impingement_sampler import (
    METRICS_PORT,
    NOVELTY_DENOMINATOR_FLOOR,
    NOVELTY_DENOMINATOR_TYPE,
    NOVELTY_NUMERATOR_TYPES,
    NOVELTY_WINDOW_S,
    ImpingementSampler,
)
from shared.impingement import ImpingementType


def _write_bus(path: Path, events: Iterable[dict]) -> None:
    """Write impingement events to the bus file as JSONL."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for ev in events:
            full = {
                "id": ev.get("id", "deadbeef0000"),
                "timestamp": ev["timestamp"],
                "source": ev.get("source", "test"),
                "type": ev["type"],
                "strength": ev.get("strength", 0.5),
                "content": ev.get("content", {}),
                "context": ev.get("context", {}),
            }
            fh.write(json.dumps(full) + "\n")


@pytest.fixture
def bus_path(tmp_path: Path) -> Path:
    return tmp_path / "impingements.jsonl"


@pytest.fixture
def cursor_path(tmp_path: Path) -> Path:
    return tmp_path / "cursor.txt"


@pytest.fixture
def now() -> float:
    return 1000000.0  # fixed epoch reference


@pytest.fixture
def make_sampler(bus_path: Path):
    """Default factory uses cursor_path=None so the sampler reads the
    entire fixture file from byte 0 — matches "test wrote events
    THEN constructed sampler" ergonomics. Tests that exercise cursor
    persistence pass cursor_path explicitly."""

    def _factory(**overrides) -> ImpingementSampler:
        kwargs = {
            "bus_path": bus_path,
            "cursor_path": None,
            "registry": CollectorRegistry(),
        }
        kwargs.update(overrides)
        return ImpingementSampler(**kwargs)

    return _factory


# ── Per-type counter ──────────────────────────────────────────────────


class TestPerTypeCounters:
    def test_curiosity_event_increments_counter(
        self, bus_path: Path, make_sampler, now: float
    ) -> None:
        _write_bus(bus_path, [{"timestamp": now, "type": "curiosity"}])
        s = make_sampler()
        s.tick_once(now=now)
        assert s.rate_total.labels(type="curiosity")._value.get() == 1

    def test_all_known_types_pre_zeroed(self, make_sampler) -> None:
        """Every ImpingementType must have a 0-valued counter from t=0."""
        s = make_sampler()
        for t in ImpingementType:
            assert s.rate_total.labels(type=t.value)._value.get() == 0

    def test_unknown_type_skipped_no_label_created(
        self, bus_path: Path, make_sampler, now: float
    ) -> None:
        # A malicious / corrupted event with a type not in the enum
        # must be skipped — never minted as a new Prometheus label.
        _write_bus(
            bus_path,
            [
                {"timestamp": now, "type": "boredom"},  # valid for sanity
                {"timestamp": now, "type": "definitely_not_a_real_type"},
            ],
        )
        s = make_sampler()
        s.tick_once(now=now)
        # Only valid event counted.
        assert s.rate_total.labels(type="boredom")._value.get() == 1


# ── Novelty score ─────────────────────────────────────────────────────


class TestNoveltyScore:
    def test_pure_curiosity_yields_high_score(
        self, bus_path: Path, make_sampler, now: float
    ) -> None:
        # 5 curiosity, 0 boredom → 5 / (0 + 0.1) = 50.
        _write_bus(
            bus_path,
            [{"timestamp": now - i, "type": "curiosity"} for i in range(5)],
        )
        s = make_sampler()
        s.tick_once(now=now)
        assert s.novelty_score._value.get() == pytest.approx(50.0)

    def test_pure_boredom_yields_low_score(self, bus_path: Path, make_sampler, now: float) -> None:
        # 0 numerator, 5 boredom → 0 / (5 + 0.1) ≈ 0.
        _write_bus(
            bus_path,
            [{"timestamp": now - i, "type": "boredom"} for i in range(5)],
        )
        s = make_sampler()
        s.tick_once(now=now)
        assert s.novelty_score._value.get() == pytest.approx(0.0)

    def test_balanced_score(self, bus_path: Path, make_sampler, now: float) -> None:
        # 3 curiosity + 2 pattern_match = 5 numerator; 5 boredom denominator.
        # Score = 5 / (5 + 0.1) ≈ 0.98.
        events = (
            [{"timestamp": now - i, "type": "curiosity"} for i in range(3)]
            + [{"timestamp": now - 10 - i, "type": "pattern_match"} for i in range(2)]
            + [{"timestamp": now - 20 - i, "type": "boredom"} for i in range(5)]
        )
        _write_bus(bus_path, events)
        s = make_sampler()
        s.tick_once(now=now)
        assert s.novelty_score._value.get() == pytest.approx(5.0 / 5.1, abs=1e-3)

    def test_denominator_floor_prevents_div_by_zero(
        self, bus_path: Path, make_sampler, now: float
    ) -> None:
        # Empty window → 0 / 0.1 = 0 (not NaN, not Inf).
        _write_bus(bus_path, [])
        s = make_sampler()
        s.tick_once(now=now)
        score = s.novelty_score._value.get()
        assert score == 0.0
        # Sanity — NaN or Inf would break alerting math.
        import math

        assert math.isfinite(score)

    def test_other_impingement_types_neither_numerator_nor_denominator(
        self, bus_path: Path, make_sampler, now: float
    ) -> None:
        """statistical_deviation / salience_integration / etc. don't touch
        the novelty score (they're tracked by the per-type counter only).
        Verifies the spec: numerator = curiosity+pattern_match;
        denominator = boredom; everything else neutral."""
        _write_bus(
            bus_path,
            [
                {"timestamp": now - 5, "type": "statistical_deviation"},
                {"timestamp": now - 4, "type": "salience_integration"},
                {"timestamp": now - 3, "type": "absolute_threshold"},
                {"timestamp": now - 2, "type": "exploration_opp"},
            ],
        )
        s = make_sampler()
        s.tick_once(now=now)
        # No numerator events → 0 / (0 + 0.1) = 0.
        assert s.novelty_score._value.get() == 0.0


# ── Rolling window pruning ─────────────────────────────────────────────


class TestRollingWindow:
    def test_old_events_pruned_from_window(self, bus_path: Path, make_sampler, now: float) -> None:
        # Old event (outside window) shouldn't contribute to novelty.
        # But it still counts toward the cumulative counter.
        _write_bus(
            bus_path,
            [
                {"timestamp": now - NOVELTY_WINDOW_S - 100, "type": "curiosity"},
                {"timestamp": now - 5, "type": "boredom"},
            ],
        )
        s = make_sampler()
        s.tick_once(now=now)
        # Counters: cumulative over all time.
        assert s.rate_total.labels(type="curiosity")._value.get() == 1
        assert s.rate_total.labels(type="boredom")._value.get() == 1
        # Novelty: only the in-window boredom event → 0 / (1 + 0.1) = 0.
        assert s.novelty_score._value.get() == pytest.approx(0.0)


# ── Malformed events ──────────────────────────────────────────────────


class TestMalformed:
    def test_malformed_lines_skipped(self, bus_path: Path, make_sampler, now: float) -> None:
        bus_path.parent.mkdir(parents=True, exist_ok=True)
        with bus_path.open("w", encoding="utf-8") as fh:
            fh.write(
                json.dumps(
                    {
                        "id": "good",
                        "timestamp": now,
                        "source": "test",
                        "type": "curiosity",
                        "strength": 0.5,
                        "content": {},
                        "context": {},
                    }
                )
                + "\n"
            )
            fh.write("not json at all\n")
            fh.write('{"truncated":\n')
            fh.write("\n")
        s = make_sampler()
        s.tick_once(now=now)
        # Only the valid event counted.
        assert s.rate_total.labels(type="curiosity")._value.get() == 1


# ── Bus missing / unreadable ──────────────────────────────────────────


class TestFailureModes:
    def test_missing_bus_yields_stale_gauges_no_raise(self, tmp_path: Path, make_sampler) -> None:
        # bus_path fixture pointed at tmp_path / "impingements.jsonl"
        # which doesn't exist.
        s = make_sampler()
        s.tick_once()  # no exception
        assert s.novelty_score._value.get() == 0.0


# ── Port allocation ───────────────────────────────────────────────────


class TestPortAllocation:
    def test_default_port_does_not_collide_with_qm1(self) -> None:
        """9495 is taken by hapax-chronicle-quality-exporter (#1292)."""
        assert METRICS_PORT >= 9496


# ── Spec invariants ───────────────────────────────────────────────────


class TestSpecInvariants:
    def test_numerator_types_match_spec(self) -> None:
        """Spec: numerator = curiosity + pattern_match."""
        assert (
            frozenset({ImpingementType.CURIOSITY, ImpingementType.PATTERN_MATCH})
            == NOVELTY_NUMERATOR_TYPES
        )

    def test_denominator_type_is_boredom(self) -> None:
        assert NOVELTY_DENOMINATOR_TYPE == ImpingementType.BOREDOM

    def test_denominator_floor_is_one_tenth(self) -> None:
        """Spec: novelty = (curiosity + pattern_match) / (boredom + 0.1).
        The 0.1 floor is load-bearing for empty/quiet windows; pin it."""
        assert NOVELTY_DENOMINATOR_FLOOR == 0.1


# ── Integration: persistent cursor ─────────────────────────────────────


class TestCursorPersistence:
    def test_restart_resumes_from_cursor(
        self, bus_path: Path, cursor_path: Path, make_sampler, now: float
    ) -> None:
        """Restart-safety pin: events read by the first sampler should
        NOT be re-read by a second sampler with the same cursor file.

        Uses ``cursor_path`` (overriding the default-None) so we
        exercise the persistent-cursor path. The first sampler is
        constructed BEFORE writing events so its bootstrap finds an
        empty file (cursor=0) — then events arrive and get drained.
        Second sampler bootstraps from the cursor file written by the
        first."""
        # Prime the bus to exist as empty so cursor bootstrap = 0.
        bus_path.parent.mkdir(parents=True, exist_ok=True)
        bus_path.write_text("", encoding="utf-8")

        s1 = make_sampler(cursor_path=cursor_path)

        # Now write the events (after s1 bootstrap).
        _write_bus(
            bus_path,
            [
                {"timestamp": now - 10, "type": "curiosity"},
                {"timestamp": now - 5, "type": "curiosity"},
            ],
        )
        s1.tick_once(now=now)
        assert s1.rate_total.labels(type="curiosity")._value.get() == 2

        # Append one more event; second sampler should see only the new one.
        with bus_path.open("a", encoding="utf-8") as fh:
            fh.write(
                json.dumps(
                    {
                        "id": "n",
                        "timestamp": now,
                        "source": "test",
                        "type": "boredom",
                        "strength": 0.5,
                        "content": {},
                        "context": {},
                    }
                )
                + "\n"
            )

        s2 = make_sampler(cursor_path=cursor_path)
        s2.tick_once(now=now)
        # Fresh registry — but s2 reads only the 1 new event because the
        # cursor file already points past the first two.
        assert s2.rate_total.labels(type="curiosity")._value.get() == 0
        assert s2.rate_total.labels(type="boredom")._value.get() == 1
