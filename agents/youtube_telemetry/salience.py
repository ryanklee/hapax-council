"""Deviation → salience mapping for telemetry impingements.

The mapping is a small decision table (cc-task §Design "salience
mapping"), reproduced here as code so test cases pin it. Each row is
(deviation_predicate, salience, kind_label).

``kind_label`` lets the bus consumer differentiate ambient ticks from
spike events without re-running the math; downstream metric labelling
also uses it.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

# Kind taxonomy. ``ambient`` = baseline holds; ``spike`` = traffic
# rose meaningfully; ``drop`` = traffic fell meaningfully;
# ``stale`` = produced when the API call failed and we want to log
# the heartbeat without a real reading.
TelemetryKind = Literal["ambient", "spike", "drop", "stale"]

SPIKE_THRESHOLD: float = 2.0
DROP_THRESHOLD: float = 0.5

AMBIENT_SALIENCE: float = 0.2
SPIKE_SALIENCE: float = 0.7
DROP_SALIENCE: float = 0.5
STALE_SALIENCE: float = 0.0


@dataclass(frozen=True, slots=True)
class SalienceVerdict:
    salience: float
    kind: TelemetryKind


def classify(deviation: float | None) -> SalienceVerdict:
    """Map a deviation ratio (current / baseline) to a salience verdict.

    ``None`` deviation (cold-start / no baseline yet) yields ambient
    salience — the impingement still fires (signals presence on the
    bus) but doesn't compete for recruitment attention.
    """
    if deviation is None:
        return SalienceVerdict(salience=AMBIENT_SALIENCE, kind="ambient")
    if deviation >= SPIKE_THRESHOLD:
        return SalienceVerdict(salience=SPIKE_SALIENCE, kind="spike")
    if deviation <= DROP_THRESHOLD:
        return SalienceVerdict(salience=DROP_SALIENCE, kind="drop")
    return SalienceVerdict(salience=AMBIENT_SALIENCE, kind="ambient")


def stale_verdict() -> SalienceVerdict:
    """Verdict for ticks where the API call failed.

    Logged on the bus with zero salience + ``stale`` kind so the
    operator (and the QM2 sampler) can distinguish "no data point
    arrived" from "data point arrived and was uneventful".
    """
    return SalienceVerdict(salience=STALE_SALIENCE, kind="stale")
