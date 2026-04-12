# Reactor Context Enrichment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enrich director LLM prompts with phenomenal context, TOON-format system state, proper reaction threading, and Claude Opus intelligence.

**Architecture:** Refactor `_build_unified_prompt()` in `director_loop.py` to assemble 4 context layers per the approved spec. Switch model from `gemini-flash` to `balanced` (Claude Opus). The director loop already has partial implementations of all 4 sources — this plan formalizes and completes them.

**Tech Stack:** Python, LiteLLM (`balanced` route), `shared/context.py` (ContextAssembler), `shared/context_compression.py` (to_toon), `agents/hapax_daimonion/phenomenal_context.py`

**Spec:** `docs/superpowers/specs/2026-04-10-reactor-context-enrichment-design.md`

---

### Task 1: Upgrade phenomenal context tier

**Files:**
- Modify: `agents/studio_compositor/director_loop.py:497-505`

The director currently calls `render_phenomenal(tier="LOCAL")` which returns ~60 tokens (layers 1-3 only). The spec requires `tier="FAST"` which returns ~200 tokens (all layers except full narrative).

- [ ] **Step 1: Change tier from LOCAL to FAST**

In `_build_unified_prompt()`, change:
```python
phenom = render_phenomenal(tier="LOCAL")  # LOCAL = layers 1-3 only, ~60 tokens
```
to:
```python
phenom = render_phenomenal(tier="FAST")  # ~200 tokens: stimmung, temporal, situation, surprises
```

- [ ] **Step 2: Verify phenomenal context renders**

Run: `uv run python -c "from agents.hapax_daimonion.phenomenal_context import render; print(render(tier='FAST'))"`

Expected: Multi-line block with stimmung, temporal bands, situation coupling. ~200 tokens.

- [ ] **Step 3: Commit**

```bash
git add agents/studio_compositor/director_loop.py
git commit -m "feat(director): upgrade phenomenal context to FAST tier (~200 tokens)"
```

---

### Task 2: Switch to TOON-format enrichment context

**Files:**
- Modify: `agents/studio_compositor/director_loop.py:475-494`

The director currently does ad-hoc field extraction from `ContextAssembler.snapshot()`. The spec requires using `to_toon()` format for ~40% token savings.

- [ ] **Step 1: Replace ad-hoc extraction with to_toon()**

Replace the current enrichment block (lines 475-494):
```python
# Current: ad-hoc extraction
try:
    from shared.context import ContextAssembler

    ctx = ContextAssembler().snapshot()
    if ctx.stimmung_stance != "nominal":
        parts.append(f"\nSystem stance: {ctx.stimmung_stance}.")
    if ctx.dmn_observations:
        parts.append(f"DMN: {ctx.dmn_observations[0][:150]}")
    if ctx.imagination_fragments:
        frag = ctx.imagination_fragments[0]
        dims = frag.get("dimensions", {})
        active = [f"{k}={v:.1f}" for k, v in dims.items() if v > 0.1]
        if active:
            parts.append(f"Imagination: {', '.join(active)}")
        mat = frag.get("material")
        if mat:
            parts.append(f"Material: {mat}")
except Exception:
    pass
```

With:
```python
# TOON-format enrichment (~150 tokens, 40% savings over JSON)
try:
    from shared.context import ContextAssembler
    from shared.context_compression import to_toon

    ctx = ContextAssembler().snapshot()
    toon_block = to_toon(ctx)
    if toon_block:
        parts.append("\n## System State")
        parts.append(toon_block)
except Exception:
    pass
```

- [ ] **Step 2: Verify TOON output format**

Run: `uv run python -c "from shared.context import ContextAssembler; from shared.context_compression import to_toon; print(to_toon(ContextAssembler().snapshot()))"`

Expected: Compact TOON string with stimmung, DMN, imagination, perception.

- [ ] **Step 3: Commit**

```bash
git add agents/studio_compositor/director_loop.py
git commit -m "feat(director): switch enrichment context to TOON format (~40% token savings)"
```

---

### Task 3: Expand reaction history to 8 entries

**Files:**
- Modify: `agents/studio_compositor/director_loop.py:542-545`

Currently shows last 5 reactions. Spec requires last 8.

- [ ] **Step 1: Change history display from 5 to 8**

Change:
```python
for entry in self._reaction_history[-5:]:
```
to:
```python
for entry in self._reaction_history[-8:]:
```

- [ ] **Step 2: Update section header**

Change:
```python
parts.append("\nYour recent utterances:")
```
to:
```python
parts.append("\n## Recent Reactions")
```

