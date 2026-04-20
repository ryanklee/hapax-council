"""Tests for shared.governance.scrim_invariants.scrim_translucency_tracker.

Covers:
  - initial state is NOMINAL with no recorded scores
  - K consecutive failing frames trips DEGRADED exactly once
  - N consecutive passing frames after DEGRADED recover to NOMINAL
  - mid-failure single passing frame does NOT recover (hysteresis)
  - publish_scrim_signal writes atomically (tmp + rename pattern)
  - failed write is logged but does not propagate
  - HAPAX_SCRIM_INVARIANT_B2_ENFORCE gate flips enforcement_active without
    altering the rest of the published payload
  - concurrent record() from multiple threads is safe (no exceptions, no
    state corruption — final counts match the input).

All tests use ``tmp_path`` for any disk I/O so production /dev/shm is
never touched.
"""

from __future__ import annotations

import json
import os
import threading
from pathlib import Path
from unittest import mock

import numpy as np
import pytest  # noqa: TC002

from shared.governance.scrim_invariants.scrim_translucency import (
    SCHEMA_VERSION,
    TranslucencyThresholds,
)
from shared.governance.scrim_invariants.scrim_translucency_tracker import (
    DEFAULT_FAILURE_K,
    DEFAULT_RECOVERY_N,
    ENFORCE_ENV_VAR,
    STATE_DEGRADED,
    STATE_NOMINAL,
    ScrimTranslucencyTracker,
    build_scrim_signal,
    enforcement_active,
    publish_scrim_signal,
)

# ---------------------------------------------------------------------------
# Frame helpers
# ---------------------------------------------------------------------------


def _failing_frame() -> np.ndarray:
    """Pure-white frame: fails luminance_variance + entropy_floor."""
    return np.full((180, 320, 3), 255, dtype=np.uint8)


def _passing_frame(seed: int = 0) -> np.ndarray:
    """Random RGB noise: structurally rich enough to pass all sub-metrics."""
    rng = np.random.default_rng(seed)
    return rng.integers(0, 256, size=(180, 320, 3), dtype=np.uint8)


def _thresholds() -> TranslucencyThresholds:
    """Lenient thresholds tuned so synthetic noise passes and pure white fails."""
    return TranslucencyThresholds(
        edge_density_min=0.10,
        luminance_variance_min=0.10,
        entropy_floor_min=0.30,
    )


# ---------------------------------------------------------------------------
# Sanity: fixture frames behave as we assert below
# ---------------------------------------------------------------------------


def test_failing_frame_actually_fails_oracle() -> None:
    from shared.governance.scrim_invariants.scrim_translucency import evaluate

    score = evaluate(_failing_frame(), _thresholds())
    assert score.passed is False


def test_passing_frame_actually_passes_oracle() -> None:
    from shared.governance.scrim_invariants.scrim_translucency import evaluate

    score = evaluate(_passing_frame(seed=1), _thresholds())
    assert score.passed is True


# ---------------------------------------------------------------------------
# Tracker state machine
# ---------------------------------------------------------------------------


def test_tracker_initial_state_no_signal() -> None:
    tracker = ScrimTranslucencyTracker()
    assert tracker.state() == STATE_NOMINAL
    assert tracker.over_threshold() is False
    assert tracker.consecutive_failures() == 0
    assert tracker.consecutive_passes() == 0
    assert tracker.transition_count() == 0

    snap = tracker.snapshot()
    assert snap.state == STATE_NOMINAL
    assert snap.over_threshold is False
    assert snap.current is None
    assert snap.samples_in_window == 0
    assert snap.schema_version == SCHEMA_VERSION


def test_k_failing_frames_triggers_degraded_exactly_once() -> None:
    tracker = ScrimTranslucencyTracker(failure_k=5, recovery_n=3)
    th = _thresholds()
    bad = _failing_frame()

    # Below K: still NOMINAL.
    for _ in range(4):
        tracker.record(bad, th)
        assert tracker.state() == STATE_NOMINAL
    assert tracker.transition_count() == 0

    # Kth failure trips DEGRADED.
    tracker.record(bad, th)
    assert tracker.state() == STATE_DEGRADED
    assert tracker.over_threshold() is True
    assert tracker.transition_count() == 1

    # Subsequent failing frames do not double-count the transition.
    for _ in range(10):
        tracker.record(bad, th)
    assert tracker.transition_count() == 1


