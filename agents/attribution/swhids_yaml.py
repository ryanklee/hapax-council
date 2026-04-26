"""SWHID persistence — read/write ``hapax-state/attribution/swhids.yaml``.

Per cc-task ``leverage-attrib-swh-swhid-bibtex``. Phase 2 daemon
collects SWHIDs across HAPAX_REPOS and persists them so downstream
consumers (CITATION.cff sidecar updater, BibTeX puller, refusal-brief
annex) read a single canonical file.

Atomic-write semantics: tempfile in same parent directory + ``os.replace``
(matching the ``shared.threshold_tuner`` pattern). Newest run completely
replaces the prior file; partial-write recovery is unnecessary because
the daemon re-runs each tick.
"""

from __future__ import annotations

import os
import tempfile
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

DEFAULT_SWHIDS_PATH: Path = Path.home() / "hapax-state" / "attribution" / "swhids.yaml"
"""Canonical path for the persisted SWHID record set."""


@dataclass
class SwhidRecord:
    """One repo's SWH archival state.

    Populated by :func:`agents.attribution.swh_archive_daemon.archive_all_repos`
    after one cycle of ``trigger_save → poll_visit → resolve_swhid``.
    Persisted to YAML; consumed by CITATION.cff updater + BibTeX puller.
    """

    slug: str
    repo_url: str
    swhid: str | None = None
    visit_status: str | None = None
    request_id: int | None = None
    last_attempted: datetime | None = None
    error: str | None = None

    def to_yaml_dict(self) -> dict[str, Any]:
        d = asdict(self)
        if self.last_attempted is not None:
            d["last_attempted"] = self.last_attempted.isoformat()
        return d

    @classmethod
    def from_yaml_dict(cls, data: dict[str, Any]) -> SwhidRecord:
        last = data.get("last_attempted")
        if isinstance(last, str):
            last = datetime.fromisoformat(last)
        return cls(
            slug=data["slug"],
            repo_url=data["repo_url"],
            swhid=data.get("swhid"),
            visit_status=data.get("visit_status"),
            request_id=data.get("request_id"),
            last_attempted=last,
            error=data.get("error"),
        )


@dataclass
class SwhidsFile:
    """Top-level YAML envelope written to swhids.yaml."""

    updated: datetime | None = None
    records: dict[str, SwhidRecord] = field(default_factory=dict)


def load_swhids(*, path: Path = DEFAULT_SWHIDS_PATH) -> dict[str, SwhidRecord]:
    """Read swhids.yaml; return ``{slug: SwhidRecord}`` (empty when absent)."""
    if not path.exists():
        return {}
    raw = yaml.safe_load(path.read_text()) or {}
    records_raw = raw.get("records", {}) if isinstance(raw, dict) else {}
    if not isinstance(records_raw, dict):
        return {}
    return {slug: SwhidRecord.from_yaml_dict(rec) for slug, rec in records_raw.items()}


def save_swhids(
    records: dict[str, SwhidRecord],
    *,
    path: Path = DEFAULT_SWHIDS_PATH,
    now: datetime | None = None,
) -> None:
    """Atomically write ``records`` to ``path``.

    Replaces any pre-existing file. Parent directories are created if
    missing. Tempfile + ``os.replace`` guarantees the file at ``path``
    is either the prior content or fully-written new content — never
    a half-written file mid-flight.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    payload: dict[str, Any] = {
        "updated": (now or datetime.now(UTC)).isoformat(),
        "records": {slug: rec.to_yaml_dict() for slug, rec in records.items()},
    }
    fd, tmp = tempfile.mkstemp(prefix=".swhids-", suffix=".yaml", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            yaml.safe_dump(payload, fh, sort_keys=False, default_flow_style=False)
        os.replace(tmp, path)
    except Exception:
        Path(tmp).unlink(missing_ok=True)
        raise


__all__ = [
    "DEFAULT_SWHIDS_PATH",
    "SwhidRecord",
    "SwhidsFile",
    "load_swhids",
    "save_swhids",
]
