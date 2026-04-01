# Studio Graph Canvas — Full UX Redesign

**Date:** 2026-04-01
**Status:** Design approved
**Supersedes:** All prior studio frontend code (effectSources.ts, CameraHero, CameraGrid, StudioDetailPane, GroundStudioContext, studio snapshot hooks)
**Motivation:** The current studio UI is a camera viewer with a preset picker bolted on. It exposes a fraction of the system's capabilities. The graph-based effect system has 56 shader nodes, 30 presets, 13+ modulation signals, 6 cameras, Reverie visual surface, IR perception, detection overlays, content layer injection, and governance — none of which are accessible from the UI. This redesign replaces the entire studio frontend with a unified node-graph canvas that exposes full creative control.

---

## 1. Core Model

Two operators, one canvas:

- **Human (compositional):** builds graph presets — wires nodes, tunes params, assigns modulation sources, saves named presets. Deliberate studio work.
- **Hapax (live performance):** atmospheric selector picks presets based on stance/energy/genre, uniform modulator drives params at 30fps from audio/biometric signals. Autonomous and reactive.

The UI serves both without mode-switching. The human builds; Hapax performs. The graph canvas is the single shared surface.

---

## 2. Architecture

### 2.1 One Canvas

A single React Flow (`@xyflow/react`) canvas fills the Tauri window. No terrain system, no regions, no depth layers. The graph IS the app.

### 2.2 Five Node Categories

| Category | Examples | Visual Treatment |
|----------|----------|-----------------|
| **Source** | Camera (6 roles), Reverie surface, IR feeds, noise generators | Amber border. Live thumbnail inside node. |
| **Shader** | All 56 processing/temporal/distortion/compositing nodes | Grey border. Collapsed by default. Expandable for param editing + modulation. |
| **Output** | Live preview nodes | Green border. Renders live video at node size. Multiple allowed, aggregable. |
| **Utility** | Recording, consent status, detection overlay config | Subdued. Functional controls, not in signal chain. |
| **Content** | Text/image/RGBA injection for content_layer slots | Feed into content_layer shader's 4 secondary inputs. |

### 2.3 Edges

Animated dots flowing along edges show signal direction. Thickness/brightness modulated by Hapax governance when it influences that path.

### 2.4 Three Persistent UI Elements (Not Nodes)

1. **Node palette** — left drawer, categorized by 10 aesthetic families. Drag to add.
2. **Preset library** — right drawer, load/save presets with category tags and reference material.
3. **Command palette** — `Cmd+K` / right-click, searchable node addition and graph actions.

### 2.5 State Management

Single Zustand store replacing GroundStudioContext. Tracks:

- Graph definition (nodes, edges, params, modulation bindings)
- Governance state (current preset, active modulations, atmospheric selector reasoning)
- Camera statuses (per-role: active/offline/starting)
- Recording state and consent phase
- UI state (drawer visibility, lock toggle, selected node)

Persisted to localStorage. Synced bidirectionally with backend via fx-request.txt / polling.

### 2.6 Technology

- **React Flow** (`@xyflow/react`) — canvas, pan/zoom, node rendering, edge routing, selection, connection
- **Zustand** — state management (already used in codebase)
- **dagre** — auto-layout for preset loading
- **Existing Tauri IPC proxy** — all API communication through `invoke()`
- **Design language** — Gruvbox Hard Dark palette via CSS custom properties per `docs/logos-design-language.md`

---

## 3. Node Design

### 3.1 Two States: Collapsed and Expanded

**Collapsed (default):** ~120×60px. Shows: node type icon, name, one-line key param summary. Source nodes include a small thumbnail. Output nodes show live video.

**Expanded (click to select → side sheet opens):** A fixed panel on the right edge of the canvas, anchored visually to the selected node by a highlighted edge. Contains:

1. **All params** — sliders, dropdowns, color pickers, toggles. Live-updating.
2. **Modulation routing per param** — dropdown to assign signal source (audio_rms, beat_phase, heart_rate, desk_energy, stimmung_valence, etc.) plus scale, offset, smoothing knobs.
3. **Hapax influence indicator** — subtle animated pip next to any param governance is currently driving.
4. **Stage preview** — thumbnail of this node's output (not final output, just this processing stage).