def test_recovery_after_n_passing_frames() -> None:
    tracker = ScrimTranslucencyTracker(failure_k=3, recovery_n=4)
    th = _thresholds()

    # Trip degraded.
    for _ in range(3):
        tracker.record(_failing_frame(), th)
    assert tracker.state() == STATE_DEGRADED

    # Below N passes: still DEGRADED.
    for i in range(3):
        tracker.record(_passing_frame(seed=i), th)
        assert tracker.state() == STATE_DEGRADED

    # Nth passing frame recovers.
    tracker.record(_passing_frame(seed=99), th)
    assert tracker.state() == STATE_NOMINAL
    assert tracker.over_threshold() is False
    # Transition count tracks NOMINAL->DEGRADED entries; recovery does NOT bump it.
    assert tracker.transition_count() == 1


def test_hysteresis_blocks_mid_failure_single_pass_recovery() -> None:
    """A single passing frame mid-failure-streak must NOT recover state."""
    tracker = ScrimTranslucencyTracker(failure_k=4, recovery_n=3)
    th = _thresholds()

    # Trip degraded.
    for _ in range(4):
        tracker.record(_failing_frame(), th)
    assert tracker.state() == STATE_DEGRADED

    # Two passes (N-1) — not enough to recover.
    tracker.record(_passing_frame(seed=1), th)
    tracker.record(_passing_frame(seed=2), th)
    assert tracker.state() == STATE_DEGRADED

    # One failure resets the consecutive-pass counter.
    tracker.record(_failing_frame(), th)
    assert tracker.state() == STATE_DEGRADED
    assert tracker.consecutive_passes() == 0

    # Two more passes alone are insufficient — counter restarted.
    tracker.record(_passing_frame(seed=3), th)
    tracker.record(_passing_frame(seed=4), th)
    assert tracker.state() == STATE_DEGRADED
    assert tracker.consecutive_passes() == 2

    # Third pass clears the recovery threshold.
    tracker.record(_passing_frame(seed=5), th)
    assert tracker.state() == STATE_NOMINAL


def test_repeated_trip_recover_cycles_increment_transition_count() -> None:
    tracker = ScrimTranslucencyTracker(failure_k=2, recovery_n=2)
    th = _thresholds()

    for cycle in range(3):
        for _ in range(2):
            tracker.record(_failing_frame(), th)
        assert tracker.state() == STATE_DEGRADED
        for i in range(2):
            tracker.record(_passing_frame(seed=cycle * 10 + i), th)
        assert tracker.state() == STATE_NOMINAL

    assert tracker.transition_count() == 3


def test_default_constants_match_spec() -> None:
    """Spec §6.1: K=30 (~1s @ 30fps); recovery N=10 (presence-engine pattern)."""
    assert DEFAULT_FAILURE_K == 30
    assert DEFAULT_RECOVERY_N == 10


def test_constructor_validates_parameters() -> None:
    with pytest.raises(ValueError):
        ScrimTranslucencyTracker(window_size=0)
    with pytest.raises(ValueError):
        ScrimTranslucencyTracker(failure_k=0)
    with pytest.raises(ValueError):
        ScrimTranslucencyTracker(recovery_n=0)


# ---------------------------------------------------------------------------
# Publisher
# ---------------------------------------------------------------------------


def test_publish_writes_atomic_and_payload_well_formed(tmp_path: Path) -> None:
    tracker = ScrimTranslucencyTracker()
    th = _thresholds()
    tracker.record(_passing_frame(seed=7), th)

    target = tmp_path / "scrim_translucency.json"
    written = publish_scrim_signal(tracker, path=target)
    assert written == target
    assert target.exists()

    payload = json.loads(target.read_text(encoding="utf-8"))
    assert payload["schema_version"] == SCHEMA_VERSION
    assert payload["state"] == STATE_NOMINAL
    assert payload["over_threshold"] is False
    assert payload["enforcement_active"] in (True, False)
    assert payload["current"]["passed"] is True
    assert "edge_density_ratio" in payload["current"]
    assert "failing_component" in payload["current"]


