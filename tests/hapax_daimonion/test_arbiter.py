"""Tests for the resource arbiter."""

from __future__ import annotations

import pytest

from agents.hapax_daimonion.arbiter import ResourceArbiter, ResourceClaim


class TestResourceArbiter:
    def _make_arbiter(self) -> ResourceArbiter:
        """Create an arbiter with two chains competing for 'audio'."""
        return ResourceArbiter(
            priorities={
                ("audio", "voice"): 10,
                ("audio", "chime"): 5,
                ("display", "voice"): 8,
            }
        )

    def test_claim_and_drain(self) -> None:
        arbiter = self._make_arbiter()
        claim = ResourceClaim(resource="audio", chain="voice", priority=10, command="speak")
        arbiter.claim(claim)

        winners = arbiter.drain_winners()
        assert len(winners) == 1
        assert winners[0].chain == "voice"

    def test_priority_ordering(self) -> None:
        arbiter = self._make_arbiter()
        low = ResourceClaim(resource="audio", chain="chime", priority=5, command="ding")
        high = ResourceClaim(resource="audio", chain="voice", priority=10, command="speak")
        arbiter.claim(low)
        arbiter.claim(high)

        winner = arbiter.resolve("audio")
        assert winner is not None
        assert winner.chain == "voice"

    def test_one_shot_removal(self) -> None:
        arbiter = self._make_arbiter()
        # hold_until=0 means one-shot
        claim = ResourceClaim(
            resource="audio", chain="voice", priority=10, command="speak", hold_until=0.0
        )
        arbiter.claim(claim)

        winners = arbiter.drain_winners()
        assert len(winners) == 1

        # One-shot should be removed after drain
        winners = arbiter.drain_winners()
        assert len(winners) == 0

    def test_same_chain_priority_rejection(self) -> None:
        arbiter = self._make_arbiter()
        claim = ResourceClaim(resource="audio", chain="voice", priority=5, command="speak")
        with pytest.raises(ValueError, match="priority"):
            arbiter.claim(claim)

    def test_unconfigured_pair_raises(self) -> None:
        arbiter = self._make_arbiter()
        claim = ResourceClaim(resource="audio", chain="unknown", priority=1, command="x")
        with pytest.raises(ValueError, match="No priority configured"):
            arbiter.claim(claim)

    def test_release(self) -> None:
        arbiter = self._make_arbiter()
        claim = ResourceClaim(resource="audio", chain="voice", priority=10, command="speak")
        arbiter.claim(claim)
        arbiter.release("audio", "voice")
        assert arbiter.resolve("audio") is None

    def test_active_claims_snapshot(self) -> None:
        arbiter = self._make_arbiter()
        claim = ResourceClaim(resource="audio", chain="voice", priority=10, command="speak")
        arbiter.claim(claim)
        snapshot = arbiter.active_claims
        assert "audio" in snapshot
        assert len(snapshot["audio"]) == 1

    def test_held_claim_survives_drain(self) -> None:
        arbiter = self._make_arbiter()
        claim = ResourceClaim(
            resource="audio", chain="voice", priority=10, command="speak", hold_until=1.0
        )
        arbiter.claim(claim)

        winners = arbiter.drain_winners(now=claim.created_at + 1.0)
        assert len(winners) == 1

        # Held claim should still be there
        winners = arbiter.drain_winners(now=claim.created_at + 2.0)
        assert len(winners) == 1
