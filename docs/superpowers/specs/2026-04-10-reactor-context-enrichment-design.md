# Reactor Context Enrichment — Design Addendum

**Date:** 2026-04-10
**Amends:** `2026-04-10-spirograph-reactor-design.md` §5.4 (Self-Reflective Context)
**Status:** Approved

---

## Problem

The reactor LLM receives one compositor screenshot and a static system prompt per turn. No memory, no environmental awareness, no audio context, no video detail. Reactions are shallow pixel descriptions ("visual cacophony", "juxtaposition of samurai and Vitruvian") because the model has zero cognitive context.

## Theoretical Clearance

All constraints verified against research documents and codebase:

| Constraint | Status |
|-----------|--------|
| phenomenal_context.render() safe outside daimonion | YES — pure /dev/shm reads, snapshot-isolated |
| Phenomenal context in non-grounding call | NO VIOLATION — orientation substrate, not grounding substrate |
| Reaction history pseudo-grounding | NO VIOLATION — broadcast context, no acceptance cycle |
| Imagination uniform reading | NO VIOLATION — dimensions are semantic intent, reactor is consumer |
| Experiment freeze | NO CONFLICT — all reactor code outside freeze manifest |
| Model tier | MUST USE CAPABLE (Claude Opus) per intelligence-first commitment |

## Design

### Context Sources

The reactor assembles context from four layers, using the canonical `ContextAssembler` from `shared/context.py` (prompt compression Phase 1 work):

1. **Phenomenal context** — `phenomenal_context.render(tier="FAST")` called standalone. Provides stimmung state, temporal awareness (retention/impression/protention), situation coupling, prediction errors, self-state. ~200 tokens.

2. **Enrichment context** — `ContextAssembler.snapshot()` provides DMN observations, imagination fragments (with 9 expressive dimensions + material quality), perception snapshot. Rendered via `to_toon()` for token efficiency. ~150 tokens.

3. **Reaction memory** — Last 8 reactions preserved across turns (not cleared between cycles). Injected as timestamped thread. Older reactions beyond 8 are dropped (no LLM summarization needed at this volume). ~120 tokens.

4. **Dual-image input** — Two images per LLM call:
   - `yt-frame-{N}.jpg` (384x216, dedicated video frame — readable detail)
   - `fx-snapshot.jpg` (1920x1080, compositor output — what viewers see)

### Model

Claude Opus via LiteLLM `balanced` route. Per the intelligence-first commitment: "always CAPABLE; intelligence is last thing shed." The reactor's turn has natural latency tolerance (TTS synthesis + playback = 3-8s; Opus response time fits within this window).

### Token Budget

| Component | Tokens |
|-----------|--------|
| System prompt (reactor context) | ~250 |
| Phenomenal context (FAST tier) | ~200 |
| Enrichment context (TOON format) | ~150 |
| Reaction history (8 entries) | ~120 |
| Images (2x, separate from text budget) | 0 text tokens |
| Response budget (max_tokens) | 300 |
| **Total** | **~1,020** |

Well within Claude Opus limits. TOON format saves ~40% vs JSON on the enrichment block.

### Prompt Structure

```
<reactor_context>
You are the daimonion — the persistent cognitive substrate of the Hapax system.
{situation block — videos, music, overlays}

## Phenomenal Context
{render(tier="FAST") output — stimmung, temporal, situation, surprises}

## System State
{ContextAssembler.snapshot() in TOON — DMN observations, imagination dimensions, perception}

## Recent Reactions
- [13:26] Reacting to Steve Jobs: "From the nascent dreams of '81 Jobs..."
- [13:27] Reacting to Narcissist: "Watching how to..."
{...last 8}

YOUR ROLE: {same as before}
RESPONSE FORMAT: {same as before}
</reactor_context>

[Image 1: Current video frame — what you're reacting to]
[Image 2: Compositor output — what viewers see]
React to what you see. The first image is the video content. The second is the full composed surface viewers are watching.
```
