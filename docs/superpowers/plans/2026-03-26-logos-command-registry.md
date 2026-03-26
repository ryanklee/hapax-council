# Logos Command Registry Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace 6+ scattered keyboard handlers with a centralized, hierarchical command registry that serves keyboard, Playwright, MCP, and voice consumers through a single dispatch surface.

**Architecture:** A framework-agnostic `CommandRegistry` class manages command registration, execution, queries, event subscription, and sequences. A React context (`CommandRegistryProvider`) wires it to existing contexts (TerrainContext, GroundStudioContext, ClassificationOverlayContext) and exposes it as `window.__logos`. A single `useKeyboardAdapter` replaces all keyboard handlers. A FastAPI WebSocket relay on `:8051/ws/commands` bridges external consumers.

**Tech Stack:** TypeScript, React 19, vitest + testing-library, FastAPI + websockets (Python)

**Spec:** `docs/superpowers/specs/2026-03-26-logos-command-registry-design.md`

---

## File Map

### New files (frontend — `hapax-logos/src/`)

| File | Responsibility |
|------|---------------|
| `lib/commandRegistry.ts` | Core registry class — register, execute, query, subscribe, sequences. Framework-agnostic. |
| `lib/commands/terrain.ts` | Terrain domain: focus, depth.set, depth.cycle, collapse. Wraps TerrainContext actions. |
| `lib/commands/studio.ts` | Studio domain: smooth.*, preset.*, recording.*. Wraps GroundStudioContext + fetch calls. |
| `lib/commands/overlay.ts` | Overlay domain: set, clear, toggle. Wraps TerrainContext overlay actions. |
| `lib/commands/detection.ts` | Detection domain: tier.*, visibility.*. Wraps ClassificationOverlayContext. |
| `lib/commands/nav.ts` | Nav domain: go, manual.toggle, palette.toggle. Wraps react-router navigate. |
| `lib/commands/split.ts` | Split domain: open, close, toggle, fullscreen.toggle. Wraps TerrainContext split actions. |
| `lib/commands/data.ts` | Data domain: refresh. Wraps react-query invalidation. |
| `lib/commands/sequences.ts` | Built-in sequences: studio.enter, studio.exit, escape. |
| `lib/keyboardAdapter.ts` | Single keydown handler + KEY_MAP + `when` clause evaluation. |
| `lib/commandRelay.ts` | WebSocket client connecting to `:8051/ws/commands`, forwarding commands to registry. |
| `contexts/CommandRegistryContext.tsx` | React context + provider. Registers all domains, exposes `window.__logos`. |
| `components/terrain/CommandFeedback.tsx` | Toast component for command failures. |

### New files (backend — `logos/api/routes/`)

| File | Responsibility |
|------|---------------|
| `logos/api/routes/commands.py` | WebSocket relay endpoint: `/ws/commands`. Dumb pipe between external clients and frontend. |

### Modified files

| File | Change |
|------|--------|
| `components/terrain/TerrainLayout.tsx` | Remove `handleKey`, `DetectionKeyboardHandler`, `StudioKeyboardHandler`. Add `<CommandFeedback />`. |
| `hooks/useKeyboardShortcuts.ts` | Delete entirely. |
| `hooks/useStudioShortcuts.ts` | Delete entirely. |
| `pages/TerrainPage.tsx` | Remove `TerrainChrome` keyboard handler. Wrap with `CommandRegistryProvider`. |
| `pages/HapaxPage.tsx` | Remove keyboard handler (lines 234–247). |
| `components/shared/CommandPalette.tsx` | Read commands from registry instead of hardcoded list. |
| `logos/api/app.py` | Register commands router. |

---

## Task 1: Core CommandRegistry class

**Files:**
- Create: `hapax-logos/src/lib/commandRegistry.ts`
- Test: `hapax-logos/src/lib/__tests__/commandRegistry.test.ts`

- [ ] **Step 1: Write failing tests for command registration and execution**

```typescript
// hapax-logos/src/lib/__tests__/commandRegistry.test.ts
import { describe, it, expect, vi } from "vitest";
import { CommandRegistry } from "../commandRegistry";

describe("CommandRegistry", () => {
  it("registers and executes a command", async () => {
    const registry = new CommandRegistry();
    registry.register({
      path: "test.greet",
      description: "Say hello",
      args: { name: { type: "string", required: true } },
      execute: (args) => ({ ok: true, state: `hello ${args.name}` }),
    });

    const result = await registry.execute("test.greet", { name: "world" });
    expect(result).toEqual({ ok: true, state: "hello world" });
  });

  it("returns error for unknown command", async () => {
    const registry = new CommandRegistry();
    const result = await registry.execute("nope.nope");
    expect(result.ok).toBe(false);
    expect(result.error).toMatch(/unknown command/i);
  });

  it("lists commands filtered by domain", () => {
    const registry = new CommandRegistry();
    registry.register({
      path: "terrain.focus",
      description: "Focus region",
      execute: () => ({ ok: true }),
    });
    registry.register({
      path: "studio.smooth.enable",
      description: "Enable smooth",
      execute: () => ({ ok: true }),
    });

    const terrainCmds = registry.list("terrain");
    expect(terrainCmds).toHaveLength(1);
    expect(terrainCmds[0].path).toBe("terrain.focus");

    const allCmds = registry.list();
    expect(allCmds).toHaveLength(2);
  });

  it("queries registered state", () => {
    const registry = new CommandRegistry();
    registry.registerQuery("terrain.focusedRegion", () => "ground");
    expect(registry.query("terrain.focusedRegion")).toBe("ground");
  });

  it("returns undefined for unknown query", () => {
    const registry = new CommandRegistry();
    expect(registry.query("nope")).toBeUndefined();
  });

  it("emits events on execute", async () => {
    const registry = new CommandRegistry();
    const listener = vi.fn();
    registry.register({
      path: "test.ping",
      description: "Ping",
      execute: () => ({ ok: true, state: "pong" }),
    });
    registry.subscribe("test.ping", listener);

    await registry.execute("test.ping", {});
    expect(listener).toHaveBeenCalledTimes(1);
    expect(listener).toHaveBeenCalledWith(
      expect.objectContaining({
        path: "test.ping",
        args: {},
        result: { ok: true, state: "pong" },
      }),
    );
  });

  it("subscribe with regex matches multiple paths", async () => {
    const registry = new CommandRegistry();
    const listener = vi.fn();
    registry.register({
      path: "studio.smooth.enable",
      description: "Enable smooth",
      execute: () => ({ ok: true }),
    });
    registry.register({
      path: "studio.preset.activate",
      description: "Activate preset",
      execute: () => ({ ok: true }),
    });
    registry.subscribe(/^studio\./, listener);

    await registry.execute("studio.smooth.enable");
    await registry.execute("studio.preset.activate", { name: "ghost" });
    expect(listener).toHaveBeenCalledTimes(2);
  });

  it("unsubscribe stops events", async () => {
    const registry = new CommandRegistry();
    const listener = vi.fn();
    registry.register({
      path: "test.ping",
      description: "Ping",
      execute: () => ({ ok: true }),
    });
    const unsub = registry.subscribe("test.ping", listener);

    await registry.execute("test.ping");
    expect(listener).toHaveBeenCalledTimes(1);

    unsub();
    await registry.execute("test.ping");
    expect(listener).toHaveBeenCalledTimes(1);
  });

  it("getState aggregates all queries", () => {
    const registry = new CommandRegistry();
    registry.registerQuery("terrain.focusedRegion", () => "ground");
    registry.registerQuery("studio.smoothMode", () => false);

    const state = registry.getState();
    expect(state).toEqual({
      "terrain.focusedRegion": "ground",
      "studio.smoothMode": false,
    });
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd hapax-logos && pnpm vitest run src/lib/__tests__/commandRegistry.test.ts`
Expected: FAIL — module not found

- [ ] **Step 3: Implement CommandRegistry**

```typescript
// hapax-logos/src/lib/commandRegistry.ts

export interface ArgDef {
  type: "string" | "number" | "boolean";
  required?: boolean;
  enum?: string[];
  description?: string;
}

export interface CommandResult {
  ok: boolean;
  error?: string;
  state?: unknown;
}

export interface CommandDef {
  path: string;
  description: string;
  args?: Record<string, ArgDef>;
  execute: (args: Record<string, unknown>) => CommandResult | Promise<CommandResult>;
}

export interface CommandEvent {
  path: string;
  args: Record<string, unknown>;
  result: CommandResult;
  timestamp: number;
  source?: string;
}

type Listener = (event: CommandEvent) => void;

interface Subscription {
  pattern: string | RegExp;
  listener: Listener;
}

export class CommandRegistry {
  private commands = new Map<string, CommandDef>();
  private queries = new Map<string, () => unknown>();
  private subscriptions: Subscription[] = [];
  debug = false;

  register(def: CommandDef): void {
    this.commands.set(def.path, def);
  }

  unregister(path: string): void {
    this.commands.delete(path);
  }

  registerQuery(path: string, fn: () => unknown): void {
    this.queries.set(path, fn);
  }

  unregisterQuery(path: string): void {
    this.queries.delete(path);
  }

  async execute(
    path: string,
    args: Record<string, unknown> = {},
    source?: string,
  ): Promise<CommandResult> {
    const def = this.commands.get(path);
    if (!def) {
      return { ok: false, error: `Unknown command: ${path}` };
    }

    let result: CommandResult;
    try {
      result = await def.execute(args);
    } catch (err) {
      result = { ok: false, error: String(err) };
    }

    const event: CommandEvent = {
      path,
      args,
      result,
      timestamp: Date.now(),
      source,
    };

    this.emit(event);
    return result;
  }

  query(path: string): unknown {
    const fn = this.queries.get(path);
    return fn ? fn() : undefined;
  }

  getState(): Record<string, unknown> {
    const state: Record<string, unknown> = {};
    for (const [path, fn] of this.queries) {
      state[path] = fn();
    }
    return state;
  }

  list(domain?: string): CommandDef[] {
    const all = Array.from(this.commands.values());
    if (!domain) return all;
    return all.filter((c) => c.path.startsWith(domain + "."));
  }

  subscribe(pattern: string | RegExp, listener: Listener): () => void {
    const sub: Subscription = { pattern, listener };
    this.subscriptions.push(sub);
    return () => {
      const idx = this.subscriptions.indexOf(sub);
      if (idx !== -1) this.subscriptions.splice(idx, 1);
    };
  }

  private emit(event: CommandEvent): void {
    if (this.debug) {
      console.log(`[logos] ${event.path}`, event.args, event.result);
    }
    for (const sub of this.subscriptions) {
      if (this.matches(sub.pattern, event.path)) {
        try {
          sub.listener(event);
        } catch (err) {
          console.error(`[logos] subscriber error for ${event.path}:`, err);
        }
      }
    }
  }

  private matches(pattern: string | RegExp, path: string): boolean {
    if (typeof pattern === "string") return pattern === path;
    return pattern.test(path);
  }
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd hapax-logos && pnpm vitest run src/lib/__tests__/commandRegistry.test.ts`
Expected: All 8 tests PASS

