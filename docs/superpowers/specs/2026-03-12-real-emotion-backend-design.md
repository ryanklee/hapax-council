# Real Emotion Backend — Design Spec

> **Status:** Proposed
> **Date:** 2026-03-12
> **Scope:** `agents/hapax_voice/backends/emotion.py` — real visual emotion backend replacing stub
> **Builds on:** [Perception Primitives](2026-03-11-perception-primitives-design.md), [North Star](2026-03-11-backup-mc-north-star-design.md), [Audio Backend](2026-03-12-real-audio-backend-design.md)

## Problem

The EmotionBackend is a stub with `available() → False` and an empty `contribute()`. Both governance chains depend on `emotion_arousal` as a load-bearing signal — MC uses it for ad-lib/vocal-throw intensity selection, OBS uses it for scene selection (face_cam vs rapid_cut). Without real emotion data, governance decisions fall back to energy-only thresholds, losing the performer-state dimension that distinguishes "energetic and engaged" from "energetic and mechanical."

The operator has multiple cameras: a face cam for expression analysis and an overhead cam for gear/hand activity. The face cam provides valence/arousal/dominant emotion via facial expression analysis. The overhead cam provides activity level via optical flow — a physical arousal proxy useful when the face cam is unavailable or as supplementary signal.

## Goal

Replace the EmotionBackend stub with a real implementation that:

1. Captures frames from a specific V4L2 device via a background thread
2. Detects faces and extracts landmarks via MediaPipe Face Mesh
3. Classifies emotion (continuous valence + arousal + discrete category) via hsemotion-onnx
4. Writes source-qualified Behaviors (`emotion_valence:<source_id>`, `emotion_arousal:<source_id>`, `emotion_dominant:<source_id>`)
5. Reports `available() → True` when the camera device exists and models are loadable

Additionally, implement an `ActivityBackend` for overhead/gear cameras that:

1. Captures frames from a V4L2 device
2. Computes optical flow magnitude between consecutive frames
3. Normalizes to `activity_level` (0.0-1.0) via rolling-window adaptive normalization
4. Reports as a SLOW-tier backend providing `activity_level:<source_id>`

## Design Decisions

### D1: OpenCV VideoCapture over ffmpeg subprocess

**Decision:** Use `cv2.VideoCapture(device_path)` in a background thread, one per camera.

**Rationale:**
- The existing `webcam_capturer.py` uses ffmpeg subprocess for single-frame snapshots. That design is correct for its use case (periodic LLM-analyzed screenshots with 5s cooldown). But emotion analysis needs continuous frame streams at 3+ fps.
- `cv2.VideoCapture` holds the V4L2 device open and provides a continuous frame stream with zero per-frame subprocess overhead.
- OpenCV is already in dependencies (`opencv-python-headless>=4.10.0`).
- Multiple `VideoCapture` instances work simultaneously — one per camera, same pattern as multiple `pw-record` instances for audio.
- `read()` releases the GIL during C++ capture, so capture threads don't contend with inference.

**Trade-off:** Holds V4L2 device exclusively while running. The existing `webcam_capturer.py` must not capture from the same device simultaneously. The perception engine's lifecycle (start/stop) manages this.

### D2: MediaPipe Face Mesh for detection + landmarks

**Decision:** Use MediaPipe Face Mesh (478 landmarks) for both face detection and landmark extraction in a single pass.

**Rationale:**
- The existing `face_detector.py` already uses MediaPipe BlazeFace for detection. Face Mesh includes detection as a first stage, so we get both detection and landmarks for the same cost.
- 478 3D landmarks provide the face bounding box needed to crop the input for the emotion model.
- CPU inference (~10ms per frame). No GPU needed for this stage.
- MediaPipe is already in dependencies (`mediapipe>=0.10.0`).

**Trade-off:** Face Mesh is heavier than BlazeFace alone (~10ms vs ~5ms). Acceptable since we process at 1-3 fps, not 30 fps.

### D3: hsemotion-onnx for emotion classification

**Decision:** Use the `hsemotion-onnx` library with the `enet_b0_8_va_mtl` model (EfficientNet-B0 backbone) for simultaneous discrete emotion classification and continuous valence/arousal regression.

**Rationale:**
- Outputs all three required signals in one inference pass: 8 discrete emotion scores + continuous valence [-1,1] + continuous arousal [-1,1].
- ONNX backend — no TensorFlow dependency. TensorFlow is the single biggest dependency risk for Python 3.12+ / numpy 2.x compatibility.
- EfficientNet-B0 is lightweight: ~20MB model, ~200MB GPU VRAM, ~10ms inference on RTX 3090 via ONNX Runtime GPU.
- Trained on AffectNet (~400K images with continuous V/A labels). Production-quality training data.
- Apache 2.0 license (no commercial restrictions).
- Dependencies: `onnxruntime`, `opencv-python`, `numpy`, `scipy` — all compatible or already present.

