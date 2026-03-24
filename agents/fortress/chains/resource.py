"""Resource Manager governance chain.

Decides production priorities: food, drink, equipment.
Suppression wiring (resource_pressure field) added in Batch 4.
"""

from __future__ import annotations

from agents.fortress.schema import FullFortressState
from agents.hapax_voice.governance import (
    Candidate,
    FallbackChain,
    Selected,
    Veto,
    VetoChain,
    VetoResult,
)


def _workshop_available(state: FullFortressState) -> bool:
    """Allow orders only if at least one workshop exists."""
    return len(state.workshops) > 0


def _needs_food(state: FullFortressState) -> bool:
    return state.stockpiles.food < state.population * 10


def _needs_drink(state: FullFortressState) -> bool:
    return state.stockpiles.drink < state.population * 5


def _needs_equipment(state: FullFortressState) -> bool:
    return state.stockpiles.weapons < state.population // 5


class ResourceManagerChain:
    """Governance chain for resource production decisions."""

    CHAIN_NAME = "resource_manager"

    def __init__(self) -> None:
        self._veto_chain: VetoChain[FullFortressState] = VetoChain(
            [
                Veto(
                    "workshop_available",
                    _workshop_available,
                    description="At least one workshop required",
                ),
            ]
        )
        self._fallback: FallbackChain[FullFortressState, str] = FallbackChain(
            candidates=[
                Candidate("food_production", _needs_food, "food_production"),
                Candidate("drink_production", _needs_drink, "drink_production"),
                Candidate("equipment_production", _needs_equipment, "equipment_production"),
            ],
            default="no_action",
        )

    def evaluate(self, state: FullFortressState) -> tuple[VetoResult, Selected[str]]:
        """Evaluate vetoes and select production priority."""
        veto_result = self._veto_chain.evaluate(state)
        if not veto_result.allowed:
            return veto_result, Selected(action="no_action", selected_by="vetoed")
        selection = self._fallback.select(state)
        return veto_result, selection
