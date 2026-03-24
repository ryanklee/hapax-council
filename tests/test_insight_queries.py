"""Tests for logos/data/insight_queries.py — JSONL persistence and task lifecycle."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest

from logos.data import insight_queries
from logos.data.insight_queries import (
    delete,
    get,
    load_all,
    recover_stale,
    start,
    update,
)


@pytest.fixture(autouse=True)
def _clean_state(tmp_path, monkeypatch):
    """Redirect JSONL to a temp dir and clear active tasks."""
    test_path = tmp_path / "insight-queries.jsonl"
    monkeypatch.setattr(insight_queries, "_QUERIES_PATH", test_path)
    insight_queries._active.clear()
    yield
    insight_queries._active.clear()


def _write_record(tmp_path, **overrides):
    """Write a record directly to the JSONL file."""
    path = tmp_path / "insight-queries.jsonl"
    rec = {
        "id": "iq-test0001",
        "query": "test query",
        "status": "done",
        "agent_type": "dev_story",
        "markdown": "# Result",
        "created_at": "2026-03-24T00:00:00+00:00",
        "completed_at": "2026-03-24T00:00:30+00:00",
        "elapsed_ms": 30000,
        "tokens_in": 500,
        "tokens_out": 1000,
        "error": None,
        "parent_id": None,
    }
    rec.update(overrides)
    with open(path, "a") as f:
        f.write(json.dumps(rec) + "\n")
    return rec


class TestLoadAll:
    def test_empty_file(self):
        assert load_all() == []

    def test_reads_records(self, tmp_path):
        _write_record(tmp_path, id="iq-aaa")
        _write_record(tmp_path, id="iq-bbb")
        records = load_all()
        assert len(records) == 2
        assert records[0]["id"] == "iq-aaa"
        assert records[1]["id"] == "iq-bbb"

    def test_skips_bad_json(self, tmp_path):
        path = tmp_path / "insight-queries.jsonl"
        path.write_text('{"id":"iq-good","status":"done"}\nnot json\n')
        records = load_all()
        assert len(records) == 1


class TestGet:
    def test_found(self, tmp_path):
        _write_record(tmp_path, id="iq-find")
        assert get("iq-find") is not None
        assert get("iq-find")["id"] == "iq-find"

    def test_not_found(self, tmp_path):
        _write_record(tmp_path, id="iq-other")
        assert get("iq-missing") is None


class TestUpdate:
    def test_updates_field(self, tmp_path):
        _write_record(tmp_path, id="iq-upd", status="running")
        update("iq-upd", {"status": "done", "markdown": "# Done"})
        rec = get("iq-upd")
        assert rec["status"] == "done"
        assert rec["markdown"] == "# Done"

    def test_no_op_for_missing(self, tmp_path):
        _write_record(tmp_path, id="iq-exists")
        update("iq-ghost", {"status": "error"})
        # Should not crash, original record unchanged
        assert get("iq-exists")["status"] == "done"


class TestDelete:
    def test_deletes_record(self, tmp_path):
        _write_record(tmp_path, id="iq-del")
        assert delete("iq-del") is True
        assert get("iq-del") is None

    def test_returns_false_for_missing(self):
        assert delete("iq-nope") is False


class TestRecoverStale:
    def test_patches_running_to_error(self, tmp_path):
        _write_record(tmp_path, id="iq-stale", status="running")
        _write_record(tmp_path, id="iq-ok", status="done")
        recover_stale()
        stale = get("iq-stale")
        assert stale["status"] == "error"
        assert "restarted" in stale["error"].lower()
        assert get("iq-ok")["status"] == "done"


class TestStart:
    @pytest.mark.asyncio
    async def test_creates_record_and_task(self, tmp_path):
        with patch.object(insight_queries, "_run_task", new_callable=AsyncMock):
            rec = start("what happened yesterday?")
            assert rec["id"].startswith("iq-")
            assert rec["status"] == "running"
            assert rec["query"] == "what happened yesterday?"
            persisted = get(rec["id"])
            assert persisted is not None
            assert persisted["status"] == "running"


class TestRotation:
    def test_rotates_at_limit(self, tmp_path, monkeypatch):
        from logos.data.insight_queries import _append

        monkeypatch.setattr(insight_queries, "_MAX_ENTRIES", 5)
        for i in range(8):
            _append({"id": f"iq-{i:04d}", "status": "done", "query": f"q{i}"})
        records = load_all()
        assert len(records) == 5
        assert records[0]["id"] == "iq-0003"
        assert records[-1]["id"] == "iq-0007"
