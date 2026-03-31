# IR Perception Remediation Design

**Date:** 2026-03-31
**Status:** Draft
**Scope:** Fix signal quality, retrain person detection, complete integration wiring
**Depends on:** 2026-03-29-ir-perception-system-design.md (original spec)

## Motivation

The IR perception infrastructure (3 Pi NoIR edge daemons, Logos API receiver, ir_presence backend, perception engine integration) is fully deployed and mechanically sound. Every Pi posts structured JSON every ~2s, state files are fresh, the backend fuses signals, and the perception state writer exports to JSON.

The problem is signal quality. An audit on 2026-03-31 found:

| Signal | Design Intent | Actual State |
|--------|--------------|--------------|
| Person detection | Lighting-invariant, 0.90 Bayesian weight | Always empty — model detects nothing |
| Gaze/posture | Face landmark classification | Dead — fdlite disabled (NumPy 2.x) |
| Hand tracking | Instrument activity on dark surfaces | Frame-spanning false positives |
| Screen detection | LCD/OLED as NIR-dark rectangles | Zero screens detected |
| Biometrics (rPPG) | Heart rate from forehead ROI | Phantom values — no face ROI to anchor on |
| Drowsiness/PERCLOS | EAR-based alertness | Dead — no face landmarks |
| Stimmung floor | IR boosts perception_confidence | Not implemented |
| Cross-modal fusion | Contact mic + IR + RGB → activity | Partial (vision only, not contact mic) |

Root causes:
1. **30 NIR training frames** — catastrophically insufficient for fine-tuning. Confidence collapse from RGB→NIR domain shift.
2. **No max-area filter** on hand detection — adaptive thresholding triggers on large reflectance regions.
3. **rPPG pipeline not gated** on face detection actually succeeding.
4. **Screen detection threshold** untested against real NIR illumination levels.
5. **Integration wiring** left incomplete after deployment sprint.

## Architecture

Three independent fix batches. Batches 1 and 2 can proceed in parallel. Batch 3 depends on 1+2 delivering clean signals.

```
Batch 1 (Signal Quality)          Batch 2 (Person Detection)
├─ Hand false-positive fix         ├─ Capture pipeline (Pi-side)
├─ rPPG gating                     ├─ 500-frame annotated dataset
├─ Screen detection tuning         ├─ Two-stage transfer learning
└─ Staleness alignment             ├─ ONNX export + validation
                                   └─ Deploy to all 3 Pis
         ╲                       ╱
          ╲                     ╱
           Batch 3 (Integration Wiring)
           ├─ Stimmung perception_confidence floor
           ├─ 5 missing perception-state signals
           └─ Contact mic cross-modal fusion
```

---

## Batch 1: Signal Quality Fixes

All changes are to Pi-side edge code (`pi-edge/`) and deployed via scp.

### 1.1 Hand Detection False Positive Suppression

**File:** `pi-edge/ir_hands.py` → `detect_hands_nir()`

**Problem:** No upper bound on contour area. A large IR-reflective surface (desk, wall) passes the `min_area=2000` filter and gets classified as a "hand" because zone classification uses normalized bbox center.

**Fix:**
- Add `max_area_pct=0.25` parameter (reject contours covering >25% of frame area).
- Add aspect ratio filter: hand contours should have aspect ratio between 0.3 and 3.0 (reject near-square full-frame blobs).
- Both filters applied before zone classification.

```python
# In detect_hands_nir(), after contour area filter:
frame_area = grey_frame.shape[0] * grey_frame.shape[1]
if area > max_area_pct * frame_area:
    continue  # reject frame-spanning blobs
x, y, w, h = cv2.boundingRect(contour)
aspect = w / h if h > 0 else 0
if aspect < 0.3 or aspect > 3.0:
    continue  # reject non-hand shapes
```

**Validation:** With operator at desk, hand detections should be 0-2 per frame with bboxes <15% of frame area. Currently seeing 2-4 per frame with bboxes up to 96%.

### 1.2 rPPG Phantom Value Gating

**File:** `pi-edge/hapax_ir_edge.py` → biometric loop, and `pi-edge/ir_biometrics.py`

**Problem:** The BiometricTracker runs FFT on pixel intensity regardless of whether a face was actually detected. Without a face ROI, it samples arbitrary pixels and produces phantom heart rate values (42-54 bpm at 0.30-0.39 confidence).

**Fix:**
- Gate `update_rppg_intensity()` on face detection succeeding in the current frame.
- If no face detected, do not update the rPPG buffer. The `compute_heart_rate()` method already returns (0, 0.0) when the buffer is too short.
- Add a `face_detected: bool` field to BiometricTracker state to make the gate explicit.

