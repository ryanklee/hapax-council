# IR Batch 1: Signal Quality Fixes — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix hand detection false positives, gate phantom biometric values, add debug capture for screen detection tuning, and align staleness threshold with design spec.

**Architecture:** Pi-side edge code changes (Batch 1.1–1.3) deployed via scp. Council-side staleness fix (1.4) is a one-line default change. All changes are backward-compatible with existing API and state file format.

**Tech Stack:** Python 3, OpenCV, NumPy (Pi-side); council Python 3.12 (staleness fix)

**Spec:** `docs/superpowers/specs/2026-03-31-ir-perception-remediation-design.md`

---

### Task 1: Hand detection — add max area filter

**Files:**
- Modify: `pi-edge/ir_hands.py:9-51`

- [ ] **Step 1: Add `max_area_pct` parameter and filter**

In `detect_hands_nir()`, add a `max_area_pct` parameter and reject contours exceeding it. Insert the check after the existing `min_area` filter and before the existing aspect ratio filter.

```python
def detect_hands_nir(
    grey_frame: np.ndarray, min_area: int = 2000, max_area_pct: float = 0.25
) -> list[dict]:
    """Detect hands on instrument surfaces using NIR skin/plastic contrast.

    In NIR, skin has lower reflectance than most plastics. Adaptive
    thresholding segments skin regions, filtered by area and shape.
    """
    blurred = cv2.GaussianBlur(grey_frame, (11, 11), 0)
    thresh = cv2.adaptiveThreshold(
        blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 31, 8
    )

    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
    thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel, iterations=2)
    thresh = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel, iterations=1)

    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    h, w = grey_frame.shape[:2]
    frame_area = h * w
    hands = []
    for contour in contours:
        area = cv2.contourArea(contour)
        if area < min_area:
            continue
        if area > max_area_pct * frame_area:
            continue

        x, y, cw, ch = cv2.boundingRect(contour)
        aspect = cw / ch if ch > 0 else 0
        if aspect < 0.3 or aspect > 3.0:
            continue

        cx = (x + cw / 2) / w
        cy = (y + ch / 2) / h
        zone = _classify_zone(cx, cy)
        activity = _classify_activity(contour, area)

        hands.append(
            {
                "zone": zone,
                "bbox": [x, y, x + cw, y + ch],
                "activity": activity,
            }
        )

    return hands[:4]
```

- [ ] **Step 2: Verify syntax**

```bash
python3 -c "import ast; ast.parse(open('pi-edge/ir_hands.py').read()); print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add pi-edge/ir_hands.py
git commit -m "fix(ir): add max_area_pct filter to hand detection

Rejects contours covering >25% of frame area. Prevents frame-spanning
NIR reflectance regions from being classified as hands."
```

---

### Task 2: Gate rPPG on face detection

**Files:**
- Modify: `pi-edge/hapax_ir_edge.py:159-169`

- [ ] **Step 1: Gate rPPG update on face landmark data**

Currently lines 160-169 update rPPG from forehead ROI whenever `persons` is non-empty. But a person detection without face landmarks has no real forehead ROI — it's just the top 30% of the YOLO bbox. Gate on the person actually having face landmark data (a `head_pose` dict with non-zero values).

Replace the rPPG section (lines 159-169):

```python
            # rPPG: update intensity from forehead ROI (only if face landmarks available)
            if persons:
                best = max(persons, key=lambda p: p.get("confidence", 0))
                head_pose = best.get("head_pose", {})
                has_face = head_pose and head_pose.get("yaw") is not None
                if has_face:
                    bbox = best["bbox"]
                    fy1 = bbox[1]
                    fy2 = bbox[1] + int((bbox[3] - bbox[1]) * 0.3)
                    fx1, fx2 = bbox[0], bbox[2]
                    if fy2 > fy1 and fx2 > fx1:
                        forehead = grey[fy1:fy2, fx1:fx2]
                        if forehead.size > 0:
                            self._biometrics.update_rppg_intensity(float(np.mean(forehead)))
```

- [ ] **Step 2: Verify syntax**

```bash
python3 -c "import ast; ast.parse(open('pi-edge/hapax_ir_edge.py').read()); print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add pi-edge/hapax_ir_edge.py
git commit -m "fix(ir): gate rPPG update on face landmark availability

Prevents phantom heart rate values when YOLO detects a person but
fdlite face landmarks are disabled (NumPy 2.x incompatibility)."
```

---

### Task 3: Add SIGUSR1 debug frame capture

**Files:**
- Modify: `pi-edge/hapax_ir_edge.py`

- [ ] **Step 1: Add debug frame save on SIGUSR1**

Add a `_save_debug_frame = False` attribute to `IrEdgeDaemon.__init__`.

Add a `request_debug_frame()` method that sets the flag and logs.

In `_main_loop`, after `color, grey = ...` (line 123), add:

```python
            if self._save_debug_frame:
                debug_path = f"/tmp/ir_debug_{self._role}.jpg"
                cv2.imwrite(debug_path, grey)
                log.info("Debug frame saved to %s", debug_path)
                self._save_debug_frame = False
```

In `main()`, after `signal.signal(signal.SIGINT, _sigterm)` (line 278), add:

```python
    def _sigusr1(signum, frame):  # noqa: ANN001
        daemon.request_debug_frame()

    signal.signal(signal.SIGUSR1, _sigusr1)
```

- [ ] **Step 2: Verify syntax**

```bash
python3 -c "import ast; ast.parse(open('pi-edge/hapax_ir_edge.py').read()); print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add pi-edge/hapax_ir_edge.py
git commit -m "feat(ir): add SIGUSR1 debug frame capture

Send SIGUSR1 to save next greyscale frame to /tmp/ir_debug_{role}.jpg
for screen detection threshold investigation."
```

