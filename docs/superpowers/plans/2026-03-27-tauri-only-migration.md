# Tauri-Only Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Eliminate the browser/HTTP fallback path, making Tauri the sole runtime for Logos.

**Architecture:** Five-phase surgical excision. Each phase is a PR that leaves the system functional. Phase 1-2 kill the HTTP transport. Phase 3 moves the command relay into Rust. Phase 4 merges the WGPU surface into the Tauri window. Phase 5 removes dead code.

**Tech Stack:** Tauri 2, wgpu 24, tokio-tungstenite, React 19, TypeScript 5.9

**Spec:** `docs/superpowers/specs/2026-03-27-tauri-only-migration-design.md`

---

## File Structure

### Phase 1-2 (Kill HTTP fallback + strip proxy)

| Action | File | Responsibility |
|--------|------|----------------|
| Rewrite | `hapax-logos/src/api/client.ts` | All API calls → `invoke()` only |
| Create | `hapax-logos/src/api/stream.ts` | Tauri event-based stream consumer (replaces SSE) |
| Rewrite | `hapax-logos/src/hooks/useSSE.ts` | Use Tauri event streams instead of fetch |
| Modify | `hapax-logos/src/components/chat/ChatProvider.tsx` | Use stream API instead of `connectSSE` |
| Delete | `hapax-logos/src/api/sse.ts` | Dead — replaced by `stream.ts` |
| Delete | `hapax-logos/src/api/__tests__/sse.test.ts` | Tests for deleted module |
| Modify | `hapax-logos/vite.config.ts` | Remove proxy, HMR relay config |
| Modify | `hapax-logos/src-tauri/tauri.conf.json` | Tighten CSP |
| Modify | `hapax-logos/package.json` | Remove preview script |
| Modify | `logos/api/app.py:104-108` | Remove localhost CORS origins |
| Create | `hapax-logos/src-tauri/src/commands/streaming.rs` | SSE bridge: subscribe to FastAPI, emit Tauri events |
| Create | `hapax-logos/src-tauri/src/commands/proxy.rs` | Proxy commands for HTTP-only endpoints |
| Modify | `hapax-logos/src-tauri/src/commands/mod.rs` | Export streaming + proxy modules |
| Modify | `hapax-logos/src-tauri/src/main.rs` | Register streaming + proxy commands |
| Modify | `hapax-logos/src-tauri/Cargo.toml` | Add urlencoding, futures-util |
| Create | `hapax-logos/src/api/__tests__/client.test.ts` | Tests for invoke-only client |
| Create | `hapax-logos/src/api/__tests__/stream.test.ts` | Tests for Tauri event stream |

### Phase 3 (Command relay → Rust)

| Action | File | Responsibility |
|--------|------|----------------|
| Create | `hapax-logos/src-tauri/src/commands/relay.rs` | WebSocket server for external clients |
| Create | `hapax-logos/src/lib/commandBridge.ts` | Tauri event listen/emit bridge |
| Modify | `hapax-logos/src/contexts/CommandRegistryContext.tsx:184` | Use new bridge |
| Delete | `hapax-logos/src/lib/commandRelay.ts` | Dead — relay moved to Rust |
| Delete | `logos/api/routes/commands.py` | Dead — relay moved to Rust |
| Modify | `logos/api/app.py` | Remove command route registration |
| Modify | `hapax-logos/src-tauri/src/main.rs` | Start relay server in setup |

### Phase 4 (WGPU overlay merge)

| Action | File | Responsibility |
|--------|------|----------------|
| Rewrite | `hapax-logos/src-tauri/src/visual/bridge.rs` | Kill winit, use tokio render loop |
| Rewrite | `hapax-logos/src-tauri/src/visual/gpu.rs` | Accept Tauri window instead of winit window |
| Modify | `hapax-logos/src-tauri/src/visual/state.rs` | Read control.json for opacities |
| Modify | `hapax-logos/src-tauri/src/main.rs:82-89` | Pass window handle to visual surface |
| Modify | `hapax-logos/src-tauri/tauri.conf.json` | `transparent: true`, `decorations: false` |
| Modify | `hapax-logos/src-tauri/Cargo.toml` | Remove `winit` dependency |
| Modify | `hapax-logos/src/index.css` | `html, body { background: transparent }` |

### Phase 5 (Cleanup)

| Action | File | Responsibility |
|--------|------|----------------|
| Modify | `hapax-logos/src/hooks/useBatchSnapshotPoll.ts` | Replace fetch with invoke |
| Modify | `CLAUDE.md` | Remove dev server worktree warnings |

---

## Task 1: Rewrite `client.ts` to invoke-only