- [ ] **Step 5: Commit**

```bash
git add hapax-logos/src/lib/commandRegistry.ts hapax-logos/src/lib/__tests__/commandRegistry.test.ts
git commit -m "feat(logos): add CommandRegistry core class with tests"
```

---

## Task 2: Sequence support

**Files:**
- Modify: `hapax-logos/src/lib/commandRegistry.ts`
- Test: `hapax-logos/src/lib/__tests__/commandRegistry.test.ts`

- [ ] **Step 1: Add failing tests for sequences**

Append to `commandRegistry.test.ts`:

```typescript
describe("Sequences", () => {
  it("executes steps in order", async () => {
    const registry = new CommandRegistry();
    const order: string[] = [];
    registry.register({
      path: "a",
      description: "Step A",
      execute: () => { order.push("a"); return { ok: true }; },
    });
    registry.register({
      path: "b",
      description: "Step B",
      execute: () => { order.push("b"); return { ok: true }; },
    });

    registry.sequence("ab", [
      { command: "a" },
      { command: "b" },
    ]);

    const result = await registry.execute("ab");
    expect(result.ok).toBe(true);
    expect(order).toEqual(["a", "b"]);
  });

  it("stops on first failure by default", async () => {
    const registry = new CommandRegistry();
    registry.register({
      path: "fail",
      description: "Fails",
      execute: () => ({ ok: false, error: "boom" }),
    });
    registry.register({
      path: "never",
      description: "Should not run",
      execute: () => { throw new Error("should not reach"); },
    });

    registry.sequence("failseq", [
      { command: "fail" },
      { command: "never" },
    ]);

    const result = await registry.execute("failseq");
    expect(result.ok).toBe(false);
    expect(result.error).toBe("boom");
  });

  it("stopOnSuccess stops at first success", async () => {
    const registry = new CommandRegistry();
    const ran: string[] = [];
    registry.register({
      path: "noop",
      description: "No-op",
      execute: () => { ran.push("noop"); return { ok: false, error: "nothing to do" }; },
    });
    registry.register({
      path: "action",
      description: "Does something",
      execute: () => { ran.push("action"); return { ok: true, state: "did it" }; },
    });
    registry.register({
      path: "extra",
      description: "Should not run",
      execute: () => { ran.push("extra"); return { ok: true }; },
    });

    registry.sequence("escape", [
      { command: "noop" },
      { command: "action" },
      { command: "extra" },
    ], { stopOnSuccess: true });

    const result = await registry.execute("escape");
    expect(result.ok).toBe(true);
    expect(result.state).toBe("did it");
    expect(ran).toEqual(["noop", "action"]);
  });

  it("sequences appear in list()", () => {
    const registry = new CommandRegistry();
    registry.register({ path: "a", description: "A", execute: () => ({ ok: true }) });
    registry.sequence("seq.test", [{ command: "a" }]);

    const all = registry.list();
    expect(all.find((c) => c.path === "seq.test")).toBeDefined();
  });
});
```

- [ ] **Step 2: Run tests to verify new ones fail**

Run: `cd hapax-logos && pnpm vitest run src/lib/__tests__/commandRegistry.test.ts`
Expected: Sequence tests FAIL — `registry.sequence` is not a function

- [ ] **Step 3: Implement sequence support**

Add to `CommandRegistry` class in `commandRegistry.ts`:

```typescript
// Add to the class:

interface SequenceStep {
  command: string;
  args?: Record<string, unknown>;
  settle?: number;
}

interface SequenceOptions {
  stopOnSuccess?: boolean;
}

// New method on CommandRegistry:
sequence(path: string, steps: SequenceStep[], options?: SequenceOptions): void {
  const description = `Sequence: ${steps.map((s) => s.command).join(" → ")}`;
  this.register({
    path,
    description,
    execute: async () => {
      let lastResult: CommandResult = { ok: false, error: "empty sequence" };
      for (const step of steps) {
        // Settle between steps to let React process state updates
        if (step.settle) {
          await new Promise((r) => setTimeout(r, step.settle));
        } else {
          await new Promise((r) => setTimeout(r, 0));
        }

        lastResult = await this.execute(step.command, step.args ?? {});

        if (options?.stopOnSuccess && lastResult.ok) {
          return lastResult;
        }
        if (!options?.stopOnSuccess && !lastResult.ok) {
          return lastResult;
        }
      }
      return lastResult;
    },
  });
}
```

Also add the types as exports at the top of the file:

```typescript
export interface SequenceStep {
  command: string;
  args?: Record<string, unknown>;
  settle?: number;
}

export interface SequenceOptions {
  stopOnSuccess?: boolean;
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd hapax-logos && pnpm vitest run src/lib/__tests__/commandRegistry.test.ts`
Expected: All 12 tests PASS

- [ ] **Step 5: Commit**

```bash
git add hapax-logos/src/lib/commandRegistry.ts hapax-logos/src/lib/__tests__/commandRegistry.test.ts
git commit -m "feat(logos): add sequence support to CommandRegistry"
```

---

## Task 3: Terrain domain commands

**Files:**
- Create: `hapax-logos/src/lib/commands/terrain.ts`
- Test: `hapax-logos/src/lib/commands/__tests__/terrain.test.ts`

- [ ] **Step 1: Write failing tests**

```typescript
// hapax-logos/src/lib/commands/__tests__/terrain.test.ts
import { describe, it, expect, vi } from "vitest";
import { CommandRegistry } from "../../commandRegistry";
import { registerTerrainCommands } from "../terrain";

function makeTerrainActions() {
  return {
    focusedRegion: null as string | null,
    regionDepths: {
      horizon: "surface" as string,
      field: "surface" as string,
      ground: "surface" as string,
      watershed: "surface" as string,
      bedrock: "surface" as string,
    },
    focusRegion: vi.fn((r: string | null) => {
      actions.focusedRegion = r;
    }),
    setRegionDepth: vi.fn((r: string, d: string) => {
      actions.regionDepths[r as keyof typeof actions.regionDepths] = d;
    }),
    cycleDepth: vi.fn(),
  };
  // Use a local ref so the mock can update state
  var actions: ReturnType<typeof makeTerrainActions>;
  // @ts-expect-error — hoisted var for closure
  actions = arguments.callee._lastActions;
}

// Simpler approach: use a state object
function createMockTerrain() {
  const state = {
    focusedRegion: null as string | null,
    regionDepths: {
      horizon: "surface",
      field: "surface",
      ground: "surface",
      watershed: "surface",
      bedrock: "surface",
    },
  };
  const actions = {
    focusRegion: vi.fn((r: string | null) => { state.focusedRegion = r; }),
    setRegionDepth: vi.fn((r: string, d: string) => {
      (state.regionDepths as Record<string, string>)[r] = d;
    }),
    cycleDepth: vi.fn(),
  };
  return { state, actions };
}

describe("Terrain domain commands", () => {
  it("terrain.focus sets region", async () => {
    const registry = new CommandRegistry();
    const { state, actions } = createMockTerrain();
    registerTerrainCommands(registry, () => state, actions);

    const result = await registry.execute("terrain.focus", { region: "ground" });
    expect(result.ok).toBe(true);
    expect(actions.focusRegion).toHaveBeenCalledWith("ground");
  });

  it("terrain.focus cycles depth when already focused", async () => {
    const registry = new CommandRegistry();
    const { state, actions } = createMockTerrain();
    state.focusedRegion = "ground";
    registerTerrainCommands(registry, () => state, actions);

    const result = await registry.execute("terrain.focus", { region: "ground" });
    expect(result.ok).toBe(true);
    expect(actions.cycleDepth).toHaveBeenCalledWith("ground");
  });

  it("terrain.focus rejects invalid region", async () => {
    const registry = new CommandRegistry();
    const { state, actions } = createMockTerrain();
    registerTerrainCommands(registry, () => state, actions);

    const result = await registry.execute("terrain.focus", { region: "invalid" });
    expect(result.ok).toBe(false);
    expect(result.error).toMatch(/invalid region/i);
  });

  it("terrain.depth.set sets specific depth", async () => {
    const registry = new CommandRegistry();
    const { state, actions } = createMockTerrain();
    registerTerrainCommands(registry, () => state, actions);

    const result = await registry.execute("terrain.depth.set", {
      region: "ground",
      depth: "core",
    });
    expect(result.ok).toBe(true);
    expect(actions.setRegionDepth).toHaveBeenCalledWith("ground", "core");
  });

  it("terrain.collapse resets all regions", async () => {
    const registry = new CommandRegistry();
    const { state, actions } = createMockTerrain();
    state.focusedRegion = "ground";
    registerTerrainCommands(registry, () => state, actions);

    const result = await registry.execute("terrain.collapse");
    expect(result.ok).toBe(true);
    expect(actions.focusRegion).toHaveBeenCalledWith(null);
    // Should reset all depths to surface
    expect(actions.setRegionDepth).toHaveBeenCalledTimes(5);
  });

  it("terrain queries return current state", () => {
    const registry = new CommandRegistry();
    const { state, actions } = createMockTerrain();
    state.focusedRegion = "field";
    registerTerrainCommands(registry, () => state, actions);

    expect(registry.query("terrain.focusedRegion")).toBe("field");
    expect(registry.query("terrain.depths")).toEqual(state.regionDepths);
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd hapax-logos && pnpm vitest run src/lib/commands/__tests__/terrain.test.ts`
Expected: FAIL — cannot find module `../terrain`

- [ ] **Step 3: Implement terrain domain**

