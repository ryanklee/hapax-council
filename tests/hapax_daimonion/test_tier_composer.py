"""Tests for CPAL tier composer."""

from agents.hapax_daimonion.cpal.tier_composer import ComposedAction, TierComposer
from agents.hapax_daimonion.cpal.types import ConversationalRegion, CorrectionTier


class TestTierComposer:
    def test_t0_only(self):
        composer = TierComposer()
        action = composer.compose(
            action_tier=CorrectionTier.T0_VISUAL,
            region=ConversationalRegion.AMBIENT,
        )
        assert action.tiers == (CorrectionTier.T0_VISUAL,)
        assert action.signal_types == ("attentional_shift",)

    def test_t1_includes_t0(self):
        composer = TierComposer()
        action = composer.compose(
            action_tier=CorrectionTier.T1_PRESYNTHESIZED,
            region=ConversationalRegion.CONVERSATIONAL,
        )
        assert CorrectionTier.T0_VISUAL in action.tiers
        assert CorrectionTier.T1_PRESYNTHESIZED in action.tiers
        assert len(action.tiers) == 2

    def test_t3_includes_full_sequence(self):
        composer = TierComposer()
        action = composer.compose(
            action_tier=CorrectionTier.T3_FULL_FORMULATION,
            region=ConversationalRegion.CONVERSATIONAL,
        )
        assert action.tiers[0] == CorrectionTier.T0_VISUAL
        assert CorrectionTier.T1_PRESYNTHESIZED in action.tiers
        assert CorrectionTier.T3_FULL_FORMULATION in action.tiers

    def test_ambient_caps_at_t0(self):
        """Even if T3 requested, ambient only produces T0."""
        composer = TierComposer()
        action = composer.compose(
            action_tier=CorrectionTier.T3_FULL_FORMULATION,
            region=ConversationalRegion.AMBIENT,
        )
        assert action.tiers == (CorrectionTier.T0_VISUAL,)

    def test_peripheral_caps_at_t1(self):
        composer = TierComposer()
        action = composer.compose(
            action_tier=CorrectionTier.T3_FULL_FORMULATION,
            region=ConversationalRegion.PERIPHERAL,
        )
        # Peripheral doesn't have T1 in region check
        assert CorrectionTier.T3_FULL_FORMULATION not in action.tiers

    def test_intensive_full_sequence(self):
        composer = TierComposer()
        action = composer.compose(
            action_tier=CorrectionTier.T3_FULL_FORMULATION,
            region=ConversationalRegion.INTENSIVE,
        )
        assert len(action.tiers) == 4  # T0, T1, T2, T3
        assert action.tiers[-1] == CorrectionTier.T3_FULL_FORMULATION

    def test_trigger_preserved(self):
        composer = TierComposer()
        action = composer.compose(
            action_tier=CorrectionTier.T0_VISUAL,
            region=ConversationalRegion.AMBIENT,
            trigger="impingement",
        )
        assert action.trigger == "impingement"

    def test_signal_types_parallel_to_tiers(self):
        composer = TierComposer()
        action = composer.compose(
            action_tier=CorrectionTier.T3_FULL_FORMULATION,
            region=ConversationalRegion.INTENSIVE,
        )
        assert len(action.tiers) == len(action.signal_types)

    def test_composed_action_is_frozen(self):
        action = ComposedAction(
            tiers=(CorrectionTier.T0_VISUAL,),
            signal_types=("visual",),
            trigger="test",
        )
        try:
            action.trigger = "changed"
            raise AssertionError("Should be frozen")
        except (AttributeError, TypeError):
            pass
