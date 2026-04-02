# Exploration Signal System Fixes — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix 4 systemic defects that render the exploration signal system's curiosity index, SEEKING stance, and DMN escalation cascade inert.

**Architecture:** All changes are in existing files. The core fix is changing `CoherenceTracker.local_coherence()` to return 0.5 instead of 0.0 when no phase data exists, preventing curiosity from saturating at 1.0. Secondary fixes: eliminate dual-writer problem in VLA process, wire real error signals into two components that hardcode 0.0, and add ExplorationTrackerBundle to SalienceRouter.

**Tech Stack:** Python 3.12, pytest, shared/exploration.py, agents/hapax_daimonion/

---

### Task 1: Fix Curiosity Saturation — CoherenceTracker Default

**Problem:** `CoherenceTracker.local_coherence()` returns 0.0 when no phases are fed. The curiosity formula includes `1.0 - local_coherence`, so "no data" = 1.0 curiosity. Every component has curiosity pegged at 1.0 because none feed phase data.

**Files:**
- Modify: `shared/exploration.py:201-203`
- Test: `tests/test_exploration.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_exploration.py` in `TestCoherenceTracker`:

```python
def test_no_phases_returns_unknown_coherence(self) -> None:
    """Empty phases = unknown, not desynchronized."""
    ct = CoherenceTracker(neighbors=["a", "b", "c"])
    # No update_phases() call — unknown state
    assert ct.local_coherence() == 0.5
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_exploration.py::TestCoherenceTracker::test_no_phases_returns_unknown_coherence -v`
Expected: FAIL — `assert 0.0 == 0.5`

- [ ] **Step 3: Write the curiosity index test**

Add to `tests/test_exploration.py` in `TestComputeCuriosityIndex`:

```python
def test_unknown_coherence_does_not_saturate_curiosity(self) -> None:
    """When coherence is unknown (0.5), curiosity should not be 1.0 unless novelty/reorg says so."""
    ci = compute_curiosity_index(
        chronic_error=0.0,
        error_improvement_rate=0.0,
        max_novelty_score=0.3,
        local_coherence=0.5,
    )
    assert ci == 0.5  # desync term = 1.0 - 0.5 = 0.5, max(0, 0.3, 0.5) = 0.5
```

- [ ] **Step 4: Run test to verify it passes** (this test already works with correct `local_coherence=0.5` input)

Run: `uv run pytest tests/test_exploration.py::TestComputeCuriosityIndex::test_unknown_coherence_does_not_saturate_curiosity -v`
Expected: PASS (this tests the formula directly with 0.5 input — the formula itself is correct)

- [ ] **Step 5: Fix `CoherenceTracker.local_coherence()`**

In `shared/exploration.py:201-203`, change:

```python
def local_coherence(self) -> float:
    if not self._phases:
        return 0.0
```

to:

```python
def local_coherence(self) -> float:
    if not self._phases:
        return 0.5  # Unknown coherence, not desynchronized
```

- [ ] **Step 6: Run all coherence and curiosity tests**

Run: `uv run pytest tests/test_exploration.py::TestCoherenceTracker tests/test_exploration.py::TestComputeCuriosityIndex -v`
Expected: ALL PASS

- [ ] **Step 7: Run full exploration test suite**

Run: `uv run pytest tests/test_exploration.py tests/test_exploration_control_law.py tests/test_exploration_stimmung.py tests/test_exploration_hardening.py -v`
Expected: ALL PASS. If any test assumed `local_coherence=0.0` as default, update that test to match the new 0.5 default.

- [ ] **Step 8: Commit**

```bash
git add shared/exploration.py tests/test_exploration.py
git commit -m "fix(exploration): default coherence to 0.5 when no phase data

CoherenceTracker.local_coherence() returned 0.0 (fully desynchronized)
when no phases were fed, causing curiosity_index to saturate at 1.0 on
every component. This made SEEKING stance, UNDIRECTED exploration, and
the entire DMN escalation cascade inert.

Change default to 0.5 (unknown coherence) so the desync term contributes
0.5 instead of 1.0, allowing other curiosity drivers (novelty, reorg)
to dominate when appropriate."
```

---

### Task 2: Fix Dual-Writer Problem — VLA StimmungCollector and TemporalBandFormatter

**Problem:** Both the VLA process and daimonion process instantiate `StimmungCollector` and `TemporalBandFormatter`, each creating `ExplorationTrackerBundle` with the same component names. Two processes, two cooldowns, interleaved to ~15s instead of 30s. `/dev/shm` files get last-write-wins.