**Trade-off:** Requires adding `hsemotion-onnx` and `onnxruntime-gpu` as new dependencies. `onnxruntime-gpu` is ~200MB. Acceptable given the RTX 3090 is available and already running Ollama.

### D4: Optical flow for overhead cam activity detection

**Decision:** Use OpenCV's dense optical flow (`calcOpticalFlowFarneback`) between consecutive frames to compute a scalar activity level for non-face cameras.

**Rationale:**
- The overhead cam sees hands on gear, not a face. No emotion model applies.
- Optical flow magnitude is a robust proxy for physical activity/arousal: high hand motion = high engagement.
- ~2ms per frame at 480p. No ML model, no GPU, no additional dependencies.
- Normalizing flow magnitude over a rolling window (same pattern as audio RMS normalization) gives `activity_level` in [0.0, 1.0].
- Complementary to facial arousal: physical engagement and facial expression are correlated but not identical signals.

**Trade-off:** Optical flow responds to any motion (camera shake, lighting changes), not just intentional activity. The rolling normalization and EMA smoothing mitigate transient noise.

### D5: Separate EmotionBackend and ActivityBackend

**Decision:** Two distinct backend classes rather than one polymorphic backend.

**Rationale:**
- They produce different behavior names (`emotion_valence` vs `activity_level`).
- They have different inference pipelines (face mesh + emotion model vs optical flow).
- They have different availability requirements (face detection capability vs any V4L2 device).
- The source naming and wiring layer already handle multiple backends per source. A single camera could conceivably feed both backends, but in practice face cam → EmotionBackend, overhead cam → ActivityBackend.
- Follows the existing pattern: AudioEnergyBackend and StreamHealthBackend are separate despite both relating to "audio."

### D6: Camera discovery via V4L2 device enumeration

**Decision:** `available()` checks that the specified V4L2 device path exists and is openable by OpenCV.

**Rationale:**
- V4L2 devices appear as `/dev/video*`. Not all are capture devices (some are metadata nodes).
- Opening with `cv2.VideoCapture(path)` and checking `isOpened()` is the definitive test.
- Camera identification by device path (e.g., `/dev/video0`) or by-id symlink (e.g., `/dev/v4l/by-id/usb-Logitech_C920-video-index0`).
- One-time check at registration, same pattern as audio's `discover_node`.

### D7: Frame processing at 1-3 fps, not capture rate

**Decision:** Capture at 15 fps but process every Nth frame (configurable, default every 5th = 3 fps inference).

**Rationale:**
- Emotion changes slowly relative to audio. 3 fps provides ~333ms temporal resolution — well within the SLOW cadence tier (3s polling interval).
- The capture thread runs at camera native rate to keep the V4L2 buffer drained (prevents stale frame accumulation). Only the latest frame is processed.
- At 3 fps inference: ~10ms face mesh + ~10ms emotion model = ~20ms per processed frame. CPU: ~3%. GPU: negligible.
- FreshnessGuard staleness limits are 3s (MC) and 5s (OBS). Processing at 3 fps ensures watermarks stay fresh.

## Architecture

### Face Cam Pipeline

```
cv2.VideoCapture("/dev/video0") at 640x480@15fps
  │
  │ Capture thread: grabs frames, holds "latest" (lock-protected)
  │
  ▼
Inference thread (every ~333ms):
  ├─ Read latest frame
  ├─ MediaPipe Face Mesh → 478 landmarks (or None if no face)
  │    └─ CPU, ~10ms
  ├─ Crop face region from landmarks bounding box
  ├─ Resize to 224×224, normalize
  ├─ hsemotion-onnx enet_b0_8_va_mtl → (8 emotions, valence, arousal)
  │    └─ ONNX Runtime GPU, ~10ms
  ├─ Publish:
  │    emotion_valence = valence (rescaled from [-1,1] to [0,1])
  │    emotion_arousal = arousal (rescaled from [-1,1] to [0,1])
  │    emotion_dominant = argmax(8 emotion scores) → string enum
  │    last_update = monotonic()
  └─ Thread-safe attribute writes (atomic under GIL)
      │
      ▼
contribute() (called by CadenceGroup on main thread):
  ├─ Read latest valence, arousal, dominant from attributes
  ├─ behaviors["emotion_valence:<source>"].update(v, now)
  ├─ behaviors["emotion_arousal:<source>"].update(a, now)
  └─ behaviors["emotion_dominant:<source>"].update(d, now)
```

