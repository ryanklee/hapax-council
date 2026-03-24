# Hapax Bar — Visual Tuning Design

**Date:** 2026-03-24
**Status:** Design
**Scope:** Make the bar visually alive — visible gradient, readable elements, ISA-101 compliance

---

## 1. Problem

The bar functions correctly but communicates nothing visually. The stimmung gradient is a dark smear indistinguishable from the background. Particles are invisible at 15% opacity on #1d2021. The consent beacon is 8px on a 2560px bar. The cost whisper is 12px wide. Normal state should "go gray" per ISA-101, but everything is already gray — there's no contrast between normal and abnormal.

## 2. Stimmung Gradient

### 2.1 Baseline Tint

Even when all dimensions are 0.0 (nominal), the field should have a faint living color — not flat background. Add a 2-3% tint of the mode accent color (yellow for R&D, blue for Research) to the gradient center. This reads as "the system is on and healthy" vs. "the bar is broken."

Implementation: after building gradient stops, blend a subtle accent at position 0.5 with intensity 0.03.

### 2.2 Nominal Breathing

Current: nominal amplitude = 0.0 (dead). Change to 0.015 at 12s period. Nearly imperceptible, but the field is never fully static. Communicates "alive."

### 2.3 Dimension Intensity

Current: `intensity * 0.4` caps visible contribution. Increase to `intensity * 0.6`. Test: is cautious stance visually distinguishable from nominal? Currently it's not.

## 3. Particles

### 3.1 Visibility

Current: base alpha 0.15, oscillates 0.05-0.25. On dark background, invisible.
New: base alpha 0.30, oscillates 0.20-0.45. Visible but not distracting.

### 3.2 Size

Current: 4px radius. New: 6px radius. Visible at arm's length.

### 3.3 Color

Current: fixed beige (0.7, 0.5, 0.3). New: theme-aware — use `--green-400` tint at nominal, shift toward `--orange-400` as agent count rises. Particles become semantic: green = healthy activity, orange = heavy load.

## 4. Consent Beacon

Current: 8px wide. New: 16px wide. Add tooltip on hover: "Perception: {state}". Pulse width (±2px) when guest present, not just opacity.

## 5. Temporal Ribbon

### 5.1 Opacity

Current: 0.6 base, 0.15 session fill, 0.4 event countdown.
New: 0.85 base, 0.35 session fill, 0.65 event countdown.

### 5.2 Event Urgency

When event < 5 minutes: shift countdown color from blue-400 to orange-400. Add breathing at 2s period.

## 6. Cost Whisper

Current: 12px wide. New: 20px wide. ISA-101: gray when budget > 75%. Only color in warning (amber) and critical (red) zones.

## 7. ISA-101 "Going Gray"

Apply consistently:
- Nudge badge: hidden when 0, gray when 1-2, green 3-5, amber 6-10, red 11+
- Cost whisper: gray when > 75% budget
- Temporal ribbon event: gray when > 60min away, blue when < 60min, orange when < 5min

## 8. Seam Timeout

Current: 5s auto-dismiss. New: 15s. Reset timer on any mouse movement inside seam.

## 9. Workspace Hover

Add CSS `:hover` state with subtle background elevation.

## 10. CSS Deduplication

Split into 3 files:
- `hapax-bar-base.css` — layout, sizing, animation, shared rules
- `hapax-bar-rnd.css` — only `:root` color variables
- `hapax-bar-research.css` — only `:root` color variables

`theme.py` loads base + mode file.
