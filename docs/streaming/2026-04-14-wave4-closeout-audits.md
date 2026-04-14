# Wave 4 close-out audits

**Date:** 2026-04-14
**Author:** alpha
**Scope:** W4.6 (MediaMTX HLS endpoint) + W4.7 (brio-synths unclaimed video interfaces). Both are explicit "no code change, document the finding" items from the livestream-performance-map execution plan.

## W4.6 — MediaMTX HLS endpoint wire

### Live state at audit
- `mediamtx.service` is enabled and active. Configuration: `/etc/mediamtx/mediamtx.yml` (default Arch package).
- HLS listener: `:8888`, low-latency variant (`hlsVariant: lowLatency`), 1 s segments, 200 ms parts.
- RTMP listener: `:1935`.
- Paths config: empty (`paths: # example`). MediaMTX accepts publishes under default-path rules.

### Flow
The compositor's RTMP output (`agents/studio_compositor/rtmp_output.py`) pushes to:

```
rtmp://127.0.0.1:1935/studio
```

MediaMTX accepts the publish on that path implicitly and exposes it as HLS at:

```
http://127.0.0.1:8888/studio/index.m3u8
```

This URL is the canonical in-app Logos preview source. Any HLS player (mpv, ffplay, browser `<video>` with hls.js, etc.) can consume it directly.

### Important: the compositor's RTMP path is consent-gated

The compositor builds the RTMP output bin **detached** at startup and only attaches it to the encoder tee when the affordance pipeline activates the `livestream` capability via `compositor.toggle_livestream(True, reason)`. The detach state is the safe default — it means a compositor restart never auto-publishes the stream. Audit hook: `agents/studio_compositor/pipeline.py:194` log line `"rtmp output bin constructed (detached until toggle_livestream)"`.

The full chain comes alive only when:
1. Affordance pipeline recruits the `livestream` capability
2. `compositor.toggle_livestream(True, ...)` is dispatched on the GLib main loop
3. The RTMP bin is attached to the tee
4. MediaMTX accepts the publish on `/studio`
5. HLS muxer creates segments at `/studio/index.m3u8`

When the chain is not engaged, MediaMTX serves `200 OK` on `http://127.0.0.1:8888/studio/` (HLS muxer alive on demand) but logs `"destroyed: no stream is available on path 'studio'"` and any GET against `/studio/index.m3u8` returns 404.

### Verification commands
```bash
# Listener present
ss -tlnp | grep -E ":1935|:8888"

# Path served (requires active publish)
curl -sf -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8888/studio/index.m3u8

# MediaMTX activity log
journalctl -u mediamtx --since "10 minutes ago" | grep "muxer studio"
```

### Conclusion
No code change required. The wiring is correct end-to-end. The HLS URL `http://127.0.0.1:8888/studio/index.m3u8` is stable and can be hardcoded into Logos UI components that need a low-latency studio preview, with the caveat that the player must handle "stream offline" gracefully (since the RTMP push only engages while `livestream` affordance is active).

---

## W4.7 — brio-synths unclaimed video interfaces

### Background
Sprint 1 finding 3 noted that the brio-synths BRIO exposes multiple `/dev/video*` nodes via the UVC driver and asked whether any of them were "unclaimed" — i.e. left dangling without a consumer.

### Audit
The 9726C031 BRIO body (currently mapped to the `brio-synths` role) exposes four V4L2 video interfaces under `/dev/v4l/by-id/`:

| Interface | Symlink target | Capture format(s) | Purpose |
|-----------|----------------|-------------------|---------|
| `usb-046d_Logitech_BRIO_9726C031-video-index0` | `/dev/video4` | YUYV / MJPEG | Primary RGB capture |
| `usb-046d_Logitech_BRIO_9726C031-video-index1` | `/dev/video5` | (none enumerated) | UVC metadata or secondary control endpoint |
| `usb-046d_Logitech_BRIO_9726C031-video-index2` | `/dev/video6` | GREY 8-bit | UVC metadata / secondary stream |
| `usb-046d_Logitech_BRIO_9726C031-video-index3` | `/dev/video7` | (none enumerated) | UVC metadata or extension-unit endpoint |

