"""Tests for cockpit/engine/reactive_rules.py — reactive engine rules.

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
    ALL_RULES,
    INFRASTRUCTURE_RULES,
    register_infrastructure_rules,
    _handle_collector_refresh,
    _handle_config_changed,
    _handle_rag_ingest,
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
    def test_registers_four_rules(self):
        reg = _registry()
        assert len(reg) == 4

    def test_rule_names(self):
        reg = _registry()
        names = {r.name for r in reg}
        assert names == {
            "collector-refresh",
            "config-changed",
            "sdlc-event-logged",
            "rag-source-landed",
        }

    def test_phase_zero_rules(self):
        phase0 = [r for r in ALL_RULES if r.phase == 0]
        assert len(phase0) == 3

    def test_phase_one_rules(self):
        phase1 = [r for r in ALL_RULES if r.phase == 1]
        assert len(phase1) == 1
        assert phase1[0].name == "rag-source-landed"


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


# ── TestRagSourceRule ───────────────────────────────────────────────────────


class TestRagSourceRule:
    def test_created_file_in_rag_sources_triggers(self):
        reg = _registry()
        plan = evaluate_rules(
            _event("/home/user/documents/rag-sources/gmail/inbox/msg.md", event_type="created"),
            reg,
        )
        rag_actions = [a for a in plan.actions if a.name.startswith("rag-ingest:")]
        assert len(rag_actions) == 1
        assert rag_actions[0].phase == 1

    def test_modified_file_does_not_trigger(self):
        """Only created events trigger — avoids re-ingest on file touch."""
        reg = _registry()
        plan = evaluate_rules(
            _event("/home/user/documents/rag-sources/gmail/inbox/msg.md", event_type="modified"),
            reg,
        )
        rag_actions = [a for a in plan.actions if a.name.startswith("rag-ingest:")]
        assert len(rag_actions) == 0

    def test_non_rag_source_path_no_match(self):
        reg = _registry()
        plan = evaluate_rules(
            _event("/data/profiles/health-history.jsonl", event_type="created"),
            reg,
        )
        rag_actions = [a for a in plan.actions if a.name.startswith("rag-ingest:")]
        assert len(rag_actions) == 0

    def test_action_name_includes_path(self):
        """Action name includes file path to prevent cross-file dedup."""
        reg = _registry()
        path = "/home/user/documents/rag-sources/gdrive/doc.pdf"
        plan = evaluate_rules(_event(path, event_type="created"), reg)
        rag_actions = [a for a in plan.actions if a.name.startswith("rag-ingest:")]
        assert len(rag_actions) == 1
        assert path in rag_actions[0].name

    def test_multiple_services_detected(self):
        """Different rag-sources subdirs all trigger."""
        reg = _registry()
        for service_path in ["rag-sources/gdrive", "rag-sources/obsidian", "rag-sources/chrome"]:
            for r in reg:
                r._last_fired = 0.0
            plan = evaluate_rules(
                _event(f"/home/user/documents/{service_path}/file.md", event_type="created"),
                reg,
            )
            rag_actions = [a for a in plan.actions if a.name.startswith("rag-ingest:")]
            assert len(rag_actions) == 1, f"Failed for {service_path}"

    @patch("agents.ingest.ingest_file", return_value=(True, ""))
    async def test_handler_success(self, mock_ingest):
        with patch("asyncio.to_thread", new=AsyncMock(return_value=(True, ""))) as mock_thread:
            result = await _handle_rag_ingest(path="/rag-sources/gmail/msg.md")
        assert "ingested:" in result

    @patch("agents.ingest.ingest_file", return_value=(False, "qdrant down"))
    async def test_handler_failure_raises(self, mock_ingest):
        with patch("asyncio.to_thread", new=AsyncMock(return_value=(False, "qdrant down"))):
            with pytest.raises(RuntimeError, match="Ingest failed"):
                await _handle_rag_ingest(path="/rag-sources/gmail/msg.md")
