# Reverie Recruitment Diversity Implementation Plan

> **Status: COMPLETE** — Merged via PR #630 (squash) + follow-on commit `dbb881873`. Deployed and verified 2026-04-05.

**Goal:** Fix three coupled failures in the Reverie recruitment loop — monotonic content resolution, satellite accumulation, and flat match scoring — using mechanisms already specified in the theoretical design documents.

**Architecture:** Three independent fixes, each grounded in existing theoretical machinery. Fix 1 applies ACT-R recency to content resolution. Fix 2 applies Carandini-Heeger habituation to satellite refresh. Fix 3 closes the exploration feedback loop into affordance scoring. All three maintain the single-recruitment-mechanism invariant. Follow-on fix added per-tick satellite dedup and narrative fallback.

**Tech Stack:** Python 3.12, Qdrant client, pydantic, unittest.mock, pytest

**Commits:**
- PR #630: content recency penalty, satellite habituation, exploration noise, audit remediation
- `dbb881873`: per-tick satellite dedup + narrative fallback (follow-on from production observation)

**Deferred items (from audit):**
- I2: Thompson sampling learns from noise-reordered winners — subtle accumulation risk
- I3: Count-based vs strength-relative habituation formula deviation
- M1: Shared deque across knowledge/episodic domains
- O4: `maxlen=10` deque short for 1s cadence

**Theoretical authority documents (do not violate):**
- `docs/superpowers/specs/2026-04-02-unified-semantic-recruitment-design.md` — single pipeline, no bypass paths
- `docs/superpowers/specs/2026-04-01-boredom-exploration-signal-design.md` — 15th control law, sigma_explore
- `docs/superpowers/specs/2026-03-31-reverie-adaptive-compositor-design.md` — satellite recruitment/dismissal
- `docs/research/stigmergic-cognitive-mesh.md` — stigmergic coordination, no direct message passing
- `docs/superpowers/specs/2026-03-25-affordance-retrieval-architecture.md` — ACT-R activation, Thompson sampling

---

## File Map

| File | Action | Responsibility |
|------|--------|---------------|
| `agents/reverie/_content_resolvers.py` | Modify | Add recency-penalized top-k retrieval to `resolve_knowledge_recall` and `resolve_episodic_recall` |
| `agents/reverie/_content_capabilities.py` | Modify | Add `_recent_documents` deque to `ContentCapabilityRouter`, pass to resolvers |
| `agents/reverie/_satellites.py` | Modify | Add habituating refresh to `SatelliteManager.recruit()` |
| `shared/affordance_pipeline.py` | Modify | Add exploration noise feedback in `select()` using existing `sigma_explore` |
| `tests/test_content_resolver_diversity.py` | Create | Tests for recency-penalized retrieval |
| `tests/test_satellite_habituation.py` | Create | Tests for diminishing refresh and cycling |
| `tests/test_affordance_exploration_feedback.py` | Create | Tests for boredom-proportional scoring noise |

---

## Task 1: Content Resolution Recency Penalty — Tests

**Files:**
- Create: `tests/test_content_resolver_diversity.py`

- [ ] **Step 1: Write failing tests for recency-penalized retrieval**