def test_publish_creates_parent_directory(tmp_path: Path) -> None:
    tracker = ScrimTranslucencyTracker()
    target = tmp_path / "nested" / "subdir" / "scrim.json"
    publish_scrim_signal(tracker, path=target)
    assert target.exists()


def test_publish_uses_atomic_write_helper(tmp_path: Path) -> None:
    """Verify the publisher delegates to ``atomic_write_json`` (tmp+rename)."""
    tracker = ScrimTranslucencyTracker()
    target = tmp_path / "scrim.json"

    with mock.patch(
        "shared.governance.scrim_invariants.scrim_translucency_tracker.atomic_write_json"
    ) as m_atomic:
        publish_scrim_signal(tracker, path=target)
        m_atomic.assert_called_once()
        call_args = m_atomic.call_args
        # Positional: (payload, path)
        assert call_args[0][1] == target
        assert isinstance(call_args[0][0], dict)


def test_publish_no_partial_writes_visible(tmp_path: Path) -> None:
    """Atomic-write contract: a successful publish leaves no .tmp siblings."""
    tracker = ScrimTranslucencyTracker()
    tracker.record(_passing_frame(seed=8), _thresholds())
    target = tmp_path / "scrim.json"
    publish_scrim_signal(tracker, path=target)

    siblings = list(target.parent.iterdir())
    # Only the final file remains; no orphaned tmp dotfiles.
    assert siblings == [target]


def test_publish_failure_logged_does_not_propagate(tmp_path: Path) -> None:
    """A failed write must NOT raise — egress must keep flowing."""
    tracker = ScrimTranslucencyTracker()
    target = tmp_path / "scrim.json"

    with mock.patch(
        "shared.governance.scrim_invariants.scrim_translucency_tracker.atomic_write_json",
        side_effect=OSError("disk full"),
    ):
        # Should not raise.
        result = publish_scrim_signal(tracker, path=target)
    assert result is None
    assert not target.exists()


def test_publish_reflects_degraded_state(tmp_path: Path) -> None:
    tracker = ScrimTranslucencyTracker(failure_k=2, recovery_n=2)
    th = _thresholds()
    tracker.record(_failing_frame(), th)
    tracker.record(_failing_frame(), th)
    assert tracker.state() == STATE_DEGRADED

    target = tmp_path / "scrim.json"
    publish_scrim_signal(tracker, path=target)
    payload = json.loads(target.read_text(encoding="utf-8"))
    assert payload["state"] == STATE_DEGRADED
    assert payload["over_threshold"] is True
    assert payload["consecutive_failures"] >= 2
    assert payload["transition_count"] == 1
    assert payload["current"]["passed"] is False
    assert payload["current"]["failing_component"] is not None


# ---------------------------------------------------------------------------
# Build-signal pure function
# ---------------------------------------------------------------------------


def test_build_scrim_signal_serializable_without_recording() -> None:
    tracker = ScrimTranslucencyTracker()
    payload = build_scrim_signal(tracker)
    # Must round-trip through JSON cleanly.
    text = json.dumps(payload)
    parsed = json.loads(text)
    assert parsed["state"] == STATE_NOMINAL
    assert parsed["current"] is None
    assert parsed["samples_in_window"] == 0


# ---------------------------------------------------------------------------
# Enforcement gate
# ---------------------------------------------------------------------------


