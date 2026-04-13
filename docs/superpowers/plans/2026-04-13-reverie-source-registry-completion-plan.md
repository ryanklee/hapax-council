# Reverie + Source Registry Completion Epic — Master Plan

**Spec:** `docs/superpowers/specs/2026-04-13-reverie-source-registry-completion-design.md`
**Parent spec:** `docs/superpowers/specs/2026-04-12-compositor-source-registry-foundation-design.md`
**Parent plan:** `docs/superpowers/plans/2026-04-12-compositor-source-registry-foundation-plan.md` (4049 lines, 29 TDD tasks)

**Execution model:** single alpha session, 9 phases, one PR per phase, serial execution off latest `main`. Each phase's task-level TDD steps are authoritative in the parent plan; this document is the phase orchestration layer and the inline plan for Phase 8 (new adjacent work).

## Phase list

| # | Phase | Parent tasks | Estimated PR size | Dependency |
|---|---|---|---|---|
| 1 | Merge PR #735 (Task 14) | D14 | (existing PR) | — |
| 2 | Cairo natural-size migration | C8, C9, C10, C11 | M | Phase 1 |
| 3 | Render path flip | E15, E16 | M | Phase 2 |
| 4 | Reverie headless mode | F18, F19 | M (Rust) | Phase 3 (for end-to-end verification) |
| 5 | Command server + control path | G20, G21, G22 | L | Phase 3 |
| 6 | Persistent appsrc pads | H23, H24, H25 | M | Phase 5 |
| 7 | Preset schema extension | I26, I27 | S | Phase 6 |
| 8 | Adjacent observability hardening | NEW (inline) | M | Phase 3+ (freshness gauge), Phase 6 (appsrc metric conventions) |
| 9 | Final acceptance sweep | J28, J29 | S | All prior |

Sizes: S ≤ 200 LoC, M ≤ 800 LoC, L ≤ 2000 LoC. These are approximate targets, not hard caps.

## Pre-flight

Before Phase 1 starts:

