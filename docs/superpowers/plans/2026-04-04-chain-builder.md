# Chain Builder Implementation Plan (Sub-project 1 of 3)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the flat preset buttons in the fullscreen output view with a drag-and-drop chain builder that merges multiple presets into a single live effect chain.

**Architecture:** New `ChainBuilder` component replaces the preset strip in `FullscreenOverlay`. Preset chips are draggable (HTML5 drag-and-drop). A `mergePresetChains()` function in `presetLoader.ts` combines multiple preset graphs by concatenating nodes, deduplicating shared types, and wiring edges. The merged graph is sent to the backend via the existing `PUT /studio/effect/graph` endpoint. Chain state lives in Zustand store, persisted to localStorage.

**Tech Stack:** React 19, Zustand, HTML5 Drag and Drop API, existing Tauri IPC proxy

---

## File Structure

| File | Action | Responsibility |
|------|--------|----------------|
| `hapax-logos/src/components/graph/ChainBuilder.tsx` | Create | Chain strip + preset palette overlay for fullscreen view |
| `hapax-logos/src/components/graph/PresetChip.tsx` | Create | Draggable/droppable preset chip component |
| `hapax-logos/src/components/graph/presetMerger.ts` | Create | Merge multiple preset EffectGraphs into one |
| `hapax-logos/src/stores/studioGraphStore.ts` | Modify | Add chain state (chainPresets, activeChain) |
| `hapax-logos/src/components/graph/nodes/OutputNode.tsx` | Modify | Replace preset strip with ChainBuilder in FullscreenOverlay |
| `hapax-logos/src/components/graph/presetLoader.ts` | Modify | Export `fetchPresetGraph()` (raw JSON, no Flow conversion) |

---

### Task 1: Preset merger function

**Files:**
- Create: `hapax-logos/src/components/graph/presetMerger.ts`
- Modify: `hapax-logos/src/components/graph/presetLoader.ts`

- [ ] **Step 1: Add raw preset fetch to presetLoader.ts**

Add this export at the end of `hapax-logos/src/components/graph/presetLoader.ts`:

```typescript
/** Fetch a preset's raw EffectGraph JSON (no Flow conversion). */
export async function fetchPresetGraph(presetName: string): Promise<EffectGraphJson | null> {
  try {
    const graph = await api.get<EffectGraphJson>(`/studio/presets/${presetName}`);
    if (!graph?.nodes) return null;
    return graph;
  } catch {
    return null;
  }
}
```

- [ ] **Step 2: Create presetMerger.ts**

Create `hapax-logos/src/components/graph/presetMerger.ts`:

