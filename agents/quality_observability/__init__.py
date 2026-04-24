"""Content-quality observability exporters.

Computes time-series quality signals from chronicle events that no other
metric layer captures. Hapax has 95+ Prometheus metrics covering
operational health (latency, error rate, GPU memory) but had zero
direct content-quality signals — chronicle (12h rolling JSONL at
``/dev/shm/hapax-chronicle/events.jsonl``) carried all the raw data
(salience, intent_family, material, grounding_provenance) but no
aggregation into time-series.

This package's exporters bridge that gap so v6 Bayesian refresh and the
SS family of self-sufficiency research conditions have measured signals
to tune against.

Spec: ytb-QM1.
"""

from agents.quality_observability.chronicle_exporter import (
    METRICS_PORT,
    ChronicleQualityExporter,
)

__all__ = ["METRICS_PORT", "ChronicleQualityExporter"]
