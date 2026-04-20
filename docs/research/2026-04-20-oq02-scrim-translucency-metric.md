# OQ-02 — Scrim Translucency Metric Selection and Prototype

**Status:** Research / metric selection. Phase 1 input for the Nebulous Scrim three-bound invariants epic.
**Owner:** alpha
**Cross-link:** `docs/research/2026-04-20-nebulous-scrim-three-bound-invariants-triage.md` §4 Phase 1 (Bound 2 candidates), §5 Phase 5 (runtime check), §6 (D-25 / OQ-01 brightness-ceiling pattern).
**Anchors:** `docs/research/2026-04-20-nebulous-scrim-design.md` §7 invariant 2 ("Studio remains readable"), §9.2 (non-negotiable: legibility at 1080p TV / mobile phone).
**Scope:** Picks one of three candidate metrics for invariant B2 (scrim-translucency / anti-opacity). Sketches threshold derivation, module skeleton, acceptance fixtures, runtime cost, integration with `agents/studio_compositor/budget_signal.py`, and failure modes. No implementation.

---

## 1. Metric choice and rationale

### 1.1 Decision

**Metric (b): structural-content score — edge-density preservation + multi-scale luminance variance + color-channel entropy floor.**

A composite scalar in `[0.0, 1.0]` aggregating three sub-metrics computed against the post-effect egress frame *only* (no reference frame required at runtime; reference statistics are baked at calibration time):

- `edge_density_ratio` — Sobel/Scharr edge fraction of the egress frame divided by a calibrated reference edge fraction expected from a "studio with people and gear" scene.
- `luminance_variance_score` — variance of luminance within each cell of a 4×4 / 8×8 grid, then minimum across cells. Captures the property "no large pure-color blob anywhere."
- `entropy_floor_score` — Shannon entropy of each color channel histogram (RGB, 64-bin), minimum across channels. Captures the property "no channel collapsed to a single value."

The aggregate is the minimum of the three (worst-of), not the mean — bound 2 is a conjunctive guarantee, and a min-aggregator means a single failing sub-metric trips the bound.

### 1.2 Why (b) over (a) SSIM/MS-SSIM

SSIM/MS-SSIM is the textbook answer and was the operator's first listed candidate (triage §4 Phase 1). It is rejected for three reasons:

1. **No reference frame at runtime.** SSIM is fundamentally a *reference-vs-distorted* metric. Bound 2 fires on the live egress frame; the "ground truth" is the pre-effect composite, which is *not retained* downstream of the effect graph in the current pipeline (`agents/studio_compositor/compositor.py`). Retaining a parallel pre-effect render path solely to compute SSIM doubles GPU cost on the exact code path the operator has just spent ~1.5ms of budget on. Triage §4 Phase 1 explicitly demands "cheap enough for runtime per-frame check"; SSIM with a parallel reference render is not cheap.
2. **SSIM is not discriminating on the bound-2 failure modes.** The triage §3 enumeration of B2 failures includes "high scrim density + heavy bloom + max colorgrade.brightness saturate to white" (D-25) and "material→color material_id swing converts scene to single-hue field." A pure-white frame and a moderately scrim'd frame can both have high SSIM against each other if the SSIM window size is wrong, because SSIM is dominated by local-luminance/structure correlation and is *insensitive to the global collapse to a constant*. SSIM's failure mode on this exact problem class is documented in the IQA literature (Wang & Bovik 2009; Chen et al. 2020 on "structural collapse"). A pure-white field has structural similarity 1.0 with itself.
3. **MS-SSIM doesn't fix it cheaply.** MS-SSIM helps with multi-scale collapse but at ~3–5× the cost of single-scale SSIM, putting it well outside the 1ms-per-frame envelope budget §9.6 of the design doc.

### 1.3 Why (b) over (c) learned classifier

A binary classifier ("studio-with-people" vs "abstract-pattern/opaque-surface") has the right output shape but is rejected because:

