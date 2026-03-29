"""Shared capability protocol for all Hapax subsystems.

Every capability — perception backends, tools, expression (speech, visual),
modulation — conforms to this protocol. It declares what it provides, what
it requires, when it's available, and how it degrades.

Phase 1 of capability parity (queue #017).
"""

from __future__ import annotations

import enum
import logging
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

log = logging.getLogger(__name__)


class CapabilityCategory(enum.Enum):
    PERCEPTION = "perception"
    TOOL = "tool"
    EXPRESSION = "expression"
    MODULATION = "modulation"


class ResourceTier(enum.Enum):
    INSTANT = "instant"
    LIGHT = "light"
    HEAVY = "heavy"


@dataclass(frozen=True)
class SystemContext:
    """Snapshot of system state used for capability availability decisions.

    Replaces ToolContext with a universal context used by all capability types.
    """

    stimmung_stance: str = "nominal"
    consent_state: dict = field(default_factory=dict)
    guest_present: bool = False
    active_backends: frozenset[str] = field(default_factory=frozenset)
    working_mode: str = "rnd"
    experiment_flags: dict = field(default_factory=dict)
    tpn_active: bool = False


@runtime_checkable
class Capability(Protocol):
    """Universal interface for all Hapax capabilities."""

    @property
    def name(self) -> str: ...

    @property
    def category(self) -> CapabilityCategory: ...

    @property
    def resource_tier(self) -> ResourceTier: ...

    def available(self, ctx: SystemContext) -> bool: ...

    def degrade(self) -> str: ...


class CapabilityRegistry:
    """Unified registry for all capabilities across all categories."""

    def __init__(self) -> None:
        self._capabilities: dict[str, Capability] = {}

    def register(self, cap: Capability) -> None:
        if cap.name in self._capabilities:
            raise ValueError(f"Capability {cap.name!r} already registered")
        self._capabilities[cap.name] = cap
        log.debug("Registered capability: %s (%s)", cap.name, cap.category.value)

    def get(self, name: str) -> Capability | None:
        return self._capabilities.get(name)

    def all(self) -> list[Capability]:
        return list(self._capabilities.values())

    def available(
        self,
        ctx: SystemContext,
        category: CapabilityCategory | None = None,
    ) -> list[Capability]:
        caps = self._capabilities.values()
        if category is not None:
            caps = [c for c in caps if c.category == category]
        return [c for c in caps if c.available(ctx)]