```typescript
// hapax-logos/src/lib/commands/terrain.ts
import type { CommandRegistry } from "../commandRegistry";

const VALID_REGIONS = ["horizon", "field", "ground", "watershed", "bedrock"] as const;
const VALID_DEPTHS = ["surface", "stratum", "core"] as const;

type RegionName = (typeof VALID_REGIONS)[number];
type Depth = (typeof VALID_DEPTHS)[number];

export interface TerrainState {
  focusedRegion: string | null;
  regionDepths: Record<string, string>;
}

export interface TerrainActions {
  focusRegion: (region: string | null) => void;
  setRegionDepth: (region: string, depth: string) => void;
  cycleDepth: (region: string) => void;
}

function isValidRegion(r: unknown): r is RegionName {
  return typeof r === "string" && (VALID_REGIONS as readonly string[]).includes(r);
}

function isValidDepth(d: unknown): d is Depth {
  return typeof d === "string" && (VALID_DEPTHS as readonly string[]).includes(d);
}

export function registerTerrainCommands(
  registry: CommandRegistry,
  getState: () => TerrainState,
  actions: TerrainActions,
): void {
  registry.register({
    path: "terrain.focus",
    description: "Focus a region (cycles depth if already focused) or unfocus",
    args: {
      region: {
        type: "string",
        required: true,
        enum: [...VALID_REGIONS, "null"],
        description: "Region name or null to unfocus",
      },
    },
    execute: (args) => {
      const { region } = args;
      if (region === null || region === "null") {
        actions.focusRegion(null);
        return { ok: true, state: null };
      }
      if (!isValidRegion(region)) {
        return { ok: false, error: `Invalid region: ${String(region)}` };
      }
      const state = getState();
      if (state.focusedRegion === region) {
        actions.cycleDepth(region);
      } else {
        actions.focusRegion(region);
      }
      return { ok: true, state: region };
    },
  });

  registry.register({
    path: "terrain.depth.set",
    description: "Set specific depth for a region",
    args: {
      region: { type: "string", required: true, enum: [...VALID_REGIONS] },
      depth: { type: "string", required: true, enum: [...VALID_DEPTHS] },
    },
    execute: (args) => {
      if (!isValidRegion(args.region)) {
        return { ok: false, error: `Invalid region: ${String(args.region)}` };
      }
      if (!isValidDepth(args.depth)) {
        return { ok: false, error: `Invalid depth: ${String(args.depth)}` };
      }
      actions.setRegionDepth(args.region, args.depth);
      return { ok: true, state: args.depth };
    },
  });

  registry.register({
    path: "terrain.depth.cycle",
    description: "Cycle depth: surface → stratum → core",
    args: {
      region: { type: "string", required: true, enum: [...VALID_REGIONS] },
    },
    execute: (args) => {
      if (!isValidRegion(args.region)) {
        return { ok: false, error: `Invalid region: ${String(args.region)}` };
      }
      actions.cycleDepth(args.region);
      return { ok: true };
    },
  });

  registry.register({
    path: "terrain.collapse",
    description: "Reset all regions to surface and unfocus",
    execute: () => {
      actions.focusRegion(null);
      for (const region of VALID_REGIONS) {
        actions.setRegionDepth(region, "surface");
      }
      return { ok: true };
    },
  });

  // Queries
  registry.registerQuery("terrain.focusedRegion", () => getState().focusedRegion);
  registry.registerQuery("terrain.depths", () => getState().regionDepths);
  registry.registerQuery("terrain.coreMiddle", () => {
    const { regionDepths } = getState();
    const middle: RegionName[] = ["field", "ground", "watershed"];
    return middle.find((r) => regionDepths[r] === "core") ?? null;
  });
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd hapax-logos && pnpm vitest run src/lib/commands/__tests__/terrain.test.ts`
Expected: All 6 tests PASS

- [ ] **Step 5: Commit**

```bash
git add hapax-logos/src/lib/commands/terrain.ts hapax-logos/src/lib/commands/__tests__/terrain.test.ts
git commit -m "feat(logos): add terrain domain commands"
```

---

## Task 4: Studio, overlay, detection, nav, split, and data domain commands

**Files:**
- Create: `hapax-logos/src/lib/commands/studio.ts`
- Create: `hapax-logos/src/lib/commands/overlay.ts`
- Create: `hapax-logos/src/lib/commands/detection.ts`
- Create: `hapax-logos/src/lib/commands/nav.ts`
- Create: `hapax-logos/src/lib/commands/split.ts`
- Create: `hapax-logos/src/lib/commands/data.ts`
- Test: `hapax-logos/src/lib/commands/__tests__/domains.test.ts`

- [ ] **Step 1: Write failing tests for all remaining domains**

```typescript
// hapax-logos/src/lib/commands/__tests__/domains.test.ts
import { describe, it, expect, vi } from "vitest";
import { CommandRegistry } from "../../commandRegistry";
import { registerStudioCommands } from "../studio";
import { registerOverlayCommands } from "../overlay";
import { registerDetectionCommands } from "../detection";
import { registerNavCommands } from "../nav";
import { registerSplitCommands } from "../split";
import { registerDataCommands } from "../data";

describe("Studio domain", () => {
  function setup() {
    const registry = new CommandRegistry();
    const state = { smoothMode: false, activePreset: null as string | null, recording: false };
    const actions = {
      setSmoothMode: vi.fn((v: boolean) => { state.smoothMode = v; }),
      activatePreset: vi.fn((name: string) => { state.activePreset = name; }),
      cyclePreset: vi.fn(),
      toggleRecording: vi.fn(),
    };
    registerStudioCommands(registry, () => state, actions);
    return { registry, state, actions };
  }

  it("studio.smooth.enable enables smooth mode", async () => {
    const { registry, actions } = setup();
    const result = await registry.execute("studio.smooth.enable");
    expect(result.ok).toBe(true);
    expect(actions.setSmoothMode).toHaveBeenCalledWith(true);
  });

  it("studio.smooth.disable disables smooth mode", async () => {
    const { registry, actions } = setup();
    const result = await registry.execute("studio.smooth.disable");
    expect(result.ok).toBe(true);
    expect(actions.setSmoothMode).toHaveBeenCalledWith(false);
  });

  it("studio.smooth.toggle toggles", async () => {
    const { registry, state, actions } = setup();
    state.smoothMode = true;
    await registry.execute("studio.smooth.toggle");
    expect(actions.setSmoothMode).toHaveBeenCalledWith(false);
  });

  it("studio.preset.activate calls action with name", async () => {
    const { registry, actions } = setup();
    const result = await registry.execute("studio.preset.activate", { name: "ghost" });
    expect(result.ok).toBe(true);
    expect(actions.activatePreset).toHaveBeenCalledWith("ghost");
  });

  it("studio.preset.activate rejects missing name", async () => {
    const { registry } = setup();
    const result = await registry.execute("studio.preset.activate", {});
    expect(result.ok).toBe(false);
  });

  it("studio queries return state", () => {
    const { registry, state } = setup();
    state.smoothMode = true;
    state.activePreset = "neon";
    expect(registry.query("studio.smoothMode")).toBe(true);
    expect(registry.query("studio.activePreset")).toBe("neon");
  });
});

describe("Overlay domain", () => {
  function setup() {
    const registry = new CommandRegistry();
    const state = { activeOverlay: null as string | null };
    const actions = {
      setOverlay: vi.fn((v: string | null) => { state.activeOverlay = v; }),
    };
    registerOverlayCommands(registry, () => state, actions);
    return { registry, state, actions };
  }

  it("overlay.set sets overlay", async () => {
    const { registry, actions } = setup();
    await registry.execute("overlay.set", { name: "investigation" });
    expect(actions.setOverlay).toHaveBeenCalledWith("investigation");
  });

  it("overlay.clear clears overlay", async () => {
    const { registry, actions } = setup();
    await registry.execute("overlay.clear");
    expect(actions.setOverlay).toHaveBeenCalledWith(null);
  });

  it("overlay.toggle toggles on/off", async () => {
    const { registry, state, actions } = setup();
    await registry.execute("overlay.toggle", { name: "investigation" });
    expect(actions.setOverlay).toHaveBeenCalledWith("investigation");

    state.activeOverlay = "investigation";
    await registry.execute("overlay.toggle", { name: "investigation" });
    expect(actions.setOverlay).toHaveBeenLastCalledWith(null);
  });
});

describe("Detection domain", () => {
  function setup() {
    const registry = new CommandRegistry();
    const state = { tier: 1 as 1 | 2 | 3, visible: true };
    const actions = {
      setDetectionTier: vi.fn((t: number) => { state.tier = t as 1 | 2 | 3; }),
      setDetectionLayerVisible: vi.fn((v: boolean) => { state.visible = v; }),
    };
    registerDetectionCommands(registry, () => state, actions);
    return { registry, state, actions };
  }

  it("detection.tier.set sets tier", async () => {
    const { registry, actions } = setup();
    await registry.execute("detection.tier.set", { tier: 2 });
    expect(actions.setDetectionTier).toHaveBeenCalledWith(2);
  });

  it("detection.tier.cycle cycles 1→2→3→1", async () => {
    const { registry, state, actions } = setup();
    state.tier = 2;
    await registry.execute("detection.tier.cycle");
    expect(actions.setDetectionTier).toHaveBeenCalledWith(3);

    state.tier = 3;
    await registry.execute("detection.tier.cycle");
    expect(actions.setDetectionTier).toHaveBeenLastCalledWith(1);
  });

  it("detection.visibility.toggle toggles", async () => {
    const { registry, state, actions } = setup();
    await registry.execute("detection.visibility.toggle");
    expect(actions.setDetectionLayerVisible).toHaveBeenCalledWith(false);
  });
});

describe("Nav domain", () => {
  function setup() {
    const registry = new CommandRegistry();
    const state = { currentPath: "/" };
    const actions = {
      navigate: vi.fn((p: string) => { state.currentPath = p; }),
      toggleManual: vi.fn(),
      togglePalette: vi.fn(),
    };
    registerNavCommands(registry, () => state, actions);
    return { registry, state, actions };
  }

  it("nav.go navigates", async () => {
    const { registry, actions } = setup();
    await registry.execute("nav.go", { path: "/chat" });
    expect(actions.navigate).toHaveBeenCalledWith("/chat");
  });

  it("nav.manual.toggle calls toggle", async () => {
    const { registry, actions } = setup();
    await registry.execute("nav.manual.toggle");
    expect(actions.toggleManual).toHaveBeenCalled();
  });
});

describe("Split domain", () => {
  function setup() {
    const registry = new CommandRegistry();
    const state = {
      splitRegion: null as string | null,
      splitFullscreen: false,
      focusedRegion: "ground" as string | null,
    };
    const actions = {
      setSplitRegion: vi.fn((r: string | null) => { state.splitRegion = r; }),
      setSplitFullscreen: vi.fn((v: boolean) => { state.splitFullscreen = v; }),
    };
    registerSplitCommands(registry, () => state, actions);
    return { registry, state, actions };
  }

  it("split.open sets region", async () => {
    const { registry, actions } = setup();
    await registry.execute("split.open", { region: "ground" });
    expect(actions.setSplitRegion).toHaveBeenCalledWith("ground");
  });

  it("split.close clears region", async () => {
    const { registry, actions } = setup();
    await registry.execute("split.close");
    expect(actions.setSplitRegion).toHaveBeenCalledWith(null);
  });

  it("split.toggle uses focused region when no arg", async () => {
    const { registry, state, actions } = setup();
    state.focusedRegion = "field";
    await registry.execute("split.toggle");
    expect(actions.setSplitRegion).toHaveBeenCalledWith("field");
  });
});

describe("Data domain", () => {
  it("data.refresh calls invalidate", async () => {
    const registry = new CommandRegistry();
    const invalidate = vi.fn();
    registerDataCommands(registry, { invalidateQueries: invalidate });

    await registry.execute("data.refresh");
    expect(invalidate).toHaveBeenCalled();
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd hapax-logos && pnpm vitest run src/lib/commands/__tests__/domains.test.ts`
Expected: FAIL — modules not found

