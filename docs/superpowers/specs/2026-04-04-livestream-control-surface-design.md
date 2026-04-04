# Livestream Production Control Surface

## Goal

Replace the flat preset buttons in the fullscreen output view with a three-layer production control surface for programming livestream visual procedures.

## Architecture

Three layers, built incrementally:

1. **Chain Builder** — Drag-and-drop preset chips into a horizontal chain. Compositor applies presets in sequence. Live preview in fullscreen output above.
2. **Source Selector** — Per-chain dropdown selecting which video feed (live/HLS/smooth) enters the chain.
3. **Sequence Programmer** — Multiple chains arranged in a timed playlist. Auto-cycles through chains with configurable durations. Hard cut transitions. Loops.

## Layout

```
+-----------------------------------------------------+
|                                                     |
|              LIVE FULLSCREEN OUTPUT                  |
|            (current active chain result)             |
|                                                     |
+-----------------------------------------------------+
| > Sequence: [Chain 1: 2min] [Chain 2: 1min] [+]    |  <- sequence bar
+-----------------------------------------------------+
| src:[live v]  [VHS] -> [Halftone] -> [Bloom]  [+]  |  <- active chain editor
|                                                     |
| Available: [ambient][ghost][trails][nightvision]..  |  <- preset palette
+-----------------------------------------------------+
```

The control panel is a collapsible overlay at the bottom of the fullscreen view. Toggle with a button or hotkey. When collapsed, only the sequence progress bar is visible.

## Data Model

```typescript
interface PresetChain {
  id: string;
  source: "live" | "hls" | "smooth";
  presets: string[];          // ordered preset names to apply in sequence
  durationSeconds: number;    // how long this chain runs before advancing
}

interface Sequence {
  chains: PresetChain[];      // ordered playlist
  loop: boolean;              // restart after last chain
  activeIndex: number;        // currently playing chain
  playing: boolean;           // auto-advance enabled
}
```

State lives in the existing `studioGraphStore` Zustand store, persisted to localStorage.

## Interaction

### Chain Builder
- Drag preset chip from palette to chain strip: appends to chain
- Drag within chain strip: reorder presets in chain
- Click X on chip: remove from chain
- Chain applies immediately on any change (live preview)
- Available presets shown as a wrap grid below the chain strip (same as current preset buttons, but draggable)

### Source Selector
- Dropdown at left end of chain strip
- Options: live (default), hls, smooth
- Changing source updates the `@live` input node's source in the merged graph

### Sequence Programmer
- Horizontal bar above the chain editor showing all chains as blocks
- Block width proportional to duration
- Click block to select and edit that chain below
- Active (playing) chain highlighted
- Click duration label to edit (inline number input, seconds)
- Drag blocks to reorder
- [+] button to add new chain
- Play/pause button starts/stops auto-cycling
- Progress indicator shows time remaining in current chain

## Backend Integration

### Preset Chaining (Frontend Merge)

No new backend endpoints. The frontend merges multiple presets into a single graph:

1. Load each preset's `EffectGraph` JSON via `GET /studio/presets/{name}`
2. Concatenate nodes from all presets, deduplicating by type (later preset wins for shared node types like `content_layer`, `postprocess`)
3. Wire edges: first preset's `@live` stays as input, each subsequent preset's input connects to the previous preset's last node before `output`
4. Remove intermediate `output` nodes, keep only the final one
5. Send merged graph via `PUT /studio/effect/graph`

The 8-slot SlotPipeline limit constrains total nodes across all chained presets. The UI should show a slot count indicator (e.g., "5/8 slots used") and prevent adding presets that would exceed the limit.

### Sequence Auto-Cycling (Frontend Timer)

A `setInterval` timer in the React component:
- On interval tick, check if current chain's duration has elapsed
- If yes, advance `activeIndex`, merge next chain's graph, send to backend
- If loop enabled and at end, reset to index 0

### Source Selection

The `@live` edge in the merged graph points to the compositor's live camera feed by default. For HLS or smooth sources, the frontend modifies the graph's input source before sending. This maps to the existing `SourceNode` type in the graph editor.

## Scope Decomposition

### Sub-project 1: Chain Builder + Live Preview
- Replace preset buttons with draggable chips in fullscreen overlay
- Implement preset graph merging on frontend
- Live preview updates on chain change
- Slot count indicator
- Persist chain to localStorage

### Sub-project 2: Source Selector
- Add source dropdown to chain strip
- Wire source selection into merged graph's input node

### Sub-project 3: Sequence Programmer
- Sequence bar UI above chain editor
- Multiple chains with durations
- Play/pause auto-cycling timer
- Persist sequence to localStorage

## Key Files to Modify

| File | Change |
|------|--------|
| `hapax-logos/src/components/graph/nodes/OutputNode.tsx` | Replace `FullscreenOverlay` preset buttons with control surface |
| `hapax-logos/src/stores/studioGraphStore.ts` | Add chain/sequence state |
| `hapax-logos/src/components/graph/presetLoader.ts` | Add `mergePresetGraphs()` function |
| New: `hapax-logos/src/components/graph/ChainBuilder.tsx` | Chain strip component |
| New: `hapax-logos/src/components/graph/SequenceBar.tsx` | Sequence programmer component |
| New: `hapax-logos/src/components/graph/PresetChip.tsx` | Draggable preset chip |

## Dependencies

- `@xyflow/react` (already installed) provides drag-and-drop primitives
- No new dependencies needed. Native HTML5 drag-and-drop for the simpler chain strip interaction (React Flow is overkill for a linear strip).

## What This Does NOT Include

- Individual node editing in the chain view (use existing StudioCanvas for that)
- Beat-synced transitions (future enhancement)
- Crossfade/dissolve transitions (hard cuts only)
- Backend chain endpoint (frontend merge is sufficient)
- Saving sequences as named presets (future)
