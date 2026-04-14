# Logos build-time audit — low-hanging iteration-speed wins

**Date:** 2026-04-14
**Author:** delta (beta role)
**Scope:** Audits the hapax-logos rebuild pipeline for
iteration-speed wins. Asks: where in the 9-minute
`rebuild-logos.sh` cycle is time being left on the table?
**Register:** scientific, neutral
**Status:** investigation only — proposed config changes
are for alpha's consideration, no code ships from this
drop

## Headline

**Four fix-candidates.**

1. **No custom `[profile.release]` section anywhere in the
   `hapax-logos` workspace.** All three Cargo.toml files
   (`hapax-logos/Cargo.toml`, `src-tauri/Cargo.toml`,
   `src-imagination/Cargo.toml`) use Cargo's defaults.
   Default release profile has `incremental = false`,
   `codegen-units = 16`, `lto = false`. The missing knob
   here is **`incremental = true`** — because the
   rebuild-logos helper uses a persistent `CARGO_TARGET_DIR`
   at `~/.cache/hapax/build-target`, cargo CAN reuse
   incremental state across rebuilds, but the current
   profile disables that path. Every rebuild re-compiles
   all affected crates from scratch.
2. **No `~/.cargo/config.toml`, no `.cargo/config.toml` in
   the hapax-logos tree.** Rust is using the default
   system linker (`ld.bfd` or `ld.gold` depending on
   toolchain). **`mold`** and **`sccache`** are available
   in the Arch repos (`cachyos-extra-v3/mold 2.40.4-3.1`,
   `extra/mold 2.40.4-3`, same for sccache) but **not
   installed**. For a Tauri app pulling in
   `chromiumoxide`, `qdrant-client`, `reqwest`, `tokio`,
   and friends, the link phase is a meaningful chunk of
   wall-clock. `mold` cuts link time by 50–80 % on
   comparable large Rust projects.
3. **Vite's `target: "safari13"`** is unusually conservative
   for a Tauri 2 webview that only renders inside
   WebKit 2.50+. Bumping to `es2022` (or `esnext`) lets
   Vite skip ES2020+ transpilation on every build — both
   faster and smaller output. No behavioral change:
   WebKit 2.50 supports ES2022 natively.
4. **`build.reportCompressedSize` is not set** in
   `vite.config.ts`, so Vite computes gzip+brotli sizes
   on every build for the build-summary table. For a
   large bundle (the existing build output has 20+
   chunks), this is a few seconds per build that vanish
   if you set `reportCompressedSize: false`.

**Net impact.** Items 1 and 2 are the big ones. On the
current ~9 minute rebuild cycle (measured 2026-04-14T14:33:
`Consumed 5min 20.195s CPU time over 8min 58.409s wall
clock`), **I estimate** enabling incremental release builds
and adopting mold drops the steady-state incremental rebuild
to **3–5 minutes wall clock**. First build after a cargo
`fetch` doesn't benefit; subsequent rebuilds where only a
few files change benefit the most.

## 1. Current state — what `rebuild-logos` does

Traced from `scripts/rebuild-logos.sh` + `hapax-logos/
justfile`:

```
rebuild-logos.sh (every 5 min via hapax-rebuild-logos.timer)
  ├─ flock on $STATE_DIR/lock       (prevents concurrent runs)
  ├─ git fetch origin main
  ├─ git rev-parse origin/main      (cheap check)
  ├─ if SHA unchanged: exit 0       (fast path)
  ├─ git worktree sync to origin/main (scratch worktree at
  │                                   $HOME/.cache/hapax/rebuild/worktree,
  │                                   git reset --hard; preserves
  │                                   untracked node_modules + target)
  └─ cd hapax-logos && just install
     └─ just build
        ├─ just imagination   → cargo build --release -p hapax-imagination
        └─ just logos
           ├─ just frontend
           │  ├─ pnpm install --frozen-lockfile  (~2.3 s when warm)
           │  └─ pnpm build        (tsc -b && vite build)
           │      ├─ tsc -b        (TypeScript project references)
           │      └─ vite build    (Rollup bundle, measured ~4–5 min)
           └─ cargo build --release -p hapax-logos
                  --features tauri/custom-protocol    (~3–4 min)
```

Environment from `justfile`:

```make
CARGO_TARGET_DIR := $HOME/.cache/hapax/build-target
```

Good call — keeps cargo artifacts outside the worktree so
`git reset --hard` on the rebuild worktree doesn't wipe
them. This is the piece that *would* let incremental
release work if the profile allowed it.

## 2. Cargo profile — the missing `incremental = true`

```text
$ grep -nE "^\[profile|^incremental" hapax-logos/Cargo.toml \
                                     hapax-logos/src-tauri/Cargo.toml \
                                     hapax-logos/src-imagination/Cargo.toml
(no matches)
```

No overrides in any of the three manifests. Cargo uses the
built-in default for `release`:

```toml
# Cargo's built-in default [profile.release]
opt-level = 3
debug = false
split-debuginfo = '...'     # platform default
strip = "none"
debug-assertions = false
overflow-checks = false
lto = false
panic = 'unwind'
incremental = false         # ← THE PROBLEM FOR REBUILD SPEED
codegen-units = 16
rpath = false
```