- [ ] **Step 3: Implement all six domain files**

`hapax-logos/src/lib/commands/studio.ts`:
```typescript
import type { CommandRegistry } from "../commandRegistry";

export interface StudioState {
  smoothMode: boolean;
  activePreset: string | null;
  recording: boolean;
}

export interface StudioActions {
  setSmoothMode: (on: boolean) => void;
  activatePreset: (name: string) => void;
  cyclePreset: (direction: "next" | "prev") => void;
  toggleRecording: () => void;
}

export function registerStudioCommands(
  registry: CommandRegistry,
  getState: () => StudioState,
  actions: StudioActions,
): void {
  registry.register({
    path: "studio.smooth.enable",
    description: "Enable smooth/HLS mode",
    execute: () => { actions.setSmoothMode(true); return { ok: true, state: true }; },
  });

  registry.register({
    path: "studio.smooth.disable",
    description: "Disable smooth/HLS mode",
    execute: () => { actions.setSmoothMode(false); return { ok: true, state: false }; },
  });

  registry.register({
    path: "studio.smooth.toggle",
    description: "Toggle smooth/HLS mode",
    execute: () => {
      const next = !getState().smoothMode;
      actions.setSmoothMode(next);
      return { ok: true, state: next };
    },
  });

  registry.register({
    path: "studio.preset.activate",
    description: "Activate a named preset",
    args: { name: { type: "string", required: true } },
    execute: (args) => {
      if (typeof args.name !== "string" || !args.name) {
        return { ok: false, error: "name is required" };
      }
      actions.activatePreset(args.name);
      return { ok: true, state: args.name };
    },
  });

  registry.register({
    path: "studio.preset.cycle",
    description: "Cycle to next/previous preset",
    args: { direction: { type: "string", required: true, enum: ["next", "prev"] } },
    execute: (args) => {
      const dir = args.direction as "next" | "prev";
      actions.cyclePreset(dir);
      return { ok: true };
    },
  });

  registry.register({
    path: "studio.recording.toggle",
    description: "Toggle recording (server-side)",
    execute: () => { actions.toggleRecording(); return { ok: true }; },
  });

  registry.registerQuery("studio.smoothMode", () => getState().smoothMode);
  registry.registerQuery("studio.activePreset", () => getState().activePreset);
  registry.registerQuery("studio.recording", () => getState().recording);
}
```

`hapax-logos/src/lib/commands/overlay.ts`:
```typescript
import type { CommandRegistry } from "../commandRegistry";

export interface OverlayState {
  activeOverlay: string | null;
}

export interface OverlayActions {
  setOverlay: (overlay: string | null) => void;
}

export function registerOverlayCommands(
  registry: CommandRegistry,
  getState: () => OverlayState,
  actions: OverlayActions,
): void {
  registry.register({
    path: "overlay.set",
    description: "Set active overlay",
    args: { name: { type: "string", required: true } },
    execute: (args) => {
      actions.setOverlay(args.name as string);
      return { ok: true, state: args.name };
    },
  });

  registry.register({
    path: "overlay.clear",
    description: "Clear active overlay",
    execute: () => { actions.setOverlay(null); return { ok: true, state: null }; },
  });

  registry.register({
    path: "overlay.toggle",
    description: "Toggle a specific overlay",
    args: { name: { type: "string", required: true } },
    execute: (args) => {
      const name = args.name as string;
      const current = getState().activeOverlay;
      const next = current === name ? null : name;
      actions.setOverlay(next);
      return { ok: true, state: next };
    },
  });

  registry.registerQuery("overlay.active", () => getState().activeOverlay);
}
```

`hapax-logos/src/lib/commands/detection.ts`:
```typescript
import type { CommandRegistry } from "../commandRegistry";

export interface DetectionState {
  tier: 1 | 2 | 3;
  visible: boolean;
}

export interface DetectionActions {
  setDetectionTier: (tier: number) => void;
  setDetectionLayerVisible: (visible: boolean) => void;
}

export function registerDetectionCommands(
  registry: CommandRegistry,
  getState: () => DetectionState,
  actions: DetectionActions,
): void {
  registry.register({
    path: "detection.tier.set",
    description: "Set detection tier",
    args: { tier: { type: "number", required: true, enum: ["1", "2", "3"] } },
    execute: (args) => {
      const tier = Number(args.tier);
      if (tier !== 1 && tier !== 2 && tier !== 3) {
        return { ok: false, error: `Invalid tier: ${args.tier}` };
      }
      actions.setDetectionTier(tier);
      return { ok: true, state: tier };
    },
  });

  registry.register({
    path: "detection.tier.cycle",
    description: "Cycle detection tier 1 → 2 → 3 → 1",
    execute: () => {
      const current = getState().tier;
      const next = (current % 3) + 1;
      actions.setDetectionTier(next);
      return { ok: true, state: next };
    },
  });

  registry.register({
    path: "detection.visibility.toggle",
    description: "Toggle detection layer visibility",
    execute: () => {
      const next = !getState().visible;
      actions.setDetectionLayerVisible(next);
      return { ok: true, state: next };
    },
  });

  registry.registerQuery("detection.tier", () => getState().tier);
  registry.registerQuery("detection.visible", () => getState().visible);
}
```

`hapax-logos/src/lib/commands/nav.ts`:
```typescript
import type { CommandRegistry } from "../commandRegistry";

export interface NavState {
  currentPath: string;
}

export interface NavActions {
  navigate: (path: string) => void;
  toggleManual: () => void;
  togglePalette: () => void;
}

export function registerNavCommands(
  registry: CommandRegistry,
  getState: () => NavState,
  actions: NavActions,
): void {
  registry.register({
    path: "nav.go",
    description: "Navigate to route",
    args: { path: { type: "string", required: true } },
    execute: (args) => {
      actions.navigate(args.path as string);
      return { ok: true, state: args.path };
    },
  });

  registry.register({
    path: "nav.manual.toggle",
    description: "Toggle operations manual",
    execute: () => { actions.toggleManual(); return { ok: true }; },
  });

  registry.register({
    path: "nav.palette.toggle",
    description: "Toggle command palette",
    execute: () => { actions.togglePalette(); return { ok: true }; },
  });

  registry.registerQuery("nav.currentPath", () => getState().currentPath);
}
```

`hapax-logos/src/lib/commands/split.ts`:
```typescript
import type { CommandRegistry } from "../commandRegistry";

const VALID_REGIONS = ["horizon", "field", "ground", "watershed", "bedrock"];

export interface SplitState {
  splitRegion: string | null;
  splitFullscreen: boolean;
  focusedRegion: string | null;
}

export interface SplitActions {
  setSplitRegion: (region: string | null) => void;
  setSplitFullscreen: (fs: boolean) => void;
}

export function registerSplitCommands(
  registry: CommandRegistry,
  getState: () => SplitState,
  actions: SplitActions,
): void {
  registry.register({
    path: "split.open",
    description: "Open split pane for region",
    args: { region: { type: "string", required: true, enum: VALID_REGIONS } },
    execute: (args) => {
      const region = args.region as string;
      if (!VALID_REGIONS.includes(region)) {
        return { ok: false, error: `Invalid region: ${region}` };
      }
      actions.setSplitRegion(region);
      return { ok: true, state: region };
    },
  });

  registry.register({
    path: "split.close",
    description: "Close split pane",
    execute: () => { actions.setSplitRegion(null); return { ok: true }; },
  });

  registry.register({
    path: "split.toggle",
    description: "Toggle split pane (uses focused region if no arg)",
    args: { region: { type: "string", required: false, enum: VALID_REGIONS } },
    execute: (args) => {
      const state = getState();
      if (state.splitRegion) {
        actions.setSplitRegion(null);
        return { ok: true, state: null };
      }
      const region = (args.region as string) || state.focusedRegion;
      if (!region) {
        return { ok: false, error: "No region specified and none focused" };
      }
      actions.setSplitRegion(region);
      return { ok: true, state: region };
    },
  });

  registry.register({
    path: "split.fullscreen.toggle",
    description: "Toggle split fullscreen",
    execute: () => {
      const next = !getState().splitFullscreen;
      actions.setSplitFullscreen(next);
      return { ok: true, state: next };
    },
  });

  registry.registerQuery("split.region", () => getState().splitRegion);
  registry.registerQuery("split.fullscreen", () => getState().splitFullscreen);
}
```

`hapax-logos/src/lib/commands/data.ts`:
```typescript
import type { CommandRegistry } from "../commandRegistry";

export interface DataActions {
  invalidateQueries: (key?: string) => void;
}

export function registerDataCommands(
  registry: CommandRegistry,
  actions: DataActions,
): void {
  registry.register({
    path: "data.refresh",
    description: "Invalidate all or specific queries",
    args: { key: { type: "string", required: false } },
    execute: (args) => {
      actions.invalidateQueries(args.key as string | undefined);
      return { ok: true };
    },
  });
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd hapax-logos && pnpm vitest run src/lib/commands/__tests__/domains.test.ts`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add hapax-logos/src/lib/commands/
git commit -m "feat(logos): add studio, overlay, detection, nav, split, data domain commands"
```

---

## Task 5: Built-in sequences

**Files:**
- Create: `hapax-logos/src/lib/commands/sequences.ts`
- Test: `hapax-logos/src/lib/commands/__tests__/sequences.test.ts`

- [ ] **Step 1: Write failing tests**

```typescript
// hapax-logos/src/lib/commands/__tests__/sequences.test.ts
import { describe, it, expect, vi } from "vitest";
import { CommandRegistry } from "../../commandRegistry";
import { registerTerrainCommands } from "../terrain";
import { registerStudioCommands } from "../studio";
import { registerOverlayCommands } from "../overlay";
import { registerSplitCommands } from "../split";
import { registerBuiltinSequences } from "../sequences";

