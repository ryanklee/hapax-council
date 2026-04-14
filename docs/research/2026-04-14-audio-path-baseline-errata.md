# Audio path baseline — ERRATUM

**Date:** 2026-04-14
**Author:** delta (beta role)
**Supersedes:** `2026-04-14-audio-path-baseline.md` finding 4
**Register:** scientific, neutral
**Status:** correction only — no code change

## Summary

Finding 4 of the earlier drop said "only brio-room exposes a
PipeWire audio source; brio-operator and brio-synths are
absent from the graph." That claim is wrong and was caused by
a measurement error — I capped the `pw-top -b -n 1` output at
40 lines in the original audit and the other two BRIOs
register with very high PipeWire IDs (5285 and 5298) that
fell below the cutoff. All three BRIO audio sources exist and
are configured with the correct profile.

The other three findings in the earlier drop (audio DSP
histogram, PipeWire quantum configuration, Kokoro TTS
truncation cadence) are unaffected and stand.

## 1. Corrected state — all three BRIO audio sources present

```text
$ pactl list sources short | grep -i brio
 127   alsa_input.usb-046d_Logitech_BRIO_43B0576A-03.analog-stereo  s16le 2ch 48000Hz  SUSPENDED
5285   alsa_input.usb-046d_Logitech_BRIO_5342C819-03.analog-stereo  s16le 2ch 48000Hz  SUSPENDED
5298   alsa_input.usb-046d_Logitech_BRIO_9726C031-03.analog-stereo  s16le 2ch 48000Hz  SUSPENDED
```

All three BRIO audio capture nodes:

- exist in PipeWire
- have matching profile `input:analog-stereo` confirmed via
  `pactl list cards`
- are format-identical (`s16le 2ch 48000Hz`)
- are currently in `SUSPENDED` state (no active consumer)

The `SUSPENDED` state is normal for sources with no active
reader; PipeWire wakes the ALSA driver only when a sink
connects. brio-room was also `SUSPENDED` at the same sample,
so "suspended" is not what drop #11 was mistaking for
"missing."

## 2. ALSA confirmation (not a regression)

```text
$ cat /proc/asound/cards | grep BRIO
 1 [BRIO           ]: USB-Audio - Logitech BRIO
                      Logitech BRIO at usb-0000:09:00.3-3, super speed
 5 [BRIO_1         ]: USB-Audio - Logitech BRIO
                      Logitech BRIO at usb-0000:09:00.3-1, super speed
 9 [BRIO_2         ]: USB-Audio - Logitech BRIO
                      Logitech BRIO at usb-0000:01:00.0-3, high speed
```

The kernel has enumerated all three BRIO audio endpoints —
two on AMD Matisse at USB 3.0 (super speed) and one on AMD
500 Series at USB 2.0 (high speed). No firmware quirk, no
driver rejection. The H2 and H3 hypotheses (firmware variance,
kernel USB 3 audio disable) from drop #11 § 5 are **both
refuted**.

## 3. The late-ID registration is real

PipeWire IDs are monotonically assigned. brio-room is at
ID 127 (created early) while brio-operator and brio-synths
are at IDs 5285 and 5298 — ~5 000 IDs later, implying ~5 000
object creations / destructions happened between the startup
registration of brio-room and the eventual registration of
the USB 3.0 BRIOs.

That means **something registered the USB 3.0 BRIO audio
cards late in the session**, not at PipeWire startup. Three
candidates:

- **USB hot-plug event.** If the BRIOs bus-kicked and
  re-enumerated (kernel `device descriptor read/64, error
  -71` — the known hardware-level issue that drove the
  camera 24/7 resilience epic), they'd re-register audio
  and video endpoints. The camera FSM would capture the
  video side as a `reconnect` transition; the audio side
  would just re-appear in PipeWire.
- **wireplumber profile switch.** If wireplumber initially
  assigned `off` to the USB 3.0 BRIO audio profiles and
  later switched to `input:analog-stereo`, new nodes would
  be created at that moment. The drop #11 `pactl list
  cards` output confirmed all three are now on
  `input:analog-stereo`, but the moment of the switch isn't
  captured.
- **Compositor restart cascade.** Per the sprint-5 delta
  audit § 8.1, several services restarted at 10:07:49 via
  `hapax-rebuild-services.timer`. If any of them held
  exclusive access to a BRIO audio endpoint (unlikely but
  possible), releasing it could trigger re-registration.

**Delta cannot distinguish these three from the live state.**
The simplest way to identify which is responsible is to
monitor the wireplumber / pipewire journal for `Card added`
events and correlate timestamps.

## 4. Corrected follow-ups

Removing the "BRIO audio missing" follow-up. What's left
from drop #11 § 8:

- **Benchmark Kokoro synthesis time vs input length** (unchanged,
  still the highest-value audio follow-up)
- **Constrain LLM output length** (unchanged)
- **Add PipeWire xrun counter to compositor metrics** (unchanged)
- **`After=hapax-daimonion.service`** (unchanged)

New item added by this erratum:

- **Find what registered the USB 3.0 BRIO audio cards at IDs
  5285/5298.** If bus-kick, the camera 24/7 epic already
  captures the video side as a recovery transition; the
  audio side is implicit. If wireplumber late-attach, the
  fix is an on-demand profile policy and the late attach
  is expected. Investigation is a single `journalctl`
  search for `wireplumber`/`pipewire` `card added` events
  around the process start time.

## 5. What the original drop got right

The other three findings in the drop stand:

1. **Audio DSP histogram is healthy.** p99 ≈ 2.5 ms, mean
   0.89 ms, thin tail. No correction.
2. **PipeWire quantum = 128 @ 48 kHz = 2.67 ms.** Good
   low-latency configuration. No correction.
3. **Kokoro TTS 400-char ceiling fires every ~4.7 min and
   truncates ~25–30 % of reactions.** This is the most
   actionable finding in the drop. No correction — alpha
   should still decide between benchmarking the guard and
   constraining LLM output upstream.

## 6. Lesson

This is the second correction this session that traces back
to a measurement cap — drop #1 filtered metric names with
`^compositor_` and missed `studio_camera_*`, and drop #11
capped `pw-top` output at 40 lines and missed the late-ID
BRIOs. The common error is **trusting a truncated probe as
a complete census**. Delta should default to either an
unbounded enumeration or an explicit assertion like "N
matches found" when producing headline claims.

## 7. References

- `2026-04-14-audio-path-baseline.md` § 5 — original
  incorrect claim
- `pactl list sources short` at 2026-04-14T16:00 UTC — the
  full enumeration that refutes finding 4
- `/proc/asound/cards` at the same time — ALSA-level
  confirmation
- `pactl list cards` at the same time — profile confirmation
  (`input:analog-stereo` on all three)