```python
# In biometric update path:
if face_result is not None and face_result.landmarks:
    forehead_roi = extract_forehead_roi(frame, face_result)
    tracker.update_rppg_intensity(forehead_roi.mean())
    tracker.face_detected = True
else:
    tracker.face_detected = False
# rPPG buffer naturally decays (10s window) when not fed
```

**Also gate EAR updates:** `update_ear()` should only be called when face landmarks are available. Currently this is already the case (EAR comes from landmarks), but add an explicit guard.

**Validation:** With face landmarks disabled (current state), all biometric fields should be zero/null. No phantom heart rates.

### 1.3 Screen Detection Threshold Tuning

**File:** `pi-edge/ir_hands.py` → `detect_screens_nir()`

**Problem:** Zero screens detected. The function thresholds for "near-zero NIR intensity" regions, but the actual threshold may not match the studio's NIR illumination level.

**Root cause investigation required:** Capture a raw greyscale frame from the desk Pi (which faces monitors) and examine the actual pixel intensity distribution where screens are. LCD backlights may emit enough NIR to prevent the "dark rectangle" assumption from working.

**Fix approach:**
- Add a `--capture-debug` flag to the edge daemon that saves one raw frame to `/tmp/ir_debug_{role}.jpg` on SIGUSR1.
- Examine the frame to determine actual screen pixel intensity range.
- If screens are darker than surroundings but not near-zero, adjust the threshold from hard-coded to `mean_brightness * 0.3` (adaptive to scene).
- If screens are NOT darker than surroundings in NIR, mark screen detection as non-viable without an IR-pass filter on the camera lens and remove from Tier 1 capabilities.

**Validation:** With monitors on, desk Pi should detect 1-3 screen regions. If not achievable, document the limitation.

### 1.4 Staleness Threshold Alignment

**File:** `agents/hapax_daimonion/ir_signals.py`

**Problem:** Design spec says 10s staleness cutoff. Implementation uses 15s.

**Fix:** Change `max_age_seconds` default from 15.0 to 10.0 in both `read_ir_signal()` and `read_all_ir_reports()`. The Pis post every 2-3s, so 10s gives ~4 missed posts before staleness — sufficient margin.

---

## Batch 2: Person Detection Retraining

### 2.1 Why 30 Frames Failed

The original fine-tuning used 30 NIR frames — well below the minimum ~300 needed for domain-shifted fine-tuning. The result is confidence collapse: the model memorized specific poses from 30 frames and produces near-zero confidence on any variation. This is a documented failure mode when running RGB-pretrained YOLO on greyscale/NIR input.

### 2.2 Capture Pipeline

**New file:** `pi-edge/ir_capture.py`

A lightweight capture script that runs on each Pi, separate from the inference daemon. Purpose: collect diverse annotated training frames.

**Capture modes:**
1. **Timed sampling** — capture 1 frame every N seconds while daemon is running. Reads from a second camera session or saves the daemon's pre-inference frame.
2. **Burst capture** — stop daemon, capture 50 frames at 2fps, restart daemon. For pose diversity sessions.

**Implementation:** Add a `--save-frames` flag to the existing daemon that writes every Nth pre-inference frame to `~/hapax-edge/captures/{role}_{timestamp}.jpg`. This avoids camera contention.

**Frame diversity requirements (per Pi role):**
- 170+ frames per role (500+ total across 3 Pis)
- Operator present in varied poses: sitting, standing, walking, reaching, leaning, entering/leaving frame
- Operator absent: empty room, 10-15% of frames
- Different times: day session, evening session (different ambient IR)
- Different clothing: NIR reflectance varies by fabric (cotton absorbs, synthetics reflect)
- Partial occlusion: behind monitor, behind equipment, at frame edge

**Capture schedule:** 3 sessions across 2 days.
- Session 1: Normal work session, timed sampling 1 frame/5s for 30 min per Pi (360 frames)
- Session 2: Directed poses — stand, sit, reach, walk, lean (50 frames per Pi, burst)
- Session 3: Evening/different clothing, timed sampling 20 min per Pi (240 frames)

Total raw: ~750 frames. After dedup and quality filter: ~500 usable.

### 2.3 Annotation

**Tool:** Roboflow (free tier, 10k images). Cloud-hosted, model-assisted labeling.

