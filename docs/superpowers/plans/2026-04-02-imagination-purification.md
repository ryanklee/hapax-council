# Imagination Purification Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove `content_references` from `ImaginationFragment` so imagination produces pure semantic intent. The narrative becomes the only recruitment query. Dimensions use the 9 canonical expressive names.

**Architecture:** The `ImaginationFragment` model drops `content_references` and renames dimension keys to canonical names (intensity, tension, depth, coherence, spectral_color, temporal_distortion, degradation, pitch_displacement, diffusion). The LLM system prompt changes from "name specific content sources" to "describe what you're imagining." All consumers that read `content_references` are updated to work without them. The `ContentReference` class is removed.

**Tech Stack:** Python 3.12, Pydantic v2, pydantic-ai, pytest

**Spec:** `docs/superpowers/specs/2026-04-02-unified-semantic-recruitment-design.md` §5

---

## File Map

| File | Action | Responsibility |
|------|--------|---------------|
| `agents/imagination.py` | Modify | Remove `ContentReference`, update `ImaginationFragment`, update `maybe_escalate()` |
| `agents/imagination_loop.py` | Modify | Update system prompt, remove content_references from context assembly |
| `agents/reverie/_uniforms.py` | Modify | `build_slot_opacities()` uses fragment salience instead of per-ref salience |
| `agents/reverie/mixer.py` | Modify | Remove `content_density` from content_references |
| `agents/hapax_daimonion/conversation_pipeline.py` | Modify | Remove ref_summary from imagination prompt |
| `tests/test_imagination.py` | Modify | Update all fragment fixtures, escalation assertions |
| `tests/test_imagination_context.py` | Modify | Remove content_references from fixtures |
| `tests/test_reverberation.py` | Modify | Remove content_references from fixtures |
| `tests/test_voice_imagination_wiring.py` | Modify | Remove content_references from fixtures, update assertions |
| `tests/test_stigmergic_chain.py` | Modify | Remove content_references from fixtures |
| `tests/test_content_resolver_daemon.py` | Modify | Remove content_references from fixtures |
| `tests/test_imagination_resolver.py` | Modify | Update escalation content assertions |

---

### Task 1: Update ImaginationFragment Model

**Files:**
- Modify: `agents/imagination.py:44-64`
- Test: `tests/test_imagination.py`

- [ ] **Step 1: Write the failing test for new fragment model**

In `tests/test_imagination.py`, add a test that verifies the new model has no `content_references` field and dimensions use canonical names:

```python
def test_fragment_has_no_content_references():
    """ImaginationFragment carries semantic intent only — no content_references."""
    frag = ImaginationFragment(
        narrative="The workspace hums with quiet focus",
        dimensions={"intensity": 0.3, "tension": 0.1, "depth": 0.5},
        salience=0.4,
        continuation=False,
        material="water",
    )
    assert not hasattr(frag, "content_references")
    dumped = frag.model_dump()
    assert "content_references" not in dumped
    assert "intensity" in frag.dimensions
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_imagination.py::test_fragment_has_no_content_references -v`
Expected: FAIL — `content_references` is still a required field on the model

- [ ] **Step 3: Update the model**

In `agents/imagination.py`, remove `ContentReference` class and update `ImaginationFragment`:

```python
# Remove the ContentReference class entirely (lines 44-50)

# The canonical 9 expressive dimensions
CANONICAL_DIMENSIONS = frozenset({
    "intensity", "tension", "depth", "coherence", "spectral_color",
    "temporal_distortion", "degradation", "pitch_displacement", "diffusion",
})


class ImaginationFragment(BaseModel, frozen=True):
    """A single imagination output — pure semantic intent."""

    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    timestamp: float = Field(default_factory=time_mod.time)
    dimensions: dict[str, float]  # canonical 9 expressive dimensions
    salience: float = Field(ge=0.0, le=1.0)
    continuation: bool
    narrative: str
    material: Literal["water", "fire", "earth", "air", "void"] = "water"
    parent_id: str | None = None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_imagination.py::test_fragment_has_no_content_references -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add agents/imagination.py tests/test_imagination.py
git commit -m "refactor(imagination): remove content_references from ImaginationFragment"
```

