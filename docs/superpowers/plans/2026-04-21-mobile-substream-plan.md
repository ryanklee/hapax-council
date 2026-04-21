# Mobile Livestream Substream — Implementation Plan

**Filed:** 2026-04-21
**Spec:** `docs/superpowers/specs/2026-04-21-mobile-substream-design.md`
**CC-task:** `mobile-livestream-substream`
**Total estimate:** ~2 weeks, 5 PRs.

---

## Phase 1 — Schema scaffolding (~0.5 days, trivial PR)

Commit: `feat(compositor): mobile substream layout schema scaffold`

- [ ] Create `config/compositor-layouts/mobile.json` with schema from spec §5.
- [ ] Verify valid JSON: `python -c "import json; json.load(open('config/compositor-layouts/mobile.json'))"`

**PR 1** — `feat/mobile-substream-schema` — config only.

---

## Phase 2 — Mobile Cairo sources (~5 days)

Commit: `feat(compositor): mobile-scaled Cairo sources (18–24pt minimum)`

- [ ] Create `agents/studio_compositor/mobile_cairo_sources.py`:
  - `MobileActivityHeaderCairoSource(CairoSource)` — 20pt, 1080×192
  - `MobileStanceIndicatorCairoSource(CairoSource)` — 20pt, 1080×192
  - `MobileImpingementCascadeCairoSource(CairoSource)` — 18pt, 3 rows, 1080×192
  - `MobileTokenPoleCairoSource(CairoSource)` — horizontal bar, 18pt, 1080×96
  - `MobileCaptionsCairoSource(CairoSource)` — 22pt, wrap 1020px, 1080×240
  - `MobileCairoRunner` — daemon thread, renders all selected wards to `/dev/shm/hapax-compositor/mobile-overlay.rgba` at 10 fps, atomic tmp+rename
  - All `TextStyle` instances: `font_size_pt >= 18`

- [ ] Create `tests/studio_compositor/test_mobile_cairo_sources.py`:
  - Render smoke per source with mocked state
  - `test_all_sources_font_size_minimum_18pt` — AST/reflect TextStyle creations, assert `font_size_pt >= 18`
  - Missing-state: render produces valid surface, no exception
  - `test_mobile_cairo_runner_writes_rgba` — SHM file 1080×1920×4 bytes

- [ ] `uv run pytest tests/studio_compositor/test_mobile_cairo_sources.py -q`
- [ ] `uv run ruff check agents/studio_compositor/mobile_cairo_sources.py`

**PR 2** — `feat/mobile-cairo-sources` — module + tests, no compositor wiring yet.

---

## Phase 3 — Salience router + layout integration (~2 days)

Commit: `feat(compositor): mobile salience router + layout routing`

- [ ] Create `agents/studio_compositor/mobile_salience_router.py` per spec §8.
  - `__init__(layout_path: Path)`, `start()`, `stop()`, `_tick()` every 2.0 s
  - `_score_ward(ward_name, recruitment, narrative) -> float` = `0.6*recruitment + 0.3*narrative_relevance + 0.1*recency`
  - Stale >30s → score 0

- [ ] Create `tests/studio_compositor/test_mobile_salience_router.py`:
  - Selection by recruitment activity
  - Stale file (via `os.utime` to 60s ago) → score 0
  - Output schema has `selected_wards`, `viewer_count`, `ts`
  - Rotation when signals change

- [ ] Update `agents/studio_compositor/compositor.py`:
  - `_mobile_salience_router: MobileSalienceRouter | None = None`
  - `_mobile_cairo_runner: MobileCairoRunner | None = None`
  - `start()`: instantiate + start both (if broadcast mode includes mobile)
  - `stop()`: stop both

- [ ] `uv run pytest tests/studio_compositor/test_mobile_salience_router.py -q`
- [ ] `uv run ruff check agents/studio_compositor/mobile_salience_router.py`

- [ ] Create `tests/studio_compositor/test_mobile_layout_routing.py`:
  - Router reads real `mobile.json` without error
  - Selected wards respond to mock signal changes

**PR 3** — `feat/mobile-salience-router` — module + compositor wiring + tests.

---

## Phase 4 — Second NVENC session + RTMP (~3 days)

Commit: `feat(compositor): mobile RTMP bin (MobileRtmpOutputBin, 1080×1920 30fps)`

- [ ] Add `MobileRtmpOutputBin` class to `agents/studio_compositor/rtmp_output.py`:
  - Pipeline: `videocrop(dynamic) → cudaupload → cudaconvert(NV12) → cudascale(1080×1920) → capsfilter → queue → nvh264enc → h264parse → flvmux → rtmp2sink`
  - Internal `compositor` mixer blends mobile Cairo overlay (from appsrc reading `/dev/shm/hapax-compositor/mobile-overlay.rgba`) over scaled camera output
  - Encoder: `preset=4, rc-mode=2, bitrate=3500, tune=3, bframes=0, gop-size=60, cuda-device-id=0`
  - Constructor: `rtmp_location` from `HAPAX_MOBILE_RTMP_URL`, `rtmp_key` from `HAPAX_MOBILE_RTMP_KEY`; empty URL → detached/no-op
  - `crop_params_path: Path = Path("/dev/shm/hapax-compositor/mobile-roi.json")`; property-update thread updates `videocrop` via `GLib.idle_add` at 0.5 Hz
  - All element names `mobile_*` prefixed for bus isolation
  - `build_and_attach(pipeline) -> bool`, `detach_and_teardown(pipeline) -> None`, `rebuild_in_place(pipeline) -> bool`