**Process:**
1. Upload all captured frames to a Roboflow project.
2. Run Roboflow's pretrained person detector for initial bbox predictions.
3. Manually correct: add missed detections, fix bbox alignment, remove false positives.
4. Single class: `person` (class 0).
5. Export in YOLOv8 format (images/ + labels/ with normalized xywh .txt files).
6. Split by capture session (not random) to prevent train/val data leakage.
7. Target split: 80% train, 10% val, 10% test.

**Annotation stored in repo:** `pi-edge/training/nir-person-v2/` with `data.yaml`.

### 2.4 Two-Stage Transfer Learning

Train on the workstation RTX 3090 (~10 GB free VRAM, sufficient for YOLOv8n).

**Stage 1 — FLIR thermal intermediate fine-tune:**

Download FLIR ADAS v2 thermal dataset from Kaggle (`samdazel/teledyne-flir-adas-thermal-dataset-v2`, 14,452 thermal images). Extract person-class annotations only (class 0 in FLIR = "person"). Convert to YOLOv8 format if needed. Fine-tune YOLOv8n from COCO pretrained weights. This teaches the model to detect people from shape/silhouette in IR-like imagery rather than RGB color features.

```python
from ultralytics import YOLO
model = YOLO("yolov8n.pt")  # COCO pretrained
model.train(
    data="flir-person.yaml",
    epochs=50,
    imgsz=320,         # match Pi inference size
    batch=32,
    device=0,
    hsv_h=0.0,         # disable hue augmentation (greyscale)
    hsv_s=0.0,         # disable saturation augmentation
    hsv_v=0.4,         # keep brightness jitter
    mosaic=1.0,
    mixup=0.15,
    single_cls=True,   # person only
    name="flir-person-stage1",
)
```

Input: pseudo-RGB (greyscale stacked to 3 channels). FLIR images are already greyscale-like.

**Stage 2 — NIR studio fine-tune:**

Fine-tune the Stage 1 checkpoint on our 500 annotated NIR frames.

```python
model = YOLO("runs/detect/flir-person-stage1/weights/best.pt")
model.train(
    data="pi-edge/training/nir-person-v2/data.yaml",
    epochs=100,
    imgsz=320,
    batch=16,
    device=0,
    hsv_h=0.0,
    hsv_s=0.0,
    hsv_v=0.4,
    mosaic=1.0,
    mixup=0.15,
    copy_paste=0.1,
    single_cls=True,
    patience=20,        # early stopping
    name="nir-person-v2",
)
```

**Validation target:** mAP@50 > 0.80 on test split. Confidence on true positives > 0.5.

### 2.5 Export and Deployment

**Primary export: ONNX** (current pipeline, proven to work on Pi ONNX Runtime).

```python
model = YOLO("runs/detect/nir-person-v2/weights/best.pt")
model.export(format="onnx", imgsz=320, simplify=True)
```

**Secondary export: NCNN** (2-3x faster on ARM, future upgrade path).

```python
model.export(format="ncnn", imgsz=320)
```

**Deployment:**
1. scp `best.onnx` to each Pi at `~/hapax-edge/best.onnx` (overwrites current model).
2. Restart daemon on each Pi: `sudo systemctl restart hapax-ir-edge`.
3. Verify via `GET /api/pi/status` and live state files.

**Rollback:** Keep previous `best.onnx` as `best.onnx.bak` on each Pi.

### 2.6 Confidence Threshold Update

