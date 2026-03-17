"""shared/spec_registry.py — Load and query operational specifications.

Mirrors shared/axiom_registry.py but for positive invariants. Specs define
what the system guarantees, not what it prohibits.

Usage:
    specs = load_specs()
    for spec in specs:
        print(f"{spec.id}: {spec.text}")
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

SPECS_PATH = Path(__file__).resolve().parent.parent / "specs" / "registry.yaml"


@dataclass(frozen=True)
class Spec:
    """A single operational specification (positive invariant)."""

    id: str
    tier: str  # V0 | V1 | V2
    text: str
    system_id: str
    system_name: str
    properties: list[str] = field(default_factory=list)
    verification: str = "integration"
    measured_by: str = ""


@dataclass(frozen=True)
class SpecSystem:
    """A circulatory system with its specs."""

    id: str
    name: str
    heartbeat: str
    description: str
    specs: list[Spec] = field(default_factory=list)


def load_specs(
    path: Path | None = None,
    tier: str = "",
    system_id: str = "",
) -> list[Spec]:
    """Load all specs, optionally filtered by tier or system.

    Args:
        path: Override path to specs/registry.yaml.
        tier: Filter to specs of this tier (e.g., "V0").
        system_id: Filter to specs in this system (e.g., "stimmung").

    Returns:
        Flat list of Spec objects.
    """
    systems = load_systems(path)
    specs: list[Spec] = []
    for system in systems:
        if system_id and system.id != system_id:
            continue
        for spec in system.specs:
            if tier and spec.tier != tier:
                continue
            specs.append(spec)
    return specs


def load_systems(path: Path | None = None) -> list[SpecSystem]:
    """Load all spec systems from the registry."""
    import yaml

    registry_path = path or SPECS_PATH
    try:
        data = yaml.safe_load(registry_path.read_text(encoding="utf-8"))
    except Exception:
        log.warning("Failed to load spec registry from %s", registry_path, exc_info=True)
        return []

    systems: list[SpecSystem] = []
    for sys_data in data.get("systems", []):
        sys_id = sys_data.get("id", "")
        sys_name = sys_data.get("name", "")
        specs: list[Spec] = []
        for spec_data in sys_data.get("specs", []):
            specs.append(
                Spec(
                    id=spec_data.get("id", ""),
                    tier=spec_data.get("tier", "V2"),
                    text=spec_data.get("text", "").strip(),
                    system_id=sys_id,
                    system_name=sys_name,
                    properties=spec_data.get("properties", []),
                    verification=spec_data.get("verification", "integration"),
                    measured_by=spec_data.get("measured_by", ""),
                )
            )
        systems.append(
            SpecSystem(
                id=sys_id,
                name=sys_name,
                heartbeat=sys_data.get("heartbeat", ""),
                description=sys_data.get("description", "").strip(),
                specs=specs,
            )
        )
    return systems


def get_spec(spec_id: str, path: Path | None = None) -> Spec | None:
    """Look up a single spec by ID."""
    for spec in load_specs(path):
        if spec.id == spec_id:
            return spec
    return None


def spec_summary(path: Path | None = None) -> dict[str, Any]:
    """Summary statistics for the spec registry."""
    systems = load_systems(path)
    total = sum(len(s.specs) for s in systems)
    by_tier: dict[str, int] = {}
    by_verification: dict[str, int] = {}
    for s in systems:
        for spec in s.specs:
            by_tier[spec.tier] = by_tier.get(spec.tier, 0) + 1
            by_verification[spec.verification] = by_verification.get(spec.verification, 0) + 1
    return {
        "systems": len(systems),
        "total_specs": total,
        "by_tier": by_tier,
        "by_verification": by_verification,
        "system_names": [s.name for s in systems],
    }