**Files:**
- Modify: `shared/stimmung.py:172,194-205,444-452`
- Modify: `agents/temporal_bands.py:51-65,139-150`
- Modify: `agents/visual_layer_aggregator/aggregator.py:145,159`
- Test: `tests/test_exploration_wiring.py`

- [ ] **Step 1: Write tests for the enable_exploration flag**

Add to `tests/test_exploration_wiring.py`:

```python
class TestExplorationGuard:
    def test_stimmung_collector_default_has_exploration(self) -> None:
        from shared.stimmung import StimmungCollector
        sc = StimmungCollector()
        assert sc._exploration is not None

    def test_stimmung_collector_disabled_exploration(self) -> None:
        from shared.stimmung import StimmungCollector
        sc = StimmungCollector(enable_exploration=False)
        assert sc._exploration is None

    def test_temporal_formatter_default_has_exploration(self) -> None:
        from agents.temporal_bands import TemporalBandFormatter
        tf = TemporalBandFormatter()
        assert tf._exploration is not None

    def test_temporal_formatter_disabled_exploration(self) -> None:
        from agents.temporal_bands import TemporalBandFormatter
        tf = TemporalBandFormatter(enable_exploration=False)
        assert tf._exploration is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_exploration_wiring.py::TestExplorationGuard -v`
Expected: FAIL — `__init__() got an unexpected keyword argument 'enable_exploration'`

- [ ] **Step 3: Add `enable_exploration` param to `StimmungCollector`**

In `shared/stimmung.py`, modify `StimmungCollector.__init__` signature (around line 172) and the exploration block (lines 194-205):

Change class docstring and `__init__`:

```python
class StimmungCollector:
    """Collects raw readings and produces SystemStimmung snapshots.

    Pure logic — no I/O. Callers feed in data via update_*() methods,
    then call snapshot() to get the current state.

    Args:
        enable_exploration: If False, skip ExplorationTrackerBundle creation.
            Set to False when this collector is a secondary instance (e.g., in
            VLA) to prevent dual-writer interference on /dev/shm.
    """

    def __init__(self, *, enable_exploration: bool = True) -> None:
```

Replace the exploration block:

```python
        # Exploration tracking (spec §8: kappa=0.005, T_patience=600s)
        self._exploration: ExplorationTrackerBundle | None = None
        if enable_exploration:
            from shared.exploration_tracker import ExplorationTrackerBundle

            self._exploration = ExplorationTrackerBundle(
                component="stimmung",
                edges=["stance_changes", "dimension_freshness"],
                traces=["overall_stance", "dimension_count"],
                neighbors=["dmn_pulse", "imagination"],
                kappa=0.005,
                t_patience=600.0,
                sigma_explore=0.02,
            )
        self._prev_stance_val: float = 0.0
```

Guard the exploration calls in the snapshot method (around line 444-452):

```python
        if self._exploration is not None:
            self._exploration.feed_habituation("stance_changes", stance_val, self._prev_stance_val, 0.1)
            self._exploration.feed_habituation(
                "dimension_freshness", float(fresh_count), float(len(dimensions)), 1.0
            )
            self._exploration.feed_interest("overall_stance", stance_val, 0.1)
            self._exploration.feed_interest("dimension_count", float(fresh_count), 1.0)
            self._exploration.feed_error(0.0 if stance in ("nominal", "seeking") else 0.5)
            self._exploration.compute_and_publish()
        self._prev_stance_val = stance_val
```

- [ ] **Step 4: Add `enable_exploration` param to `TemporalBandFormatter`**

In `agents/temporal_bands.py`, modify `__init__` (line 51):

```python
    def __init__(
        self,
        protention_engine: ProtentionEngine | None = None,
        *,
        enable_exploration: bool = True,
    ) -> None:
        self._protention_engine = protention_engine
        self._last_protention: list[ProtentionEntry] = []
        self._exploration: ExplorationTrackerBundle | None = None
        if enable_exploration:
            from shared.exploration_tracker import ExplorationTrackerBundle

            self._exploration = ExplorationTrackerBundle(
                component="temporal_bands",
                edges=["snapshot_content", "surprise_level"],
                traces=["perception_freshness", "protention_accuracy"],
                neighbors=["stimmung", "dmn_pulse"],
                kappa=0.010,
                t_patience=360.0,
                sigma_explore=0.08,
            )
        self._prev_snapshot_hash: float = 0.0
```

