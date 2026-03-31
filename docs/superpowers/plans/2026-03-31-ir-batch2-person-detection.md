# IR Batch 2: Person Detection Retraining — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Retrain YOLOv8n person detection for 850nm NIR studio images via two-stage transfer learning (COCO → FLIR thermal → studio NIR). Deploy to all 3 Pis with validated mAP@50 > 0.80.

**Architecture:** Capture frames from existing Pi daemons, annotate via Roboflow, train on workstation RTX 3090, export ONNX, deploy via scp. Two-stage transfer: FLIR thermal intermediate checkpoint teaches IR-domain shape priors, then studio NIR fine-tune adapts to actual deployment environment.

**Tech Stack:** ultralytics 8.4.22, ONNX Runtime, Python 3.12, RTX 3090 (10GB free VRAM)

**Spec:** `docs/superpowers/specs/2026-03-31-ir-perception-remediation-design.md` §2

---

### Task 1: Add frame capture to edge daemon

**Files:**
- Modify: `pi-edge/hapax_ir_edge.py`

- [ ] **Step 1: Add `--save-frames` flag and capture interval**

Add CLI argument `--save-frames` (int, default 0 = disabled) that saves every Nth pre-inference frame to `~/hapax-edge/captures/{role}_{timestamp}.jpg`.

In `argparse` section of `main()`, add:

```python
    parser.add_argument(
        "--save-frames", type=int, default=0,
        help="Save every Nth frame to ~/hapax-edge/captures/ (0=disabled)",
    )
```

Pass to daemon:

```python
    daemon = IrEdgeDaemon(
        role=args.role,
        hostname=hostname,
        workstation_url=args.workstation,
        save_frame_interval=args.save_frames,
    )
```

- [ ] **Step 2: Add capture logic to daemon**

In `IrEdgeDaemon.__init__`, add:

```python
        self._save_interval = save_frame_interval
        self._frame_count = 0
        self._captures_dir = Path.home() / "hapax-edge" / "captures"
        if self._save_interval > 0:
            self._captures_dir.mkdir(parents=True, exist_ok=True)
```

Update `__init__` signature to include `save_frame_interval: int = 0`.

In `_main_loop`, after `color, grey = ...` and the debug frame block, add:

```python
            self._frame_count += 1
            if self._save_interval > 0 and self._frame_count % self._save_interval == 0:
                ts = datetime.now(UTC).strftime("%Y%m%d_%H%M%S_%f")
                path = self._captures_dir / f"{self._role}_{ts}.jpg"
                cv2.imwrite(str(path), grey)
```

- [ ] **Step 3: Verify syntax**

```bash
python3 -c "import ast; ast.parse(open('pi-edge/hapax_ir_edge.py').read()); print('OK')"
```

- [ ] **Step 4: Commit**

```bash
git add pi-edge/hapax_ir_edge.py
git commit -m "feat(ir): add --save-frames flag for training data capture

Saves every Nth pre-inference greyscale frame to ~/hapax-edge/captures/.
Used to build the NIR person detection training dataset."
```

---

### Task 2: Deploy capture and collect Session 1 frames

- [ ] **Step 1: Deploy updated daemon with --save-frames**

```bash
for pi in hapax-pi1 hapax-pi2 hapax-pi6; do
  scp pi-edge/hapax_ir_edge.py $pi:~/hapax-edge/
done
```

- [ ] **Step 2: Start capture on all Pis (1 frame every 5 seconds)**

Temporarily override the systemd service to add `--save-frames 25` (5 FPS × 5 = every 25th frame ≈ 5s). Or restart manually:

```bash
for pi in hapax-pi1 hapax-pi2 hapax-pi6; do
  role=$(ssh $pi "grep ROLE /etc/systemd/system/hapax-ir-edge.service | grep -oP 'desk|room|overhead'")
  ssh $pi "sudo systemctl stop hapax-ir-edge && nohup ~/hapax-edge/.venv/bin/python ~/hapax-edge/hapax_ir_edge.py --role=$role --save-frames=25 > /tmp/ir_capture.log 2>&1 &"
  echo "$pi ($role): capture started"
done
```

- [ ] **Step 3: Let run for 30 minutes during normal work**

Work normally at the desk. Move around occasionally. Get up and leave once. The goal is diverse poses: sitting, typing, reaching, leaning, standing, and absent frames.