### 3.2 Output Nodes

- Render live video via snapshot polling (useBatchSnapshotPoll pattern).
- Resizable — drag corners.
- Aggregation: right-click → "Aggregate with..." tiles 2-4 output nodes side by side in a floating comparison panel.
- Wire after any shader node to see intermediate results.
- Poll rate: ~12-20fps for visible output nodes, paused when offscreen.

### 3.3 Source Nodes

- **Camera:** live thumbnail, dropdown for role selection (brio-operator, brio-room, brio-synths, c920-desk, c920-overhead, c920-room). Status dot (green/amber/red). Poll rate: ~4fps thumbnail.
- **Reverie surface:** frame from `:8053`. Same poll pattern.
- **IR feeds:** latest IR snapshot per Pi role.
- **Generators:** noise_gen, solid, waveform_render, etc. Static or animated preview thumbnail.

### 3.4 Utility Nodes

**Recording node:**
- Not in signal chain (no video ports).
- Shows: on/off toggle, elapsed time, per-camera recording status, disk usage bar.
- Consent status embedded: current consent phase with color coding.
- Recording controls disabled when consent refused.

**Detection overlay node:**
- Configures detection rendering on all output nodes.
- Controls: tier selector (1/2/3), visibility toggle, per-enrichment toggles (gaze, emotion, posture, gesture, action, depth).
- When active, output nodes render DetectionOverlay canvas layer on top of video.

### 3.5 Content Injection Nodes

- Source nodes for content_layer shader's 4 slots.
- Types: "Text Content", "Image Content", "RGBA Content".
- Wire into content_layer node's secondary input ports (slot 0-3).

---

## 4. Hapax Governance Visualization

Three layers of ambient presence. Non-intrusive, never structural.

### 4.1 Node-Level: Param Pulse

When Hapax's modulator drives a param, the param label in the expanded detail panel breathes (opacity 0.6→1.0 at modulation rate). Value live-updates. Color: `var(--color-yellow)`.

### 4.2 Edge-Level: Flow Intensity

Edges carrying governance-modulated signals pulse brighter/thicker. Beat-driven modulation makes edges pulse on beat. Idle edges have slow, dim dots. Instant visual read of "what is Hapax touching."

### 4.3 Canvas-Level: Preset Transition

When the atmospheric selector switches presets:
- Toast notification: "Hapax → Neon" with reason (energy: high, stance: nominal).
- If you're editing a different graph, amber banner: "Hapax wants: Neon — you're editing: Custom 3" with "Accept" button.

### 4.4 Override Model

- By default, Hapax switches presets autonomously.
- When you're actively editing (node selected, param being dragged), preset switches are suppressed. Hapax queues its suggestion; banner shows what it wanted.
- After 30s idle with nothing selected, Hapax resumes autonomous control.
- Lock toggle in toolbar: 🔒 = suppress Hapax / 🔓 = Hapax can drive.

---

## 5. Preset Library

Right-side drawer, toggleable via `L` key or toolbar button.

### 5.1 Current Graph Section

- Name field (editable), save button, "Save As" for variants.
- Category tags (can belong to multiple aesthetic categories).
- Dirty indicator when unsaved changes exist.

### 5.2 Preset Browser

10 collapsible category groups:

1. **Minimal / Transparent** — ambient, clean
2. **Temporal Persistence / Feedback** — ghost, trails, feedback_preset, echo, reverie_vocabulary
3. **Analog Degradation** — vhs_preset, dither_retro, nightvision
4. **Databending / Glitch** — datamosh, datamosh_heavy, glitch_blocks_preset, pixsort_preset
5. **Houston Syrup / Hip Hop Temporal** — screwed, trap
6. **False Color / Spectral** — neon, thermal_preset
7. **Edge / Silhouette / Relief** — silhouette, sculpture
8. **Halftone / Mosaic / Character** — halftone_preset, ascii_preset
9. **Geometric Distortion / Symmetry** — fisheye_pulse, kaleidodream, mirror_rorschach, tunnelvision, voronoi_crystal
10. **Biometric / Reactive** — heartbeat, diff_preset, slitscan_preset

