# Mobile Livestream Substream — Design

**Filed:** 2026-04-21
**Status:** Formal design. Phase 1 (substream) in scope. Phase 2 (companion web page) named but out of scope.
**CC-task:** `mobile-livestream-substream`
**Depends on:** Camera 24/7 resilience epic shipped (native RTMP, output-tee fan-out, RtmpOutputBin detachable bin pattern).

---

## 1. Problem

The studio compositor produces a single 1920×1080 16:9 frame at 30 fps, encoded to H.264 and delivered via MediaMTX to YouTube. Research (2026-04-21) quantified that **14 of 21 wards render text at 10–11pt effective size at 720p**, which resolves to approximately 7.5–8.3 physical pixels on a 5–7" phone screen (Apple HIG minimum: 17pt; Material Design minimum: 16sp; WCAG 1.4.4: 200% scale must be supported). The current stream is hostile to mobile viewers.

YouTube Live does not multiplex aspect ratios from a single RTMP key. Delivering a 9:16 portrait stream requires either a second encoder session feeding a second channel or a second service (TikTok, Twitch). This spec addresses the second encoder session approach.

The affected wards (`agents/studio_compositor/legibility_sources.py` lines 596–630 and `agents/studio_compositor/hothouse_sources.py` lines 329, 485, 698, 768, 960) include: ActivityHeaderCairoSource, StanceIndicatorCairoSource, GroundingProvenanceTickerCairoSource, ImpingementCascadeCairoSource, RecruitmentCandidatePanelCairoSource, ThinkingIndicatorCairoSource, PressureGaugeCairoSource, ActivityVarietyLogCairoSource, WhosHereCairoSource, captions, token pole.

---

## 2. Scope

**Phase 1 (this spec):** Second NVENC session at 1080×1920 9:16 portrait, 30 fps, with mobile-scaled Cairo overlays and dynamic ROI selection. Delivered as a parallel RTMP egress from the same compositor process.

**Phase 2 (out of scope here):** Responsive React companion web page at `localhost:8051/studio/mobile`, SSE-driven from logos-api, embedded video player pointing at the mobile RTMP stream, 20pt+ text, single-column layout. Discovery via QR code in YouTube description. §13 reserves the hook.

---

## 3. Non-goals

- Replacing or modifying the existing 1920×1080 desktop stream.
- ML upscaling or super-resolution of any kind.
- Changing face-obscure policy, timeout, or fail-closed behavior.
- Real-time ML object detection in the mobile ROI path.
- Audio routing changes — mobile stream shares the same AAC audio as the desktop stream.
- Support for more than two simultaneous RTMP egresses in this spec revision.

---

## 4. Architecture

### 4.1 Pipeline topology

Existing output chain after FX pass:

```
cudacompositor → cudadownload → videoconvert(BGRA) → bgra-caps →
pre-fx-tee → [fx-chain] → output-tee ─┬─ queue-v4l2 → v4l2sink(/dev/video42)
                                        ├─ [hls-branch] → hlssink2
                                        ├─ [smooth-delay-branch]
                                        ├─ [fx-snapshot-branch]
                                        └─ RtmpOutputBin (desktop, 9000 kbps)
```

Mobile substream adds a new detachable bin attached to `output-tee` via `request_pad(src_%u)`:

```
output-tee ──────────────────────────────────────────────────────────────┐
           └─ MobileRtmpOutputBin:                                        │
                queue(mobile) → videocrop(dynamic) → cudaupload →         │
                cudaconvert(NV12) → cudascale(1080×1920) →                │
                capsfilter(CUDAMemory,NV12) → queue(enc-feed) →           │
                nvh264enc(mobile) → h264parse →                           │
                flvmux ← aacparse ← voaacenc ← audioresample ← pipewiresrc│
                flvmux → rtmp2sink(HAPAX_MOBILE_RTMP_URL/HAPAX_MOBILE_RTMP_KEY)
```

`videocrop` operates CPU-side before `cudaupload` (the output-tee carries BGRA CPU frames via the existing `bgra-caps` filter). A property-update thread in `MobileRtmpOutputBin` reads `/dev/shm/hapax-compositor/mobile-roi.json` at 0.5 Hz and updates `videocrop` via `GLib.idle_add`.

### 4.2 Mobile overlay tier

A `MobileCairoRunner` daemon renders all 5 mobile zones into a single 1080×1920 BGRA surface at 10 fps and pushes it via an `appsrc` element into an internal `compositor` mixer inside `MobileRtmpOutputBin` (alpha-blended over the scaled camera output). Keeps the mobile bin self-contained; avoids adding a second cairooverlay to the main pipeline.

### 4.3 Portrait frame composition

| Band | Height | Content |
|------|--------|---------|
| Hero cam | 0–1152 px (60%) | Scaled hero camera crop |
| Ward zone | 1152–1728 px (30%) | Up to 3 highest-salience mobile wards, stacked |
| Metadata footer | 1728–1920 px (10%) | Stance, activity, viewer count |