Guard the exploration block in `format()` (around lines 139-150):

```python
        # Exploration signal
        if self._exploration is not None:
            snap_hash = hash(str(current.get("activity", ""))) % 100 / 100.0
            surprise_total = sum(s.surprise for s in surprises) if surprises else 0.0
            self._exploration.feed_habituation(
                "snapshot_content", snap_hash, self._prev_snapshot_hash, 0.3
            )
            self._exploration.feed_habituation("surprise_level", surprise_total, 0.0, 0.2)
            self._exploration.feed_interest("perception_freshness", 1.0, 0.3)
            self._exploration.feed_interest("protention_accuracy", 1.0 - min(surprise_total, 1.0), 0.3)
            self._exploration.feed_error(min(surprise_total, 1.0))
            self._exploration.compute_and_publish()
            self._prev_snapshot_hash = snap_hash
```

Note: This also fixes temporal_bands `feed_error` by using `min(surprise_total, 1.0)` instead of hardcoded `0.0`. High surprise = high prediction error = real L3 signal.

- [ ] **Step 5: Pass `enable_exploration=False` in VLA**

In `agents/visual_layer_aggregator/aggregator.py`, line 145:

```python
        self._stimmung_collector = StimmungCollector(enable_exploration=False)
```

Line 159:

```python
        self._temporal_formatter = TemporalBandFormatter(
            protention_engine=self._protention, enable_exploration=False
        )
```

- [ ] **Step 6: Run tests**

Run: `uv run pytest tests/test_exploration_wiring.py::TestExplorationGuard tests/test_exploration_stimmung.py -v`
Expected: ALL PASS

- [ ] **Step 7: Commit**

```bash
git add shared/stimmung.py agents/temporal_bands.py agents/visual_layer_aggregator/aggregator.py tests/test_exploration_wiring.py
git commit -m "fix(exploration): prevent dual-writer on stimmung and temporal_bands

VLA process instantiated StimmungCollector and TemporalBandFormatter
with their own ExplorationTrackerBundles, creating a second writer for
the same /dev/shm component files. Two 30s cooldowns interleaved to
~15s emission intervals.

Add enable_exploration param (default True). VLA passes False since it
is a secondary consumer, not the canonical producer. Also wires
temporal_bands feed_error to surprise_total instead of hardcoded 0.0."
```

---

### Task 3: Wire voice_state `feed_error` to Cognitive Readiness

**Problem:** `CognitiveLoop.contribute()` calls `feed_error(0.0)` unconditionally. L3 learning progress is always zero for voice_state.

**Files:**
- Modify: `agents/hapax_daimonion/cognitive_loop.py:192`

- [ ] **Step 1: Fix the feed_error call**

In `agents/hapax_daimonion/cognitive_loop.py`, line 192, change:

```python
        self._exploration.feed_error(0.0)
```

to:

```python
        self._exploration.feed_error(1.0 - self._cognitive_readiness)
```

This mirrors the pattern used by ir_presence (`1.0 - freshness`) and input_activity (`0.0 if active else 0.5`). Low cognitive readiness = high error signal = something needs attention.

- [ ] **Step 2: Run existing tests**

Run: `uv run pytest tests/ -k "cognitive_loop or exploration" -v --timeout=30`
Expected: ALL PASS

- [ ] **Step 3: Commit**

```bash
git add agents/hapax_daimonion/cognitive_loop.py
git commit -m "fix(exploration): wire voice_state L3 error to cognitive readiness

Was hardcoded 0.0. Now feeds 1.0 - cognitive_readiness so L3 learning
progress reflects actual voice session health."
```

---

### Task 4: Add ExplorationTrackerBundle to SalienceRouter

**Problem:** SalienceRouter has `set_seeking()` for SEEKING stance modulation but no ExplorationTrackerBundle. It cannot report its own boredom/curiosity state to the mesh.

**Files:**
- Modify: `agents/hapax_daimonion/salience_router.py:98,263`
- Test: `tests/test_exploration_wiring.py`

- [ ] **Step 1: Write the test**

Add to `tests/test_exploration_wiring.py`:

```python
class TestSalienceRouterExploration:
    def test_salience_router_has_exploration_tracker(self) -> None:
        from unittest.mock import MagicMock

        from agents.hapax_daimonion.salience_router import SalienceRouter

        embedder = MagicMock()
        concern_graph = MagicMock()
        concern_graph.anchor_count = 0

        router = SalienceRouter(embedder, concern_graph)
        assert router._exploration is not None
        assert router._exploration.component == "salience_router"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_exploration_wiring.py::TestSalienceRouterExploration -v`
