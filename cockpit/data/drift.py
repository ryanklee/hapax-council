"""Drift report data collector."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime

from shared.config import PROFILES_DIR


@dataclass
class DriftItem:
    severity: str = ""
    category: str = ""
    doc_file: str = ""
    description: str = ""
    suggestion: str = ""
    remediability: str = "review_required"
    confidence: float = 1.0
    source: str = "llm"


@dataclass
class DriftSummary:
    drift_count: int = 0
    docs_analyzed: int = 0
    summary: str = ""
    latest_timestamp: str = ""
    items: list[DriftItem] = field(default_factory=list)
    report_age_h: float = 0.0
    fix_success_rate: float | None = None
    auto_fixed_count: int = 0
    fixes_verified: int = 0


def collect_drift() -> DriftSummary | None:
    """Read profiles/drift-report.json."""
    report_path = PROFILES_DIR / "drift-report.json"
    history_path = PROFILES_DIR / "drift-history.jsonl"

    if not report_path.exists():
        return None

    try:
        data = json.loads(report_path.read_text())
    except (json.JSONDecodeError, OSError):
        return None

    # Get timestamp from history if available
    timestamp = ""
    if history_path.exists():
        for line in reversed(history_path.read_text().splitlines()):
            line = line.strip()
            if line:
                try:
                    timestamp = json.loads(line).get("timestamp", "")
                except (json.JSONDecodeError, KeyError):
                    pass
                break

    # Parse drift items
    items = []
    for raw in data.get("drift_items", []):
        # Agent model uses doc_claim/reality; build description from them
        doc_claim = raw.get("doc_claim", "")
        reality = raw.get("reality", "")
        description = raw.get("description", "") or (
            f"{doc_claim} → {reality}" if doc_claim and reality else doc_claim or reality
        )
        items.append(
            DriftItem(
                severity=raw.get("severity", ""),
                category=raw.get("category", ""),
                doc_file=raw.get("doc_file", ""),
                description=description,
                suggestion=raw.get("suggestion", ""),
                remediability=raw.get("remediability", "review_required"),
                confidence=float(raw.get("confidence", 1.0)),
                source=raw.get("source", "llm"),
            )
        )

    # Load remediation metrics if available
    fix_success_rate = None
    auto_fixed_count = 0
    fixes_verified = 0
    metrics_path = PROFILES_DIR / "drift-metrics.json"
    if metrics_path.exists():
        try:
            mdata = json.loads(metrics_path.read_text())
            fix_success_rate = mdata.get("fix_success_rate")
            auto_fixed_count = mdata.get("total_applied_30d", 0)
            fixes_verified = mdata.get("persisted_true_30d", 0)
        except (json.JSONDecodeError, OSError):
            pass

    # Compute report age
    report_age_h = 0.0
    if timestamp:
        try:
            ts = datetime.fromisoformat(timestamp)
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=UTC)
            report_age_h = (datetime.now(UTC) - ts).total_seconds() / 3600
        except (ValueError, TypeError):
            pass

    return DriftSummary(
        drift_count=len(items),
        docs_analyzed=len(data.get("docs_analyzed", [])),
        summary=data.get("summary", ""),
        latest_timestamp=timestamp,
        items=items,
        report_age_h=round(report_age_h, 1),
        fix_success_rate=fix_success_rate,
        auto_fixed_count=auto_fixed_count,
        fixes_verified=fixes_verified,
    )
