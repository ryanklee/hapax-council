"""Test sensor snapshot publishing to /dev/shm."""

import json


def test_publish_snapshot_writes_atomic_json(tmp_path):
    """Verify publish_snapshot writes atomically via .tmp rename."""
    from agents.dmn.sensor import publish_snapshot

    snapshot = {"stimmung": {"stance": "nominal"}, "perception": {"vad_confidence": 0.8}}
    out = tmp_path / "snapshot.json"
    publish_snapshot(snapshot, path=out)

    assert out.exists()
    data = json.loads(out.read_text())
    assert data["stimmung"]["stance"] == "nominal"
    assert data["perception"]["vad_confidence"] == 0.8
    assert "published_at" in data


def test_publish_snapshot_no_tmp_file_remains(tmp_path):
    """After publish, no .tmp file should exist."""
    from agents.dmn.sensor import publish_snapshot

    snapshot = {"test": True}
    out = tmp_path / "snapshot.json"
    publish_snapshot(snapshot, path=out)

    assert not (tmp_path / "snapshot.json.tmp").exists()