All four interfaces are claimed by the kernel `uvcvideo` driver. The compositor uses `index0` only (the primary RGB MJPEG stream, which is the high-resolution path). Indices 1–3 are standard UVC sub-interfaces that the BRIO exposes for things like:
- Per-frame metadata (timestamps, sequence numbers)
- Secondary greyscale streams (commonly used for IR or face-tracking on the BRIO)
- UVC extension-unit endpoints (vendor controls)

These are not "unclaimed bugs" — they're standard UVC class behavior. The BRIO firmware exposes them and they're available if a consumer wants to use them (e.g. fusing the GREY stream with Pi-NoIR IR data for shadow detection), but nothing in the compositor or daimonion currently consumes them.

### Conclusion
No fix needed. The interfaces are correctly enumerated, claimed by `uvcvideo`, and intentionally unused by current code. Future opportunity: the `index2` GREY 8-bit stream could be a useful second-channel input for IR fusion if the operator ever wants the BRIO to act as a NIR sensor in addition to its primary RGB role. Not in scope for tonight.

---

## Status

Both audits closed. No follow-up code work scheduled. This doc is the canonical record so future sessions don't re-run the same investigations.

---

## 2026-04-14 update — LRR Phase 0 item 6: native RTMP path is canonical

Filed alongside this audit doc as part of LRR Phase 0 (Verification & Stabilization). The RTMP output path is fully wired and consent-gated; this section pins the decision and documents the runtime contract.

### `toggle_livestream` definition

`agents/studio_compositor/compositor.py:594-647` defines `StudioCompositor.toggle_livestream(activate, reason)`. The method:

1. Accesses `self._rtmp_bin` (constructed at compositor build time, **detached** by default per `agents/studio_compositor/pipeline.py:194` log line `"rtmp output bin constructed (detached until toggle_livestream)"`)
2. On `activate=True`: calls `rtmp_bin.build_and_attach(self.pipeline)`, sets `metrics.RTMP_CONNECTED{endpoint="youtube"}=1`, sends an ntfy notification
3. On `activate=False`: calls `rtmp_bin.detach_and_teardown(self.pipeline)`, clears the metric, sends an ntfy stop notification
4. Returns `(success, message)` for the affordance handler

### Consent gating

`toggle_livestream` is **only** called from the affordance handler that runs after the unified semantic recruitment pipeline's consent check. The constitutional axiom `interpersonal_transparency` (`axioms/registry.yaml` weight 88) requires a `livestream` capability with `consent_required=True`, so the affordance pipeline filters it out unless an active consent contract exists. Fail-closed, 60 s cache.

This means the RTMP output cannot start without:
1. Affordance pipeline recruiting the `livestream` capability
2. Consent contract being active in `axioms/contracts/`
3. Affordance handler dispatching `compositor.toggle_livestream(True, reason)` on the GLib main loop

### The chain when active

```
director_loop / affordance handler
  → compositor.toggle_livestream(True, ...)
    → rtmp_bin.build_and_attach(pipeline)
      → GStreamer elements wired into the encoder tee
        → rtmp2sink location=rtmp://127.0.0.1:1935/studio
          → MediaMTX accepts publish on path 'studio'
            → HLS muxer at http://127.0.0.1:8888/studio/index.m3u8
              → in-app Logos preview, restream candidates, etc.
```

### Decision: native RTMP is the canonical LRR output path

For all LRR phase work going forward:

- **Native RTMP (the chain documented above) is canonical.** Phase 5 (Hermes 3 substrate swap) latency budgets, Phase 9 (closed-loop feedback) trigger latencies, and Phase 10 (observability + drills) measurements all use the native RTMP path.
- **The OBS-fork path** (`/dev/video42` v4l2 loopback → OBS → NVENC → OBS RTMP push) is **legacy**. It still works and is useful for operator-controlled scene composition during recording, but LRR's research-validity requirements need the deterministic single-process path that native RTMP provides. The OBS fork remains available for non-LRR use cases.
- **`/dev/video42` loopback stays alive** because Logos preview surfaces and the studio-person-detector still consume it. It's not deprecated, just not part of the LRR critical path.

### LRR Phase 0 exit criterion satisfied

> `toggle_livestream` path documented; production output confirmed.

This update is the documentation. Production output is confirmed by the audit chain in PR #781 plus the `metrics.RTMP_CONNECTED{endpoint="youtube"}` gauge wiring already in place.