---

### Task 2: Update maybe_escalate() to Remove content_references from Impingement

**Files:**
- Modify: `agents/imagination.py:233-259`
- Test: `tests/test_imagination.py`

- [ ] **Step 1: Write the failing test**

```python
def test_escalation_impingement_has_no_content_references():
    """Escalated impingement carries narrative and dimensions, not content_references."""
    frag = ImaginationFragment(
        narrative="Something important is emerging",
        dimensions={"intensity": 0.8, "tension": 0.6},
        salience=0.9,
        continuation=False,
        material="fire",
    )
    # Force escalation by setting salience high
    imp = maybe_escalate(frag)
    # With salience=0.9, escalation probability is ~97%, but it's stochastic.
    # Run in a loop to ensure we get one.
    import random
    random.seed(42)
    imp = maybe_escalate(frag)
    assert imp is not None
    assert "narrative" in imp.content
    assert "dimensions" in imp.content
    assert "material" in imp.content
    assert "content_references" not in imp.content
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_imagination.py::test_escalation_impingement_has_no_content_references -v`
Expected: FAIL — `content_references` still in imp.content

- [ ] **Step 3: Update maybe_escalate()**

In `agents/imagination.py`, update the `maybe_escalate` function's impingement content:

```python
def maybe_escalate(fragment: ImaginationFragment) -> Impingement | None:
    """Probabilistic escalation — sigmoid around 0.55, boosted by continuation."""
    midpoint = 0.55
    steepness = 8.0
    probability = 1.0 / (1.0 + math.exp(-steepness * (fragment.salience - midpoint)))

    if fragment.continuation:
        probability = min(1.0, probability * 1.3)

    if random.random() > probability:
        return None

    return Impingement(
        id=fragment.id,
        timestamp=fragment.timestamp,
        source="imagination",
        type=ImpingementType.SALIENCE_INTEGRATION,
        strength=fragment.salience,
        content={
            "narrative": fragment.narrative,
            "continuation": fragment.continuation,
            "material": fragment.material,
            "dimensions": fragment.dimensions,
        },
        context={},
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_imagination.py::test_escalation_impingement_has_no_content_references -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add agents/imagination.py tests/test_imagination.py
git commit -m "refactor(imagination): remove content_references from escalated impingement"
```

---

### Task 3: Update System Prompt

**Files:**
- Modify: `agents/imagination_loop.py:34-69`
- Test: `tests/test_imagination_context.py`

- [ ] **Step 1: Write the failing test**

```python
def test_system_prompt_has_no_content_sources():
    """System prompt should not mention specific content sources."""
    from agents.imagination_loop import IMAGINATION_SYSTEM_PROMPT

    assert "camera_frame" not in IMAGINATION_SYSTEM_PROMPT
    assert "qdrant_query" not in IMAGINATION_SYSTEM_PROMPT
    assert "content_references" not in IMAGINATION_SYSTEM_PROMPT
    assert "Content sources you can reference" not in IMAGINATION_SYSTEM_PROMPT
    # Should mention dimensions
    assert "intensity" in IMAGINATION_SYSTEM_PROMPT
    assert "tension" in IMAGINATION_SYSTEM_PROMPT
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_imagination_context.py::test_system_prompt_has_no_content_sources -v`
Expected: FAIL — prompt still mentions camera_frame, qdrant_query

- [ ] **Step 3: Update the system prompt**

In `agents/imagination_loop.py`, replace `IMAGINATION_SYSTEM_PROMPT`:

