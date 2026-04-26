"""Regression: livestream audio path survives wireplumber restart.

Pitch: docs/research/2026-04-26-livestream-tap-silence-shape-up.md

The 2026-04-26 incident: double wireplumber restart left
``hapax-l12-evilpet-capture`` playback orphaned (passive node, no
downstream claim), stalling the entire broadcast chain. Operator had to
restart studio-compositor to recover.

The fix in ``config/pipewire/hapax-l12-evilpet-capture.conf`` sets
``node.passive = false`` on the playback node so the chain actively
pulls from L-12 USB regardless of downstream demand.

The static config-shape pin is the load-bearing assertion. The runtime
restart-and-reverify check is gated on a live PipeWire daemon and the
``HAPAX_LIVESTREAM_RESILIENCE_LIVE=1`` env var so CI does not bounce
audio on the broadcast machine.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import time
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
CONF = REPO_ROOT / "config" / "pipewire" / "hapax-l12-evilpet-capture.conf"


def test_evilpet_playback_node_is_active() -> None:
    """The fix line must remain in the canonical config.

    A future refactor that drops the line resurrects the wireplumber-
    restart silence. Pin the contract at the config layer.
    """
    text = CONF.read_text()
    assert 'node.name = "hapax-l12-evilpet-playback"' in text, (
        "playback node missing — config refactored?"
    )
    playback_block_start = text.index('node.name = "hapax-l12-evilpet-playback"')
    playback_block = text[playback_block_start : playback_block_start + 2000]
    assert "node.passive = false" in playback_block, (
        "node.passive = false missing on hapax-l12-evilpet-playback — "
        "wireplumber-restart silence regression risk. See "
        "docs/research/2026-04-26-livestream-tap-silence-shape-up.md."
    )


@pytest.mark.skipif(
    os.environ.get("HAPAX_LIVESTREAM_RESILIENCE_LIVE") != "1",
    reason="live wireplumber-restart drill; opt-in via env var on broadcast host",
)
def test_livestream_chain_survives_double_wireplumber_restart() -> None:
    if shutil.which("pw-link") is None or shutil.which("systemctl") is None:
        pytest.skip("pw-link or systemctl unavailable")

    def chain_intact() -> bool:
        result = subprocess.run(["pw-link", "-l"], capture_output=True, text=True, timeout=5)
        out = result.stdout
        return (
            "hapax-l12-evilpet-playback" in out
            and "hapax-livestream-tap" in out
            and "hapax-broadcast-master-capture" in out
        )

    assert chain_intact(), "baseline chain not present"

    for _ in range(2):
        subprocess.run(
            ["systemctl", "--user", "restart", "wireplumber.service"],
            check=True,
            timeout=10,
        )
        time.sleep(3)

    time.sleep(2)
    assert chain_intact(), (
        "broadcast chain missing nodes after wireplumber restart — passive-node fix has regressed"
    )
