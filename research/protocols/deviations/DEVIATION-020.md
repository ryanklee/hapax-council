# Deviation Record: DEVIATION-020

**Date:** 2026-03-26
**Phase at time of change:** baseline
**Author:** hapax + Claude Opus 4.6

## What Changed

`agents/hapax_voice/conversation_pipeline.py`:
- Added `_desk_activity: str = "idle"` field (line 356)
- Passed `desk_activity=self._desk_activity` to `salience_router.route()` call

## Why

Wiring contact mic desk_activity signal through to salience router for production mode boost. The salience router already accepts the new parameter with a default — this change connects the live perception data to it.

## Impact on Experiment Validity

Minimal. The salience router's activation score gains +0.08 during active desk engagement (scratching/drumming/tapping). However, the intelligence-first override in conversation_pipeline.py already forces CAPABLE for all non-CANNED tiers, so the activation change only appears in diagnostic logging, not model selection.

## Mitigation

The intelligence-first override means the actual model tier used is unchanged — CAPABLE for all real utterances. The activation score change is diagnostic-only during baseline phase.
