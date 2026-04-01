"""Tests for imagination wiring into DMN daemon."""

from agents.dmn.buffer import DMNBuffer


def test_recent_observations_empty():
    buf = DMNBuffer()
    assert buf.recent_observations(5) == []


def test_recent_observations_returns_content():
    buf = DMNBuffer()
    buf.add_observation("Activity: coding. Flow: 0.8.")
    buf.add_observation("Activity: idle. Flow: 0.2.")
    result = buf.recent_observations(5)
    assert result == ["Activity: coding. Flow: 0.8.", "Activity: idle. Flow: 0.2."]


def test_recent_observations_caps_at_n():
    buf = DMNBuffer()
    for i in range(10):
        buf.add_observation(f"obs {i}")
    result = buf.recent_observations(3)
    assert len(result) == 3
    assert result == ["obs 7", "obs 8", "obs 9"]


def test_recent_observations_returns_all_when_fewer_than_n():
    buf = DMNBuffer()
    buf.add_observation("only one")
    result = buf.recent_observations(5)
    assert result == ["only one"]


# DMN daemon tests for imagination integration removed — imagination is now
# an independent daemon (agents/imagination_daemon/). See test_imagination_daemon.py
# and test_stigmergic_chain.py for the replacement tests.
