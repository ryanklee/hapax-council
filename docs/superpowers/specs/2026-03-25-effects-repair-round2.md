# Effects System Repair Round 2 — Design Specification

**Date**: 2026-03-25
**Scope**: Systemic fixes (drift, trail categories, scanlines) + per-effect tuning from smoke test
**Prerequisite**: Round 1 effects repair (PR #335, branch `feat/effects-system-repair`)

---

## 1. Problem Statement

Smoke testing round 1 revealed three systemic issues affecting most effects:

1. **Frame detachment** — The drift mechanism shifts the entire accumulated back buffer sinusoidally, causing all historical content to roam around the canvas. Observed on 14/15 tested effects.
2. **Trail smear drowning GPU shaders** — Every preset forces GPU shader output through the trail persistence model at reduced alpha. GPU shader effects (pixsort, ASCII, halftone, glitch blocks, slit-scan) are invisible — their precise visual character is smeared into the echo buffer.
3. **Scanline overuse** — Generic 4px/0.12alpha CRT scanlines applied to 7 presets, but only 3 are authentically CRT-based (VHS, NightVision, ASCII).

Additionally, per-effect issues: Trails decay too fast, VHS too blurry (CSS blur), Neon lacks illuminance, Trap too dark + strobe broken, Screwed scanlines don't fit.

---

## 2. Systemic Fix 1: Kill Drift Globally

**Root cause**: `driftX`/`driftY` values on presets cause `CompositeCanvas.tsx` lines 589-611 to shift the ENTIRE `backCanvas` (all accumulated history) by fractional pixels every tick. This creates visible frame detachment on every effect with non-zero drift.

**Fix**: Set `driftX: 0, driftY: 0` on ALL presets. Trail separation comes naturally from temporal offset — different frames show the subject at different positions during motion. Drift adds nothing authentic.

**Presets requiring change** (currently have non-zero drift):
- Ghost: 3/4 → 0/0
- Trails: 2/3 → 0/0
- Screwed: 0/6 → 0/0
- Datamosh: 12/10 → 0/0
- VHS: 4/2 → 0/0
- Neon: 3/4 → 0/0
- Trap: 1/4 → 0/0
- Pixsort: 0/5 → 0/0
- Feedback: 2/3 → 0/0
- Glitch Blocks: 6/4 → 0/0

**File**: `compositePresets.ts` — set `driftX: 0, driftY: 0` in every preset's `trail` object.

---

## 3. Systemic Fix 2: Disable Trails on GPU Shader Effects

**Root cause**: When `trail.count > 0`, CompositeCanvas renders through the ping-pong persistence model. GPU shader output (pixsort sorting, ASCII character grids, halftone dots, etc.) is composited at reduced `mainAlpha` into the fading echo buffer, losing all precision and sharpness.

**Fix**: Set `trail.count: 0` on GPU-shader effects so they render via the clean no-trails path (clear canvas → draw frame → overlay → post-effects). This displays the GPU shader output at full opacity with no accumulation smear.

**Presets to set trail.count = 0**:
- Pixsort: count 4 → 0
- ASCII: count 2 → 0
- Halftone: count 2 → 0
- Glitch Blocks: count 5 → 0
- Slit-scan: count 8 → 0

**Keep trails on** (trail IS the effect or provides essential character):
- Ghost (5), Trails (12), Screwed (5), Datamosh (6), VHS (3), Neon (8), Trap (4), Diff (2), Feedback (12), NightVision (3), Silhouette (2), Thermal IR (2), Ambient (3), Clean (2)

**File**: `compositePresets.ts` — set `count: 0, opacity: 0` in the `trail` object for the 5 GPU-shader presets listed above.

---

## 4. Systemic Fix 3: Remove Scanlines from Non-CRT Effects

**Root cause**: One-size-fits-all scanline overlay (4px spacing, 0.12 alpha) applied to 7 presets. Only 3 are authentically CRT/interlaced-video effects.

**Fix**: Remove `scanlines: true` from:
- Datamosh (codec artifacts, purely digital)
- Trap (underground digital aesthetic)
- Glitch Blocks (digital block corruption)
- Screwed (lo-fi degradation comes from blur + noise, not CRT)

**Keep scanlines on**:
- VHS (interlaced tape scan lines)
- NightVision (P-43 phosphor CRT tube)
- ASCII (terminal CRT)

**File**: `compositePresets.ts` — set `scanlines: false` in the `effects` object for the 4 presets above.

---

## 5. Per-Effect Tuning

### 5.1 Trails — longer persistence

Reduce `lighter` baseFade from 0.03 to 0.015 in `computeTrailAlphas`. This halves the fade rate, keeping trail bodies visible longer before decaying. Addresses "needs more persistence with properly scaled decay."

**File**: `CompositeCanvas.tsx` — change baseFade for `lighter` in `computeTrailAlphas`.

### 5.2 VHS — remove CSS blur

Remove `blur(1.5px)` from colorFilter and `blur(3px)` from trail filter. The GPU VHS shader already handles softness via chroma bandwidth simulation and horizontal blur. CSS blur on top creates excessive smear.

**Current**: `"saturate(0.4) sepia(0.55) hue-rotate(-10deg) contrast(1.25) brightness(1.1) blur(1.5px)"`
**New**: `"saturate(0.4) sepia(0.55) hue-rotate(-10deg) contrast(1.25) brightness(1.1)"`

Trail filter current: `"saturate(0.3) sepia(0.6) blur(3px) brightness(1.05)"`
Trail filter new: `"saturate(0.3) sepia(0.6) brightness(1.05)"`

### 5.3 Neon — more illuminance and color variation

- Increase saturation: 2.5 → 3.5 (colorFilter)
- Increase trail saturation: 3 → 4 (trail filter)
- Increase bloom alpha: 0.5 → 0.7
- Increase hue accumulation rate in render loop: 4 → 8 degrees per tick for wider color spread

**File**: `compositePresets.ts` (saturation, bloom alpha), `CompositeCanvas.tsx` (hue accumulation rate).

### 5.4 Trap — visible + remove strobe

- Increase brightness: 0.65 → 0.75 so subject is visible through multiply darkening
- Remove `strobe` field entirely (random probability-based flashing with no musical connection is annoying, not aesthetic)
- Remove scanlines (already covered in §4)
- Keep noise, vignette, syrup, multiply blend

### 5.5 Screwed — remove scanlines

Already covered in §4. The blur + noise + syrup gradient provide sufficient lo-fi degradation without CRT scanlines.

### 5.6 Feedback — may need zoom increase

With drift gone, the recursive zoom (1.04) should become more visible since the zoom tunnel won't be displaced by buffer wandering. Observe after drift fix — may need zoom increase to 1.06 if still not recursive enough.

### 5.7 Ambient — may need more blur

With drift gone, the abstract color wash should read cleaner. May need to increase blur from 8px to 12px if the scene is still too recognizable. Observe after drift fix.

---

## 6. Files Modified

| File | Changes |
|------|---------|
| `compositePresets.ts` | All drift → 0/0; GPU shader trails → count 0; scanlines removed from 4 presets; VHS blur removed; Neon saturation/bloom; Trap brightness/strobe removal |
| `CompositeCanvas.tsx` | baseFade lighter 0.03→0.015; hue accumulation rate 4→8 |

---

## 7. What Is NOT Changed

- GPU shaders (all verified working — the problem was frontend trail smear, not shader correctness)
- Backend presets (studio_effects.py — no changes needed)
- Noise/bloom/circularMask infrastructure (working correctly)
- Warp mechanism (separate from drift, correctly pre-rendered to scratch canvas)
- Filter crossfade (implemented in round 1)
- Overlay drift fix (completed in round 1)