function fullSetup() {
  const registry = new CommandRegistry();

  const terrainState = {
    focusedRegion: null as string | null,
    regionDepths: {
      horizon: "surface", field: "surface", ground: "surface",
      watershed: "surface", bedrock: "surface",
    },
  };
  const terrainActions = {
    focusRegion: vi.fn((r: string | null) => { terrainState.focusedRegion = r; }),
    setRegionDepth: vi.fn((r: string, d: string) => {
      (terrainState.regionDepths as Record<string, string>)[r] = d;
    }),
    cycleDepth: vi.fn(),
  };
  registerTerrainCommands(registry, () => terrainState, terrainActions);

  const studioState = { smoothMode: false, activePreset: null as string | null, recording: false };
  const studioActions = {
    setSmoothMode: vi.fn((v: boolean) => { studioState.smoothMode = v; }),
    activatePreset: vi.fn(),
    cyclePreset: vi.fn(),
    toggleRecording: vi.fn(),
  };
  registerStudioCommands(registry, () => studioState, studioActions);

  const overlayState = { activeOverlay: null as string | null };
  const overlayActions = { setOverlay: vi.fn((v: string | null) => { overlayState.activeOverlay = v; }) };
  registerOverlayCommands(registry, () => overlayState, overlayActions);

  const splitState = { splitRegion: null as string | null, splitFullscreen: false, focusedRegion: null as string | null };
  const splitActions = {
    setSplitRegion: vi.fn((r: string | null) => { splitState.splitRegion = r; }),
    setSplitFullscreen: vi.fn(),
  };
  registerSplitCommands(registry, () => splitState, splitActions);

  registerBuiltinSequences(registry);

  return {
    registry, terrainState, terrainActions, studioState, studioActions,
    overlayState, overlayActions, splitState, splitActions,
  };
}