```typescript
/**
 * Merge multiple preset EffectGraphs into a single chained graph.
 *
 * Strategy:
 * - Nodes from each preset get a prefix to avoid ID collisions (p0_, p1_, ...)
 * - Shared infrastructure nodes (content_layer, postprocess, output) use only
 *   the LAST preset's version (dedup by type)
 * - Edges wire each preset's last effect node into the next preset's first
 * - @live feeds into the first preset's input
 */
import type { EffectGraphJson } from "./presetLoader";

const INFRA_TYPES = new Set(["output", "content_layer", "postprocess"]);

export function mergePresetGraphs(
  presetName: string,
  graphs: EffectGraphJson[],
): EffectGraphJson {
  if (graphs.length === 0) {
    return { name: presetName, nodes: { out: { type: "output", params: {} } }, edges: [], modulations: [] };
  }
  if (graphs.length === 1) {
    return { ...graphs[0], name: presetName };
  }

  const merged: EffectGraphJson = {
    name: presetName,
    nodes: {},
    edges: [],
    modulations: [],
  };

  // Collect effect nodes (non-infra) from each preset, prefixed
  const chainSegments: { prefix: string; effectNodes: string[]; firstNode: string; lastNode: string }[] = [];

  for (let i = 0; i < graphs.length; i++) {
    const g = graphs[i];
    const prefix = `p${i}_`;
    const effectNodes: string[] = [];

    // Add prefixed non-infra nodes
    for (const [id, def] of Object.entries(g.nodes)) {
      if (INFRA_TYPES.has(def.type)) continue;
      const prefixedId = prefix + id;
      merged.nodes[prefixedId] = { ...def };
      effectNodes.push(prefixedId);
    }

    // Find first and last effect nodes from edge order
    const orderedIds: string[] = [];
    const edgeMap = new Map<string, string>();
    for (const [src, tgt] of g.edges) {
      if (src === "@live" || INFRA_TYPES.has(g.nodes[tgt]?.type ?? "")) continue;
      edgeMap.set(src === "@live" ? "@live" : prefix + src, prefix + tgt);
    }

    // Topological walk from @live
    let cursor = "@live";
    while (edgeMap.has(cursor)) {
      const next = edgeMap.get(cursor)!;
      if (effectNodes.includes(next)) orderedIds.push(next);
      cursor = next;
    }

    // Add intra-preset edges (between effect nodes only)
    for (const [src, tgt] of g.edges) {
      const srcType = g.nodes[src]?.type;
      const tgtType = g.nodes[tgt]?.type;
      if (src === "@live" && !INFRA_TYPES.has(tgtType ?? "")) {
        // Will be wired to previous chain segment's output or @live
        continue;
      }
      if (INFRA_TYPES.has(srcType ?? "") || INFRA_TYPES.has(tgtType ?? "")) continue;
      merged.edges.push([prefix + src, prefix + tgt]);
    }

    // Add modulations with prefixed node IDs
    for (const m of g.modulations ?? []) {
      if (INFRA_TYPES.has(g.nodes[m.node]?.type ?? "")) continue;
      merged.modulations.push({ ...m, node: prefix + m.node });
    }

    const first = orderedIds.length > 0 ? orderedIds[0] : effectNodes[0];
    const last = orderedIds.length > 0 ? orderedIds[orderedIds.length - 1] : effectNodes[effectNodes.length - 1];
    if (first && last) {
      chainSegments.push({ prefix, effectNodes, firstNode: first, lastNode: last });
    }
  }

  // Wire chain: @live → first preset → second preset → ... → infra → output
  if (chainSegments.length > 0) {
    // @live → first segment's first node
    merged.edges.push(["@live", chainSegments[0].firstNode]);

    // Wire segments together
    for (let i = 1; i < chainSegments.length; i++) {
      merged.edges.push([chainSegments[i - 1].lastNode, chainSegments[i].firstNode]);
    }

    // Last segment → infra chain
    const lastSegment = chainSegments[chainSegments.length - 1];
    const lastGraph = graphs[graphs.length - 1];

    // Add infra nodes from last preset (no prefix)
    for (const [id, def] of Object.entries(lastGraph.nodes)) {
      if (INFRA_TYPES.has(def.type)) {
        merged.nodes[id] = { ...def };
      }
    }

    // Wire last effect → content_layer → postprocess → output
    const infraChain = ["content_layer", "postprocess", "out"]
      .filter((id) => merged.nodes[id]);

    if (infraChain.length > 0) {
      merged.edges.push([lastSegment.lastNode, infraChain[0]]);
      for (let i = 1; i < infraChain.length; i++) {
        merged.edges.push([infraChain[i - 1], infraChain[i]]);
      }
    }
  }

  return merged;
}

/** Count total effect slots needed for a merged chain. */
export function countSlots(graphs: EffectGraphJson[]): number {
  const seen = new Set<string>();
  let count = 0;
  for (const g of graphs) {
    for (const def of Object.values(g.nodes)) {
      if (!INFRA_TYPES.has(def.type)) count++;
    }
  }
  // Infra nodes from last preset
  if (graphs.length > 0) {
    const last = graphs[graphs.length - 1];
    for (const def of Object.values(last.nodes)) {
      if (INFRA_TYPES.has(def.type) && def.type !== "output") count++;
    }
  }
  return count;
}

export const MAX_SLOTS = 8;
```

- [ ] **Step 3: Verify build**

```bash
cd hapax-logos && pnpm tauri dev 2>&1 | head -20
# Wait for "Compiled successfully" or check for TypeScript errors
```

- [ ] **Step 4: Commit**

```bash
git add hapax-logos/src/components/graph/presetMerger.ts hapax-logos/src/components/graph/presetLoader.ts
git commit -m "feat: preset merger — combine multiple presets into one chain graph"
```

---

### Task 2: Chain state in Zustand store

**Files:**
- Modify: `hapax-logos/src/stores/studioGraphStore.ts`

- [ ] **Step 1: Add chain state and actions**

Add these fields to the `StudioGraphState` interface in `hapax-logos/src/stores/studioGraphStore.ts`, after the `outputFullscreen` field:

```typescript
  // Chain
  chainPresets: string[];
  chainSlotCount: number;
```

Add these actions to the interface, after `setOutputFullscreen`:

```typescript
  setChainPresets: (presets: string[]) => void;
  setChainSlotCount: (count: number) => void;
```