Each preset shows: name, node count, static thumbnail.

Click to load → replaces canvas with preset's graph. Auto-layout via dagre.

Custom user presets (from `~/.config/hapax/effect-presets/`) appear in a "Custom" category at the top.

### 5.3 Reference Material (Per Category)

Each category has a collapsible reference section showing 4 exemplary works: artist, title, year, 1-2 sentence description. Textual references for creative context, not an image gallery.

**Minimal / Transparent:**
- Andy Warhol, *Screen Tests* (1964-1966) — 472 silent portrait films, single unbroken takes.
- James Benning, *13 Lakes* (2004) — thirteen 10-minute static shots, pure observational cinema.
- Bill Viola, *The Reflecting Pool* (1977-1979) — radical clarity of the unprocessed frame.
- Michael Snow, *Wavelength* (1967) — 45-minute zoom foregrounding perception itself.

**Temporal Persistence / Feedback:**
- Nam June Paik, *TV Buddha* (1974) — foundational video feedback loop as art.
- Steina and Woody Vasulka, *Noisefields* (1974) — audio-video feedback experiments at The Kitchen.
- Zbigniew Rybczynski, *Tango* (1980) — 36 temporal layers coexisting in one room.
- Paul Sharits, *N:O:T:H:I:N:G* (1968) — polychromatic flicker creating temporal persistence.

**Analog Degradation:**
- Pipilotti Rist, *I'm Not The Girl Who Misses Much* (1986) — deliberate VHS degradation as ritual.
- Kathryn Bigelow / Greig Fraser, *Zero Dark Thirty* raid sequence (2012) — authentic night-vision device on ARRI Alexa.
- Rosa Menkman, *A Vernacular of File Formats* (2010) — systematic codec failure aesthetics.
- JODI, *%20Wrong* (1999) — digital degradation as native artistic vocabulary.

**Databending / Glitch:**
- Takeshi Murata, *Monster Movie* (2005) — datamoshed B-movie footage, now at Smithsonian.
- Kanye West (dir. Nabil Elderkin), *Welcome to Heartbreak* (2009) — datamoshing enters mainstream hip hop.
- Kim Asendorf, *Mountain Tour* (2010) — inventor of pixel sorting algorithm.
- Chairlift (dir. Ray Tintori), *Evident Utensil* (2009) — choreographed datamoshing.

**Houston Syrup / Hip Hop Temporal:**
- DJ Screw, *Screw Tapes* (1991-2000) — 300+ mixtapes defining the source aesthetic.
- A$AP Rocky (dir. Dexter Navy), *L$D* (2015) — liquefied psychedelic smears through Tokyo neon.
- Travis Scott (dir. Dave Meyers), *SICKO MODE* (2018) — purple-hued desaturation and frame stuttering.
- Gaspar Noe, *Enter the Void* (2009) — foundational cinematic psychedelic temporal distortion.

**False Color / Spectral:**
- Richard Mosse, *The Enclave* (2013) — Kodak Aerochrome infrared film in eastern Congo.
- Dan Flavin, *untitled (to the "innovator" of Wheeling Peachblow)* (1966-1968) — fluorescent light sculptures as spectral saturation.
- Gaspar Noe, *Enter the Void* title sequence (2009) — neon spectrum strobing typography.
- Ryoji Ikeda, *test pattern* (2008-ongoing) — data streams remapped to spectral gradients.

**Edge / Silhouette / Relief:**
- Saul Bass, *The Man with the Golden Arm* titles (1955) — silhouette as narrative device.
- Richard Linklater, *A Scanner Darkly* (2006) — interpolated rotoscope as shifting edge detection.
- Daniel Rozin, *Wooden Mirror* (1999) — live camera feed converted to physical relief sculpture.
- Saul Bass, *Vertigo* titles (1958) — computational image processing meets graphic design.