Expected: FAIL — `AttributeError: 'SalienceRouter' object has no attribute '_exploration'`

- [ ] **Step 3: Add ExplorationTrackerBundle to SalienceRouter.__init__**

In `agents/hapax_daimonion/salience_router.py`, add after line 98 (`self._seeking: bool = False`):

```python
        # Exploration tracking (spec §8: kappa=0.012, T_patience=300s)
        from shared.exploration_tracker import ExplorationTrackerBundle

        self._exploration = ExplorationTrackerBundle(
            component="salience_router",
            edges=["concern_overlap", "activation_level"],
            traces=["novelty_signal", "tier_selection"],
            neighbors=["stimmung", "dmn_pulse"],
            kappa=0.012,
            t_patience=300.0,
            sigma_explore=0.10,
        )
        self._prev_activation: float = 0.0
        self._prev_novelty: float = 0.0
```

- [ ] **Step 4: Wire exploration feeds in `route()`**

In `agents/hapax_daimonion/salience_router.py`, add after the `self._add_recent_turn(transcript)` line (line 263), before `self._concern_graph.add_recent_utterance(utt_vec)`:

```python
        # Exploration signal
        self._exploration.feed_habituation(
            "concern_overlap", concern_overlap, self._prev_activation, 0.2
        )
        self._exploration.feed_habituation(
            "activation_level", activation, self._prev_activation, 0.1
        )
        self._exploration.feed_interest("novelty_signal", novelty, 0.2)
        self._exploration.feed_interest("tier_selection", float(tier.value) / 4.0, 0.3)
        self._exploration.feed_error(1.0 - activation)
        self._exploration.compute_and_publish()
        self._prev_activation = activation
        self._prev_novelty = novelty
```

`feed_error(1.0 - activation)`: low activation = high error (the router isn't finding salient content).

- [ ] **Step 5: Run tests**

Run: `uv run pytest tests/test_exploration_wiring.py::TestSalienceRouterExploration tests/test_exploration_wiring.py -v`
Expected: ALL PASS

- [ ] **Step 6: Commit**

```bash
git add agents/hapax_daimonion/salience_router.py tests/test_exploration_wiring.py
git commit -m "feat(exploration): add ExplorationTrackerBundle to SalienceRouter

Wires the salience router as the 13th active exploration component.
Tracks concern_overlap and activation_level habituation, novelty and
tier selection interest, and 1.0-activation as L3 error. Spec §8
params: kappa=0.012, T_patience=300s, sigma_explore=0.10."
```

---

### Task 5: Verify and Validate

**Files:** None (validation only)

- [ ] **Step 1: Run full test suite**

Run: `uv run pytest tests/test_exploration*.py -v`
Expected: ALL PASS

- [ ] **Step 2: Run ruff**

Run: `uv run ruff check shared/exploration.py shared/stimmung.py agents/temporal_bands.py agents/hapax_daimonion/cognitive_loop.py agents/hapax_daimonion/salience_router.py agents/visual_layer_aggregator/aggregator.py`
Expected: Clean

- [ ] **Step 3: Run pyright on modified files**

Run: `uv run pyright shared/exploration.py shared/stimmung.py agents/temporal_bands.py agents/hapax_daimonion/cognitive_loop.py agents/hapax_daimonion/salience_router.py`
Expected: No new errors

- [ ] **Step 4: Restart affected services and verify /dev/shm**

After deploying, verify:

```bash
# Wait ~60s after service restart, then check:
# 1. curiosity_index should NOT be 1.0 on all components
curl -s http://localhost:8051/api/exploration | python3 -c "
import sys, json
d = json.load(sys.stdin)
for name, comp in d['components'].items():
    ci = comp['curiosity_index']
    bi = comp['boredom_index']
    print(f'{name}: boredom={bi:.3f} curiosity={ci:.3f}')
print()
agg = d['aggregate']
print(f'Aggregate: boredom={agg[\"boredom\"]:.3f} curiosity={agg[\"curiosity\"]:.3f}')
print(f'Exploration deficit: {agg[\"exploration_deficit\"]:.3f}')
print(f'SEEKING: {agg[\"seeking\"]}')
"

# 2. No duplicate stimmung or temporal_bands emissions
wc -l /dev/shm/hapax-dmn/impingements.jsonl

# 3. salience_router.json should appear
ls /dev/shm/hapax-exploration/salience_router.json
```
