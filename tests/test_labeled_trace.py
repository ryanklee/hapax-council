import json
import os
import time

from shared.governance.consent_label import ConsentLabel


def test_write_read_roundtrip(tmp_path):
    from shared.labeled_trace import read_labeled_trace, write_labeled_trace

    label = ConsentLabel(frozenset({("alice", frozenset({"operator"}))}))
    path = tmp_path / "state.json"
    write_labeled_trace(path, {"value": 42}, label, provenance=frozenset({"c1"}))
    data, recovered = read_labeled_trace(path, stale_s=30.0)
    assert data is not None
    assert data["value"] == 42
    assert "_consent" not in data
    assert recovered is not None
    assert recovered.policies == label.policies


def test_null_label(tmp_path):
    from shared.labeled_trace import read_labeled_trace, write_labeled_trace

    path = tmp_path / "s.json"
    write_labeled_trace(path, {"v": 1}, None)
    data, label = read_labeled_trace(path, stale_s=30.0)
    assert data is not None
    assert label == ConsentLabel.bottom()


def test_legacy_file(tmp_path):
    from shared.labeled_trace import read_labeled_trace

    path = tmp_path / "s.json"
    path.write_text(json.dumps({"v": 1}))
    data, label = read_labeled_trace(path, stale_s=30.0)
    assert data is not None
    assert label == ConsentLabel.bottom()


def test_stale_returns_none(tmp_path):
    from shared.labeled_trace import read_labeled_trace

    path = tmp_path / "s.json"
    path.write_text(json.dumps({"v": 1}))
    os.utime(path, (time.time() - 60, time.time() - 60))
    data, label = read_labeled_trace(path, stale_s=10.0)
    assert data is None
    assert label is None
