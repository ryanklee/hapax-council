---
title: GEM rendering redesign — brainstorm
date: 2026-04-22
status: brainstorm (operator decides A / B / C before plan + spec)
context:
  - operator memory `feedback_gem_aesthetic_bar` (2026-04-21):
    "Current GEM rendering reads as chiron/ticker-tape. Must match
    Sierpinski's visual caliber (not look) — multi-layer, algorithmic,
    depth-capable. Text-in-a-box is a failure state."
  - cc-task: lssh-002 (WSJF 9.0)
related:
  - agents/studio_compositor/gem_source.py
  - agents/studio_compositor/sierpinski_renderer.py
  - agents/studio_compositor/hardm_source.py
  - agents/hapax_daimonion/gem_producer.py
---

> Methodology note: this brainstorm was authored by a subagent dispatch on
> 2026-04-22. The dispatch produced a 320-line working file; this doc is
> the operator-facing brief (full divergence + elimination history captured
> in the dispatch summary at the time). Three candidates survived
> elimination with full specificity.

## Problem framing — what "Sierpinski-caliber" actually means

Reading `gem_source.py::_render_text_centered` next to
`sierpinski_renderer.py` and `hardm_source.py` exposes the failure mode at
the **rendering-model** level, not the template level. Current GEM is one
font, one rectangle, one centered text string per frame. That is the
chyron failure mode no matter how good the font or how clever the text.

Reading the three together also reveals the actual quality bar.
Sierpinski-caliber means three things at once:

1. **Generative substrate that always runs.** The triangle subdivides
   continuously regardless of content. Content rides the substrate; it
   doesn't replace it.
2. **Multi-layer composition with depth cues.** Sierpinski has six layers
   visible at glance distance: outer triangle, L1 corner subdivision, L2
   inner subdivision, inscribed YouTube frames, central waveform, and
   audio-reactive line widths with glow halo. Depth comes from
   compositing order plus per-layer modulation.
3. **Signal-driven modulation visible at glance distance.** Line widths
   pulse with the audio envelope. Saturation tracks stance. The
   modulation reads even without parsing the content — that's the
   instrument-panel quality the operator's calling out.

Current GEM hits **zero** of these. Adding fancier templates inside the
single-text-string contract cannot clear the bar; the producer must
**author** a structured composition and the renderer must **compose
layers algorithmically**.

This means the redesign is not at the gem-producer prompt level. It is
at the renderer + producer-schema level. The v1 fallback (`» hapax «`)
is preserved by versioning the schema; old producer outputs continue to
land inside the v1 path while the renderer prefers v2 when present.

## Eliminated candidates

Out of 8 candidates explored in the dispatch, 5 were eliminated:

- **D1 — fancier centered-text templates** (e.g. drop shadow, two-tone).
  Rejected: still single-region, still ticker-tape. Quality bar is at
  the composition model, not the type treatment.
- **D2 — animated single-line crawl.** Rejected: structurally a ticker.
  Operator memory pins this exact failure mode.
- **D5 — pure ASCII-art glyph alone** (no substrate, no modulation).
  Rejected: fails the always-running-substrate criterion. Static glyph
  reads as decoration, not as instrument.
- **D6 — fixed-grid scoreboard** (HUD-style numeric panels). Rejected:
  reads as telemetry / debug overlay, not as compositional surface.
- **D7 — vertical scrolling text column.** Rejected: structurally a
  ticker rotated 90°. Same memory pin as D2.

## Surviving candidates

Three candidates survive with full specificity (gestalt, schema,
impingement-bus inputs, render budget, anti-pattern risk).

### Candidate A — Multi-region zones ("instrument panel")

Five fixed zones in the 1840×240 GEM band, each its own glyph
vocabulary and signal binding:

| Zone | Width | Content | Driving signal |
|---|---|---|---|
| 1. family-glyph | ~240 px | Single CP437 glyph denoting active fx family | preset-recruitment winner family |
| 2. density meter | ~320 px | Vertical bar of `▁▂▃▄▅▆▇█` ramping with audio RMS | audio envelope |
| 3. banner with Braille shadow | ~720 px | Center text + per-glyph Braille (`⠁⠂⠄⠈⠐⠠⡀⢀`) drop-shadow | producer-authored emphasis |
| 4. counter | ~180 px | Three-digit CP437 odometer | bar count / event count |
| 5. pulse strips | ~380 px | Three vertical strips, brightness modulated independently | stance, intensity, coherence |

