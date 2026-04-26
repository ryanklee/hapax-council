"""Regression pin: hapax-l12-evilpet-capture playback must be active (not passive).

Without ``node.passive = false`` on the playback node, the filter-chain
only flows when something downstream actively reads from
``hapax-livestream-tap``. After a wireplumber restart, no claim is
re-established until ``studio-compositor``'s ``pw-cat --record``
activates — leaving the entire broadcast chain silent in the meantime.

That orphan state was the 2026-04-26 silent-livestream-tap incident
(post-double-wireplumber-restart at 11:04 + 11:09 CDT). Operator
recovered via ``systemctl --user restart studio-compositor``; the
permanent fix is the explicit-active flag pinned by this test.

Constitutional binders:
- ``feedback_l12_equals_livestream_invariant`` — L-12 input MUST reach
  broadcast; if the chain stalls, it doesn't
- ``feedback_never_drop_speech`` — silent broadcast during the orphan
  window drops in-flight speech
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
L12_EVILPET_CONFIG = REPO_ROOT / "config" / "pipewire" / "hapax-l12-evilpet-capture.conf"


class TestLivestreamTapPassiveNodePin:
    def test_config_file_exists(self) -> None:
        assert L12_EVILPET_CONFIG.exists(), (
            f"Expected pipewire config at {L12_EVILPET_CONFIG} — has it moved?"
        )

    def test_playback_node_passive_false(self) -> None:
        """``hapax-l12-evilpet-playback`` must declare ``node.passive = false``.

        Implicit default is ``true`` (passive); without the explicit
        false, the filter-chain only flows when downstream consumers
        actively claim the playback output. Wireplumber restarts can
        orphan that claim, leaving the broadcast chain silent.
        """
        content = L12_EVILPET_CONFIG.read_text(encoding="utf-8")
        playback_anchor = content.find('node.name = "hapax-l12-evilpet-playback"')
        assert playback_anchor != -1, (
            "hapax-l12-evilpet-playback node not defined — config restructured?"
        )
        # Limit search scope to the playback.props block only. The block
        # ends at the closing brace of `playback.props = { ... }`. The
        # config uses 4-space indentation so the closing `}` line is
        # the first one starting with 12 spaces (3 levels of indent).
        playback_block = content[playback_anchor:]
        block_end = playback_block.find("\n            }")
        assert block_end != -1, "playback.props block end not found"
        playback_block = playback_block[:block_end]
        assert "node.passive = false" in playback_block, (
            "hapax-l12-evilpet-playback must declare node.passive = false. "
            "Without this, the filter-chain only flows when something "
            "downstream is actively reading from hapax-livestream-tap. "
            "After a wireplumber restart, no claim is re-established "
            "until studio-compositor's pw-cat --record activates — "
            "leaving the broadcast chain silent. See the 2026-04-26 "
            "silent-livestream-tap incident shape-up."
        )

    def test_playback_targets_livestream_tap(self) -> None:
        """``hapax-l12-evilpet-playback`` targets ``hapax-livestream-tap``."""
        content = L12_EVILPET_CONFIG.read_text(encoding="utf-8")
        playback_anchor = content.find('node.name = "hapax-l12-evilpet-playback"')
        assert playback_anchor != -1
        playback_block = content[playback_anchor:]
        block_end = playback_block.find("\n            }")
        playback_block = playback_block[:block_end]
        assert 'target.object = "hapax-livestream-tap"' in playback_block, (
            "hapax-l12-evilpet-playback target.object changed — does the "
            "broadcast topology still terminate at hapax-livestream-tap?"
        )