Expected: ~360 frames per Pi (1/5s × 30min × 60s = 360), ~1080 total.

- [ ] **Step 4: Collect frames**

```bash
mkdir -p /tmp/ir_training_raw
for pi in hapax-pi1 hapax-pi2 hapax-pi6; do
  role=$(ssh $pi "ls ~/hapax-edge/captures/ | head -1 | cut -d_ -f1")
  scp "$pi:~/hapax-edge/captures/*.jpg" /tmp/ir_training_raw/
  echo "$pi: $(ssh $pi 'ls ~/hapax-edge/captures/ | wc -l') frames"
done
echo "Total: $(ls /tmp/ir_training_raw/ | wc -l) frames"
```

- [ ] **Step 5: Restore normal daemon operation**

```bash
for pi in hapax-pi1 hapax-pi2 hapax-pi6; do
  ssh $pi "pkill -f 'hapax_ir_edge.*save-frames'; sudo systemctl start hapax-ir-edge"
done
```

---

### Task 3: Collect Session 2 — directed poses

- [ ] **Step 1: Burst capture with explicit poses**

For each Pi, stop daemon, run burst capture at 2fps for 30 seconds per pose set:

```bash
for pi in hapax-pi1 hapax-pi2 hapax-pi6; do
  role=$(ssh $pi "grep ROLE /etc/systemd/system/hapax-ir-edge.service | grep -oP 'desk|room|overhead'")
  ssh $pi "sudo systemctl stop hapax-ir-edge && ~/hapax-edge/.venv/bin/python ~/hapax-edge/hapax_ir_edge.py --role=$role --save-frames=1 &"
  echo "$pi: burst capture started — perform poses now"
done
```

Perform these poses for ~2 minutes total:
- Sit normally, face forward
- Stand up, step back
- Walk across room
- Lean to reach something
- Sit with different posture (leaning back, forward)
- Leave frame entirely (10s)
- Return and sit down
- Raise arms / gesture

- [ ] **Step 2: Collect and restore**

```bash
for pi in hapax-pi1 hapax-pi2 hapax-pi6; do
  scp "$pi:~/hapax-edge/captures/*.jpg" /tmp/ir_training_raw/
  ssh $pi "rm ~/hapax-edge/captures/*.jpg; pkill -f 'hapax_ir_edge.*save-frames'; sudo systemctl start hapax-ir-edge"
done
echo "Total after session 2: $(ls /tmp/ir_training_raw/ | wc -l) frames"
```

---

### Task 4: Deduplicate and quality-filter frames

- [ ] **Step 1: Write dedup script**

Create `scripts/ir_dedup_frames.py`:

```python
#!/usr/bin/env python3
"""Deduplicate near-identical IR training frames via perceptual hashing."""

import hashlib
import sys
from pathlib import Path

import cv2
import numpy as np


def phash(img: np.ndarray, size: int = 8) -> str:
    resized = cv2.resize(img, (size + 1, size))
    diff = resized[:, 1:] > resized[:, :-1]
    return hashlib.md5(diff.tobytes()).hexdigest()


def main():
    src = Path(sys.argv[1])
    dst = Path(sys.argv[2])
    dst.mkdir(parents=True, exist_ok=True)

    seen: set[str] = set()
    kept = 0
    skipped = 0

    for f in sorted(src.glob("*.jpg")):
        img = cv2.imread(str(f), cv2.IMREAD_GRAYSCALE)
        if img is None:
            continue
        h = phash(img)
        if h in seen:
            skipped += 1
            continue
        seen.add(h)
        cv2.imwrite(str(dst / f.name), img)
        kept += 1

    print(f"Kept {kept}, skipped {skipped} duplicates")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run dedup**

```bash
python3 scripts/ir_dedup_frames.py /tmp/ir_training_raw /tmp/ir_training_deduped
```

Expected: ~500-700 unique frames from ~1000+ raw.

- [ ] **Step 3: Commit script**

```bash
git add scripts/ir_dedup_frames.py
git commit -m "feat(ir): add training frame dedup script (perceptual hash)"
```

---

### Task 5: Annotate via Roboflow

This is a manual step using the Roboflow web UI.

- [ ] **Step 1: Upload frames to Roboflow**

Create a Roboflow project "hapax-nir-person" with single class "person". Upload all deduped frames from `/tmp/ir_training_deduped/`.

- [ ] **Step 2: Model-assisted labeling**

Run Roboflow's pretrained person detector on all frames. Review and correct: add missed detections, fix bbox alignment, remove false positives. Label all persons in every frame. Frames with no person are background examples (keep ~10-15% unlabeled as negatives).

- [ ] **Step 3: Split and export**

Split by capture session (not random): Session 1 → train, Session 2 → val/test.
Export in YOLOv8 format. Download and extract to `pi-edge/training/nir-person-v2/`.

- [ ] **Step 4: Verify dataset structure**

```bash
ls pi-edge/training/nir-person-v2/
# Expected: data.yaml, train/, valid/, test/
# Each containing images/ and labels/ subdirectories
cat pi-edge/training/nir-person-v2/data.yaml
```

The `data.yaml` should look like:

```yaml
train: train/images
val: valid/images
test: test/images
nc: 1
names: ['person']
```

- [ ] **Step 5: Commit dataset config (not images)**

```bash
# Add data.yaml only — images are too large for git
echo "pi-edge/training/nir-person-v2/train/" >> .gitignore
echo "pi-edge/training/nir-person-v2/valid/" >> .gitignore
echo "pi-edge/training/nir-person-v2/test/" >> .gitignore
git add pi-edge/training/nir-person-v2/data.yaml .gitignore
git commit -m "feat(ir): add NIR person detection dataset config

