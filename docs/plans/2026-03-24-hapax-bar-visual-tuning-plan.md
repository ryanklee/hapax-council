# Hapax Bar — Visual Tuning Plan

**Date:** 2026-03-24
**Design:** hapax-bar-visual-tuning-design.md

## Phase 1: Stimmung Field Visual (biggest impact)

1. **stimmung_field.py** — gradient baseline tint, nominal breathing, dimension intensity
2. **stimmung_field.py** — particle visibility (opacity, size, semantic color)
3. **stimmung_field.py** — consent beacon wider (16px), tooltip, spatial pulse

## Phase 2: Widget Tuning

4. **temporal_ribbon.py** — opacity increase, event urgency color shift
5. **cost_whisper.py** — wider (20px), ISA-101 gray-when-good
6. **nudge_badge.py** — ISA-101 gray for low counts

## Phase 3: Interaction + CSS

7. **seam_window.py** — 15s timeout, reset on mouse movement
8. **CSS** — workspace hover, dedup into base + color files
9. **theme.py** — load base + mode CSS

## Estimated: ~150 lines changed across ~8 files
