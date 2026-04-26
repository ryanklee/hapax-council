"""Shared Prometheus metrics for the refused-lifecycle substrate.

All three watchers (structural / constitutional / conditional) share the
``probes_total`` and ``probe_failures_total`` counters; the ``trigger``
label discriminates them. Centralising the registration here avoids
``CollectorRegistry`` duplicate-timeseries errors when more than one
watcher module is loaded in the same process (e.g., during pytest
collection).
"""

from __future__ import annotations

from prometheus_client import Counter

probes_total = Counter(
    "hapax_refused_lifecycle_probes_total",
    "Refused-lifecycle probes executed (any outcome).",
    ["trigger", "slug"],
)

probe_failures_total = Counter(
    "hapax_refused_lifecycle_probe_failures_total",
    "Refused-lifecycle probe failures by reason.",
    ["trigger", "slug", "reason"],
)


__all__ = ["probe_failures_total", "probes_total"]