Dataset annotated via Roboflow. Images stored locally (too large for
git). data.yaml references train/valid/test splits."
```

---

### Task 6: Stage 1 — FLIR thermal intermediate training

- [ ] **Step 1: Download FLIR ADAS v2 person subset**

Download from Kaggle (`samdazel/teledyne-flir-adas-thermal-dataset-v2`). Extract person-class-only annotations into a YOLO-format dataset.

```bash
# If kaggle CLI available:
kaggle datasets download -d samdazel/teledyne-flir-adas-thermal-dataset-v2 -p /tmp/flir/
# Otherwise download manually from Kaggle web UI
```

- [ ] **Step 2: Create FLIR training script**

Create `scripts/train_ir_stage1_flir.py`:

```python
#!/usr/bin/env python3
"""Stage 1: Fine-tune YOLOv8n on FLIR thermal person detection."""

from ultralytics import YOLO

model = YOLO("yolov8n.pt")

model.train(
    data="/tmp/flir/data.yaml",  # adjust path to extracted dataset
    epochs=50,
    imgsz=320,
    batch=32,
    device=0,
    hsv_h=0.0,
    hsv_s=0.0,
    hsv_v=0.4,
    mosaic=1.0,
    mixup=0.15,
    single_cls=True,
    name="flir-person-stage1",
    project="runs/detect",
)

print("Stage 1 complete. Best weights:", "runs/detect/flir-person-stage1/weights/best.pt")
```

- [ ] **Step 3: Run Stage 1 training**

```bash
cd ~/projects/hapax-council && uv run python scripts/train_ir_stage1_flir.py
```

Expected: ~30 minutes on RTX 3090. mAP@50 on FLIR val should be >0.60.

- [ ] **Step 4: Commit training script**

```bash
git add scripts/train_ir_stage1_flir.py
git commit -m "feat(ir): Stage 1 FLIR thermal person detection training script"
```

---

### Task 7: Stage 2 — NIR studio fine-tune

- [ ] **Step 1: Create Stage 2 training script**

Create `scripts/train_ir_stage2_nir.py`:

```python
#!/usr/bin/env python3
"""Stage 2: Fine-tune FLIR checkpoint on studio NIR person detection."""

from pathlib import Path

from ultralytics import YOLO

stage1_weights = Path("runs/detect/flir-person-stage1/weights/best.pt")
if not stage1_weights.exists():
    raise FileNotFoundError(f"Stage 1 weights not found: {stage1_weights}")

model = YOLO(str(stage1_weights))

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
    patience=20,
    name="nir-person-v2",
    project="runs/detect",
)

