# Deviation Record: DEVIATION-019

**Date:** 2026-03-25
**Phase at time of change:** baseline
**Author:** Claude Opus 4.6 (alpha session)

## What Changed

`agents/hapax_voice/conversation_pipeline.py`:
- Added `generate_spontaneous_speech(impingement)` method (~50 lines)
- Bypasses STT, routes impingement context to LLM, LLM decides whether to speak or [silence]

`agents/hapax_voice/cognitive_loop.py`:
- Added spontaneous speech polling in utterance dispatch block (~10 lines)
- Added `_dispatch_spontaneous_speech(impingement)` method (~15 lines)
- Only fires during MUTUAL_SILENCE phase

## Why

Phase 1 of the impingement-driven activation cascade: speech is a tool, recruited when the DMN detects a situation warranting verbal output. This is the first spontaneous behavior — the system speaks without being addressed.

## Impact on Experiment Validity

**Minimal.** Spontaneous speech only fires during MUTUAL_SILENCE (no active conversation). The LLM can choose [silence] to suppress output. The feature has no effect during active voice sessions where grounding quality is being measured.

## Mitigation

Set `self._speech_capability = None` in voice daemon init to disable spontaneous speech entirely. The cognitive loop checks `hasattr` + `is not None` before polling.
