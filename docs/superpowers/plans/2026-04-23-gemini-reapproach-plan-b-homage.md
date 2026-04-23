# Plan B — HOMAGE Ward Layout Hardening

**Design:** `docs/superpowers/specs/2026-04-23-gemini-reapproach-epic-design.md` §Epic B

4 phases. Small PRs, high operator-visibility value. Ships inline this session.

## Phase B1 — Occlusion fix + captions cutover cleanup

**Branch:** `feat/homage-b1-occlusion-fix`

- [ ] Move `thinking-indicator-tr` from (1620, 20, 170, 44) → (1380, 20, 170, 44). No overlap with HARDM (1600-1856 x-range).
- [ ] Move `stance-indicator-tr` from (1800, 24, 100, 40) → (1800, 290, 100, 40). Below HARDM (which ends at y=276).
- [ ] Move `whos-here-tr` from (1460, 20, 150, 46) → (1200, 20, 150, 46). No overlap with thinking-indicator's new position.
- [ ] Remove `captions` source + `captions_strip` surface + `captions` assignment from `config/compositor-layouts/default.json` and `_FALLBACK_LAYOUT`. GEM replaced captions 2026-04-21 (comment at existing test line 101-104 already documents cutover, but the entries survive).
- [ ] Update `tests/studio_compositor/test_default_layout_loading.py` assertions to reflect new coords + captions retirement.
- [ ] Add `tests/studio_compositor/test_default_layout_no_occlusion.py` — regression pin computing pairwise axis-aligned rectangle intersection of all `pip-*` / homage / legibility surfaces, asserts zero overlap (excluding `pip-*` quadrant assignments to their intended single surface).
- [ ] Local verify: `uv run pytest tests/studio_compositor/test_default_layout_loading.py tests/studio_compositor/test_default_layout_no_occlusion.py -q`
- [ ] Post-merge live verify: rebuild cascade; inspect `journalctl --user -u studio-compositor.service --since=5min`; visual check no overlap on broadcast.

## Phase B2 — Scale parity regression test

**Branch:** `feat/homage-b2-scale-parity`
**Pins current values 0.75 / NATURAL_SIZE=300 / album 400×520 as baselines.**

- [ ] `tests/studio_compositor/test_scale_parity.py`:
  - Assert `agents/studio_compositor/layout.py` `_sierpinski_layout` scale matches `agents/studio_compositor/sierpinski_renderer.py` `render_content` scale (AST parse both, extract constant, compare).
  - Assert `agents/studio_compositor/token_pole.py::NATURAL_SIZE` == `default.json pip-ul`.w == .h.
  - Assert `agents/studio_compositor/album_overlay.py::SIZE` + `TEXT_BUFFER` compose to `default.json pip-ll` proportions.
- [ ] No code changes to any scale constants. Regression test only.
- [ ] Local verify: `uv run pytest tests/studio_compositor/test_scale_parity.py -q`

If operator later wants the 10% reduction Gemini attempted, they update all four constants atomically and the regression test catches any missed one.

## Phase B3 — CBIP audio-reactive without alpha-beat modulation

**Branch:** `feat/homage-b3-cbip-constant-alpha`
**Re-implements 28f68afc5's chromatic-aberration core cleanly.**

- [ ] Rewrite `agents/studio_compositor/album_overlay.py::_pip_fx_package`:
  - R/G/B chromatic aberration via `push_group` / `pop_group_to_source` (3 channel masks, translate-only) — audio-reactive translate magnitude via `beat_smooth`.
  - Final composite: `paint_with_alpha(ALPHA)` with **constant** ALPHA (0.85) — never time-varying.
  - Remove ALL alpha-beat modulation (no `set_source_rgba(..., 0.4 + beat_smooth * ...)`, no `paint_with_alpha(beat_smooth * ...)`).
  - Keep allowed modulations: translate offset, line_width, channel-shift magnitude, ordered-dither density, geometric mesh displacement.
  - Remove any duplicated scanline block (Gemini's copy-paste bug).
- [ ] Add CI lint (grep hook) fails on `paint_with_alpha\([^)]*beat|set_source_rgba\([^)]+,\s*[0-9.]+\s*\+\s*\w+` in `agents/studio_compositor/*.py`.
- [ ] Add `tests/studio_compositor/test_album_constant_alpha.py`:
  - Render 10 ticks with synthetic `beat_smooth ∈ {0.0, 0.3, 0.5, 0.7, 1.0}`.
  - Sample alpha channel of center 32×32 patch.
  - Assert alpha range < 2/255 across ticks (ignoring quantization).
  - Assert RGB channels DO vary across ticks (otherwise audio-reactive is dead).
- [ ] Local verify: `uv run pytest tests/studio_compositor/test_album_constant_alpha.py -q`

## Phase B4 — Task #186 closeout + token-pole goldens

**Branch:** `feat/homage-b4-token-pole-verify`
**Task #186 is already implementation-shipped (cfff06e41, 6afcde7bb, cf09f73e2). This closes the task.**

- [ ] `tests/studio_compositor/test_token_pole_path_continuity.py`:
  - Render token surface at `position=0.0, 0.5, 1.0`.
  - Sample pixel intensity along the NAVEL→CRANIUM line at 20 points.
  - Assert: the traveled segment brightness > untraveled brightness (continuous-backbone invariant).
- [ ] `tests/studio_compositor/test_token_pole_explosion_fires.py`:
  - Trigger `_total_tokens >= _threshold`.
  - Assert `len(self._particles) > 0` within 1 tick.
- [ ] Close task #186 in vault/cc-tasks.
- [ ] Local verify: `uv run pytest tests/studio_compositor/test_token_pole_path_continuity.py tests/studio_compositor/test_token_pole_explosion_fires.py -q`

## Deferred (separate scope)

- 10% reduction of reverie/sierpinski/CBIP — requires atomic change to 4 constants; Phase B2's regression test makes this safer; operator can ratify when satisfied.
- Vinyl-groove / chessboard-specific compositing (operator 07:45 "highly indicative of the vinyl album, its artwork, and the chessboard backdrop") — deeper research; spec phase before code.

## Rollback

Phase B1 is the biggest delta (layout geometry). Revert commit restores pre-Phase-B1 geometry immediately; `default.json` is data-only so zero service restart needed, just `hapax-rebuild-services` cycle.
