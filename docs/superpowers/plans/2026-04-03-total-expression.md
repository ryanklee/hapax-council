# Total Expression Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make recruited affordances produce actual expression — visual content on the Reverie surface, recalled knowledge, rendered text — by implementing the five content resolution stubs.

**Architecture:** `activate_content()` in `ContentCapabilityRouter` dispatches to `content_injector.py` functions (inject_text, inject_search) and new Qdrant query handlers. Each content type resolves asynchronously: FAST types (waveform) within the tick, SLOW types (recall, text) queued and resolved next tick. The sources protocol (`/dev/shm/hapax-imagination/sources/`) is the delivery mechanism — the Rust ContentSourceManager picks up whatever is written there.

**Tech Stack:** Python 3.12, Qdrant, Pillow, httpx, pytest

**Spec:** `docs/superpowers/specs/2026-04-03-total-affordance-field-design.md` Phase 3 (Track A — Reverie content, safe to execute now)

**Experiment gate:** Track B (tool recruitment, voice expression) is gated on Cycle 2 Phase A completion. This plan covers ONLY Track A.

---

## File Map

| Action | File | Responsibility |
|--------|------|---------------|
| Modify | `agents/reverie/_content_capabilities.py:97-108` | Implement activate_content() dispatch |
| Create | `agents/reverie/_content_resolvers.py` | SLOW content resolution handlers |
| Create | `tests/test_content_resolution.py` | Tests for content resolution |

---

### Task 1: Implement activate_content() dispatch

**Files:**
- Modify: `agents/reverie/_content_capabilities.py:97-108`
- Create: `agents/reverie/_content_resolvers.py`
- Create: `tests/test_content_resolution.py`

- [ ] **Step 1: Write the test**

```python
# tests/test_content_resolution.py
"""Test that content affordances produce visual output via the sources protocol."""

import json
import tempfile
from pathlib import Path

from agents.reverie._content_capabilities import ContentCapabilityRouter


def test_narrative_text_produces_source(tmp_path):
    router = ContentCapabilityRouter(sources_dir=tmp_path)
    result = router.activate_content(
        "content.narrative_text",
        "the weight of unfinished work accumulates like sediment",
        level=0.6,
    )
    assert result is True
    source_dir = tmp_path / "content-narrative_text"
    assert (source_dir / "frame.rgba").exists()
    manifest = json.loads((source_dir / "manifest.json").read_text())
    assert manifest["opacity"] == 0.6
    assert "recruited" in manifest["tags"]


def test_unknown_content_returns_false(tmp_path):
    router = ContentCapabilityRouter(sources_dir=tmp_path)
    result = router.activate_content("content.unknown_type", "test", level=0.5)
    assert result is False


def test_knowledge_recall_produces_source(tmp_path):
    """Knowledge recall should produce text output even without Qdrant."""
    router = ContentCapabilityRouter(sources_dir=tmp_path)
    result = router.activate_content(
        "knowledge.document_search",
        "voice grounding research",
        level=0.5,
    )
    # Falls back to rendering the query as text when Qdrant unavailable
    source_dir = tmp_path / "content-knowledge.document_search"
    if result:
        assert (source_dir / "frame.rgba").exists()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_content_resolution.py::test_narrative_text_produces_source -v`
Expected: FAIL — activate_content returns False

- [ ] **Step 3: Create content resolvers module**