def test_enforcement_gate_default_observe_only(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(ENFORCE_ENV_VAR, raising=False)
    assert enforcement_active() is False

    tracker = ScrimTranslucencyTracker()
    snap = tracker.snapshot()
    assert snap.enforcement_active is False
    payload = build_scrim_signal(tracker)
    assert payload["enforcement_active"] is False


def test_enforcement_gate_enabled_via_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(ENFORCE_ENV_VAR, "1")
    assert enforcement_active() is True

    tracker = ScrimTranslucencyTracker()
    snap = tracker.snapshot()
    assert snap.enforcement_active is True
    payload = build_scrim_signal(tracker)
    assert payload["enforcement_active"] is True


def test_enforcement_gate_other_values_treated_as_observe_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for value in ("0", "", "true", "yes", "TRUE"):
        monkeypatch.setenv(ENFORCE_ENV_VAR, value)
        assert enforcement_active() is False, f"value={value!r} should be observe-only"


def test_enforcement_gate_does_not_change_other_payload_keys(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Flipping the gate must only flip enforcement_active, nothing else."""
    tracker = ScrimTranslucencyTracker(failure_k=2, recovery_n=2)
    th = _thresholds()
    tracker.record(_failing_frame(), th)
    tracker.record(_failing_frame(), th)

    monkeypatch.setenv(ENFORCE_ENV_VAR, "0")
    p_off = build_scrim_signal(tracker)
    monkeypatch.setenv(ENFORCE_ENV_VAR, "1")
    p_on = build_scrim_signal(tracker)

    # State, hysteresis-derived values, transition_count must match.
    assert p_off["state"] == p_on["state"]
    assert p_off["over_threshold"] == p_on["over_threshold"]
    assert p_off["consecutive_failures"] == p_on["consecutive_failures"]
    assert p_off["transition_count"] == p_on["transition_count"]
    # Only enforcement_active differs.
    assert p_off["enforcement_active"] is False
    assert p_on["enforcement_active"] is True


# ---------------------------------------------------------------------------
# Concurrency
# ---------------------------------------------------------------------------


def test_concurrent_record_is_thread_safe() -> None:
    """Multiple threads recording concurrently must not corrupt counts.

    We pre-build N frames per thread, fire them all from worker threads,
    then assert no exceptions were raised and the final samples_in_window
    matches the total work scheduled (or the deque cap, whichever is
    smaller).
    """
    n_threads = 4
    per_thread = 50
    tracker = ScrimTranslucencyTracker(window_size=1024)
    th = _thresholds()
    pre_frames = [_passing_frame(seed=i) for i in range(per_thread)]
    errors: list[BaseException] = []

    def worker() -> None:
        try:
            for f in pre_frames:
                tracker.record(f, th)
        except BaseException as exc:  # noqa: BLE001
            errors.append(exc)

    threads = [threading.Thread(target=worker) for _ in range(n_threads)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors, f"worker threads raised: {errors!r}"
    snap = tracker.snapshot()
    expected = n_threads * per_thread
    assert snap.samples_in_window == min(expected, 1024)
    # All passing frames → never tripped.
    assert snap.state == STATE_NOMINAL
    assert snap.transition_count == 0


def test_concurrent_record_preserves_transition_invariant() -> None:
    """Concurrent failing-frame load must trip exactly once (hysteresis sane)."""
    tracker = ScrimTranslucencyTracker(failure_k=4, recovery_n=8, window_size=1024)
    th = _thresholds()
    bad = _failing_frame()
    n_threads = 4
    per_thread = 25
    errors: list[BaseException] = []

    def worker() -> None:
        try:
            for _ in range(per_thread):
                tracker.record(bad, th)
        except BaseException as exc:  # noqa: BLE001
            errors.append(exc)

    threads = [threading.Thread(target=worker) for _ in range(n_threads)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors
    assert tracker.state() == STATE_DEGRADED
    # Whether we count strictly via consecutive_failures or wall-time
    # ordering, the count of NOMINAL->DEGRADED transitions must be 1
    # because no passing frames were interleaved.
    assert tracker.transition_count() == 1


# ---------------------------------------------------------------------------
# Default signal path is under /dev/shm/hapax-compositor
# ---------------------------------------------------------------------------


def test_default_signal_path_under_shm() -> None:
    from shared.governance.scrim_invariants.scrim_translucency_tracker import (
        DEFAULT_SIGNAL_PATH,
    )

    # Per spec §6.2: /dev/shm/hapax-compositor/scrim_translucency.json
    assert str(DEFAULT_SIGNAL_PATH).startswith("/dev/shm/hapax-compositor/")
    assert DEFAULT_SIGNAL_PATH.name == "scrim_translucency.json"


# ---------------------------------------------------------------------------
# Defensive: env-var read at call time, not import time
# ---------------------------------------------------------------------------


def test_enforcement_gate_re_evaluated_per_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(ENFORCE_ENV_VAR, raising=False)
    assert enforcement_active() is False
    os.environ[ENFORCE_ENV_VAR] = "1"
    try:
        assert enforcement_active() is True
    finally:
        del os.environ[ENFORCE_ENV_VAR]
    assert enforcement_active() is False
