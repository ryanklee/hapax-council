# Deviation Record: DEVIATION-021

**Date:** 2026-03-27
**Phase at time of change:** baseline
**Author:** Claude (alpha session)

## What Changed

`agents/hapax_daimonion/conversation_pipeline.py` — two comment-only changes:
- Line 1852: `"Kokoro synthesizes them as"` → `"they synthesize as Unicode names"`
- Line 1952: `"# Kokoro output rate"` → `"# Voxtral output rate"`

No functional code changes. Same sample rate (24000), same logic.

## Why

TTS engine swap from Kokoro to Voxtral. Comments referenced the old engine name. Part of a larger migration (feat/voxtral-tts-swap branch).

## Impact on Experiment Validity

None. Comment-only changes, no behavioral impact.

## Mitigation

No code logic changed. Verified by diff inspection.