- [ ] Extend `agents/studio_compositor/pipeline.py` `build_pipeline()`:
  ```python
  compositor._mobile_rtmp_bin = MobileRtmpOutputBin(
      gst=Gst,
      video_tee=output_tee,
      rtmp_location=os.environ.get("HAPAX_MOBILE_RTMP_URL", ""),
      rtmp_key=os.environ.get("HAPAX_MOBILE_RTMP_KEY", ""),
      bitrate_kbps=3500,
      gop_size=fps * 2,
  )
  ```

- [ ] Extend `agents/studio_compositor/metrics.py`:
  - `HAPAX_MOBILE_SUBSTREAM_FRAMES_TOTAL: Counter(labels=['status'])`
  - `HAPAX_MOBILE_SUBSTREAM_BITRATE_KBPS: Gauge`
  - `HAPAX_BROADCAST_MODE: Gauge`
  - `HAPAX_MOBILE_CAIRO_RENDER_DURATION_MS: Histogram(buckets=[1,5,10,20,50,100])`
  - Wire counters in `MobileRtmpOutputBin` buffer probe + `MobileCairoRunner` render loop

- [ ] Document env vars in `systemd/README.md`:
  - `HAPAX_MOBILE_RTMP_URL=rtmp://127.0.0.1:1935/mobile` (or YouTube-2 RTMP URL)
  - `HAPAX_MOBILE_RTMP_KEY=` (loaded from `pass show streaming/youtube-mobile-key` via `hapax-secrets`)

- [ ] Create `tests/studio_compositor/test_mobile_face_obscure_topology.py` — **must-have acceptance:**
  - `test_obscure_called_before_snapshot_write` — AST parse `cameras.py`, assert line of `obscure_frame_for_camera(...)` call < line of `cv2.imencode(...)` in same function
  - `test_mobile_bin_does_not_call_obscure` — string "obscure_frame_for_camera" not in `rtmp_output.py`
  - `test_obscure_fail_closed_frame_is_dark` — mock obscure raises, assert handler produces (40,40,40) fill

- [ ] `uv run pytest tests/studio_compositor/test_mobile_face_obscure_topology.py -q` — must pass before PR

- [ ] Manual test: set env vars, restart compositor, verify second RTMP stream at MediaMTX/YT, verify portrait orientation + face-obscure on both

**PR 4** — `feat/mobile-rtmp-bin` — MobileRtmpOutputBin + pipeline wiring + metrics + governance test.

---

## Phase 5 — Command registry integration (~1 day)

Commit: `feat(logos): studio.broadcast.mode command`

- [ ] Extend `hapax-logos/src/lib/commands/studio.ts`:
  - Add `broadcastMode: "desktop" | "mobile" | "dual"` to `StudioState`; default `"dual"`
  - Add `setBroadcastMode(mode)` to `StudioActions`
  - Register `studio.broadcast.mode` command + `studio.broadcastMode` query (spec §9)

- [ ] Extend `logos/api/routes/studio.py`:
  - `BroadcastModeRequest(BaseModel)`: `mode: Literal["desktop","mobile","dual"]`
  - `PATCH /api/studio/broadcast-mode` → writes `/dev/shm/hapax-compositor/broadcast-mode.json`
  - Return `JSONResponse({"ok": True, "mode": req.mode})`

- [ ] Extend `agents/studio_compositor/compositor.py`:
  - `_broadcast_mode: str = "dual"` field
  - Watchdog tick (1 Hz): read `broadcast-mode.json`, on change call `_apply_broadcast_mode(new_mode)`
  - `_apply_broadcast_mode(mode)`:
    - `desktop` → detach mobile bin
    - `mobile` → detach desktop bin, attach mobile bin
    - `dual` → attach both
    - Guard: `_livestream_active` before attach

- [ ] Verify Tauri IPC passthrough for `PATCH /api/studio/broadcast-mode` in `hapax-logos/src-tauri/src/commands/`; add if missing

**PR 5** — `feat/mobile-broadcast-mode-command` — command + API + compositor mode-switch.

---

## Phase 6 — Companion web page (separate spec, deferred)

Captured as future item. Pre-work in Phase 5 (no scope add):
- [ ] Create `hapax-logos/src/components/studio/MobileCompanionPage.tsx` as empty stub with pointer to Phase 2 spec.

---

## Acceptance criteria (Phase 1 complete)

- [ ] `test_mobile_face_obscure_topology.py` — all green
- [ ] `test_mobile_cairo_sources.py` — all green (incl. `test_all_sources_font_size_minimum_18pt`)
- [ ] `test_mobile_salience_router.py` — all green
- [ ] `test_mobile_layout_routing.py` — all green
- [ ] `hapax_broadcast_mode` gauge scrape-visible at `127.0.0.1:9482`
- [ ] Second RTMP stream visible at configured URL during test stream
- [ ] Operator confirms mobile legibility on physical phone
- [ ] CI green (gitleaks, pyright, ruff)

---

## LOC estimate

| Phase | New | Modified |
|-------|-----|----------|
| 1 (schema) | ~40 JSON | 0 |
| 2 (Cairo sources) | ~600 | 0 |
| 3 (salience router) | ~250 | ~60 |
| 4 (RTMP bin) | ~350 | ~80 |
| 5 (commands) | ~140 (TS+Py) | ~50 |
| Tests | ~500 | 0 |
| **Total** | **~1880** | **~190** |
