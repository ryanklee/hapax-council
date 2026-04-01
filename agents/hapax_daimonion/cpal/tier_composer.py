"""Tier composer -- sequences tiered signals into conversational responses.

When the evaluator selects an action tier, the composer produces the
full sequence: T0 (visual) -> T1 (backchannel/ack) -> T2 (floor claim)
-> T3 (substantive). Each tier fills the time the next needs to prepare.

This is the "no dead air" principle from the spec: the 3-5s LLM latency
is inhabited by lower-tier signals.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from agents.hapax_daimonion.cpal.types import ConversationalRegion, CorrectionTier

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class ComposedAction:
    """A sequence of tiered actions to execute."""

    tiers: tuple[CorrectionTier, ...]
    signal_types: tuple[str, ...]  # parallel to tiers
    trigger: str  # what caused this composition


class TierComposer:
    """Composes tiered signal sequences from evaluator decisions.

    Given an action tier and conversational region, produces the
    full sequence of signals that should fire. Lower tiers fire
    first to fill latency.
    """

    def compose(
        self,
        *,
        action_tier: CorrectionTier,
        region: ConversationalRegion,
        trigger: str = "control_law",
    ) -> ComposedAction:
        """Compose a signal sequence for the given action tier.

        The sequence always starts at T0 and builds up to the
        requested tier, skipping tiers not available in the
        current region.
        """
        tiers: list[CorrectionTier] = []
        signals: list[str] = []

        # T0 always fires (visual acknowledgment)
        tiers.append(CorrectionTier.T0_VISUAL)
        signals.append("attentional_shift")

        if action_tier == CorrectionTier.T0_VISUAL:
            return ComposedAction(
                tiers=tuple(tiers),
                signal_types=tuple(signals),
                trigger=trigger,
            )

        # T1 fires if region permits and tier requests it
        if action_tier.value >= CorrectionTier.T1_PRESYNTHESIZED.value:
            if region in (
                ConversationalRegion.ATTENTIVE,
                ConversationalRegion.CONVERSATIONAL,
                ConversationalRegion.INTENSIVE,
            ):
                tiers.append(CorrectionTier.T1_PRESYNTHESIZED)
                signals.append("acknowledgment")

        if action_tier == CorrectionTier.T1_PRESYNTHESIZED:
            return ComposedAction(
                tiers=tuple(tiers),
                signal_types=tuple(signals),
                trigger=trigger,
            )

        # T2 fires for floor claim before T3
        if action_tier.value >= CorrectionTier.T2_LIGHTWEIGHT.value:
            if region in (
                ConversationalRegion.ATTENTIVE,
                ConversationalRegion.CONVERSATIONAL,
                ConversationalRegion.INTENSIVE,
            ):
                tiers.append(CorrectionTier.T2_LIGHTWEIGHT)
                signals.append("discourse_marker")

        if action_tier == CorrectionTier.T2_LIGHTWEIGHT:
            return ComposedAction(
                tiers=tuple(tiers),
                signal_types=tuple(signals),
                trigger=trigger,
            )

        # T3 substantive response
        if action_tier == CorrectionTier.T3_FULL_FORMULATION:
            if region in (
                ConversationalRegion.CONVERSATIONAL,
                ConversationalRegion.INTENSIVE,
            ):
                tiers.append(CorrectionTier.T3_FULL_FORMULATION)
                signals.append("substantive_response")

        return ComposedAction(
            tiers=tuple(tiers),
            signal_types=tuple(signals),
            trigger=trigger,
        )