```python
"""Tests for content resolution diversity — recency penalty prevents monotonic lock-on."""

from collections import deque
from unittest.mock import MagicMock, patch

import pytest


class TestRecencyPenalty:
    def test_fresh_query_returns_top_result(self):
        """With no recent history, resolver returns the highest-scoring document."""
        from agents.reverie._content_resolvers import resolve_knowledge_recall

        mock_points = [
            _make_point("doc-a", 0.9, "Alpha content text here"),
            _make_point("doc-b", 0.85, "Beta content text here"),
            _make_point("doc-c", 0.8, "Gamma content text here"),
        ]
        recent: deque[str] = deque(maxlen=10)

        with _patch_qdrant(mock_points), _patch_embed(), _patch_inject() as injected:
            result = resolve_knowledge_recall("test narrative", 0.5, recent_ids=recent)

        assert result is True
        assert "Alpha content" in injected[0]
        assert len(recent) == 1

    def test_repeated_query_avoids_recent_document(self):
        """When top result was recently returned, resolver picks the next-best."""
        from agents.reverie._content_resolvers import resolve_knowledge_recall

        mock_points = [
            _make_point("doc-a", 0.9, "Alpha content text here"),
            _make_point("doc-b", 0.85, "Beta content text here"),
            _make_point("doc-c", 0.8, "Gamma content text here"),
        ]
        recent: deque[str] = deque(["doc-a"], maxlen=10)

        with _patch_qdrant(mock_points), _patch_embed(), _patch_inject() as injected:
            result = resolve_knowledge_recall("test narrative", 0.5, recent_ids=recent)

        assert result is True
        assert "Beta content" in injected[0]

    def test_all_recent_falls_through_to_best(self):
        """When all results are recent, still returns best (don't return nothing)."""
        from agents.reverie._content_resolvers import resolve_knowledge_recall

        mock_points = [
            _make_point("doc-a", 0.9, "Alpha content text here"),
            _make_point("doc-b", 0.85, "Beta content text here"),
        ]
        recent: deque[str] = deque(["doc-a", "doc-b"], maxlen=10)

        with _patch_qdrant(mock_points), _patch_embed(), _patch_inject() as injected:
            result = resolve_knowledge_recall("test narrative", 0.5, recent_ids=recent)

        assert result is True
        # Falls through to best available
        assert "Alpha content" in injected[0]

    def test_dedup_by_source_filename(self):
        """Multiple chunks from same file should be deduped before scoring."""
        from agents.reverie._content_resolvers import resolve_knowledge_recall

        mock_points = [
            _make_point("doc-a", 0.9, "Alpha chunk 0", filename="notes.md"),
            _make_point("doc-a2", 0.88, "Alpha chunk 1", filename="notes.md"),
            _make_point("doc-b", 0.85, "Beta content", filename="other.md"),
        ]
        recent: deque[str] = deque(maxlen=10)

        with _patch_qdrant(mock_points), _patch_embed(), _patch_inject() as injected:
            result = resolve_knowledge_recall("test narrative", 0.5, recent_ids=recent)

        assert result is True
        assert "Alpha chunk 0" in injected[0]

    def test_recent_ids_updated_after_resolution(self):
        """Resolver appends selected document ID to recent deque."""
        from agents.reverie._content_resolvers import resolve_knowledge_recall

        mock_points = [_make_point("doc-x", 0.9, "X content")]
        recent: deque[str] = deque(maxlen=10)

        with _patch_qdrant(mock_points), _patch_embed(), _patch_inject():
            resolve_knowledge_recall("test narrative", 0.5, recent_ids=recent)

        assert "doc-x" in recent


# ── Test helpers ──────────────────────────────────────────────────────────


def _make_point(point_id, score, text, filename=None):
    """Create a mock Qdrant ScoredPoint."""
    pt = MagicMock()
    pt.id = point_id
    pt.score = score
    pt.payload = {"text": text}
    if filename:
        pt.payload["filename"] = filename
    return pt


def _patch_qdrant(points):
    """Patch get_qdrant to return mock points."""
    mock_client = MagicMock()
    mock_result = MagicMock()
    mock_result.points = points
    mock_client.query_points.return_value = mock_result
    return patch("agents.reverie._content_resolvers.get_qdrant", return_value=mock_client)


def _patch_embed():
    """Patch embed_safe to return a dummy vector."""
    return patch(
        "agents.reverie._content_resolvers.embed_safe", return_value=[0.1] * 768
    )


def _patch_inject():
    """Patch _inject_recalled_text and capture what was injected."""
    captured = []

    def side_effect(source_suffix, text, level):
        captured.append(text)
        return True

    p = patch(
        "agents.reverie._content_resolvers._inject_recalled_text",
        side_effect=side_effect,
    )
    captured_ref = captured
    # Return the captured list so callers can inspect it
    class PatchContext:
        def __enter__(self_inner):
            p.__enter__()
            return captured_ref
        def __exit__(self_inner, *args):
            p.__exit__(*args)
    return PatchContext()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd hapax-council && uv run pytest tests/test_content_resolver_diversity.py -v`
Expected: FAIL — `resolve_knowledge_recall` does not accept `recent_ids` parameter yet.

- [ ] **Step 3: Commit test file**

```bash
cd hapax-council && git add tests/test_content_resolver_diversity.py
git commit -m "test: content resolver diversity — recency penalty and dedup"
```

---

## Task 2: Content Resolution Recency Penalty — Implementation

