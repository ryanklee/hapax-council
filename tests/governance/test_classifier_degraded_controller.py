"""Tests for ClassifierDegradedController — hysteresis state machine (#202 D-14)."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

import pytest

from shared.governance.classifier_degraded_controller import (
    DEGRADE_THRESHOLD,
    RESTORE_THRESHOLD,
    ClassifierDegradedController,
    ClassifierHealthState,
)


class TestInitialState:
    def test_starts_nominal(self) -> None:
        c = ClassifierDegradedController()
        assert c.is_degraded() is False
        snap = c.snapshot()
        assert snap.state == ClassifierHealthState.NOMINAL
        assert snap.consecutive_failures == 0
        assert snap.consecutive_successes == 0


class TestFailureAccumulation:
    def test_one_failure_does_not_degrade(self) -> None:
        c = ClassifierDegradedController()
        c.record_failure("timeout")
        assert c.is_degraded() is False

    def test_threshold_minus_one_does_not_degrade(self) -> None:
        c = ClassifierDegradedController()
        for _ in range(DEGRADE_THRESHOLD - 1):
            c.record_failure("timeout")
        assert c.is_degraded() is False

    def test_threshold_failures_triggers_degrade(self) -> None:
        c = ClassifierDegradedController()
        for _ in range(DEGRADE_THRESHOLD):
            c.record_failure("backend down")
        assert c.is_degraded() is True

    def test_intervening_success_resets_failure_count(self) -> None:
        """A single success within a failure run prevents degrade."""
        c = ClassifierDegradedController()
        c.record_failure("timeout")
        c.record_failure("timeout")
        c.record_success()  # resets consecutive_failures
        c.record_failure("timeout")
        c.record_failure("timeout")
        # Only 2 consecutive failures since the success — below threshold.
        assert c.is_degraded() is False


class TestRestore:
    def test_restore_requires_threshold_successes(self) -> None:
        c = ClassifierDegradedController()
        # Drive into degrade.
        for _ in range(DEGRADE_THRESHOLD):
            c.record_failure("x")
        assert c.is_degraded() is True
        # threshold-1 successes — still degraded.
        for _ in range(RESTORE_THRESHOLD - 1):
            c.record_success()
        assert c.is_degraded() is True
        # One more → restore.
        c.record_success()
        assert c.is_degraded() is False

    def test_failure_during_recovery_resets_success_count(self) -> None:
        c = ClassifierDegradedController()
        for _ in range(DEGRADE_THRESHOLD):
            c.record_failure("x")
        assert c.is_degraded() is True
        # Partial recovery then setback.
        for _ in range(RESTORE_THRESHOLD - 1):
            c.record_success()
        c.record_failure("new fault")
        # Success count reset; fully recover from here.
        for _ in range(RESTORE_THRESHOLD - 1):
            c.record_success()
        assert c.is_degraded() is True  # one short of threshold
        c.record_success()
        assert c.is_degraded() is False


class TestTransitionCallback:
    def test_callback_fires_on_degrade(self) -> None:
        events: list[tuple[ClassifierHealthState, ClassifierHealthState, str]] = []
        c = ClassifierDegradedController(
            on_transition=lambda old, new, r: events.append((old, new, r))
        )
        for _ in range(DEGRADE_THRESHOLD):
            c.record_failure("TabbyAPI 502")
        assert len(events) == 1
        old, new, reason = events[0]
        assert old == ClassifierHealthState.NOMINAL
        assert new == ClassifierHealthState.DEGRADE
        assert "TabbyAPI 502" in reason

    def test_callback_fires_on_restore(self) -> None:
        events: list[tuple[ClassifierHealthState, ClassifierHealthState, str]] = []
        c = ClassifierDegradedController(
            on_transition=lambda old, new, r: events.append((old, new, r))
        )
        for _ in range(DEGRADE_THRESHOLD):
            c.record_failure("x")
        for _ in range(RESTORE_THRESHOLD):
            c.record_success()
        # Two transitions: degrade, then restore.
        assert len(events) == 2
        assert events[0][1] == ClassifierHealthState.DEGRADE
        assert events[1][1] == ClassifierHealthState.NOMINAL

    def test_callback_exception_does_not_break_state_machine(self) -> None:
        def bad_callback(old, new, r):
            raise RuntimeError("ntfy subsystem crashed")

        c = ClassifierDegradedController(on_transition=bad_callback)
        for _ in range(DEGRADE_THRESHOLD):
            c.record_failure("x")
        # Despite callback raising, state machine should have transitioned.
        assert c.is_degraded() is True

    def test_no_callback_fires_without_transition(self) -> None:
        events: list = []
        c = ClassifierDegradedController(
            on_transition=lambda old, new, r: events.append((old, new))
        )
        # One failure — no transition.
        c.record_failure("x")
        assert events == []


class TestSnapshot:
    def test_counts_both_consecutive_and_total(self) -> None:
        c = ClassifierDegradedController()
        for _ in range(5):
            c.record_failure("x")
        for _ in range(2):
            c.record_success()
        snap = c.snapshot()
        assert snap.total_failures == 5
        assert snap.total_successes == 2
        assert snap.consecutive_failures == 0  # reset by success
        assert snap.consecutive_successes == 2

    def test_snapshot_reflects_current_state(self) -> None:
        c = ClassifierDegradedController()
        for _ in range(DEGRADE_THRESHOLD):
            c.record_failure("x")
        snap = c.snapshot()
        assert snap.state == ClassifierHealthState.DEGRADE


class TestReset:
    def test_reset_clears_counters_and_state(self) -> None:
        c = ClassifierDegradedController()
        for _ in range(DEGRADE_THRESHOLD):
            c.record_failure("x")
        assert c.is_degraded() is True
        c.reset()
        snap = c.snapshot()
        assert snap.state == ClassifierHealthState.NOMINAL
        assert snap.consecutive_failures == 0
        assert snap.total_failures == 0

    def test_reset_fires_callback_if_was_degraded(self) -> None:
        events: list = []
        c = ClassifierDegradedController(on_transition=lambda o, n, r: events.append((o, n, r)))
        for _ in range(DEGRADE_THRESHOLD):
            c.record_failure("x")
        events.clear()  # drop the nominal→degrade event
        c.reset()
        assert len(events) == 1
        assert events[0][0] == ClassifierHealthState.DEGRADE
        assert events[0][1] == ClassifierHealthState.NOMINAL
        assert events[0][2] == "reset"


class TestCustomThresholds:
    def test_small_degrade_threshold(self) -> None:
        """Operator can tune — 1-fail-degrade for demos."""
        c = ClassifierDegradedController(degrade_threshold=1, restore_threshold=2)
        c.record_failure("x")
        assert c.is_degraded() is True
        c.record_success()
        assert c.is_degraded() is True  # still degraded
        c.record_success()
        assert c.is_degraded() is False


class TestThreadSafety:
    def test_concurrent_writes_preserve_total_counts(self) -> None:
        """Many threads calling record_failure/record_success — no drops."""
        c = ClassifierDegradedController(
            degrade_threshold=100_000,  # never degrade during test
            restore_threshold=100_000,
        )

        def record_failures(n: int) -> None:
            for _ in range(n):
                c.record_failure("stress")

        def record_successes(n: int) -> None:
            for _ in range(n):
                c.record_success()

        with ThreadPoolExecutor(max_workers=8) as ex:
            futures = []
            for _ in range(4):
                futures.append(ex.submit(record_failures, 250))
            for _ in range(4):
                futures.append(ex.submit(record_successes, 250))
            for f in futures:
                f.result()
        snap = c.snapshot()
        assert snap.total_failures == 1000
        assert snap.total_successes == 1000

    def test_concurrent_degrade_triggers_exactly_once(self) -> None:
        """Multiple threads crossing threshold simultaneously — single transition."""
        events: list = []
        c = ClassifierDegradedController(
            degrade_threshold=3,
            on_transition=lambda o, n, r: events.append(n),
        )
        with ThreadPoolExecutor(max_workers=8) as ex:
            for _ in range(8):
                ex.submit(c.record_failure, "stress")
        # Multiple failures may have been recorded but only one transition.
        assert events.count(ClassifierHealthState.DEGRADE) == 1


class TestModuleSingleton:
    def test_module_controller_exists(self) -> None:
        from shared.governance.classifier_degraded_controller import CONTROLLER

        assert isinstance(CONTROLLER, ClassifierDegradedController)

    @pytest.fixture(autouse=True)
    def _reset_module_controller(self) -> None:
        """Each test gets a fresh module controller."""
        from shared.governance.classifier_degraded_controller import CONTROLLER

        CONTROLLER.reset()