```python
IMAGINATION_SYSTEM_PROMPT = """\
You are the imagination process of a personal computing system. You observe
the system's current state and produce spontaneous associations, memories,
projections, and novel connections — the way a human mind wanders during
idle moments.

Your output carries semantic intent only: a narrative describing what you
are imagining, expressive dimensions characterizing its quality, a material
quality, and a salience assessment. You do not decide how or where the
thought is expressed — that is handled by downstream recruitment. Focus on
WHAT you are imagining and WHY it matters.

## Material Quality
Each fragment has an elemental material that determines how it interacts
with the field:
- water: dissolving, flowing, reflective. For contemplative, fluid thoughts.
- fire: consuming, vertical, rapid. For urgent, transformative insights.
- earth: dense, persistent, resistant. For grounded, factual observations.
- air: translucent, drifting, dispersing. For light, fleeting associations.
- void: darkening, absorbing. For absence, loss, emptiness.
Choose the material that matches the character of your thought.

## Expressive Dimensions
Rate the fragment on the nine dimensions (0.0-1.0):
intensity, tension, depth, coherence, spectral_color,
temporal_distortion, degradation, pitch_displacement, diffusion.

Produce one ImaginationFragment. Assess salience honestly — most fragments
are low salience (0.1-0.3). Only mark high salience (>0.6) for genuine
insights or concerns worth escalating.

If your previous fragment had continuation=true, you may continue that
train of thought or let it go. Don't force continuation.\
"""
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_imagination_context.py::test_system_prompt_has_no_content_sources -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add agents/imagination_loop.py tests/test_imagination_context.py
git commit -m "refactor(imagination): system prompt produces intent not implementation"
```

---

### Task 4: Update build_slot_opacities() in Reverie Uniforms

**Files:**
- Modify: `agents/reverie/_uniforms.py:19-33`
- Modify: `agents/reverie/_uniforms.py:49-58` (update_trace)
- Test: `tests/test_reverie_mixer.py`

- [ ] **Step 1: Write the failing test**

```python
def test_slot_opacities_from_fragment_salience():
    """Slot opacities use fragment-level salience, not per-reference salience."""
    from agents.reverie._uniforms import build_slot_opacities

    # Fragment with salience but no content_references
    imagination = {"salience": 0.6}
    opacities = build_slot_opacities(imagination, fallback_salience=0.6)
    # Should produce uniform opacity from fragment salience
    assert opacities[0] == 0.6
    assert opacities[1] == 0.0  # only one slot active without recruitment


def test_slot_opacities_no_imagination():
    """No imagination → all zeros."""
    from agents.reverie._uniforms import build_slot_opacities

    opacities = build_slot_opacities(None, fallback_salience=0.0)
    assert opacities == [0.0, 0.0, 0.0, 0.0]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_reverie_mixer.py::test_slot_opacities_from_fragment_salience -v`
Expected: FAIL — current implementation reads content_references

- [ ] **Step 3: Update build_slot_opacities()**

In `agents/reverie/_uniforms.py`, replace `build_slot_opacities`:

```python
def build_slot_opacities(imagination: dict | None, fallback_salience: float) -> list[float]:
    """Build slot opacities from fragment salience (uniform, not per-reference)."""
    opacities = [0.0, 0.0, 0.0, 0.0]
    if not imagination:
        return opacities
    salience = float(imagination.get("salience", fallback_salience))
    if salience > 0:
        opacities[0] = salience
    return opacities
```

Also update `update_trace` to remove content_references access. In the same file, the `update_trace` function (around line 49-58) accesses `imagination.get("content_references", [])` for trace center selection. Replace:

```python
def update_trace(
    imagination: dict | None,
    last_salience: float,
    trace_strength: float,
    trace_radius: float,
    trace_center: tuple[float, float],
    trace_decay_rate: float,
    dt: float,
) -> tuple[float, float, float, tuple[float, float]]:
    """Update dwelling trace state. Returns (salience, strength, radius, center)."""
    current_salience = float(imagination.get("salience", 0.0)) if imagination else 0.0
    if last_salience > 0.2 and current_salience < last_salience * 0.5:
        trace_strength = min(1.0, last_salience)
        trace_radius = 0.3 + last_salience * 0.2
        trace_center = SLOT_CENTERS.get(0, (0.5, 0.5))
        log.info(
            "Trace: strength=%.2f radius=%.2f center=%s", trace_strength, trace_radius, trace_center
        )
    if trace_strength > 0:
        trace_strength = max(0.0, trace_strength - trace_decay_rate * dt)
    return current_salience, trace_strength, trace_radius, trace_center
```

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/test_reverie_mixer.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add agents/reverie/_uniforms.py tests/test_reverie_mixer.py
git commit -m "refactor(reverie): slot opacities from fragment salience, not per-reference"
```

---

### Task 5: Update Mixer and Conversation Pipeline

**Files:**
- Modify: `agents/reverie/mixer.py:185`
- Modify: `agents/hapax_daimonion/conversation_pipeline.py:200-212`

- [ ] **Step 1: Update mixer content_density**

In `agents/reverie/mixer.py`, line 185, replace:

```python
content_density = len(imagination.get("content_references", [])) if imagination else 0
```

with:

```python
content_density = 1 if imagination and imagination.get("salience", 0) > 0.1 else 0
```

- [ ] **Step 2: Update conversation pipeline**

In `agents/hapax_daimonion/conversation_pipeline.py`, around lines 200-212, replace:

```python
        if source == "imagination":
            narrative = content.get("narrative", "")
            refs = content.get("content_references", [])
            ref_summary = ", ".join(r.get("source", "") for r in refs[:3] if isinstance(r, dict))
            prompt = (
                "You just had a thought worth sharing with the operator. "
                "Express it naturally and concisely — 1-3 sentences. "
                "Don't announce that you had a thought; just share the insight "
                "as if continuing a natural conversation.\n\n"
                f"The thought: {narrative}"
            )
            if ref_summary:
                prompt += f"\nRelated context: {ref_summary}"
```

with:

```python
        if source == "imagination":
            narrative = content.get("narrative", "")
            prompt = (
                "You just had a thought worth sharing with the operator. "
                "Express it naturally and concisely — 1-3 sentences. "
                "Don't announce that you had a thought; just share the insight "
                "as if continuing a natural conversation.\n\n"
                f"The thought: {narrative}"
            )