- [ ] **Step 3: Commit**

```bash
git add agents/studio_compositor/director_loop.py
git commit -m "feat(director): expand reaction history to 8 entries"
```

---

### Task 4: Restructure prompt to spec format

**Files:**
- Modify: `agents/studio_compositor/director_loop.py:456-550` (`_build_unified_prompt`)

The spec defines a specific `<reactor_context>` prompt structure. Restructure the prompt to match.

- [ ] **Step 1: Rewrite prompt builder to spec structure**

Restructure `_build_unified_prompt()` to emit:
```
<reactor_context>
You are the daimonion — the persistent cognitive substrate of the Hapax system.
{situation block — videos, music, overlays}

## Phenomenal Context
{render(tier="FAST") output}

## System State
{to_toon(ContextAssembler.snapshot())}

## Recent Reactions
- [HH:MM] activity: "text"
{...last 8}

YOUR ROLE: ...
RESPONSE FORMAT: {"activity": "chosen_activity", "react": "your words"}
</reactor_context>
```

Keep the existing situation block content (video info, album info, chat state, time) but move it inside the `<reactor_context>` tags and label the sections.

- [ ] **Step 2: Verify prompt renders correctly**

Add temporary debug logging to see the full prompt at startup.

- [ ] **Step 3: Commit**

```bash
git add agents/studio_compositor/director_loop.py
git commit -m "feat(director): restructure prompt to reactor_context spec format"
```

---

### Task 5: Switch model from gemini-flash to balanced (Claude Opus)

**Files:**
- Modify: `agents/studio_compositor/director_loop.py:736` and `director_loop.py:909`

Per intelligence-first commitment: "always CAPABLE; intelligence is last thing shed."

- [ ] **Step 1: Update model in _call_activity_llm()**

Change line 736:
```python
{"model": "gemini-flash", "messages": messages, "max_tokens": 2048, "temperature": 0.7}
```
to:
```python
{"model": "balanced", "messages": messages, "max_tokens": 300, "temperature": 0.7}
```

Note: `max_tokens` drops from 2048 to 300 per the spec's token budget.

- [ ] **Step 2: Update model in _call_llm() (legacy path)**

Change line 909:
```python
"model": "gemini-flash",
```
to:
```python
"model": "balanced",
```

Also update `max_tokens` from 2048 to 300.

- [ ] **Step 3: Verify LiteLLM routes balanced to Claude Opus**

Run: `curl -s http://localhost:4000/v1/models | python3 -c "import sys,json; models=json.load(sys.stdin)['data']; [print(m['id']) for m in models if 'balanced' in m['id']]"`

Expected: `balanced` model exists in LiteLLM config.

- [ ] **Step 4: Test the full prompt with a dry run**

Run: `uv run python -c "
from agents.studio_compositor.director_loop import DirectorLoop
from agents.studio_compositor.sierpinski_loader import VideoSlotStub
slots = [VideoSlotStub(i) for i in range(3)]

class FakeReactor:
    def set_header(self, h): pass
    def set_text(self, t): pass
    def set_speaking(self, s): pass
    def feed_pcm(self, p): pass

d = DirectorLoop(video_slots=slots, reactor_overlay=FakeReactor())
print(d._build_unified_prompt())
print(f'--- Token estimate: ~{len(d._build_unified_prompt().split())} words ---')
"`

Expected: Structured prompt with all 4 context layers, ~300-400 words (~1000 tokens).

- [ ] **Step 5: Commit**

```bash
git add agents/studio_compositor/director_loop.py
git commit -m "feat(director): switch from gemini-flash to Claude Opus (balanced route)

Per intelligence-first commitment: always CAPABLE. Opus response
time fits within the TTS synthesis+playback window (3-8s).
max_tokens reduced from 2048 to 300 per token budget spec."
```

---

### Task 6: Verify end-to-end

- [ ] **Step 1: Run tests**

Run: `uv run pytest tests/ -q --ignore=tests/hapax_daimonion --ignore=tests/contract -m "not llm" -x`

Expected: All tests pass (no test changes needed — this is runtime behavior).

- [ ] **Step 2: Run ruff**

Run: `uv run ruff check agents/studio_compositor/director_loop.py`

Expected: No lint errors.

- [ ] **Step 3: Create PR**

```bash
git push -u origin feat/reactor-context-enrichment
gh pr create --title "feat: enrich director LLM with phenomenal context and Claude Opus" --body "..."
```

- [ ] **Step 4: Monitor CI, fix failures, merge when green**
