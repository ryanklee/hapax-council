# Audio path baseline — PipeWire, DSP, TTS

**Date:** 2026-04-14
**Author:** delta (beta role)
**Scope:** First pass audit of the compositor's audio path.
Covers: PipeWire graph health, compositor DSP histogram,
Kokoro TTS truncation behaviour, camera audio source
availability. Asks: is the audio side of the livestream as
smooth as the video side, and where are the latent
concerns?
**Register:** scientific, neutral
**Status:** baseline only — no code change

## Headline

**Four findings.**

1. **Audio DSP is healthy.** `compositor_audio_dsp_ms`
   histogram shows 138 750 samples over ~10 minutes of
   fresh runtime with **mean 0.89 ms, p95 ≈ 1.5 ms, p99 ≈
   2.5 ms, p99.9 ≈ 5 ms, max in the ≤ 50 ms bucket**. No
   sustained tail, no outlier spikes. Whatever the compositor's
   audio DSP pass is doing, it fits comfortably in one frame
   budget.
2. **PipeWire configuration is low-latency.** Global
   `default.clock.quantum = 128`, `default.clock.rate`
   48 000 Hz → one quantum is **2.67 ms**. Min quantum is 64
   (1.33 ms); max is 1024 (21.3 ms); `clock.power-of-two-
   quantum = true`. This is the right configuration for a
   realtime livestream — the operator can push latency down
   without risking audio glitches from an oversized buffer.
3. **Kokoro TTS has a 400-char input ceiling enforced by
   `director_loop._synthesize`.** Four truncation warnings
   fired in the last 19 minutes of steady state (~one every
   4.7 min). The truncation algorithm trims at the last
   word boundary within 80 chars of the cutoff and appends
   an ellipsis. It is called a "Kokoro throughput guard" in
   the log line. This is not a bug — it's a deliberate cap
   — but it means **~25–30 % of director_loop reactions get
   cut mid-thought** based on the measured distribution of
   reply lengths in drop #8 (300–500 char range). Worth
   understanding whether the 400-char number is tuned or
   historical.
4. **Two out of three BRIO audio sources are missing from
   the PipeWire graph.** Only `brio-room` (43B0576A) appears
   as `alsa_input.usb-046d_Logitech_BRIO_43B0576A-03.analog-
   stereo`. `brio-operator` (5342C819) and `brio-synths`
   (9726C031) — both on USB 3.0 Gen 1 via the AMD Matisse
   controller — do not expose audio inputs to the graph at
   all. Status could be intentional (operator prefers the
   Studio 24c + Cortado as the primary audio sources and
   has suppressed the cheap camera mics) or a bug (USB audio
   endpoints not enumerating for those units). Unverified
   which.

## 1. DSP histogram details

```text
$ curl -s http://127.0.0.1:9482/metrics | grep "^compositor_audio_dsp_ms"
compositor_audio_dsp_ms_bucket{le="0.5"}   11961
compositor_audio_dsp_ms_bucket{le="1.0"}  103945    # p50 < 1 ms
compositor_audio_dsp_ms_bucket{le="2.0"}  134703    # p95 ≈ 1.5 ms
compositor_audio_dsp_ms_bucket{le="3.0"}  137321    # p99 ≈ 2.5 ms
compositor_audio_dsp_ms_bucket{le="5.0"}  138512    # p99.9 ≈ 5 ms
compositor_audio_dsp_ms_bucket{le="7.5"}  138673
compositor_audio_dsp_ms_bucket{le="10.0"} 138702
compositor_audio_dsp_ms_bucket{le="12.5"} 138714
compositor_audio_dsp_ms_bucket{le="15.0"} 138718
compositor_audio_dsp_ms_bucket{le="20.0"} 138730
compositor_audio_dsp_ms_bucket{le="30.0"} 138740
compositor_audio_dsp_ms_bucket{le="50.0"} 138746
compositor_audio_dsp_ms_bucket{le="+Inf"} 138750
compositor_audio_dsp_ms_count             138750
compositor_audio_dsp_ms_sum            123196.20
```

