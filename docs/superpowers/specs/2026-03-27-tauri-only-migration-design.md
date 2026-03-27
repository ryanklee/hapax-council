# Logos Tauri-Only Migration

**Date:** 2026-03-27
**Status:** Design approved, awaiting implementation plan
**Scope:** Eliminate browser/HTTP fallback, consolidate Logos onto Tauri as sole runtime

## Drivers

1. **Complexity reduction** — two transport paths (IPC vs HTTP fallback), dev server worktree mismatches, HMR relay quirks, dual CORS config
2. **Native UX** — window management, multi-window, always-on-top, borderless rendering that the browser path cannot deliver
3. **Officium alignment** — single deployment model across both Logos and Officium

## Approach: Surgical Excision

Strip the browser path in five phases. Each phase is a PR. Each leaves the system fully functional.

| Phase | What dies | What changes |
|-------|-----------|-------------|
| 1 | HTTP fallback in `client.ts`, SSE via fetch | All API calls → `invoke()`, SSE → Tauri events |
| 2 | Vite proxy, CORS origins for localhost | Vite serves assets only, CSP tightened |
| 3 | FastAPI WebSocket command relay | Command relay moves to Tauri Rust backend |
| 4 | Separate WGPU winit window | GPU texture sharing — WGPU renders to Tauri window surface |
| 5 | Dead code | ~400 lines deleted, ~50 added |

## Phase 1: Kill HTTP Fallback

### API Client (`src/api/client.ts`)

Delete `IS_TAURI` detection (`"__TAURI_INTERNALS__" in window`), `tauriOrHttp()` wrapper, `get()`/`put()`/`post()` HTTP helpers, and `BASE` constant. Every API method becomes a direct `invoke()` call. ~60 lines deleted, ~30 lines simplified.

### SSE → Tauri Events (`src/api/sse.ts`)

SSE currently uses raw `fetch()` for streaming (chat, agent runs, query refinement). Replace with Tauri event listeners:

- New Rust commands in `src-tauri/src/commands/` subscribe to FastAPI's SSE endpoints internally
- Re-emit as Tauri events (`agent:stream`, `chat:stream`, `query:stream`)
- Frontend listens via `@tauri-apps/api/event` instead of parsing EventSource format

Eliminates `connectSSE()`, the EventSource parser, and all browser-origin HTTP.

### Polling Hooks

`useSnapshotPoll` and `useBatchSnapshotPoll` replace `fetch()` calls with `invoke()` calls on the same intervals. Straightforward substitution.

### What Survives

FastAPI still runs on `:8051` — it's the backend, not the transport. Tauri's Rust layer talks to it over localhost HTTP internally. The React frontend never touches HTTP directly.

### New Rust Code

~3-4 SSE bridge commands in `src-tauri/src/commands/streaming.rs`:
- `start_agent_stream(agent, payload)` → subscribes to FastAPI SSE, emits Tauri events
- `start_chat_stream(messages)` → same pattern
- `start_query_stream(query)` → same pattern
- `cancel_stream(stream_id)` → aborts the internal subscription

## Phase 2: Strip Vite Proxy and Lock Down Dev Server

### Vite Config (`vite.config.ts`)

