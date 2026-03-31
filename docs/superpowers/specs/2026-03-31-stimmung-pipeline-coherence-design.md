# Stimmung Pipeline Coherence — Design Specification

**Date:** 2026-03-31
**Sprint:** 0, Day 2
**Status:** Approved (pre-approved by operator)

## Problem Statement

Full audit of the stimmung sync pipeline reveals 4 critical bugs, 4 high-severity issues, and 5 medium issues. The core model (`shared/stimmung.py`) is well-designed, but consumption is inconsistent and partially broken. The pipeline writes correctly but consumers read incorrectly.

## Confirmed Issues

### Critical (data loss / silent wrong behavior)

| ID | Issue | File:Line | Root Cause |
|----|-------|-----------|------------|
| C1 | API route parses flat dict; VLA writes nested | `logos/api/routes/stimmung.py:35-42` | `_build_dimensions()` does `raw.get(key, 0.0)` — gets nested dict object, not float |
| C2 | Sync persists 6/10 dimensions | `agents/stimmung_sync.py:30-37` | `DIMENSION_NAMES` missing cognitive + biometric |
| C3 | Imagination reads `"stance"` not `"overall_stance"` | `agents/imagination.py:179` | Field name typo |
| C4 | Reverie reads `"stance"` + phantom `"color_warmth"` | `agents/reverie/actuation.py:259,262` | Field names wrong; color_warmth never existed |

### High (reliability degradation)

| ID | Issue | File:Line |
|----|-------|-----------|
| H1 | 3 identical copies of stimmung.py (432 lines each) | `shared/`, `agents/`, `logos/` |
| H2 | Engine reads SHM with no staleness check | `logos/engine/__init__.py:369-378` |
| H3 | VLA swallows all source errors with bare `pass` | `agents/visual_layer_aggregator/stimmung_methods.py:36,48,62` |
| H4 | Manifest says `daemon`, service is `oneshot` on timer | `agents/manifests/stimmung_sync.yaml:6` |

### Medium

| ID | Issue | File:Line |
|----|-------|-----------|
| M1 | API drops `freshness_s` from response | `logos/api/routes/stimmung.py:41` |
| M2 | `update_engine()` never called from VLA | No call site |
| M3 | GQI staleness threshold hardcoded independently | `stimmung_methods.py:87` |
| M4 | ContextAssembler reads SHM file twice (stance + raw) | `shared/context.py:92,99` |
| M5 | No SHM write or E2E pipeline tests | Test suite |

## Design Decisions

### C4 — color_warmth semantics

`color_warmth` was intended as a visual signal for Reverie's shader pipeline. It should be derived from the worst infrastructure dimension value, mapping system stress to visual warmth:
- 0.0 = cool (system nominal)
- 1.0 = warm (system critical)

**Implementation:** Derive in reverie actuation from `stimmung_raw` worst infra dimension, not from a phantom field.

### H1 — Deduplication strategy

Replace `agents/_stimmung.py` and `logos/_stimmung.py` with thin re-export modules. This preserves all existing import paths while eliminating 864 lines of duplicate code. Update production imports where safe; leave test imports for a separate pass.

### M2 — Engine stats

The engine doesn't push stats to VLA currently. This requires architectural work (engine→SHM→VLA read path). **Deferred** — not in scope for this coherence fix. Document as known gap.

### M4 — Double SHM read

ContextAssembler reads the stimmung file twice: once for stance string, once for full dict. Fix: read once, extract both.

## Implementation Stages

### Stage 1: Critical consumer fixes (C1-C4)
Fix all field name mismatches and parsing bugs. Zero-risk, surgical changes.

### Stage 2: Deduplication (H1)
Replace duplicate files with re-exports. Update production imports.

### Stage 3: Robustness (H2, H3, H4, M1, M3, M4)
Add staleness checks, replace bare `pass` with logging, fix manifest, add freshness to API, consolidate GQI threshold, fix double-read.

### Stage 4: Sync completeness (C2)
Add all 10 dimensions to sync agent. Update daily doc generation.

### Stage 5: Test coverage (M5)
Add tests for SHM write, E2E pipeline, field name consistency.

### Stage 6: Verify
Run full test suite, lint, type check.