1. **Training-set bootstrap problem.** There is no labeled corpus of pre/post-scrim frames at the operator's actual studio. Building one requires either capturing a representative set live (which requires the metric we are trying to ship in order to recognize the failure modes) or hand-labeling frames (unbounded operator time).
2. **Adversarial fragility.** A learned classifier can pass a smoke test on rare failure modes while being trivially defeated by a new effect chain that produces a frame statistically inside the training distribution but perceptually opaque. The triage §3 risk surface for B2 is *open-ended* — every new effect, every new chain, every new audio profile expands it. A composite of first-principles statistics generalizes; a classifier overfits.
3. **Cost.** Even a tiny CNN (e.g. MobileNetV3-small at 224×224) costs 2–4ms on the council's GPU under contention with TabbyAPI and Reverie. Falls outside the runtime budget.
4. **Opacity as a debugging surface.** When the metric fails, the operator and Hapax both need to know *why*. A classifier returns a single scalar; the structural-content score returns three named sub-scores, each with a clear physical interpretation ("edges collapsed", "luminance collapsed in cell (2,3)", "blue channel histogram collapsed"). This matches the project's "show your work" telemetry posture (cf. `shared/telemetry.py` `hapax_score` instrumentation pattern).

### 1.4 Why this composite specifically

Each sub-metric kills one specific B2 failure mode that the others would miss:

| Sub-metric | Catches | Misses (handled by other sub-metric) |
|---|---|---|
| `edge_density_ratio` | "noise-only" frame collapses to static (no real edges); pure single-hue field (no edges); over-blurred everything | high-frequency noise patterns that have edges but no semantic content |
| `luminance_variance_score` (per-cell min) | brightness-saturation-to-white in any region; black crush in any region; large constant blobs anywhere | uniform mid-grey field with high noise; busy abstract patterns |
| `entropy_floor_score` (per-channel min) | single-channel collapse (blue → 0, etc.); palette-rotate to single hue; full saturation to one color | structured patterns whose individual channels happen to remain entropic |

The min-of-three aggregator is the conjunctive guarantee. This is the same pattern as the existing `agents/studio_compositor/budget.py:223` `over_budget` check: a single threshold violation trips the signal, and recovery requires *all three* sub-scores to clear the threshold simultaneously.

---

## 2. Threshold derivation methodology

### 2.1 Calibration corpus

Three frame populations, captured offline during a one-time calibration pass:

- **POSITIVE — "legitimate scrim density passes"**: ~600 frames captured live during a representative R&D session with the scrim active at every supported `scrim_profile` (per `nebulous-scrim-design.md` §13 — gauzy_quiet, warm_haze, moire_crackle, clarity_peak, dissolving, ritual_open, rain_streak), under three audio profiles (silence, music, voice), with the operator visibly present in the scene.
- **NEGATIVE-OPAQUE — "opaque-saturation fails"**: synthetic and captured failure exemplars: pure white (RGB 255,255,255), pure black (0,0,0), single-hue magenta, single-hue cyan, the actual D-25 / OQ-01 white-edge-neon failure frame (preserved in `tests/effect_graph/test_neon_palette_cycle.py`), brightness-saturated overshoot of every shipped preset.
- **NEGATIVE-NOISE — "abstract-pattern fails"**: pure Perlin noise, pure RGB noise, the worst-trail/worst-decay configurations of `feedback`/`drift`/`rd` nodes when the camera signal has been swamped (per triage §3 B2 risk surface).

### 2.2 Thresholds

For each sub-metric, compute the empirical distribution over each of the three populations. The threshold is derived by:

1. Compute the 5th-percentile value over POSITIVE.
2. Compute the 95th-percentile value over NEGATIVE-OPAQUE ∪ NEGATIVE-NOISE.
3. If positive-5th > negative-95th, the sub-metric is *separating* — set threshold at the midpoint and record the separation margin.
4. If positive-5th ≤ negative-95th, the sub-metric is *overlapping* — record the overlap, and do not ship that sub-metric until the overlap is investigated (likely indicates a positive frame that is actually borderline B2-violating, or a sub-metric tuning issue).