```

- [ ] **Step 3: Run all affected tests**

Run: `uv run pytest tests/test_reverie_mixer.py tests/test_voice_imagination_wiring.py -v`
Expected: PASS (or test failures that we fix in Task 6)

- [ ] **Step 4: Commit**

```bash
git add agents/reverie/mixer.py agents/hapax_daimonion/conversation_pipeline.py
git commit -m "refactor: remove content_references from mixer and conversation pipeline"
```

---

### Task 6: Update All Test Fixtures

**Files:**
- Modify: `tests/test_imagination.py`
- Modify: `tests/test_reverberation.py`
- Modify: `tests/test_imagination_context.py`
- Modify: `tests/test_voice_imagination_wiring.py`
- Modify: `tests/test_stigmergic_chain.py`
- Modify: `tests/test_content_resolver_daemon.py`
- Modify: `tests/test_imagination_resolver.py`

- [ ] **Step 1: Update test_imagination.py fixtures**

Find every `ImaginationFragment(` or fixture dict containing `content_references` and remove the field. Replace `ContentReference` imports with nothing. Replace dimension color names with canonical names. Key patterns:

- Remove all `from agents.imagination import ContentReference` imports
- Remove `content_references=[ContentReference(...)]` from all fragment constructors
- Change `dimensions={"red": 0.3, "blue": 0.6}` to `dimensions={"intensity": 0.3, "depth": 0.6}`
- Update escalation tests: `assert "content_references" not in imp.content` replaces checks on content_references content

- [ ] **Step 2: Update test_reverberation.py fixtures**

Remove `"content_references": [...]` from all fixture dicts. These are raw dicts read from JSON, not model instances.

- [ ] **Step 3: Update test_imagination_context.py fixtures**

Remove `"content_references": []` from all fixture dicts.

- [ ] **Step 4: Update test_voice_imagination_wiring.py**

Remove `"content_references": [...]` from impingement content dicts. Remove assertion on `refs` variable that accessed content_references.

- [ ] **Step 5: Update test_stigmergic_chain.py**

Remove `"content_references"` from raw JSON dicts and assertions.

- [ ] **Step 6: Update test_content_resolver_daemon.py**

Remove `"content_references": []` from raw JSON dicts. These tests write to current.json — they should still work with the new model (just no content_references field).

- [ ] **Step 7: Update test_imagination_resolver.py**

Remove assertion `assert "content_references" in imp.content` (line 609). Update any fixture that constructs fragments with content_references.

- [ ] **Step 8: Run full test suite**

Run: `uv run pytest tests/test_imagination.py tests/test_reverberation.py tests/test_imagination_context.py tests/test_voice_imagination_wiring.py tests/test_stigmergic_chain.py tests/test_content_resolver_daemon.py tests/test_imagination_resolver.py tests/test_reverie_mixer.py tests/test_reverie_daemon.py tests/test_visual_chain.py -v`
Expected: ALL PASS

- [ ] **Step 9: Commit**

```bash
git add tests/
git commit -m "test: update all fixtures to remove content_references"
```

---

### Task 7: Run Full Test Suite and Lint

**Files:** None (verification only)

- [ ] **Step 1: Run full test suite**

Run: `uv run pytest tests/ -q --ignore=tests/test_llm_integration.py -x`
Expected: All pass (some pre-existing failures in exploration_hardening and compositor may persist — those are unrelated)

- [ ] **Step 2: Run linter**

Run: `uv run ruff check agents/imagination.py agents/imagination_loop.py agents/reverie/_uniforms.py agents/reverie/mixer.py agents/hapax_daimonion/conversation_pipeline.py`
Expected: All checks passed

- [ ] **Step 3: Run type checker**

Run: `uv run pyright agents/imagination.py agents/imagination_loop.py agents/reverie/_uniforms.py`
Expected: 0 errors

- [ ] **Step 4: Commit any lint/type fixes**

```bash
git add -A && git commit -m "chore: lint and type fixes for imagination purification"
```

---

### Task 8: Restart Daemons and Verify Live

**Files:** None (deployment verification)

- [ ] **Step 1: Restart imagination daemon**

```bash
systemctl --user restart hapax-imagination-loop.service
```

Wait 15s for the first tick. Check logs:
```bash
journalctl --user -u hapax-imagination-loop.service --since "30 sec ago" --no-pager | tail -5
```

Expected: No errors. Imagination produces fragments WITHOUT content_references.

- [ ] **Step 2: Verify fragment model on disk**

```bash
python3 -c "
import json
d = json.loads(open('/dev/shm/hapax-imagination/current.json').read())
assert 'content_references' not in d, 'FAIL: content_references still present'
assert 'narrative' in d, 'FAIL: narrative missing'
assert 'dimensions' in d, 'FAIL: dimensions missing'
print(f'OK: fragment has narrative, dimensions={list(d[\"dimensions\"].keys())}, material={d.get(\"material\")}')
"
```

Expected: `OK: fragment has narrative, dimensions=[intensity, tension, ...], material=water`

- [ ] **Step 3: Restart reverie daemon**

```bash
> /dev/shm/hapax-dmn/impingements.jsonl
systemctl --user restart hapax-reverie.service
```

Wait 20s. Check visual surface is still rendering:
```bash
stat /dev/shm/hapax-visual/frame.jpg | grep Modify
```

Expected: Frame is being written (recent modification time).

- [ ] **Step 4: Commit deployment verification note**

No code to commit — this is a manual verification step.
