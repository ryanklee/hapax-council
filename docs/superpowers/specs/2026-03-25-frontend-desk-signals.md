# Frontend Desk Signal Display

**Date:** 2026-03-25
**Status:** Design approved
**Depends on:** Contact Mic Integration (merged), Scratch Detection, Overhead Zone Tracking

## Summary

Wire 7 new contact mic and overhead camera signals into the Logos frontend TypeScript types and display them in PerceptionMeter and PerceptionOverlayPortal. The backend already writes these to perception-state.json; the frontend is completely blind to them.

## Component 1: TypeScript Types

**File:** `hapax-logos/src/api/types.ts`

Add to `PerceptionState` interface (after `detected_action: string`):

```typescript
  // Contact mic (desk vibration sensing)
  desk_activity: string;
  desk_energy: number;
  desk_onset_rate: number;
  desk_tap_gesture: string;
  desk_spectral_centroid: number;
  desk_autocorr_peak: number;
  // Overhead hand tracking
  overhead_hand_zones: string;
```

All fields have sensible zero-values in the JSON (`""` for strings, `0.0` for numbers), so the frontend gracefully handles missing data from older perception writers.

## Component 2: PerceptionMeter

**File:** `hapax-logos/src/components/perception/PerceptionMeter.tsx`

Add two new badges after the existing `detected_action` IconTag:

### Desk Activity Badge

Show the current desk activity classification with instrument-aware colors:

```tsx
{/* Desk activity (contact mic) */}
{perception.desk_activity && perception.desk_activity !== "idle" && perception.desk_activity !== "" && (
  <IconTag
    icon={Activity}
    value={perception.desk_activity.replace(/_/g, " ")}
    color={
      perception.desk_activity === "scratching"
        ? "text-rose-300"
        : perception.desk_activity === "drumming"
          ? "text-orange-300"
          : perception.desk_activity === "tapping"
            ? "text-amber-300"
            : perception.desk_activity === "typing"
              ? "text-zinc-400"
              : "text-zinc-400"
    }
  />
)}
```

Color rationale: scratching (rose) is the most distinctive production activity. Drumming (orange) is high-energy. Tapping (amber) is moderate. Typing (zinc) is non-musical, dimmed.

### Desk Energy Bar

Show energy as a percentage badge — only when above idle threshold:

```tsx
{/* Desk energy (contact mic) */}
{perception.desk_energy > 0.12 && (
  <Tag
    value={`desk ${Math.round(perception.desk_energy * 100)}%`}
    color={
      perception.desk_energy > 0.5
        ? "bg-emerald-900/50 text-emerald-300"
        : perception.desk_energy > 0.25
          ? "bg-amber-900/50 text-amber-300"
          : "bg-zinc-800 text-zinc-400"
    }
  />
)}
```

### Overhead Hand Zones

Show which instrument zones have hands — only when non-empty:

```tsx
{/* Overhead hand zones */}
{perception.overhead_hand_zones && perception.overhead_hand_zones !== "" && (
  <IconTag
    icon={Hand}
    value={perception.overhead_hand_zones.replace(/,/g, " + ")}
    color="text-violet-300"
  />
)}
```

## Component 3: PerceptionOverlayPortal (Minimal Mode)

**File:** `hapax-logos/src/components/perception/PerceptionOverlayPortal.tsx`

Add desk activity to the top-left badge group (alongside person count, gaze, emotion):

```tsx
{perception.desk_activity && perception.desk_activity !== "idle" && perception.desk_activity !== "" && (
  <span className="rounded bg-black/70 px-2 py-0.5 text-[10px] font-bold text-emerald-300 backdrop-blur-sm">
    {perception.desk_activity.replace(/_/g, " ")}
  </span>
)}
```

## What NOT to Display

- `desk_onset_rate` — Internal DSP metric, not meaningful to the operator
- `desk_spectral_centroid` — Same, diagnostic only
- `desk_autocorr_peak` — Same, diagnostic only (and effectively disabled)
- `desk_tap_gesture` — Transient, auto-expires in <1s, would flash too briefly to read

These are available in the TypeScript type for the ClassificationInspector (diagnostic tool) but not shown in the production UI.

## File Inventory

| Action | Path | Scope |
|--------|------|-------|
| Edit | `hapax-logos/src/api/types.ts` | Add 7 fields to PerceptionState |
| Edit | `hapax-logos/src/components/perception/PerceptionMeter.tsx` | Add desk_activity + desk_energy + overhead_hand_zones |
| Edit | `hapax-logos/src/components/perception/PerceptionOverlayPortal.tsx` | Add desk_activity badge in minimal mode |

## Testing

| Component | Method |
|-----------|--------|
| TypeScript types | `npm run build` in hapax-logos — type errors if fields are wrong |
| Visual rendering | Manual — check PerceptionMeter shows desk activity during typing/drumming |
| Overlay badge | Manual — toggle overlay to minimal mode, verify desk_activity appears |

## Design Language Compliance

- Colors use Tailwind classes (not hardcoded hex) per §3 of design language
- Typography: `text-[9px]` for badges, JetBrains Mono (inherited)
- No decorative elements, flat badges on dark background per §1.2
- Conditional rendering hides badges when idle/empty (no visual noise)