Add default values in the store initializer (after `outputFullscreen: false`):

```typescript
      chainPresets: [],
      chainSlotCount: 0,
```

Add action implementations (after the `setOutputFullscreen` implementation):

```typescript
      setChainPresets: (presets) => set({ chainPresets: presets }),
      setChainSlotCount: (count) => set({ chainSlotCount: count }),
```

Add `chainPresets` to the `partialize` persist config (the list of persisted fields):

```typescript
        partialize: (state) => ({
          graphName: state.graphName,
          hapaxLocked: state.hapaxLocked,
          leftDrawerOpen: state.leftDrawerOpen,
          rightDrawerOpen: state.rightDrawerOpen,
          chainPresets: state.chainPresets,
        }),
```

- [ ] **Step 2: Verify build**

```bash
cd hapax-logos && pnpm tauri dev 2>&1 | head -20
```

- [ ] **Step 3: Commit**

```bash
git add hapax-logos/src/stores/studioGraphStore.ts
git commit -m "feat: chain state in store — chainPresets persisted to localStorage"
```

---

### Task 3: PresetChip component

**Files:**
- Create: `hapax-logos/src/components/graph/PresetChip.tsx`

- [ ] **Step 1: Create PresetChip.tsx**

```tsx
import { memo, useCallback } from "react";

interface PresetChipProps {
  name: string;
  /** In chain strip — shows X button, draggable for reorder */
  inChain?: boolean;
  /** Index in chain (for reorder drag data) */
  chainIndex?: number;
  /** Called when X is clicked in chain mode */
  onRemove?: (index: number) => void;
  /** Called when chip is dragged from palette to chain */
  onDragStart?: (name: string) => void;
}

function PresetChipInner({ name, inChain, chainIndex, onRemove, onDragStart }: PresetChipProps) {
  const handleDragStart = useCallback(
    (e: React.DragEvent) => {
      if (inChain && chainIndex !== undefined) {
        e.dataTransfer.setData("chain-reorder", String(chainIndex));
      } else {
        e.dataTransfer.setData("preset-name", name);
      }
      e.dataTransfer.effectAllowed = "move";
      onDragStart?.(name);
    },
    [name, inChain, chainIndex, onDragStart],
  );

  return (
    <div
      draggable
      onDragStart={handleDragStart}
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 4,
        padding: "3px 8px",
        fontSize: 10,
        fontFamily: "JetBrains Mono, monospace",
        color: inChain ? "#ebdbb2" : "#928374",
        background: inChain ? "#3c3836" : "none",
        border: inChain ? "1px solid #fabd2f" : "1px solid #504945",
        borderRadius: 2,
        cursor: "grab",
        userSelect: "none",
      }}
    >
      {name}
      {inChain && onRemove && chainIndex !== undefined && (
        <span
          onClick={(e) => {
            e.stopPropagation();
            onRemove(chainIndex);
          }}
          style={{ color: "#665c54", cursor: "pointer", marginLeft: 2 }}
        >
          x
        </span>
      )}
    </div>
  );
}

export const PresetChip = memo(PresetChipInner);
```

- [ ] **Step 2: Commit**

```bash
git add hapax-logos/src/components/graph/PresetChip.tsx
git commit -m "feat: PresetChip — draggable preset chip for chain builder"
```

---

### Task 4: ChainBuilder component

**Files:**
- Create: `hapax-logos/src/components/graph/ChainBuilder.tsx`

- [ ] **Step 1: Create ChainBuilder.tsx**