**Files:**
- Modify: `agents/reverie/_content_resolvers.py:57-82` (resolve_knowledge_recall)
- Modify: `agents/reverie/_content_resolvers.py:31-54` (resolve_episodic_recall — same pattern)
- Modify: `agents/reverie/_content_capabilities.py:29-37` (ContentCapabilityRouter — add recent_ids deque)
- Modify: `agents/reverie/_content_capabilities.py:100-126` (activate_content — pass recent_ids)

- [ ] **Step 4: Implement recency-penalized resolve_knowledge_recall**

In `agents/reverie/_content_resolvers.py`, replace `resolve_knowledge_recall` (lines 57-82):

```python
def resolve_knowledge_recall(
    narrative: str,
    level: float,
    sources_dir: Path = SOURCES_DIR,
    recent_ids: deque | None = None,
) -> bool:
    """Query documents Qdrant collection for relevant knowledge.

    Retrieves top-5, deduplicates by source filename, applies recency
    penalty (ACT-R principle: recently returned content is suppressed
    to prevent monotonic lock-on). Maintains the recruitment invariant:
    narrative drives the query, recency modulates selection.
    """
    try:
        from shared.config import embed_safe, get_qdrant

        embedding = embed_safe(narrative, prefix="search_query")
        if embedding is None:
            return _fallback_text("knowledge_recall", f"Searching: {narrative[:80]}", level)

        client = get_qdrant()
        results = client.query_points(
            collection_name="documents",
            query=embedding,
            limit=5,
        ).points
        if not results:
            return _fallback_text(
                "knowledge_recall", f"No documents match: {narrative[:80]}", level
            )

        # Dedup by filename (same document chunked multiple times)
        seen_files: set[str] = set()
        unique: list = []
        for pt in results:
            fname = pt.payload.get("filename", pt.id)
            if fname not in seen_files:
                seen_files.add(fname)
                unique.append(pt)

        # Recency penalty: prefer documents not recently shown
        recent_set = set(recent_ids) if recent_ids is not None else set()
        non_recent = [pt for pt in unique if str(pt.id) not in recent_set]
        selected = non_recent[0] if non_recent else unique[0]

        # Track this selection
        if recent_ids is not None:
            recent_ids.append(str(selected.id))

        text = selected.payload.get("text", selected.payload.get("content", str(selected.payload)))
        return _inject_recalled_text("knowledge_recall", text[:400], level)
    except Exception:
        log.debug("Knowledge recall failed", exc_info=True)
        return _fallback_text("knowledge_recall", f"Searching: {narrative[:80]}", level)
```

Add `from collections import deque` to the imports at line 7.

- [ ] **Step 5: Apply same pattern to resolve_episodic_recall**

In `agents/reverie/_content_resolvers.py`, replace `resolve_episodic_recall` (lines 31-54):

```python
def resolve_episodic_recall(
    narrative: str,
    level: float,
    sources_dir: Path = SOURCES_DIR,
    recent_ids: deque | None = None,
) -> bool:
    """Query operator-episodes Qdrant collection for similar past experiences."""
    try:
        from shared.config import embed_safe, get_qdrant

        embedding = embed_safe(narrative, prefix="search_query")
        if embedding is None:
            return _fallback_text("episodic_recall", f"Recalling: {narrative[:80]}", level)

        client = get_qdrant()
        results = client.query_points(
            collection_name="operator-episodes",
            query=embedding,
            limit=3,
        ).points
        if not results:
            return _fallback_text("episodic_recall", f"No episodes match: {narrative[:80]}", level)

        # Recency penalty
        recent_set = set(recent_ids) if recent_ids is not None else set()
        non_recent = [pt for pt in results if str(pt.id) not in recent_set]
        selected = non_recent[0] if non_recent else results[0]

        if recent_ids is not None:
            recent_ids.append(str(selected.id))

        text = selected.payload.get("narrative", selected.payload.get("text", str(selected.payload)))
        return _inject_recalled_text("episodic_recall", text[:400], level)
    except Exception:
        log.debug("Episodic recall failed", exc_info=True)
        return _fallback_text("episodic_recall", f"Recalling: {narrative[:80]}", level)
```

- [ ] **Step 6: Wire recent_ids deque into ContentCapabilityRouter**