Delete `/api` proxy block entirely. Remove `server.host`/`server.cors` config. Keep `server.port: 5173` and `strictPort: true` (Tauri's `beforeDevCommand` expects it). Remove HMR WebSocket relay config (port 1421).

### Tauri Config (`tauri.conf.json`)

Tighten CSP: remove `http://127.0.0.1:8051` and `ws://127.0.0.1:*` from `connect-src`.

### FastAPI CORS (`logos/api/app.py`)

Remove `http://localhost:5173` and `http://127.0.0.1:5173` from CORS origins. Only `tauri://localhost` remains.

### Package.json

Remove `"preview": "vite preview"` script.

### Bundling with Phase 1

If the combined diff stays clean, Phases 1 and 2 can ship as a single PR.

## Phase 3: Command Relay Moves to Rust

### Current Flow

```
MCP/Voice → ws://127.0.0.1:8051/ws/commands → FastAPI → ws → frontend CommandRegistry
```

### Target Flow

```
MCP/Voice → ws://127.0.0.1:8052/ws/commands → Tauri Rust → Tauri event → frontend CommandRegistry
```

### New: `src-tauri/src/commands/relay.rs`

Rust WebSocket server (tokio-tungstenite) that:
- Listens on `:8052` (default; configurable via `HAPAX_RELAY_PORT` env var)
- Accepts `role=external` connections from MCP/voice
- Receives `execute`, `query`, `list` messages (identical JSON protocol)
- Emits Tauri events to the webview (`command:execute`, `command:query`)
- Receives results back from the frontend via `invoke()` response
- Forwards results to the external client

### Frontend Changes

`src/lib/commandRelay.ts` → replace WebSocket client with Tauri event listener:
```typescript
listen("command:execute", handler)   // replaces ws.onmessage
emit("command:result", result)       // replaces ws.send
```

~70 lines simplified. Reconnection/backoff logic disappears — Tauri events don't disconnect.

`src/contexts/CommandRegistryContext.tsx` → replace `connectCommandRelay(registry)` with `listenCommandRelay(registry)`.

### Backend Deletion

`logos/api/routes/commands.py` — delete the WebSocket route entirely.

### External Client Updates

- `hapax-mcp/` — update WebSocket URL from `:8051` to `:8052`
- Voice daemon — same URL update
- JSON message protocol unchanged

## Phase 4: Overlay Model (GPU Texture Sharing)

### Architecture

WGPU renders directly to the Tauri window's surface. Transparent webview composites on top via webkit2gtk. Zero-copy, sub-millisecond latency.

### Render Order Per Frame

```
1. WGPU renders visual surface → Tauri window surface
2. Transparent webview composites on top (webkit2gtk)
3. User sees: shaders behind, UI on top
```

### Proof-of-Concept (Required Before Full Implementation)

Throwaway branch. Tauri window with `transparent: true`, wgpu clears to bright red, webview shows a semi-transparent `<div>`. If red shows through → proceed. If not → fall back to Option A (shm-based frame transfer, same pipeline restructuring).

Estimated PoC scope: ~2 hours.

### Tauri Config

```json
{
  "transparent": true,
  "decorations": false
}
```

### `src-tauri/src/main.rs`

In `setup()`, extract raw window handle from Tauri's `WebviewWindow`:
```rust
let webview_window = app.get_webview_window("main").unwrap();
let raw_handle = webview_window.rwh_06_display_handle();
visual::bridge::start_visual_surface(app_handle.clone(), raw_handle);
```

### `src-tauri/src/visual/bridge.rs` — Major Rewrite

Kill winit entirely:
- No `EventLoop`, no `Window`, no `ApplicationHandler`
- Render loop becomes a `tokio::task` on a fixed-interval timer (~30fps) or vsync
- `VisualApp` simplifies to pipeline + state reader — no window lifecycle

### `src-tauri/src/visual/gpu.rs`

```rust
// Before (winit):
let surface = instance.create_surface(window)?;
// After (Tauri raw handle):
let surface = unsafe { instance.create_surface_from_raw(raw_handle) }?;
```

Surface config unchanged (Vulkan, Fifo, sRGB).

### `src-tauri/src/visual/output.rs`

`ShmOutput` becomes optional — keep for `visual-layer-aggregator` external consumer, but primary render path goes directly to window surface. No staging buffer needed for display.

### Kill List

- `winit` dependency (remove from `Cargo.toml`)
- `ApplicationHandler` impl (~100 lines in `bridge.rs`)
- Window creation, resize handling, event loop management
- Separate "hapax-visual" thread

### CSS

```css
html, body { background: transparent; }
```

UI panels, cards, sidebar get explicit opaque backgrounds. Terrain regions that should show the visual surface get `background: transparent`.

### Gap Fix

`control.json` is written by `set_visual_layer_param()` but never read by the compositor (opacities hardcoded in `CompositeUniforms::default()`). Wire `StateReader` to read `control.json` and apply opacities. ~20 lines in `state.rs`.

### PoC Result: Option B Failed

The PoC confirmed wgpu can create a surface from the Tauri window and render (red flash visible). However, webkit2gtk and wgpu cannot share the same Wayland surface — `Gdk-Message: Error flushing display: Protocol error` crashes the app immediately. This is a Wayland protocol limitation: dual GPU contexts on one surface are not supported.

**Using Option A (shm-based frame transfer) instead:**
- WGPU renders offscreen, writes JPEG/WebP to `/dev/shm`
- Tauri custom protocol (`hapax://visual/frame`) serves frames
- Frontend renders as fullscreen `background-image`
- ~33ms latency, acceptable for ambient procedural graphics
- Pipeline restructuring (kill winit, headless render) is identical — only the display path differs

## Phase 5: Dead Code Cleanup

### Deletions

| File/Code | Reason |
|-----------|--------|
| `IS_TAURI` constant and all ternary branches in `client.ts` | Only one path |
| `get()`, `put()`, `post()` HTTP helpers in `client.ts` | Frontend never does HTTP |
| `src/api/sse.ts` | Replaced by Tauri events (Phase 1) |
| `src/lib/commandRelay.ts` WebSocket client | Replaced by Tauri event bridge (Phase 3) |
| Vite proxy in `vite.config.ts` | Done in Phase 2 |
| `logos/api/routes/commands.py` WS route | Done in Phase 3 |
| CORS origins for `localhost:5173` in `app.py` | Done in Phase 2 |
| `"preview"` script in `package.json` | No standalone preview |
| `winit` in `Cargo.toml` | Done in Phase 4 |
| HMR relay config (port 1421) in `vite.config.ts` | Tauri dev handles HMR |

### Simplifications

- `commandRelay.ts` → rename to `commandBridge.ts`, ~20 lines (Tauri event listen/emit)
- `client.ts` → every method is a one-liner `invoke()` call
- `useSnapshotPoll`/`useBatchSnapshotPoll` → invoke-based, remove fetch error handling
- `tauri.conf.json` CSP → `default-src 'self'; style-src 'self' 'unsafe-inline'`

### Documentation Updates

- `hapax-council/CLAUDE.md` — remove dev server worktree mismatch warnings, Vite proxy references
- Relay protocol — note command relay port changed to `:8052`
- `hapax-mcp/` connection docs — update WebSocket URL

### Estimated Net Diff

~400 lines deleted, ~50 lines added.

## Officium Alignment

Once Logos migration is complete, the same pattern applies to `hapax-officium`:
1. Add `src-tauri/` scaffold (Officium has no Tauri code today)
2. Port `officium-web` API calls from fetch → invoke
3. Remove nginx deployment, ship as native app
4. Share the command relay architecture from Logos

Officium is simpler (no WGPU surface, no shaders) — essentially Phases 1-3 only.

## Risk Summary

| Risk | Severity | Mitigation |
|------|----------|------------|
| webkit2gtk transparency on Wayland | High | PoC before committing to Phase 4 |
| External tools break on relay port change | Medium | Keep JSON protocol identical, config-only change |
| SSE→Tauri event conversion misses edge cases | Low | Existing SSE tests validate behavior |
| `cargo tauri dev` slower than raw Vite | Low | Rust recompile only when Rust changes; Vite HMR still instant for frontend |