This is the same calibration protocol used by `shared/governance/classifier_degradation.py` for its degradation thresholds and matches the broader council pattern of empirical-distribution-based threshold setting (see `agents/hapax_daimonion/presence_engine.py` likelihood ratios).

The calibration is recorded in a JSON file at `axioms/scrim/scrim_translucency_thresholds.json` with schema:

```json
{
  "schema_version": 1,
  "calibrated_at": "2026-04-2X",
  "calibration_corpus_size": {"positive": 600, "negative_opaque": 40, "negative_noise": 60},
  "edge_density_ratio": {"threshold": 0.42, "positive_p05": 0.48, "negative_p95": 0.31, "margin": 0.17},
  "luminance_variance_score": {"threshold": 0.18, ...},
  "entropy_floor_score": {"threshold": 0.55, ...}
}
```

This file is operator-visible, version-controlled, and re-derivable by re-running the calibration script. Re-calibration is required when a new scrim profile ships or when the camera/lighting setup materially changes.

### 2.3 Ratchet semantics

The threshold should be *biased toward letting current legitimate frames pass* and ratchet downward only when (a) a B2 violation is observed in the wild and (b) the calibration is rerun and finds the threshold can be raised without taking out legitimate positives. This avoids the failure mode where a tightening threshold quietly suppresses every interesting effect to the lowest common denominator. Same pattern as the brightness-ceiling fix shipped for D-25 (triage §6).

---

## 3. Prototype Python module sketch

Path: `shared/governance/scrim_invariants/scrim_translucency.py`

```python
"""Scrim-translucency runtime invariant (Bound 2 of the Nebulous Scrim).

Computes a structural-content score over the live egress frame, returning a
scalar in [0.0, 1.0] plus per-component breakdown for telemetry. A score
below the calibrated threshold indicates the scrim has lost its translucent
character — the frame has collapsed toward pure color, pure noise, or
single-channel saturation, violating the design's §7 invariant 2 promise that
"the audience can always tell what's happening."

See: docs/research/2026-04-20-oq02-scrim-translucency-metric.md
See: docs/research/2026-04-20-nebulous-scrim-three-bound-invariants-triage.md §4 Phase 1
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Final

import numpy as np


SCHEMA_VERSION: Final[int] = 1
DEFAULT_THRESHOLDS_PATH: Final[Path] = Path(
    "axioms/scrim/scrim_translucency_thresholds.json"
)


@dataclass(frozen=True)
class TranslucencyThresholds:
    """Calibrated cutoff values per sub-metric. Loaded from JSON at startup."""

    edge_density_min: float
    luminance_variance_min: float
    entropy_floor_min: float
    schema_version: int = SCHEMA_VERSION

    @classmethod
    def load(cls, path: Path = DEFAULT_THRESHOLDS_PATH) -> "TranslucencyThresholds":
        """Load and validate calibration thresholds from disk."""
        ...


@dataclass(frozen=True)
class TranslucencyScore:
    """Decomposed B2 score. The aggregate is min(...) of the three components."""

    edge_density_ratio: float
    luminance_variance_score: float
    entropy_floor_score: float
    aggregate: float
    passed: bool

    @property
    def failing_component(self) -> str | None:
        """Name of the lowest-scoring component when ``passed`` is False, else None."""
        ...


def compute_edge_density_ratio(
    frame: np.ndarray,
    reference_density: float,
) -> float:
    """Sobel edge fraction divided by calibrated reference. Clipped to [0, 1].

    A pure-color frame yields 0.0 (no edges); a noise-saturated frame yields
    a value above 1.0 (clipped). The "studio with gear" reference density
    sits near 1.0 by construction.
    """
    ...


def compute_luminance_variance_score(
    frame: np.ndarray,
    grid: tuple[int, int] = (4, 4),
) -> float:
    """Per-cell luminance variance, normalized, then *minimum* across cells.

    Returns the variance of the worst (lowest-variance) grid cell. This
    fails when any region has collapsed to a flat tone — bright saturation
    in the corner, dark crush in the middle, etc.
    """
    ...


def compute_entropy_floor_score(
    frame: np.ndarray,
    bins: int = 64,
) -> float:
    """Shannon entropy of each RGB channel histogram, normalized, then min.

    A frame whose blue channel has collapsed to a single value yields
    entropy_blue ≈ 0 → score ≈ 0, regardless of how busy R and G are.
    """
    ...


def evaluate(
    frame: np.ndarray,
    thresholds: TranslucencyThresholds,
    *,
    reference_edge_density: float,
) -> TranslucencyScore:
    """Score a single egress frame against the calibrated thresholds.

    The aggregate is the minimum of the three sub-scores (conjunctive
    guarantee). ``passed`` is True iff every sub-score clears its
    threshold; one sub-failure trips the whole bound.

    Cost target: < 0.5 ms on a 1280×720 RGB uint8 ndarray, single-threaded
    on the host CPU. See § 5 of the research doc for the cost analysis.
    """
    ...
```