Producer schema v2 carries `{family_glyph, density_value, banner_text,
counter_value, pulse_levels: [3]}`.

- **Cost.** Five Pango/Cairo regions, no shader pipeline. ~3 ms/tick at
  12 Hz. Lowest-cost option.
- **Risk profile.** Lowest aesthetic risk — every zone is independently
  legible. Highest "still-might-read-as-HUD" risk because the layout is
  fixed.
- **Best if** "Sierpinski-caliber" is interpreted as **information
  density + multi-layer + signal modulation**, less so as **algorithmic
  depth**.

### Candidate B — RD substrate + content mask

The full canvas runs a Gray-Scott reaction-diffusion field as a
background substrate that always animates. Producer-authored text
emerges as a **mask through the field** (the field is brighter where
the text is, dimmer where it isn't), then decays back into the
substrate over ~600–1200 ms.

- **Cost.** ~3–7 ms/tick depending on substrate brightness and text
  duration. RD is a well-trodden CPU-cheap pattern (already used in
  reverie's `rd` pass — port the kernel constants directly).
- **Risk profile.** Highest readability risk if substrate brightness
  competes with mask. Operator-tunable substrate brightness is a
  required parameter.
- **Best if** interpretation = **algorithmic depth + emergence**.
  Closest single-candidate match to Sierpinski's "always-running
  generative process" criterion.

### Candidate C — RD + nested box-draw rooms + fragment punch-in (A+B fusion)

Layer 1 is the RD substrate from B. Layer 2 is a recursive nested set
of CP437 box-draw "rooms" (`╔═╗║╚╝` and friends) at three depth levels,
positions and sizes modulated by per-room signal bindings (similar to
Sierpinski's L1/L2 corner subdivisions). Layer 3 is "fragment punch-in"
— short content-bearing strings appear briefly inside individual rooms,
fade out, then a different room takes over.

- **Cost.** ~6 ms/tick. Highest of the three but well within the
  studio_compositor per-tick budget (cairooverlay path, no GPU).
- **Risk profile.** Highest aesthetic ceiling, highest implementation
  cost, highest QA cost (per-room signal bindings are independent
  surfaces to verify). Producer schema v2 needs per-room emphasis
  arrays and per-room duration controls.
- **Best if** the bar is **"closest structural analog to Sierpinski"**:
  recursive subdivision + per-room modulators + line-work + signal-
  driven modulation. This is Sierpinski's full method translated to
  text-grid output.

## Cross-candidate invariants

All three options require:

1. **Producer-schema v2** carrying a structured composition, not a
   single text blob. `schema_version: 2` field; v1 producer output stays
   on the v1 fallback path so deploying the new renderer doesn't break
   in-flight calls.
2. **`» hapax «` v1 fallback preserved.** When the producer hasn't
   adopted v2 yet, or returns invalid v2, fall back to current renderer.
3. **Anti-pattern guards still apply.** No emoji
   (`AntiPatternKind.emoji`), no faces (`AntiPatternKind.face` Pearson <
   0.6 face-correlation). The HARDM principle — `feedback_no_blinking_homage_wards`
   plus the "no eyes/mouths/expressions" governance — applies to GEM
   the same way it applies to HARDM. Smooth envelopes only.

## Recommended ordering (no operator override)

Ship **A first**. It is the lowest-cost, lowest-risk surface change
that clears the multi-region + signal-modulation criteria and validates
the v2 producer schema. Treat **C as Phase 2 ascent**: once v2
producer + renderer + signal bindings are validated under A, add the RD
substrate (B) and the nested box-draw rooms incrementally. **B alone**
is also acceptable as Phase 1 if the operator weights the
algorithmic-depth criterion most heavily — the v2 schema and renderer
plumbing carry over to A or C.

## Open questions for operator

1. **A vs B vs C** as Phase 1 target?
2. **Render rate**: 12 Hz (default cadence, lower CPU) vs 24 Hz (smoother
   modulation, higher CPU)? Affects cost numbers above.
3. **B substrate brightness ceiling**: how bright can the RD field go
   before it competes with the content mask for legibility? Needs a
   visual-test pass on the livestream-output canvas.

Once operator picks, next step is the spec (`docs/superpowers/specs/`)
+ plan (`docs/superpowers/plans/`) for the chosen Phase 1 candidate.