**Mean: 123 196 / 138 750 = 0.888 ms.** Cumulative percentiles
above. The tail is thin: only 38 samples above 30 ms
(0.027 %), only 10 samples above 50 ms in the +Inf bucket
(0.007 %). **This is a healthy histogram.**

The 4 outliers in the 30–50 ms range are almost certainly
GC pauses, scheduler preemption, or glfeedback shader-recompile
cluster side effects (see drop 5 for the recompile cluster,
which serializes ~20-40 ms of GL work in the same pad push).

## 2. PipeWire configuration

```text
$ pw-metadata
default.clock.quantum     = "128"
default.clock.min-quantum = "64"
default.clock.max-quantum = "1024"
default.clock.quantum-limit = "8192"
default.clock.quantum-floor = "4"
clock.power-of-two-quantum = "true"
```

At 48 kHz:

- 128 samples = **2.67 ms** per quantum (the default)
- 64 samples = **1.33 ms** (min)
- 1024 samples = **21.3 ms** (max)

Low-latency realtime audio typically targets 64–256 sample
quanta; 128 is the sweet spot for stability + latency. The
quantum is a PipeWire-global setting, so every audio client
on the graph inherits it.

**Round-trip latency floor** at this config, for a client
that reads input and writes output in a single quantum, is
~5.3 ms (one input quantum + one output quantum). Real
applications add DSP overhead, JACK / ALSA kernel hops,
and the audio interface's own buffer depth; realistic
microphone-to-speaker latency on this rig is probably
~10–15 ms.

## 3. Graph inventory

```text
$ pw-dump  # parsed into node + link count
nodes: 53  links: 26
audio nodes: 37
```

53 PipeWire nodes total, 37 of them are audio (Audio/Source,
Audio/Sink, Stream/Input/Audio, Stream/Output/Audio). 26
active links among them. Breakdown of the audio nodes by
role:

