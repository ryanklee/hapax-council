"""Test ControlSignal model and health publishing."""

import json

import pytest


def test_control_signal_creation():
    from shared.control_signal import ControlSignal

    sig = ControlSignal(component="ir_perception", reference=1.0, perception=0.7)
    assert sig.error == pytest.approx(0.3)
    assert sig.component == "ir_perception"


def test_control_signal_zero_error():
    from shared.control_signal import ControlSignal

    sig = ControlSignal(component="stimmung", reference=0.0, perception=0.0)
    assert sig.error == 0.0


def test_publish_health(tmp_path):
    from shared.control_signal import ControlSignal, publish_health

    sig = ControlSignal(component="test", reference=1.0, perception=0.5)
    path = tmp_path / "health.json"
    publish_health(sig, path=path)
    data = json.loads(path.read_text())
    assert data["component"] == "test"
    assert data["error"] == pytest.approx(0.5)
    assert "timestamp" in data
