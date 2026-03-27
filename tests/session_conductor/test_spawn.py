"""Tests for the session spawn and reunion rule."""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

import yaml

from agents.session_conductor.rules import HookEvent
from agents.session_conductor.rules.spawn import SpawnRule, detect_spawn_intent
from agents.session_conductor.state import SessionState
from agents.session_conductor.topology import TopologyConfig


def _make_state(session_id: str = "sess-alpha", parent: str | None = None) -> SessionState:
    state = SessionState(
        session_id=session_id,
        pid=12345,
        started_at=datetime.now(),
    )
    state.parent_session = parent
    return state


def _make_user_msg_event(message: str) -> HookEvent:
    return HookEvent(
        event_type="post_tool_use",
        tool_name="Agent",
        tool_input={},
        session_id="sess-alpha",
        user_message=message,
    )


def _make_edit_event(file_path: str, session_id: str = "sess-beta") -> HookEvent:
    return HookEvent(
        event_type="pre_tool_use",
        tool_name="Edit",
        tool_input={"file_path": file_path},
        session_id=session_id,
    )


# ---------------------------------------------------------------------------
# detect_spawn_intent tests
# ---------------------------------------------------------------------------


def test_detect_spawn_intent_break_out():
    assert detect_spawn_intent("let's break this out into another session") is True


def test_detect_spawn_intent_another_session_fix():
    assert detect_spawn_intent("another session fix this bug") is True


def test_detect_spawn_intent_spawn_child():
    assert detect_spawn_intent("spawn a child session for this") is True


def test_detect_spawn_intent_no_match():
    assert detect_spawn_intent("just keep going with what we have") is False


# ---------------------------------------------------------------------------
# SpawnRule tests
# ---------------------------------------------------------------------------


def test_writes_manifest_on_spawn_intent(tmp_path: Path):
    state = _make_state()
    topology = TopologyConfig()
    rule = SpawnRule(topology, state, spawns_dir=tmp_path)

    event = _make_user_msg_event("let's break this out into a new session for the relay work")
    rule.on_post_tool_use(event)

    manifests = list(tmp_path.glob("*.yaml"))
    assert len(manifests) == 1
    data = yaml.safe_load(manifests[0].read_text())
    assert data["status"] == "pending"
    assert data["parent_session"] == "sess-alpha"
    assert len(state.children) == 1


def test_child_claims_manifest(tmp_path: Path):
    # Parent writes manifest
    parent_state = _make_state("sess-alpha")
    topology = TopologyConfig()
    parent_rule = SpawnRule(topology, parent_state, spawns_dir=tmp_path)
    parent_rule._write_manifest(topic="fix relay bug")

    # Child claims it
    child_state = _make_state("sess-beta")
    child_rule = SpawnRule(topology, child_state, spawns_dir=tmp_path)
    claimed = child_rule.claim_pending_manifest(child_state)

    assert claimed is not None
    assert claimed["status"] == "claimed"
    assert claimed["claimed_by"] == "sess-beta"
    assert child_state.parent_session == "sess-alpha"


def test_child_blocked_from_parent_files(tmp_path: Path):
    # Parent session has in-flight files
    parent_state = _make_state("sess-alpha")
    parent_state.in_flight_files = {"/foo/bar.py", "/baz/qux.py"}

    # Child session knows it has a parent
    child_state = _make_state("sess-beta", parent="sess-alpha")
    child_state.in_flight_files = {"/foo/bar.py", "/baz/qux.py"}  # same files as parent

    topology = TopologyConfig()
    # Child's rule knows about the parent's blocked files via state
    child_rule = SpawnRule(topology, child_state, spawns_dir=tmp_path)

    # Block child from editing a parent-owned file
    event = _make_edit_event("/foo/bar.py", session_id="sess-beta")
    response = child_rule.on_pre_tool_use(event)

    assert response is not None
    assert response.action == "block"
    assert "sess-alpha" in (response.message or "")


def test_stale_manifest_ignored(tmp_path: Path):
    topology = TopologyConfig()
    state = _make_state("sess-alpha")
    rule = SpawnRule(topology, state, spawns_dir=tmp_path)

    # Write a manifest with an old timestamp (>10 minutes ago)
    old_time = (datetime.now() - timedelta(minutes=15)).isoformat()
    manifest = {
        "child_id": "oldchild",
        "parent_session": "sess-parent",
        "topic": "old work",
        "created_at": old_time,
        "status": "pending",
        "blocked_patterns": [],
    }
    (tmp_path / "oldchild.yaml").write_text(yaml.dump(manifest))

    child_state = _make_state("sess-new")
    claimed = rule.claim_pending_manifest(child_state)
    assert claimed is None


def test_reunion_injects_results(tmp_path: Path):
    from agents.session_conductor.state import ChildSession

    parent_state = _make_state("sess-alpha")
    topology = TopologyConfig()
    rule = SpawnRule(topology, parent_state, spawns_dir=tmp_path)

    # Write a completed manifest
    manifest_path = tmp_path / "child01.yaml"
    manifest_data = {
        "child_id": "child01",
        "parent_session": "sess-alpha",
        "topic": "fix relay",
        "status": "completed",
        "result_summary": "Fixed the relay bug in 3 files",
    }
    manifest_path.write_text(yaml.dump(manifest_data))

    # Add the child to parent state
    child = ChildSession(
        session_id="child01",
        topic="fix relay",
        spawn_manifest=manifest_path,
        status="pending",
    )
    parent_state.children.append(child)

    completed = rule.check_completed_children(parent_state)
    assert len(completed) == 1
    assert completed[0]["result_summary"] == "Fixed the relay bug in 3 files"
    assert child.status == "completed"