**Halftone / Mosaic / Character:**
- Kenneth Knowlton and Leon Harmon, *Studies in Perception I* (1966) — foundational computer mosaic.
- Ryoji Ikeda, *datamatics* (2006-ongoing) — pure data as black-and-white visual grid.
- Jim Campbell, *Portrait of My Father* (2000) — 16x24 LED grid portrait.
- Vuk Cosic, *ASCII History of Moving Images* (1998) — Lumiere and Psycho as ASCII streams.

**Geometric Distortion / Symmetry:**
- Hype Williams, *The Rain (Supa Dupa Fly)* — Missy Elliott (1997) — fisheye as hip hop visual identity.
- James Whitney, *Lapis* (1966) — analog computer mandala animation.
- Douglas Trumbull, Stargate sequence, *2001: A Space Odyssey* (1968) — slit-scan tunnel.
- Jordan Belson, *Allures* (1961) — 30 simultaneous projectors at the Vortex Concerts.

**Biometric / Reactive:**
- Rafael Lozano-Hemmer, *Pulse Room* (2006) — incandescent bulbs pulsing with visitor heartbeats.
- Daniel Rozin, *Mechanical Mirrors* series (1999-ongoing) — frame differencing driving physical actuators.
- Douglas Trumbull, slit-scan camera rig for *2001* (1968) — the original temporal-spatial scanning apparatus.
- Sabato Visconti, *Glitch Landscapes* (2012-ongoing) — corrupted camera firmware at moment of capture.

---

## 6. Interaction & Navigation

### 6.1 Canvas Interaction (React Flow native)

| Action | Input |
|--------|-------|
| Pan | Scroll / middle-click drag |
| Zoom | Pinch / Ctrl+scroll |
| Select | Click node |
| Multi-select | Shift+click or drag-box |
| Connect | Drag from output port to input port |
| Delete | Select + Backspace |
| Undo/redo | Cmd+Z / Cmd+Shift+Z |

### 6.2 Node Addition (Three Paths)

1. Drag from left palette onto canvas.
2. Cmd+K → type node name → Enter (places at viewport center).
3. Right-click canvas → categorized submenu.

### 6.3 Keyboard Shortcuts (Command Registry)

| Key | Action |
|-----|--------|
| `Cmd+K` | Command palette |
| `L` | Toggle preset library drawer |
| `P` | Toggle node palette drawer |
| `Space` | Toggle Hapax lock |
| `F` | Fit graph to viewport |
| `1` / `2` / `3` | Detection tier |
| `Cmd+S` | Save current graph as preset |
| `Tab` | Cycle selection through nodes in chain order |
| `Cmd+Shift+L` | Auto-layout (dagre) |

All shortcuts registered via the existing command registry for consistency with keyboard adapter and MCP relay.

### 6.4 Auto-Layout

On preset load or Cmd+Shift+L: dagre arranges nodes left-to-right (source → processing → output). Manual repositioning afterward. Positions saved with preset.

### 6.5 Responsive Behavior

Canvas fills the Tauri window at any size. Drawers overlay (not side-by-side). On smaller windows, drawers auto-close on canvas interaction.

---

## 7. Data Flow & Backend Integration

### 7.1 Graph → Backend

Saving or activating a preset serializes the React Flow graph to existing `EffectGraph` JSON format:
```json
{
  "name": "Custom 1",
  "nodes": {"mirror": {"type": "mirror", "params": {"axis": 0, "position": 0.5}}},
  "edges": [["@live", "mirror"], ["mirror", "out"]],
  "modulations": [{"node": "mirror", "param": "position", "signal": "beat_phase", "scale": 0.3}]
}
```

- Custom presets: written to `~/.config/hapax/effect-presets/{name}.json`.
- Activation: writes preset name to `/dev/shm/hapax-compositor/fx-request.txt`.
- No new API endpoints needed for preset switching.

### 7.2 Backend → Frontend