### Overhead Cam Pipeline

```
cv2.VideoCapture("/dev/video2") at 640x480@15fps
  │
  │ Capture thread: grabs frames, holds "latest"
  │
  ▼
Inference thread (every ~333ms):
  ├─ Read latest frame
  ├─ Convert to grayscale
  ├─ cv2.calcOpticalFlowFarneback(prev_gray, curr_gray, ...)
  │    └─ CPU, ~2ms at 480p
  ├─ flow_magnitude = mean(sqrt(dx² + dy²))
  ├─ EMA smooth (alpha=0.2)
  ├─ Normalize: smoothed / running_max_30s
  ├─ Publish: activity_level = normalized (0.0-1.0)
  └─ Thread-safe attribute write
      │
      ▼
contribute():
  └─ behaviors["activity_level:<source>"].update(level, now)
```

### Camera Discovery

```python
def discover_camera(target: str) -> str | None:
    """Find a V4L2 camera device by path or by-id symlink.

    Args:
        target: A device path ("/dev/video0"), a by-id path
                ("/dev/v4l/by-id/usb-Logitech..."), or a substring
                to match against by-id symlink names.
    """
```

The `target` parameter accepts:
- A direct device path (e.g., `"/dev/video0"`)
- A by-id symlink (e.g., `"/dev/v4l/by-id/usb-Logitech_C920-video-index0"`)
- A substring match on by-id names (e.g., `"Logitech"`, `"C920"`)

### Lifecycle

- `__init__(source_id, target)` — validate source_id, store target
- `available()` — check device exists, openable, models loadable
- `start()` — launch capture thread + inference thread
- `contribute()` — read latest values, write to Behaviors
- `stop()` — stop threads, release VideoCapture

### Failure Modes

| Failure | Behavior |
|---------|----------|
| Camera not found | `available() → False`, backend skipped |
| Camera disconnected mid-session | Capture thread detects `read()` failure, logs error, watermarks stop advancing → FreshnessGuard rejects |
| No face detected | Valence/arousal hold last known values, watermark stops → FreshnessGuard rejects after staleness limit |
| MediaPipe import fails | `available() → False` (checked at registration) |
| ONNX model download fails | `available() → False` |
| USB bandwidth contention | Reduced framerate, dropped frames. Capture thread drains buffer, inference processes latest available frame |
| GPU OOM | ONNX Runtime falls back to CPU. Slower (~50ms) but functional within 3s cadence budget |

## Signals Produced

### EmotionBackend

| Behavior | Type | Range | Update Rate |
|----------|------|-------|-------------|
| `emotion_valence:<source>` | float | 0.0-1.0 (rescaled from model's [-1,1]) | ~3Hz |
| `emotion_arousal:<source>` | float | 0.0-1.0 (rescaled from model's [-1,1]) | ~3Hz |
| `emotion_dominant:<source>` | str | One of: neutral, happy, sad, angry, surprise, fear, disgust, contempt | ~3Hz |

### ActivityBackend

| Behavior | Type | Range | Update Rate |
|----------|------|-------|-------------|
| `activity_level:<source>` | float | 0.0-1.0 (normalized optical flow magnitude) | ~3Hz |

## Dependencies

### New

- `hsemotion-onnx>=0.3.1` — emotion classification (Apache 2.0)
- `onnxruntime-gpu>=1.17` — ONNX inference with CUDA support

### Existing

- `opencv-python-headless>=4.10.0` (in `audio` extra)
- `mediapipe>=0.10.0` (in `audio` extra)
- `numpy>=2.0` (core dependency)

### System

- V4L2-compatible USB cameras
- CUDA 12.x + cuDNN 9 (for ONNX Runtime GPU, already present for Ollama)

## Testing Strategy

Unit tests mock OpenCV and models — no real cameras or GPU needed in CI:

- **Camera discovery tests**: Mock `/dev/v4l/by-id/` directory listing, verify path matching
- **Frame reader tests**: Feed synthetic numpy frames via a mock VideoCapture, verify frame buffer behavior
- **Face detection + emotion tests**: Mock MediaPipe results and hsemotion model output, verify valence/arousal/dominant extraction and rescaling
- **Optical flow tests**: Feed pairs of synthetic frames, verify flow magnitude computation, EMA smoothing, normalization
- **Lifecycle tests**: Start/stop, thread cleanup, camera release
- **Contribute tests**: Source-qualified behavior writing, staleness handling, no-data-yet skip
- **Integration with wiring**: Verify source-qualified Behaviors land in the correct governance chain alias
- **Property tests**: Valence and arousal always 0.0-1.0, dominant always a valid enum value, watermarks are monotonic, activity_level always 0.0-1.0