**Files:**
- Rewrite: `hapax-logos/src/api/client.ts`
- Create: `hapax-logos/src/api/__tests__/client.test.ts`
- Create: `hapax-logos/src-tauri/src/commands/proxy.rs`
- Modify: `hapax-logos/src-tauri/src/commands/mod.rs`
- Modify: `hapax-logos/src-tauri/src/main.rs`
- Modify: `hapax-logos/src-tauri/Cargo.toml`

- [ ] **Step 1: Write failing tests for invoke-only client**

```typescript
// hapax-logos/src/api/__tests__/client.test.ts
import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("@tauri-apps/api/core", () => ({
  invoke: vi.fn(),
}));

import { invoke } from "@tauri-apps/api/core";
import { api } from "../client";

const mockInvoke = vi.mocked(invoke);

describe("api client (invoke-only)", () => {
  beforeEach(() => {
    mockInvoke.mockReset();
  });

  it("health() calls invoke with get_health", async () => {
    mockInvoke.mockResolvedValue({ score: 95 });
    const result = await api.health();
    expect(mockInvoke).toHaveBeenCalledWith("get_health");
    expect(result).toEqual({ score: 95 });
  });

  it("setWorkingMode() passes mode arg", async () => {
    mockInvoke.mockResolvedValue({ mode: "research" });
    await api.setWorkingMode("research");
    expect(mockInvoke).toHaveBeenCalledWith("set_working_mode", { mode: "research" });
  });

  it("healthHistory() passes days arg", async () => {
    mockInvoke.mockResolvedValue({ entries: [] });
    await api.healthHistory(14);
    expect(mockInvoke).toHaveBeenCalledWith("get_health_history", { days: 14 });
  });

  it("selectEffect() passes preset arg", async () => {
    mockInvoke.mockResolvedValue({ status: "ok", preset: "ghost" });
    await api.selectEffect("ghost");
    expect(mockInvoke).toHaveBeenCalledWith("select_effect", { preset: "ghost" });
  });

  it("demo() passes id arg", async () => {
    mockInvoke.mockResolvedValue({ id: "abc", title: "test" });
    await api.demo("abc");
    expect(mockInvoke).toHaveBeenCalledWith("get_demo", { id: "abc" });
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd hapax-logos && pnpm test -- src/api/__tests__/client.test.ts --run`
Expected: FAIL — current client.ts has HTTP fallback that conflicts with the mock.

- [ ] **Step 3: Rewrite client.ts to invoke-only**

