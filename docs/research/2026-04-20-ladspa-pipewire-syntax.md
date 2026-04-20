---
date: 2026-04-20
author: delta
status: unblock research
related:
  - docs/research/2026-04-20-audio-normalization-ducking-strategy.md
  - config/pipewire/voice-fx-chain.conf
unblock-for: task #209, then audio-normalization plan Phase A + B
---

# LADSPA Plugin Syntax in PipeWire filter-chain

## §1. TL;DR

The prior delta attempt at loading an LADSPA plugin in `voice-fx-chain
.conf` failed with `could not load mandatory module
libpipewire-module-filter-chain`. **Root cause (likely):** the node
`type` keyword was passed as `type = ladspa` (bare), but PipeWire's
filter-chain `ladspa` plugin type expects a `plugin` field naming
the `.so` file path **and** a `label` field naming the plugin label
inside the shared object. Missing either of those surfaces as a
module-load failure at the context level, not the node level, which
is why the whole filter-chain module was rejected.

The correct syntax:

```
{ type = ladspa
  plugin = "sc4_1882"           # or full path: "/usr/lib/ladspa/sc4_1882.so"
  label = "sc4"                 # the label inside the .so (NOT the filename)
  name = "comp_l"               # PipeWire-local node name, optional but
                                # strongly recommended for inputs/outputs
                                # cross-referencing below
  control = {                   # per-plugin control defaults
    "RMS/peak" = 0.5
    "Attack time (ms)" = 1.5
    "Release time (ms)" = 150
    "Threshold level (dB)" = -18
    "Ratio (1:n)" = 3
    "Knee radius (dB)" = 3.5
    "Makeup gain (dB)" = 0
  }
}
```

## §2. Plugin label vs filename

**The trap:** the filename `sc4_1882.so` is what lives on disk; the
`label` inside is what PipeWire uses to resolve the plugin from the
`.so`. They're often different.

How to inspect a plugin's labels:

```
listplugins /usr/lib/ladspa/sc4_1882.so
# or
analyseplugin /usr/lib/ladspa/sc4_1882.so | head -20
```

`listplugins` is from `ladspa-sdk`. The leftmost column is the label.
For `sc4_1882.so`, the label is `sc4` (the C1 Compressor by Steve
Harris). `sc1_1425.so` → label `sc1`; `sc2_1426.so` → label `sc2`;
`fast_lookahead_limiter_1913.so` → label `fastLookaheadLimiter`.

## §3. Plugin path resolution

PipeWire searches in this order:

1. Exact path if the `plugin` value starts with `/`.
2. `LADSPA_PATH` environment variable (colon-separated).
3. `~/.ladspa/`
4. `/usr/lib/ladspa/` and `/usr/local/lib/ladspa/`.

On CachyOS, the default `/usr/lib/ladspa/` is populated by the
`ladspa-plugins` or `swh-plugins` packages. Our workstation has
103 plugins installed including the full Steve Harris set
(`sc1`..`sc4`, `fast_lookahead_limiter`, `hard_limiter`, etc.).

For brittle-proofing, prefer short plugin names (resolved via
default path) over absolute paths — it decouples the conf from the
distro's layout.

## §4. A working Phase A / B config

The original failed attempt tried to drop `sc4` into the existing
voice-fx-chain filter graph next to biquad nodes. PipeWire allows
mixing `builtin` and `ladspa` node types in the same graph as long
as the `inputs`/`outputs` ports wire up correctly.

Proposed config for the audio-normalization plan's Phase A
(compressor) + Phase B (loudness-target limiter):

