"""Rolling-median baseline for deviation-from-baseline scoring.

A streaming median is more robust than mean for spiky time-series
signals (concurrent viewers, engagement rate) where a single hour of
high traffic shouldn't pull the next 23 hours of baselines off the
true level.

Implementation: bounded deque + sort-on-query. The cap is small
(≤ ~480 samples for 24h at 3-min cadence) so the per-tick sort is
microseconds. No need for a P² estimator or t-digest.
"""

from __future__ import annotations

import statistics
from collections import deque
from collections.abc import Iterable


class RollingMedianBaseline:
    """24-hour-cap rolling-median baseline.

    Default ``cap`` is 480 samples — exactly 24h at the documented
    3-min polling cadence. ``record`` adds a sample (oldest evicted
    once the cap is reached). ``median`` returns ``None`` until
    ``min_samples`` have accumulated, so cold-start callers see "no
    baseline yet" instead of misleading early values.
    """

    def __init__(self, *, cap: int = 480, min_samples: int = 5) -> None:
        if cap < 1:
            raise ValueError("cap must be positive")
        if min_samples < 1:
            raise ValueError("min_samples must be positive")
        self._buf: deque[float] = deque(maxlen=cap)
        self._min_samples = min_samples

    def record(self, value: float) -> None:
        if value < 0:
            return  # ignore impossible negative readings
        self._buf.append(float(value))

    def extend(self, values: Iterable[float]) -> None:
        for v in values:
            self.record(v)

    def median(self) -> float | None:
        if len(self._buf) < self._min_samples:
            return None
        return statistics.median(self._buf)

    def deviation(self, current: float) -> float | None:
        """Multiplicative deviation: ``current / median``.

        Returns ``None`` when the baseline is not yet established or
        when the median is zero (no signal to deviate from).
        ``current >= 0`` is a precondition; negative inputs return
        None so the salience mapping never sees a nonsensical value.
        """
        med = self.median()
        if med is None or med <= 0 or current < 0:
            return None
        return current / med

    def __len__(self) -> int:
        return len(self._buf)