This module is intentionally **stateless and pure**. The runtime check (§6) wraps it with rolling-window state. Statelessness means the same frame always scores the same value, which makes the metric trivially testable and eliminates a class of "why did the threshold trip" debugging questions.

---

## 4. Acceptance test sketch

Path: `tests/governance/scrim_invariants/test_scrim_translucency.py`

Fixtures (synthesized in-test, no external test data):

| Fixture | Construction | Expected pass |
|---|---|---|
| `clean_studio_scene` | Captured 1280×720 frame from the operator's actual studio (committed binary fixture, ~200KB) | PASS |
| `opaque_white` | `np.full((720, 1280, 3), 255, dtype=np.uint8)` | FAIL on `luminance_variance_score` and `entropy_floor_score` |
| `opaque_black` | `np.zeros((720, 1280, 3), dtype=np.uint8)` | FAIL on `luminance_variance_score` and `entropy_floor_score` |
| `single_hue_magenta` | `np.full((720, 1280, 3), [255, 0, 255], dtype=np.uint8)` | FAIL on all three (no edges, no variance, channel collapse on G) |
| `pure_perlin_noise` | Perlin/value noise at multiple scales | FAIL on `edge_density_ratio` (edges everywhere, ratio >> 1.0; clipped) — see §7 below for the noise-passing failure mode |
| `all_trail` | Captured worst-case `feedback` node decay frame | FAIL on `entropy_floor_score` (palette compresses) |
| `single_hue_field_with_grain` | magenta + 5% gaussian noise | borderline; documents the threshold's exact behavior on near-failure inputs |
| `D-25 white-edge neon (preserved frame)` | captured before the brightness-ceiling fix shipped 2026-04-20 | FAIL — this is the in-the-wild B2 violation that motivated the metric |
| `D-25 fixed neon` | captured after the brightness-ceiling fix | PASS |

Assertions:

- `evaluate(clean_studio_scene, thresholds, ...).passed is True`
- `evaluate(opaque_white, thresholds, ...).passed is False`
- `evaluate(opaque_white, thresholds, ...).failing_component in {"luminance_variance_score", "entropy_floor_score"}`
- For every failure fixture: `score.aggregate < min(threshold)` (i.e. the *worst* sub-score is below threshold).
- Determinism: `evaluate(frame, ...) == evaluate(frame, ...)` for all fixtures (pure function, no RNG).
- `compute_*` functions individually return values in `[0.0, 1.0]` (post-clip) for every fixture.
- A property test (Hypothesis, per workspace convention): for any random uint8 frame `evaluate()` returns a `TranslucencyScore` whose `aggregate == min(edge_density_ratio, luminance_variance_score, entropy_floor_score)`.

The `D-25 white-edge neon` fixture is the most important. It anchors the metric to the one *real-world* B2 violation we have, per triage §6. If a future calibration breaks this assertion, the calibration is broken — not the assertion.

---

## 5. Runtime cost analysis