| Data | Source | Poll Rate | Drives |
|------|--------|-----------|--------|
| Camera frames | `useBatchSnapshotPoll` → `/api/studio/stream/cameras/batch` | Source nodes: ~4fps, output nodes: ~12-20fps | Node thumbnails and output previews |
| Compositor status | `useCompositorLive` → `/api/studio/live/status` | 2s | Camera status dots, recording state, consent phase |
| Governance state | New: `/api/studio/governance/state` | 1s | Hapax ambient overlays, preset transition toasts |
| Visual layer | `useVisualLayer` → `/api/visual-layer` | 2s | Detection overlays on output nodes |
| Perception | `usePerception` → `/api/perception` | 3s | Activity labels, modulation signal values |

### 7.3 New Backend Endpoints (3)

1. **`GET /api/studio/governance/state`** — current atmospheric selector state (stance, energy, target preset, active modulations). Small JSON from compositor state.
2. **`GET /api/studio/stream/node/{slot}`** — snapshot at a specific SlotPipeline slot for intermediate output nodes. Falls back to fx-snapshot.jpg.
3. **`POST /api/studio/presets`** — save a preset JSON to user preset directory. Body is the EffectGraph JSON.

### 7.4 Tauri IPC

All new endpoints proxied through Tauri invoke commands following the existing pattern in `src-tauri/src/commands/studio.rs`. No direct HTTP fetch from React.

### 7.5 State Sync

```
Zustand store (frontend truth)
  ↔ React Flow (canvas reads/writes graph)
  → Tauri IPC → FastAPI → compositor (backend activation)
  ← Polling hooks → store updates (cameras, governance, detections)
  → localStorage (graph layout, drawer state, lock toggle)
```

---

## 8. What Gets Deleted

The entire current studio frontend is replaced:

| File | Reason |
|------|--------|
| `components/studio/effectSources.ts` | Replaced by direct preset JSON loading |
| `components/terrain/ground/CameraHero.tsx` | Replaced by output nodes |
| `components/terrain/ground/CameraGrid.tsx` | Replaced by source nodes |
| `components/terrain/ground/CameraPip.tsx` | Replaced by source node thumbnails |
| `components/terrain/ground/StudioDetailPane.tsx` | Replaced by node detail side sheet |
| `components/studio/StudioStatusGrid.tsx` | Replaced by utility nodes |
| `components/studio/CameraSoloView.tsx` | Replaced by output node + fullscreen |
| `components/studio/VisualLayerPanel.tsx` | Replaced by modulation routing in node detail |
| `components/studio/SceneBadges.tsx` | Absorbed into governance visualization |
| `contexts/GroundStudioContext.tsx` | Replaced by Zustand store |
| `hooks/useSnapshotPoll.ts` | Replaced by unified node polling |

**What stays:**
- `hooks/useBatchSnapshotPoll.ts` — reused for source and output node polling
- `components/studio/DetectionOverlay.tsx` — reused as canvas layer on output nodes
- `contexts/ClassificationOverlayContext.tsx` — reused for signal routing
- `api/hooks.ts` — polling hooks reused
- `api/client.ts` — Tauri invoke wrappers reused
- `api/types.ts` — type definitions reused and extended
- `lib/commandRegistry.ts` — framework reused, new studio commands registered
- `lib/commands/studio.ts` — rewritten for graph canvas actions
- `lib/commands/detection.ts` — kept as-is

---

## 9. Scope Boundaries

**In scope:**
- React Flow canvas with all 5 node categories
- Node palette (left drawer) with 10 aesthetic categories
- Preset library (right drawer) with reference material
- Command palette (Cmd+K)
- Hapax governance ambient visualization
- Override model (lock toggle, edit suppression)
- Node detail side sheet with modulation routing
- Output node aggregation
- 3 new backend endpoints
- Zustand store replacing GroundStudioContext

**Out of scope (future work):**
- HLS smooth mode (can be added as an output node option later)
- Visual surface / Reverie parameter editing (currently Rust-side, complex)
- Graph versioning / undo history persistence across sessions
- Collaborative editing (single-operator axiom)
- Mobile / Wear OS integration
- Effect chain A/B testing (compare two graphs side by side)
