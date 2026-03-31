# Truthful System Anatomy Animation

**Date:** 2026-03-31
**Status:** Approved
**Scope:** `hapax-logos/src/pages/FlowPage.tsx`, `logos/api/routes/flow.py`

## Problem

The system anatomy visualization uses continuous animations (breathing speed, opacity gradients, edge particles, edge color ramps) all driven by a single variable: `age_s` (seconds since a node's state file was last written). This creates a staleness display that visually claims to show activity, throughput, and health. The operator cannot distinguish "node wrote 2s ago and is now idle" from "node is in a tight processing loop." Every pulse, particle, and fade is a lie.

The Logos design language (§1) states: "Every visual element carries information. Nothing is decorative. An element that does not encode state, afford interaction, or provide spatial orientation must be removed."

## Design

### Principle

The visualization is still until the system gives it reason to move. Color encodes discrete state. Breathing encodes system-wide mood via stimmung stance. Nothing else animates. Every pixel that changes is driven by a real signal.

### Removals

| Current animation | Data driver | Why removed |
|---|---|---|
| `breathDur(age, status)` — 4-bucket breathing speed (1.5s/2.5s/4s/6s) | `age_s` | Age is not activity |
| `nodeOp(age, status)` — 5-bucket opacity (1.0/0.95/0.85/0.7/0.5) | `age_s` | Fading implies declining relevance; an offline consent engine is critical, not irrelevant |
| `edgeColor(age, active)` — 3-bucket green/yellow/orange | `age_s` | Claims health, measures only file freshness |
| Edge particles — age-based count (3/2/1) and speed (2s/3.5s/5s) | `age_s` | Claims throughput, measures nothing |
| `@keyframes breathe` applied to all active nodes | `age_s` | Currently decorative; reassigned to stimmung severity |

### Node visual states

Three states, no gradients between them. Matches backend `_status()` enum.

| Status | Border | Background | Opacity | Glow | Animation |
|---|---|---|---|---|---|
| **active** | `green-400` | `green-400` @ 10% | 1.0 | none (unless stimmung degraded/critical) | none (unless stimmung degraded/critical) |
| **stale** | `yellow-400` | `yellow-400` @ 10% | 1.0 | none (unless stimmung degraded/critical) | none (unless stimmung degraded/critical) |
| **offline** | `zinc-600` | `zinc-600` @ 6% | 0.5 | none | none |

**Changes from current:**
- Stale border: `orange-400` → `yellow-400` (matches design language severity ladder — yellow is caution/stale, orange is degraded/urgent)
- No default glow on active nodes (box-shadow removed unless stimmung warrants it)
- No opacity gradient (binary: 1.0 or 0.5)
- 6px status dot (top-right) retained as truthful binary indicator

Per-node body renderers (PerceptionBody, StimmungBody, VoiceBody, etc.) are unchanged — they display actual metric values.

Sparklines retained — historical traces of real metric values.

### Stimmung-driven breathing — the only continuous animation

The design language §3.4 specifies when and how breathing occurs, driven by stimmung stance.

**Scope:** All nodes with status `active` or `stale`. Offline nodes never breathe.

| Stimmung stance | Breathing duration | Glow | Scale |
|---|---|---|---|
| **nominal** | none | none | 1.0 |
| **cautious** | none | none | 1.0 |
| **degraded** | 6s cycle | inset 8px @ 6% of node border color | 1.0 |
| **critical** | 2s cycle | inset 12px @ 8% of node border color | 1.15x pulse |

**Implementation:** Replace `breathDur(age, status)` with `stimmungBreath(stance: string)` returning `"0s"` | `"6s"` | `"2s"`. Stance value read from stimmung node's `metrics.stance` field, already present in flow state.

**Visual effect:** Most of the time, the visualization is completely still. When stimmung enters degraded or critical, all non-offline nodes breathe together at the same rate — a truthful ambient signal of changed system conditions.

**Stimmung node special treatment:** Its own border opacity follows §3.4 directly (15% at cautious, 25% at degraded, 35% at critical).

### Edge visual treatment

Three classes, all always visible. No particles. No continuous animation.

| Class | Stroke | Dash | Width | Opacity | Color |
|---|---|---|---|---|---|
| **confirmed + active** | solid | none | 1.5px | 0.7 | source node status color (`green-400` if active, `yellow-400` if stale) |
| **confirmed + inactive** | solid | none | 0.8px | 0.15 | `zinc-700` |
| **emergent** | dashed 6/3 | — | 2px | 0.8 | `yellow-400` |
| **dormant** | dotted 2/4 | — | 1px | 0.2 | `zinc-600` |

Edge labels on hover retained. Emergent edge `⚡` marker retained. Arrow markers use simplified color. Edges do not breathe — they are wires, not organs.

### Age display

`age_s` text in bottom-right of each node retained as last-seen timestamp. Color: `text-muted` always (no severity coding on the number itself). The backend staleness threshold still drives the `active`/`stale`/`offline` status enum; the age number is supplementary context.

### Bottom status bar

No changes. Already driven by real data (stimmung stance, active flow count, health API, nvidia-smi GPU data, Langfuse cost).

## Files to modify

| File | Changes |
|---|---|
| `hapax-logos/src/pages/FlowPage.tsx` | Replace `breathDur()` with `stimmungBreath()`. Remove `nodeOp()` gradient (binary 1.0/0.5). Remove particle rendering from `FlowingEdge`. Simplify `edgeColor()` to status-based. Update `flowColors()` stale from orange to yellow. Remove default glow from `@keyframes breathe` application. Add stimmung stance glow/scale logic to `SystemNode`. |
| `logos/api/routes/flow.py` | No changes needed — backend already provides all required data (node status, stimmung stance via metrics) |

## Out of scope

- Adding new data sources (throughput counters, CPU metrics)
- Changing node topology or discovery logic
- Modifying per-node body renderers
- Changing the detail panel
- Backend flow observer changes