```tsx
import { memo, useCallback, useRef, useState } from "react";
import { PresetChip } from "./PresetChip";
import { PRESET_CATEGORIES } from "./presetData";
import { fetchPresetGraph, type EffectGraphJson } from "./presetLoader";
import { mergePresetGraphs, countSlots, MAX_SLOTS } from "./presetMerger";
import { api } from "../../api/client";
import { useStudioGraph } from "../../stores/studioGraphStore";

const allPresetNames = PRESET_CATEGORIES.flatMap((cat) => cat.presets);

function ChainBuilderInner() {
  const chainPresets = useStudioGraph((s) => s.chainPresets);
  const setChainPresets = useStudioGraph((s) => s.setChainPresets);
  const chainSlotCount = useStudioGraph((s) => s.chainSlotCount);
  const setChainSlotCount = useStudioGraph((s) => s.setChainSlotCount);
  const [activating, setActivating] = useState(false);
  const dropRef = useRef<HTMLDivElement>(null);

  // Activate chain: fetch all preset graphs, merge, send to backend
  const activateChain = useCallback(
    async (presets: string[]) => {
      if (presets.length === 0) {
        api.post("/studio/effect/select", { preset: "clean" }).catch(() => {});
        setChainSlotCount(0);
        return;
      }
      if (presets.length === 1) {
        api.post("/studio/effect/select", { preset: presets[0] }).catch(() => {});
        setChainSlotCount(0);
        return;
      }

      setActivating(true);
      try {
        const graphs: EffectGraphJson[] = [];
        for (const name of presets) {
          const g = await fetchPresetGraph(name);
          if (g) graphs.push(g);
        }
        if (graphs.length === 0) return;

        const slots = countSlots(graphs);
        setChainSlotCount(slots);
        if (slots > MAX_SLOTS) return; // UI shows warning

        const merged = mergePresetGraphs("chain", graphs);
        await api.put("/studio/effect/graph", merged);
      } finally {
        setActivating(false);
      }
    },
    [setChainSlotCount],
  );

  // Add preset to chain
  const addPreset = useCallback(
    (name: string) => {
      const next = [...chainPresets, name];
      setChainPresets(next);
      activateChain(next);
    },
    [chainPresets, setChainPresets, activateChain],
  );

  // Remove preset from chain
  const removePreset = useCallback(
    (index: number) => {
      const next = chainPresets.filter((_, i) => i !== index);
      setChainPresets(next);
      activateChain(next);
    },
    [chainPresets, setChainPresets, activateChain],
  );

  // Reorder within chain via drag
  const handleChainDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      const reorderIdx = e.dataTransfer.getData("chain-reorder");
      const presetName = e.dataTransfer.getData("preset-name");

      if (presetName) {
        // Dragged from palette → append
        addPreset(presetName);
        return;
      }

      if (reorderIdx) {
        // Reorder within chain
        const fromIdx = parseInt(reorderIdx, 10);
        const rect = dropRef.current?.getBoundingClientRect();
        if (!rect) return;

        // Find drop position based on X coordinate
        const chipWidth = rect.width / Math.max(chainPresets.length, 1);
        const toIdx = Math.min(
          Math.floor((e.clientX - rect.left) / chipWidth),
          chainPresets.length - 1,
        );

        if (fromIdx === toIdx) return;
        const next = [...chainPresets];
        const [moved] = next.splice(fromIdx, 1);
        next.splice(toIdx, 0, moved);
        setChainPresets(next);
        activateChain(next);
      }
    },
    [chainPresets, setChainPresets, addPreset, activateChain],
  );

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = "move";
  }, []);

  const slotsOver = chainSlotCount > MAX_SLOTS;

  return (
    <div
      onClick={(e) => e.stopPropagation()}
      style={{
        position: "absolute",
        bottom: 0,
        left: 0,
        right: 0,
        background: "rgba(29,32,33,0.92)",
        borderTop: "1px solid #3c3836",
        padding: "8px 16px",
        fontFamily: "JetBrains Mono, monospace",
      }}
    >
      {/* Chain strip */}
      <div style={{ display: "flex", alignItems: "center", gap: 4, marginBottom: 8 }}>
        <span style={{ fontSize: 9, color: "#665c54", marginRight: 4 }}>chain:</span>
        <div
          ref={dropRef}
          onDrop={handleChainDrop}
          onDragOver={handleDragOver}
          style={{
            flex: 1,
            display: "flex",
            alignItems: "center",
            gap: 4,
            minHeight: 24,
            padding: "2px 4px",
            border: "1px dashed #504945",
            borderRadius: 2,
          }}
        >
          {chainPresets.length === 0 && (
            <span style={{ fontSize: 9, color: "#504945" }}>drag presets here</span>
          )}
          {chainPresets.map((name, i) => (
            <span key={`${name}-${i}`} style={{ display: "flex", alignItems: "center", gap: 2 }}>
              {i > 0 && <span style={{ color: "#665c54", fontSize: 10 }}>&rarr;</span>}
              <PresetChip name={name} inChain chainIndex={i} onRemove={removePreset} />
            </span>
          ))}
        </div>
        {chainSlotCount > 0 && (
          <span style={{ fontSize: 9, color: slotsOver ? "#fb4934" : "#665c54" }}>
            {chainSlotCount}/{MAX_SLOTS}
          </span>
        )}
        {activating && <span style={{ fontSize: 9, color: "#fabd2f" }}>...</span>}
      </div>

      {/* Preset palette */}
      <div style={{ display: "flex", flexWrap: "wrap", gap: 4, maxHeight: 120, overflowY: "auto" }}>
        {allPresetNames.map((name) => (
          <PresetChip key={name} name={name} onDragStart={() => {}} />
        ))}
      </div>
    </div>
  );
}

export const ChainBuilder = memo(ChainBuilderInner);
```