describe("Built-in sequences", () => {
  it("studio.enter focuses ground, sets core, enables smooth", async () => {
    const { registry, terrainActions, studioActions } = fullSetup();
    const result = await registry.execute("studio.enter");
    expect(result.ok).toBe(true);
    expect(terrainActions.focusRegion).toHaveBeenCalledWith("ground");
    expect(terrainActions.setRegionDepth).toHaveBeenCalledWith("ground", "core");
    expect(studioActions.setSmoothMode).toHaveBeenCalledWith(true);
  });

  it("studio.exit disables smooth and collapses", async () => {
    const { registry, studioActions, terrainActions } = fullSetup();
    const result = await registry.execute("studio.exit");
    expect(result.ok).toBe(true);
    expect(studioActions.setSmoothMode).toHaveBeenCalledWith(false);
    expect(terrainActions.focusRegion).toHaveBeenCalledWith(null);
  });

  it("escape clears overlay first (stopOnSuccess)", async () => {
    const { registry, overlayState, overlayActions } = fullSetup();
    overlayState.activeOverlay = "investigation";
    const result = await registry.execute("escape");
    expect(result.ok).toBe(true);
    expect(overlayActions.setOverlay).toHaveBeenCalledWith(null);
  });

  it("escape sequence is listed", () => {
    const { registry } = fullSetup();
    const all = registry.list();
    expect(all.find((c) => c.path === "escape")).toBeDefined();
    expect(all.find((c) => c.path === "studio.enter")).toBeDefined();
    expect(all.find((c) => c.path === "studio.exit")).toBeDefined();
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd hapax-logos && pnpm vitest run src/lib/commands/__tests__/sequences.test.ts`
Expected: FAIL — module `../sequences` not found

- [ ] **Step 3: Implement built-in sequences**

```typescript
// hapax-logos/src/lib/commands/sequences.ts
import type { CommandRegistry } from "../commandRegistry";

export function registerBuiltinSequences(registry: CommandRegistry): void {
  registry.sequence("studio.enter", [
    { command: "terrain.focus", args: { region: "ground" } },
    { command: "terrain.depth.set", args: { region: "ground", depth: "core" } },
    { command: "studio.smooth.enable" },
  ]);

  registry.sequence("studio.exit", [
    { command: "studio.smooth.disable" },
    { command: "terrain.collapse" },
  ]);

  // Escape: hierarchical dismiss — first successful action stops the chain.
  // Each step returns ok:false if there's nothing to dismiss at that level.
  registry.sequence(
    "escape",
    [
      { command: "overlay.clear" },
      { command: "split.close" },
      { command: "terrain.collapse" },
    ],
    { stopOnSuccess: true },
  );
}
```

Note: The `overlay.clear` and `split.close` commands currently always return `ok: true` even when there's nothing to clear. For stopOnSuccess to work correctly, these commands need to return `ok: false` when they're no-ops. Update `overlay.ts` and `split.ts`:

In `overlay.ts`, change the `overlay.clear` execute to:
```typescript
execute: () => {
  const current = getState().activeOverlay;
  if (current === null) return { ok: false, error: "no overlay active" };
  actions.setOverlay(null);
  return { ok: true, state: null };
},
```

In `split.ts`, change the `split.close` execute to:
```typescript
execute: () => {
  const current = getState().splitRegion;
  if (current === null) return { ok: false, error: "no split open" };
  actions.setSplitRegion(null);
  return { ok: true };
},
```

In `terrain.ts`, change the `terrain.collapse` execute to:
```typescript
execute: () => {
  const state = getState();
  const isAlreadyCollapsed =
    state.focusedRegion === null &&
    Object.values(state.regionDepths).every((d) => d === "surface");
  if (isAlreadyCollapsed) return { ok: false, error: "already collapsed" };
  actions.focusRegion(null);
  for (const region of VALID_REGIONS) {
    actions.setRegionDepth(region, "surface");
  }
  return { ok: true };
},
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd hapax-logos && pnpm vitest run src/lib/commands/__tests__/sequences.test.ts`
Expected: All 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add hapax-logos/src/lib/commands/sequences.ts hapax-logos/src/lib/commands/__tests__/sequences.test.ts hapax-logos/src/lib/commands/overlay.ts hapax-logos/src/lib/commands/split.ts hapax-logos/src/lib/commands/terrain.ts
git commit -m "feat(logos): add built-in sequences (studio.enter, studio.exit, escape)"
```

---

## Task 6: Keyboard adapter

**Files:**
- Create: `hapax-logos/src/lib/keyboardAdapter.ts`
- Test: `hapax-logos/src/lib/__tests__/keyboardAdapter.test.ts`

- [ ] **Step 1: Write failing tests**

```typescript
// hapax-logos/src/lib/__tests__/keyboardAdapter.test.ts
import { describe, it, expect, vi, beforeEach } from "vitest";
import { evaluateKeyMap, type KeyBinding } from "../keyboardAdapter";
import { CommandRegistry } from "../commandRegistry";

const KEY_MAP: KeyBinding[] = [
  { key: "g", command: "terrain.focus", args: { region: "ground" } },
  { key: "r", command: "studio.recording.toggle", when: "terrain.focusedRegion=ground" },
  { key: "r", command: "data.refresh" },
  { key: "D", modifiers: { shift: true }, command: "detection.visibility.toggle" },
  { key: "Escape", command: "escape" },
];

describe("evaluateKeyMap", () => {
  it("matches simple key", () => {
    const registry = new CommandRegistry();
    const match = evaluateKeyMap(KEY_MAP, "g", {}, registry);
    expect(match).toEqual({ command: "terrain.focus", args: { region: "ground" } });
  });

  it("matches when clause", () => {
    const registry = new CommandRegistry();
    registry.registerQuery("terrain.focusedRegion", () => "ground");
    const match = evaluateKeyMap(KEY_MAP, "r", {}, registry);
    expect(match).toEqual({ command: "studio.recording.toggle", args: undefined });
  });

  it("falls through when clause to next binding", () => {
    const registry = new CommandRegistry();
    registry.registerQuery("terrain.focusedRegion", () => "horizon");
    const match = evaluateKeyMap(KEY_MAP, "r", {}, registry);
    expect(match).toEqual({ command: "data.refresh", args: undefined });
  });

  it("matches modifier keys", () => {
    const registry = new CommandRegistry();
    const match = evaluateKeyMap(KEY_MAP, "D", { shift: true }, registry);
    expect(match).toEqual({ command: "detection.visibility.toggle", args: undefined });
  });

  it("does not match when modifier mismatch", () => {
    const registry = new CommandRegistry();
    const match = evaluateKeyMap(KEY_MAP, "D", {}, registry);
    expect(match).toBeNull();
  });

  it("returns null for unmapped key", () => {
    const registry = new CommandRegistry();
    const match = evaluateKeyMap(KEY_MAP, "z", {}, registry);
    expect(match).toBeNull();
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd hapax-logos && pnpm vitest run src/lib/__tests__/keyboardAdapter.test.ts`
Expected: FAIL — module not found

- [ ] **Step 3: Implement keyboard adapter**

```typescript
// hapax-logos/src/lib/keyboardAdapter.ts
import type { CommandRegistry } from "./commandRegistry";

export interface KeyBinding {
  key: string;
  modifiers?: { ctrl?: boolean; shift?: boolean; alt?: boolean; meta?: boolean };
  command: string;
  args?: Record<string, unknown>;
  when?: string; // "query.path=value" or "query.path" (truthy check)
}

interface ModifierState {
  ctrl?: boolean;
  shift?: boolean;
  alt?: boolean;
  meta?: boolean;
}

function modifiersMatch(
  required: KeyBinding["modifiers"],
  actual: ModifierState,
): boolean {
  if (!required) {
    // No modifiers required — reject if any are pressed (except for special keys)
    return !actual.ctrl && !actual.shift && !actual.alt && !actual.meta;
  }
  return (
    !!required.ctrl === !!actual.ctrl &&
    !!required.shift === !!actual.shift &&
    !!required.alt === !!actual.alt &&
    !!required.meta === !!actual.meta
  );
}

function evaluateWhen(when: string, registry: CommandRegistry): boolean {
  const eqIdx = when.indexOf("=");
  if (eqIdx === -1) {
    // Truthy check
    return !!registry.query(when);
  }
  const path = when.slice(0, eqIdx);
  const expected = when.slice(eqIdx + 1);
  const actual = registry.query(path);
  return String(actual) === expected;
}

export function evaluateKeyMap(
  keyMap: KeyBinding[],
  key: string,
  modifiers: ModifierState,
  registry: CommandRegistry,
): { command: string; args?: Record<string, unknown> } | null {
  for (const binding of keyMap) {
    if (binding.key !== key) continue;
    if (!modifiersMatch(binding.modifiers, modifiers)) continue;
    if (binding.when && !evaluateWhen(binding.when, registry)) continue;
    return { command: binding.command, args: binding.args };
  }
  return null;
}

export const LOGOS_KEY_MAP: KeyBinding[] = [
  // Region focus
  { key: "h", command: "terrain.focus", args: { region: "horizon" } },
  { key: "f", command: "terrain.focus", args: { region: "field" } },
  { key: "g", command: "terrain.focus", args: { region: "ground" } },
  { key: "w", command: "terrain.focus", args: { region: "watershed" } },
  { key: "b", command: "terrain.focus", args: { region: "bedrock" } },
  // Overlays
  { key: "/", command: "overlay.toggle", args: { name: "investigation" } },
  { key: "Escape", command: "escape" },
  // Split
  { key: "s", command: "split.toggle" },
  // Detection
  { key: "d", command: "detection.tier.cycle" },
  { key: "D", modifiers: { shift: true }, command: "detection.visibility.toggle" },
  // Studio (ground-gated)
  { key: "e", command: "studio.smooth.toggle", when: "terrain.focusedRegion=ground" },
  { key: "r", command: "studio.recording.toggle", when: "terrain.focusedRegion=ground" },
  { key: "[", command: "studio.preset.cycle", args: { direction: "prev" }, when: "terrain.focusedRegion=ground" },
  { key: "]", command: "studio.preset.cycle", args: { direction: "next" }, when: "terrain.focusedRegion=ground" },
  // Navigation
  { key: "?", command: "nav.manual.toggle" },
  { key: "c", command: "nav.go", args: { path: "/chat" } },
  { key: "i", command: "nav.go", args: { path: "/insight" } },
  // Data (r falls through from studio.recording when not ground-focused)
  { key: "r", command: "data.refresh" },
];
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd hapax-logos && pnpm vitest run src/lib/__tests__/keyboardAdapter.test.ts`
Expected: All 6 tests PASS

- [ ] **Step 5: Commit**

```bash
git add hapax-logos/src/lib/keyboardAdapter.ts hapax-logos/src/lib/__tests__/keyboardAdapter.test.ts
git commit -m "feat(logos): add keyboard adapter with when-clause evaluation"
```

---

## Task 7: React context provider and window.__logos binding

**Files:**
- Create: `hapax-logos/src/contexts/CommandRegistryContext.tsx`

- [ ] **Step 1: Implement the context provider**

This file wires the pure CommandRegistry to React contexts. It reads state from existing providers and registers domain commands.

```typescript
// hapax-logos/src/contexts/CommandRegistryContext.tsx
import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useRef,
  type ReactNode,
} from "react";
import { useNavigate } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { CommandRegistry } from "../lib/commandRegistry";
import { evaluateKeyMap, LOGOS_KEY_MAP } from "../lib/keyboardAdapter";
import { registerTerrainCommands } from "../lib/commands/terrain";
import { registerStudioCommands } from "../lib/commands/studio";
import { registerOverlayCommands } from "../lib/commands/overlay";
import { registerDetectionCommands } from "../lib/commands/detection";
import { registerNavCommands } from "../lib/commands/nav";
import { registerSplitCommands } from "../lib/commands/split";
import { registerDataCommands } from "../lib/commands/data";
import { registerBuiltinSequences } from "../lib/commands/sequences";
import {
  useTerrainDisplay,
  useTerrainActions,
} from "./TerrainContext";

const CommandRegistryCtx = createContext<CommandRegistry | null>(null);

export function useCommandRegistry(): CommandRegistry {
  const ctx = useContext(CommandRegistryCtx);
  if (!ctx) throw new Error("useCommandRegistry must be inside CommandRegistryProvider");
  return ctx;
}

interface Props {
  children: ReactNode;
  onManualToggle: () => void;
  onPaletteToggle: () => void;
  /** Optional — pass GroundStudio + Detection state/actions when available (inside their providers). */
  studioState?: {
    smoothMode: boolean;
    activePreset: string | null;
    recording: boolean;
  };
  studioActions?: {
    setSmoothMode: (on: boolean) => void;
    activatePreset: (name: string) => void;
    cyclePreset: (direction: "next" | "prev") => void;
    toggleRecording: () => void;
  };
  detectionState?: {
    tier: 1 | 2 | 3;
    visible: boolean;
  };
  detectionActions?: {
    setDetectionTier: (tier: number) => void;
    setDetectionLayerVisible: (visible: boolean) => void;
  };
}

export function CommandRegistryProvider({
  children,
  onManualToggle,
  onPaletteToggle,
  studioState,
  studioActions,
  detectionState,
  detectionActions,
}: Props) {
  const registry = useMemo(() => new CommandRegistry(), []);
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const terrainDisplay = useTerrainDisplay();
  const terrainActionsHook = useTerrainActions();

  // Use refs for values that change frequently so registration stays stable
  const terrainRef = useRef(terrainDisplay);
  terrainRef.current = terrainDisplay;

  const studioStateRef = useRef(studioState);
  studioStateRef.current = studioState;

  const detectionStateRef = useRef(detectionState);
  detectionStateRef.current = detectionState;

  // Register domains once
  useEffect(() => {
    registerTerrainCommands(
      registry,
      () => ({
        focusedRegion: terrainRef.current.focusedRegion,
        regionDepths: terrainRef.current.regionDepths as Record<string, string>,
      }),
      {
        focusRegion: terrainActionsHook.focusRegion,
        setRegionDepth: terrainActionsHook.setRegionDepth,
        cycleDepth: terrainActionsHook.cycleDepth,
      },
    );

    registerOverlayCommands(
      registry,
      () => ({ activeOverlay: terrainRef.current.activeOverlay }),
      { setOverlay: terrainActionsHook.setOverlay },
    );

    registerSplitCommands(
      registry,
      () => ({
        splitRegion: terrainRef.current.splitRegion,
        splitFullscreen: terrainRef.current.splitFullscreen,
        focusedRegion: terrainRef.current.focusedRegion,
      }),
      {
        setSplitRegion: terrainActionsHook.setSplitRegion,
        setSplitFullscreen: terrainActionsHook.setSplitFullscreen,
      },
    );

    registerNavCommands(
      registry,
      () => ({ currentPath: window.location.pathname }),
      { navigate, toggleManual: onManualToggle, togglePalette: onPaletteToggle },
    );

    registerDataCommands(registry, {
      invalidateQueries: (key?: string) => {
        if (key) {
          queryClient.invalidateQueries({ queryKey: [key] });
        } else {
          queryClient.invalidateQueries();
        }
      },
    });

    registerBuiltinSequences(registry);

    // Expose on window
    (window as unknown as Record<string, unknown>).__logos = {
      execute: registry.execute.bind(registry),
      query: registry.query.bind(registry),
      list: registry.list.bind(registry),
      subscribe: registry.subscribe.bind(registry),
      getState: registry.getState.bind(registry),
      get debug() { return registry.debug; },
      set debug(v: boolean) { registry.debug = v; },
    };

    return () => {
      delete (window as unknown as Record<string, unknown>).__logos;
    };
  }, [registry, navigate, queryClient, terrainActionsHook, onManualToggle, onPaletteToggle]);

  // Register studio/detection domains when their providers are available
  useEffect(() => {
    if (!studioState || !studioActions) return;
    registerStudioCommands(
      registry,
      () => studioStateRef.current!,
      studioActions,
    );
    return () => {
      registry.unregister("studio.smooth.enable");
      registry.unregister("studio.smooth.disable");
      registry.unregister("studio.smooth.toggle");
      registry.unregister("studio.preset.activate");
      registry.unregister("studio.preset.cycle");
      registry.unregister("studio.recording.toggle");
      registry.unregisterQuery("studio.smoothMode");
      registry.unregisterQuery("studio.activePreset");
      registry.unregisterQuery("studio.recording");
    };
  }, [registry, studioState, studioActions]);

  useEffect(() => {
    if (!detectionState || !detectionActions) return;
    registerDetectionCommands(
      registry,
      () => detectionStateRef.current!,
      detectionActions,
    );
    return () => {
      registry.unregister("detection.tier.set");
      registry.unregister("detection.tier.cycle");
      registry.unregister("detection.visibility.toggle");
      registry.unregisterQuery("detection.tier");
      registry.unregisterQuery("detection.visible");
    };
  }, [registry, detectionState, detectionActions]);

  // Global keyboard handler
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      const target = e.target as HTMLElement;
      if (
        target.tagName === "INPUT" ||
        target.tagName === "TEXTAREA" ||
        target.isContentEditable
      ) {
        // Allow Ctrl+P for palette and Escape even in inputs
        if (
          !((e.ctrlKey || e.metaKey) && e.key === "p") &&
          e.key !== "Escape"
        ) {
          return;
        }
      }

      // Ctrl+P — palette toggle (handled separately from key map)
      if ((e.ctrlKey || e.metaKey) && e.key === "p") {
        e.preventDefault();
        onPaletteToggle();
        return;
      }

      const match = evaluateKeyMap(
        LOGOS_KEY_MAP,
        e.key,
        { ctrl: e.ctrlKey, shift: e.shiftKey, alt: e.altKey, meta: e.metaKey },
        registry,
      );

      if (match) {
        e.preventDefault();
        registry.execute(match.command, match.args ?? {}, "keyboard");
      }
    }

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [registry, onPaletteToggle]);

  return (
    <CommandRegistryCtx.Provider value={registry}>
      {children}
    </CommandRegistryCtx.Provider>
  );
}
```

- [ ] **Step 2: Verify the file has no TypeScript errors**

Run: `cd hapax-logos && pnpm exec tsc --noEmit --strict src/contexts/CommandRegistryContext.tsx 2>&1 | head -20`
(May show errors about missing react-router types etc. in isolation — that's OK. Full typecheck in task 9.)

- [ ] **Step 3: Commit**

```bash
git add hapax-logos/src/contexts/CommandRegistryContext.tsx
git commit -m "feat(logos): add CommandRegistryProvider with window.__logos binding"
```

---

## Task 8: CommandFeedback toast component

**Files:**
- Create: `hapax-logos/src/components/terrain/CommandFeedback.tsx`

- [ ] **Step 1: Implement command feedback**

```typescript
// hapax-logos/src/components/terrain/CommandFeedback.tsx
import { useEffect, useState } from "react";
import { useCommandRegistry } from "../../contexts/CommandRegistryContext";

interface Toast {
  id: number;
  message: string;
  timestamp: number;
}

let nextId = 0;

export function CommandFeedback() {
  const registry = useCommandRegistry();
  const [toasts, setToasts] = useState<Toast[]>([]);

  useEffect(() => {
    return registry.subscribe(/./, (event) => {
      if (event.result.ok) return; // Only show failures
      if (event.source === "keyboard") {
        // Silently swallow keyboard misses — the user doesn't need a toast
        // for pressing a key that doesn't apply in the current context
        return;
      }
      const id = nextId++;
      setToasts((prev) => [...prev, { id, message: `${event.path}: ${event.result.error}`, timestamp: Date.now() }]);
      // Auto-dismiss after 3s
      setTimeout(() => {
        setToasts((prev) => prev.filter((t) => t.id !== id));
      }, 3000);
    });
  }, [registry]);

  if (toasts.length === 0) return null;

  return (
    <div
      className="fixed bottom-4 right-4 flex flex-col gap-2"
      style={{ zIndex: 100, pointerEvents: "none" }}
    >
      {toasts.map((toast) => (
        <div
          key={toast.id}
          className="rounded border border-red-800/50 bg-zinc-900/90 px-3 py-2 text-xs text-red-400 backdrop-blur-sm"
          style={{
            fontFamily: "'JetBrains Mono', monospace",
            maxWidth: 400,
            pointerEvents: "auto",
          }}
        >
          {toast.message}
        </div>
      ))}
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add hapax-logos/src/components/terrain/CommandFeedback.tsx
git commit -m "feat(logos): add CommandFeedback toast component"
```

---

## Task 9: Wire provider into app and remove old keyboard handlers

**Files:**
- Modify: `hapax-logos/src/pages/TerrainPage.tsx`
- Modify: `hapax-logos/src/components/terrain/TerrainLayout.tsx`
- Modify: `hapax-logos/src/pages/HapaxPage.tsx`
- Delete: `hapax-logos/src/hooks/useKeyboardShortcuts.ts`
- Delete: `hapax-logos/src/hooks/useStudioShortcuts.ts`

This is the integration task — it touches multiple files. Read each file before editing. The changes are:

- [ ] **Step 1: Modify TerrainPage.tsx — add CommandRegistryProvider, remove TerrainChrome keyboard handler**

Read `TerrainPage.tsx`. Then:

1. Add state for `manualOpen` and `paletteOpen` at the `TerrainPage` level (lift from `TerrainChrome`).
2. Wrap the tree with `CommandRegistryProvider` inside `TerrainProvider` (it needs terrain context).
3. Remove the `useEffect` keyboard handler from `TerrainChrome` (lines ~53–72).
4. Pass `onManualToggle` and `onPaletteToggle` to `CommandRegistryProvider`.

The new `TerrainPage` should look like:

```typescript
export function TerrainPage() {
  const [manualOpen, setManualOpen] = useState(false);
  const [paletteOpen, setPaletteOpen] = useState(false);

  return (
    <ToastProvider>
      <AgentRunProvider>
        <TerrainProvider>
          <CommandRegistryProvider
            onManualToggle={() => setManualOpen((p) => !p)}
            onPaletteToggle={() => setPaletteOpen((p) => !p)}
          >
            <ErrorBoundary>
              <TerrainParamSync />
              <TerrainLayout />
              <CommandPalette
                open={paletteOpen}
                onClose={() => setPaletteOpen(false)}
                onManualToggle={() => setManualOpen((p) => !p)}
              />
              <ManualDrawer open={manualOpen} onClose={() => setManualOpen(false)} />
              <HapaxModal ... />
              <HealthToastWatcher />
              <DemoGate />
            </ErrorBoundary>
          </CommandRegistryProvider>
        </TerrainProvider>
      </AgentRunProvider>
    </ToastProvider>
  );
}
```

Remove the `TerrainChrome` component entirely — its UI elements move into the `TerrainPage` render directly, its keyboard handler is replaced by `CommandRegistryProvider`.

- [ ] **Step 2: Modify TerrainLayout.tsx — remove all keyboard handlers, wire studio/detection to registry**

Read `TerrainLayout.tsx`. Then:

1. Delete `DetectionKeyboardHandler` component (lines ~119–144).
2. Delete `StudioKeyboardHandler` component (lines ~171–218).
3. Delete `handleKey` useCallback and its `useEffect` (lines ~265–331).
4. Delete `KeyboardHintBar` component (lines ~60–117) — it will be rebuilt to read from the registry in a future task.
5. Add `CommandFeedback` component to the render tree.
6. Add a new component `CommandRegistryBridge` inside the `GroundStudioProvider`/`ClassificationOverlayProvider` tree that passes studio and detection state/actions up to the registry. This is needed because these providers are inside `TerrainLayout`, not at the `TerrainPage` level.

The bridge pattern:
```typescript
function CommandRegistryBridge() {
  const registry = useCommandRegistry();
  const { smoothMode, setSmoothMode } = useGroundStudio();
  const { detectionTier, setDetectionTier, detectionLayerVisible, setDetectionLayerVisible } = useDetections();
  const recordingToggle = useRecordingToggle();
  const { regionDepths, setRegionDepth } = useTerrain();

  useEffect(() => {
    registerStudioCommands(
      registry,
      () => ({
        smoothMode,
        activePreset: null, // TODO: wire from preset query when available
        recording: false,
      }),
      {
        setSmoothMode: (on: boolean) => {
          setSmoothMode(on);
          if (on && regionDepths.ground !== "core") {
            setRegionDepth("ground", "core");
          }
        },
        activatePreset: (name: string) => {
          fetch(`/api/studio/presets/${name}/activate`, { method: "POST" }).catch(() => {});
        },
        cyclePreset: (direction: "next" | "prev") => {
          fetch(`/api/studio/presets/cycle?direction=${direction}`, { method: "POST" }).catch(() => {});
        },
        toggleRecording: () => { recordingToggle.mutate(true); },
      },
    );

    registerDetectionCommands(
      registry,
      () => ({ tier: detectionTier as 1 | 2 | 3, visible: detectionLayerVisible }),
      { setDetectionTier, setDetectionLayerVisible },
    );

    return () => {
      // Cleanup on unmount
      for (const p of ["studio.smooth.enable", "studio.smooth.disable", "studio.smooth.toggle",
        "studio.preset.activate", "studio.preset.cycle", "studio.recording.toggle"]) {
        registry.unregister(p);
      }
      for (const p of ["studio.smoothMode", "studio.activePreset", "studio.recording"]) {
        registry.unregisterQuery(p);
      }
      for (const p of ["detection.tier.set", "detection.tier.cycle", "detection.visibility.toggle"]) {
        registry.unregister(p);
      }
      for (const p of ["detection.tier", "detection.visible"]) {
        registry.unregisterQuery(p);
      }
    };
  }, [registry, smoothMode, setSmoothMode, detectionTier, setDetectionTier,
      detectionLayerVisible, setDetectionLayerVisible, recordingToggle,
      regionDepths, setRegionDepth]);

  return null;
}
```

Then simplify the `CommandRegistryProvider` in task 7 — remove the optional studio/detection props since the bridge handles it. The provider only needs terrain, nav, overlay, split, data, and sequences.

- [ ] **Step 3: Remove HapaxPage keyboard handler**

Read `HapaxPage.tsx`. Delete lines ~234–247 (the `handleKey` callback and its `useEffect`). HapaxPage is a separate route — its keys (c, v, s, f) are specific to the ambient display. For now, leave them removed. They can be re-registered as a `hapax` domain later if needed — the ambient page is not the automation priority.

- [ ] **Step 4: Delete old keyboard hook files**

```bash
rm hapax-logos/src/hooks/useKeyboardShortcuts.ts
rm hapax-logos/src/hooks/useStudioShortcuts.ts
```

Verify no imports reference them:
```bash
cd hapax-logos && grep -r "useKeyboardShortcuts\|useStudioShortcuts" src/ --include="*.ts" --include="*.tsx"
```

Remove any remaining imports found.

- [ ] **Step 5: Run full typecheck and lint**

```bash
cd hapax-logos && pnpm exec tsc --noEmit && pnpm lint
```

Fix any type errors or lint issues.

- [ ] **Step 6: Run all tests**

```bash
cd hapax-logos && pnpm vitest run
```

All tests should pass.

- [ ] **Step 7: Commit**

```bash
git add -A hapax-logos/src/
git commit -m "feat(logos): wire CommandRegistry into app, remove old keyboard handlers"
```

---

## Task 10: Update CommandPalette to read from registry

**Files:**
- Modify: `hapax-logos/src/components/shared/CommandPalette.tsx`

- [ ] **Step 1: Read current CommandPalette.tsx and modify**

Replace the hardcoded `staticCommands` array with `registry.list()`. The palette already has the right UI — it just needs a different data source.

```typescript
// Key changes to CommandPalette.tsx:
import { useCommandRegistry } from "../../contexts/CommandRegistryContext";

export function CommandPalette({ open, onClose }: { open: boolean; onClose: () => void }) {
  const registry = useCommandRegistry();
  const { data: agents } = useAgents();
  const navigate = useNavigate();
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  const registryCommands = useMemo(() => {
    return registry.list().map((cmd) => ({
      id: cmd.path,
      label: cmd.description,
      shortcut: undefined as string | undefined, // Could derive from LOGOS_KEY_MAP
      action: () => {
        registry.execute(cmd.path, {}, "palette");
        onClose();
      },
    }));
  }, [registry, onClose]);

  const agentCommands = (agents ?? []).map((a) => ({
    id: `agent-${a.name}`,
    label: `Run ${a.name}`,
    action: () => { navigate("/"); onClose(); },
  }));

  const commands = [...registryCommands, ...agentCommands];
  // ... rest unchanged
}
```

Remove the `useTerrain`, `useQueryClient` imports since those are no longer needed directly — the registry handles them.

- [ ] **Step 2: Run typecheck and lint**

```bash
cd hapax-logos && pnpm exec tsc --noEmit && pnpm lint
```

- [ ] **Step 3: Commit**

```bash
git add hapax-logos/src/components/shared/CommandPalette.tsx
git commit -m "feat(logos): CommandPalette reads from command registry"
```

---

## Task 11: WebSocket relay (backend)

**Files:**
- Create: `logos/api/routes/commands.py`
- Modify: `logos/api/app.py`
- Test: `tests/logos/api/test_commands_ws.py`

- [ ] **Step 1: Write failing test**

```python
# tests/logos/api/test_commands_ws.py
"""WebSocket command relay tests."""
from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from logos.api.app import app


@pytest.fixture
def client():
    return TestClient(app)


def test_execute_without_frontend_returns_error(client: TestClient):
    """External client sends execute, but no frontend is connected."""
    with client.websocket_connect("/ws/commands") as ws:
        ws.send_json({"type": "execute", "id": "1", "path": "terrain.focus", "args": {"region": "ground"}})
        resp = ws.receive_json()
        assert resp["type"] == "result"
        assert resp["id"] == "1"
        assert resp["data"]["ok"] is False
        assert "frontend not connected" in resp["data"]["error"]


def test_frontend_registration(client: TestClient):
    """Frontend connects with role=frontend, external client can then send commands."""
    # This test verifies the relay protocol — frontend echoes back results
    with client.websocket_connect("/ws/commands?role=frontend") as frontend:
        with client.websocket_connect("/ws/commands") as ext:
            # External client sends command
            ext.send_json({"type": "execute", "id": "42", "path": "terrain.focus", "args": {"region": "ground"}})

            # Frontend receives the forwarded command
            msg = frontend.receive_json()
            assert msg["type"] == "execute"
            assert msg["id"] == "42"
            assert msg["path"] == "terrain.focus"

            # Frontend sends result back
            frontend.send_json({"type": "result", "id": "42", "data": {"ok": True, "state": "ground"}})

            # External client receives the result
            resp = ext.receive_json()
            assert resp["type"] == "result"
            assert resp["id"] == "42"
            assert resp["data"]["ok"] is True


def test_query_forwarded(client: TestClient):
    """Query messages are forwarded to frontend and results returned."""
    with client.websocket_connect("/ws/commands?role=frontend") as frontend:
        with client.websocket_connect("/ws/commands") as ext:
            ext.send_json({"type": "query", "id": "q1", "path": "terrain.focusedRegion"})

            msg = frontend.receive_json()
            assert msg["type"] == "query"

            frontend.send_json({"type": "result", "id": "q1", "data": {"ok": True, "state": "ground"}})

            resp = ext.receive_json()
            assert resp["id"] == "q1"


def test_list_forwarded(client: TestClient):
    """List messages are forwarded to frontend."""
    with client.websocket_connect("/ws/commands?role=frontend") as frontend:
        with client.websocket_connect("/ws/commands") as ext:
            ext.send_json({"type": "list", "id": "l1", "domain": "terrain"})

            msg = frontend.receive_json()
            assert msg["type"] == "list"
            assert msg["domain"] == "terrain"

            frontend.send_json({"type": "result", "id": "l1", "data": {"ok": True, "state": []}})

            resp = ext.receive_json()
            assert resp["id"] == "l1"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/hapax/projects/hapax-council && uv run pytest tests/logos/api/test_commands_ws.py -v`
Expected: FAIL — route not found

- [ ] **Step 3: Implement the WebSocket relay**

```python
# logos/api/routes/commands.py
"""WebSocket relay for Logos command registry.

The frontend connects with ?role=frontend. External clients connect without that param.
All command messages from external clients are forwarded to the frontend connection.
Results from the frontend are routed back to the originating client by message id.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query

_log = logging.getLogger(__name__)

router = APIRouter()

# Single frontend connection (the browser tab running Logos)
_frontend_ws: WebSocket | None = None
_frontend_lock = asyncio.Lock()

# External clients waiting for responses, keyed by message id
_pending: dict[str, WebSocket] = {}

# External clients with active subscriptions
_subscribers: dict[str, tuple[WebSocket, str]] = {}  # sub_id -> (ws, pattern)


@router.websocket("/ws/commands")
async def command_relay(
    websocket: WebSocket,
    role: str = Query(default=""),
) -> None:
    await websocket.accept()
    global _frontend_ws

    if role == "frontend":
        async with _frontend_lock:
            _frontend_ws = websocket
        _log.info("Frontend connected to command relay")
        try:
            await _handle_frontend(websocket)
        except WebSocketDisconnect:
            _log.info("Frontend disconnected from command relay")
        finally:
            async with _frontend_lock:
                if _frontend_ws is websocket:
                    _frontend_ws = None
    else:
        _log.info("External client connected to command relay")
        try:
            await _handle_external(websocket)
        except WebSocketDisconnect:
            _log.debug("External client disconnected")
        finally:
            # Clean up any pending requests from this client
            to_remove = [k for k, v in _pending.items() if v is websocket]
            for k in to_remove:
                del _pending[k]
            to_remove = [k for k, (ws, _) in _subscribers.items() if ws is websocket]
            for k in to_remove:
                del _subscribers[k]


async def _handle_frontend(ws: WebSocket) -> None:
    """Frontend sends results and events back."""
    while True:
        data: dict[str, Any] = await ws.receive_json()
        msg_type = data.get("type")

        if msg_type == "result":
            msg_id = data.get("id")
            if msg_id and msg_id in _pending:
                client = _pending.pop(msg_id)
                try:
                    await client.send_json(data)
                except Exception:
                    pass  # Client may have disconnected

        elif msg_type == "event":
            # Forward events to matching subscribers
            path = data.get("path", "")
            for sub_id, (client, pattern) in list(_subscribers.items()):
                if _pattern_matches(pattern, path):
                    try:
                        await client.send_json({**data, "subscription": sub_id})
                    except Exception:
                        del _subscribers[sub_id]


async def _handle_external(ws: WebSocket) -> None:
    """External client sends commands, queries, list, subscribe requests."""
    while True:
        data: dict[str, Any] = await ws.receive_json()
        msg_type = data.get("type")
        msg_id = data.get("id")

        if msg_type == "subscribe":
            if msg_id:
                pattern = data.get("pattern", ".*")
                _subscribers[msg_id] = (ws, pattern)
                await ws.send_json({"type": "result", "id": msg_id, "data": {"ok": True}})
            continue

        if msg_type == "unsubscribe":
            if msg_id and msg_id in _subscribers:
                del _subscribers[msg_id]
            continue

        # For execute, query, list — forward to frontend
        if _frontend_ws is None:
            if msg_id:
                await ws.send_json({
                    "type": "result",
                    "id": msg_id,
                    "data": {"ok": False, "error": "frontend not connected"},
                })
            continue

        # Register pending and forward
        if msg_id:
            _pending[msg_id] = ws
        try:
            await _frontend_ws.send_json(data)
        except Exception:
            if msg_id:
                _pending.pop(msg_id, None)
                await ws.send_json({
                    "type": "result",
                    "id": msg_id,
                    "data": {"ok": False, "error": "frontend connection lost"},
                })


def _pattern_matches(pattern: str, path: str) -> bool:
    """Simple glob-style matching: studio.* matches studio.anything."""
    import re

    regex = pattern.replace(".", r"\.").replace("*", ".*")
    return bool(re.match(f"^{regex}$", path))
```

- [ ] **Step 4: Register the router in app.py**

Add to `logos/api/app.py`:
```python
from logos.api.routes.commands import router as commands_router
app.include_router(commands_router)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd /home/hapax/projects/hapax-council && uv run pytest tests/logos/api/test_commands_ws.py -v`
Expected: All 4 tests PASS

- [ ] **Step 6: Commit**

```bash
git add logos/api/routes/commands.py logos/api/app.py tests/logos/api/test_commands_ws.py
git commit -m "feat(logos-api): add WebSocket command relay endpoint"
```

---

## Task 12: Frontend WebSocket relay client

**Files:**
- Create: `hapax-logos/src/lib/commandRelay.ts`

- [ ] **Step 1: Implement the relay client**

```typescript
// hapax-logos/src/lib/commandRelay.ts
import type { CommandRegistry } from "./commandRegistry";

/**
 * Connects the frontend to the Logos API WebSocket relay.
 * Receives commands from external clients (MCP, voice) and
 * executes them via the local registry.
 */
export function connectCommandRelay(
  registry: CommandRegistry,
  url = `ws://${window.location.hostname}:8051/ws/commands?role=frontend`,
): () => void {
  let ws: WebSocket | null = null;
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  let disposed = false;

  function connect() {
    if (disposed) return;
    ws = new WebSocket(url);

    ws.onopen = () => {
      console.log("[logos relay] connected to backend");
    };

    ws.onmessage = async (event) => {
      let msg: Record<string, unknown>;
      try {
        msg = JSON.parse(event.data as string);
      } catch {
        return;
      }

      const type = msg.type as string;
      const id = msg.id as string | undefined;

      if (type === "execute") {
        const result = await registry.execute(
          msg.path as string,
          (msg.args as Record<string, unknown>) ?? {},
          "ws",
        );
        if (id && ws?.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ type: "result", id, data: result }));
        }
      } else if (type === "query") {
        const value = registry.query(msg.path as string);
        if (id && ws?.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ type: "result", id, data: { ok: true, state: value } }));
        }
      } else if (type === "list") {
        const commands = registry.list(msg.domain as string | undefined);
        const serializable = commands.map((c) => ({
          path: c.path,
          description: c.description,
          args: c.args,
        }));
        if (id && ws?.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ type: "result", id, data: { ok: true, state: serializable } }));
        }
      }
    };

    ws.onclose = () => {
      if (!disposed) {
        console.log("[logos relay] disconnected, reconnecting in 3s...");
        reconnectTimer = setTimeout(connect, 3000);
      }
    };

    ws.onerror = () => {
      ws?.close();
    };
  }

  // Subscribe to all events and forward to backend for external subscribers
  const unsub = registry.subscribe(/./, (event) => {
    if (ws?.readyState === WebSocket.OPEN) {
      ws.send(
        JSON.stringify({
          type: "event",
          path: event.path,
          args: event.args,
          result: event.result,
          timestamp: event.timestamp,
        }),
      );
    }
  });

  connect();

  return () => {
    disposed = true;
    unsub();
    if (reconnectTimer) clearTimeout(reconnectTimer);
    ws?.close();
  };
}
```

- [ ] **Step 2: Wire into CommandRegistryProvider**

Add to the first `useEffect` in `CommandRegistryContext.tsx`, after the `window.__logos` assignment:

```typescript
import { connectCommandRelay } from "../lib/commandRelay";

