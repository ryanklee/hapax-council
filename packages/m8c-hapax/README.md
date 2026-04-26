# m8c-hapax

Carry-fork of [laamaa/m8c](https://github.com/laamaa/m8c) (the Linux client for the Dirtywave M8 tracker) that adds a **V4L2 output-loopback bridge**. Every frame the M8 LCD draws (320×240 ARGB) is also published as a V4L2 output device frame, ready for the studio compositor's pyudev camera FSM to consume as another camera Source.

cc-task: `re-splay-homage-ward-m8` (Re-Splay Homage Ward — Dirtywave M8 hotplug → display + audio into broadcast).

## Why a fork

Upstream m8c v2.2.3 has no V4L2 path. The patch surface is small (one new source file + ~10-line render.c hook + 3-line Makefile target). Per operator decision (2026-04-26), this is a **carry-fork forever**, not staged for upstream PR — refusal-shaped-affordance stance, not seeking contributor relationships. Rebases against upstream tags should remain trivial.

The build coexists with stock `m8c` (or AUR `m8c`) at `/usr/local/bin/m8c-hapax`. Operators who want both can have both.

## Files

- `PKGBUILD` — Arch package spec; downloads upstream tarball, drops in the carry-fork source files, applies the patch, builds with `make v4l2`, installs as `m8c-hapax`
- `v4l2_sink.c` — opaque V4L2 output sink (open / publish frame / close)
- `v4l2_sink.h` — public interface
- `0001-add-v4l2-sink.patch` — three integration points in upstream m8c (Makefile target + render.c hook + #include)

## Behavioural contract

When `USE_V4L2_SINK` is defined at build time:

1. `v4l2_sink_init()` runs after `main_texture` exists in `renderer_initialize()`. It opens `/dev/video15` (override via `M8C_V4L2_SINK_PATH` env) and sets the format to 320×240 ARGB8888.
2. After every `SDL_RenderPresent`, `v4l2_sink_publish(rend, main_texture)` reads the M8 native-resolution texture into a stack buffer and writes it to the loopback. NEAREST sampling is implicit — pixels are read from `main_texture`, which is allocated at exactly 320×240, so no scaling artefacts.
3. `v4l2_sink_shutdown()` closes the device on `renderer_close`.

When `USE_V4L2_SINK` is not defined, all three calls are no-ops. The patch is harmless on stock builds.

## Operator install

```bash
cd packages/m8c-hapax
makepkg -si
```

Then load the v4l2-loopback module persistently (covered by the companion systemd / modprobe.d pieces in this cc-task's later phases):

```bash
sudo modprobe v4l2loopback video_nr=15 card_label="Hapax M8 LCD" exclusive_caps=1
```

Run with:

```bash
m8c-hapax  # publishes to /dev/video15 by default
M8C_V4L2_SINK_PATH=/dev/video16 m8c-hapax  # override
```

## Verification

After running `m8c-hapax` with the M8 plugged in:

```bash
# m8c-hapax should be writing frames to /dev/video15
v4l2-ctl --device /dev/video15 --info
ffplay -f v4l2 -framerate 30 /dev/video15  # see the M8's LCD content
```

## Constitutional binders

- `feedback_full_automation_or_no_engagement`: this package is half of the hotplug-only flow; the systemd skeleton (later phase) wires the lifecycle.
- `feedback_l12_equals_livestream_invariant` (vacuous): the V4L2 path is video-only; M8 audio is a separate wireplumber path that bypasses the L-12 entirely.
- `anti-anthropomorphization`: the M8 LCD is an instrument's pixel grid, not personified.
