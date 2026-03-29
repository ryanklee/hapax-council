# Signal Wiring Enrichment

**Date:** 2026-03-25
**Status:** Design approved
**Depends on:** Contact Mic Integration (PR #333)

## Summary

Wire `desk_activity` from the ContactMicBackend into OBS governance (activity-aware scene selection), MC governance (scratch suppression), and export two additional DSP metrics (spectral centroid, autocorrelation peak) as behaviors for downstream consumers.

## Problem

The contact mic produces `desk_activity`, `desk_energy`, `desk_onset_rate`, and `desk_tap_gesture`, all available in `self.perception.behaviors`. OBS governance and MC governance both consume from this same behaviors dict but are completely blind to desk_activity. The DSP pipeline also computes spectral centroid and autocorrelation peak internally but doesn't export them.

## Component 1: OBS Governance — Activity-Aware Scene Selection

**File:** `agents/hapax_daimonion/obs_governance.py`

### Current Behavior

Four candidates in priority order: rapid_cut (energy ≥ 0.8), face_cam_mc_bias, face_cam (energy ≥ 0.5), gear_closeup (energy ≥ 0.2). Default: wide_ambient. Scenes are driven entirely by energy + arousal.

### Change

Add a new candidate `instrument_focus` that triggers GEAR_CLOSEUP when the operator is physically interacting with instruments, regardless of airborne audio energy. Insert it **after** face_cam but **before** the existing gear_closeup (priority: gear_closeup already fires at energy ≥ 0.2, but instrument_focus fires from desk_activity alone).

```python
Candidate(
    name="instrument_focus",
    predicate=lambda ctx: ctx.get_sample("desk_activity").value in (
        "scratching", "drumming", "tapping",
    ),
    action=OBSScene.GEAR_CLOSEUP,
),
```

This fires when the contact mic detects any instrument interaction, even if airborne audio energy is below 0.2 (e.g., headphone-only practice). The existing energy-based gear_closeup is redundant when this fires, but harmless since FallbackChain returns the first match.

### Required Behaviors

`desk_activity` must NOT be hard-required — the voice daemon must start even if the contact mic backend fails. Instead, the predicate handles missing behavior gracefully via an `in ctx.samples` guard. `FallbackChain` is constructed with a fixed candidate list (the `candidates` property returns a copy — `.insert()` on it is a no-op). The candidate must be included in the initial list.

```python
Candidate(
    name="instrument_focus",
    predicate=lambda ctx: (
        ctx.get_sample("desk_activity").value in ("scratching", "drumming", "tapping")
        if "desk_activity" in ctx.samples
        else False
    ),
    action=OBSScene.GEAR_CLOSEUP,
),
```

`FusedContext.samples` is a `MappingProxyType` — supports `in` checks. If `desk_activity` isn't in the behaviors dict passed to `with_latest_from`, it won't be in `samples`. The guard returns False and the candidate is skipped.

## Component 2: MC Governance — Scratch Suppression

**File:** `agents/hapax_daimonion/mc_governance.py`

### Current Behavior

Veto chain: speech_clear, energy_sufficient, spacing_respected, transport_active. All must pass for a throw to fire. Three action candidates: vocal_throw (energy ≥ 0.7), ad_lib (energy ≥ 0.3), silence.

### Change

Add a new veto `desk_allows_throw` that blocks throws during scratching and typing. Scratching is hands-on audio control — throws interrupt the operator's intentional sound. Typing is non-musical — throws during coding are jarring.

Insert in `build_mc_veto_chain()` after `speech_clear` (before `energy_sufficient`):

```python
Veto(
    name="desk_allows_throw",
    predicate=lambda ctx: (
        ctx.get_sample("desk_activity").value not in ("scratching", "typing")
        if "desk_activity" in ctx.samples
        else True  # allow if contact mic not available
    ),
),
```

When `desk_activity` is `"scratching"` or `"typing"`, this veto returns False → throw is blocked. For `"drumming"`, `"tapping"`, `"idle"` → veto passes → throw can fire.

Drumming and tapping ALLOW throws because pad playing and MC vocal samples are complementary — they layer rather than compete.

## Component 3: Export Additional DSP Metrics

**File:** `agents/hapax_daimonion/backends/contact_mic.py`

### Current State

The capture loop computes `spectral_centroid` and `autocorr_peak` but only uses them internally for classification. They're useful downstream:
- **Spectral centroid**: Tells what's vibrating (low = heavy impacts, high = clicks/taps)
- **Autocorrelation peak**: Tells how rhythmic the activity is (high = scratching, low = random)

### Change

Add two new behaviors to `provides` and `contribute()`:

```python
# In __init__:
self._b_spectral_centroid: Behavior[float] = Behavior(0.0)
self._b_autocorr_peak: Behavior[float] = Behavior(0.0)

# In provides:
return frozenset({
    "desk_activity", "desk_energy", "desk_onset_rate", "desk_tap_gesture",
    "desk_spectral_centroid", "desk_autocorr_peak",
})

# In _ContactMicCache, add fields + update signature
# In contribute():
self._b_spectral_centroid.update(float(data["desk_spectral_centroid"]), now)
self._b_autocorr_peak.update(float(data["desk_autocorr_peak"]), now)
behaviors["desk_spectral_centroid"] = self._b_spectral_centroid
behaviors["desk_autocorr_peak"] = self._b_autocorr_peak
```

Update `_ContactMicCache` to store and expose these values. Update the capture loop's `_cache.update()` call to pass the new fields:

```python
self._cache.update(
    desk_activity=activity,
    desk_energy=smoothed_energy,
    desk_onset_rate=onset_rate,
    desk_tap_gesture=current_gesture,
    desk_spectral_centroid=centroid,
    desk_autocorr_peak=autocorr_peak,
)
```

Both `centroid` and `autocorr_peak` are already in scope at the call site (computed every 4th frame, persisted across frames). The `_ContactMicCache.update()` signature uses `*` for keyword-only params — the new fields are appended after the existing ones.

### Perception State Export

Add to `_perception_state_writer.py`:

```python
"desk_spectral_centroid": _safe_float(_bval("desk_spectral_centroid", 0.0)),
"desk_autocorr_peak": _safe_float(_bval("desk_autocorr_peak", 0.0)),
```

## File Inventory

| Action | Path | Scope |
|--------|------|-------|
| Edit | `agents/hapax_daimonion/obs_governance.py` | Add instrument_focus candidate |
| Edit | `agents/hapax_daimonion/mc_governance.py` | Add desk_allows_throw veto |
| Edit | `agents/hapax_daimonion/backends/contact_mic.py` | Export spectral_centroid + autocorr_peak as behaviors |
| Edit | `agents/hapax_daimonion/_perception_state_writer.py` | Export 2 new fields |
| Create | `tests/hapax_daimonion/test_obs_desk_activity.py` | OBS instrument_focus candidate tests |
| Create | `tests/hapax_daimonion/test_mc_desk_suppression.py` | MC scratch suppression tests |
| Edit | `tests/hapax_daimonion/test_contact_mic_backend.py` | Update for 2 new behaviors in protocol test |

## Testing

| Component | Method |
|-----------|--------|
| OBS instrument_focus | Unit test: desk_activity=scratching → GEAR_CLOSEUP; desk_activity=idle → falls through |
| OBS backward compat | Unit test: no desk_activity in samples → candidate returns False |
| MC desk_allows_throw | Unit test: desk_activity=scratching → throw blocked; desk_activity=drumming → throw allowed |
| MC backward compat | Unit test: no desk_activity in samples → veto passes (allows throw) |
| New behaviors | Unit test: desk_spectral_centroid + desk_autocorr_peak in contribute() output |

## Constraints

- Both governance additions are soft — they degrade gracefully when contact mic is unavailable
- `FusedContext.samples` access via `in` check prevents KeyError
- The `instrument_focus` candidate does not override RAPID_CUT or FACE_CAM — those fire at higher priority for high-energy moments
- MC suppression during typing is intentional — vocal throws while coding are disruptive, not complementary
- Spectral centroid and autocorr_peak are computed every 4th frame; the exported behavior values update at this cadence (~128ms)
