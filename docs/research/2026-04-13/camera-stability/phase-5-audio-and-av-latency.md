# Phase 5 — Audio and End-to-End A/V Latency

**Session:** beta, camera-stability research pass (queue 022)
**Status:** **PARTIALLY DEFERRED.** Audio steady state captured from `pw-top` / `wpctl`. Speech-to-RTMP latency, A/V sync delta, and pipewire-restart recovery characterization are not measurable autonomously in this session.

## Why partially deferred

1. **No live RTMP receiver.** `systemctl --user is-active mediamtx.service` returns `inactive`. The Phase 5 of the camera resilience epic shipped `rtmp_output.py` writing to `rtmp://127.0.0.1:1935/studio`, but MediaMTX is the receiver and it is currently off. There is no HLS manifest or RTMP egress stream to measure latency against. Two options for a future session: (a) start MediaMTX and run through its HLS output, or (b) if the operator is still using OBS as the RTMP encoder (parallel path, not the epic's native path), probe OBS's HLS output directly.

2. **Operator-action required for click-track measurements.** A speech-to-RTMP latency number needs a known event at the source side (operator clap, tone burst from a visible prop) and a corresponding observation at the RTMP output side. Beta cannot generate a physically audible event; only the operator can.

3. **Restart-class test (`systemctl --user restart pipewire`) is coordination-sensitive.** Restarting pipewire during an active livestream will glitch the operator's real output; restarting it while the compositor + daimonion are trying to use it can cascade failures. Not appropriate without operator supervision.

What IS captured here: audio pipeline steady-state observation, the audio path topology from source code, and the instrumentation surface for each measurable number — so the next session can run the measurements against a known baseline.

## Audio pipeline topology (from source)

Reading `agents/studio_compositor/rtmp_output.py` (the epic's Phase 5 native RTMP bin):

```text
pipewiresrc target-object=<audio_target> \
  → audioconvert \
  → voaacenc bitrate=<target_kbps> \
  → aacparse \
  → flvmux name=mux [← nvh264enc video path] \
  → rtmp2sink location=rtmp://127.0.0.1:1935/studio
```

`audio_target` is a `pipewiresrc target-object` node name passed in at construction time from `compositor.py`. The compositor's voice-FX chain (see council CLAUDE.md § "Voice FX Chain") installs a `filter-chain` with a `hapax-voice-fx-capture` sink that hapax-daimonion writes TTS into. Whether the compositor's RTMP audio bin listens to `hapax-voice-fx-capture` or to the raw Yeti mic node depends on `compositor.py`'s construction arg, which depends on the compositor config for audio routing — verify before running.

**`[inferred]`** Audio rate mismatch notes from Phase 1's dmesg scan (18 `current rate 16000 is different from the runtime rate 48000` lines across BRIO mics on buses 5-4, 6-2, 8-3) are **BRIO integrated microphones**, not the primary studio mic chain. If the compositor's RTMP bin is pulling from `hapax-voice-fx-capture` (filter-chain sink), the BRIO mic rate mismatches are irrelevant; if it is pulling raw from a BRIO mic node, those mismatches would show up as xruns on voaacenc and glitches in the RTMP output. The Phase 5 measurement is latency, not glitches, so this is a secondary concern — flag for a future audio-quality pass.

## Audio steady-state observation

From `wpctl status` at 16:25 CDT:

- PipeWire 1.6.2 live
- 300+ client entries — audio graph is well-populated
- Active producers include `waybar`, `pacat` (multiple), `pw-cat` (multiple, 16 kHz mono capture clients — these are daimonion's STT pipeline and the contact-mic Cortado capture), `Lavf62.12.100` (compositor's pipewiresrc, two distinct clients — video + audio paths?), `KDE Connect Daemon`, `xdg-desktop-portal-hyprland`
- No visible xrun warnings in the `wpctl` output
- No clock-drift warnings in the `wpctl` output

**Reproduction commands:**
```bash
# Full pipewire graph
wpctl status

# Live node/port/link inspection (per-client latency + buffer size)
pw-top

# One-shot audio metrics from pipewire introspection
wpctl inspect <node_id>
```

## End-to-end latency — measurement plan for next session

### Speech-to-RTMP latency

**Precondition:** MediaMTX is running AND RTMP output is attached on the compositor.

```bash
# 1. Start MediaMTX if needed
systemctl --user start mediamtx

# 2. Confirm the compositor's RTMP bin is attached (look for "rtmp_" prefixed elements in gst-dot graph, or increment the rebuild counter and watch it tick)
curl -s http://127.0.0.1:9482/metrics | grep '^studio_rtmp_connected'

# 3. Start reading HLS manifest (MediaMTX exposes HLS)
watch -n 0.1 'curl -s http://127.0.0.1:8888/studio/index.m3u8 | head -20'
```

Then the operator claps at a known wall-clock time, observed from a visible source (e.g., webcam preview). The HLS segment containing the clap arrives N seconds later. Measure N. Repeat 3 times for dispersion.

### Video-to-audio A/V sync at RTMP

Same setup, but the operator provides both an audible clap and a visible light flash (e.g., a hand sweeping across the BRIO with a bright LED). At the HLS side, use `ffprobe -show_frames -select_streams a` and `ffprobe -show_frames -select_streams v` on the output segment to find the clap's audio peak frame and the flash's video peak frame. Delta gives the A/V sync offset at the RTMP output boundary. Repeat 3 times.

### Pipewire-restart recovery

```bash
# Mid-stream
systemctl --user restart pipewire pipewire-pulse wireplumber
sleep 5
# Inspect the compositor's reaction
curl -s http://127.0.0.1:9482/metrics | grep '^studio_rtmp_encoder_errors_total'
curl -s http://127.0.0.1:9482/metrics | grep '^studio_rtmp_bin_rebuilds_total'
journalctl --user -u studio-compositor.service --since="1 min ago" | grep -i 'rtmp\|voaacenc\|pipewiresrc'
```

Expected behavior: `rtmp2sink` receives a downstream EOS or error from the restarted pipewire source; the bus handler routes this via the `rtmp_` prefix filter to the RTMP bin only; the bin is torn down and rebuilt; `studio_rtmp_bin_rebuilds_total{endpoint="youtube"}` increments; video-side pipelines are undisturbed. The end-to-end observable is the duration of the audio gap in the RTMP output — measure by listening to the HLS output or by looking at `ffprobe` pts gaps.

### Stimmung fortress-mode sink swap

If the operator has fortress-mode wired for studio-streaming use, exercise it mid-stream and measure the audio glitch at the RTMP output. **Not measurable autonomously — beta does not know the operator's fortress-mode hotkey or the target audio sink topology.** Defer to operator-supervised run.

## What beta CAN claim right now

| signal | value | source |
|---|---|---|
| PipeWire live + healthy | yes | `wpctl status` |
| Pipewire xruns in `wpctl status` output | none visible | same |
| Compositor connected to pipewire | **unknown** on PID 2529279 — two `Lavf62.12.100` entries in wpctl suggest the `pipewiresrc` side of the pipeline is attached; no explicit confirmation that the RTMP bin is built | indirect |
| `studio_rtmp_connected{endpoint="youtube"}` | **series absent from live scrape** — means `compositor.py` has not hit the `set(1)` or `set(0)` line yet, i.e. the RTMP bin has never been attached on this PID since restart | Phase 4 §series classification |

**Inference from the combination:** on PID 2529279 the compositor is not currently streaming via the epic's native RTMP output path. Either OBS is still doing the egress (likely, given MediaMTX is inactive), or the RTMP bin is configured off entirely for this run. Without the native bin attached, all of Phase 5's latency numbers would characterize OBS, not the compositor's design — which is a different research question from the epic's validation.

## Follow-up tickets

1. **`research(compositor): complete Phase 5 A/V latency characterization post-FINDING-1-fix`** — execute the three latency measurements above against the epic's native RTMP path. Requires: (a) MediaMTX running, (b) the compositor's RTMP bin attached, (c) operator supervision for the clap/flash events. Assign to beta + operator. *(Severity: medium. Affects: claim validity that the epic's native RTMP output is at parity with the previous OBS-based path.)*

2. **`fix(compositor): confirm-or-document whether the epic's native RTMP bin is currently in production use`** — the epic is merged but MediaMTX is inactive and `studio_rtmp_connected` is absent from the live scrape, which is inconsistent with "native RTMP is shipping." Either (a) native RTMP is not yet the primary egress path despite the epic's merge, or (b) it is configured off in the current compositor run, or (c) it is active but something is preventing the `set(1)` call. Needs a one-sentence answer in the epic handoff doc. *(Severity: medium. Affects: epic retrospective accuracy + future research clarity.)*

3. **`research(audio): characterize BRIO mic rate mismatches as a separate audio-quality question`** — 18 kernel log lines of `current rate 16000 is different from the runtime rate 48000` on BRIO mics across buses 5-4 / 6-2 / 8-3. Not a latency concern per se but worth confirming whether any of them feed the compositor's audio path. *(Severity: low. Affects: audio quality only if BRIO mics are upstream of flvmux.)*

## Acceptance check

- [x] Audio pipeline topology captured from source.
- [x] Audio steady-state sanity check via `wpctl status`.
- [ ] Speech-to-RTMP latency with 3-run dispersion. **Deferred.**
- [ ] Video-to-audio sync delta at RTMP with 3-run dispersion. **Deferred.**
- [ ] Pipewire-restart recovery time measured. **Deferred.**
- [x] Stimmung fortress-mode sink-swap glitch characterization plan documented. Execution deferred.
- [x] Inference that the epic's native RTMP path may not be the primary egress on this PID, flagged as a clarification question for alpha / epic handoff author.