// Inside the useEffect, after window.__logos assignment:
const disconnectRelay = connectCommandRelay(registry);

// In the cleanup:
return () => {
  disconnectRelay();
  delete (window as unknown as Record<string, unknown>).__logos;
};
```

- [ ] **Step 3: Commit**

```bash
git add hapax-logos/src/lib/commandRelay.ts hapax-logos/src/contexts/CommandRegistryContext.tsx
git commit -m "feat(logos): add WebSocket relay client, auto-connect on boot"
```

---

## Task 13: Full integration test — verify everything works

- [ ] **Step 1: Run all frontend tests**

```bash
cd hapax-logos && pnpm vitest run
```

All tests should pass.

- [ ] **Step 2: Run full backend test suite**

```bash
cd /home/hapax/projects/hapax-council && uv run pytest tests/ -q --timeout=60
```

All tests should pass.

- [ ] **Step 3: Run typecheck and lint on frontend**

```bash
cd hapax-logos && pnpm exec tsc --noEmit && pnpm lint
```

- [ ] **Step 4: Run ruff on backend**

```bash
cd /home/hapax/projects/hapax-council && uv run ruff check . && uv run ruff format --check .
```

- [ ] **Step 5: Build frontend**

```bash
cd hapax-logos && pnpm build
```

Should succeed without errors.

- [ ] **Step 6: Manual smoke test**

Open Logos in browser at `http://localhost:5173`. Verify:
1. Press `g` — ground region focuses
2. Press `g` again — depth cycles
3. Press `/` — investigation overlay opens
4. Press `Escape` — overlay closes
5. Open browser console, run:
   ```javascript
   await window.__logos.execute("terrain.focus", { region: "ground" })
   window.__logos.query("terrain.focusedRegion")
   window.__logos.list("terrain")
   ```
6. Ctrl+P — command palette opens with registry commands

- [ ] **Step 7: Commit any fixes**

```bash
git add -A hapax-logos/ logos/
git commit -m "fix(logos): integration fixes for command registry"
```

- [ ] **Step 8: Final commit — clean up any remaining old imports**

Search for any remaining references to deleted hooks:
```bash
grep -r "useKeyboardShortcuts\|useStudioShortcuts\|DetectionKeyboardHandler\|StudioKeyboardHandler" hapax-logos/src/
```

Remove any found. Commit.
