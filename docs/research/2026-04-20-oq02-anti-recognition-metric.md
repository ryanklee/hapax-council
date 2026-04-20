# OQ-02 Bound 1 — Anti-Recognition Metric Selection

**Status:** RESEARCH — input to Phase 1 of the Nebulous Scrim three-bound invariant epic.
**Owner:** alpha
**Cross-link:** parent epic `docs/research/2026-04-20-nebulous-scrim-three-bound-invariants-triage.md` §3 (Bound 1) and §4 (Phase 1).
**Scope:** select and prototype the Bound 1 oracle only. Bounds 2 (scrim-translucency) and 3 (anti-audio-visualizer) are deferred to sibling research docs.

## 1. Metric specification

### 1.1 Chosen oracle

**InsightFace SCRFD `buffalo_sc` 512-d face embedding, cosine similarity against the operator's enrolled `operator_face.npy`, evaluated on the post-effect egress frame.**

The candidate enumerated in the triage doc (`triage.md` §4 Phase 1, line 54) names L2 distance. Cosine similarity is preferred for three reasons:

1. The existing operator-ReID path in `agents/hapax_daimonion/face_detector.py:144` already uses cosine. Reusing it keeps a single threshold-derivation methodology across presence detection (Bound 1 internal, "is this the operator?") and scrim escape (Bound 1 external, "can a viewer recognise the operator?"). Two numeric thresholds against the same embedding space, one oracle.
2. `buffalo_sc` embeddings are not L2-normalised on emit; cosine implicitly normalises and removes the dependency on detected-face area magnitude, which would otherwise bias L2 toward large faces.
3. The literature on InsightFace ReID (`ArcFace`, `CosFace`) is built on angular margin objectives — the trained embedding manifold IS angular. L2 over a curved manifold has poorly behaved tails; cosine respects the geometry.

The **oracle predicate** is:

```
recognisable(post_effect_frame) ⇔ ∃ face f detected in post_effect_frame
                                    such that cos_sim(embed(f), operator_embedding) > τ_anti_recognition
```

The bound is satisfied when the predicate is **false** — no detected face survives the post-effect frame with a similarity to the operator above τ.

### 1.2 Threshold derivation methodology

Two thresholds matter and they are NOT the same number:

- **τ_present** (used by `face_detector.is_operator`, currently `0.35` per `face_detector.py:24`) — "is this face plausibly the operator from a clean BRIO frame?". Tuned for true-positive recall on un-obscured operator imagery.
- **τ_anti_recognition** (this work) — "could a third party with the operator's embedding recognise the operator from this scrim frame?". This is an **adversary-model** threshold, not a recall threshold. The adversary owns a clean reference embedding and asks a single yes/no.

Methodology to derive τ_anti_recognition (corpus-based, offline, one-time per model):