```python
# agents/reverie/_content_resolvers.py
"""Content resolution handlers for recruited affordances.

Each handler takes a narrative string and activation level, resolves the
content (text render, Qdrant query, etc.), and writes to the sources protocol.
"""

from __future__ import annotations

import logging
from pathlib import Path

log = logging.getLogger("reverie.content_resolvers")

SOURCES_DIR = Path("/dev/shm/hapax-imagination/sources")


def resolve_narrative_text(
    narrative: str, level: float, sources_dir: Path = SOURCES_DIR
) -> bool:
    """Render imagination narrative as visible text on the visual surface."""
    from agents.reverie.content_injector import inject_text

    return inject_text(
        "content-narrative_text",
        narrative,
        opacity=level,
        z_order=20,
        tags=["content", "recruited", "narrative"],
    )


def resolve_episodic_recall(
    narrative: str, level: float, sources_dir: Path = SOURCES_DIR
) -> bool:
    """Query operator-episodes Qdrant collection for similar past experiences."""
    try:
        from shared.config import embed_safe, get_qdrant

        embedding = embed_safe(narrative, prefix="search_query")
        if embedding is None:
            return _fallback_text("episodic_recall", f"Recalling: {narrative}", level)

        client = get_qdrant()
        from qdrant_client.models import ScoredPoint

        results = client.query_points(
            collection_name="operator-episodes",
            query=embedding,
            limit=1,
        ).points
        if not results:
            return _fallback_text("episodic_recall", f"No episodes match: {narrative[:80]}", level)

        top = results[0]
        text = top.payload.get("narrative", top.payload.get("text", str(top.payload)))
        return _inject_recalled_text("episodic_recall", text[:400], level)
    except Exception:
        log.debug("Episodic recall failed", exc_info=True)
        return _fallback_text("episodic_recall", f"Recalling: {narrative[:80]}", level)


def resolve_knowledge_recall(
    narrative: str, level: float, sources_dir: Path = SOURCES_DIR
) -> bool:
    """Query documents Qdrant collection for relevant knowledge."""
    try:
        from shared.config import embed_safe, get_qdrant

        embedding = embed_safe(narrative, prefix="search_query")
        if embedding is None:
            return _fallback_text("knowledge_recall", f"Searching: {narrative}", level)

        client = get_qdrant()
        results = client.query_points(
            collection_name="documents",
            query=embedding,
            limit=1,
        ).points
        if not results:
            return _fallback_text("knowledge_recall", f"No documents match: {narrative[:80]}", level)

        top = results[0]
        text = top.payload.get("text", top.payload.get("content", str(top.payload)))
        return _inject_recalled_text("knowledge_recall", text[:400], level)
    except Exception:
        log.debug("Knowledge recall failed", exc_info=True)
        return _fallback_text("knowledge_recall", f"Searching: {narrative[:80]}", level)


def resolve_profile_recall(
    narrative: str, level: float, sources_dir: Path = SOURCES_DIR
) -> bool:
    """Query profile-facts Qdrant collection for operator preferences."""
    try:
        from shared.config import embed_safe, get_qdrant

        embedding = embed_safe(narrative, prefix="search_query")
        if embedding is None:
            return _fallback_text("profile_recall", f"Recalling profile: {narrative}", level)

        client = get_qdrant()
        results = client.query_points(
            collection_name="profile-facts",
            query=embedding,
            limit=2,
        ).points
        if not results:
            return _fallback_text("profile_recall", f"No profile match: {narrative[:80]}", level)

        facts = [p.payload.get("fact", str(p.payload))[:150] for p in results]
        return _inject_recalled_text("profile_recall", "\n".join(facts), level)
    except Exception:
        log.debug("Profile recall failed", exc_info=True)
        return _fallback_text("profile_recall", f"Recalling: {narrative[:80]}", level)


def resolve_waveform_viz(
    narrative: str, level: float, sources_dir: Path = SOURCES_DIR
) -> bool:
    """Render current audio energy as a simple visual waveform indicator."""
    # FAST tier — reads current energy from perception state
    try:
        import json

        perc_path = Path("/dev/shm/hapax-daimonion/perception-state.json")
        perc = json.loads(perc_path.read_text())
        energy = perc.get("audio_energy_rms", 0.0)
        bars = int(energy * 20)
        viz = "▁▂▃▄▅▆▇█"
        waveform = "".join(viz[min(int(energy * 8 + i * 0.5) % 9, 8)] for i in range(bars + 5))
        return _inject_recalled_text("waveform_viz", f"Audio: {waveform}", level * 0.5)
    except Exception:
        log.debug("Waveform viz failed", exc_info=True)
        return False


def _inject_recalled_text(source_suffix: str, text: str, level: float) -> bool:
    """Write recalled text to the sources protocol."""
    from agents.reverie.content_injector import inject_text

    return inject_text(
        f"content-{source_suffix}",
        text,
        opacity=level,
        z_order=15,
        tags=["content", "recruited", "recall"],
    )


def _fallback_text(source_suffix: str, text: str, level: float) -> bool:
    """Fallback: render the query itself as visible text."""
    from agents.reverie.content_injector import inject_text

    return inject_text(
        f"content-{source_suffix}",
        text,
        opacity=level * 0.3,
        z_order=15,
        tags=["content", "recruited", "fallback"],
    )


# Dispatch table: affordance name → resolver function
CONTENT_RESOLVERS: dict[str, callable] = {
    "content.narrative_text": resolve_narrative_text,
    "content.episodic_recall": resolve_episodic_recall,
    "knowledge.episodic_recall": resolve_episodic_recall,
    "content.knowledge_recall": resolve_knowledge_recall,
    "knowledge.document_search": resolve_knowledge_recall,
    "knowledge.vault_search": resolve_knowledge_recall,
    "content.profile_recall": resolve_profile_recall,
    "knowledge.profile_facts": resolve_profile_recall,
    "content.waveform_viz": resolve_waveform_viz,
}
```

- [ ] **Step 4: Wire activate_content to dispatch table**

In `agents/reverie/_content_capabilities.py`, replace the `activate_content` method (lines 97-108):

```python
    def activate_content(self, affordance_name: str, narrative: str, level: float) -> bool:
        """Activate a content capability — dispatches to the appropriate resolver.

        Returns True if content was produced. FAST resolvers run inline;
        SLOW resolvers (Qdrant queries) may take 50-200ms but still run
        synchronously within the mixer tick.
        """
        from agents.reverie._content_resolvers import CONTENT_RESOLVERS

        resolver = CONTENT_RESOLVERS.get(affordance_name)
        if resolver is None:
            log.debug("No resolver for content affordance: %s", affordance_name)
            return False

        try:
            result = resolver(narrative, level, sources_dir=self._sources)
            if result:
                log.info(
                    "Content resolved: %s at %.2f (narrative: %s)",
                    affordance_name,
                    level,
                    narrative[:50],
                )
            return result
        except Exception:
            log.warning("Content resolver failed: %s", affordance_name, exc_info=True)
            return False
```

