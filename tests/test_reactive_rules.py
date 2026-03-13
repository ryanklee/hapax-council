"""Tests for cockpit/engine/reactive_rules.py — Phase B infrastructure rules.

Self-contained, asyncio_mode="auto", unittest.mock only.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cockpit.engine.models import ChangeEvent
from cockpit.engine.rules import RuleRegistry, evaluate_rules
from cockpit.engine.reactive_rules import (
    INFRASTRUCTURE_RULES,
    register_infrastructure_rules,
    _handle_collector_refresh,
    _handle_config_changed,
    _handle_sdlc_event,
)


def _event(path: str, event_type: str = "modified") -> ChangeEvent:
    return ChangeEvent(
        path=Path(path),
        event_type=event_type,
        doc_type=None,
        frontmatter=None,
        timestamp=datetime.now(),
    )


def _registry() -> RuleRegistry:
    reg = RuleRegistry()
    register_infrastructure_rules(reg)
    # Reset cooldowns for test isolation
    for rule in reg:
        rule._last_fired = 0.0
    return reg


# ── TestRegistration ────────────────────────────────────────────────────────


class TestRegistration:
    def test_registers_three_rules(self):
        reg = _registry()
        assert len(reg) == 3

    def test_rule_names(self):
        reg = _registry()
        names = {r.name for r in reg}
        assert names == {"collector-refresh", "config-changed", "sdlc-event-logged"}

    def test_all_phase_zero(self):
        for rule in INFRASTRUCTURE_RULES:
            assert rule.phase == 0


# ── TestCollectorRefreshRule ────────────────────────────────────────────────


class TestCollectorRefreshRule:
    def test_health_history_triggers_fast(self):
        reg = _registry()
        plan = evaluate_rules(_event("/data/profiles/health-history.jsonl"), reg)
        assert len(plan.actions) == 1
        assert plan.actions[0].name == "collector-refresh-fast"
        assert plan.actions[0].args["tier"] == "fast"

    def test_drift_report_triggers_slow(self):
        reg = _registry()
        plan = evaluate_rules(_event("/data/profiles/drift-report.json"), reg)
        assert len(plan.actions) == 1
        assert plan.actions[0].name == "collector-refresh-slow"
        assert plan.actions[0].args["tier"] == "slow"

    def test_scout_report_triggers_slow(self):
        reg = _registry()
        plan = evaluate_rules(_event("/data/profiles/scout-report.json"), reg)
        assert len(plan.actions) == 1
        assert plan.actions[0].name == "collector-refresh-slow"

    def test_operator_profile_triggers_slow(self):
        reg = _registry()
        plan = evaluate_rules(_event("/data/profiles/operator-profile.json"), reg)
        assert len(plan.actions) == 1
        assert plan.actions[0].name == "collector-refresh-slow"

    def test_unrelated_file_no_match(self):
        reg = _registry()
        plan = evaluate_rules(_event("/data/profiles/random-file.txt"), reg)
        assert len(plan.actions) == 0

    @patch("cockpit.api.cache.cache")
    async def test_handler_fast(self, mock_cache):
        mock_cache.refresh_fast = AsyncMock()
        result = await _handle_collector_refresh(tier="fast")
        mock_cache.refresh_fast.assert_awaited_once()
        assert result == "cache.refresh_fast"

    @patch("cockpit.api.cache.cache")
    async def test_handler_slow(self, mock_cache):
        mock_cache.refresh_slow = AsyncMock()
        result = await _handle_collector_refresh(tier="slow")
        mock_cache.refresh_slow.assert_awaited_once()
        assert result == "cache.refresh_slow"


# ── TestConfigChangedRule ───────────────────────────────────────────────────


class TestConfigChangedRule:
    def test_registry_yaml_triggers(self):
        reg = _registry()
        plan = evaluate_rules(
            _event("/project/axioms/registry.yaml"),
            reg,
        )
        assert len(plan.actions) == 1
        assert plan.actions[0].name == "config-changed"

    def test_non_axiom_yaml_no_match(self):
        reg = _registry()
        plan = evaluate_rules(_event("/data/profiles/registry.yaml"), reg)
        assert len(plan.actions) == 0

    def test_axiom_implication_no_match(self):
        reg = _registry()
        plan = evaluate_rules(
            _event("/project/axioms/implications/single_user.yaml"),
            reg,
        )
        # Only registry.yaml triggers, not implication files
        assert not any(a.name == "config-changed" for a in plan.actions)

    async def test_handler_returns_reloaded(self):
        result = await _handle_config_changed(path="/axioms/registry.yaml")
        assert result == "config-reloaded"


# ── TestSdlcEventRule ───────────────────────────────────────────────────────


class TestSdlcEventRule:
    def test_sdlc_events_triggers(self):
        reg = _registry()
        plan = evaluate_rules(
            _event("/data/profiles/sdlc-events.jsonl"),
            reg,
        )
        # Should match both sdlc-event-logged and collector-refresh (sdlc-events.jsonl
        # is not in the refresh file list, so only sdlc rule fires)
        sdlc_actions = [a for a in plan.actions if a.name == "sdlc-event-logged"]
        assert len(sdlc_actions) == 1

    def test_other_jsonl_no_sdlc_match(self):
        reg = _registry()
        plan = evaluate_rules(
            _event("/data/profiles/health-history.jsonl"),
            reg,
        )
        sdlc_actions = [a for a in plan.actions if a.name == "sdlc-event-logged"]
        assert len(sdlc_actions) == 0

    def test_sdlc_rule_has_cooldown(self):
        rule = next(r for r in INFRASTRUCTURE_RULES if r.name == "sdlc-event-logged")
        assert rule.cooldown_s == 30

    @patch("cockpit.api.cache.cache")
    @patch("shared.notify.send_notification", return_value=True)
    async def test_handler_sends_notification_and_refreshes(self, mock_notify, mock_cache):
        mock_cache.refresh_slow = AsyncMock()

        with patch("asyncio.to_thread", new=AsyncMock(return_value=True)):
            result = await _handle_sdlc_event(path="/profiles/sdlc-events.jsonl")

        assert result == "sdlc-notified"


# ── TestEdgeCases ───────────────────────────────────────────────────────────


class TestEdgeCases:
    def test_sdlc_and_health_both_fire_independently(self):
        """sdlc-events.jsonl fires sdlc rule, health-history fires collector rule."""
        reg = RuleRegistry()
        register_infrastructure_rules(reg)

        sdlc_plan = evaluate_rules(_event("/data/profiles/sdlc-events.jsonl"), reg)
        sdlc_names = {a.name for a in sdlc_plan.actions}
        assert "sdlc-event-logged" in sdlc_names

        # Reset cooldowns for clean test
        for r in reg:
            r._last_fired = 0.0

        health_plan = evaluate_rules(_event("/data/profiles/health-history.jsonl"), reg)
        health_names = {a.name for a in health_plan.actions}
        assert "collector-refresh-fast" in health_names
        assert "sdlc-event-logged" not in health_names

    def test_created_event_also_matches(self):
        reg = _registry()
        plan = evaluate_rules(
            _event("/data/profiles/health-history.jsonl", event_type="created"),
            reg,
        )
        assert len(plan.actions) == 1
