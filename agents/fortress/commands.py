"""Fortress command types — serializable action descriptors.

Each command represents a game action to send through the DFHack bridge.
Commands are frozen (no TOCTOU bugs) and carry full provenance.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class FortressCommand:
    """A serializable fortress action descriptor."""

    id: str  # unique command ID (assigned by bridge on send)
    action: str  # dig, build, place, order, military, labor, pause, save, raw
    chain: str  # which governance chain produced this
    params: dict[str, object] = field(default_factory=dict)
    created_at: float = 0.0
    governance_allowed: bool = True
    governance_denied_by: tuple[str, ...] = ()

    def to_bridge_dict(self) -> dict[str, object]:
        """Convert to dict suitable for DFHackBridge.send_command()."""
        return {"action": self.action, **self.params}


def cmd_dig(chain: str, blueprint_csv: str, **kw: object) -> FortressCommand:
    """Create a dig command from a blueprint CSV string."""
    return FortressCommand(
        id="",
        action="dig",
        chain=chain,
        params={"blueprint": blueprint_csv},
        **kw,  # type: ignore[arg-type]
    )


def cmd_build(chain: str, blueprint_csv: str, **kw: object) -> FortressCommand:
    """Create a build command from a blueprint CSV string."""
    return FortressCommand(
        id="",
        action="build",
        chain=chain,
        params={"blueprint": blueprint_csv},
        **kw,  # type: ignore[arg-type]
    )


def cmd_place(chain: str, blueprint_csv: str, **kw: object) -> FortressCommand:
    """Create a furniture placement command from a blueprint CSV string."""
    return FortressCommand(
        id="",
        action="place",
        chain=chain,
        params={"blueprint": blueprint_csv},
        **kw,  # type: ignore[arg-type]
    )


def cmd_order(
    chain: str,
    item_type: str,
    material: str = "",
    quantity: int = 1,
    **kw: object,
) -> FortressCommand:
    """Create a work order command."""
    return FortressCommand(
        id="",
        action="order",
        chain=chain,
        params={"item_type": item_type, "material": material, "quantity": quantity},
        **kw,
    )


def cmd_military(chain: str, operation: str, **kw: object) -> FortressCommand:
    """Create a military command (station, attack, train, etc.)."""
    params = {"operation": operation}
    # Pull known military params out of kw, leave the rest for FortressCommand
    for key in ("squad_id", "target_x", "target_y", "target_z"):
        if key in kw:
            params[key] = kw.pop(key)
    return FortressCommand(id="", action="military", chain=chain, params=params, **kw)


def cmd_labor(
    chain: str,
    unit_id: int,
    labor: str,
    enabled: bool = True,
    **kw: object,
) -> FortressCommand:
    """Create a labor assignment command."""
    return FortressCommand(
        id="",
        action="labor",
        chain=chain,
        params={"unit_id": unit_id, "labor": labor, "enabled": enabled},
        **kw,
    )


def cmd_pause(chain: str, state: bool = True, **kw: object) -> FortressCommand:
    """Create a pause/unpause command."""
    return FortressCommand(id="", action="pause", chain=chain, params={"state": state}, **kw)