---

### Task 4: Adaptive screen detection threshold

**Files:**
- Modify: `pi-edge/ir_hands.py:78-109`

- [ ] **Step 1: Make screen threshold adaptive to scene brightness**

Replace the hard-coded threshold of 15 with a scene-adaptive threshold. Screens are darker than the scene average — use `mean_brightness * 0.3` with a floor of 10.

```python
def detect_screens_nir(grey_frame: np.ndarray, min_area_pct: float = 0.02) -> list[dict]:
    """Detect screens as low-NIR-intensity rectangles.

    LCD/OLED screens emit no NIR, appearing as dark rectangles relative
    to the IR-illuminated scene. Threshold adapts to scene brightness.
    """
    h, w = grey_frame.shape[:2]
    total_area = h * w

    mean_brightness = float(np.mean(grey_frame))
    dark_threshold = max(10, int(mean_brightness * 0.3))

    _, dark_mask = cv2.threshold(grey_frame, dark_threshold, 255, cv2.THRESH_BINARY_INV)

    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 15))
    dark_mask = cv2.morphologyEx(dark_mask, cv2.MORPH_CLOSE, kernel, iterations=2)

    contours, _ = cv2.findContours(dark_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    screens = []
    for contour in contours:
        area = cv2.contourArea(contour)
        if area / total_area < min_area_pct:
            continue

        x, y, cw, ch = cv2.boundingRect(contour)
        rect_area = cw * ch
        if rect_area > 0 and area / rect_area > 0.7:
            screens.append(
                {
                    "bbox": [x, y, x + cw, y + ch],
                    "area_pct": round(area / total_area, 3),
                }
            )

    return screens[:5]
```

- [ ] **Step 2: Verify syntax**

```bash
python3 -c "import ast; ast.parse(open('pi-edge/ir_hands.py').read()); print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add pi-edge/ir_hands.py
git commit -m "fix(ir): adaptive screen detection threshold

Replace fixed NIR dark threshold (15) with scene-adaptive
mean_brightness * 0.3. Handles varying IR illumination levels."
```

---

### Task 5: Align staleness threshold to design spec

**Files:**
- Modify: `agents/hapax_daimonion/ir_signals.py:22,36`
- Test: `tests/hapax_daimonion/test_ir_signals.py`

- [ ] **Step 1: Change default staleness from 15s to 10s**

In `ir_signals.py`, change both function signatures:

```python
def read_ir_signal(path: Path, max_age_seconds: float = 10.0) -> dict[str, object] | None:
```

```python
def read_all_ir_reports(
    state_dir: Path | None = None, max_age_seconds: float = 10.0
) -> dict[str, dict[str, object]]:
```

- [ ] **Step 2: Run existing tests**

```bash
uv run pytest tests/hapax_daimonion/test_ir_signals.py tests/hapax_daimonion/test_ir_presence_backend.py -v
```

Expected: all 12 tests pass. The stale test uses `max_age_seconds=10` explicitly, so it still works.

- [ ] **Step 3: Commit**

```bash
git add agents/hapax_daimonion/ir_signals.py
git commit -m "fix(ir): align staleness threshold to design spec (10s)

Design spec says 10s cutoff. Implementation drifted to 15s. With Pis
posting every 2-3s, 10s gives ~4 missed posts before staleness."
```

---

### Task 6: Deploy to Pis and verify

- [ ] **Step 1: scp updated Pi-side files to all 3 Pis**

```bash
for pi in hapax-pi1 hapax-pi2 hapax-pi6; do
  echo "=== Deploying to $pi ==="
  scp pi-edge/ir_hands.py pi-edge/hapax_ir_edge.py $pi:~/hapax-edge/
done
```

- [ ] **Step 2: Restart daemons**

```bash
for pi in hapax-pi1 hapax-pi2 hapax-pi6; do
  echo "=== Restarting $pi ==="
  ssh $pi "sudo systemctl restart hapax-ir-edge"
done
```

- [ ] **Step 3: Wait 10s then verify hand detection is cleaner**

```bash
sleep 10
for f in ~/hapax-state/pi-noir/*.json; do
  echo "=== $(basename $f) ==="
  python3 -c "
import json
d = json.load(open('$f'))
hands = d.get('hands', [])
print(f'  hands: {len(hands)}')
for h in hands:
    bbox = h.get('bbox', [])
    area = (bbox[2]-bbox[0]) * (bbox[3]-bbox[1]) if len(bbox)==4 else 0
    frame_area = 640*480
    pct = area/frame_area*100
    print(f'    zone={h[\"zone\"]} activity={h[\"activity\"]} area={pct:.1f}%')
bio = d.get('biometrics', {})
print(f'  heart_rate_bpm: {bio.get(\"heart_rate_bpm\", 0)}')
print(f'  heart_rate_conf: {bio.get(\"heart_rate_confidence\", 0)}')
"
done
```

Expected: No hand bboxes >25% of frame. Heart rate should be 0 (no face landmarks = no rPPG feed).

- [ ] **Step 4: Capture debug frames for screen investigation**

```bash
for pi in hapax-pi1 hapax-pi2 hapax-pi6; do
  ssh $pi "kill -USR1 \$(pgrep -f hapax_ir_edge)"
  sleep 2
  scp $pi:/tmp/ir_debug_*.jpg /tmp/ 2>/dev/null
done
ls -la /tmp/ir_debug_*.jpg
```

Examine the frames to determine if adaptive screen threshold detects monitors.
