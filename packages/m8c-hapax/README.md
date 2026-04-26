# m8c-hapax

Carry-fork of [laamaa/m8c](https://github.com/laamaa/m8c) (the Linux client for the Dirtywave M8 tracker) that adds a **/dev/shm RGBA bridge**. Every frame the M8 LCD draws (320×240 BGRA) is also published to `/dev/shm/hapax-sources/m8-display.rgba` with a sidecar `m8-display.rgba.json` carrying frame-id and dimensions — matching the studio compositor's `external_rgba` source pattern (same shape as Reverie).

cc-task: `re-splay-homage-ward-m8` (Re-Splay Homage Ward — Dirtywave M8 hotplug → display + audio into broadcast).

## Why a fork

Upstream m8c v2.2.3 has no off-screen / SHM publishing path. The patch surface is small (one new source file + ~10-line render.c hook + 3-line Makefile target). Per operator decision (2026-04-26), this is a **carry-fork forever**, not staged for upstream PR — refusal-shaped-affordance stance, not seeking contributor relationships. Rebases against upstream tags should remain trivial.

The build coexists with stock `m8c` (or AUR `m8c`) at `/usr/local/bin/m8c-hapax`. Operators who want both can have both.

## Why SHM, not v4l2-loopback

Operator decision (2026-04-26 ~17:55Z): the SHM path reuses the existing studio compositor `external_rgba` source pattern (exactly how Reverie's wgpu surface lands in the composite), avoiding any modification to the production camera_pipeline / GStreamer 6-camera path. Cleaner dispatch, zero production risk.

## Files

- `PKGBUILD` — Arch package spec; downloads upstream tarball, drops in the carry-fork source files, applies the patch, builds with `make shm`, installs as `m8c-hapax`
- `shm_sink.c` — opaque /dev/shm publisher (open / publish frame / close)
- `shm_sink.h` — public interface
- `0001-add-shm-sink.patch` — three integration points in upstream m8c (Makefile target + render.c hook + `#include`)

## Behavioural contract

When `USE_SHM_SINK` is defined at build time:

1. `shm_sink_init()` runs after `main_texture` exists in `renderer_initialize()`. It ensures `/dev/shm/hapax-sources/` exists, opens `m8-display.rgba` (override via `M8C_SHM_SINK_PATH` env), and pre-sizes the file to 307,200 bytes (320×240×4).
2. After every `SDL_RenderPresent`, `shm_sink_publish(rend, main_texture)` reads the M8 native-resolution texture into a stack buffer, writes it to the SHM file, increments `frame_id`, and atomically (tmp+rename) updates the sidecar JSON. Pixels are read from `main_texture`, which is allocated at exactly 320×240, so no scaling artefacts.
3. `shm_sink_shutdown()` closes the file on `renderer_close`.

When `USE_SHM_SINK` is not defined, all three calls are no-ops. The patch is harmless on stock builds.

### SHM file format

| File | Content |
|---|---|
| `/dev/shm/hapax-sources/m8-display.rgba` | 320×240 BGRA bytes, raw, stride 1280, no header |
| `/dev/shm/hapax-sources/m8-display.rgba.json` | `{"frame_id":N,"w":320,"h":240,"stride":1280}` |

Compositor side: `agents/studio_compositor/shm_rgba_reader.py::ShmRgbaReader` polls the sidecar `frame_id` and re-imports the RGBA when it changes.

## Operator install

```bash
cd packages/m8c-hapax
makepkg -si
```

Run with:

```bash
m8c-hapax  # publishes to /dev/shm/hapax-sources/m8-display.rgba by default
M8C_SHM_SINK_PATH=/dev/shm/test.rgba m8c-hapax  # override
```

## Verification

After running `m8c-hapax` with the M8 plugged in:

```bash
ls -la /dev/shm/hapax-sources/m8-display.rgba    # 307200 bytes
cat /dev/shm/hapax-sources/m8-display.rgba.json  # {"frame_id":N,...}
# frame_id should increment as the M8 draws frames
```

## Constitutional binders

- `feedback_full_automation_or_no_engagement`: this package is half of the hotplug-only flow; the systemd skeleton (Phase 2) wires the lifecycle.
- `feedback_l12_equals_livestream_invariant` (vacuous): the SHM path is video-only; M8 audio is a separate wireplumber path that bypasses the L-12 entirely.
- `anti-anthropomorphization`: the M8 LCD is an instrument's pixel grid, not personified.
