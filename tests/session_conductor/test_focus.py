"""Tests for the focus enforcement rule."""

from __future__ import annotations

from agents.session_conductor.rules import HookEvent
from agents.session_conductor.rules.focus import FocusRule
from agents.session_conductor.topology import TopologyConfig, WorkspaceConfig


def _make_topology(testing_workspace: int = 10) -> TopologyConfig:
    topology = TopologyConfig()
    topology.playwright.testing_workspace = testing_workspace
    topology.workspaces = [
        WorkspaceConfig(id=10, name="testing", monitor="HDMI-1"),
    ]
    return topology


def test_rewrites_playwright_tools():
    topology = _make_topology()
    rule = FocusRule(topology)
    event = HookEvent(
        event_type="pre_tool_use",
        tool_name="browser_navigate",
        tool_input={"url": "http://localhost:5173"},
        session_id="sess-1",
        user_message=None,
    )
    resp = rule.on_pre_tool_use(event)
    assert resp is not None
    assert resp.action == "rewrite"
    assert resp.rewrite is not None
    assert "workspace" in resp.rewrite or "10" in str(resp.rewrite)


def test_ignores_non_playwright_tools():
    topology = _make_topology()
    rule = FocusRule(topology)
    event = HookEvent(
        event_type="pre_tool_use",
        tool_name="Read",
        tool_input={"file_path": "/tmp/foo.py"},
        session_id="sess-1",
        user_message=None,
    )
    resp = rule.on_pre_tool_use(event)
    assert resp is None


def test_blocks_workspace_switch_commands():
    topology = _make_topology()
    rule = FocusRule(topology)
    event = HookEvent(
        event_type="pre_tool_use",
        tool_name="Bash",
        tool_input={"command": "hyprctl dispatch workspace 3"},
        session_id="sess-1",
        user_message=None,
    )
    resp = rule.on_pre_tool_use(event)
    assert resp is not None
    assert resp.action == "rewrite"
    # Should be rewritten to silent variant
    assert resp.rewrite is not None


def test_allows_silent_commands():
    topology = _make_topology()
    rule = FocusRule(topology)
    event = HookEvent(
        event_type="pre_tool_use",
        tool_name="Bash",
        tool_input={"command": "hyprctl dispatch workspace silent:3"},
        session_id="sess-1",
        user_message=None,
    )
    resp = rule.on_pre_tool_use(event)
    assert resp is None