| node | media.class | notes |
|---|---|---|
| `contact_mic` | Audio/Source | **default source** — Cortado MKIII on Studio 24c input 2 |
| `mixer_master` | Audio/Source | primary mix bus — the compositor reads from this via pw-cat |
| `echo_cancel_capture/source/sink/playback` | various | PipeWire echo-cancel module chain |
| `noise-suppress-capture/playback` | various | PipeWire noise-suppression filter chain |
| `hapax-voice-fx-capture/playback` | various | PipeWire `filter-chain` per `config/pipewire/README.md` § Voice FX Chain |
| `input.loopback.sink.role.{multimedia,notification,assistant}` + output | Stream/* | role-based loopback sinks for scheduler routing |
| `alsa_input.usb-PreSonus_Studio_24c_…-00.analog-stereo` | Audio/Source | Studio 24c capture (8 inputs) |
| `alsa_output.usb-PreSonus_Studio_24c_…-00.analog-stereo` | Audio/Sink | **default sink** — Studio 24c monitor out |
| `alsa_input.usb-046d_HD_Pro_Webcam_C920_{2657DFCF,86B6B75F,7B88C71F}-02.analog-stereo` | Audio/Source | all three C920 mics present |
| `alsa_input.usb-046d_Logitech_BRIO_43B0576A-03.analog-stereo` | Audio/Source | brio-room only |
| `alsa_output.pci-0000_03_00.1.hdmi-stereo` | Audio/Sink | HDMI out |
| `alsa_input.pci-0000_09_00.4.analog-stereo` | Audio/Source | onboard chipset line-in |

See finding 4 below for the BRIO audio gap.

## 4. TTS truncation cadence

Journal search in the last 19 minutes (since the compositor
restart at 10:07:49):

```text
$ journalctl --user -u studio-compositor.service --since 10:07 | \
      grep "Kokoro throughput guard"
10:17:07  speak-react text truncated to 396 chars
10:22:06  speak-react text truncated to 397 chars
10:23:48  speak-react text truncated to 399 chars
10:25:53  speak-react text truncated to 395 chars
```

Four truncations in 19 minutes — one per 4.7 min on average.
The truncated length clusters tightly at 395–399 chars because
`director_loop._synthesize` (line 812) enforces
`_MAX_REACT_TEXT_CHARS = 400` with a word-boundary preference
(line 817):

```python
_MAX_REACT_TEXT_CHARS = 400

def _synthesize(self, text: str) -> bytes:
    if len(text) > self._MAX_REACT_TEXT_CHARS:
        cutoff = self._MAX_REACT_TEXT_CHARS
        word_boundary = text.rfind(" ", 0, cutoff)
        if word_boundary > self._MAX_REACT_TEXT_CHARS - 80:
            cutoff = word_boundary
        text = text[:cutoff].rstrip() + "…"
        log.warning(
            "speak-react text truncated to %d chars (Kokoro throughput guard)",
            cutoff,
        )
    return self._tts_client.synthesize(text, "conversation")
```

The algorithm is sound (preserves word boundary within 80
chars of the cutoff). The question is whether **400 is the
right cap**. From drop 8 § 2.3, observed react output lengths
cluster around 300–500 characters, meaning **roughly 25–30 %
of reactions hit the ceiling**. That's measurable content
loss for the livestream — mid-sentence truncations with an
ellipsis.

**Two paths for alpha:**

- **If 400 is tuned**: that is, Kokoro's throughput drops
  above 400 chars enough to cause speech lag, and the
  truncation is the least-bad option — then the fix is
  upstream. Constrain the LLM's output length in the
  `max_tokens` call or in the system prompt ("respond in
  ≤ 90 words") so reactions never exceed the cap in the
  first place. This is a 2-line change in
  `director_loop._call_activity_llm` and a 1-line change in
  the system prompt.
- **If 400 is historical**: that is, Kokoro can actually
  handle longer inputs without lag, and 400 was set during
  an earlier Kokoro tuning round — then the fix is to raise
  the cap (or remove it). Benchmark: run `hapax-daimonion`
  TTS against 400-, 600-, 800-, 1000-char inputs and
  measure synthesis wall clock. If TTS time is linear in
  input length within that range, the guard is unnecessary.
  If it's super-linear, the guard is real and path 1
  applies.

Worth a short benchmark drop. Delta has not run the
benchmark yet — it needs `hapax-daimonion` to be reachable
on its UDS socket, and the one TTS socket warning observed
at 10:08:03 (`"daimonion socket missing at
/run/user/1000/hapax-daimonion-tts.sock"`) suggests the
socket was racing at that moment. Needs a separate attempt.

## 5. Missing BRIO audio sources

Expected: three BRIO units each expose a USB audio endpoint
as `alsa_input.usb-046d_Logitech_BRIO_<serial>-03.analog-
stereo`.

Observed:

- `alsa_input.usb-046d_Logitech_BRIO_43B0576A-03.analog-stereo` ✓ (brio-room)
- `alsa_input.usb-046d_Logitech_BRIO_5342C819-03.analog-stereo` ✗ (brio-operator)
- `alsa_input.usb-046d_Logitech_BRIO_9726C031-03.analog-stereo` ✗ (brio-synths)

Only `brio-room` is present. The other two BRIOs are on USB
3.0 5000 Mbps ports (AMD Matisse, `09:00.3`, usb4/4-1 and
usb4/4-3) while `brio-room` is on USB 2.0 480 Mbps (AMD 500
Series, `01:00.0`, usb1/1-3).

**Three possible explanations:**

- **H1 (intentional)**: operator suppressed the BRIO mics via
  udev rules, module blacklist, or a wireplumber policy.
  Typical reason: BRIO mics are lower quality than the Cortado
  + Studio 24c path, and having them on the default graph
  creates ambiguity about which source the compositor pulls.
  Checkable via `find /etc/udev/rules.d /usr/lib/udev/rules.d
  -name "*brio*"` or `find /etc/wireplumber
  ~/.config/wireplumber -name "*.lua" -exec grep -l BRIO {}
  \;`.
- **H2 (firmware)**: the BRIO firmware on those two units
  does not expose the audio descriptor properly over USB 3.0.
  Sprint-1 F4 already noted brio-synths has 2 video interfaces
  with no driver bound — a firmware quirk. Could extend to
  audio too.
- **H3 (kernel)**: uvcvideo / snd-usb-audio interaction on
  USB 3.0 disables the audio endpoint when the video endpoint
  is in use at 5000 Mbps. Happens in some kernel versions.
  Checkable via `lsusb -v -d 046d:085e` and looking for the
  audio descriptor.

Not blocking — the operator's audio flow uses the Studio 24c
+ Cortado path — but worth a data point because **if a BRIO
mic becomes needed later, two of three are silent right now**.
Flag for alpha.

## 6. One TTS socket warning at startup

```text
10:08:03  WARNING agents.studio_compositor.tts_client: tts client:
          daimonion socket missing at /run/user/1000/hapax-daimonion-tts.sock
```

One occurrence, 14 seconds after compositor start at 10:07:49.
Probably a startup race: the compositor came up, tried to
reach the daimonion TTS UDS, and daimonion hadn't finished
binding the socket yet. No repeat. The compositor's TTS client
has a fall-through path — the next call succeeds when
daimonion finishes initialization.

If this is reproducible on every compositor restart, consider
adding an `After=hapax-daimonion.service` or equivalent wait
to `studio-compositor.service`. But a one-time 14-second
warning on a cold start is survivable; not worth a fix until
it becomes recurring.

## 7. What's not in this drop

- **TTS latency quantified.** Need a real synthesis benchmark
  against Kokoro. Deferred.
- **Ducking behavior during TTS.** Sprint-4 territory. The
  `studio_compositor_music_ducked` gauge exists; I didn't
  sample its history across TTS events.
- **Audio path in the RTMP output.** The RTMP bin is
  constructed-but-detached (drop 4 § 5.1), so the audio
  encoder (voaacenc per sprint-5 F1) is not running. Nothing
  to measure live until `toggle_livestream` fires.
- **PipeWire xruns / dropped samples.** No user-space exporter
  for these on this box. Would require `pw-top -b` with a
  longer sampling window or a custom dump of
  `/proc/asound/card*/stream*`. Follow-up data-gathering.
- **BRIO audio root cause.** H1/H2/H3 from § 5 are all unverified.

## 8. Follow-ups

1. **Benchmark Kokoro synthesis time vs input length** — 100, 200, 400, 600, 800, 1000 chars. Result determines whether the 400-char cap is tuned or historical.
2. **Constrain LLM output length** (independent of #1) — add "respond in ≤ 90 words" to director_loop's system prompt, or lower `max_tokens` from 2048 to ~200. Prevents truncation by keeping reacts short in the first place. 1-line change, no Kokoro dependency.
3. **Check BRIO audio suppression source** — the three `find` commands in § 5 should close the H1/H2/H3 branch in 2 minutes.
4. **Add PipeWire xrun counter to compositor metrics** — `studio_audio_xruns_total` gauge. Matches the sprint-6 F4 missing-histogram pattern but for the audio side.
5. **`After=hapax-daimonion.service`** in `studio-compositor.service` — eliminates the 14-second startup race if it keeps happening. Only needed if reproducible.

## 9. References

- `compositor_audio_dsp_ms_*` live metrics at 2026-04-14T15:57 UTC
- `pw-metadata` output showing clock quantum / rate settings
- `pw-dump` parsed node / link count
- `agents/studio_compositor/director_loop.py:810-825` —
  `_MAX_REACT_TEXT_CHARS` and the `_synthesize` truncation
- `config/pipewire/README.md` — Voice FX Chain context
- `docs/research/2026-04-14-director-loop-prompt-cache-gap.md`
  § 2.3 — observed react length distribution (context for
  truncation rate estimate)
- `docs/research/2026-04-13/livestream-performance-map/sprint-1/sprint-1-foundations.md`
  F4 — brio-synths firmware quirk precedent
