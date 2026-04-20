"""Tests for agents/relay_to_cc_tasks.py (D-30 Phase 5).

Mirrors relay-yaml active_queue_items[] into vault cc-task notes.
Tests use synthetic relay yaml + tmp vault so the operator's real
~/.cache/hapax/relay and ~/Documents/Personal vault are never touched.
"""

from __future__ import annotations

from pathlib import Path

from agents.relay_to_cc_tasks import (
    RelayQueueItem,
    load_relay_queue_items,
    mirror,
    render_task_note,
    vault_note_path,
)


def _write_relay(relay_dir: Path, role: str, items: list[str]) -> None:
    relay_dir.mkdir(parents=True, exist_ok=True)
    yaml_text = f"session: {role}\nactive_queue_items:\n"
    for item in items:
        # Quote each item so YAML preserves embedded punctuation.
        escaped = item.replace('"', '\\"')
        yaml_text += f'  - "{escaped}"\n'
    (relay_dir / f"{role}.yaml").write_text(yaml_text)


class TestRelayQueueItemTaskId:
    def test_deterministic(self) -> None:
        a = RelayQueueItem(role="alpha", title="hello")
        b = RelayQueueItem(role="delta", title="hello")
        # Same title → same hash → same task_id, regardless of role.
        assert a.task_id == b.task_id

    def test_different_titles_different_ids(self) -> None:
        a = RelayQueueItem(role="alpha", title="hello")
        b = RelayQueueItem(role="alpha", title="world")
        assert a.task_id != b.task_id

    def test_id_format(self) -> None:
        item = RelayQueueItem(role="alpha", title="hello")
        assert item.task_id.startswith("relay-")
        assert len(item.task_id) == len("relay-") + 8


class TestLoadRelayQueueItems:
    def test_loads_from_each_role_file(self, tmp_path: Path) -> None:
        _write_relay(tmp_path, "alpha", ["alpha task 1", "alpha task 2"])
        _write_relay(tmp_path, "beta", ["beta task 1"])
        items = load_relay_queue_items(tmp_path)
        roles = {it.role for it in items}
        assert roles == {"alpha", "beta"}
        titles = {it.title for it in items}
        assert "alpha task 1" in titles
        assert "alpha task 2" in titles
        assert "beta task 1" in titles

    def test_skips_missing_role_files(self, tmp_path: Path) -> None:
        _write_relay(tmp_path, "alpha", ["only alpha"])
        items = load_relay_queue_items(tmp_path)
        assert len(items) == 1
        assert items[0].role == "alpha"

    def test_handles_malformed_yaml(self, tmp_path: Path) -> None:
        tmp_path.mkdir(parents=True, exist_ok=True)
        (tmp_path / "alpha.yaml").write_text("{not valid yaml")
        # Plus one valid file.
        _write_relay(tmp_path, "delta", ["valid"])
        items = load_relay_queue_items(tmp_path)
        assert len(items) == 1  # only the valid one

    def test_skips_non_string_entries(self, tmp_path: Path) -> None:
        tmp_path.mkdir(parents=True, exist_ok=True)
        (tmp_path / "alpha.yaml").write_text(
            "active_queue_items:\n  - real string\n  - 42\n  - {nested: dict}\n"
        )
        items = load_relay_queue_items(tmp_path)
        assert [i.title for i in items] == ["real string"]

    def test_missing_relay_dir_returns_empty(self, tmp_path: Path) -> None:
        items = load_relay_queue_items(tmp_path / "missing")
        assert items == []


class TestRenderTaskNote:
    def test_required_frontmatter_fields(self) -> None:
        item = RelayQueueItem(role="alpha", title="Test queue item")
        body = render_task_note(item)
        assert "type: cc-task" in body
        assert f"task_id: {item.task_id}" in body
        assert "status: offered" in body
        assert "assigned_to: alpha" in body
        assert "tags: [from-relay-alpha]" in body
        assert "# Test queue item" in body


class TestMirror:
    def test_dry_run_writes_nothing(self, tmp_path: Path) -> None:
        relay_dir = tmp_path / "relay"
        vault_root = tmp_path / "vault"
        _write_relay(relay_dir, "alpha", ["task one"])
        counts = mirror(relay_dir=relay_dir, vault_root=vault_root, apply=False)
        assert counts["loaded"] == 1
        assert counts["written"] == 1
        assert not (vault_root / "active").exists()

    def test_apply_writes_files(self, tmp_path: Path) -> None:
        relay_dir = tmp_path / "relay"
        vault_root = tmp_path / "vault"
        _write_relay(relay_dir, "alpha", ["task one", "task two"])
        _write_relay(relay_dir, "delta", ["task three"])
        counts = mirror(relay_dir=relay_dir, vault_root=vault_root, apply=True)
        assert counts["written"] == 3
        active_files = list((vault_root / "active").glob("*.md"))
        assert len(active_files) == 3

    def test_idempotent_skips_existing(self, tmp_path: Path) -> None:
        relay_dir = tmp_path / "relay"
        vault_root = tmp_path / "vault"
        _write_relay(relay_dir, "alpha", ["task one"])
        c1 = mirror(relay_dir=relay_dir, vault_root=vault_root, apply=True)
        assert c1["written"] == 1 and c1["skipped_existing"] == 0
        c2 = mirror(relay_dir=relay_dir, vault_root=vault_root, apply=True)
        assert c2["written"] == 0 and c2["skipped_existing"] == 1

    def test_idempotent_preserves_operator_edits(self, tmp_path: Path) -> None:
        """Operator hand-edits to a mirrored note's body must survive
        re-runs — bridge skips existing notes."""
        relay_dir = tmp_path / "relay"
        vault_root = tmp_path / "vault"
        _write_relay(relay_dir, "alpha", ["task one"])
        mirror(relay_dir=relay_dir, vault_root=vault_root, apply=True)
        # Operator edits the body.
        item = RelayQueueItem(role="alpha", title="task one")
        path = vault_note_path(vault_root, item)
        original = path.read_text()
        edited = original.replace("(operator-author or session-claim", "OPERATOR EDITED HERE")
        path.write_text(edited)
        # Re-run.
        mirror(relay_dir=relay_dir, vault_root=vault_root, apply=True)
        # Edit survived.
        assert "OPERATOR EDITED HERE" in path.read_text()
