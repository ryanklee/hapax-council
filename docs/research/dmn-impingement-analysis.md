# DMN Impingement Analysis (Measure 4.1)

**Date:** 2026-03-31
**Sprint:** 0, Day 2
**Gate:** G3 (contradiction rate ≤ 15%)

## Summary

**Gate result: PASS — 0.0% contradiction rate**

716 impingements analyzed. Zero directional contradictions (same metric improving→degrading within 60s). The DMN impingement stream is coherent.

## Data

- **Source:** `/dev/shm/hapax-dmn/impingements.jsonl`
- **Count:** 716 impingements
- **Duration:** Single DMN session (timestamps cluster around one epoch; file resets on DMN restart)

## Distribution by type

| Type | Count | Pct |
|------|-------|-----|
| salience_integration | 427 | 59.6% |
| absolute_threshold | 250 | 34.9% |
| pattern_match | 39 | 5.4% |

## Distribution by source

| Source | Count | Pct |
|--------|-------|-----|
| imagination | 427 | 59.6% |
| dmn.sensor_starvation | 236 | 33.0% |
| sensor.watch | 29 | 4.1% |
| dmn.ollama_degraded | 10 | 1.4% |
| sensor.weather | 7 | 1.0% |
| sensor.git | 2 | 0.3% |
| dmn.resolver | 2 | 0.3% |
| dmn.absolute_threshold | 2 | 0.3% |
| sensor.stimmung | 1 | 0.1% |

## Distribution by metric

92.6% of impingements have no `metric` field in content — these are imagination-sourced salience integrations and sensor starvation thresholds. Only 53 impingements (7.4%) carry structured metric data.

| Metric | Count |
|--------|-------|
| profile_dimension_updated | 39 |
| ollama_degraded | 10 |
| resolver_consecutive_failures | 2 |
| stimmung_critical | 2 |

## Contradiction scan

**Method:** Group impingements by metric. For each adjacent pair within 60s, check for directional reversal (improving↔degrading, rising↔falling).

- Metrics with timeline data: 4
- Adjacent pairs checked: 49
- Contradictions found: 0
- **Rate: 0.0%**

No contradictions detected. The low metric coverage (7.4% of impingements carry trajectory-bearing metrics) means the scan has limited statistical power, but the data that exists is fully consistent.

## Observations

### Rapid-fire signals (noise concern)

Two sources emit impingements faster than 5s apart:

| Source | Rapid-fire pairs | Total | Burst rate |
|--------|-----------------|-------|------------|
| imagination | 159 | 427 | 37.2% |
| dmn.sensor_starvation | 136 | 236 | 57.6% |

`dmn.sensor_starvation` fires on every tick when a sensor is unavailable — this is expected behavior but generates significant volume. The 57.6% burst rate suggests the threshold is too sensitive or the cooldown is too short for missing sensors.

`imagination` fires on every imagination tick with salience > 0. At ~2s cadence, adjacent pairs within 5s are expected. Not a concern.

### Strength distribution

- Mean: 0.520, median: 0.500, stdev: 0.147
- Range: 0.200 – 0.900

The narrow range and low variance suggest most impingements cluster around mid-strength. No outlier spikes or near-zero noise floor — the strength signal carries limited dynamic range.

## Gate decision

**G3: PASS.** Contradiction rate 0.0% (threshold: ≤ 15%). DMN impingement stream is coherent. Proceed with Sprint 0 remaining measures.

## Recommendations

1. **sensor_starvation cooldown:** Consider increasing cooldown or adding dedup — 236 starvation impingements from one source is high volume for a single session.
2. **Metric coverage:** 92.6% of impingements lack structured metric fields. If future measures depend on per-metric trajectory analysis, imagination-sourced impingements should carry a `metric` field.
3. **Strength dynamic range:** The 0.2–0.9 range with 0.147 stdev suggests strength values could be more discriminating. Consider whether the current strength assignment captures meaningful variation.