- [ ] Epic design doc (this file's sibling) committed to `docs/superpowers/specs/2026-04-13-reverie-source-registry-completion-design.md` via a non-blocking docs-only PR (bundled with a CLAUDE.md pointer for CI).
- [ ] Master plan (this file) committed to `docs/superpowers/plans/2026-04-13-reverie-source-registry-completion-plan.md` in the same PR.
- [ ] Relay update posted: alpha.yaml updated with `focus: "executing reverie source registry completion epic"`.
- [ ] Inflection posted to `~/.cache/hapax/relay/inflections/20260413-<time>-alpha-epic-start.md` so beta and any future delta see the work in flight.
- [ ] Convergence log entry added: `RESOLVED-COMPLEMENTARY` for BETA-FINDING-2026-04-13-C adoption into Phase 8.

## Phase 1 — Merge PR #735

**Tasks:**

- [ ] Confirm CI all-green on PR #735 (`gh pr checks 735`).
- [ ] `gh pr merge 735 --squash --delete-branch -R ryanklee/hapax-council`.
- [ ] `git fetch origin && git checkout main && git pull`.
- [ ] Verify `git log --oneline -1` shows the squash-merge of `feat/phase-d-task-14-layout-wiring`.
- [ ] `systemctl --user start hapax-rebuild-services.service` to refresh the running compositor with the new main.
- [ ] Confirm compositor is still healthy: `systemctl --user is-active studio-compositor.service` and `journalctl --user -u studio-compositor.service --since "1 min ago" | grep -v "^$" | tail -20`.
- [ ] Remove the spontaneous worktree used for Phase D task 14 (`git worktree remove ~/projects/hapax-council--phase-d-task-14`).

**Exit criterion:** `git log --oneline main | grep "Phase D task 14"` returns the merged squash commit. Compositor active.

## Phase 2 — Cairo natural-size migration (parent C8–C11)

**Branch:** `feat/cairo-natural-size-migration`

**Tasks:** execute parent plan tasks 8, 9, 10, 11 in order. Each parent task has its own failing-test / impl / commit cycle. Do not batch commits — one commit per task, squash-merge at PR time.

**Task 8 (parent plan lines ~1116–1303) — TokenPoleCairoSource migration.**

Parent-plan fidelity except for one delta: **write a golden-image regression test BEFORE dropping the `OVERLAY_*` constants.** Parent plan task 8 assumes the test is optional; delta handoff explicitly flagged this task as the reason the whole Phase C was deferred. The golden-image pattern:

1. Before any code change, render `TokenPoleCairoSource` once at natural size with a fixed seed (monkeypatch `time.time()` to a constant, monkeypatch `random.Random(seed=42)` if stochasticity exists). Save the resulting `cairo.ImageSurface` to `tests/fixtures/token_pole_golden.png` via `surface.write_to_png()`. Commit the golden separately.
2. Refactor `token_pole.py` to drop `OVERLAY_X=20`, `OVERLAY_Y=20`, `OVERLAY_SIZE=300` and rewrite the 17+ sites where they're referenced in the render method so all coordinates are relative to `(0, 0)` of a 300×300 natural-size surface.
3. Re-render with the same fixed seed, compare against the golden. Max allowed per-pixel delta: 2 (LSB noise tolerance). Any larger delta means the refactor visibly changed output.
4. If the refactor was semantically identical (just `OVERLAY_X`/`OVERLAY_Y` shifted to origin), the output is pixel-identical.

**Task 9 (parent plan lines ~1304–1393) — AlbumOverlayCairoSource verification.**

Per parent plan + a verification step: `grep -n "OVERLAY_X\|OVERLAY_Y\|OVERLAY_SIZE" agents/studio_compositor/album_overlay.py` must return zero hits before AND after Task 9 (class already draws at origin per delta's initial grep). If grep returns hits, the refactor parallels Task 8.

**Task 10 (parent plan lines ~1394–1437) — SierpinskiCairoSource verification.**

Same as Task 9 but for `sierpinski_renderer.py`.

**Task 11 (parent plan lines ~1438–1482) — Final shim sweep.**

Per parent plan: grep the repo for leftover `OVERLAY_X`, `OVERLAY_Y`, `OVERLAY_SIZE` references outside the legacy facade classes. Verify the legacy facades (`TokenPole`, `AlbumOverlay`, `SierpinskiRenderer`) still work by running existing compositor integration tests.

**PR body template:**

```
Phase 2 of the reverie source registry completion epic. Parent plan
tasks 8–11.

Migrates the three PiP cairo sources off hardcoded canvas-relative
offsets onto natural-size rendering:

- TokenPoleCairoSource: 300×300 natural. OVERLAY_X/Y/SIZE constants
  removed from token_pole.py and all 17 render-site references
  rewritten to origin-relative coordinates. Golden-image regression
  test pins the pixel output.
- AlbumOverlayCairoSource: 400×520 natural. Already draws at origin
  per Phase 3b of the compositor unification epic; audit confirms no
  hidden offset. Tests tightened.
- SierpinskiCairoSource: 640×640 natural. Same as album.
- Shim sweep: legacy facade classes (`TokenPole`, `AlbumOverlay`,
  `SierpinskiRenderer`) continue to work for fx_chain._pip_draw's
  legacy code path because Phase 3 (the render flip) has not shipped
  yet.

Tests (N new):
- tests/fixtures/token_pole_golden.png
- tests/test_token_pole_natural_size.py
- tests/test_album_overlay_natural_size.py
- tests/test_sierpinski_natural_size.py
- tests/test_cairo_sources_no_residual_overlay_constants.py

Plan task numbers: C8, C9, C10, C11. PR N/9 of the epic.
```

**Exit criterion:** PR merged. `rg 'OVERLAY_X|OVERLAY_Y|OVERLAY_SIZE' agents/studio_compositor/` returns only comment references or archival docs, not code.

## Phase 3 — Render path flip (parent E15–E16)

**Branch:** `feat/render-path-layout-state-walk`

**Tasks:** parent plan tasks 15 (blit_scaled helper) and 16 (_pip_draw refactor).

**Task 15 (parent plan lines ~1880–1994) — `blit_scaled` helper.**

Per parent plan verbatim.

**Task 16 (parent plan lines ~1995–2179) — `_pip_draw` refactor to walk LayoutState.**

Per parent plan + three invariants from the epic design:

1. When a source returns `None` from `get_current_surface()`, blit nothing and increment `compositor_source_frame_skip_total{source_id}`. Do NOT fall back to the legacy `compositor._token_pole.draw(cr)` path.
2. Legacy `TokenPole.draw()`, `AlbumOverlay.draw()`, `SierpinskiRenderer.draw()` methods gain `@deprecated` decorators pointing at Phase 3 epic removal (Phase 9).
3. Legacy facade construction in `fx_chain.py` lines ~244–263 (the `compositor._album_overlay = AlbumOverlay()` / `compositor._token_pole = TokenPole()` / etc.) stays in place — backward compat during transition. Deleted in Phase 9.

**Exit criterion:** After merge + `hapax-rebuild-services.service`, compositor frame still shows Vitruvian UL + album LL + reverie UR (from the PR #723 producer) + sierpinski LR empty, via the new `LayoutState`-walking render path.

## Phase 4 — Reverie headless mode (parent F18–F19)

**Branch:** `feat/reverie-headless-mode`

**Tasks:** parent plan tasks 18 and 19.

**Task 18 (parent plan lines ~2300–2436) — `headless::Renderer` branch in `src-imagination/src/main.rs`.**

Per parent plan verbatim. Notes:

- Create `src-imagination/src/headless.rs` as a new module.
- `resumed()` branches on `env::var("HAPAX_IMAGINATION_HEADLESS").ok().as_deref() == Some("1")`.
- Headless renderer owns a `wgpu::Texture` of the same dimensions as the winit surface would have been (1920×1080 per the existing surface config) and calls `DynamicPipeline::render` into a view of that texture on a 60fps tokio interval.
- `ShmOutput::write_frame()` already writes `/dev/shm/hapax-sources/reverie.rgba` and sidecar per PR #723; that path is unchanged.
- `WindowEvent::*` handlers become no-ops in headless mode because no Window exists.
- `ApplicationHandler::resumed()` in headless mode constructs the `headless::Renderer` directly and does not call `event_loop.create_window()`.

**Task 19 (parent plan lines ~2437–2468) — systemd unit `HAPAX_IMAGINATION_HEADLESS=1`.**

Per parent plan verbatim. **Deployment gate:** do not merge Phase 4 until Phase 3 has been running cleanly for at least one `rebuild-services.timer` cycle (~5 min). Rationale: if Phase 3 has a regression, rolling back Phase 3 is cheap. If Phase 4's headless mode has a regression and Phase 3 is broken, two reverts needed.

**Exit criterion:**

- `HAPAX_IMAGINATION_HEADLESS=1 hapax-imagination` runs with no visible Wayland window.
- `stat -c '%Y' /dev/shm/hapax-sources/reverie.rgba` mtime advances every ~16ms.
- `jq . /dev/shm/hapax-sources/reverie.rgba.json | jq .frame_id` increments.
- Existing `hapax-logos` VisualSurface HTTP server at `:8053` still serves frames (the `/dev/shm/hapax-visual/frame.{jpg,rgba}` path is unchanged).

## Phase 5 — Command server + control path (parent G20–G22)

**Branch:** `feat/compositor-command-server`

**Tasks:** parent plan tasks 20, 21, 22.

**Task 20 (parent plan lines ~2469–2837) — `command_server.py` UDS handler.**

Per parent plan verbatim. Implementation note: use the newline-delimited JSON framing from the parent spec (one JSON object per line, `\n` separator), with `asyncio.start_unix_server` as the transport. Socket path: `$XDG_RUNTIME_DIR/hapax-compositor.sock`. `atexit` cleanup + `systemd-tmpfiles` exclusion for the socket.

**Task 21 (parent plan lines ~2838–3014) — Tauri Rust pass-through + frontend command registry.**

Per parent plan verbatim. `hapax-logos/src-tauri/src/commands/compositor.rs` is a thin UDS client; no compositor logic in Tauri. `hapax-logos/src/lib/commands/compositor.ts` registers 5 commands (`surface.set_geometry`, `surface.set_z_order`, `assignment.set_opacity`, `layout.save`, `layout.reload`).

**Task 22 (parent plan lines ~3015–3267) — file-watch + debounced auto-save.**

Per parent plan verbatim with the mtime-polling implementation choice: use `pathlib.Path.stat().st_mtime_ns` in a 500ms background loop rather than `inotify_simple` to avoid adding a runtime dependency. File-watch polling cadence is low-cost (one stat call every 500ms) and the layout file is < 4KB. Self-write detection via `_last_self_write_mtime` tolerance window of 2s.

**Exit criterion:**

- From a terminal: `echo '{"command": "compositor.surface.set_geometry", "args": {"surface_id": "pip-ur", "x": 1260, "y": 40, "w": 640, "h": 360}}' | nc -U $XDG_RUNTIME_DIR/hapax-compositor.sock` produces a `{"status": "ok"}` response and the reverie PiP moves on the next frame.
- Hand-edit `~/.config/hapax-compositor/layouts/default.json` → compositor picks up changes within 2s.
- `~/.config/hapax-compositor/layouts/default.json` updates on disk when commands are issued via the socket (after 500ms debounce).

## Phase 6 — Persistent appsrc pads (parent H23–H25)

**Branch:** `feat/persistent-appsrc-pads`

**Tasks:** parent plan tasks 23, 24, 25.

Per parent plan verbatim. The main-layer integration test (`tests/studio_compositor/test_main_layer_path.py`) is the "railroad tracks" proof: an augmented layout fixture adds an `fx_chain_input` surface + assignment for reverie, renders 30 frames, asserts reverie's RGBA bytes reach the `glvideomixer` output buffer with ≤5% golden-image tolerance.

**Exit criterion:**

- `test_main_layer_path.py` passes.
- Existing default.json runtime output unchanged (no visible main-layer promotion).
- `gst-inspect-1.0 glvideomixer | grep alpha` confirms the `alpha` pad property is available (spec assumption — re-verify during implementation).

## Phase 7 — Preset schema extension (parent I26–I27)

**Branch:** `feat/preset-inputs-schema`

**Tasks:** parent plan tasks 26 and 27.

Per parent plan verbatim. Resolution timing is **load-time** (parent spec open question 3 resolved in this epic). Unknown pad → `UnknownPresetInputError` raised, preset load blocked, structured error with preset name + unknown pad name in the message.

**Exit criterion:**

- `Preset(inputs=[PresetInput(pad="reverie", as_="layer0")])` validates and persists.
- Loading a preset with an unknown pad raises `UnknownPresetInputError`.
- Existing presets without `inputs` load unchanged.

## Phase 8 — Adjacent observability hardening (new)

**Branch:** `feat/observability-hardening`

This phase has no parent plan counterpart. Task breakdown inline.

### Task 8.1 — `FreshnessGauge` shared helper + imagination-loop seed

**Files:**
- New: `shared/freshness_gauge.py`
- New: `tests/test_freshness_gauge.py`
- Modify: `agents/imagination_loop.py` — construct gauge, call `mark_published()` / `mark_failed()`
- Modify: `agents/health_monitor/` — add `check_imagination_freshness()` helper

**Steps:**

- [ ] **Step 1: Write the failing test** (`tests/test_freshness_gauge.py`)

```python
"""FreshnessGauge tests — per-producer freshness contracts for always-on loops."""
from __future__ import annotations

import time

import pytest

from shared.freshness_gauge import FreshnessGauge


def test_new_gauge_reports_infinite_age_before_first_publish():
    gauge = FreshnessGauge("test_producer", expected_cadence_s=30)
    assert gauge.age_seconds() == float("inf")
    assert gauge.is_stale()


def test_mark_published_resets_age():
    gauge = FreshnessGauge("test_producer", expected_cadence_s=30)
    gauge.mark_published()
    assert gauge.age_seconds() < 0.1


def test_mark_failed_does_not_reset_age():
    gauge = FreshnessGauge("test_producer", expected_cadence_s=30)
    gauge.mark_published()
    time.sleep(0.05)
    gauge.mark_failed(RuntimeError("nope"))
    assert gauge.age_seconds() >= 0.05  # still counting from last publish


def test_is_stale_at_10x_cadence_by_default():
    gauge = FreshnessGauge("test_producer", expected_cadence_s=0.01)
    gauge.mark_published()
    time.sleep(0.12)  # 12x cadence
    assert gauge.is_stale()


def test_is_stale_tolerance_mult_override():
    gauge = FreshnessGauge("test_producer", expected_cadence_s=0.01)
    gauge.mark_published()
    time.sleep(0.03)  # 3x cadence
    assert not gauge.is_stale(tolerance_mult=5.0)
    assert gauge.is_stale(tolerance_mult=2.0)


def test_counter_increments_on_publish():
    gauge = FreshnessGauge("test_producer", expected_cadence_s=30)
    assert gauge.published_count() == 0
    gauge.mark_published()
    assert gauge.published_count() == 1
    gauge.mark_published()
    assert gauge.published_count() == 2


def test_gauge_name_cannot_start_with_digit():
    with pytest.raises(ValueError):
        FreshnessGauge("1_bad_name", expected_cadence_s=30)
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/test_freshness_gauge.py -v
```

Expected: module-not-found error for `shared.freshness_gauge`.

- [ ] **Step 3: Create `shared/freshness_gauge.py`**

```python
"""Per-producer freshness contracts for always-on loops.

Every always-on producer with a `try/except + log.warning + return` shape MUST
own a FreshnessGauge instance. The gauge publishes:

- `{name}_published_total` counter — incremented on every successful tick
- `{name}_age_seconds` gauge — seconds since the last successful tick
- `{name}_failed_total` counter — incremented on each mark_failed() call

The health monitor reads the age gauge and flags stale producers via
`FreshnessGauge.is_stale(tolerance_mult=10)`.

Fixes BETA-FINDING-2026-04-13-C: `graceful catch + log warning` masks
production-critical loops. Every instance of that pattern must come with a
freshness contract.
"""
from __future__ import annotations

import re
import time
from typing import Final

from prometheus_client import REGISTRY, CollectorRegistry, Counter, Gauge

_VALID_NAME: Final = re.compile(r"^[a-z_][a-z0-9_]*$")


class FreshnessGauge:
    """Bounded age + publish-count contract for an always-on producer.

    Construct once per producer. Call ``mark_published()`` on every successful
    tick and ``mark_failed(exc)`` inside every catch-all ``except``. Health
    monitor reads ``is_stale()`` on its periodic check.
    """

    def __init__(
        self,
        name: str,
        expected_cadence_s: float,
        *,
        registry: CollectorRegistry = REGISTRY,
    ) -> None:
        if not _VALID_NAME.fullmatch(name):
            raise ValueError(
                f"FreshnessGauge name {name!r} must match [a-z_][a-z0-9_]*"
            )
        if expected_cadence_s <= 0:
            raise ValueError(
                f"expected_cadence_s must be positive, got {expected_cadence_s}"
            )
        self._name = name
        self._expected_cadence_s = expected_cadence_s
        self._last_published_at: float | None = None
        self._published_counter = Counter(
            f"{name}_published_total",
            f"Successful tick count for {name}",
            registry=registry,
        )
        self._failed_counter = Counter(
            f"{name}_failed_total",
            f"Failed tick count for {name}",
            registry=registry,
        )
        self._age_gauge = Gauge(
            f"{name}_age_seconds",
            f"Seconds since the last successful tick of {name}",
            registry=registry,
        )
        self._age_gauge.set_function(self.age_seconds)

    def mark_published(self) -> None:
        """Record a successful tick."""
        self._last_published_at = time.monotonic()
        self._published_counter.inc()

    def mark_failed(self, exc: BaseException | None = None) -> None:
        """Record a failed tick. Does not reset the age."""
        self._failed_counter.inc()

    def age_seconds(self) -> float:
        """Seconds since the last successful tick, or +inf if never published."""
        if self._last_published_at is None:
            return float("inf")
        return time.monotonic() - self._last_published_at

    def is_stale(self, tolerance_mult: float = 10.0) -> bool:
        """Return True if age > expected_cadence_s × tolerance_mult."""
        return self.age_seconds() > self._expected_cadence_s * tolerance_mult

    def published_count(self) -> int:
        """Number of mark_published() calls — test helper."""
        return int(self._published_counter._value.get())  # type: ignore[attr-defined]
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/test_freshness_gauge.py -v
```

Expected: 7 passing.

- [ ] **Step 5: Wire into `imagination_loop.py`**

Modify `agents/imagination_loop.py` around line 93 (constructor) and line 198–206 (tick try/except):

```python
# At top of __init__:
from shared.freshness_gauge import FreshnessGauge

# In __init__, after existing attributes:
self._freshness = FreshnessGauge(
    "hapax_imagination_loop_fragments",
    expected_cadence_s=30.0,  # nominal cadence; actual varies via CadenceController
)

# In tick(), after self._process_fragment(fragment) on success:
self._freshness.mark_published()

# In the except Exception block:
self._freshness.mark_failed()
```

- [ ] **Step 6: Add health monitor helper**

Add to `agents/health_monitor/checks.py` (or wherever the check helpers live — grep for `check_pi_fleet` to find the module):

```python
def check_imagination_freshness() -> HealthCheckResult:
    """Flag stale imagination producer via the freshness gauge."""
    from agents.imagination_loop import get_global_loop_instance  # if one exists
    loop = get_global_loop_instance()
    if loop is None:
        return HealthCheckResult(
            component="imagination_loop",
            status="unknown",
            message="no loop instance registered",
        )
    if loop._freshness.is_stale():
        age = loop._freshness.age_seconds()
        return HealthCheckResult(
            component="imagination_loop",
            status="critical",
            message=f"imagination_loop silent for {age:.1f}s (10x cadence)",
        )
    return HealthCheckResult(component="imagination_loop", status="healthy")
```

If no global instance registry exists, fall back to reading `/dev/shm/hapax-imagination/current.json` mtime (older than 300s → stale) — the same signal from the filesystem.

- [ ] **Step 7: Verify and commit**

```bash
uv run pytest tests/test_freshness_gauge.py tests/test_imagination_loop.py -q
uv run ruff check shared/freshness_gauge.py agents/imagination_loop.py
git add shared/freshness_gauge.py tests/test_freshness_gauge.py agents/imagination_loop.py agents/health_monitor/checks.py
git commit -m "feat(observability): FreshnessGauge helper + imagination_loop seed (BETA-FINDING-C)"
```

### Task 8.2 — CairoSourceRunner freshness + two more always-on producers

**Files:**
- Modify: `agents/studio_compositor/cairo_source.py`
- Modify: two more always-on producers (scouted during implementation — grep for `except Exception.*:\s*log.*warning` in agents/ and pick the top two by criticality)

**Steps:**

- [ ] **Step 1:** `rg -n "except Exception.*:\s*\n\s+log" agents/` and inventory the matches.
- [ ] **Step 2:** Pick the two highest-criticality always-on producers (candidates: `agents/imagination_loop.py` already done; `agents/hapax_daimonion/run_inner.py` impingement loops; `agents/visual_layer_aggregator/run.py` tick loop; `agents/effect_graph/compiler.py` graph rebuild; `agents/content_scheduler.py` if present).
- [ ] **Step 3:** For each picked producer, wire a `FreshnessGauge` with an appropriate name and cadence.
- [ ] **Step 4:** Add a health check helper per producer.
- [ ] **Step 5:** Add `CairoSourceRunner` freshness for each registered cairo source — gauge name `compositor_source_{source_id}` at the source's native render cadence.
- [ ] **Step 6:** Tests for each wiring.
- [ ] **Step 7:** Commit.

### Task 8.3 — Pool metrics IPC exposure

**Files:**
- Modify: `hapax-logos/crates/hapax-visual/src/output.rs` — add `write_pool_metrics` path
- Modify: `hapax-logos/crates/hapax-visual/src-imagination/src/main.rs` (or headless path after Phase 4) — call `write_pool_metrics` once per frame (or every N frames)
- Modify: `agents/reverie_prediction_monitor.py` — add pool metrics reader + four Prometheus gauges
- New: `tests/test_reverie_pool_metrics.py`

**Steps:**

- [ ] **Step 1:** Write failing test for the Python-side reader (mock the JSON file, assert gauges populate).
- [ ] **Step 2:** Implement `write_pool_metrics` in Rust. Use `serde_json::to_writer` + `std::fs::rename` for atomic write. Path: `/dev/shm/hapax-imagination/pool_metrics.json`.
- [ ] **Step 3:** Hook `write_pool_metrics` into the render tick loop (every 60 frames = 1Hz).
- [ ] **Step 4:** Implement Python reader in `reverie_prediction_monitor.py`. Add four gauges: `reverie_pool_bucket_count`, `reverie_pool_total_textures`, `reverie_pool_acquires_total`, `reverie_pool_reuse_ratio`.
- [ ] **Step 5:** Add an alert threshold: log a warning if `reuse_ratio < 0.5` for > 60s.
- [ ] **Step 6:** Tests pass.
- [ ] **Step 7:** Commit.

### Task 8.4 — F7 decision: document + `#[allow(dead_code)]`

**Files:**
- Modify: `hapax-logos/crates/hapax-visual/src/dynamic_pipeline.rs` — lines 812–828, add a doc comment block explaining the override surface is reserved for future `visual_chain` extensions and an `#[allow(dead_code)]` annotation if Clippy complains

**Steps:**

- [ ] **Step 1:** Read the current F7 arms. Confirm they're in a `match` on `key.strip_prefix("signal.")` and read 9 dimension keys.
- [ ] **Step 2:** Add a doc comment above the match arm: "Reserved for future per-frame dimension override by `visual_chain`. Writer is absent today — the dimensions reach the GPU via `UniformBuffer::from_state` from `StateReader.imagination.dimensions` (Path 1 of the bridge). This override surface allows Path 2 (per-node params) to bias the shared dimensions in a future extension without a Rust change. Do not delete without a plan."
- [ ] **Step 3:** If `cargo clippy` complains about the match arms being "dead", add `#[allow(dead_code)]`.
- [ ] **Step 4:** `cargo test`.
- [ ] **Step 5:** Commit.

### Task 8.5 — F10 verification: delete if orphaned

**Files:**
- Modify or delete: `shared/imagination_state.py` — `ImaginationState.content_references` field
- Grep all callers

**Steps:**

- [ ] **Step 1:** `rg -n "content_references" agents/ shared/ tests/` — inventory all references.
- [ ] **Step 2:** If the field has no non-construction, non-test references, delete it from the Pydantic model + construction sites + tests.
- [ ] **Step 3:** If it has real usage, document the user inline and close F10.
- [ ] **Step 4:** `uv run pytest` + `uv run pyright` — must pass.
- [ ] **Step 5:** Commit.

### Task 8.6 — Amendment 4 reverberation cadence observational script

**Files:**
- New: `scripts/verify_reverberation_cadence.py`

**Steps:**

- [ ] **Step 1:** Write a small script that tails `journalctl --user -u hapax-imagination-loop.service --since "5 min ago"`, greps for `Reverberation %.2f`, counts acceleration events (`force_accelerated(True)` log lines), exits 0 if ≥ 1 event found, 1 otherwise.
- [ ] **Step 2:** Document in the script docstring that this runs as part of Phase 9's AC sweep.
- [ ] **Step 3:** `uv run python scripts/verify_reverberation_cadence.py` — should exit 0 under normal operation if imagination has been running.
- [ ] **Step 4:** Commit.

**Phase 8 PR body template:**

```
Phase 8 of the reverie source registry completion epic. Adjacent
observability hardening.

- shared/freshness_gauge.py: reusable per-producer freshness contract.
  Seeded with hapax_imagination_loop_fragments + two more always-on
  producers (picked by grep at implementation time). Fixes
  BETA-FINDING-2026-04-13-C (imagination-loop silent mask).
- CairoSourceRunner: freshness gauge per registered cairo source.
- Pool metrics IPC: Rust writes /dev/shm/hapax-imagination/pool_metrics.json
  every 60 frames; reverie_prediction_monitor reads and exposes four
  Prometheus gauges (bucket_count, total_textures, acquires, reuse_ratio).
- F7 decision: dormant signal.{9dim} override arms in dynamic_pipeline.rs
  are documented as a reserved override surface, not deleted.
- F10 decision: ImaginationState.content_references [deleted | documented]
  based on repo grep of references.
- Amendment 4: observational verify_reverberation_cadence.py script
  runs as part of Phase 9's AC sweep.

Tests: N new.

Plan task numbers: 8.1–8.6 (inline). PR 8/9 of the epic.
```

**Exit criterion:** Freshness gauge integrated, pool metrics visible in Prometheus scrape, F7/F10 decisions landed, Amendment 4 script runs green.

## Phase 9 — Final acceptance sweep (parent J28–J29)

**Branch:** `feat/source-registry-epic-final-sweep`

**Tasks:** parent plan tasks 28 and 29 plus epic-level post-audit.

**Task 28 (parent plan lines ~3932–4016) — acceptance criteria validation sweep.**

Walk the 11 parent ACs + the 4 new Phase 8 ACs. Run each verification command. Capture output in `docs/superpowers/audits/2026-04-13-reverie-source-registry-completion-sweep.md`. Parent AC table:

1. Compositor boots with `default.json`; reverie PiP shows live frames in upper-right.
2. Existing visible behavior preserved (UL Vitruvian, LL album).
3. `hapax-imagination.service` runs headless; no winit window visible.
4. `compositor.surface.set_geometry` moves a PiP within ≤1 frame.
5. File-watch reload within ≤2s for valid edits; invalid edit ignored with warning.
6. Every source has a persistent `appsrc` pad; reverie RGBA reaches glvideomixer.
7. Preset load with unknown source reference fails loudly.
8. Deleting `default.json` → fallback layout + ntfy.
9. All new tests pass; existing `tests/studio_compositor/` suite unchanged.
10. `compositor_source_frame_age_seconds` populates for every registered source.
11. Natural-size migration preserves visual output (golden-image regression).

Phase 8 ACs:

12. `imagination_loop_fragments_published_total` counter increments per tick.
13. `reverie_pool_*` gauges populate with live values.
14. F10 `content_references` decision landed in code.
15. Amendment 4 reverberation acceleration observed once in live logs.

**Task 29 (parent plan lines ~4017–4049) — final push.**

- [ ] Delete `@deprecated` legacy facade methods (`TokenPole.draw()` etc.) — phase-3 debt.
- [ ] Delete legacy facade construction in `fx_chain.py` (`compositor._token_pole = TokenPole()` etc.).
- [ ] Update `shared/compositor_model.py` docstrings to reflect the source registry being authoritative.
- [ ] Run full test suite, ruff, pyright, and `cargo test --manifest-path hapax-logos/crates/hapax-visual/Cargo.toml`.
- [ ] Commit retirement handoff: `docs/superpowers/handoff/2026-04-13-alpha-reverie-source-registry-epic-retirement.md`.
- [ ] Update epic design + plan doc status to "COMPLETE".
- [ ] Close the epic.

**PR body template:**

```
Phase 9 of the reverie source registry completion epic. Final sweep.

- Acceptance criteria sweep: all 11 parent ACs + 4 Phase 8 ACs pass.
  Full audit artifact at docs/superpowers/audits/.
- Legacy facade removal: TokenPole/AlbumOverlay/SierpinskiRenderer
  legacy draw() methods deleted; fx_chain.py legacy construction sites
  removed. Phase 3 debt closed.
- Retirement handoff: docs/superpowers/handoff/.
- Epic spec + plan marked COMPLETE.

Plan task numbers: 28, 29. PR 9/9 of the epic.

Closes source-registry epic originated in PR #709.
```

**Exit criterion:** All 15 ACs pass. Epic marked complete. Retirement handoff written.

## Definition of done — epic-level

- [ ] All 9 phase PRs merged green.
- [ ] All 15 acceptance criteria pass.
- [ ] `rebuild-services.timer` has fired at least once post-Phase-9 and the compositor is running cleanly on the merged state.
- [ ] Live observational verification: reverie visibly appears in the upper-right quadrant of the compositor frame.
- [ ] Live observational verification: `window.__logos.execute("compositor.surface.set_geometry", ...)` moves a PiP.
- [ ] `journalctl --user -u studio-compositor.service --since "30 min ago"` shows no ERRORs.
- [ ] `BETA-FINDING-2026-04-13-C` marked closed in `~/.cache/hapax/relay/beta.yaml`.
- [ ] `F7`, `F10`, Amendment 4 decisions documented.
- [ ] Retirement handoff written.
- [ ] Relay updated: `alpha.yaml` status `RETIRED — epic complete` (or continuing if more work exists).

## Rollback

Per-phase rollback: `git revert <merge SHA>`. Critical rollback notes:

- Phase 3 revert restores the legacy facade render path since legacy facades are still present.
- Phase 4 revert restores the winit window; set `HAPAX_IMAGINATION_HEADLESS=0` if the revert can't land fast enough.
- Phase 6 revert restores pre-appsrc pipeline topology; Cairo PiPs continue unaffected (they're on cairooverlay).
- Phase 9 deletion of legacy facades is the only non-rollback-safe change in the epic. If Phase 9 breaks production, revert Phase 9 and re-land after fixing.

## Process notes

- One branch at a time. No stacking. Each phase merges before the next branch is created.
- Use the `ci-watch` skill or `gh pr checks --watch` to monitor CI without polling.
- Every phase PR must bundle at least one non-`docs/` and non-root-`*.md` change for CI to fire (branch-protection ignores docs-only). Most phases naturally bundle test files + code changes so this is only a concern for Phase 8 Task 8.4 (F7 documentation), which adds a doc comment in Rust code — Rust code counts as non-docs.
- `rebuild-services.timer` auto-refreshes alpha's worktree to the merged main within 5 min of each merge, so compositor live-behavior changes are visible to the operator within 5 min of each PR's merge.

## Epic state tracker

| Phase | PR # | Status | Merged SHA |
|---|---|---|---|
| 1 | 735 | — | — |
| 2 | — | — | — |
| 3 | — | — | — |
| 4 | — | — | — |
| 5 | — | — | — |
| 6 | — | — | — |
| 7 | — | — | — |
| 8 | — | — | — |
| 9 | — | — | — |

**Update this table after each phase merges.**
