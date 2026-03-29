"""Adapters that wrap existing types as Capability protocol instances.

PerceptionBackend has available() with no args (checks hardware).
This adapter wraps it to conform to the Capability protocol.
"""

from __future__ import annotations

from shared.capability import CapabilityCategory, ResourceTier, SystemContext


class PerceptionBackendAdapter:
    """Wraps a PerceptionBackend as a Capability for registry purposes."""

    def __init__(self, backend) -> None:
        self._backend = backend

    @property
    def name(self) -> str:
        return self._backend.name

    @property
    def category(self) -> CapabilityCategory:
        return CapabilityCategory.PERCEPTION

    @property
    def resource_tier(self) -> ResourceTier:
        tier = self._backend.tier
        if tier.value == "fast":
            return ResourceTier.INSTANT
        if tier.value == "slow":
            return ResourceTier.LIGHT
        return ResourceTier.INSTANT

    def available(self, ctx: SystemContext) -> bool:
        return self._backend.available()

    def degrade(self) -> str:
        return f"Perception backend {self._backend.name} is unavailable."

    @property
    def backend(self):
        """Access the wrapped backend for medium-specific operations."""
        return self._backend