```typescript
// hapax-logos/src/api/client.ts
import { invoke } from "@tauri-apps/api/core";

export const api = {
  // --- Tier 1: Tauri commands (file I/O) ---
  health: () => invoke<import("./types").HealthSnapshot | null>("get_health"),
  gpu: () => invoke<import("./types").VramSnapshot | null>("get_gpu"),
  infrastructure: () => invoke<import("./types").Infrastructure>("get_infrastructure"),
  healthHistory: (days = 7) =>
    invoke<import("./types").HealthHistory>("get_health_history", { days }),
  workingMode: () =>
    invoke<import("./types").WorkingModeResponse>("get_working_mode"),
  setWorkingMode: (mode: "research" | "rnd") =>
    invoke<import("./types").WorkingModeResponse>("set_working_mode", { mode }),
  accommodations: () =>
    invoke<import("./types").AccommodationSet>("get_accommodations"),
  manual: () => invoke<import("./types").ManualResponse>("get_manual"),
  goals: () => invoke<import("./types").GoalSnapshot>("get_goals"),
  scout: () => invoke<import("./types").ScoutData | null>("get_scout"),
  scoutDecisions: () =>
    invoke<import("./types").ScoutDecisionsResponse>("get_scout_decisions"),
  drift: () => invoke<import("./types").DriftSummary | null>("get_drift"),
  management: () =>
    invoke<import("./types").ManagementSnapshot>("get_management"),
  nudges: () => invoke<import("./types").Nudge[]>("get_nudges"),
  readiness: () =>
    invoke<import("./types").ReadinessSnapshot>("get_readiness"),
  agents: () => invoke<import("./types").AgentInfo[]>("get_agents"),
  briefing: () =>
    invoke<import("./types").BriefingData | null>("get_briefing"),
  studio: () => invoke<import("./types").StudioSnapshot>("get_studio"),
  studioStreamInfo: () =>
    invoke<import("./types").StudioStreamInfo>("get_studio_stream_info"),
  perception: () =>
    invoke<import("./types").PerceptionState>("get_perception"),
  visualLayer: () =>
    invoke<import("./types").VisualLayerState>("get_visual_layer"),
  selectEffect: (preset: string) =>
    invoke<{ status: string; preset: string }>("select_effect", { preset }),
  demos: () => invoke<import("./types").Demo[]>("get_demos"),
  demo: (id: string) => invoke<import("./types").Demo>("get_demo", { id }),

  // --- Tier 2: Tauri commands (Qdrant/Langfuse direct) ---
  cost: () => invoke<import("./types").CostSnapshot>("get_cost"),

  // --- Studio (Rust proxy → FastAPI) ---
  compositorLive: () =>
    invoke<import("./types").LiveCompositorStatus>("get_compositor_live"),
  studioDisk: () =>
    invoke<import("./types").StudioDisk>("get_studio_disk"),
  enableRecording: () =>
    invoke<{ status: string }>("enable_recording"),
  disableRecording: () =>
    invoke<{ status: string }>("disable_recording"),

  // --- Tier 3: LLM orchestration (Rust proxy → FastAPI) ---
  copilot: () =>
    invoke<import("./types").CopilotResponse>("get_copilot"),
  scoutDecide: (component: string, decision: string, notes?: string) =>
    invoke<import("./types").ScoutDecision>("scout_decide", {
      component,
      decision,
      notes: notes ?? "",
    }),
  deleteDemo: (id: string) =>
    invoke<{ deleted: string }>("delete_demo", { id }),

  // --- Governance & Consent (Rust proxy → FastAPI) ---
  consentContracts: () => invoke<unknown[]>("get_consent_contracts"),
  consentTrace: (path?: string) =>
    invoke<unknown>("get_consent_trace", { path: path ?? null }),
  consentCoverage: () => invoke<unknown>("get_consent_coverage"),
  consentOverhead: () => invoke<unknown>("get_consent_overhead"),
  consentPrecedents: () => invoke<unknown[]>("get_consent_precedents"),
  governanceHeartbeat: () =>
    invoke<import("./types").GovernanceHeartbeat>("get_governance_heartbeat"),
  governanceCoverage: () => invoke<unknown>("get_governance_coverage"),
  governanceCarriers: () => invoke<unknown>("get_governance_carriers"),

  // --- Engine (Rust proxy → FastAPI) ---
  engineStatus: () => invoke<unknown>("get_engine_status"),
  engineRules: () => invoke<unknown[]>("get_engine_rules"),
  engineHistory: () => invoke<unknown[]>("get_engine_history"),

  // --- Profile (Rust proxy → FastAPI) ---
  profile: () => invoke<unknown>("get_profile"),
  profileDimension: (dim: string) =>
    invoke<unknown>("get_profile_dimension", { dim }),
  profilePending: () => invoke<unknown>("get_profile_pending"),

  // --- Insight Queries (Rust proxy → FastAPI) ---
  insightQueries: () =>
    invoke<import("./types").InsightQueryList>("get_insight_queries"),
  insightQuery: (id: string) =>
    invoke<import("./types").InsightQuery>("get_insight_query", { id }),
  runInsightQuery: (query: string) =>
    invoke<{ id: string; status: string }>("run_insight_query", { query }),
  refineInsightQuery: (
    query: string,
    parentId: string,
    priorResult: string,
    agentType: string,
  ) =>
    invoke<{ id: string; status: string }>("refine_insight_query", {
      query,
      parent_id: parentId,
      prior_result: priorResult,
      agent_type: agentType,
    }),
  deleteInsightQuery: (id: string) =>
    invoke<{ deleted: string }>("delete_insight_query", { id }),

  // --- Fortress (Rust proxy → FastAPI) ---
  fortressState: () =>
    invoke<import("./types").FortressState>("get_fortress_state"),
  fortressGovernance: () =>
    invoke<import("./types").FortressGovernance>("get_fortress_governance"),
  fortressGoals: () =>
    invoke<import("./types").FortressGoals>("get_fortress_goals"),
  fortressEvents: () =>
    invoke<import("./types").FortressEvents>("get_fortress_events"),
  fortressMetrics: () =>
    invoke<import("./types").FortressMetrics>("get_fortress_metrics"),
  fortressSessions: () =>
    invoke<import("./types").FortressSessions>("get_fortress_sessions"),
  fortressChronicle: () =>
    invoke<import("./types").FortressChronicle>("get_fortress_chronicle"),
};
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd hapax-logos && pnpm test -- src/api/__tests__/client.test.ts --run`
Expected: PASS

- [ ] **Step 5: Create Rust proxy commands for HTTP-only endpoints**

Create `hapax-logos/src-tauri/src/commands/proxy.rs` with proxy commands for all endpoints that were previously HTTP-only (studio recording, copilot, consent, governance, engine, profile, insight queries, fortress). Each command forwards to FastAPI at `http://127.0.0.1:8051/api/...` using `reqwest`.

