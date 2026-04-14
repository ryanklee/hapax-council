# FINDING-Q Spike Notes — WGSL hot-reload validation + rollback

**Date:** 2026-04-14
**Author:** alpha (LRR Phase 0 PR #3 spike)
**Scope:** Reading hapax-imagination's WGSL hot-reload path to design FINDING-Q steps 2-4 (validation, rollback, counter). Step 1 (RUST_BACKTRACE=1) already shipped in PR #768.
**Goal of this doc:** capture enough understanding to implement steps 2-4 in a follow-up PR (or split into 3a/3b/3c) without re-reading the codebase from scratch.

## 1. Where hot-reload happens

**File:** `hapax-logos/crates/hapax-visual/src/dynamic_pipeline.rs`
**Function:** `DynamicPipeline::try_reload(&mut self, device: &wgpu::Device) -> bool` (line 490)

**Trigger:** `pending_reload: Arc<AtomicBool>` flipped by an inotify watcher (`_watcher: RecommendedWatcher`) when `PLAN_FILE` (`/dev/shm/hapax-imagination/pipeline/plan.json`) changes. The `try_reload` call is invoked at the top of every `render()` (line 794) so a freshly-set pending flag is honored within one frame.

**Current sequence:**

1. Read `pending_reload`. Bail if false.
2. Read PLAN_FILE → `plan_data: String`. **On read error: log `warn`, return false** (keeps old `self.passes`). Good.
3. Parse JSON → `PlanFile`. **On parse error: log `warn`, return false** (keeps old). Good.
4. Walk `plan.passes_by_target()` → build `active_passes: Vec<(String, PlanPass)>` with namespaced texture names.
5. **Empty plan special case:** clear `self.passes`, log info, return true (intentional — renders black).
6. Allocate intermediate textures via `ensure_texture` / `ensure_temporal_texture`.
7. **Build phase loop** over `active_passes`:
    - Read shader file. **On read error: log `warn`, `continue`** ← **silent drop of the failing pass**. The build proceeds with a partial set.
    - Compile fragment / compute module via `device.create_shader_module(...)`. **No error handling — wgpu panics on invalid WGSL**.
    - Create pipeline layout + pipeline. Same — wgpu panics on layout mismatch.
    - Push the new `DynamicPass` onto `new_passes`.
8. **The swap (line 776): `self.passes = new_passes;`** ← **THE IRREVERSIBLE POINT**.
9. Log `info!("dynamic_pipeline: loaded {} passes", count)`. Return true.

## 2. What state needs to be preserved as last-known-good

**Only `self.passes`** (`Vec<DynamicPass>`) is replaced wholesale by the hot-reload. Everything else on `DynamicPipeline` (texture pool, uniform buffer, vertex module, etc.) is preserved across reloads.

**Implication:** rollback only needs to snapshot `self.passes` — and only if validation succeeds and we're about to swap. If validation fails BEFORE the swap, there's nothing to roll back to (the old `self.passes` is still in place).

**Important nuance:** `self.passes` is `Vec<DynamicPass>`. `DynamicPass` contains `wgpu::RenderPipeline` / `wgpu::ComputePipeline` handles which are Arc-backed. Cloning a `Vec<DynamicPass>` clones the wgpu handles cheaply. So a snapshot is `let last_known_good = self.passes.clone();` — cheap, no GPU re-upload.

## 3. The two failure modes FINDING-Q must catch

### Failure mode A — silent drop (current behavior)

A shader file fails to read (typo in plan.json's shader path, missing file, etc.). The build phase logs a warning and `continue`s. **The build completes with fewer passes than the plan declared.** The swap installs the partial set. Next render produces missing-pass artifacts (black pixels, missing layers, wrong final output).

**Fix shape:** detect this. If `new_passes.len() != active_passes.len()`, the swap is invalid. Reject before line 776.

### Failure mode B — panic during pipeline build

`device.create_shader_module(...)` calls into wgpu, which panics on:
- Invalid WGSL (parse errors, type errors)
- Missing entry points
- Bind group layout mismatches against the declared pipeline layout

**Currently:** the panic propagates up the stack, kills the render thread, takes down the imagination process. Step 1 of FINDING-Q (PR #768 RUST_BACKTRACE=1) lets us see the panic location, but does not prevent the crash.

**Fix shape:** wrap `device.create_shader_module` + `device.create_*_pipeline` in `std::panic::catch_unwind` so a panicking pass is treated like a failed pass — drop it, set the failure flag, reject the swap.

**Caveat:** `catch_unwind` requires `UnwindSafe`. wgpu types may not be `UnwindSafe`. May need `AssertUnwindSafe` wrapper, with the understanding that wgpu state after a panic might be inconsistent. The pragmatic safer alternative is to validate the WGSL **statically** before calling wgpu — use `naga::front::wgsl::parse_str` to validate the source before passing it to `device.create_shader_module`. That avoids the panic entirely.

## 4. Step-by-step design

### Step 2 — WGSL manifest validation BEFORE the swap

Two layers:

**Layer 2a — pre-build validation (cheap, catches Failure mode A):**

```rust
// Compute a manifest hash for structured logging
let manifest_hash = {
    use std::collections::hash_map::DefaultHasher;
    use std::hash::{Hash, Hasher};
    let mut h = DefaultHasher::new();
    plan_data.hash(&mut h);
    format!("{:016x}", h.finish())
};

// Pre-validate every pass's shader file is readable + parseable BEFORE
// touching wgpu. Fail-closed if any pass would be silently dropped.
let mut validation_failures: Vec<String> = Vec::new();
for (target_name, plan_pass) in &active_passes {
    let shader_path = self.plan_dir.join(&plan_pass.shader);
    let fragment_source = match std::fs::read_to_string(&shader_path) {
        Ok(src) => src,
        Err(e) => {
            validation_failures.push(format!(
                "{}/{}: shader file unreadable: {}",
                target_name, plan_pass.node_id, e
            ));
            continue;
        }
    };
    // Naga static parse — catches WGSL syntax + type errors without
    // touching wgpu (no panic risk).
    let combined = format!("{}\n{}", SHARED_UNIFORMS_WGSL, fragment_source);
    if let Err(e) = naga::front::wgsl::parse_str(&combined) {
        validation_failures.push(format!(
            "{}/{}: WGSL parse failed: {:?}",
            target_name, plan_pass.node_id, e
        ));
    }
}

if !validation_failures.is_empty() {
    log::warn!(
        "dynamic_pipeline: hot-reload validation FAILED, {} pass(es) invalid, manifest_hash={}: {}",
        validation_failures.len(),
        manifest_hash,
        validation_failures.join("; ")
    );
    increment_rollback_counter("validation_failed");  // Step 4
    return false;  // Keeps old self.passes
}
```

**Layer 2b — bind-group-layout sanity check (more thorough, optional):**

If we want full pipeline validation without wgpu panic risk, build the pipeline pieces inside `catch_unwind`:

```rust
let build_result = std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| {
    // existing fragment_module + pipeline_layout + render_pipeline build
}));
match build_result {
    Ok(pipeline) => new_passes.push(...),
    Err(panic) => {
        validation_failures.push(format!("{}: wgpu panic during build", plan_pass.node_id));
    }
}
```

This is more invasive (touches the build loop). **Recommended: ship Layer 2a alone in PR #3a.** Layer 2b is a separate stretch goal — it requires understanding wgpu's `UnwindSafe` story and may be platform-dependent.

### Step 3 — Previous-good shader rollback panic handler

After Step 2 lands, the validation already prevents the swap on failure. The "rollback" semantics become:

**For the validation-detected failure path** (most common): no rollback needed because the old `self.passes` is still in place. Step 2's `return false` IS the rollback.

**For the runtime-panic path during render** (rare but real): wrap the per-pass execution in `render()` with a panic handler. On panic, log structured event with the offending pass's `node_id`, increment the counter, and remove the broken pass from `self.passes` (or mark it as dead so render skips it). Subsequent frames continue with the surviving passes.

This second path is harder because `render()` runs on the GPU thread and a wgpu panic mid-frame may have already corrupted the device state. The pragmatic option: instead of trying to recover mid-frame, set a `self.shader_disaster` flag, log the event, increment the counter, and let the next `try_reload` rebuild from a clean known-good snapshot. The "snapshot" can be a copy of the LAST PLAN that successfully validated — stored on disk at `~/.cache/hapax-imagination/last-known-good-plan.json`.

**Recommended split:**
- **PR #3a:** Step 2 Layer 2a (naga pre-validation) + Step 4 counter
- **PR #3b:** Step 3 last-known-good plan snapshot + recovery on next reload after a runtime panic
- **PR #3c (optional):** Step 2 Layer 2b (catch_unwind around wgpu build calls)

### Step 4 — `hapax_imagination_shader_rollback_total` counter

**Architecture:** the imagination crate has NO direct prometheus exporter. The reverie pool metrics work via:

```
DynamicPipeline::pool_metrics() (Rust)
  → headless.rs::publish_pool_metrics() (writes JSON to /dev/shm/hapax-imagination/pool_metrics.json)
    → agents/studio_compositor/metrics.py::_mirror_reverie_pool_metrics() (Python reader)
      → reverie_pool_* Prometheus gauges on :9482
```

**Counter follows the same pattern:**

1. Add a static counter to `DynamicPipeline`:
   ```rust
   pub struct DynamicPipeline {
       // ... existing fields ...
       shader_rollback_total: Arc<AtomicU64>,
   }
   ```
2. Increment from any rollback path:
   ```rust
   self.shader_rollback_total.fetch_add(1, Ordering::Relaxed);
   ```
3. Expose via a public getter:
   ```rust
   pub fn shader_rollback_total(&self) -> u64 {
       self.shader_rollback_total.load(Ordering::Relaxed)
   }
   ```
4. Publish from `headless.rs` alongside the pool metrics — extend the JSON shape:
   ```json
   {"bucket_count":..., "shader_rollback_total":N, "shader_rollback_last_reason":"validation_failed"}
   ```
5. Read in compositor `metrics.py::_mirror_reverie_pool_metrics()` and publish a new Prometheus counter `hapax_imagination_shader_rollback_total`.

**JSON path:** can reuse `pool_metrics.json` (extend the shape) OR create a sibling `~/.cache/hapax-imagination/shader_health.json`. Reusing pool_metrics.json is one fewer file to manage; creating a sibling keeps concerns separated. **Recommendation:** sibling file. The pool metrics are render-loop-frequency (60 Hz) and the shader rollback counter is event-driven (rare); separate cadences keep the writers clean.

## 5. Test plan for PR #3a

- **Unit:** synthetic `PlanFile` with a missing shader path → `try_reload` returns false, counter increments, `self.passes` unchanged.
- **Unit:** synthetic `PlanFile` with valid shader paths but broken WGSL → `try_reload` returns false (naga rejects), counter increments, `self.passes` unchanged.
- **Unit:** valid plan → `try_reload` returns true, counter does NOT increment, `self.passes` updated.
- **Integration:** simulate a hot-reload by writing a known-bad plan to `PLAN_FILE` and verifying the imagination process logs the rollback warning + continues rendering the previous valid plan.

## 6. Risks and unknowns

- **Naga version compatibility:** the imagination crate uses `wgpu = "24"`, which depends on a specific naga version. Need to add `naga` as a direct dependency at the matching version. `cargo tree -p hapax-visual | grep naga` will show the right version.
- **`UnwindSafe`:** wgpu objects may not be `UnwindSafe`. Layer 2b in Step 2 may need `AssertUnwindSafe` with documented assumptions, or be deferred entirely. Layer 2a (naga static parse) sidesteps this — recommended.
- **Cross-process IPC freshness:** the `_mirror_reverie_pool_metrics()` Python reader runs every N seconds (existing cadence — need to verify). The shader rollback counter should be visible within one Prometheus scrape interval after a rollback. If the existing reader doesn't reread fast enough, may need to bump its frequency.
- **`last-known-good-plan.json`** for Step 3 rollback adds disk I/O. Could keep it in memory only (on `DynamicPipeline`) and skip persistence. Persistence helps recover from imagination process restarts mid-broken-plan.

## 7. Recommended PR sequence

| PR | Scope | Effort | Independent? |
|---|---|---|---|
| **Phase 0 PR #3a** | Step 2 Layer 2a (naga pre-validation) + Step 4 counter (in-memory) + counter publish via JSON sibling | ~1 session | yes |
| **Phase 0 PR #3b** | Step 3 last-known-good plan snapshot + recovery on next reload | ~1 session | yes (depends on 3a) |
| **Phase 0 PR #3c** | Step 2 Layer 2b (catch_unwind wgpu build) — optional stretch | ~half session | yes (depends on 3a) |

Together the three PRs close LRR Phase 0 item 4. Each PR independently advances the exit criterion checkbox.

## 8. What this spike doc is

A handoff artifact. The next alpha session opening Phase 0 PR #3a reads this doc instead of re-doing the spike. Implementation can start at §4 Step 2 Layer 2a and follow the recommended sequence in §7.
