"""Tests for IR brightness delta as body-heat proxy."""

from __future__ import annotations

from collections import deque


def test_stable_brightness_no_signal():
    from agents.hapax_daimonion.backends.ir_presence import _compute_brightness_delta

    history = deque([100.0] * 30, maxlen=30)
    assert _compute_brightness_delta(history, 100.0) == 0.0


def test_brightness_drop_signals_departure():
    from agents.hapax_daimonion.backends.ir_presence import _compute_brightness_delta

    history = deque([120.0] * 30, maxlen=30)
    delta = _compute_brightness_delta(history, 100.0)
    assert delta < -15


def test_brightness_rise_signals_arrival():
    from agents.hapax_daimonion.backends.ir_presence import _compute_brightness_delta

    history = deque([90.0] * 30, maxlen=30)
    delta = _compute_brightness_delta(history, 115.0)
    assert delta > 15


def test_insufficient_history_returns_zero():
    from agents.hapax_daimonion.backends.ir_presence import _compute_brightness_delta

    history = deque([100.0] * 5, maxlen=30)
    assert _compute_brightness_delta(history, 200.0) == 0.0