1. **Reference set construction.** Render N=200 reference frames from the studio cameras with the face-obscure pipeline ENABLED (the §3 §10 Q1 decision: face-obscure runs BEFORE scrim). These frames are the "post-obscure, pre-scrim" baseline — already privacy-bounded by #129.
2. **Negative reference set.** Render N=200 reference frames with face-obscure DISABLED — the "raw operator face" attacker upper bound. These represent worst-case re-identification.
3. **Distribution measurement.** For every shipped scrim effect AND every preset chain in `agents/effect_graph/presets/`, render each reference frame through the chain, run SCRFD on the result, record the maximum cos_sim against `operator_face.npy` across all detected faces (or `0.0` if no faces detected).
4. **Threshold selection.** τ_anti_recognition = the 99th percentile of cos_sim from the **face-obscure-ENABLED** baseline distribution PLUS a safety margin of `0.05`. Rationale: the obscured baseline already passes the privacy bar by construction (#129 is a hard requirement); any scrim frame whose maximum cos_sim is at or below the 99p of the obscured baseline is at least as private as the baseline. The `+0.05` margin guards against measurement noise from the small N.
5. **Sanity check.** τ_anti_recognition must be ≤ τ_present − 0.05. If the derived threshold is higher than the presence-detection threshold, either the obscure pipeline is leaking identity OR the presence detector is too lenient. Either is a bug, not a tuning knob.

Initial point estimate (to be replaced by the corpus measurement): **τ_anti_recognition = 0.28**. This is τ_present (0.35) − 0.07, which leaves margin both above the obscured baseline and below the presence threshold. The first run of the Phase 2 harness will replace this with a measured value and emit a calibration artefact at `~/hapax-state/scrim-invariants/anti-recognition-calibration.json`.

### 1.3 False-positive / false-negative cost

| Outcome | Cost | Trigger |
|---|---|---|
| **False negative** (oracle says SAFE, viewer can recognise) | **Constitutional violation.** Identity leak to livestream. Same severity tier as a #129 face-obscure bypass. | τ set too high; or detector misses a face that is actually recognisable; or post-effect distortion fools the embedder but not a human. |
| **False positive** (oracle says LEAK, viewer cannot recognise) | Operational nuisance. Effect is rejected at CI gate or runtime damps a chain. Studio aesthetic narrows. | τ set too low; or detector lights up on hallucinated face in scrim noise; or degraded scrim still embeds far from operator but above τ. |

The cost asymmetry mandates **conservative τ** — when in doubt, fail the bound. This is consistent with the `face_obscure_integration.py:173` fail-closed pattern: a privacy-critical surface treats "uncertain" as "violated".

The single most dangerous failure mode is a **detector miss** combined with residual identity in the frame — SCRFD finds no face in the scrim output, returns the empty list, the oracle returns `safe=True` because there is "no face to compare", but a human viewer (or a more powerful detector) recognises the operator from low-frequency face-shape information. Mitigation: see §6 (failure modes) — the oracle treats detector misses on frames with high pre-effect face-shape SSIM as a fail-closed condition.

## 2. Operator's enrolled embedding — location

**Confirmed present** at `~/.local/share/hapax-daimonion/operator_face.npy` (2176 bytes, mtime 2026-03-18 — 2048 bytes for 512 float32 + 128-byte numpy `.npy` header). Loaded by `agents/hapax_daimonion/face_detector.py:101`.

Enrollment workflows (already shipped):

- **Auto-enrollment** (`face_detector.py:147`): first BRIO-camera face above `_AUTO_ENROLL_CONFIDENCE = 0.7` is captured silently. Single-sample, no validation.
- **Interactive multi-modal enrollment** (`agents/hapax_daimonion/enrollment.py:204` — `enroll_face`): part of the voice enrollment ritual; reads the latest BRIO frame from `/dev/shm/hapax-compositor/brio-operator.jpg` and writes the same target file.

**Recommended enhancement** (NOT a blocker for this metric, but a recommended Phase 1+ task): replace single-sample enrollment with multi-sample averaged enrollment, mirroring the existing speaker-embedding multi-sample pattern in `enrollment.py:274` (the voice path already records 10 samples, validates pairwise similarity, drops outliers, averages). The same pattern applied to face yields a more robust operator centroid — record N=8 frames at varied angles/expressions/lighting, validate with `compute_pairwise_similarity` (already factored out in `enrollment.py:46`), average the in-distribution embeddings, normalise to unit length. The voice enrollment already calls into `enroll_face` as a side effect; extending this to a multi-sample face capture is one new function.

Two operational concerns:

1. **Embedding staleness.** Faces drift over months (beard, weight, lighting). The current single-sample embedding from 2026-03-18 may already be drifting. Re-enrollment cadence needs a policy — proposal: re-enroll on every voice enrollment session (since both rituals are co-located at `enrollment.py`), and emit a Prometheus gauge `operator_embedding_age_days` so the staleness is observable.
2. **Embedding tampering.** The file lives in user-writable space. The oracle MUST refuse to load an embedding whose dimensionality differs from 512 OR whose L2 norm is more than 3σ from the enrollment-time norm. Protects against silent corruption that would invalidate every threshold downstream.

## 3. Module sketch — `shared/governance/scrim_invariants/anti_recognition.py`

The placement under `shared/governance/scrim_invariants/` (not `agents/effect_graph/invariants/` as the triage doc speculatively named) sits the oracle next to the existing governance primitives in `shared/governance/` (consent gate, qdrant gate, monetization audit). The CI gate, the runtime check, and any future cross-surface invariant code all import from one place.

```python
# shared/governance/scrim_invariants/anti_recognition.py
"""Bound 1 (anti-recognition) oracle for the Nebulous Scrim three-bound invariants.

See docs/research/2026-04-20-oq02-anti-recognition-metric.md for design.
See docs/research/2026-04-20-nebulous-scrim-three-bound-invariants-triage.md
for the parent epic.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    import numpy as np

# Default operator embedding location — same path as
# agents/hapax_daimonion/face_detector.py:_OPERATOR_EMBEDDING_PATH.
DEFAULT_OPERATOR_EMBEDDING_PATH: Path = (
    Path.home() / ".local" / "share" / "hapax-daimonion" / "operator_face.npy"
)

# Conservative initial threshold — replaced by the calibration artefact
# at ~/hapax-state/scrim-invariants/anti-recognition-calibration.json
# once Phase 2 harness has run against the reference corpus.
DEFAULT_TAU_ANTI_RECOGNITION: float = 0.28

# Embedding dimensionality for buffalo_sc — the oracle refuses any other.
EXPECTED_EMBEDDING_DIM: int = 512


@dataclass(frozen=True)
class AntiRecognitionResult:
    """Outcome of one oracle evaluation on a single egress frame.

    `safe=True` means the bound is satisfied: no detected face on the
    post-effect frame matches the operator's enrolled embedding above τ.
    `max_similarity` is the worst (highest) cosine similarity observed
    across all detected faces; equal to 0.0 when no face was detected.
    `face_count` is informational — number of SCRFD detections above the
    detector's own min_confidence threshold.
    `fail_closed_reason` is non-None when the oracle could not produce a
    real measurement and defaulted to `safe=False`. Examples: detector
    missing, embedding missing, frame malformed.
    """

    safe: bool
    max_similarity: float
    face_count: int
    threshold: float
    fail_closed_reason: str | None = None


class FaceEmbeddingProvider(Protocol):
    """Protocol for the SCRFD detector + embedder.

    Production implementation wraps agents.hapax_daimonion.face_detector.
    Tests inject a stub that returns canned embeddings without loading
    InsightFace.
    """

    def embed_faces(self, frame: np.ndarray) -> list[np.ndarray]:
        """Return one 512-d embedding per detected face (empty if none)."""
        ...


def load_operator_embedding(
    path: Path = DEFAULT_OPERATOR_EMBEDDING_PATH,
) -> np.ndarray | None:
    """Load and validate the operator embedding.

    Returns the embedding on success, None on any failure (missing file,
    wrong dimensionality, NaN, abnormal norm). Callers must treat None as
    a fail-closed condition — the oracle cannot run without a reference.
    """
    ...


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Stable cosine similarity, returning 0.0 for zero-norm inputs.

    Mirrors agents.hapax_daimonion.face_detector._cosine_similarity but
    re-implemented locally so this module does not import a daimonion
    internal.
    """
    ...


def evaluate_frame(
    frame: np.ndarray,
    *,
    embedder: FaceEmbeddingProvider,
    operator_embedding: np.ndarray,
    threshold: float = DEFAULT_TAU_ANTI_RECOGNITION,
) -> AntiRecognitionResult:
    """Run the Bound 1 oracle on one post-effect egress frame.

    The frame is expected to be the COMPOSITED, POST-EFFECT, PRE-ENCODE
    BGR uint8 ndarray — the last surface before NVENC. Earlier in the
    pipeline (raw camera, post-obscure pre-scrim) the bound is enforced
    by other layers (#129) and this oracle would over-report leaks.

    Behaviour summary:
    - No faces detected → safe=True, max_similarity=0.0
      (subject to §6 fail-closed-on-detector-miss caveat — see notes
      in the design doc; this initial cut treats no-detection as safe
      and the harness covers the silhouette-leak case separately)
    - Faces detected, max_similarity ≤ threshold → safe=True
    - Faces detected, max_similarity > threshold → safe=False
    - Embedder raises → safe=False, fail_closed_reason set
    """
    ...


def evaluate_chain(
    frames: list[np.ndarray],
    *,
    embedder: FaceEmbeddingProvider,
    operator_embedding: np.ndarray,
    threshold: float = DEFAULT_TAU_ANTI_RECOGNITION,
) -> list[AntiRecognitionResult]:
    """Evaluate a sequence of frames produced by one effect or chain.

    Used by the Phase 2 test harness for per-effect and per-chain
    sweeps. Returns one result per frame; harness aggregates.
    """
    ...


def make_default_embedder() -> FaceEmbeddingProvider:
    """Construct the production embedder backed by the daimonion's
    SCRFD instance.

    Lazy-imports agents.hapax_daimonion.face_detector so the governance
    package stays optional-import-free at module load time.
    """
    ...
```

The `make_default_embedder()` factory deliberately wraps the existing daimonion `FaceDetector` rather than constructing a parallel SCRFD session — VRAM is finite (workspace CLAUDE.md `project_vram_budget` notes 24 GB coexistence) and a second buffalo_sc instance would compete with the live presence-detection path.

## 4. Acceptance test sketch

`tests/governance/scrim_invariants/test_anti_recognition.py`. Self-contained per project convention (`unittest.mock` only, no shared `conftest`).

**Fixtures:**

- `operator_embedding_npy` — small temp `.npy` file with a synthetic 512-d unit vector (deterministic seed). Avoids loading the real operator file in CI.
- `stub_embedder` — `Mock(spec=FaceEmbeddingProvider)` whose `embed_faces` returns canned lists per test.
- `synthetic_bgr_frame` — `np.zeros((720, 1280, 3), dtype=np.uint8)`. The oracle does not care about pixel content when the embedder is stubbed.

**Assertions (one-liner per test, ten tests):**

1. `evaluate_frame` with empty `embed_faces` → `safe=True`, `max_similarity=0.0`, `face_count=0`.
2. `evaluate_frame` with one embedding equal to `operator_embedding` → `safe=False`, `max_similarity≈1.0`.
3. `evaluate_frame` with one embedding orthogonal to `operator_embedding` → `safe=True`, `max_similarity≈0.0`.
4. `evaluate_frame` with two embeddings, one above τ and one below → `safe=False`, `max_similarity` = the higher of the two.
5. `evaluate_frame` with a custom `threshold=0.99` and embedding ≈ 0.95 sim → `safe=True`.
6. `evaluate_frame` when embedder raises → `safe=False`, `fail_closed_reason` non-None.
7. `load_operator_embedding` on a nonexistent path → `None`.
8. `load_operator_embedding` on a `.npy` of wrong shape (e.g. 256-d) → `None`.
9. `load_operator_embedding` on a `.npy` containing NaN → `None`.
10. `cosine_similarity` on two zero vectors → `0.0` (no division-by-zero crash).

Property-based test (Hypothesis, per workspace convention):

- For any random 512-d unit vector `v`, `cosine_similarity(v, v) == pytest.approx(1.0)`.
- For any random pair `(v, w)`, `−1.0 <= cosine_similarity(v, w) <= 1.0`.

Integration smoke test (gated `@pytest.mark.llm` style — excluded by default, runs when InsightFace is installed):

- Load the real `operator_face.npy`. Embed a clean BRIO snapshot from `/dev/shm/hapax-compositor/brio-operator.jpg`. Assert `max_similarity > 0.7` (sanity: the operator IS the operator on a clean frame). Embed a maximally-pixelated version of the same frame (16-pixel blocks). Assert `max_similarity < τ_anti_recognition`. This anchors both ends of the scale.

## 5. Runtime cost analysis

**Per-frame cost components on the post-effect egress frame:**

1. SCRFD detection on `buffalo_sc` at 640×640 input: prior measurement in `face_detector.py` deployment context is ~15–25 ms on the GPU (`CUDAExecutionProvider`). The egress frame is 1920×1080; downscale-to-detector-size dominates over inference.
2. Embedding extraction per detected face: ~5 ms each, parallelised inside InsightFace's pipeline.
3. Cosine similarity: O(512) multiply-add per face. Sub-millisecond.
4. Oracle bookkeeping: dataclass construction, return — sub-millisecond.

**Realistic per-frame cost: 25–40 ms when 1–2 faces present.** At 30 fps stream (33.3 ms budget per frame), running this oracle inline on every egress frame is **not feasible** — it consumes the entire frame budget and competes with the daimonion's presence-detection use of the SAME SCRFD instance.

**Rate budget proposal:**

- **CI gate (Phase 4):** off-stream, no rate budget. Run the oracle on every (effect × audio profile) and (chain × audio profile) cell of the test matrix. Test runtime is the only budget.
- **Runtime egress check (Phase 5):** sample at 1 Hz on egress, in a separate thread that pulls the latest composited frame from a single-slot ring buffer. 1 Hz is sufficient because: (a) face-recognition leak is a perceptual continuum, not a one-frame event — three consecutive 1 Hz fails span 3 seconds of compromised stream, well within human perception window; (b) the 5-state recovery FSM model from camera 24/7 epic shows that operator-perceptible degradation needs ≥ ~2 s coherence. A 1 Hz sample with a 3-of-5 sliding-window vote on `safe=False` triggers chain-damping. False-positive cost (one transient damping every few minutes) is acceptable.
- **Sentinel-pixel check (separate from this oracle):** the triage doc Phase 5 also proposes a checksum-on-obscured-pixels sentinel for the obscure-bypass case. That is a different invariant (face-obscure pipeline correctness) and not this metric's responsibility.

**SCRFD instance sharing:** the runtime check MUST share the daimonion's `FaceDetector` singleton, not allocate its own. Two concurrent buffalo_sc sessions on the same GPU thrash. `make_default_embedder()` resolves the singleton by importing the daimonion module, which already caches the InsightFace `FaceAnalysis` per `face_detector.py:74`.

**Memory cost:** the operator embedding is 2 KB, in-process. Negligible.

## 6. Failure modes

The oracle is privacy-critical infrastructure. Every failure path must default to **safe=False** (fail-closed) so that a broken oracle blocks effects rather than silently passing a leaky chain. This mirrors the `face_obscure_integration.py:173` fail-closed posture.

| Failure | Behaviour |
|---|---|
| **Detector model not installed** (InsightFace missing in the environment) | `make_default_embedder()` raises at construction. CI gate FAILS the test run loudly with a setup error — install the package or skip the suite via `@pytest.mark.requires_insightface`. The runtime check daemon refuses to start and emits a Prometheus gauge `scrim_invariants_anti_recognition_available=0`. The compositor MUST treat the absence of the runtime check as a degraded-stream signal, not as "no problem" — see `agents/studio_compositor/budget_signal.py` pattern. |
| **GPU OOM during detection** | Embedder raises. `evaluate_frame` returns `safe=False, fail_closed_reason="embedder_raised"`. Runtime check increments a Prometheus counter `scrim_invariants_oracle_errors_total{reason="embedder_raised"}`. After K consecutive failures (default K=10) the runtime check emits a degraded-stream signal and the chain-damper drops to a known-safe minimum chain. |
| **Operator embedding file missing** (`~/.local/share/hapax-daimonion/operator_face.npy` absent) | `load_operator_embedding` returns `None`. The oracle MUST refuse to evaluate — without a reference there is no Bound 1, only a vacuous true. CI gate fails; runtime check emits `scrim_invariants_anti_recognition_available=0` and the compositor degrades. The single-user axiom means re-enrolment is straightforward (`uv run python -m agents.hapax_daimonion.enrollment`). |
| **Operator embedding malformed** (wrong dim, NaN, abnormal norm) | Same as missing. Validated in `load_operator_embedding`. |
| **Detector returns no faces on a frame that demonstrably contains a recognisable operator** (silhouette leak or detector-confused-by-effect case) | This is the most pernicious failure. The oracle as specified returns `safe=True` because there is nothing to score. Mitigation lives ONE LAYER UP in the test harness, not in this oracle: the Phase 2 harness pairs every post-effect frame with its pre-effect counterpart, and asserts that if the pre-effect frame had a high-confidence operator face AND the post-effect frame has zero detections AND the structural similarity (SSIM) of the face region is above a sanity floor (i.e. the face-shape is still there), the harness flags the cell as a Bound 1 violation regardless of what `evaluate_frame` says. This bug class is discussed in §1.3 above. |
| **Frame is malformed** (None, wrong dtype, zero-size) | Embedder is responsible for handling — the existing `FaceDetector.detect` at `face_detector.py:180` returns an empty result on `image.size == 0`. Oracle returns `safe=True` for empty results in normal mode but the runtime check should treat sustained empty-frame periods as a streaming-pipeline bug, not as a bound-satisfaction signal. |
| **Threshold calibration file missing** (Phase 2 calibration not yet run) | Oracle uses `DEFAULT_TAU_ANTI_RECOGNITION = 0.28`. This is conservative-by-design; running un-calibrated is acceptable and produces tighter-than-necessary rejections. A WARN log is emitted on first use. |

The metric is auditable end-to-end: every result includes `max_similarity`, `face_count`, `threshold`, and `fail_closed_reason`. Langfuse instrumentation via `shared.telemetry.hapax_event` at the runtime-check layer (NOT inside `evaluate_frame`, which must stay pure) lets the operator review the distribution of similarities over a stream and recalibrate the corpus when face drift becomes measurable.

## 7. Sources

- Parent epic: `docs/research/2026-04-20-nebulous-scrim-three-bound-invariants-triage.md`
- Existing operator ReID + threshold context: `agents/hapax_daimonion/face_detector.py:20-29`, `face_detector.py:129-145`, `face_detector.py:170-228`
- Existing enrollment workflow: `agents/hapax_daimonion/enrollment.py:30-32`, `enrollment.py:204-230`, `enrollment.py:46-77` (multi-sample validation pattern reusable for face)
- Existing face-obscure pipeline (Bound 1's pre-condition layer): `agents/studio_compositor/face_obscure_integration.py:132-206`, `face_obscure.py:30-43`
- SCRFD bbox source already wrapping `FaceDetector`: `agents/studio_compositor/face_obscure_pipeline.py:75-`
- Council CLAUDE.md § Bayesian Presence Detection: `operator_face (InsightFace SCRFD, 9x)` confirms buffalo_sc is the production embedder
- Workspace CLAUDE.md § VRAM budget reference for justifying SCRFD singleton sharing
- Governance package home: `shared/governance/` (consent gate, qdrant gate, monetization audit — peer modules)
- Operator embedding on disk: `~/.local/share/hapax-daimonion/operator_face.npy` (2176 bytes, 512-d float32 + npy header, mtime 2026-03-18)