print("Stage 2 complete. Best weights:", "runs/detect/nir-person-v2/weights/best.pt")
```

- [ ] **Step 2: Run Stage 2 training**

```bash
cd ~/projects/hapax-council && uv run python scripts/train_ir_stage2_nir.py
```

Expected: ~20 minutes on RTX 3090. mAP@50 on NIR test split should be >0.80.

- [ ] **Step 3: Validate on test split**

```bash
cd ~/projects/hapax-council && uv run python -c "
from ultralytics import YOLO
model = YOLO('runs/detect/nir-person-v2/weights/best.pt')
results = model.val(data='pi-edge/training/nir-person-v2/data.yaml', split='test', imgsz=320)
print(f'mAP@50: {results.box.map50:.3f}')
print(f'mAP@50-95: {results.box.map:.3f}')
"
```

Expected: mAP@50 > 0.80. If not, review training logs for overfitting (val loss diverging from train loss) and consider more data or different augmentation.

- [ ] **Step 4: Commit training script**

```bash
git add scripts/train_ir_stage2_nir.py
git commit -m "feat(ir): Stage 2 NIR studio person detection training script"
```

---

### Task 8: Export to ONNX and deploy

- [ ] **Step 1: Export ONNX**

```bash
cd ~/projects/hapax-council && uv run python -c "
from ultralytics import YOLO
model = YOLO('runs/detect/nir-person-v2/weights/best.pt')
model.export(format='onnx', imgsz=320, simplify=True)
print('Exported to:', 'runs/detect/nir-person-v2/weights/best.onnx')
"
```

- [ ] **Step 2: Update confidence threshold back to design spec**

In `pi-edge/ir_inference.py`, change:

```python
CONFIDENCE_THRESHOLD = 0.40
```

- [ ] **Step 3: Deploy model and code to all Pis**

```bash
for pi in hapax-pi1 hapax-pi2 hapax-pi6; do
  echo "=== Deploying to $pi ==="
  # Backup old model
  ssh $pi "cp ~/hapax-edge/best.onnx ~/hapax-edge/best.onnx.bak"
  # Deploy new model + updated inference code
  scp runs/detect/nir-person-v2/weights/best.onnx $pi:~/hapax-edge/best.onnx
  scp pi-edge/ir_inference.py $pi:~/hapax-edge/
  # Restart
  ssh $pi "sudo systemctl restart hapax-ir-edge"
done
```

- [ ] **Step 4: Commit confidence threshold update**

```bash
git add pi-edge/ir_inference.py
git commit -m "fix(ir): restore confidence threshold to 0.40 (design spec)

With retrained model, confidence on true positives exceeds 0.5.
Threshold 0.40 matches original design spec."
```

---

### Task 9: Live validation

- [ ] **Step 1: Verify person detection while at desk**

```bash
sleep 10
for f in ~/hapax-state/pi-noir/*.json; do
  echo "=== $(basename $f) ==="
  python3 -c "
import json
d = json.load(open('$f'))
persons = d.get('persons', [])
print(f'  persons: {len(persons)}')
for p in persons:
    print(f'    confidence={p.get(\"confidence\", 0):.3f} bbox={p.get(\"bbox\", [])}')
"
done
```

Expected: At least desk Pi (and likely room Pi) should detect 1 person with confidence > 0.5.

- [ ] **Step 2: Verify perception state reflects detection**

```bash
python3 -c "
import json
d = json.load(open('$HOME/.cache/hapax-daimonion/perception-state.json'))
print(f'ir_person_detected: {d.get(\"ir_person_detected\")}')
print(f'ir_brightness: {d.get(\"ir_brightness\")}')
"
```

Expected: `ir_person_detected: True`

- [ ] **Step 3: Verify empty room detection**

Step away from the desk and all camera views for 15 seconds, then check:

```bash
sleep 15
python3 -c "
import json
d = json.load(open('$HOME/.cache/hapax-daimonion/perception-state.json'))
print(f'ir_person_detected: {d.get(\"ir_person_detected\")}')
"
```

Expected: `ir_person_detected: False`

- [ ] **Step 4: Store model artifact reference**

```bash
# Copy best.onnx to a versioned location
cp runs/detect/nir-person-v2/weights/best.onnx pi-edge/models/nir-person-v2.onnx
mkdir -p pi-edge/models
git add pi-edge/models/
git commit -m "feat(ir): store trained NIR person detection model v2

Two-stage transfer: COCO → FLIR thermal → studio NIR.
500+ frames, mAP@50 > 0.80 on test split."
```
