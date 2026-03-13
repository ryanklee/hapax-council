"""cockpit/engine/reactive_rules.py — Phase B infrastructure rules (Phase 0 only).

Three deterministic rules that fire on filesystem changes:
- collector-refresh: refresh cockpit cache tier on profiles/ changes
- config-changed: log axiom registry reload on axioms/registry.yaml change
- sdlc-event-logged: notify + cache refresh on SDLC event append
"""

from __future__ import annotations

import asyncio
import logging

from cockpit.engine.models import Action, ChangeEvent
from cockpit.engine.rules import Rule

_log = logging.getLogger(__name__)

# ── File-to-cache-tier mapping ───────────────────────────────────────────────

_FAST_REFRESH_FILES = {"health-history.jsonl"}
_SLOW_REFRESH_FILES = {"drift-report.json", "scout-report.json", "operator-profile.json"}


# ── Handlers (lazy imports to avoid circular deps) ──────────────────────────


async def _handle_collector_refresh(*, tier: str) -> str:
    """Refresh the appropriate cockpit cache tier."""
    from cockpit.api.cache import cache

    if tier == "fast":
        await cache.refresh_fast()
    else:
        await cache.refresh_slow()
    _log.info("Cache %s refresh triggered by file change", tier)
    return f"cache.refresh_{tier}"


async def _handle_config_changed(*, path: str) -> str:
    """Log axiom registry change. No explicit reload needed — loaders read fresh."""
    _log.info("Axiom config changed: %s (loaders will pick up on next call)", path)
    return "config-reloaded"


async def _handle_sdlc_event(*, path: str) -> str:
    """Send notification and refresh slow cache for SDLC events."""
    from cockpit.api.cache import cache
    from shared.notify import send_notification

    await asyncio.to_thread(
        send_notification,
        "SDLC Pipeline Event",
        "New event logged to sdlc-events.jsonl",
        priority="default",
        tags=["gear"],
    )
    await cache.refresh_slow()
    _log.info("SDLC event notification sent + slow cache refreshed")
    return "sdlc-notified"


# ── Rule definitions ────────────────────────────────────────────────────────


def _collector_refresh_filter(event: ChangeEvent) -> bool:
    """Match profiles/ file changes that need cache refresh."""
    return event.path.name in _FAST_REFRESH_FILES | _SLOW_REFRESH_FILES


def _collector_refresh_produce(event: ChangeEvent) -> list[Action]:
    """Produce cache refresh action for the correct tier."""
    filename = event.path.name
    if filename in _FAST_REFRESH_FILES:
        tier = "fast"
    else:
        tier = "slow"
    return [
        Action(
            name=f"collector-refresh-{tier}",
            handler=_handle_collector_refresh,
            args={"tier": tier},
            phase=0,
            priority=10,
        )
    ]


def _config_changed_filter(event: ChangeEvent) -> bool:
    """Match axioms/registry.yaml modifications."""
    return event.path.name == "registry.yaml" and "axioms" in event.path.parts


def _config_changed_produce(event: ChangeEvent) -> list[Action]:
    return [
        Action(
            name="config-changed",
            handler=_handle_config_changed,
            args={"path": str(event.path)},
            phase=0,
            priority=5,
        )
    ]


def _sdlc_event_filter(event: ChangeEvent) -> bool:
    """Match sdlc-events.jsonl modifications."""
    return event.path.name == "sdlc-events.jsonl"


def _sdlc_event_produce(event: ChangeEvent) -> list[Action]:
    return [
        Action(
            name="sdlc-event-logged",
            handler=_handle_sdlc_event,
            args={"path": str(event.path)},
            phase=0,
            priority=20,
        )
    ]


# ── Registration ────────────────────────────────────────────────────────────

INFRASTRUCTURE_RULES: list[Rule] = [
    Rule(
        name="collector-refresh",
        description="Refresh cockpit cache tier when profiles/ data changes",
        trigger_filter=_collector_refresh_filter,
        produce=_collector_refresh_produce,
        phase=0,
    ),
    Rule(
        name="config-changed",
        description="Log axiom registry reload on axioms/registry.yaml change",
        trigger_filter=_config_changed_filter,
        produce=_config_changed_produce,
        phase=0,
    ),
    Rule(
        name="sdlc-event-logged",
        description="Notify and refresh cache on SDLC pipeline event",
        trigger_filter=_sdlc_event_filter,
        produce=_sdlc_event_produce,
        phase=0,
        cooldown_s=30,
    ),
]


def register_infrastructure_rules(registry) -> None:
    """Register all Phase B infrastructure rules on a RuleRegistry."""
    for rule in INFRASTRUCTURE_RULES:
        registry.register(rule)
    _log.info("Registered %d infrastructure rules", len(INFRASTRUCTURE_RULES))