Hero cam crop: center 608 columns of the 1920×1080 source (columns 656–1264, the desk camera tile), scaled to 1080×1152. Ward zone: up to 3 wards from the salience router's selection, each 1080×192 px, 16 px padding. Mobile font minimum 18pt.

---

## 5. Mobile layout schema

`config/compositor-layouts/mobile.json`:

```json
{
  "version": 1,
  "target_width": 1080,
  "target_height": 1920,
  "hero_cam": {
    "source_crop": { "x": 656, "y": 0, "width": 608, "height": 1080 },
    "dest": { "x": 0, "y": 0, "width": 1080, "height": 1152 }
  },
  "ward_zone": {
    "y_top": 1152,
    "y_bottom": 1728,
    "max_wards": 3,
    "ward_height": 192,
    "padding_px": 16
  },
  "metadata_footer": {
    "y_top": 1728,
    "y_bottom": 1920,
    "font_size_pt": 20
  },
  "salience_sources": [
    "/dev/shm/hapax-compositor/recent-recruitment.json",
    "/dev/shm/hapax-director/narrative-state.json",
    "/dev/shm/hapax-compositor/youtube-viewer-count.txt"
  ],
  "ward_candidates": [
    "activity_header",
    "stance_indicator",
    "impingement_cascade",
    "token_pole",
    "captions"
  ]
}
```

---

## 6. Governance — face-obscure

Face-obscure fires in `agents/studio_compositor/cameras.py` at raw frame capture (line 101), before the obscured frame is JPEG-encoded and placed in `SNAPSHOT_DIR`. Every downstream consumer — v4l2sink, HLS branch, desktop RTMP bin, and the new mobile RTMP bin — reads from the compositor pipeline, which is seeded exclusively from these pre-obscured JPEG frames via per-camera `appsrc` elements.

**The mobile egress inherits face-obscuring by construction. No additional call site required.**

Acceptance test `tests/studio_compositor/test_mobile_face_obscure_topology.py`:
1. `obscure_frame_for_camera` called in `cameras.py` before `cv2.imencode` writes to `SNAPSHOT_DIR`.
2. `SNAPSHOT_DIR` JPEG files are the only video data source for all compositor appsrc elements.
3. `MobileRtmpOutputBin.build_and_attach` does NOT call `obscure_frame_for_camera`.

Fail-closed: if `obscure_frame_for_camera` raises, `cameras.py` substitutes a Gruvbox-dark frame (40, 40, 40) (lines 112–115). Both egresses receive the masking frame.

---

## 7. Mobile Cairo sources

`agents/studio_compositor/mobile_cairo_sources.py` — all subclass `CairoSource`. Zone prefix `mobile_`. `TextStyle.font_size_pt >= 18` enforced by test.

- **`MobileActivityHeaderCairoSource`** — `>>> [ACTIVITY | gloss]`, 20pt, single-line, 1080×192
- **`MobileStanceIndicatorCairoSource`** — `[+H <stance>]`, 20pt, pulse at stance Hz, 1080×192
- **`MobileImpingementCascadeCairoSource`** — 3 most-recent rows, 18pt, slide-in, 1080×192
- **`MobileTokenPoleCairoSource`** — horizontal progress bar (1020×32), 18pt labels, 1080×96
- **`MobileCaptionsCairoSource`** — rolling captions, 22pt, word-wrap at 1020px, 1080×240

**`MobileCairoRunner`** — daemon thread, 10 fps. Reads `/dev/shm/hapax-compositor/mobile-salience.json`; renders each active source into its band within a 1080×1920 BGRA composite; writes to `/dev/shm/hapax-compositor/mobile-overlay.rgba` atomic tmp+rename. `MobileRtmpOutputBin` `appsrc` reads this SHM file.

---

## 8. Mobile salience router

`agents/studio_compositor/mobile_salience_router.py`:

```python
class MobileSalienceRouter:
    _INTERVAL_S: float = 2.0  # 0.5 Hz

    def __init__(self, layout_path: Path) -> None: ...
    def start(self) -> None: ...
    def stop(self) -> None: ...
    def _tick(self) -> None: ...
    def _score_ward(self, ward_name: str, recruitment: dict, narrative: dict) -> float:
        # 0.6 * recruitment_activity + 0.3 * narrative_relevance + 0.1 * recency
        ...
```

Reads `recent-recruitment.json`, `narrative-state.json`, `youtube-viewer-count.txt`. Writes `/dev/shm/hapax-compositor/mobile-salience.json`:

```json
{
  "selected_wards": ["impingement_cascade", "activity_header", "captions"],
  "viewer_count": 12,
  "ts": 1745001234.5
}
```

Staleness: any source >30s old → associated ward scores 0. Graceful degradation, no errors.

---

## 9. Command registry integration

`hapax-logos/src/lib/commands/studio.ts`:

```typescript
registry.register({
  path: "studio.broadcast.mode",
  args: { mode: { type: "string", required: true, enum: ["desktop", "mobile", "dual"] } },
  execute(args) {
    api.patch("/api/studio/broadcast-mode", { mode: args.mode }).catch(() => {});
    return { ok: true };
  },
});
registry.registerQuery("studio.broadcastMode", () => getState().broadcastMode);
```

