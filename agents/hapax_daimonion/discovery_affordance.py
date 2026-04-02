"""Novel capability discovery — the recursive meta-affordance.

When no existing capability matches an intention, the exploration tracker
emits boredom/curiosity impingements. This affordance matches those signals
and searches for capabilities that could fulfill the unresolved need.

Discovery (searching for what's possible) is read-only and safe.
Acquisition (installing/configuring) requires operator consent.
"""

from __future__ import annotations

import logging

from shared.impingement import Impingement

log = logging.getLogger("capability.discovery")

DISCOVERY_AFFORDANCE: tuple[str, str] = (
    "capability_discovery",
    "Discover and acquire new capabilities when no existing capability matches an intention. "
    "Find tools, services, or resources that could fulfill unmet cognitive needs.",
)


class CapabilityDiscoveryHandler:
    """Handles the capability_discovery affordance."""

    consent_required: bool = True

    def extract_intent(self, impingement: Impingement) -> str:
        content = impingement.content or {}
        narrative = content.get("narrative", "")
        if narrative:
            return narrative
        return f"unresolved intent from {impingement.source}"

    def search(self, intent: str) -> list[dict]:
        log.info("Searching for capability: %s", intent[:80])
        return []  # stub for Phase 5

    def propose(self, capabilities: list[dict]) -> None:
        for cap in capabilities:
            log.info(
                "Discovered potential capability: %s — %s (from %s)",
                cap.get("name", "unknown"),
                cap.get("description", ""),
                cap.get("source", "unknown"),
            )