The current inference code uses `CONFIDENCE_THRESHOLD = 0.25` (relaxed from design's 0.4 due to poor model performance). After retraining with adequate data:

- Set `CONFIDENCE_THRESHOLD = 0.40` (back to design spec).
- The retrained model should produce >0.5 confidence on true positives, so 0.4 gives margin.

### 2.7 Greyscale Input Handling

**Current code in `ir_inference.py`** already handles greyscale→RGB conversion:

```python
if len(frame.shape) == 2:
    frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2RGB)
```

This is correct — pseudo-RGB preserves COCO pretrained weights. No change needed.

---

## Batch 3: Integration Wiring

These changes are council-side only. No Pi changes.

### 3.1 Stimmung Perception Confidence Floor — ALREADY IMPLEMENTED

**File:** `agents/visual_layer_aggregator/stimmung_methods.py:72-78`

The audit reported stimmung had "zero IR signal references." This was incorrect — the VLA stimmung feeder (which calls `stimmung_collector.update_perception()`) already contains:

```python
ir_detected = agg._last_perception_data.get("ir_person_detected", False)
ir_hands = agg._last_perception_data.get("ir_hand_activity", "idle")
if ir_detected or ir_hands not in ("idle", ""):
    confidence = max(float(confidence), 0.7)
```

This is the designed perception_confidence floor. No additional work needed.

### 3.2 Missing Perception State Signals

**File:** `agents/hapax_daimonion/_perception_state_writer.py`

The backend produces 13 signals. The state writer exports 8. Add the missing 5:

| Signal | Type | Why Missing | Consumer Value |
|--------|------|------------|----------------|
| `ir_person_count` | int | Oversight | Guest detection, consent |
| `ir_motion_delta` | float | Oversight | Activity classification |
| `ir_head_pose_yaw` | float | Oversight | Attention direction |
| `ir_posture` | str | Oversight | Ergonomic awareness |
| `ir_heart_rate_conf` | float | Oversight | Biometric signal quality gate |

Add to the IR section of the perception state dict alongside the existing 8 fields.

### 3.3 Contact Mic Cross-Modal Fusion

**File:** `agents/hapax_daimonion/backends/contact_mic.py`

**Design spec (Component 8):** "Contact mic energy + IR hands-on-pads + RGB activity → high-confidence producing."

The vision backend already consumes `ir_hand_activity`. Extend the contact mic backend to read IR hand activity for disambiguation:

| Contact Mic | IR Hands | Fused Activity |
|-------------|----------|----------------|
| scratching energy | zone=turntable | scratching (high confidence) |
| tapping energy | zone=mpc-pads | pad work (high confidence) |
| typing energy | zone=desk-center | typing (high confidence) |
| energy present | hands=none | ambient noise (low confidence) |
| silent | hands present | visual-only activity (no sound) |

The contact mic backend reads from the perception behavior dict (same as vision backend). Add `ir_hand_activity` and `ir_hand_zone` (new: extract from the hand detection reports) as supplementary inputs to the activity classifier.

**Note:** This requires the ir_presence backend to expose hand zone in addition to hand activity. Currently `ir_hand_activity` is a single string. Add `ir_hand_zone` (str) as signal #14 from the backend.

---

## Out of Scope

- **Face landmark replacement** — fdlite requires upstream fix for NumPy 2.x. When fixed, gaze/posture/EAR will come back automatically. Not blocking on this.
- **IR LED rings** — Tier 2 hardware ($9 total). Not blocking retraining. Biometrics will improve once face detection works, but full PERCLOS/rPPG accuracy needs the LEDs.
- **NCNN migration** — Future performance optimization. ONNX Runtime works at ~200-400ms, sufficient for 2-3s post interval.
- **Video streaming** — Design spec explicitly excludes this.
- **MQTT backbone** — From spatial awareness research spec, independent project.

## Testing Strategy

### Batch 1 (unit tests, council-side)
- `test_ir_hands.py`: frame-spanning contour rejected, normal hand contour accepted, aspect ratio filter works.
- `test_ir_biometrics.py`: rPPG values are zero when no face detected.
- Existing `test_ir_presence_backend.py` and `test_ir_signals.py` should still pass.

### Batch 2 (model validation)
- mAP@50 > 0.80 on held-out test split.
- Live validation: operator at desk → `ir_person_detected: True` within 3s.
- Live validation: empty room → `ir_person_detected: False`.
- Confidence on true positives > 0.5.

### Batch 3 (integration tests)
- Stimmung perception_confidence ≥ 0.7 when IR detects person and RGB cameras degraded.
- All 13+1 signals present in perception-state.json.
- Contact mic + IR hand zone disambiguation produces expected fused activity labels.

## Deployment Sequence

1. **Batch 1** — Fix Pi-side code, scp to all Pis, restart daemons. Fix staleness threshold council-side. Run unit tests.
2. **Batch 2** — Capture frames (2 days), annotate (Roboflow), train (workstation GPU), export, deploy to Pis, validate live.
3. **Batch 3** — Council-side wiring changes, unit + integration tests, deploy via logos-api restart.

## Hardware Status

| Item | Status | Needed For |
|------|--------|-----------|
| Pi Camera Module 3 NoIR × 3 | All installed | All capabilities |
| 850nm IR flood illumination | Deployed | All capabilities (ambient NIR sufficient for Tier 1) |
| 850nm IR LED ring (on-axis) × 3 | Not ordered ($3/ea) | Tier 2: pupil tracking, PERCLOS, rPPG accuracy |
| Heatsink + fan × 3 | TBD | 24/7 thermal management (Pi-1 runs 61°C) |
| RTX 3090 (workstation) | Available (~10 GB free) | Training Stage 1 + Stage 2 |