```
context.modules = [
    { name = libpipewire-module-filter-chain
      args = {
          node.name = "hapax-loudnorm"
          node.description = "Hapax TTS loudness normalisation"
          media.class = "Audio/Sink"
          audio.rate = 48000
          audio.channels = 2
          audio.position = [ FL FR ]

          filter.graph = {
              nodes = [
                  # SC4: full-frequency compressor (Steve Harris).
                  # Controls per analyseplugin output; -18 dB threshold
                  # + 3:1 ratio + 1.5 ms attack + 150 ms release is
                  # broadcast-voice starting point.
                  { type = ladspa
                    plugin = "sc4_1882"
                    label = "sc4"
                    name = "comp_l"
                    control = {
                      "RMS/peak" = 0.5
                      "Attack time (ms)" = 1.5
                      "Release time (ms)" = 150
                      "Threshold level (dB)" = -18
                      "Ratio (1:n)" = 3
                      "Knee radius (dB)" = 3.5
                      "Makeup gain (dB)" = 0
                    } }
                  { type = ladspa
                    plugin = "sc4_1882"
                    label = "sc4"
                    name = "comp_r"
                    control = {
                      "RMS/peak" = 0.5
                      "Attack time (ms)" = 1.5
                      "Release time (ms)" = 150
                      "Threshold level (dB)" = -18
                      "Ratio (1:n)" = 3
                      "Knee radius (dB)" = 3.5
                      "Makeup gain (dB)" = 0
                    } }

                  # Fast-lookahead limiter (Steve Harris).
                  # -1 dB ceiling prevents inter-sample peak clipping
                  # at the broadcast encoder.
                  { type = ladspa
                    plugin = "fast_lookahead_limiter_1913"
                    label = "fastLookaheadLimiter"
                    name = "limit_l"
                    control = {
                      "Input gain (dB)" = 0.0
                      "Limit (dB)" = -1.0
                      "Release time (s)" = 0.05
                    } }
                  { type = ladspa
                    plugin = "fast_lookahead_limiter_1913"
                    label = "fastLookaheadLimiter"
                    name = "limit_r"
                    control = {
                      "Input gain (dB)" = 0.0
                      "Limit (dB)" = -1.0
                      "Release time (s)" = 0.05
                    } }
              ]
              inputs  = [ "comp_l:Input"  "comp_r:Input"  ]
              outputs = [ "limit_l:Output" "limit_r:Output" ]
              links = [
                  { output = "comp_l:Output"  input = "limit_l:Input" }
                  { output = "comp_r:Output"  input = "limit_r:Input" }
              ]
          }
      }
    }
]
```

Notes:
- Per-channel plugin instances (`_l` / `_r`) are mandatory — SC4 and
  fast_lookahead_limiter are mono plugins. The built-in `builtin
  mixer` approach only works for pass-through gain, not stereo
  compression.
- `inputs` are the plugin ports that receive the filter-chain's
  entry signal; `outputs` are what leaves. `links` wires internal
  edges between nodes.
- `Input`/`Output` port names come from the plugin; match
  `analyseplugin`'s output capitalisation exactly (case-sensitive).

## §5. Verify workflow

Apply the conf + reload:

```
cp ladspa-test.conf ~/.config/pipewire/pipewire.conf.d/
systemctl --user restart pipewire pipewire-pulse wireplumber

# Verify the sink appeared:
pw-cli ls Node | grep -i hapax-loudnorm

# Probe the filter-chain module loaded:
journalctl --user -u pipewire -n 30 | grep -i filter-chain
```

If the module fails to load, `journalctl` prints a specific plugin
resolution error (missing label, missing .so, missing control name).
The original failure logged `could not load mandatory module` which
is the parent-level rollup; the specific error is in the plugin-load
line right before it.

## §6. Unblocking audio-normalization Phase A + B

Plan doc `docs/research/2026-04-20-audio-normalization-ducking-
strategy.md` Phase A is the compressor + limiter filter-chain. The
§4 config above is the drop-in for that phase. Phase B (LUFS target
metering) ships alongside the `mixquality/loudness` sub-score in
`shared/mix_quality/` (task #207 Phase 1) — pyloudnorm-based EBU
R128 measurement on the monitor port, independent of the filter-
chain graph.

Net: task #209 unblocks task #207 Phase 1 (loudness meter) + Phase
A of the normalization plan. No further research needed; operator
can apply `voice-fx-loudnorm.conf` when ready.
