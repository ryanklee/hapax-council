"""Consent-labeled /dev/shm trace I/O.

Embeds/extracts ConsentLabel in _consent envelope so labels survive
JSON serialization across process boundaries.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

from shared.governance.consent_label import ConsentLabel


def serialize_label(
    label: ConsentLabel | None, provenance: frozenset[str] = frozenset()
) -> dict | None:
    if label is None:
        return None
    return {
        "label": [
            {"owner": owner, "readers": sorted(readers)}
            for owner, readers in sorted(label.policies)
        ],
        "provenance": sorted(provenance),
        "labeled_at": time.time(),
    }


def deserialize_label(consent_data: dict | None) -> tuple[ConsentLabel, frozenset[str]]:
    if consent_data is None:
        return ConsentLabel.bottom(), frozenset()
    policies: set[tuple[str, frozenset[str]]] = set()
    for entry in consent_data.get("label", []):
        owner = entry.get("owner", "")
        readers = frozenset(entry.get("readers", []))
        if owner:
            policies.add((owner, readers))
    provenance = frozenset(str(x) for x in consent_data.get("provenance", []))
    return ConsentLabel(frozenset(policies)), provenance


def write_labeled_trace(
    path: Path,
    data: dict,
    label: ConsentLabel | None,
    provenance: frozenset[str] = frozenset(),
) -> None:
    """Write JSON trace with embedded consent label. Atomic (tmp + rename)."""
    enriched = {**data, "_consent": serialize_label(label, provenance)}
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(enriched), encoding="utf-8")
    os.replace(str(tmp), str(path))


def read_labeled_trace(path: Path, stale_s: float) -> tuple[dict | None, ConsentLabel | None]:
    """Read JSON trace with staleness check and consent extraction."""
    try:
        age = time.time() - path.stat().st_mtime
        if age > stale_s:
            return None, None
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None, None
    consent_data = raw.pop("_consent", None)
    label, _provenance = deserialize_label(consent_data)
    return raw, label
