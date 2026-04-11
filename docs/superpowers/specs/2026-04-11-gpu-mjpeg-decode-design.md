# GPU MJPEG Decode for Studio Compositor

**Date:** 2026-04-11
**Status:** Approved
**Scope:** Replace CPU MJPEG decode with NVIDIA nvjpegdec, reduce snapshot overhead

## Problem

The studio compositor decodes 6 USB camera MJPEG streams (3× BRIO 1080p + 3× C920 720p) using CPU `jpegdec`. At 30fps this is 254.7 megapixels/second of CPU decode, consuming ~600% CPU on a Ryzen 7 5800XT. The RTX 3090 GPU sits at 14% utilization.

Per-camera snapshots run at 1fps with CPU `jpegenc`, adding further CPU load for a use case (perception/person detection) that only needs a frame every few seconds.

## Design

### 1. nvjpegdec Camera Decode

Replace `jpegdec` with `jpegparse → nvjpegdec` in the MJPEG decode path (`cameras.py:104-117`). `nvjpegdec` uses the nvJPEG CUDA library to decode JPEG on GPU. Output is NV12 in CUDA memory.

`jpegparse` is required — `nvjpegdec` needs parsed JPEG frames, not raw V4L2 output.

**New decode chain:**
```
v4l2src → capsfilter(image/jpeg) → jpegparse → nvjpegdec → tee
```

**Fallback:** If `nvjpegdec` is unavailable (missing CUDA runtime, driver issue), fall back to `jpegdec` with a log warning. The downstream CUDA branch has `cudaupload` which handles CPU-resident buffers.

```python
decoder = Gst.ElementFactory.make("nvjpegdec", f"dec_{role}")
if decoder is not None:
    parser = Gst.ElementFactory.make("jpegparse", f"parse_{role}")
    for el in [src, src_caps, parser, decoder]:
        pipeline.add(el)
    src.link(src_caps)
    src_caps.link(parser)
    parser.link(decoder)
    last = decoder
    log.info("Camera %s: using nvjpegdec (GPU decode)", cam.role)
else:
    log.warning("Camera %s: nvjpegdec unavailable, falling back to jpegdec (CPU)", cam.role)
    decoder = Gst.ElementFactory.make("jpegdec", f"dec_{role}")
    for el in [src, src_caps, decoder]:
        pipeline.add(el)
    src.link(src_caps)
    src_caps.link(decoder)
    last = decoder
```

The CUDA compositor branch (`cudaupload → cudaconvert → cudascale`) is unchanged. When `nvjpegdec` outputs CUDA memory, `cudaupload` becomes a passthrough. When `jpegdec` outputs CPU memory, `cudaupload` handles the transfer.

### 2. Snapshot Branch Adaptation

Per-camera snapshots tee off after decode. With `nvjpegdec`, the tee output is NV12 in CUDA memory. The snapshot branch needs `cudadownload` to get data back to CPU for `jpegenc`.

**Reduce rate from 1fps to 0.2fps** (1 frame every 5 seconds). Sufficient for person detection and perception. Cuts snapshot CPU cost by 5×.

**New snapshot chain:**
```
tee → queue → cudadownload → videoconvert → videorate(0.2fps) → videoscale(640×360) → jpegenc → appsink
```

`cudadownload` is only added when `nvjpegdec` is active (`compositor._use_nvjpeg` flag). In CPU fallback mode, the chain is the same as before (minus the rate reduction, which applies regardless).

### 3. Detection Flag

Add `compositor._use_nvjpeg: bool` set during camera branch construction. True if the first camera's `nvjpegdec` creation succeeded. Used by the snapshot branch to decide whether `cudadownload` is needed.

## File Changes

| File | Action | Summary |
|------|--------|---------|
| `agents/studio_compositor/cameras.py:87-117` | Edit | `add_camera_branch`: replace `jpegdec` with `jpegparse → nvjpegdec`, fallback |
| `agents/studio_compositor/cameras.py:16-84` | Edit | `add_camera_snapshot_branch`: add conditional `cudadownload`, reduce rate to 0.2fps |

## Not Changed

- `pipeline.py` — CUDA compositor detection and output chain unchanged
- `fx_chain.py` — effect pipeline unchanged
- `config.py` — no new config knobs
- `effect_graph/pipeline.py` — shader pipeline unchanged

## Expected Impact

- **CPU:** ~600% → ~150-200% (MJPEG decode moves to GPU, snapshots 5× less frequent)
- **GPU:** ~14% → ~40-50% (JPEG decode + existing GL compositing + effects)
- **Video smoothness:** 5fps jerky → 30fps smooth (ffmpeg processes no longer CPU-starved)

## Testing

1. Start compositor — confirm "using nvjpegdec (GPU decode)" in logs for all 6 cameras
2. `nvidia-smi` — GPU utilization increases
3. `ps aux | grep compositor` — CPU% drops significantly
4. All 6 camera feeds render correctly in the compositor output
5. Per-camera snapshots still write to `/dev/shm/hapax-compositor/` (at ~5s intervals)
6. Fallback: `GST_PLUGIN_FEATURE_RANK=nvjpegdec:0` forces CPU path — verify `jpegdec` fallback works