In `agents/reverie/_content_capabilities.py`, add the deque to `__init__` (after line 37):

```python
from collections import deque

class ContentCapabilityRouter:
    """Routes recruited content affordances to concrete handlers."""

    def __init__(
        self,
        sources_dir: Path = DEFAULT_SOURCES,
        compositor_dir: Path = DEFAULT_COMPOSITOR,
    ) -> None:
        self._sources = sources_dir
        self._compositor = compositor_dir
        self._recent_ids: deque[str] = deque(maxlen=10)
```

In `activate_content` (line 115), pass `recent_ids` to the resolver:

Replace:
```python
            result = resolver(narrative, level, sources_dir=self._sources)
```
With:
```python
            result = resolver(narrative, level, sources_dir=self._sources, recent_ids=self._recent_ids)
```

- [ ] **Step 7: Run tests to verify they pass**

Run: `cd hapax-council && uv run pytest tests/test_content_resolver_diversity.py -v`
Expected: All 5 tests PASS.

- [ ] **Step 8: Run existing resolver tests**

Run: `cd hapax-council && uv run pytest tests/test_content_resolver_daemon.py -v`
Expected: All 3 existing tests PASS (they don't use `recent_ids`).

- [ ] **Step 9: Commit**

```bash
cd hapax-council && git add agents/reverie/_content_resolvers.py agents/reverie/_content_capabilities.py
git commit -m "fix(reverie): recency-penalized content resolution — ACT-R diversity

Retrieve top-5 from Qdrant (was limit=1), dedup by filename, suppress
recently-returned documents. Prevents monotonic lock-on where the same
document was returned 1,756 times in 2 hours. Maintains recruitment
invariant: narrative drives query, recency modulates selection."
```

---

## Task 3: Satellite Habituation — Tests

**Files:**
- Create: `tests/test_satellite_habituation.py`

- [ ] **Step 10: Write failing tests for habituating refresh**

```python
"""Tests for satellite habituation — diminishing refresh via Carandini-Heeger gain control."""

import json
from pathlib import Path

from agents.reverie._satellites import (
    DISMISSAL_THRESHOLD,
    RECRUITMENT_THRESHOLD,
    SatelliteManager,
)


def _core_vocab() -> dict:
    path = Path(__file__).resolve().parents[1] / "presets" / "reverie_vocabulary.json"
    return json.loads(path.read_text())


class TestHabituatingRefresh:
    def test_first_recruitment_full_strength(self):
        """First recruitment sets full strength (no habituation)."""
        mgr = SatelliteManager(_core_vocab())
        mgr.recruit("bloom", 0.5)
        assert mgr.recruited["bloom"] == 0.5

    def test_repeated_recruitment_diminishes(self):
        """Re-recruiting an active satellite applies diminishing gain."""
        mgr = SatelliteManager(_core_vocab())
        mgr.recruit("bloom", 0.5)
        mgr.recruit("bloom", 0.5)
        # Second recruitment at same strength should NOT fully refresh
        assert mgr.recruited["bloom"] < 0.5

    def test_stronger_signal_still_boosts(self):
        """A genuinely stronger signal should increase strength, even with habituation."""
        mgr = SatelliteManager(_core_vocab())
        mgr.recruit("bloom", 0.4)
        strength_before = mgr.recruited["bloom"]
        mgr.recruit("bloom", 0.65)
        assert mgr.recruited["bloom"] > strength_before

    def test_decay_eventually_dismisses_despite_refresh(self):
        """With diminishing refresh, decay eventually wins and satellite dismisses."""
        mgr = SatelliteManager(_core_vocab())
        mgr.recruit("bloom", 0.35)
        # Simulate 30 cycles: recruit at same strength, then decay
        for _ in range(30):
            mgr.recruit("bloom", 0.35)
            mgr.decay(dt=1.0)
        assert "bloom" not in mgr.recruited

    def test_no_habituation_after_dismissal(self):
        """After a satellite is dismissed and re-recruited, habituation resets."""
        mgr = SatelliteManager(_core_vocab())
        mgr.recruit("bloom", 0.5)
        mgr.decay(dt=100.0)  # Force dismissal
        assert "bloom" not in mgr.recruited
        mgr.recruit("bloom", 0.5)
        assert mgr.recruited["bloom"] == 0.5  # Full strength again
```

- [ ] **Step 11: Run tests to verify they fail**

Run: `cd hapax-council && uv run pytest tests/test_satellite_habituation.py -v`
Expected: `test_repeated_recruitment_diminishes` and `test_decay_eventually_dismisses_despite_refresh` FAIL (current `max()` behavior doesn't diminish).

- [ ] **Step 12: Commit test file**

```bash
cd hapax-council && git add tests/test_satellite_habituation.py
git commit -m "test: satellite habituation — diminishing refresh and cycling"
```

---

## Task 4: Satellite Habituation — Implementation

**Files:**
- Modify: `agents/reverie/_satellites.py:40-47` (SatelliteManager.recruit)

- [ ] **Step 13: Implement habituating refresh**

In `agents/reverie/_satellites.py`, replace the `recruit` method (lines 40-47):

```python
    def recruit(self, node_type: str, strength: float) -> None:
        """Recruit a satellite node with habituating refresh.

        First recruitment sets full strength. Re-recruitment of an already-active
        satellite applies diminishing gain (Carandini-Heeger divisive normalization):
        the closer the current strength is to the incoming strength, the smaller
        the refresh. This ensures decay eventually wins for monotonic input,
        while genuinely novel (stronger) signals still boost effectively.
        """
        if strength < RECRUITMENT_THRESHOLD:
            return
        prev = self._recruited.get(node_type, 0.0)
        if prev > 0:
            # Diminishing gain: ratio of headroom to signal strength.
            # At prev=0.3, strength=0.6: gain = 1.0 - 0.3/0.6 = 0.5 (strong refresh)
            # At prev=0.5, strength=0.5: gain = 0.3 (minimal floor, near-saturated)
            gain = max(0.3, 1.0 - prev / strength) if strength > 0 else 0.3
            self._recruited[node_type] = prev + (strength - prev) * gain
        else:
            self._recruited[node_type] = strength
        if node_type not in self._active_set:
            log.info("Satellite recruited: %s (strength=%.2f)", node_type, strength)
```

- [ ] **Step 14: Run habituation tests**

Run: `cd hapax-council && uv run pytest tests/test_satellite_habituation.py -v`
Expected: All 5 tests PASS.

- [ ] **Step 15: Run existing satellite tests**

Run: `cd hapax-council && uv run pytest tests/test_satellite_recruitment.py -v`
Expected: All existing tests PASS (recruit above threshold, decay dismisses, etc.).

- [ ] **Step 16: Commit**

```bash
cd hapax-council && git add agents/reverie/_satellites.py
git commit -m "fix(reverie): satellite habituation — diminishing refresh via divisive normalization

Replace max(prev, strength) with gain-controlled refresh. Repeated
re-recruitment at the same strength produces progressively smaller
boosts, allowing decay to eventually dismiss monotonically-recruited
satellites. Fixes 22:1 recruit-to-dismiss ratio. Genuinely stronger
signals still boost effectively."
```

---

## Task 5: Exploration Feedback into Scoring — Tests

**Files:**
- Create: `tests/test_affordance_exploration_feedback.py`

- [ ] **Step 17: Write failing tests for boredom-proportional noise**

```python
"""Tests for exploration feedback into affordance scoring.

The 15th control law specifies that boredom should increase gain on novelty
edges. The affordance pipeline's sigma_explore parameter should inject
scoring noise proportional to boredom_index, disrupting monotonic winners.
"""

import random
import time
from unittest.mock import MagicMock, patch

from shared.affordance import ActivationState, SelectionCandidate
from shared.exploration import ExplorationSignal
from shared.impingement import Impingement, ImpingementType


def _make_signal(boredom: float, curiosity: float = 0.0) -> ExplorationSignal:
    return ExplorationSignal(
        component="affordance_pipeline",
        timestamp=time.time(),
        mean_habituation=boredom,
        max_novelty_edge=None,
        max_novelty_score=0.0,
        error_improvement_rate=0.0,
        chronic_error=0.0,
        mean_trace_interest=1.0 - boredom,
        stagnation_duration=0.0,
        local_coherence=0.5,
        dwell_time_in_coherence=0.0,
        boredom_index=boredom,
        curiosity_index=curiosity,
    )


class TestExplorationNoise:
    def test_no_noise_when_not_bored(self):
        """With low boredom, scoring should be deterministic (no noise)."""
        from shared.affordance_pipeline import _apply_exploration_noise

        candidates = [
            _make_candidate("cap-a", 0.65),
            _make_candidate("cap-b", 0.60),
        ]
        sig = _make_signal(boredom=0.1)
        random.seed(42)
        _apply_exploration_noise(candidates, sig, sigma_explore=0.10)
        # No noise applied — scores unchanged
        assert candidates[0].combined == 0.65
        assert candidates[1].combined == 0.60

    def test_noise_applied_when_bored(self):
        """High boredom should perturb candidate scores."""
        from shared.affordance_pipeline import _apply_exploration_noise

        candidates = [
            _make_candidate("cap-a", 0.65),
            _make_candidate("cap-b", 0.60),
        ]
        sig = _make_signal(boredom=0.8)
        _apply_exploration_noise(candidates, sig, sigma_explore=0.10)
        # At least one score should have changed
        changed = candidates[0].combined != 0.65 or candidates[1].combined != 0.60
        assert changed

    def test_noise_can_reorder_candidates(self):
        """With enough boredom, noise should occasionally swap rankings."""
        from shared.affordance_pipeline import _apply_exploration_noise

        reordered = False
        for seed in range(100):
            candidates = [
                _make_candidate("cap-a", 0.65),
                _make_candidate("cap-b", 0.63),  # close gap — noise can flip
            ]
            sig = _make_signal(boredom=0.9)
            random.seed(seed)
            _apply_exploration_noise(candidates, sig, sigma_explore=0.10)
            if candidates[1].combined > candidates[0].combined:
                reordered = True
                break
        assert reordered, "100 trials with high boredom should reorder at least once"

    def test_noise_magnitude_proportional_to_boredom(self):
        """Higher boredom should produce larger perturbations."""
        from shared.affordance_pipeline import _apply_exploration_noise

        low_deltas = []
        high_deltas = []
        for seed in range(50):
            c_low = [_make_candidate("a", 0.65)]
            c_high = [_make_candidate("a", 0.65)]
            random.seed(seed)
            _apply_exploration_noise(c_low, _make_signal(boredom=0.45), sigma_explore=0.10)
            random.seed(seed)
            _apply_exploration_noise(c_high, _make_signal(boredom=0.9), sigma_explore=0.10)
            low_deltas.append(abs(c_low[0].combined - 0.65))
            high_deltas.append(abs(c_high[0].combined - 0.65))

        avg_low = sum(low_deltas) / len(low_deltas)
        avg_high = sum(high_deltas) / len(high_deltas)
        assert avg_high > avg_low


def _make_candidate(name: str, combined: float) -> SelectionCandidate:
    return SelectionCandidate(
        capability_name=name,
        similarity=combined,
        combined=combined,
        payload={},
    )
```

- [ ] **Step 18: Run tests to verify they fail**

Run: `cd hapax-council && uv run pytest tests/test_affordance_exploration_feedback.py -v`
Expected: FAIL — `_apply_exploration_noise` does not exist yet.

- [ ] **Step 19: Commit test file**

```bash
cd hapax-council && git add tests/test_affordance_exploration_feedback.py
git commit -m "test: exploration feedback into affordance scoring — boredom-proportional noise"
```

---

## Task 6: Exploration Feedback into Scoring — Implementation

**Files:**
- Modify: `shared/affordance_pipeline.py:285-384` (AffordancePipeline.select)

- [ ] **Step 20: Add _apply_exploration_noise function**

In `shared/affordance_pipeline.py`, add this function before the `AffordancePipeline` class (near the top, after the weight constants):

```python
def _apply_exploration_noise(
    candidates: list[SelectionCandidate],
    signal: ExplorationSignal | None,
    sigma_explore: float,
) -> None:
    """Apply boredom-proportional noise to candidate scores (15th control law).

    When boredom_index > 0.4, inject Gaussian noise scaled by
    sigma_explore * boredom_index. This disrupts monotonic winners
    without affecting focused states. Modifies candidates in-place.
    """
    if signal is None or signal.boredom_index <= 0.4:
        return
    noise_scale = sigma_explore * signal.boredom_index
    for c in candidates:
        c.combined += random.gauss(0, noise_scale)
```

Add `import random` and the `ExplorationSignal` import at the top of the file:

```python
import random

from shared.exploration import ExplorationSignal
```

- [ ] **Step 21: Wire exploration noise into select()**

In `shared/affordance_pipeline.py`, in the `select()` method, after the exploration signal is computed (after line 381 `self._exploration.compute_and_publish()`), add the noise application before returning survivors:

Replace the block at lines 370-384:
```python
        # Exploration signal
        source_hash = hash(impingement.source) % 100 / 100.0
        diversity = float(len(set(c.capability_name for c in candidates))) if candidates else 0.0
        self._exploration.feed_habituation(
            "impingement_source", source_hash, self._prev_source_hash, 0.3
        )
        self._exploration.feed_habituation("candidate_diversity", diversity, 0.0, 2.0)
        self._exploration.feed_interest("selection_frequency", float(len(survivors)), 1.0)
        spread = float(len(self._activation))
        self._exploration.feed_interest("activation_spread", spread, 5.0)
        self._exploration.feed_error(0.0 if survivors else 1.0)
        sig = self._exploration.compute_and_publish()
        self._prev_source_hash = source_hash

        return survivors
```

With:
```python
        # Exploration signal
        source_hash = hash(impingement.source) % 100 / 100.0
        diversity = float(len(set(c.capability_name for c in candidates))) if candidates else 0.0
        self._exploration.feed_habituation(
            "impingement_source", source_hash, self._prev_source_hash, 0.3
        )
        self._exploration.feed_habituation("candidate_diversity", diversity, 0.0, 2.0)
        self._exploration.feed_interest("selection_frequency", float(len(survivors)), 1.0)
        spread = float(len(self._activation))
        self._exploration.feed_interest("activation_spread", spread, 5.0)
        self._exploration.feed_error(0.0 if survivors else 1.0)
        sig = self._exploration.compute_and_publish()
        self._prev_source_hash = source_hash

        # 15th control law: boredom-proportional scoring noise
        _apply_exploration_noise(survivors, sig, self._exploration.sigma_explore)
        survivors.sort(key=lambda c: -c.combined)

        return survivors
```

- [ ] **Step 22: Run exploration feedback tests**

Run: `cd hapax-council && uv run pytest tests/test_affordance_exploration_feedback.py -v`
Expected: All 4 tests PASS.

- [ ] **Step 23: Run existing pipeline tests**

Run: `cd hapax-council && uv run pytest tests/test_affordance_pipeline.py -v`
Expected: All existing tests PASS.

- [ ] **Step 24: Commit**

```bash
cd hapax-council && git add shared/affordance_pipeline.py
git commit -m "fix(affordance): exploration feedback into scoring — 15th control law

Close the one-way exploration signal loop. When boredom_index > 0.4,
inject Gaussian noise (sigma_explore * boredom) into candidate scores.
Disrupts monotonic winner lock-on during habituated states. No effect
during focused engagement. Uses the existing sigma_explore parameter
from the exploration tracker spec."
```

---

## Task 7: Integration Verification

**Files:** None (verification only)

- [ ] **Step 25: Run full test suite for modified modules**

```bash
cd hapax-council && uv run pytest tests/test_content_resolver_diversity.py tests/test_satellite_habituation.py tests/test_affordance_exploration_feedback.py tests/test_satellite_recruitment.py tests/test_affordance_pipeline.py tests/test_content_resolver_daemon.py -v
```

Expected: All tests PASS.

- [ ] **Step 26: Run ruff check and format**

```bash
cd hapax-council && uv run ruff check agents/reverie/_content_resolvers.py agents/reverie/_content_capabilities.py agents/reverie/_satellites.py shared/affordance_pipeline.py && uv run ruff format agents/reverie/_content_resolvers.py agents/reverie/_content_capabilities.py agents/reverie/_satellites.py shared/affordance_pipeline.py
```

Expected: No errors.

- [ ] **Step 27: Run pyright on modified files**

```bash
cd hapax-council && uv run pyright agents/reverie/_content_resolvers.py agents/reverie/_content_capabilities.py agents/reverie/_satellites.py shared/affordance_pipeline.py
```

Expected: No type errors.

- [ ] **Step 28: Commit any lint fixes**

If ruff or pyright required changes:
```bash
cd hapax-council && git add -u && git commit -m "style: lint fixes for reverie diversity changes"
```
