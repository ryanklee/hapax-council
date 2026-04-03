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
        """Search for capabilities matching the intent via DuckDuckGo Instant Answers.

        Returns a list of {name, description, source} dicts for propose().
        Uses the DuckDuckGo API (exception-duckduckgo-instant in enforcement-exceptions.yaml).
        """
        try:
            import httpx

            resp = httpx.get(
                "https://api.duckduckgo.com/",
                params={"q": intent, "format": "json", "no_html": "1"},
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()

            results: list[dict] = []
            abstract = data.get("AbstractText", "")
            if abstract:
                results.append(
                    {
                        "name": data.get("AbstractSource", "web"),
                        "description": abstract[:200],
                        "source": "duckduckgo",
                    }
                )
            for topic in data.get("RelatedTopics", [])[:3]:
                if isinstance(topic, dict) and topic.get("Text"):
                    results.append(
                        {
                            "name": (topic.get("FirstURL", "") or "related")[-40:],
                            "description": topic["Text"][:150],
                            "source": "duckduckgo",
                        }
                    )
            return results
        except Exception:
            log.debug("Discovery search failed for: %s", intent[:80], exc_info=True)
            return []

    def propose(self, capabilities: list[dict]) -> None:
        for cap in capabilities:
            log.info(
                "Discovered potential capability: %s — %s (from %s)",
                cap.get("name", "unknown"),
                cap.get("description", ""),
                cap.get("source", "unknown"),
            )