`StudioState` gains `broadcastMode: "desktop" | "mobile" | "dual"`; default `"dual"`.

`logos/api/routes/studio.py`:

```python
class BroadcastModeRequest(BaseModel):
    mode: Literal["desktop", "mobile", "dual"]

@router.patch("/api/studio/broadcast-mode")
async def set_broadcast_mode(req: BroadcastModeRequest) -> JSONResponse: ...
```

Writes `/dev/shm/hapax-compositor/broadcast-mode.json`. `StudioCompositor` polls at 1 Hz, calls `mobile_bin.build_and_attach()` or `mobile_bin.detach_and_teardown()` on change.

---

## 10. Encoder cost

| Resource | Estimate |
|----------|---------|
| VRAM | +500–700 MB (NVENC session + cudascale buffers + overlay appsrc) |
| SM | +8–12% (NVENC p4 + cudascale) |
| CPU | +0.3 threads (MobileCairoRunner + MobileSalienceRouter + mux/write) |
| Uplink | +3500 kbps |

**Bitrate: 3500 kbps CBR.** YouTube Live 1080p mobile range: 1000–6000 kbps. 3500 is adequate for primarily text + single-camera content at 1080×1920 30fps.

Encoder settings for `MobileRtmpOutputBin`:
- `nvh264enc preset=4` (p4, balanced)
- `rc-mode=2` (CBR)
- `bitrate=3500`, `tune=3` (ull), `bframes=0`, `gop-size=60`, `cuda-device-id=0`

---

## 11. Observability

`agents/studio_compositor/metrics.py`:

- `HAPAX_MOBILE_SUBSTREAM_FRAMES_TOTAL` — Counter, labels `status=(encoded|dropped)`
- `HAPAX_MOBILE_SUBSTREAM_BITRATE_KBPS` — Gauge, updated every 5s
- `HAPAX_BROADCAST_MODE` — Gauge, 0=desktop/1=mobile/2=dual
- `HAPAX_MOBILE_CAIRO_RENDER_DURATION_MS` — Histogram, buckets [1,5,10,20,50,100]

Scrape endpoint `127.0.0.1:9482` (shared with existing compositor metrics).

---

## 12. Testing

### Unit tests

`tests/studio_compositor/test_mobile_cairo_sources.py`:
- Render smoke per source
- `test_all_sources_font_size_minimum_18pt` — inspect `TextStyle` instances, assert `font_size_pt >= 18`
- Missing state file → valid surface (no exception)

`tests/studio_compositor/test_mobile_salience_router.py`:
- Ward selection by recruitment activity
- Staleness → score 0
- Output schema
- Rotation on signal change

### Integration

`tests/studio_compositor/test_mobile_face_obscure_topology.py` — **must-have acceptance:**
- AST-check: `obscure_frame_for_camera` call precedes `cv2.imencode` in `cameras.py`
- String-scan: `MobileRtmpOutputBin` does NOT contain `obscure_frame_for_camera`
- Fail-closed test: mock obscure to raise, assert dark-frame substitution

`tests/studio_compositor/test_mobile_layout_routing.py`:
- Router reads layout JSON
- Selected wards change with salience signal changes

### Manual acceptance

Configure `HAPAX_MOBILE_RTMP_URL` + `HAPAX_MOBILE_RTMP_KEY` to a test YouTube Live event. `mode=dual`. Verify:
1. YouTube Live preview shows 9:16 portrait stream
2. Text readable on 5" phone
3. Face-obscure active on both streams
4. `hapax_broadcast_mode` gauge = 2
5. Operator confirms mobile legibility

---

## 13. Phase 2 hook

Future endpoints:
- `GET /api/studio/mobile-state` — SSE stream, narrative state updates
- `GET /api/studio/mobile-overlay-png` — periodic JPEG of the mobile overlay surface

`MobileCompanionPage.tsx` stub scaffolded in Phase 5 (command registry) so Tauri routing is in place before SSE work.

---

## Summary of new files

| File | Purpose |
|------|---------|
| `config/compositor-layouts/mobile.json` | ROI zones + ward candidates |
| `agents/studio_compositor/mobile_cairo_sources.py` | 5 sources + MobileCairoRunner |
| `agents/studio_compositor/mobile_salience_router.py` | 0.5 Hz ward selector |
| `agents/studio_compositor/rtmp_output.py` (ext) | `MobileRtmpOutputBin` class |
| `agents/studio_compositor/compositor.py` (ext) | Mobile bin/runner/router fields + wiring |
| `agents/studio_compositor/pipeline.py` (ext) | Attach MobileRtmpOutputBin to output-tee |
| `agents/studio_compositor/metrics.py` (ext) | 4 new metrics |
| `logos/api/routes/studio.py` (ext) | `PATCH /api/studio/broadcast-mode` |
| `hapax-logos/src/lib/commands/studio.ts` (ext) | `studio.broadcast.mode` command |
| `tests/studio_compositor/test_mobile_*.py` | 4 test files |
