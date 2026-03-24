"""Resource Manager governance chain.

Decides production priorities: food, drink, equipment.
Works with both FastFortressState (food_count/drink_count) and
FullFortressState (stockpiles + workshops).
"""

from __future__ import annotations

from agents.fortress.schema import FastFortressState, FullFortressState
from agents.hapax_voice.governance import (
    Candidate,
    FallbackChain,
    Selected,
    Veto,
    VetoChain,
    VetoResult,
)


def _workshop_available(state: FastFortressState) -> bool:
    """Allow orders only if workshops exist (skip check for fast state)."""
    if isinstance(state, FullFortressState):
        return len(state.workshops) > 0
    return True  # Assume workshops exist when we can't check


def _needs_food(state: FastFortressState) -> bool:
    return state.food_count < state.population * 10


def _needs_drink(state: FastFortressState) -> bool:
    return state.drink_count < state.population * 5


def _needs_equipment(state: FastFortressState) -> bool:
    if isinstance(state, FullFortressState):
        return state.stockpiles.weapons < state.population // 5
    return False  # Can't check without full state


class ResourceManagerChain:
    """Governance chain for resource production decisions."""

    CHAIN_NAME = "resource_manager"

    def __init__(self) -> None:
        self._veto_chain: VetoChain[FastFortressState] = VetoChain(
            [
                Veto(
                    "workshop_available",
                    _workshop_available,
                    description="At least one workshop required",
                ),
            ]
        )
        self._fallback: FallbackChain[FastFortressState, str] = FallbackChain(
            candidates=[
                Candidate("food_production", _needs_food, "food_production"),
                Candidate("drink_production", _needs_drink, "drink_production"),
                Candidate("equipment_production", _needs_equipment, "equipment_production"),
            ],
            default="no_action",
        )

    def evaluate(self, state: FastFortressState) -> tuple[VetoResult, Selected[str]]:
        """Evaluate vetoes and select production priority."""
        veto_result = self._veto_chain.evaluate(state)
        if not veto_result.allowed:
            return veto_result, Selected(action="no_action", selected_by="vetoed")
        selection = self._fallback.select(state)
        return veto_result, selection