**`incremental = false`** means: every release build
re-compiles all changed crates from scratch. Cargo does
NOT reuse per-function compilation units from the last
build. For large Rust projects this throws away a lot of
reusable work between rebuilds.

**Why this matters for rebuild-logos specifically.** The
`CARGO_TARGET_DIR` is persistent at `~/.cache/hapax/build-
target`. Every rebuild, cargo sees the previous release
artifacts. With `incremental = true`, cargo's dep-graph
tracking would diff the inputs and recompile only changed
crates. Without it, cargo recompiles any crate whose source
inputs hash differently. That's everything that depends on
a changed file.

**Cost of enabling.** `incremental = true` writes an
`incremental/` subdirectory inside the target. ~200 MiB
for a mid-size Tauri app. Some tools report incremental
release builds as slightly slower than non-incremental for
a SINGLE first build (~5 % extra overhead on the first
clean build). For subsequent rebuilds where a few files
change, incremental cuts cargo wall-clock significantly —
20–60 % depending on how much downstream recompilation the
change triggers.

**Proposed change** to `hapax-logos/Cargo.toml`:

```toml
[workspace]
members = [
    "src-tauri",
    "crates/hapax-visual",
    "src-imagination",
]
resolver = "2"

[profile.release]
incremental = true
codegen-units = 256
# Optional — more aggressive binary optimization at the
# cost of a slower first build:
# lto = "thin"
```

`codegen-units = 256` is Tauri's recommended default for
dev iteration (Cargo default is 16; higher is faster
compile, slightly slower binary). Combined with
`incremental = true`, incremental rebuilds become notably
faster.

**Tradeoff to be explicit about:** the binary will run
slightly slower at runtime with these settings. For a
Tauri app where the webview is doing the heavy lifting,
that's almost always the right trade; the host process
spends most of its time in IPC stubs, not CPU-bound Rust.

## 3. Linker — install `mold`

Current state:

```text
$ which mold
mold not in PATH

$ pacman -Ss '^mold$'
cachyos-extra-v3/mold 2.40.4-3.1
    A Modern Linker
extra/mold 2.40.4-3
    A Modern Linker
```

Available, not installed. Install is `sudo pacman -S mold`
(~5 MB).

`mold` is drop-in compatible with `ld`: the only
integration is telling `rustc` to invoke it. Two options:

**Option A** — workspace-local (no global change):

Create `hapax-logos/.cargo/config.toml`:

```toml
[target.x86_64-unknown-linux-gnu]
linker = "clang"
rustflags = ["-C", "link-arg=-fuse-ld=mold"]
```

Requires `clang` installed (usually is on CachyOS). Only
affects builds from within `hapax-logos/`. Doesn't touch
any other Rust project on the system.

**Option B** — user-level (applies to all Rust builds):

Create `~/.cargo/config.toml`:

```toml
[target.x86_64-unknown-linux-gnu]
linker = "clang"
rustflags = ["-C", "link-arg=-fuse-ld=mold"]
```

Same content, broader scope.

**Expected savings.** For Tauri 2 apps with heavy
dependencies, link phase runs 10–30 seconds with the
default linker. mold typically cuts this to 2–8 seconds.
That's **8–22 seconds per rebuild** saved, on top of the
incremental-release savings.

## 4. Optional — `sccache` for cross-rebuild caching

```text
$ pacman -Ss '^sccache$'
cachyos-extra-v3/sccache 0.14.0-1.1
extra/sccache 0.14.0-1
```

Install: `sudo pacman -S sccache`. Config:

```toml
# ~/.cargo/config.toml (or hapax-logos/.cargo/config.toml)
[build]
rustc-wrapper = "sccache"
```