- [ ] **Step 2: Commit**

```bash
git add hapax-logos/src/components/graph/ChainBuilder.tsx
git commit -m "feat: ChainBuilder — drag-and-drop chain strip with preset palette"
```

---

### Task 5: Wire ChainBuilder into FullscreenOverlay

**Files:**
- Modify: `hapax-logos/src/components/graph/nodes/OutputNode.tsx`

- [ ] **Step 1: Replace preset strip with ChainBuilder**

In `hapax-logos/src/components/graph/nodes/OutputNode.tsx`, replace the `FullscreenOverlay` component's preset strip section.

Add import at the top of the file:

```typescript
import { ChainBuilder } from "../ChainBuilder";
```

In the `FullscreenOverlay` function, remove:
- The `allPresets` variable (line ~153-155)
- The `selectPreset` callback (line ~157-159)
- The `useEffect` that fetches current preset (line ~162-166)
- The entire `{/* Preset strip */}` block (line ~232-268)

Replace the removed preset strip with:

```tsx
      {/* Chain builder */}
      {showPresets && <ChainBuilder />}
```

Also update the top bar label to show chain info. Replace:
```tsx
<span style={{ fontSize: 11, color: "#928374" }}>{activePreset || "output"}</span>
```
with:
```tsx
<span style={{ fontSize: 11, color: "#928374" }}>output</span>
```

Remove the now-unused `activePreset` state and its setter (`useState("")` for activePreset).

- [ ] **Step 2: Verify in Logos**

1. `pnpm tauri dev`
2. Open graph editor, double-click output node to go fullscreen
3. Click "presets" button — should show chain builder with drag palette
4. Drag a preset chip to the chain strip — should append
5. Drag a second preset — should show arrow between them
6. Verify the live output updates (merged graph activates)
7. Click X on a chip — should remove and update output
8. Slot count should display (e.g., "5/8")

- [ ] **Step 3: Commit**

```bash
git add hapax-logos/src/components/graph/nodes/OutputNode.tsx
git commit -m "feat: wire ChainBuilder into fullscreen output overlay"
```

---

### Task 6: Click-to-add (single preset activation)

The chain builder should also support clicking a preset chip (not just dragging) to set it as the sole active preset — matching the current UX for quick switching.

**Files:**
- Modify: `hapax-logos/src/components/graph/PresetChip.tsx`
- Modify: `hapax-logos/src/components/graph/ChainBuilder.tsx`

- [ ] **Step 1: Add onClick to palette chips**

In `PresetChip.tsx`, add an `onClick` prop:

```typescript
  onClick?: (name: string) => void;
```

Add the click handler to the outer div:

```tsx
      onClick={() => onClick?.(name)}
```

In `ChainBuilder.tsx`, update the palette preset chips to support click-to-set:

```tsx
        {allPresetNames.map((name) => (
          <PresetChip
            key={name}
            name={name}
            onClick={(n) => {
              setChainPresets([n]);
              activateChain([n]);
            }}
          />
        ))}
```

This means: click sets it as the only preset in the chain (like current behavior), drag appends it to the chain.

- [ ] **Step 2: Commit**

```bash
git add hapax-logos/src/components/graph/PresetChip.tsx hapax-logos/src/components/graph/ChainBuilder.tsx
git commit -m "feat: click-to-set single preset in chain builder"
```

---

### Task 7: Final integration test and push

- [ ] **Step 1: Full test sequence**

1. Open Logos, go fullscreen output
2. Click "presets" — chain builder appears
3. Click "vhs_preset" — sets single preset, live output shows VHS
4. Drag "halftone_preset" to chain strip → chain shows [vhs_preset → halftone_preset]
5. Verify slot count shows (e.g., "6/8")
6. Verify live output changes (merged VHS + halftone effect)
7. Drag "nightvision" → 3 presets in chain, check slot count
8. If over 8 slots, count shows red, chain doesn't activate
9. Remove middle preset (click X) → chain updates, output updates
10. Press Escape — fullscreen closes
11. Re-enter fullscreen — chain persists (from localStorage)

- [ ] **Step 2: Build production binary**

```bash
cd hapax-logos && pnpm tauri build
```

- [ ] **Step 3: Push**

```bash
git push origin main
```
