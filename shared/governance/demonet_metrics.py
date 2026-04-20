"""Prometheus counters for the demonet (Ring 1 + Ring 2) pipeline.

Lazy-registered counters shared across governance modules per
D-23 / AUDIT §11.1. Pattern mirrors ``shared.evil_pet_state._EngineMetrics``
— tolerate prometheus_client absence so tests + headless smoke runs
never crash on import. All ``inc_*`` methods are no-ops when
prometheus_client is unavailable or registration failed.

Counters exposed:

- ``hapax_demonet_gate_decisions_total{risk, allowed, surface}``
  — one per MonetizationRiskGate.assess() call
- ``hapax_demonet_classifier_calls_total{verdict, used_fallback}``
  — one per classify_with_fallback() resolution (success or
  fallback)
- ``hapax_demonet_classifier_health_transitions_total{from_state,
  to_state}`` — one per ClassifierDegradedController transition
- ``hapax_demonet_music_policy_mutes_total{path, reason_class}``
  — one per MusicPolicy decision with should_mute=True

Callers import the module-level singleton ``METRICS`` and call the
typed inc_* methods. Tests never depend on live counters; they
stub or inspect the underlying Counter objects via
``_registered_counter(name)`` when needed.

Reference:
    - docs/superpowers/handoff/2026-04-20-delta-wsjf-reorganization.md §4.11 D-23
    - docs/research/2026-04-20-six-hour-audit.md §11.1
"""

from __future__ import annotations

import logging
from typing import Any

log = logging.getLogger(__name__)


class _DemonetMetrics:
    """Lazy-registered Prometheus counters for the demonet pipeline."""

    def __init__(self) -> None:
        self._gate_decisions: Any = None
        self._classifier_calls: Any = None
        self._classifier_health: Any = None
        self._music_mutes: Any = None
        try:
            from prometheus_client import REGISTRY, Counter
        except ImportError:
            return
        for name, doc, labels, attr in (
            (
                "hapax_demonet_gate_decisions_total",
                "MonetizationRiskGate.assess() decisions by risk, allowed, surface",
                ["risk", "allowed", "surface"],
                "_gate_decisions",
            ),
            (
                "hapax_demonet_classifier_calls_total",
                "Ring 2 classifier calls by verdict risk and whether fallback fired",
                ["verdict", "used_fallback"],
                "_classifier_calls",
            ),
            (
                "hapax_demonet_classifier_health_transitions_total",
                "ClassifierDegradedController state transitions",
                ["from_state", "to_state"],
                "_classifier_health",
            ),
            (
                "hapax_demonet_music_policy_mutes_total",
                "MusicPolicy mute decisions by path and reason class",
                ["path", "reason_class"],
                "_music_mutes",
            ),
        ):
            try:
                setattr(self, attr, Counter(name, doc, labels))
            except ValueError:
                # Already registered (import re-runs across tests).
                setattr(self, attr, REGISTRY._names_to_collectors.get(name))  # noqa: SLF001

    # ── increment helpers ────────────────────────────────────────────

    def inc_gate_decision(self, risk: str, allowed: bool, surface: str | None) -> None:
        if self._gate_decisions is None:
            return
        try:
            self._gate_decisions.labels(
                risk=risk,
                allowed="true" if allowed else "false",
                surface=surface or "none",
            ).inc()
        except Exception:
            log.debug("gate_decisions counter inc failed", exc_info=True)

    def inc_classifier_call(self, verdict: str, used_fallback: bool) -> None:
        if self._classifier_calls is None:
            return
        try:
            self._classifier_calls.labels(
                verdict=verdict,
                used_fallback="true" if used_fallback else "false",
            ).inc()
        except Exception:
            log.debug("classifier_calls counter inc failed", exc_info=True)

    def inc_classifier_transition(self, from_state: str, to_state: str) -> None:
        if self._classifier_health is None:
            return
        try:
            self._classifier_health.labels(from_state=from_state, to_state=to_state).inc()
        except Exception:
            log.debug("classifier_health counter inc failed", exc_info=True)

    def inc_music_mute(self, path: str, reason_class: str) -> None:
        if self._music_mutes is None:
            return
        try:
            self._music_mutes.labels(path=path, reason_class=reason_class).inc()
        except Exception:
            log.debug("music_mutes counter inc failed", exc_info=True)


# Module-level singleton — production services share this.
METRICS = _DemonetMetrics()


__all__ = ["METRICS"]