Pattern for each command:
```rust
use reqwest::Client;
use serde_json::Value;
use std::sync::OnceLock;

static CLIENT: OnceLock<Client> = OnceLock::new();
fn client() -> &'static Client { CLIENT.get_or_init(Client::new) }
const API_BASE: &str = "http://127.0.0.1:8051";

async fn proxy_get(path: &str) -> Result<Value, String> {
    let resp = client().get(format!("{}{}", API_BASE, path))
        .send().await.map_err(|e| format!("proxy {}: {}", path, e))?;
    resp.json::<Value>().await.map_err(|e| format!("parse {}: {}", path, e))
}

async fn proxy_post(path: &str, body: Option<Value>) -> Result<Value, String> {
    let mut req = client().post(format!("{}{}", API_BASE, path));
    if let Some(b) = body { req = req.json(&b); }
    let resp = req.send().await.map_err(|e| format!("proxy {}: {}", path, e))?;
    resp.json::<Value>().await.map_err(|e| format!("parse {}: {}", path, e))
}

async fn proxy_delete(path: &str) -> Result<Value, String> {
    let resp = client().delete(format!("{}{}", API_BASE, path))
        .send().await.map_err(|e| format!("proxy {}: {}", path, e))?;
    resp.json::<Value>().await.map_err(|e| format!("parse {}: {}", path, e))
}

// Then one #[tauri::command] per endpoint:
#[tauri::command]
pub async fn get_compositor_live() -> Result<Value, String> {
    proxy_get("/api/studio/compositor/live").await
}
// ... (all 30+ proxy commands, one per HTTP-only endpoint)
```

Add `urlencoding = "2"` to Cargo.toml for query parameter encoding.

- [ ] **Step 6: Export proxy module and register commands in main.rs**

In `commands/mod.rs`, add `pub mod proxy;`.

In `main.rs` `invoke_handler`, register all proxy commands:
```rust
commands::proxy::get_compositor_live,
commands::proxy::get_studio_disk,
commands::proxy::enable_recording,
commands::proxy::disable_recording,
commands::proxy::get_copilot,
commands::proxy::scout_decide,
commands::proxy::delete_demo,
commands::proxy::get_consent_contracts,
commands::proxy::get_consent_trace,
commands::proxy::get_consent_coverage,
commands::proxy::get_consent_overhead,
commands::proxy::get_consent_precedents,
commands::proxy::get_governance_heartbeat,
commands::proxy::get_governance_coverage,
commands::proxy::get_governance_carriers,
commands::proxy::get_engine_status,
commands::proxy::get_engine_rules,
commands::proxy::get_engine_history,
commands::proxy::get_profile,
commands::proxy::get_profile_dimension,
commands::proxy::get_profile_pending,
commands::proxy::get_insight_queries,
commands::proxy::get_insight_query,
commands::proxy::run_insight_query,
commands::proxy::refine_insight_query,
commands::proxy::delete_insight_query,
commands::proxy::get_fortress_state,
commands::proxy::get_fortress_governance,
commands::proxy::get_fortress_goals,
commands::proxy::get_fortress_events,
commands::proxy::get_fortress_metrics,
commands::proxy::get_fortress_sessions,
commands::proxy::get_fortress_chronicle,
```

- [ ] **Step 7: Build Rust to verify compilation**

Run: `cd hapax-logos && cargo build -p hapax-logos`
Expected: Compiles.

- [ ] **Step 8: Run all frontend tests**

