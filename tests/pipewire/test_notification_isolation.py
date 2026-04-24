"""Notification-private sink isolation (Phase A3).

Pins the governance contract that system / chat / desktop notifications
never reach the livestream broadcast. Surface-level verification: the
conf file exists, declares a dedicated sink, and targets an off-L-12
monitor (Yeti headphone-amp loopback, not the L-12 MASTER and not any
capture target, explicitly not ``hapax-l12-evilpet-capture``).

Routing refinement (2026-04-23): per the L-12-equals-livestream
invariant (memory: feedback_l12_equals_livestream_invariant), any
audio on L-12 — including the master monitor — reaches broadcast.
Notifications are operator-private by governance, so they now route
entirely off L-12 to the Yeti headphone monitor loopback.

Runtime verification (live graph check) is handled by the Phase B /
Phase C integration tests; this file is the static schema pin.
"""

from __future__ import annotations

from pathlib import Path

import pytest

CONF_REPO_PATH = (
    Path(__file__).resolve().parents[2] / "config" / "pipewire" / "hapax-notification-private.conf"
)


@pytest.fixture()
def conf_text() -> str:
    if not CONF_REPO_PATH.exists():
        pytest.skip(f"conf missing from repo: {CONF_REPO_PATH}")
    return CONF_REPO_PATH.read_text(encoding="utf-8")


def test_conf_exists(conf_text: str) -> None:
    assert len(conf_text) > 0


def test_declares_dedicated_sink_name(conf_text: str) -> None:
    assert 'node.name       = "hapax-notification-private"' in conf_text, (
        "notification-private sink must declare the exact node.name"
    )


def test_uses_loopback_module(conf_text: str) -> None:
    assert "libpipewire-module-loopback" in conf_text


def test_targets_off_l12_monitor_not_capture(conf_text: str) -> None:
    """2026-04-23 routing refinement: notifications leave L-12 entirely.

    Prior rubric: target L-12 MASTER (not capture). Invariant tightened
    per the L-12-equals-livestream memory — any audio on L-12, even the
    master monitor, could reach broadcast via the capture or tap path,
    so the private sink now targets the Yeti headphone-amp loopback
    instead.
    """
    # Strip comment lines so we only check active configuration.
    active_lines = [line for line in conf_text.splitlines() if not line.lstrip().startswith("#")]
    active = "\n".join(active_lines)

    assert "hapax-l12-evilpet-capture" not in active, (
        "Notification sink must NEVER target the L-12 filter-chain capture; "
        "notifications forbidden on broadcast."
    )
    assert "hapax-livestream-tap" not in active, (
        "Notification sink must not route into the livestream tap directly."
    )
    assert "ZOOM_Corporation_L-12" not in active, (
        "Notification sink must NOT target the L-12 MASTER analog output — "
        "L-12-equals-livestream invariant means any L-12 audio reaches "
        "broadcast. Route to an off-L-12 private monitor instead."
    )
    # Positive assertion: target must be an off-L-12 operator-private
    # loopback. Yeti headphone monitor is the 2026-04 choice.
    assert "Blue_Microphones_Yeti" in active or "blue-yeti" in active.lower(), (
        "Notification sink target must be an off-L-12 operator-private "
        "monitor (Yeti headphone-amp loopback)."
    )


def test_declares_stereo(conf_text: str) -> None:
    assert "audio.channels  = 2" in conf_text or "audio.channels = 2" in conf_text
    assert "[ FL FR ]" in conf_text


def test_documents_governance_rationale(conf_text: str) -> None:
    assert "governance" in conf_text.lower() or "forbidden" in conf_text.lower(), (
        "Conf file must document WHY notifications are gated off broadcast."
    )