Target frame: 1280×720 RGB uint8 ndarray. Target budget: < 1.0 ms per frame at 30 fps egress (compositor's existing budget envelope per `nebulous-scrim-design.md` §9.6).

Per-component CPU cost estimates (single-threaded on the operator's Ryzen):

| Component | Operation | Estimated cost |
|---|---|---|
| `edge_density_ratio` | Sobel via `scipy.ndimage.sobel` on luminance channel + threshold + mean | 0.20–0.30 ms |
| `luminance_variance_score` | RGB→Y conversion, `numpy.var` over 16 grid cells, min | 0.10–0.15 ms |
| `entropy_floor_score` | 3× `numpy.histogram` (64 bins) + entropy, min | 0.15–0.20 ms |
| Aggregation + dataclass construction | trivial | < 0.01 ms |
| **Total** | | **0.45–0.65 ms** |

At 30 fps this is ~2% of the 33ms frame budget on a single core. Comfortably inside `nebulous-scrim-design.md` §9.6's 1.5ms ceiling. If empirical measurement comes in higher, three optimizations are available:

1. Downsample to 640×360 before scoring. The metric is statistical, not perceptual; halving each axis quarters the cost with negligible discriminative loss.
2. Compute on every Nth frame (N=2 or N=3) and hold the previous score between updates. Bound 2 violations are sustained, not single-frame; the runtime check (§6) already requires K consecutive failing frames.
3. Move to a background thread and consume the score asynchronously. Pattern matches `CairoSourceRunner` (`agents/studio_compositor/cairo_source.py`) — render thread reads cached score, scoring thread updates it.

No GPU work. The metric runs CPU-side after frame egress, off the Reverie/effect-graph hot path. Cost analysis assumes scipy and numpy are already loaded (they are — both are workspace-wide dependencies).

---

## 6. Integration with `agents/studio_compositor/budget_signal.py` degraded-signal pattern

Triage §4 Phase 5 specifies the integration shape:

> per-frame scene-legibility on egress; if below threshold for >K consecutive frames, force scrim density toward minimum and emit degraded signal.

The integration mirrors `agents/studio_compositor/budget.py:118` `BudgetTracker` + `agents/studio_compositor/budget_signal.py:99` `build_degraded_signal` exactly. Three pieces:

### 6.1 Rolling-window tracker

A new `ScrimTranslucencyTracker` class in `shared/governance/scrim_invariants/scrim_translucency_tracker.py`, threaded identically to `BudgetTracker`:

- `record(frame, thresholds, reference_density)` — call `evaluate()`, append the score to a `deque(maxlen=window_size)`, return the score.
- `consecutive_failures()` — count of the trailing failing frames in the window.
- `over_threshold()` — `consecutive_failures() >= K` where K defaults to 30 (~1s at 30fps); same per-frame-then-sustained pattern as `BudgetTracker.over_budget` (`budget.py:223`).
- `snapshot()` — returns a frozen `ScrimTranslucencySnapshot` for serialization.

The `K=30` consecutive-frame floor means a single frame's worth of bad scoring (transient blip during a transition) does NOT trip the bound. Bound 2 violations in production are sustained — see the D-25 brightness-ceiling: the white edges stayed white for the duration of the neon preset. The K-floor matches the operator's expectation that the bound is a "stays this way for a noticeable beat" test, not a "single frame went wrong" test.

### 6.2 Signal publisher

A new `publish_scrim_signal()` function at `shared/governance/scrim_invariants/scrim_translucency_signal.py`, mirroring `budget_signal.publish_degraded_signal`:

- Writes a JSON document atomically (via `agents.studio_compositor.atomic_io.atomic_write_json`) to `/dev/shm/hapax-compositor/scrim_translucency.json`.
- Schema:

  ```json
  {
    "schema_version": 1,
    "timestamp_ms": 12345.678,
    "wall_clock": 1728000000.123,
    "current": {"edge_density_ratio": 0.31, "luminance_variance_score": 0.06, "entropy_floor_score": 0.42, "aggregate": 0.06, "passed": false},
    "consecutive_failures": 47,
    "over_threshold": true,
    "failing_component": "luminance_variance_score"
  }
  ```

- Wraps with a `FreshnessGauge` ("compositor_scrim_translucency", expected_cadence_s=1.0) registered to the same `_COMPOSITOR_METRICS_REGISTRY` as `_PUBLISH_DEGRADED_FRESHNESS` (per `budget_signal.py:86`). Same dead-path-becomes-loud pattern.

### 6.3 Effect graph response

When `over_threshold == true`, the structural director (per `nebulous-scrim-design.md` §11 Phase 5) drops the scrim profile to the minimum-density operating point (`gauzy_quiet` if not already there; clarity_peak if available) by writing to the scrim parameter envelope. This mirrors the existing `agents/studio_compositor/chat_reactor.py` `PresetReactor` pattern: a deterministic mapping from a signal to a `graph-mutation.json` write with a cooldown.

The response is *graceful degradation*, not an emergency cut. The scrim doesn't disappear — it thins until the metric clears. Once `consecutive_failures` drops to zero and the score has been passing for the recovery window (recommend 30s), the structural director is permitted to raise scrim density again. Recovery hysteresis matches the `presence_engine.py` PRESENT/UNCERTAIN/AWAY hysteresis pattern.

The VLA-side subscriber (analogous to the planned but not-yet-shipped degraded-signal subscriber called out in `budget_signal.py:14`) maps the signal into a stimmung dimension `scrim_translucency_pressure` — the signal becomes legible to Hapax cognition, not just an automated mitigation. Hapax can then *speak to* a sustained over-threshold condition ("the scrim got too thick, easing back"), which respects the `feedback_show_dont_tell_director` memory (no narrating director moves) by speaking to the *condition*, not the *action*.

---

## 7. Failure modes

Every metric has dragons. Documenting them up front so the calibration and integration know what they're guarding against.

**False positives (legitimate scrim flagged):**

- *Intentional minimalism.* `clarity_peak` profile + research-mode framing + minimal cameras may produce a frame whose edge_density_ratio dips below threshold simply because the scene is genuinely sparse. Mitigation: calibrate POSITIVE corpus to include `clarity_peak` frames.
- *Operator-step-out moments.* If the operator steps out of frame, the scene loses its "person at desk" structural content. Mitigation: B2 cares about the *studio*, not the person — the room itself, the gear, the captions ward all retain edges and entropy. A scene with no operator should still pass if the rest of the studio is visible.
- *Heavy-bloom intentional moments.* Ritual openings and `scrim.pierce` moments deliberately blow out a small region. Mitigation: `luminance_variance_score` uses a per-cell *minimum* — a single cell of bloom doesn't trip it. If multiple cells trip, the bloom is spreading too far and the metric correctly fires.

**False negatives (B2-violating scrim passes):**

- *Structured noise that happens to be statistically rich.* Pure perlin noise has edges, variance, and entropy in every channel. The metric will pass it. The triage §3 risk surface specifically calls this out as a B2 failure ("temporal-feedback at extreme decay produces trail-only abstraction"). Mitigation: this is exactly why bound 1 (anti-recognition) and bound 3 (anti-visualizer) exist as separate invariants. B2 alone *cannot* catch every "studio dissolved" failure; the three bounds together cover the space. A future v2 of this metric could add a low-level texture-statistic comparison against the camera's pre-effect frame, but that reintroduces the reference-frame requirement that motivated rejecting (a) — a cost trade-off to revisit if v1 leaks too many noise-passing frames.
- *Slow drift below threshold.* A chain that gradually pushes the scene toward opacity over 30+ seconds may stay just above threshold the whole way. Mitigation: long-running averages of `aggregate` published in the signal payload give the structural director and Hapax visibility into trend direction, not just instantaneous state. Future enhancement: a `trend_pressure` field tracking the slope of `aggregate` over the rolling window.
- *Calibration drift.* The operator's lighting and camera setup will change. The thresholds calibrated today will not apply unmodified in three months. Mitigation: the calibration JSON is a versioned artifact; re-calibration is a documented operator workflow (script `scripts/recalibrate-scrim-thresholds.sh`), and the freshness of the calibration is itself surfaced in the signal payload (`calibrated_at` field).

**Operational failure modes:**

- *Module crashes mid-frame.* If `evaluate()` raises (e.g. unexpected frame shape from a misconfigured pipeline), the publisher must fail-OPEN (not block egress) and emit a `FreshnessGauge.mark_failed()` so the dead path is loud. Same pattern as `budget_signal.py:163`. The scrim continues to render; the bound is unenforced for that frame; the operator is alerted via the gauge.
- *Threshold file missing or stale.* `TranslucencyThresholds.load()` raises a clear error pointing at the calibration script. The runtime check refuses to start without a current threshold file — fail-CLOSED on configuration, fail-OPEN on per-frame errors. Same posture as `shared/governance/consent.py` consent contract loading.
- *Reference edge density drift.* The `reference_edge_density` parameter is a single calibrated scalar. If it's stale (operator added new gear, changed camera angle), the `edge_density_ratio` will bias systematically. Mitigation: re-derive at calibration time; the freshness gauge surfaces the staleness; the metric's three sub-scores let the operator see *which* sub-score is biased.

---

## 8. Acceptance for this metric selection

The OQ-02 metric-pick task is complete when:

- (a) Metric (b) is committed as the B2 metric with rationale in this document.
- (b) Module skeleton path `shared/governance/scrim_invariants/scrim_translucency.py` is named, with function signatures and docstrings.
- (c) Threshold derivation methodology is recorded with calibration corpus design, JSON schema, and ratchet semantics.
- (d) Acceptance test fixtures and assertions are enumerated.
- (e) Runtime cost target (< 1ms per frame on 1280×720) is stated with per-component breakdown.
- (f) Integration with `budget_signal.py` degraded-signal pattern is sketched with module paths, schema, and hysteresis semantics.
- (g) Failure modes are documented (false positives, false negatives, operational).

This document satisfies all seven. Phase 1 of the triage epic now has a chosen metric for B2; Phase 2 (test harness across all effects and chains) and Phase 5 (runtime check) can be planned against it.

---

## 9. References

- `docs/research/2026-04-20-nebulous-scrim-three-bound-invariants-triage.md` (planning epic; B2 is one of three bounds)
- `docs/research/2026-04-20-nebulous-scrim-design.md` §7 invariant 2, §9.2, §9.6, §11 Phase 5, §13 (scrim-profile taxonomy)
- `agents/studio_compositor/budget.py:118` (`BudgetTracker` — rolling-window pattern)
- `agents/studio_compositor/budget.py:223` (`over_budget` — single-frame threshold pattern)
- `agents/studio_compositor/budget_signal.py:99` (`build_degraded_signal` — pure-function score builder)
- `agents/studio_compositor/budget_signal.py:145` (`publish_degraded_signal` — atomic write + freshness gauge)
- `agents/studio_compositor/budget_signal.py:63` (`DEFAULT_SIGNAL_PATH` — `/dev/shm/hapax-compositor/` convention)
- `agents/studio_compositor/atomic_io.py` (`atomic_write_json` — shared atomic-write helper)
- `agents/studio_compositor/chat_reactor.py` (`PresetReactor` — signal → graph-mutation.json pattern)
- `agents/hapax_daimonion/presence_engine.py` (Bayesian hysteresis state machine — recovery semantics reference)
- `shared/governance/consent.py` (fail-closed configuration loading pattern)
- `shared/governance/classifier_degradation.py` (empirical-distribution threshold derivation pattern)
- `shared/freshness_gauge.py` (`FreshnessGauge` — silent-stop visibility)
- `shared/telemetry.py` (`hapax_score` — telemetry shape for sub-scored governance metrics)
- `tests/effect_graph/test_neon_palette_cycle.py` (D-25 / OQ-01 brightness-ceiling regression — preserves the in-the-wild B2 violation frame)
- Wang, Z., & Bovik, A.C. (2009). "Mean Squared Error: Love It or Leave It?" IEEE Signal Processing Magazine. (SSIM's failure mode on global-collapse distortions.)