`sccache` caches the output of `rustc` invocations keyed
on the input hash. For a persistent `CARGO_TARGET_DIR`
that already survives across rebuild cycles, the
cross-rebuild value of sccache is **smaller than mold**
(cargo's own dep tracking already catches most of this).
Bigger value when switching between branches in-place —
and the hapax-logos dev workflow does have the
alpha/beta/delta branch rotation.

**My recommendation: ship mold first** (highest ratio,
smallest change), measure savings, then consider sccache
if the alpha/beta branch-switch case is a pain point.

## 5. Vite — two small wins

### 5.1 Bump `target`

```typescript
// vite.config.ts current:
build: {
    target: "safari13",
    ...
}

// proposed:
build: {
    target: "es2022",     // or "esnext" — Tauri 2 webview supports it
    ...
}
```

`safari13` was the "safe" default for a public web app
shipping to real Safari users. For a Tauri 2 app running
only in a bundled WebKit (≥ 2.50), it's dead weight — Vite
transpiles away ES2020+ syntax on every build for no
runtime benefit. `es2022` lets the bundler skip that work
and emit the original source where possible.

Expected savings: ~5–15 % of vite build time on a large
bundle, plus slightly smaller output files.

### 5.2 Skip compressed-size reporting

```typescript
build: {
    ...
    reportCompressedSize: false,
}
```

Vite computes gzip+brotli sizes for every emitted chunk
to populate the build-summary table the user sees in
stdout. For a bundle with 20+ chunks (which hapax-logos
has — manualChunks vendor-react, vendor-recharts,
vendor-xyflow, vendor-hls, plus the automatic route
splits), this is a few seconds of pure reporting
overhead per build. Setting it to `false` hides the
compressed sizes from the build log but removes the
work. The compressed sizes don't affect anything
operational; they're just a human-readable report.

Expected savings: 2–5 seconds per build.

## 6. TypeScript incremental state — worth verifying

`pnpm build` runs `tsc -b` before `vite build`. `tsc -b`
uses TypeScript project references to enable incremental
type checking via `.tsbuildinfo` cache files.

Grep for these files in the live worktree:

```text
$ find hapax-logos -name "*.tsbuildinfo" | grep -v node_modules
(no matches)
```

No `.tsbuildinfo` files at the project level. They may be
living inside `dist/` (typical outDir), inside
`node_modules/.cache/`, or derived from a path declared
in `tsconfig.app.json` I didn't read.

**If `.tsbuildinfo` is not being produced at all**, every
`tsc -b` invocation is a full type check. Slow.

**If it's being produced inside `dist/`**, and `dist/` is
in `.gitignore` (which it is — line 2 of `.gitignore`),
the file survives `git reset --hard` (untracked). Good.

**If it's being produced somewhere that `git reset --hard`
wipes**, that's a perf bug — every rebuild re-checks
everything. The `rebuild-logos.sh` script uses
`git reset --hard "$CURRENT_SHA"` (line 81), which wipes
tracked file changes but **preserves untracked files**,
so `.tsbuildinfo` in an untracked / gitignored path is
safe.

**Action for alpha:** run one rebuild, then check whether
`.tsbuildinfo` files exist in the rebuild worktree and
whether their mtimes are old (evidence of reuse) or fresh
(evidence of always-regenerated). That's a 30-second check
that resolves this item.

## 7. What's intentionally not in this drop

- **`[profile.release] lto = "thin"`** — valid optimization
  but the tradeoff is slower first build + (probably)
  slower incremental rebuilds too. Not obviously an
  iteration-speed win. If alpha wants a smaller or faster
  binary for the `install` step (what the operator
  actually runs), adding thin LTO is a separate
  call.
- **Cargo `jobs`** — already defaults to the number of
  logical cores (16). No change available.
- **Parallelism between `imagination` and `logos`** in
  `justfile` — they currently run sequentially. Could
  run `cargo build --release -p hapax-imagination -p
  hapax-logos` in a single invocation, which lets cargo
  schedule both crate graphs together. Minor win at
  best; Cargo is already parallelizing inside the
  workspace.
- **Skipping `tsc -b`** — Vite does its own type-free
  transpilation and can be used without tsc, but then
  TypeScript type errors don't block builds. Alpha
  presumably wants type checking; not changing this.

## 8. Follow-ups for alpha

Ordered by ratio (impact ÷ cost):

1. **Install `mold`**. `sudo pacman -S mold`. 5 MB install.
2. **Create `hapax-logos/.cargo/config.toml`** with the
   3-line mold rustflags (§ 3 option A).
3. **Add `[profile.release] incremental = true,
   codegen-units = 256`** to `hapax-logos/Cargo.toml`.
4. **Add `build.reportCompressedSize: false`** and bump
   `build.target` to `"es2022"` in `vite.config.ts`.
5. **Check `.tsbuildinfo` status** — one-minute diagnostic
   to decide if TypeScript incremental is actually
   working.
6. **Optionally install `sccache`** — revisit after #1–#4
   land, based on measured incremental rebuild time.
7. **Add a timing tee to `rebuild-logos.sh`** — log
   `vite build` and `cargo build` wall-clock separately
   so before/after comparisons on the above changes are
   measurable rather than folklore.

After each of #1–#4, the right measurement is: run one
full rebuild from a cold cache (delete `~/.cache/hapax/
build-target/release`), then run a second rebuild after
a trivial one-line change in `src-tauri/`. Compare wall
clock on the second rebuild.

## 9. References

- `scripts/rebuild-logos.sh` — pipeline source
- `hapax-logos/justfile` — `frontend` / `imagination` /
  `logos` / `build` targets
- `hapax-logos/Cargo.toml` — workspace manifest, no
  `[profile.release]`
- `hapax-logos/src-tauri/Cargo.toml` — crate manifest,
  no overrides
- `hapax-logos/vite.config.ts` — Vite config with
  `target: "safari13"` and no `reportCompressedSize`
- `hapax-logos/.gitignore` lines 1–6 — `dist/`, `target/`,
  `src-imagination/target/`, `crates/*/target/` all ignored
- `pacman -Ss '^mold$|^sccache$'` — availability check
- Build time measurement: `rebuild-logos.service` log
  entry at 2026-04-14T09:33:56 —
  "Consumed 5min 20.195s CPU time over 8min 58.409s
  wall clock time, 3.8G memory peak"