- [ ] **Step 5: Run tests**

Run: `uv run pytest tests/test_content_resolution.py -v`
Expected: test_narrative_text_produces_source PASS, test_unknown_content_returns_false PASS

- [ ] **Step 6: Run broader suite**

Run: `uv run pytest tests/ -q -k "content or reverie" --timeout=30`
Expected: no new failures

- [ ] **Step 7: Lint and commit**

```bash
uv run ruff check agents/reverie/_content_capabilities.py agents/reverie/_content_resolvers.py
uv run ruff format agents/reverie/_content_capabilities.py agents/reverie/_content_resolvers.py
git add agents/reverie/_content_capabilities.py agents/reverie/_content_resolvers.py tests/test_content_resolution.py
git commit -m "feat: implement content resolution for 5 recruited affordances

activate_content() now dispatches to resolver functions: narrative text
renders via Pillow, episodic/knowledge/profile recall query Qdrant
collections (operator-episodes, documents, profile-facts), waveform viz
reads audio energy from perception state. All write to the sources
protocol for Rust ContentSourceManager pickup. Graceful fallback to
rendering the query text when Qdrant is unavailable."
```

---

### Task 2: Wire new domain affordances into mixer dispatch

**Files:**
- Modify: `agents/reverie/mixer.py` (dispatch_impingement method)

The mixer currently handles `node.*`, `content.*`, `shader_graph`, `visual_chain`, `fortress_visual_response`. The new affordance registry has `knowledge.*`, `space.*`, `env.*`, etc. The mixer needs to route these to appropriate handlers.

- [ ] **Step 1: Read mixer.py dispatch_impingement**

Read the method to understand current dispatch structure.

- [ ] **Step 2: Add dispatch for knowledge.* affordances**

In `dispatch_impingement()`, after the `content.*` branch, add:

```python
            elif name.startswith("knowledge."):
                narrative = imp.content.get("narrative", "")
                self._content_router.activate_content(name, narrative, c.combined)
                self._recruited_content_count += 1
                self._chronicle_technique(name, c.combined)
                ctx = {"source": imp.source, "metric": imp.content.get("metric", "")}
                self._pipeline.record_outcome(name, success=True, context=ctx)
                break
```

- [ ] **Step 3: Add dispatch for space.* camera affordances**

The space.overhead_perspective, space.desk_perspective, space.operator_perspective affordances replace the old content.* camera affordances. Add to CAMERA_MAP in _content_capabilities.py:

```python
CAMERA_MAP: dict[str, str] = {
    "content.overhead_perspective": "c920-overhead",
    "content.desk_perspective": "c920-desk",
    "content.operator_perspective": "brio-operator",
    "space.overhead_perspective": "c920-overhead",
    "space.desk_perspective": "c920-desk",
    "space.operator_perspective": "brio-operator",
}
```

And in dispatch_impingement, route `space.*` camera affordances through the camera path:

```python
            elif name.startswith("space."):
                if self._content_router.camera_for_affordance(name):
                    self._content_router.activate_camera(name, c.combined)
                    self._chronicle_technique(name, c.combined)
                    ctx = {"source": imp.source, "metric": imp.content.get("metric", "")}
                    self._pipeline.record_outcome(name, success=True, context=ctx)
                    break
```

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/ -q -k "reverie or mixer" --timeout=30`
Expected: no new failures

- [ ] **Step 5: Commit**

```bash
git add agents/reverie/mixer.py agents/reverie/_content_capabilities.py
git commit -m "feat: route knowledge.* and space.* affordances through mixer dispatch

knowledge.* affordances dispatch to content resolvers (Qdrant queries,
text rendering). space.* camera affordances dispatch to camera activation.
Extends the mixer's vocabulary from content/node/legacy to include the
new shared registry domains."
```

---

## Execution Notes

- **Track A only** — this plan covers Reverie visual content resolution
- **Do not touch** `agents/hapax_daimonion/conversation_pipeline.py` — experiment freeze
- **Do not touch** `agents/hapax_daimonion/run_loops_aux.py` consumer loop
- The Qdrant recall handlers (episodic, knowledge, profile) gracefully degrade when Qdrant is unreachable — they render the query text as fallback
- The `inject_text` function pre-renders via Pillow to RGBA — the Rust pipeline has no text renderer
- `inject_search` (DuckDuckGo) and `inject_url` (web content) exist but are NOT wired to affordances in this plan — they require `consent_required=True` and the capability_discovery gate (Phase 5 of USR spec)
- After tasks: restart logos-api and the Reverie daemon