Run: `cd hapax-logos && pnpm test --run`
Expected: All pass (SSE tests may fail — Task 2's concern).

- [ ] **Step 9: Commit**

```bash
cd ~/projects/hapax-council/hapax-logos
git add src/api/client.ts src/api/__tests__/client.test.ts \
  src-tauri/src/commands/proxy.rs src-tauri/src/commands/mod.rs \
  src-tauri/src/main.rs src-tauri/Cargo.toml
git commit -m "feat: rewrite API client to invoke-only, add Rust proxy commands"
```

---

## Task 2: Replace SSE with Tauri event streams

**Files:**
- Create: `hapax-logos/src/api/stream.ts`
- Create: `hapax-logos/src/api/__tests__/stream.test.ts`
- Create: `hapax-logos/src-tauri/src/commands/streaming.rs`
- Rewrite: `hapax-logos/src/hooks/useSSE.ts`
- Modify: `hapax-logos/src/components/chat/ChatProvider.tsx`
- Delete: `hapax-logos/src/api/sse.ts`
- Delete: `hapax-logos/src/api/__tests__/sse.test.ts`

- [ ] **Step 1: Create the Rust SSE bridge**

Create `hapax-logos/src-tauri/src/commands/streaming.rs`. This module:
- Exposes `start_stream(path, method, body)` → returns `stream_id`
- Internally subscribes to FastAPI's SSE endpoint using `reqwest` streaming
- Parses SSE format (event:/data: lines) from the byte stream
- Re-emits parsed events as Tauri events: `stream:{stream_id}` with `{ type: "event", event, data }`
- Emits `{ type: "done" }` when the stream ends
- Emits `{ type: "error", data }` on failure
- Exposes `cancel_stream(stream_id)` using tokio oneshot channels
- Exposes `cancel_stream_and_server(stream_id)` that also DELETEs `/api/agents/runs/current`
- Uses `futures_util::StreamExt` for async byte stream iteration
- Uses `tokio::select!` for cancellation

Add `futures-util = "0.3"` to Cargo.toml if not already transitively available.
Export in `commands/mod.rs`: `pub mod streaming;`
Register in `main.rs`: `commands::streaming::start_stream`, `commands::streaming::cancel_stream`, `commands::streaming::cancel_stream_and_server`

- [ ] **Step 2: Build Rust to verify compilation**

Run: `cd hapax-logos && cargo build -p hapax-logos`
Expected: Compiles.

- [ ] **Step 3: Create TypeScript stream consumer**

```typescript
// hapax-logos/src/api/stream.ts
import { invoke } from "@tauri-apps/api/core";
import { listen, type UnlistenFn } from "@tauri-apps/api/event";

export interface StreamEvent {
  event: string;
  data: string;
}

export type StreamCallback = (event: StreamEvent) => void;

interface StreamHandle {
  streamId: number;
  cancel: () => Promise<void>;
}

export async function startStream(
  path: string,
  options: {
    method?: string;
    body?: unknown;
    onEvent: StreamCallback;
    onDone?: () => void;
    onError?: (error: string) => void;
  },
): Promise<StreamHandle> {
  const streamId = await invoke<number>("start_stream", {
    path,
    method: options.method ?? "POST",
    body: options.body ?? null,
  });

  const eventName = `stream:${streamId}`;
  const unlisten: UnlistenFn = await listen(eventName, (event) => {
    const payload = event.payload as {
      type: string;
      event?: string;
      data?: string;
    };
    if (payload.type === "event" && payload.event && payload.data) {
      options.onEvent({ event: payload.event, data: payload.data });
    } else if (payload.type === "error") {
      options.onError?.(payload.data ?? "Unknown error");
    } else if (payload.type === "done") {
      options.onDone?.();
      unlisten();
    }
  });

  return {
    streamId,
    cancel: async () => {
      unlisten();
      await invoke("cancel_stream", { streamId });
    },
  };
}

export async function startCancellableStream(
  path: string,
  options: Parameters<typeof startStream>[1],
): Promise<StreamHandle> {
  const handle = await startStream(path, options);
  return {
    ...handle,
    cancel: async () => {
      await invoke("cancel_stream_and_server", {
        streamId: handle.streamId,
      });
    },
  };
}
```

- [ ] **Step 4: Write tests for stream.ts**

```typescript
// hapax-logos/src/api/__tests__/stream.test.ts
import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("@tauri-apps/api/core", () => ({ invoke: vi.fn() }));
vi.mock("@tauri-apps/api/event", () => ({ listen: vi.fn() }));

import { invoke } from "@tauri-apps/api/core";
import { listen } from "@tauri-apps/api/event";
import { startStream } from "../stream";

const mockInvoke = vi.mocked(invoke);
const mockListen = vi.mocked(listen);

describe("startStream", () => {
  beforeEach(() => {
    mockInvoke.mockReset();
    mockListen.mockReset();
  });

  it("invokes start_stream and listens for events", async () => {
    mockInvoke.mockResolvedValue(42);
    mockListen.mockResolvedValue(vi.fn());
    const handle = await startStream("/api/chat/send", {
      body: { message: "hi" },
      onEvent: vi.fn(),
    });
    expect(mockInvoke).toHaveBeenCalledWith("start_stream", {
      path: "/api/chat/send",
      method: "POST",
      body: { message: "hi" },
    });
    expect(mockListen).toHaveBeenCalledWith("stream:42", expect.any(Function));
    expect(handle.streamId).toBe(42);
  });

  it("cancel calls invoke and unlisten", async () => {
    mockInvoke.mockResolvedValueOnce(7);
    const unlisten = vi.fn();
    mockListen.mockResolvedValue(unlisten);
    mockInvoke.mockResolvedValueOnce(true);
    const handle = await startStream("/api/test", { onEvent: vi.fn() });
    await handle.cancel();
    expect(unlisten).toHaveBeenCalled();
    expect(mockInvoke).toHaveBeenCalledWith("cancel_stream", { streamId: 7 });
  });
});
```

- [ ] **Step 5: Run stream tests**

Run: `cd hapax-logos && pnpm test -- src/api/__tests__/stream.test.ts --run`
Expected: PASS

- [ ] **Step 6: Rewrite useSSE hook**

Replace `connectSSE` with `startCancellableStream`. The hook signature stays identical (`lines`, `isRunning`, `error`, `start`, `cancel`, `clear`). The `start` callback now calls `startCancellableStream(path, ...)` instead of `connectSSE(url, ...)`. Cancel calls `handle.cancel()` instead of `controller.abort()`.

- [ ] **Step 7: Update ChatProvider.tsx**

Replace `import { connectSSE } from "../../api/sse"` with `import { startStream } from "../../api/stream"`. Update the two `connectSSE(...)` call sites (lines ~245 and ~359) to use `startStream(...)`. Change `controllerRef.current?.abort()` to `handleRef.current?.cancel()`.

- [ ] **Step 8: Delete sse.ts and its tests**

```bash
rm hapax-logos/src/api/sse.ts hapax-logos/src/api/__tests__/sse.test.ts
```

- [ ] **Step 9: Run all tests**

Run: `cd hapax-logos && pnpm test --run`
Expected: All pass.

- [ ] **Step 10: Commit**

```bash
cd ~/projects/hapax-council/hapax-logos
git add src/api/stream.ts src/api/__tests__/stream.test.ts \
  src/hooks/useSSE.ts src/components/chat/ChatProvider.tsx \
  src-tauri/src/commands/streaming.rs src-tauri/src/commands/mod.rs \
  src-tauri/src/main.rs src-tauri/Cargo.toml
git rm src/api/sse.ts src/api/__tests__/sse.test.ts
git commit -m "feat: replace SSE with Tauri event streams"
```

---

## Task 3: Strip Vite proxy and lock down config

**Files:**
- Modify: `hapax-logos/vite.config.ts`
- Modify: `hapax-logos/src-tauri/tauri.conf.json`
- Modify: `hapax-logos/package.json`
- Modify: `logos/api/app.py`

- [ ] **Step 1: Strip vite.config.ts**

Remove: proxy block (lines 22-24), HMR relay config (lines 14-21), `server.host` (line 14).
Keep: `port: 5173`, `strictPort: true`, `watch.ignored`, everything else.

- [ ] **Step 2: Tighten CSP in tauri.conf.json**

Replace CSP line (line 23) — remove `connect-src` entries for `http://127.0.0.1:8051`, `ws://127.0.0.1:*`, `http://localhost:*`. Remove `img-src`/`media-src` entries for `http://127.0.0.1:8051`.

New CSP: `"default-src 'self'; img-src 'self' blob: data:; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-eval'"`

- [ ] **Step 3: Remove preview script from package.json**

Delete `"preview": "vite preview",` from scripts.

- [ ] **Step 4: Remove localhost CORS from FastAPI**

In `logos/api/app.py` lines 104-108, remove `"http://localhost:5173"` and `"http://127.0.0.1:5173"` from `allow_origins`. Keep only `"tauri://localhost"`.

- [ ] **Step 5: Build and test**

Run: `cd hapax-logos && cargo build -p hapax-logos && pnpm test --run`
Expected: All pass.

- [ ] **Step 6: Commit**

```bash
cd ~/projects/hapax-council
git add hapax-logos/vite.config.ts hapax-logos/src-tauri/tauri.conf.json \
  hapax-logos/package.json logos/api/app.py
git commit -m "feat: strip Vite proxy, tighten CSP, remove browser CORS"
```

---

## Task 4: Create PR for Phases 1-2

- [ ] **Step 1: Run full test suite**

Run: `cd hapax-logos && pnpm test --run && cargo test -p hapax-logos`

- [ ] **Step 2: Push and create PR**

```bash
cd ~/projects/hapax-council && git push -u origin HEAD
gh pr create --title "feat: Tauri-only runtime (Phases 1-2)" --body "$(cat <<'EOF'
## Summary
- Rewrite API client to invoke-only — all HTTP helpers deleted
- Add Rust proxy commands for browser-only HTTP endpoints
- Replace SSE fetch with Tauri event streams
- Strip Vite proxy, tighten CSP, remove browser CORS

## Test plan
- [ ] `cargo tauri dev` launches, all API calls work
- [ ] Chat/agent streaming works via Tauri events
- [ ] `pnpm test --run` and `cargo build` pass

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

- [ ] **Step 3: Monitor CI, fix failures, merge when green**

---

## Task 5: Move command relay to Rust (Phase 3)

**Files:**
- Create: `hapax-logos/src-tauri/src/commands/relay.rs`
- Create: `hapax-logos/src/lib/commandBridge.ts`
- Modify: `hapax-logos/src/contexts/CommandRegistryContext.tsx`
- Delete: `hapax-logos/src/lib/commandRelay.ts`
- Delete: `logos/api/routes/commands.py`
- Modify: `logos/api/app.py`

- [ ] **Step 1: Create Rust WebSocket relay server**

Create `hapax-logos/src-tauri/src/commands/relay.rs`. This module:
- Starts a `tokio-tungstenite` WebSocket server on port 8052 (configurable via `HAPAX_RELAY_PORT`)
- Accepts external client connections (MCP, voice)
- Receives `execute`, `query`, `list` messages (same JSON protocol as current FastAPI relay)
- Emits Tauri events to the frontend: `command:execute`, `command:query`, `command:list`
- Receives results from the frontend via `command:result` Tauri events
- Correlates request/response using message IDs with oneshot channels
- Forwards registry events from the frontend to subscribed external clients
- Uses `broadcast::channel` for event fan-out to multiple external clients
- 10-second timeout per request

Add `tokio-tungstenite = "0.26"` to Cargo.toml.
Export in `commands/mod.rs`: `pub mod relay;`
Call `commands::relay::start_relay(app.handle().clone())` in `main.rs` `setup()`.

- [ ] **Step 2: Create frontend command bridge**

```typescript
// hapax-logos/src/lib/commandBridge.ts
import { emit, listen, type UnlistenFn } from "@tauri-apps/api/event";
import type { CommandRegistry } from "./commandRegistry";

export function connectCommandBridge(registry: CommandRegistry): () => void {
  const unlisteners: Promise<UnlistenFn>[] = [];

  unlisteners.push(
    listen("command:execute", async (event) => {
      const msg = event.payload as {
        id?: string;
        path: string;
        args?: Record<string, unknown>;
      };
      const result = await registry.execute(msg.path, msg.args ?? {}, "relay");
      if (msg.id) {
        await emit("command:result", { type: "result", id: msg.id, data: result });
      }
    }),
  );

  unlisteners.push(
    listen("command:query", async (event) => {
      const msg = event.payload as { id?: string; path: string };
      const value = registry.query(msg.path);
      if (msg.id) {
        await emit("command:result", {
          type: "result",
          id: msg.id,
          data: { ok: true, state: value },
        });
      }
    }),
  );

  unlisteners.push(
    listen("command:list", async (event) => {
      const msg = event.payload as { id?: string; domain?: string };
      const commands = registry.list(msg.domain).map((c) => ({
        path: c.path,
        description: c.description,
        args: c.args,
      }));
      if (msg.id) {
        await emit("command:result", {
          type: "result",
          id: msg.id,
          data: { ok: true, state: commands },
        });
      }
    }),
  );

  const unsub = registry.subscribe(/./, (event) => {
    emit("command:event", {
      type: "event",
      path: event.path,
      args: event.args,
      result: event.result,
      timestamp: event.timestamp,
    });
  });

  return () => {
    unsub();
    unlisteners.forEach((p) => p.then((fn) => fn()));
  };
}
```

- [ ] **Step 3: Update CommandRegistryContext.tsx**

Change import: `connectCommandRelay` → `connectCommandBridge` from `"../lib/commandBridge"`.
Change line 184: `connectCommandRelay(registry)` → `connectCommandBridge(registry)`.

- [ ] **Step 4: Delete old relay files**

```bash
rm hapax-logos/src/lib/commandRelay.ts
rm logos/api/routes/commands.py
```

Remove the command route registration from `logos/api/app.py`.

- [ ] **Step 5: Update hapax-mcp WebSocket URL**

Change the WebSocket URL in `hapax-mcp/` from `ws://127.0.0.1:8051/ws/commands` to `ws://127.0.0.1:8052/ws/commands`.

- [ ] **Step 6: Build and test**

Run: `cd hapax-logos && cargo build -p hapax-logos && pnpm test --run`

- [ ] **Step 7: Commit and PR**

```bash
cd ~/projects/hapax-council
git add hapax-logos/src-tauri/src/commands/relay.rs hapax-logos/src/lib/commandBridge.ts \
  hapax-logos/src/contexts/CommandRegistryContext.tsx \
  hapax-logos/src-tauri/Cargo.toml logos/api/app.py
git rm hapax-logos/src/lib/commandRelay.ts logos/api/routes/commands.py
git commit -m "feat: move command relay from FastAPI to Tauri Rust"
git push -u origin HEAD
gh pr create --title "feat: command relay moves to Tauri Rust (Phase 3)" --body "$(cat <<'EOF'
## Summary
- WebSocket command relay now in Tauri Rust backend (port 8052)
- Frontend uses Tauri events instead of WebSocket client
- FastAPI WebSocket route deleted

## Test plan
- [ ] MCP tools execute commands via WebSocket on :8052
- [ ] Registry events forwarded to external subscribers
- [ ] `cargo build` and `pnpm test` pass

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

---

## Task 6: PoC — WGPU behind transparent webview (Phase 4 gate)

**This determines Phase 4 approach: GPU texture sharing (Option B) vs shm fallback (Option A).**

- [ ] **Step 1: Create throwaway PoC branch**

```bash
cd ~/projects/hapax-council && git checkout -b poc/transparent-wgpu
```

- [ ] **Step 2: Enable transparency**

In `tauri.conf.json`, add `"transparent": true`, `"decorations": false` to window config.
In `index.css`, add `html, body { background: transparent !important; }`.

- [ ] **Step 3: Modify gpu.rs to use Tauri window handle**

Replace `Arc<Window>` with `&tauri::WebviewWindow` in `GpuContext::new()`. Use `instance.create_surface(window)` with Tauri's window.

- [ ] **Step 4: Modify main.rs to pass window handle**

In `setup()`, get the webview window and pass it to a test render loop that clears to bright red.

- [ ] **Step 5: Test**

Run: `cd hapax-logos && cargo tauri dev`
**Success:** Red visible behind semi-transparent UI → proceed with Option B.
**Failure:** Black background → fall back to Option A (shm frame transfer).

- [ ] **Step 6: Clean up**

```bash
git checkout main && git branch -D poc/transparent-wgpu
```

---

## Task 7: Merge WGPU into Tauri window (Phase 4)

**Depends on Task 6 PoC result.**

- [ ] **Step 1: Enable transparency in tauri.conf.json**

Add `"transparent": true`, `"decorations": false`.

- [ ] **Step 2: Rewrite gpu.rs**

Accept `&tauri::WebviewWindow` instead of `Arc<winit::window::Window>`. Use Tauri's window for surface creation. Get window size from `window.inner_size()`.

- [ ] **Step 3: Rewrite bridge.rs**

Kill winit entirely. Replace `VisualApp` + `ApplicationHandler` + winit event loop with a tokio task that:
- Creates GpuContext from Tauri window
- Initializes all 6 techniques + compositor + postprocess + shm output
- Runs a `tokio::time::interval(33ms)` render loop
- Same render pipeline as before (transplant from `VisualApp::render`)
- Emits `visual:frame-stats` every 300 frames

- [ ] **Step 4: Update main.rs**

Pass `app.get_webview_window("main")` to `visual::bridge::start_visual_surface()` instead of calling `spawn_visual_surface()`.

- [ ] **Step 5: Wire control.json into StateReader**

Add `layer_opacities: HashMap<String, f32>` to `SmoothedParams`. In `poll()`, read `/dev/shm/hapax-visual/control.json` and apply opacities.

- [ ] **Step 6: Remove winit from Cargo.toml**

Delete `winit = "0.30"`.

- [ ] **Step 7: Set transparent CSS**

`html, body { background: transparent; }` in `index.css`. Ensure opaque panels have explicit backgrounds.

- [ ] **Step 8: Build and test**

Run: `cd hapax-logos && cargo build -p hapax-logos && cargo tauri dev`
Expected: Shaders render behind transparent webview.

- [ ] **Step 9: Commit and PR**

```bash
git commit -m "feat: merge WGPU surface into Tauri window, kill winit"
git push -u origin HEAD
gh pr create --title "feat: WGPU renders behind transparent Tauri webview (Phase 4)" --body "$(cat <<'EOF'
## Summary
- Visual surface renders directly to Tauri window (no separate winit window)
- Transparent webview composites React UI on top
- winit removed, control.json wired for opacity control

## Test plan
- [ ] `cargo tauri dev` shows shaders behind UI
- [ ] All 6 techniques render correctly
- [ ] `HAPAX_NO_VISUAL=1` still works

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

---

## Task 8: Dead code cleanup (Phase 5)

- [ ] **Step 1: Convert useBatchSnapshotPoll**

Add `get_camera_batch` Rust proxy command. Update `fetchBatch()` to use `invoke`.

- [ ] **Step 2: Remove `sseUrl` from client.ts if still present**

- [ ] **Step 3: Update CLAUDE.md**

Remove dev server worktree mismatch warnings, Vite proxy references. Update command relay port to 8052.

- [ ] **Step 4: Test and commit**

```bash
pnpm test --run && cargo build -p hapax-logos
git commit -m "chore: dead code cleanup for Tauri-only runtime"
git push -u origin HEAD
gh pr create --title "chore: Tauri-only cleanup (Phase 5)" --body "..."
```

---

## Dependency Graph

```
Task 1 → Task 2 → Task 3 → Task 4 (PR Phases 1-2)
                                ↓
                            Task 5 (Phase 3 PR)
                                ↓
                            Task 6 (PoC)
                                ↓
                            Task 7 (Phase 4 PR)
                                ↓
                            Task 8 (Phase 5 PR)
```
