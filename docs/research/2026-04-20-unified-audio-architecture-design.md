---
date: 2026-04-20
author: delta
audience: operator + alpha + delta (execution)
register: scientific, engineering-normative
status: design — unified audio-routing abstraction + config generator + migration plan
operator-directive-load-bearing: |
  "I am starting to get the feeling that we have a very messy audio pathing
  system that doesn't have a very good layer of abstraction to keep things
  sorted. Maybe this is something that should be researched deeply and
  solved. Too many mistakes around audio routing."
supersedes-in-intent: |
  config/pipewire/{voice-fx-chain,voice-fx-radio,hapax-stream-split,
  hapax-l6-evilpet-capture,hapax-vinyl-to-stream,hapax-livestream-tap,
  hapax-echo-cancel,voice-over-ytube-duck,yt-over-24c-duck}.conf
  + config/wireplumber/{50-hapax-voice-duck,60-ryzen-analog-always}.conf
  — the *topology* they express is absorbed into a single declarative
  source; the files themselves become build artefacts of the generator,
  not hand-edited truth.
related:
  - docs/research/2026-04-20-audio-normalization-ducking-strategy.md (§2 source inventory, §4 ducking matrix)
  - docs/research/2026-04-20-dual-fx-routing-design.md (Evil Pet + S-4 parallel FX, §7 programme role × source × FX)
  - docs/research/2026-04-20-mixquality-skeleton-design.md (§2 six sub-scores, §5 integration points)
  - docs/research/2026-04-19-audio-path-baseline.md (pre-24c-retirement baseline)
  - docs/research/2026-04-20-voice-transformation-tier-spectrum.md (tiers T0..T6, CC presets per tier)
  - docs/research/2026-04-20-mode-d-voice-tier-mutex.md (Evil Pet granular mutex)
  - docs/runbooks/audio-topology.md (canonical runbook; this doc extends it)
  - scripts/audio-topology-check.sh (drift detector — subsumed by `verify` subcommand)
---

# Unified Audio Architecture — a single abstraction layer for sources, sinks, FX, monitors, and broadcast paths

## §1. State of the mess

The rig currently has **nine** PipeWire conf files and **two** WirePlumber
policy files, plus one standalone topology-check shell script, plus five
load-bearing research documents whose prescriptions overlap in non-obvious
ways. Each file was written against a different hardware topology era
(pre-24c, pre-24c-retirement, pre-S-4-USB, pre-ch6-repurpose). There is no
single file or document that describes "the correct topology"; the
authoritative state is the union of the config contents, the L6's current
fader/AUX positions, the S-4's currently-loaded scene, the Evil Pet's
current knob state, the active `ProgrammeRole`, the Mode-D SHM flag, and
the operator's in-head model. At least five of the audio failures tonight
were traceable to an assumption one file made about a hardware position
that a different file contradicted.

### §1.1 Per-file audit

| File | Designed for | Assumption-era | Valid today? | Notes |
|---|---|---|---|---|
| `voice-fx-chain.conf` | TTS EQ chain: HP80 / LM-350 / P+3k / Air+10k, target Ryzen analog | post-24c-retirement (2026-04-20) | **valid** | Dry TTS via Ryzen → L6 ch 5 → AUX 1 → Evil Pet → ch 3. Target in config was retargeted from 24c → Ryzen on 2026-04-20. |
| `voice-fx-radio.conf` | Alternate TTS preset (AM-radio BP 400–3400) | pre-24c-retirement | **stale target** | Still points at `alsa_output.usb-PreSonus_Studio_24c_...analog-stereo` (retired). Swap with `voice-fx-chain.conf` is currently broken. |
| `hapax-stream-split.conf` | Two pass-through loopback sinks (`hapax-livestream`, `hapax-private`) → Ryzen analog | 2026-04-20 rewrite | **partial** | Works as a null-target stack but the names mislead: `hapax-private` is not semantically private anymore (no separate hardware destination). Ch 5 AUX is the *actual* broadcast gate. |
| `hapax-l6-evilpet-capture.conf` | Picks L6 Main Mix stem (AUX10+11) from 12-channel multitrack → `hapax-livestream-tap` | 2026-04-20 rewrite (was ch-1-only) | **valid** | This is the one feeding OBS. If the multitrack capture or the tap goes, everything goes. |
| `hapax-vinyl-to-stream.conf` | Forwards 24c Input 2 (FR) → `hapax-livestream-tap` | pre-24c-retirement | **dead wire** | Target `alsa_input.usb-PreSonus_Studio_24c_...analog-stereo` doesn't exist; module-loopback currently silent or erroring on load. |
| `hapax-livestream-tap.conf` | Null-sink with explicit monitor port + loopback to `hapax-livestream` | post-bug #187 | **valid** | Load-bearing: fixes the filter-chain-monitor-starvation class of bug. |
| `hapax-echo-cancel.conf` | WebRTC AEC on Yeti → `echo_cancel_capture` | ongoing | **valid** | Independent of hardware-topology churn; feeds VAD/STT/multi_mic. |
| `voice-over-ytube-duck.conf` | Sidechain compressor, op-voice ducks YT bed on `hapax-ytube-ducked` | 2026-04 | **valid** | Shipped and used. |
| `yt-over-24c-duck.conf` | Pipewire-side gain sink `hapax-24c-ducked`, driven by `AudioDuckingController` | 2026-04, CVS #145 | **flag-gated** | Valid; off by default. 24c retirement moots the "24c" in the name — it now guards the L6 backing bus. |
| `50-hapax-voice-duck.conf` | Role-based 3-tier duck (Multimedia, Notification, Assistant) | 2026-04-19 (notif-retarget fix) | **partial** | Still references `preferred-target = "hapax-private"` for notifications — correct by name, but `hapax-private` no longer has a hardware destination distinct from `hapax-livestream`. Notifications on broadcast are ruled out only by L6 ch 5 AUX 1 behaviour, not by the routing. Fragile. |
| `60-ryzen-analog-always.conf` | Force Ryzen `output:analog-stereo` profile active | post-24c-retirement | **valid** | Without it, PipeWire resets profile when jack-sense reads "no jack" (deliberately driving the line-out into a DC-coupled input). |

### §1.2 Current topology diagram (as of 2026-04-20 late tonight)

```
╔══════════════════════════════════════════════════════════════════════════════════╗
║  PC (Ryzen workstation)                                                          ║
║                                                                                  ║
║   ┌───────────────┐     ┌──────────────────┐     ┌────────────────────┐          ║
║   │ daimonion TTS │────▶│ voice-fx-chain   │────▶│ Ryzen HD analog    │──3.5mm──▶║
║   │ (Kokoro CPU)  │     │ hapax-voice-fx-* │     │ output (codec 73:) │          ║
║   └───────────────┘     └──────────────────┘     └────────────────────┘          ║
║                                                                                  ║
║   ┌───────────────┐     ┌──────────────────┐     ┌────────────────────┐          ║
║   │ YouTube / SC  │────▶│ hapax-livestream │────▶│ hapax-livestream-  │          ║
║   │ browser / OBS │     │ (loopback sink)  │     │ tap (null + mon)   │          ║
║   └───────────────┘     └──────────────────┘     └──────────┬─────────┘          ║
║                                                             │                     ║
║   ┌───────────────┐     ┌──────────────────┐                │                     ║
║   │ default sink  │     │ role.assistant / │                │                     ║
║   │ (most apps)   │────▶│ role.multimedia /│──(shared PW)──┤                     ║
║   └───────────────┘     │ role.notification│                │                     ║
║                         └──────────────────┘                │                     ║
║                                                             ▼                     ║
║   ┌───────────────┐     ┌──────────────────┐     ┌────────────────────┐          ║
║   │ L6 multitrack │────▶│ hapax-l6-evilpet-│────▶│ hapax-livestream-  │──▶ OBS   ║
║   │ USB (12ch)    │     │ capture (AUX10+11)│    │ tap.monitor        │   (PW    ║
║   └──────▲────────┘     └──────────────────┘     └────────────────────┘   capt) ║
║          │                                                                        ║
║   ┌──────┴────────┐     ┌──────────────────┐                                      ║
║   │ Yeti raw      │────▶│ module-echo-     │──▶ echo_cancel_capture → VAD/STT   ║
║   └───────────────┘     │ cancel (WebRTC)  │                                      ║
║                         └──────────────────┘                                      ║
║                                                                                  ║
║   ┌───────────────┐     ┌──────────────────┐                                      ║
║   │ operator mic  │────▶│ hapax-ytube-     │──▶ default stereo                   ║
║   │ (Rode/Yeti)   │     │ ducked (SC comp) │                                      ║
║   └───────────────┘     └──────────────────┘                                      ║
╚══════════════════════════════════════════════════════════════════════════════════╝
                                                │
                                                ▼  3.5mm-to-TRS
╔══════════════════════════════════════════════════════════════════════════════════╗
║  Zoom LiveTrak L6 (hardware mixer)                                               ║
║                                                                                  ║
║   ch 1 — Rode Wireless Pro RX (XLR)      fader UP       AUX 1 off              ║
║   ch 2 — Cortado MKIII (XLR +48V)        fader PRIVATE  AUX 1 off              ║
║   ch 3 — Evil Pet L-out (TRS return)     fader UP       AUX 1 off              ║
║   ch 4 — Handytrax vinyl (line)          fader UP       AUX 1 = mutex w/ ch 5  ║
║   ch 5 — PC Ryzen line-out (TRS)         fader DOWN     AUX 1 = mutex w/ ch 4  ║
║   ch 6 — sampler chain (MPC/SP bus)      fader UP       AUX 1 off              ║
║                                                                                  ║
║   AUX 1 OUT ──▶ Evil Pet L-in    (one source at a time — hard rule)            ║
║   AUX 2 OUT ──▶ retired (S-4 now USB direct)                                    ║
║   MAIN OUT  ──▶ L12 ──▶ monitors                                                ║
║   USB OUT   ──▶ PC multitrack (12ch, AUX0..AUX11; Main on AUX10+11)            ║
╚══════════════════════════════════════════════════════════════════════════════════╝
                                                                │
                                                                ▼
╔══════════════════════════════════════════════════════════════════════════════════╗
║  Evil Pet (Endorphin.es, MIDI ch 1 from Dispatch OUT 1)                          ║
║   L-in ◀── AUX 1       L-out ──▶ L6 ch 3                                        ║
║   Single granular engine: mutex(voice T5/T6, Mode D)                             ║
║                                                                                  ║
║  Torso S-4 (USB class-compliant, MIDI ch 2-5 from Dispatch OUT 2)                ║
║   Planned per dual-FX doc: USB direct from PC → S-4 → L-out → L6 ch 2           ║
║   (Cortado migrated to ch 6 in that plan)                                        ║
╚══════════════════════════════════════════════════════════════════════════════════╝
```

### §1.3 Concrete failure modes tonight attributable to missing abstraction

1. `voice-fx-radio.conf` still targets the retired 24c, so switching to the
   radio preset silently kills TTS. No single file told us this.
2. `hapax-vinyl-to-stream.conf` references a dead ALSA source; its
   module-loopback load is a no-op. The file exists, loads, and does
   nothing — impossible to tell which without reading it.
3. `hapax-private` is a sink name with no remaining semantic distinction
   from `hapax-livestream`. A developer reading `50-hapax-voice-duck.conf`'s
   `preferred-target = "hapax-private"` might assume notifications are
   guaranteed not to broadcast; they are not — only the operator's ch 5
   fader behaviour makes that true.
4. OBS's audio capture is a tap on `hapax-livestream-tap.monitor`. Whether
   a particular source reaches broadcast depends on whether its writer
   ever forwards to `hapax-livestream-tap`. The set of forwarders is
   scattered across three configs and an operator-driven L6 mixer.
5. Every time the operator repatches a hardware channel, three to four
   PipeWire configs need to be synchronously updated — and there is no
   test, diff, or schema telling us which ones.

The abstraction this document proposes is the minimum additional structure
that makes the above impossible by construction.

---

## §2. The abstraction layer

Three tiers, each with a single canonical representation, each derivable
(in one direction only) from the tier below.

```
Tier 3 — PER-SCENARIO MATRIX       (derived; operator-facing names)
            ▲
            │  resolver: (programme_role, stimmung, mutex_state)
            │            → active_scenario → routing_table
            │
Tier 2 — TOPOLOGY DECLARATION      (hand-authored YAML)
            ▲                        one-to-one with generated configs
            │  generator: yaml → {pipewire.conf.d/*.conf,
            │                     wireplumber.conf.d/*.conf,
            │                     OBS audio-source manifests,
            │                     L6 preset PDFs,
            │                     Evil Pet / S-4 scene SysEx}
            │
Tier 1 — SOURCE DECLARATIONS       (hand-authored YAML, append-only)
```

### §2.1 Tier 1 — Source declarations

**One file:** `config/audio/sources.yaml`. Append-only. Each entry is a
permanent declaration of an audio source (hardware device or logical
stream) that *could* enter the rig. Adding a source is a PR; retiring
one is a PR. The file is the authoritative inventory.

Schema (Pydantic validated):

```yaml
# config/audio/sources.yaml
sources:
  - id: tts_kokoro                   # internal stable identifier
    name: "Hapax TTS (Kokoro 82M CPU)"
    kind: software_stream             # software_stream | hardware_input
                                      # | hardware_output | virtual_loopback
    emitter: hapax-daimonion          # who produces signal (systemd unit / app)
    channels: 2
    typical_lufs: [-22, -14]          # integrated LUFS range observed
    broadcast_default: true           # does it reach broadcast by default?
    private_by_governance: false      # NOT allowed on broadcast under any scenario
    consent_class: operator_voice     # operator_voice | guest_voice | media | notification | environmental | machine
    normalize_target_lufs: -18        # per audio-normalization-ducking-strategy §3.1
    peak_ceiling_dbtp: -1
    hardware_path: "Ryzen analog out → 3.5mm → L6 ch 5 → AUX1 → Evil Pet L-in → ch 3"
    pipewire_nodes:
      input_sink: hapax-voice-fx-capture      # where emitter writes
      output_node: hapax-voice-fx-playback    # where fx-chain writes next
    telemetry:
      prom_counter: hapax_audio_source_emitted_seconds_total
      labels: { source: tts_kokoro }

  - id: vinyl_handytrax
    name: "Korg Handytrax vinyl (line)"
    kind: hardware_input
    emitter: korg_handytrax          # physical device — not a systemd unit
    channels: 2
    typical_lufs: [-18, -6]
    broadcast_default: true
    private_by_governance: false
    consent_class: media
    normalize_target_lufs: -14
    peak_ceiling_dbtp: -1
    hardware_path: "Handytrax RCA → L6 ch 4 (TRS)"
    pipewire_nodes:
      capture_node: null              # pure hardware; no PW node until L6 USB multitrack
      multitrack_channel: 4           # 1-indexed L6 channel
    telemetry: { prom_counter: hapax_audio_source_emitted_seconds_total,
                 labels: { source: vinyl_handytrax } }

  - id: cortado_contact_mic
    name: "Cortado MKIII contact mic"
    kind: hardware_input
    emitter: cortado_mk3
    channels: 1
    typical_lufs: [-40, -20]
    broadcast_default: false
    private_by_governance: true       # can only reach broadcast via operator_override scenario
    consent_class: environmental
    normalize_target_lufs: null       # private signal; DSP consumer sets its own level
    peak_ceiling_dbtp: null
    hardware_path: "Cortado XLR +48V → L6 ch 2"
    pipewire_nodes:
      capture_node: alsa_input.usb-ZOOM_Corporation_L6-00.multitrack
      multitrack_channel: 2
    telemetry: { prom_counter: hapax_audio_source_emitted_seconds_total,
                 labels: { source: cortado_contact_mic } }

  - id: system_notifications
    name: "System notifications"
    kind: software_stream
    emitter: any_app
    channels: 2
    typical_lufs: [-30, -12]
    broadcast_default: false
    private_by_governance: true       # FORBIDDEN on broadcast — governance axiom
    consent_class: notification
    normalize_target_lufs: null
    peak_ceiling_dbtp: null
    hardware_path: "(software) → role.notification loopback → private monitor only"
    pipewire_nodes:
      input_sink: loopback.sink.role.notification
    telemetry: { prom_counter: hapax_audio_source_emitted_seconds_total,
                 labels: { source: system_notifications } }

# ... all 8+ sources from audio-normalization-ducking-strategy §2 get an entry,
# plus the dual-FX doc's S-4 return and the contact-mic-migrated-to-ch-6 plan.
```

**Why append-only:** adding a new source must never silently break
existing routing. If the S-4 is introduced, its entry gets added; the
topology files that reference S-4 then compile. If the S-4 is retired,
the entry is marked `retired: true` rather than deleted — the generator
refuses to emit configs referencing retired sources and prints a
diagnostic. This is how we prevent the current `hapax-vinyl-to-stream.conf`
failure mode (config referencing dead hardware, no diagnostic).

### §2.2 Tier 2 — Topology declarations

**One file:** `config/audio/topology.yaml`. This is the *current*
topology: which sources route where, which filter-chains are live, which
WirePlumber policies are active, who feeds the broadcast aggregate. Every
topology change (24c retirement, S-4 USB addition, ch 6 repurposed) is a
PR that edits this file — no other file.

```yaml
# config/audio/topology.yaml
version: 3
as_of: 2026-04-20
authority: docs/research/2026-04-20-unified-audio-architecture-design.md

# Every physical channel on the L6 gets declared here — exactly once.
# Changing ch 4 from vinyl to sampler changes ONE entry.
mixer:
  l6:
    multitrack_capture_node: alsa_input.usb-ZOOM_Corporation_L6-00.multitrack
    main_mix_multitrack_channels: [AUX10, AUX11]    # post-fader stereo main
    channels:
      1: { source: rode_wireless_pro,    aux1: off,    fader_default: up }
      2: { source: cortado_contact_mic,  aux1: off,    fader_default: private }
      3: { source: evil_pet_return,      aux1: off,    fader_default: up }
      4: { source: vinyl_handytrax,      aux1: mutex_with_ch5, fader_default: up }
      5: { source: pc_ryzen_analog_out,  aux1: mutex_with_ch4, fader_default: down }
      6: { source: sampler_chain_bus,    aux1: off,    fader_default: up }
    aux_sends:
      1: { destination: evil_pet_lin,    mutex: [ch4, ch5] }   # hardware-enforceable
      2: { destination: retired }

# Filter-chains the generator should emit + install.
# Each entry produces exactly one file in ~/.config/pipewire/pipewire.conf.d/.
# Naming invariant: <category>__<purpose>.conf so files sort by function.
filter_chains:
  - id: voice_fx_chain
    purpose: "TTS EQ chain (HP80 / LM-350 / P+3k / Air+10k)"
    sink_name: hapax-voice-fx-capture
    playback_target: ryzen_analog_out       # resolved from sources.yaml
    preset: voice_studio                    # voice_studio | voice_radio
    enabled_when: { programme_role_in: [SHOWCASE, NARRATOR, AMBIENT, LISTENING, MODE_D+NARRATOR] }

  - id: livestream_tap
    purpose: "OBS monitor tap (null-sink + loopback; prevents monitor-starvation)"
    sink_name: hapax-livestream-tap
    sink_kind: null_audio_sink
    forwards_to: hapax-livestream           # keeps existing bridge alive
    enabled_when: always

  - id: l6_main_mix_to_tap
    purpose: "L6 Main Mix (AUX10+11) → hapax-livestream-tap for OBS"
    capture_node: alsa_input.usb-ZOOM_Corporation_L6-00.multitrack
    capture_channel_pick: [AUX10, AUX11]    # explicit — not magic indices
    playback_target: hapax-livestream-tap
    enabled_when: always

  - id: ytube_duck
    purpose: "Sidechain compressor: operator voice ducks YT bed"
    sink_name: hapax-ytube-ducked
    sidechain_source: hapax-operator-mic-tap
    ladspa: { plugin: sc4m_1916, threshold_db: -30, ratio: 8, attack_ms: 5, release_ms: 300 }
    enabled_when: always

  - id: echo_cancel
    purpose: "WebRTC AEC on Yeti; reference = default-sink monitor"
    source_name: echo_cancel_capture
    reference_sink: echo_cancel_sink
    input_hardware: yeti_blue
    enabled_when: always

  - id: s4_fx
    purpose: "Music-path FX via S-4 USB direct"
    sink_name: hapax-s4-fx-capture
    playback_target: s4_usb_out_1_2
    ebur128_target_lufs: -14                # music target per §3.1
    peak_ceiling_dbtp: -1
    enabled_when: { s4_usb_available: true }  # if S-4 absent, fall back to livestream sink
    # This entry is what removes the "hapax-private is semantically empty"
    # ambiguity: with S-4 present, non-voice PC audio has its own hardware
    # return (ch 2) — a meaningful second destination.

# WirePlumber policies.
wireplumber_policies:
  - id: voice_role_duck
    kind: role_based_loopbacks
    duck_level: 0.3                         # -10 dB
    priorities: { multimedia: 10, notification: 20, assistant: 40 }
    notification_preferred_target: null_private_monitor   # see §2.3 naming
    # "null_private_monitor" is a logical name resolved by the generator;
    # today it maps to Ryzen analog (TTS shares the wire); post-dual-FX
    # it maps to the dedicated S-4 monitor out pair.

  - id: ryzen_always_on
    kind: profile_lock
    device: ryzen_hd_audio_codec
    profile: "output:analog-stereo"

# Logical sinks that the scenario matrix (Tier 3) references.
# Each one is a NAMED SEMANTIC (not just a PW sink name) that the
# generator resolves to the actual nodes it produces.
logical_sinks:
  broadcast_aggregate:
    realised_by: hapax-livestream-tap
    consumers: [obs_pipewire_capture]
    governance: "reaches YouTube RTMP; nothing private_by_governance allowed"

  operator_monitor:
    realised_by: l6_main_out                # hardware
    consumers: [l12_amp, operator_headphones]
    governance: "operator-only; notifications + contact mic permitted"

  fx_evil_pet:
    realised_by: l6_aux1                    # hardware return
    consumers: [evil_pet_lin]
    governance: "single-writer mutex: {ch4 AUX1, ch5 AUX1}"

  fx_s4:
    realised_by: s4_usb_in                  # USB direct
    consumers: [s4_track_1]
    governance: "no mutex constraint; parallel to evil_pet"

# Constraints the generator enforces at compile time.
invariants:
  - name: "no private source reaches broadcast by default"
    rule: |
      for s in sources:
        if s.private_by_governance and s.broadcast_default:
          FAIL
  - name: "evil_pet aux1 mutex"
    rule: |
      cannot have both mixer.l6.channels[4].aux1 == on
                  and mixer.l6.channels[5].aux1 == on
      in the same active scenario
  - name: "retired sources not referenced"
    rule: |
      no filter_chain, no logical_sink may name a retired source
  - name: "Mode D ⇒ TTS muted OR routed to s4_mosaic"
    rule: |
      if programme_role in {MODE_D, MODE_D+NARRATOR}:
        either voice_fx_chain.enabled == false
        or     voice_fx_chain.playback_target == s4_usb_in
```

### §2.3 Tier 3 — Per-scenario matrix

**One file, derived:** `config/audio/scenarios.yaml`. Lists every named
scenario the operator recognises; resolves each to the routing decisions
over Tier 2's logical sinks. The matrix is **computed**, not hand-written
— `hapax-audio-topology describe` emits it from Tier 2 plus the
programme/stimmung/mutex state space, and writes a pretty-printed Markdown
table next to the YAML for operator reference. Hand-editing `scenarios.yaml`
is permitted only for overrides not expressible as a pure function of Tier 2
(rare; each override is a TODO to lift into the schema).

Scenario enumeration is a Cartesian product over:

- `ProgrammeRole` ∈ {LISTENING, SHOWCASE, NARRATOR, AMBIENT, MODE_D,
  MODE_D+NARRATOR, SILENT} (per `dual-fx-routing-design.md` §7)
- `voice_tier` ∈ {T0..T6} (per `voice-transformation-tier-spectrum.md`)
- `stimmung_wash` bin ∈ {dry, medium, wet}
- `operator_override` ∈ {none, contact_mic_on_broadcast, headphones_only, ...}

Not every combination is realisable (Mode D + voice T5/T6 is mutex — the
generator emits a `conflict: mode_d_granular_mutex` entry instead of a
routing). Scenarios the operator actually uses get human-readable names
and Stream Deck buttons (§8).

```yaml
# config/audio/scenarios.yaml (derived)
scenarios:
  - name: voice_only_default
    programme_role: SHOWCASE
    voice_tier: T2                           # BROADCAST-GHOST
    stimmung_wash: medium
    mutex_state: {}
    routing:
      tts_kokoro:        { via: voice_fx_chain → evil_pet → l6_ch3 → broadcast_aggregate }
      vinyl_handytrax:   muted_at_source     # ch4 fader down
      rode_wireless_pro: broadcast_aggregate
      cortado_contact_mic: private_only
      system_notifications: operator_monitor_only
      yt_soundcloud:     { via: hapax-s4-fx → s4_ch2 → broadcast_aggregate }
    l6_fader_intent:
      ch1: up, ch2: private, ch3: up, ch4: down, ch5: down (AUX1 up), ch6: up
    expected_mix_quality: >= 0.85
    governance_ok: true

  - name: vinyl_mode_d
    programme_role: MODE_D
    voice_tier: T0                           # forced mute
    stimmung_wash: wet
    mutex_state: { evil_pet_granular: vinyl }
    routing:
      tts_kokoro:        muted_at_source
      vinyl_handytrax:   { via: ch4 AUX1 → evil_pet_granular → l6_ch3 → broadcast_aggregate }
      rode_wireless_pro: broadcast_aggregate
    l6_fader_intent:
      ch1: up, ch2: private, ch3: up, ch4: up (AUX1 up), ch5: down (AUX1 down), ch6: up
    expected_mix_quality: >= 0.80
    governance_ok: true

  - name: sampler_performance_narrating
    programme_role: NARRATOR
    voice_tier: T3                           # MEMORY register
    stimmung_wash: medium
    mutex_state: { evil_pet_granular: voice, s4_mosaic: idle }
    routing:
      tts_kokoro:        { via: voice_fx_chain → evil_pet → l6_ch3 → broadcast_aggregate }
      sampler_chain_bus: { via: ch6 → broadcast_aggregate }
      yt_soundcloud:     { via: hapax-s4-fx → s4 → l6_ch2 → broadcast_aggregate }
      vinyl_handytrax:   muted_at_source
    l6_fader_intent:
      ch1: up, ch2: private, ch3: up, ch4: down, ch5: down (AUX1 up), ch6: up
    expected_mix_quality: >= 0.85
    governance_ok: true

  - name: mode_d_narrator_dual_granular
    programme_role: MODE_D+NARRATOR
    voice_tier: T5                           # GRANULAR-WASH via S-4 Mosaic
    stimmung_wash: wet
    mutex_state: { evil_pet_granular: vinyl, s4_mosaic: voice }
    routing:
      tts_kokoro:        { via: voice_fx_chain → hapax-s4-fx → s4_mosaic → l6_ch2 → broadcast_aggregate }
      vinyl_handytrax:   { via: ch4 AUX1 → evil_pet_granular → l6_ch3 → broadcast_aggregate }
    l6_fader_intent:
      ch1: up, ch2: private, ch3: up, ch4: up (AUX1 up), ch5: down (AUX1 down), ch6: up
    expected_mix_quality: >= 0.80
    governance_ok: true
    notes: |
      Only realisable when S-4 is USB-connected. Without S-4, degrades to
      `vinyl_mode_d` scenario (voice muted).
```

### §2.4 Where the abstraction lives — concrete placement

- `config/audio/sources.yaml` (hand-authored)
- `config/audio/topology.yaml` (hand-authored)
- `config/audio/scenarios.yaml` (generated; committed for review)
- `shared/audio/topology_schema.py` (Pydantic models for the three files)
- `shared/audio/topology_compile.py` (Tier 2 → PipeWire confs)
- `shared/audio/topology_resolve.py` (Tier 2 + programme state → active scenario)
- `scripts/hapax-audio-topology` (CLI; §4)
- `config/pipewire/generated/*.conf` (build artefacts; gitignored; emitted
  by `hapax-audio-topology generate`)
- `~/.config/pipewire/pipewire.conf.d/*.conf` (install target; symlinks
  to `config/pipewire/generated/*.conf` by default)

The hand-authored set is **two** files plus one schema module. The
generated set can be regenerated at any time and is not the source of
truth.

---

## §3. Three concrete scenarios — end-to-end trace

Each scenario traces from Tier 3 (scenario name) down through Tier 2
(routing decisions) to concrete hardware + PipeWire state. All three are
expressible in the schema above; none require hand-edit of generated
configs.

### §3.1 Scenario A — Operator speaking over music (Rode ch 1, Handytrax ch 4, TTS silent)

**Abstraction notation:**
```
scenario: operator_talking_over_vinyl
  programme_role: SHOWCASE
  voice_tier: T0                         # TTS silent (tier 0 = unadorned; but CPAL does not emit)
  mutex_state: { evil_pet_granular: idle }
  operator_override: vinyl_dry_on_broadcast
```

**Sources active (from Tier 1):**
- `rode_wireless_pro` (operator voice) — broadcast
- `vinyl_handytrax` — broadcast
- `cortado_contact_mic` — private
- `system_notifications` — operator_monitor_only

**Tier 2 derivation (routes resolved):**
- `rode_wireless_pro → l6_ch1 → main_mix → broadcast_aggregate`
- `vinyl_handytrax → l6_ch4 (AUX1 OFF; dry) → main_mix → broadcast_aggregate`
- `tts_kokoro`: no emission (tier T0 + CPAL idle)
- `cortado_contact_mic → l6_ch2 (fader private) → private_monitor`
- `system_notifications → role.notification → null_private_monitor`

**Concrete state:**

*L6 hardware:*
| ch | fader | AUX 1 | trim |
|---|---|---|---|
| 1 | up (unity) | off | -18 LUFS norm |
| 2 | private | off | -22 LUFS RMS |
| 3 | up (standby for Hapax) | off | -18 dB nominal |
| 4 | up | off | record-dependent trim |
| 5 | down | **up (prearmed)** | -18 LUFS norm |
| 6 | up | off | as set |

*PipeWire:*
- Filter-chain `voice_fx_chain`: sink present (hapax-voice-fx-capture), idle.
- `hapax-livestream-tap`: forwarding L6 main-mix capture to OBS normally.
- `hapax-ytube-ducked`: idle (no YT playing).
- `echo_cancel_capture`: live — VAD/STT still run on operator voice.

*MIDI / FX:*
- Evil Pet: at voice-tier-T0-bypass scene; no notes/CCs being emitted by
  `vocal_chain.py` (TTS silent so the 9-dim emitter is quiet).
- S-4: if present, sitting at `HAPAX-CLEAN` scene (Scene 4).

*OBS:*
- Audio source: PipeWire capture of `hapax-livestream-tap.monitor` (only
  configured input — never changes between scenarios).

*Governance check:* `cortado_contact_mic.private_by_governance == true`
and it is NOT in broadcast routing. `system_notifications` same. Pass.

### §3.2 Scenario B — Hapax speaking during vinyl Mode D

**Abstraction notation:**
```
scenario: mode_d_narrator_dual_granular
  programme_role: MODE_D+NARRATOR
  voice_tier: T5                         # GRANULAR-WASH
  mutex_state: { evil_pet_granular: vinyl, s4_mosaic: voice }
  requires: s4_usb_connected
```

**Sources active:**
- `tts_kokoro` — broadcast via S-4 Mosaic
- `vinyl_handytrax` — broadcast via Evil Pet granular (Mode D)
- `rode_wireless_pro` — broadcast (operator may talk over both)
- All private sources in their private routes

**Tier 2 derivation:**
- Both granular engines claimed; the mutex solver verifies
  `evil_pet_granular` claimed by vinyl AND `s4_mosaic` claimed by voice,
  which are independent devices: no conflict.
- `tts_kokoro → voice_fx_chain → hapax-s4-fx-capture → s4_mosaic (Scene 3)
  → s4_out_1_2 → l6_ch2 → broadcast_aggregate`
- `vinyl_handytrax → l6_ch4 (AUX1 ON) → evil_pet_lin (granular, Mode D
  scene) → evil_pet_lout → l6_ch3 → broadcast_aggregate`
- `voice_fx_chain.playback_target` is **rewritten** by the generator
  under this scenario from the default (`ryzen_analog_out`) to
  `hapax-s4-fx-capture` — handled via a WirePlumber role override in
  `50-hapax-voice-duck.conf`'s generated variant.

**Concrete state:**

*L6 hardware:*
| ch | fader | AUX 1 |
|---|---|---|
| 1 | up | off |
| 2 | up (S-4 music+voice return) | off |
| 3 | up (Evil Pet vinyl-granular return) | off |
| 4 | up | **ON** (to Evil Pet) |
| 5 | down | **OFF** (mutex) — TTS bypasses ch 5 entirely in this scenario |
| 6 | up | off |

*PipeWire:*
- `voice_fx_chain` sink's `playback.target.object` = `hapax-s4-fx-capture`
  (generator-emitted override active under MODE_D+NARRATOR).
- `hapax-s4-fx` active; S-4 USB sink live.
- `hapax-livestream-tap` forwarding as always.

*MIDI / FX:*
- Evil Pet: Mode D scene active (CC 11=120, CC 40=127, CC 94=60, CC 84=40).
- S-4: Scene 3 `HAPAX-NARRATOR-FX` active; Mosaic ON (size 60, density 50,
  wet 60%).

*OBS:* unchanged (always monitors `hapax-livestream-tap.monitor`).

*Governance check:* Mutex solver verified no engine double-claim. Mode D
hard-mutex on TTS-through-Evil-Pet satisfied (TTS rerouted to S-4). Pass.

### §3.3 Scenario C — Sampler performance, Hapax narrating T3 MEMORY, YouTube via S-4

**Abstraction notation:**
```
scenario: sampler_performance_narrating
  programme_role: NARRATOR
  voice_tier: T3                         # MEMORY
  mutex_state: { evil_pet_granular: voice (but T3 uses non-granular), s4_mosaic: idle }
```

Note: voice tier T3 does NOT engage Evil Pet granular (per
`voice-transformation-tier-spectrum.md` §2 — CC 11 grains volume = 0 at
T3). Evil Pet is operating in its non-granular reverb+saturator regime.
The mutex state `evil_pet_granular: voice` is technically reserved but
unused; the mutex solver accepts it as a no-op reservation.

**Sources active:**
- `tts_kokoro` — broadcast via Evil Pet (voice regime)
- `sampler_chain_bus` (ch 6) — broadcast direct
- `yt_soundcloud` — broadcast via S-4 music FX
- `vinyl_handytrax` — muted at source (fader down)

**Tier 2 derivation:**
- `tts_kokoro → voice_fx_chain → ryzen_analog_out → l6_ch5 (AUX1 ON) →
  evil_pet_lin → evil_pet_lout → l6_ch3 → broadcast_aggregate`
- `sampler_chain_bus → l6_ch6 → main_mix → broadcast_aggregate`
- `yt_soundcloud → hapax-livestream (sink) → hapax-s4-fx → s4_track_1
  (Scene 2 HAPAX-MUSIC-FX) → s4_out → l6_ch2 → broadcast_aggregate`

*L6 hardware:* as per §3.1 but ch 5 AUX 1 ON, ch 4 AUX 1 OFF.

*PipeWire:* `voice_fx_chain` default target (Ryzen); `hapax-s4-fx` active
routing to S-4 Scene 2 (not Scene 3). WirePlumber role override NOT active.

*MIDI / FX:*
- Evil Pet: T3 MEMORY scene (CC 40=70 wet, CC 91=55 reverb, CC 44=70
  pitch-up hint).
- S-4 Scene 2 active (Ring wet 50, Deform wet 90, Vast reverb 55/size 95).

*Governance check:* AUX 1 mutex satisfied (ch 4 off). S-4 music scene
doesn't claim Mosaic. Pass.

---

## §4. Config generator — `hapax-audio-topology` CLI

Python 3.12, Typer. Lives at `scripts/hapax-audio-topology` (wrapper) +
`shared/audio/cli.py` (implementation). Single-binary entry point; all
subcommands operate on the Tier 1/2 files.

### §4.1 Subcommands

```
hapax-audio-topology describe
    Print every source, every sink, every route. Optionally filter by
    programme_role or source id. Produces a Markdown or JSON table.
    Output includes:
      - Which sources currently have live PW nodes
      - Which sinks currently exist in PW
      - Which routes are realisable now vs. gated on hardware (S-4)
      - Each source's governance class and current broadcast status

hapax-audio-topology generate [--dry-run] [--dir DIR]
    Reads sources.yaml + topology.yaml, emits:
      - config/pipewire/generated/*.conf   (one file per filter_chain)
      - config/wireplumber/generated/*.conf (one per policy entry)
      - config/audio/scenarios.yaml          (Tier 3 derivation)
      - docs/runbooks/audio-topology.generated.md  (pretty-printed table)
    By default writes to config/{pipewire,wireplumber}/generated/ (repo).
    --dir ~/.config/pipewire/pipewire.conf.d/ installs to runtime.
    Atomic: writes to a tmp dir then renames in one fs operation.

hapax-audio-topology verify [--strict]
    Reads live PipeWire state via `pw-dump` + `wpctl status`, diffs
    against the declared topology. Exits non-zero if drift. Failures:
      - PW sink missing that topology declares
      - PW node present that topology does NOT declare (strange)
      - Filter-chain target mismatches
      - L6 multitrack not in Altset 2 (can't reach AUX10+11)
      - Hardware (Ryzen, L6, S-4 if declared) not discoverable
      - Retired source referenced by any active config
    Subsumes scripts/audio-topology-check.sh.

hapax-audio-topology switch <scenario> [--hold-faders]
    Transition from current active scenario → named scenario.
    Emits:
      - MIDI PC messages to Evil Pet + S-4 for scene recall
      - WirePlumber role-override writes (voice-fx retarget for MODE_D+NARRATOR)
      - SHM flag writes (/dev/shm/hapax-compositor/mode-d-active etc.)
      - Prompt overlay on Logos showing the L6 fader intent the operator
        must physically realise (unless --hold-faders)
    Does NOT touch PipeWire conf files at runtime (those are static post-generate).

hapax-audio-topology audit <source_id>
    Traces a source through every realisable scenario: which sinks it
    reaches, which mutex groups it participates in, whether any route
    is dead (references retired hardware / missing PW node).
    Prints:
      - Routes realisable today vs. gated on hardware
      - Governance flags on each route
      - Dead paths (if any) with remediation suggestion

hapax-audio-topology diff HEAD
    Shows the delta between the generated configs at HEAD and the
    current working tree's generated output. CI gate.
```

### §4.2 Minimal Python skeleton

```python
# shared/audio/cli.py
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Literal

import typer
from pydantic import BaseModel, Field

from shared.audio.topology_schema import (
    AudioSource, Topology, ScenarioResolution, validate_invariants,
)
from shared.audio.topology_compile import (
    compile_filter_chains, compile_wireplumber, compile_scenarios_yaml,
)
from shared.audio.topology_resolve import resolve_scenario, live_pipewire_state

app = typer.Typer(help="Unified audio topology management for hapax-council.")
SOURCES = Path("config/audio/sources.yaml")
TOPOLOGY = Path("config/audio/topology.yaml")


def _load() -> tuple[list[AudioSource], Topology]:
    sources = [AudioSource.model_validate(s)
               for s in typer.get_app_dir(".") and _yaml(SOURCES)["sources"]]
    topology = Topology.model_validate(_yaml(TOPOLOGY))
    validate_invariants(sources, topology)
    return sources, topology


@app.command()
def describe(source: str | None = None, role: str | None = None,
             format: Literal["md", "json"] = "md") -> None:
    sources, topology = _load()
    # ... walk sources/sinks/routes, filter by args, emit table ...


@app.command()
def generate(dry_run: bool = False,
             dir: Path = Path("config/pipewire/generated")) -> None:
    sources, topology = _load()
    pw_confs = compile_filter_chains(sources, topology)
    wp_confs = compile_wireplumber(sources, topology)
    scenarios = compile_scenarios_yaml(sources, topology)
    if dry_run:
        for name, body in {**pw_confs, **wp_confs}.items():
            typer.echo(f"--- {name} ---\n{body}")
        return
    _atomic_write_dir(dir, pw_confs | wp_confs)
    _atomic_write(Path("config/audio/scenarios.yaml"), scenarios)


@app.command()
def verify(strict: bool = False) -> None:
    sources, topology = _load()
    live = live_pipewire_state()                         # pw-dump + wpctl
    drift = topology.diff_against_live(live)
    if drift:
        for d in drift:
            typer.secho(f"DRIFT: {d.kind}: {d.detail}", fg="red")
        raise typer.Exit(1 if strict else 0)
    typer.secho("OK: topology matches live state.", fg="green")


@app.command()
def switch(scenario: str, hold_faders: bool = False) -> None:
    sources, topology = _load()
    scenarios = compile_scenarios_yaml(sources, topology)
    target = scenarios[scenario]
    current = resolve_scenario(topology, live_pipewire_state())
    plan = target.transition_plan(from_=current)
    for step in plan.midi_messages:
        _midi_send(step)
    for step in plan.wireplumber_overrides:
        _wp_override(step)
    for step in plan.shm_writes:
        _shm_write(step.path, step.payload)
    if not hold_faders:
        _prompt_fader_intent(target.l6_fader_intent)


@app.command()
def audit(source_id: str) -> None:
    sources, topology = _load()
    source = next(s for s in sources if s.id == source_id)
    paths = topology.enumerate_paths_from(source)
    for p in paths:
        typer.echo(f"{source.id} → {' → '.join(p.hops)}  ({p.governance}, {p.liveness})")


if __name__ == "__main__":
    app()
```

The generator's code is deliberately terse: compile functions are pure
(YAML → string); `resolve_scenario` is pure over a snapshot of live PW
state; `switch` issues side effects in a named, replayable plan. All
pure pieces test as unit tests; the side-effect pieces get an
integration test against a mock PipeWire socket (`pw-mon` JSON frames).

### §4.3 What the generator emits for Tier 2's `voice_fx_chain`

Input (topology.yaml excerpt):
```yaml
- id: voice_fx_chain
  purpose: "TTS EQ chain (HP80 / LM-350 / P+3k / Air+10k)"
  sink_name: hapax-voice-fx-capture
  playback_target: ryzen_analog_out
  preset: voice_studio
  enabled_when: { programme_role_in: [SHOWCASE, NARRATOR, AMBIENT, LISTENING] }
```

Output (`config/pipewire/generated/voice_fx_chain.conf`):
```
# GENERATED by hapax-audio-topology at 2026-04-20T22:17:04
# Source: config/audio/topology.yaml filter_chains[voice_fx_chain]
# DO NOT EDIT — regenerate with `hapax-audio-topology generate`
context.modules = [
    {
        name = libpipewire-module-filter-chain
        args = {
            node.name = "hapax-voice-fx"
            node.description = "Hapax Voice FX Chain (voice_studio preset)"
            media.class = "Audio/Sink"
            audio.rate = 48000
            audio.channels = 2
            audio.position = [ FL FR ]
            filter.graph = {
                nodes = [
                    { type = builtin name = hp_l    label = bq_highpass    control = { "Freq" = 80.0    "Q" = 0.707 } }
                    { type = builtin name = hp_r    label = bq_highpass    control = { "Freq" = 80.0    "Q" = 0.707 } }
                    { type = builtin name = lm_l    label = bq_peaking     control = { "Freq" = 350.0   "Q" = 1.2 "Gain" = -2.0 } }
                    { type = builtin name = lm_r    label = bq_peaking     control = { "Freq" = 350.0   "Q" = 1.2 "Gain" = -2.0 } }
                    { type = builtin name = pres_l  label = bq_peaking     control = { "Freq" = 3000.0  "Q" = 0.9 "Gain" = 3.0 } }
                    { type = builtin name = pres_r  label = bq_peaking     control = { "Freq" = 3000.0  "Q" = 0.9 "Gain" = 3.0 } }
                    { type = builtin name = air_l   label = bq_highshelf   control = { "Freq" = 10000.0 "Q" = 0.707 "Gain" = 2.0 } }
                    { type = builtin name = air_r   label = bq_highshelf   control = { "Freq" = 10000.0 "Q" = 0.707 "Gain" = 2.0 } }
                ]
                inputs  = [ "hp_l:In" "hp_r:In" ]
                outputs = [ "air_l:Out" "air_r:Out" ]
                links   = [ ... ]
            }
            capture.props  = { node.name = "hapax-voice-fx-capture"  media.class = "Audio/Sink" }
            playback.props = { node.name = "hapax-voice-fx-playback" target.object = "alsa_output.pci-0000_73_00.6.analog-stereo" }
        }
    }
]
```

When topology.yaml resolves `playback_target: ryzen_analog_out` to an
alsa sink name using sources.yaml (`pc_ryzen_analog_out.pipewire_nodes.output_node`),
every config changes in one place. That is what the abstraction is for.

---

## §5. Migration plan

Five phases, each rollback-safe, each producing a shippable commit + a
live-verified topology. Estimated LOC are authored (not generated); each
phase ends with a visible-on-broadcast verification the operator performs.

### §5.1 Phase 1 — Parallel shadow (no behaviour change)

**Goal:** introduce the schema + generator without touching any
installed config. Verify that `generate` reproduces the current files
byte-equivalent.

**LOC:** ~800 new Python (schema + compile + CLI + tests) + ~400 YAML
(two new files that reproduce current state).

1. Add `shared/audio/topology_schema.py` with Pydantic models.
2. Add `config/audio/sources.yaml` reflecting all 8 sources from
   `audio-normalization-ducking-strategy.md` §2 + S-4 return entry (for
   later) + sampler_chain_bus.
3. Add `config/audio/topology.yaml` reflecting the current 9
   filter-chains + 2 WP policies as they exist today.
4. Add `shared/audio/topology_compile.py` emitters.
5. Add `scripts/hapax-audio-topology` + `shared/audio/cli.py`.
6. Add `tests/shared/audio/test_compile_byte_equivalent.py`: golden-file
   test — `generate --dry-run` against the current configs must produce
   byte-identical output (formatting normalised). This is the
   correctness gate for the phase.
7. Add `tests/shared/audio/test_invariants.py`: violations caught at
   compile time (retired source, aux1 mutex, private-on-broadcast).
8. Add CI job that runs `hapax-audio-topology verify` nightly against
   recorded topology fixtures.

**Rollback:** delete the four Python files and two YAML files. No
installed-config changes happened; system is untouched.

### §5.2 Phase 2 — Cutover install target (generated ≡ installed)

**LOC:** ~100 (install logic + systemd one-shot).

1. `hapax-audio-topology generate --dir ~/.config/pipewire/pipewire.conf.d/`
   emits the same content that currently exists.
2. Add a systemd user one-shot `hapax-audio-topology-install.service`
   that runs `generate --dir ~/.config/pipewire/pipewire.conf.d/` on
   boot (after hapax-secrets, before pipewire user units).
3. Update `~/.config/pipewire/pipewire.conf.d/` to contain only the
   generated files (manual cp to replace the current hand-edited ones).
4. Verification: `hapax-audio-topology verify --strict` passes. Live
   audio unchanged (if it changes, the Phase 1 byte-equivalence test
   missed something and we revert).
5. Delete the hand-edited files from `config/pipewire/*.conf` — they
   are now superseded by `config/pipewire/generated/*.conf`. Commit
   with cross-reference to this doc.

**Rollback:** `git checkout` the deleted hand-edited files; disable
`hapax-audio-topology-install.service`; `systemctl --user restart
pipewire` re-reads the restored hand-edits. 60-second recovery.

### §5.3 Phase 3 — Repair the known stale targets

**LOC:** ~20 YAML edits.

With generate authoritative, the stale targets become trivial to fix:

1. `voice-fx-radio.conf` target (currently pointing at retired 24c):
   change `topology.yaml` filter_chains[voice_fx_radio].playback_target
   from `studio_24c_analog_out` (retired) to `ryzen_analog_out`.
2. `hapax-vinyl-to-stream.conf` (dead 24c source): remove from
   topology.yaml. The 24c source hasn't existed since retirement; the
   compiler should have refused to emit this file in Phase 1. Fixing
   it now is a retroactive cleanup.
3. `hapax-private` vs `hapax-livestream` ambiguity: collapse to one
   logical sink until the S-4 USB path is live (Phase 4). Mark
   `hapax-private` as a synonym-alias rather than a distinct node;
   generator emits one loopback, two names.
4. `50-hapax-voice-duck.conf` notification preferred-target: update to
   a Tier-2 logical sink (`null_private_monitor`) rather than a raw
   PW node name. Generator resolves the alias.

Verification: `verify --strict` passes with updated topology; live
smoke test: load `voice-fx-radio` preset, swap to `voice-fx-chain`,
verify audio continuity.

### §5.4 Phase 4 — S-4 USB direct + dual-FX scenarios

**LOC:** ~150 (topology.yaml additions + scenario derivation for
MODE_D+NARRATOR + test fixtures).

Realise the architecture of `dual-fx-routing-design.md`:

1. Add S-4 entries to sources.yaml + topology.yaml.
2. Emit `hapax-s4-fx.conf` via generate.
3. Add scenario definitions for SHOWCASE, NARRATOR,
   MODE_D+NARRATOR — generator computes scenarios.yaml from topology.
4. Wire `hapax-audio-topology switch <scenario>` to issue S-4 + Evil Pet
   MIDI PC scene recalls.
5. Cortado migration ch 2 → ch 6 is a single edit in topology.yaml's
   `mixer.l6.channels`.

Verification: Scenario B (§3.2) end-to-end — operator confirms both
granular engines running, no cross-modulation.

### §5.5 Phase 5 — Scenario UI + observability

**LOC:** ~300 (Logos panel + Stream Deck map + Prometheus metrics).

1. Logos orientation panel adds a "scenario" pill showing active
   scenario name + last transition timestamp (§8).
2. Stream Deck layer: 6 scenarios mapped to 6 keys; key press invokes
   `hapax-audio-topology switch <scenario>`.
3. Prometheus metrics per §7.
4. Grafana panel rollup.
5. Retire `scripts/audio-topology-check.sh` — fully subsumed by
   `verify`.

Verification: operator uses Stream Deck to cycle through all three §3
scenarios live on broadcast; Grafana shows clean transitions, no
drops, no governance violations.

### §5.6 Phase 6 — Deferred: EBU R128 loudnorm wiring

Not strictly part of the abstraction epic; tracked in
`audio-normalization-ducking-strategy.md` §9 Phase A/B. Ships after
Phase 5 once the `filter_chains` entries can carry `ebur128: {target,
peak_ceiling}` attributes and the generator emits them.

---

## §6. Governance coupling

### §6.1 ProgrammeRole × topology

`ProgrammeRole` (defined in `shared/programme.py`, extended in
`dual-fx-routing-design.md` §7) is the top-level discriminator over
scenarios. The mapping is:

| ProgrammeRole | Resolves to scenario family |
|---|---|
| LISTENING | `*_listening_only` — voice muted, music optional |
| SHOWCASE | `*_showcase_default` — full mix per current tier state |
| NARRATOR | `*_narrator_*` — voice forward, music bed |
| AMBIENT | `*_ambient_*` — low-key voice, long washes |
| MODE_D | `vinyl_mode_d` — voice muted, Evil Pet on vinyl |
| MODE_D+NARRATOR | `mode_d_narrator_dual_granular` — dual granular engines |
| SILENT | `*_silent` — everything muted at source; no hardware change |

The scenario name includes the programme role as a prefix. One
scenario per programme role × voice tier × stimmung bin, minus the
mutex-forbidden combinations.

### §6.2 Monetization opt-ins

Every source has a `consent_class` in sources.yaml. The generator
refuses to emit a scenario that routes a `consent_class: guest_voice`
source to `broadcast_aggregate` unless `Programme.monetization_opt_ins`
includes `guest_voice_broadcast`. The opt-in check is a compile-time
invariant: a scenario that violates it is never produced.

### §6.3 Voice-tier mutex groups

`mode-d-voice-tier-mutex.md` defines the single-source-of-truth at
`/dev/shm/hapax-compositor/evil-pet-state.json`. The topology YAML
declares `fx_evil_pet.governance` as "single-writer mutex"; the
scenario resolver reads the SHM state before accepting a switch
request. A switch that would violate the mutex is refused with a
named error, not silently best-effort-applied.

Similarly `fx_s4.governance` reserves `s4_mosaic` as a separate mutex
group; the MODE_D+NARRATOR scenario is unique in claiming both
granular mutexes simultaneously (with different engines).

### §6.4 Vinyl Mode D lease

The Mode D scenario acquires a lease over ch 4 AUX 1 + Evil Pet
granular. The scenario resolver writes the lease marker at switch time
and releases at exit. If a competing scenario requests Evil Pet
granular during an active Mode D lease, the resolver returns
`SCENARIO_LEASE_CONFLICT` and the operator's UI shows the current
lease holder. `switch` never preempts leases silently.

---

## §7. Observability

### §7.1 Per-source Prometheus counters

Emitted by a lightweight `hapax-audio-meters` systemd user service that
subscribes to each PW sink's monitor and runs a rolling window:

```
hapax_audio_source_emitted_seconds_total{source="tts_kokoro"}
hapax_audio_source_rms_dbfs{source, window="1s"}
hapax_audio_source_lufs{source, window="short"}
hapax_audio_source_peak_dbtp{source, window="1s"}
```

### §7.2 Per-route dB levels

```
hapax_audio_route_gain_db{from=<source>, to=<sink>, via=<logical_sink>}
hapax_audio_route_active{from, to, via}
```

Emitted by the scenario resolver on every switch and on WirePlumber
state change (pw-mon event subscription).

### §7.3 Per-scenario transition events

Each `switch` call emits a structured event to `profiles/sdlc-events.jsonl`
+ Langfuse:

```json
{
  "event": "audio_scenario_transition",
  "from": "voice_only_default",
  "to": "mode_d_narrator_dual_granular",
  "duration_ms": 820,
  "midi_messages": 4,
  "wireplumber_overrides": 1,
  "shm_writes": 2,
  "fader_intent_prompted": true,
  "governance_check": "pass",
  "mutex_groups_claimed": ["evil_pet_granular", "s4_mosaic"]
}
```

### §7.4 MixQuality integration

Per `mixquality-skeleton-design.md` §5 integration points, the unified
abstraction feeds:

- `hapax_mix_source_balance` sub-score: per-route RMS envelope vs
  declared scenario's expected per-source presence.
- `hapax_mix_intentionality_coverage` sub-score: binary per-frame —
  every source currently audible on broadcast either has an active
  scenario routing entry, or it counts as "unattributed broadcast
  content" and drags the score. This sub-score is *the* measurable form
  of "every audio source on broadcast is intentional."

### §7.5 Grafana panels

One dashboard `livestream-audio-unified` with:

1. **Top row:** current scenario name, MixQuality aggregate, LUFS
   integrated, peak dBTP.
2. **Per-source row:** 8 tiles (one per Tier-1 source), each showing
   live LUFS + route state (broadcast / private / muted).
3. **Per-FX row:** Evil Pet + S-4 engine status (current scene, mutex
   holder, CC write rate).
4. **Transition log:** scrolling list of scenario switches + governance
   results + any `verify` drift alerts.

---

## §8. Operator-facing surface

### §8.1 Stream Deck layer

Six keys, one per frequently-used scenario:

| Key | Scenario | Stream Deck icon |
|---|---|---|
| 1 | voice_only_default | Hapax glyph |
| 2 | vinyl_mode_d | Turntable + D |
| 3 | sampler_performance_narrating | MPC + H |
| 4 | mode_d_narrator_dual_granular | Turntable + H (dual) |
| 5 | listening_only | Ear |
| 6 | silent | Mute X |

Key press invokes `hapax-audio-topology switch <scenario>`. Key LED
colour reflects live scenario state (green = active, amber = transitioning,
red = governance violation aborting).

### §8.2 Logos scenario pill

In the Logos orientation panel header, a pill:

```
[ scenario: mode_d_narrator_dual_granular | since 14:22:07 | mix 0.87 ]
```

Click → full scenario inspector showing:
- Source → sink table (every currently-broadcasting source and its path)
- Last 10 scenario transitions with timestamps
- Pending governance checks (if any source is private-by-governance
  but currently routed to broadcast_aggregate by operator override)
- L6 fader intent (visual six-channel mixer with recommended positions)

### §8.3 CLI surface for alpha/delta

```
hapax-audio-topology describe            # what's where
hapax-audio-topology verify               # am I in sync with declared
hapax-audio-topology switch silent        # emergency kill
hapax-audio-topology audit tts_kokoro     # where does this source reach?
hapax-audio-topology diff HEAD            # what did this PR change?
```

The CLI is the authoritative interactive surface. Everything the UI
shows is a view of CLI state.

### §8.4 Compositor overlay (on-broadcast)

Optional (default off): an always-on-top overlay on the operator
monitor (NOT on broadcast) showing:

```
SCENARIO: mode_d_narrator_dual_granular
MIX: 0.87    LUFS: -14.2    PEAK: -1.4 dBTP
SOURCES ON AIR: vinyl_handytrax, tts_kokoro, rode_wireless_pro
PENDING FADER CHANGE: ch 4 AUX 1 → UP (operator action required)
```

Driven by the same telemetry as §7; lives in the existing `visual-layer-aggregator`
→ compositor overlay system (Pango renderer, operator-only region).

---

## §9. Open questions + risks

1. **Byte-equivalent golden test fragility.** Phase 1's
   byte-equivalence test depends on PipeWire's parser being
   whitespace/formatting tolerant. If the parser ever becomes
   whitespace-sensitive, the golden test becomes a CI-only
   equivalence test and runtime equivalence is verified by
   `verify --strict`. Acceptable fallback.

2. **L6 hardware state not enumerable over USB.** The L6 does not
   expose fader positions or AUX levels over USB multitrack; we can
   only enumerate which multitrack channels carry signal. The scenario
   resolver detects "signal where declared absent" (e.g. unexpected ch
   6 audio during a scenario that mutes it) and flags drift, but
   cannot detect "ch 4 AUX 1 is at 12 o'clock instead of unity."
   Fader intent is operator-enforced, not software-enforced. The
   design accepts this — the scenario pill reminds the operator of
   the intent each switch.

3. **Evil Pet scene recall latency.** Mode D MIDI PC scene recall is
   documented at < 50 ms on the S-4; the Evil Pet has no documented
   SysEx recall spec. Worst case, scene transition during a live
   broadcast produces a 100–300 ms glitch. Mitigation: scene
   transitions scheduled by the scenario resolver during silent
   moments (detected via VAD on `hapax-operator-mic-tap`), or the
   switch command deferred behind a `hapax-audio-topology
   schedule-switch <scenario> --at-silence-window` subcommand.

4. **Scenarios.yaml staleness.** If an engineer edits
   `scenarios.yaml` by hand (forbidden, but enforceable only by
   convention), the derived Tier 3 diverges from Tier 2. Mitigation:
   pre-commit hook that re-runs `generate` and fails if scenarios.yaml
   changed without a corresponding topology.yaml change.

5. **Mutex solver correctness.** The mutex solver is the load-bearing
   safety property. Property-based tests (Hypothesis) over all
   scenarios × all mutex-group assignments should prove: for every
   scenario, at most one writer claims each mutex group, and the
   forbidden pairs (Mode D + any voice tier using EP granular) are
   never co-active. Tests in
   `tests/shared/audio/test_mutex_invariants.py`.

6. **Runtime-dynamic sources.** If the operator plugs in a new audio
   device mid-stream (new USB interface, second phone mic, etc.), the
   schema currently requires a PR to add it. Mitigation: a
   `hapax-audio-topology register --adhoc` subcommand that adds a
   runtime-only source entry with `private_by_governance: true` and
   `broadcast_default: false` — any escalation to broadcast requires
   the explicit scenario route.

7. **Subsumption of the existing shell check.** `scripts/audio-topology-check.sh`
   currently emits JSON violations consumed by the notification
   system (the 2026-04-19 leak finding was captured by this script).
   The `verify --strict` migration path must preserve the violation
   vocabulary. Tracked as a Phase 5 item: port the shell script's
   violation classes into `shared/audio/topology_diff.py` with unit
   tests pinning the exact strings.

8. **Generated files in-tree vs gitignored.** The generator writes to
   `config/pipewire/generated/`. Two options: (a) commit the generated
   files for reviewability — reviewers see the emitted conf diff; (b)
   gitignore them and rely on `generate` being deterministic. Option
   (a) chosen: the diff is small, CI re-runs `generate` and fails if
   it diverges from committed. This is the same pattern used for
   other generated code in the repo.

9. **Voice-fx preset space growth.** With tiers T0..T6 × programme
   roles × stimmung bins, the preset space is combinatorial. Current
   `voice-fx-*.conf` presets are hand-authored. Going forward, the
   generator needs a preset-interpolation layer (piecewise linear in
   the 9-dim vector, which `vocal_chain.py` already owns) so a single
   `preset: voice_studio_t2_showcase` resolves to the CC state
   computed from the tier's 9-dim vector, not an in-tree file. Tracked
   as Phase 6+ work.

10. **What happens if topology.yaml is broken.** The generator's
    `validate_invariants` must fail cleanly (no partial writes) if the
    YAML is malformed. Atomic write with tmp+rename is the mechanism;
    pytest fixtures that inject malformed YAML cover the regression.

---

## §10. Success criteria

The design is successful when:

1. Any audio-topology change (new source, retired source, channel
   repurposed) is a single-file PR editing `topology.yaml` only. No
   hand-edits to PipeWire confs.
2. `hapax-audio-topology verify` exits zero at all times in normal
   operation; any non-zero exit is either a real drift (investigate)
   or a transitional state during `switch`.
3. The operator can say "I want X on livestream, Y on monitors, Z via
   Evil Pet" and that maps cleanly to a named scenario or a new
   scenario that compiles in one edit.
4. Every live broadcast interval has an attributable scenario; every
   source in the broadcast aggregate is declared in Tier 1 with
   matching governance class.
5. No audio-routing mistake during livestream tonight reoccurs after
   Phase 5 — the scenarios that failed tonight (stale targets, dead
   wires, ambiguous `hapax-private` semantics) are impossible to
   instantiate in the new schema.
6. Time-to-diagnose an audio routing issue drops from "read 4 config
   files and the L6" to "run `hapax-audio-topology audit <source>`."

---

## §11. References

### Internal research this doc unifies
- `docs/research/2026-04-20-audio-normalization-ducking-strategy.md`
- `docs/research/2026-04-20-dual-fx-routing-design.md`
- `docs/research/2026-04-20-mixquality-skeleton-design.md`
- `docs/research/2026-04-20-voice-transformation-tier-spectrum.md`
- `docs/research/2026-04-20-mode-d-voice-tier-mutex.md`
- `docs/research/2026-04-19-audio-path-baseline.md`
- `docs/research/2026-04-14-audio-path-baseline.md`
- `docs/research/2026-04-14-audio-path-baseline-errata.md`
- `docs/runbooks/audio-topology.md`

### Current configs superseded-in-intent
- `config/pipewire/voice-fx-chain.conf`
- `config/pipewire/voice-fx-radio.conf`
- `config/pipewire/hapax-stream-split.conf`
- `config/pipewire/hapax-l6-evilpet-capture.conf`
- `config/pipewire/hapax-vinyl-to-stream.conf`
- `config/pipewire/hapax-livestream-tap.conf`
- `config/pipewire/hapax-echo-cancel.conf`
- `config/pipewire/voice-over-ytube-duck.conf`
- `config/pipewire/yt-over-24c-duck.conf`
- `config/wireplumber/50-hapax-voice-duck.conf`
- `config/wireplumber/60-ryzen-analog-always.conf`
- `scripts/audio-topology-check.sh`

### External
- [PipeWire filter-chain module docs](https://docs.pipewire.org/page_module_filter_chain.html)
- [WirePlumber policy docs](https://pipewire.pages.freedesktop.org/wireplumber/)
- [EBU R128 loudness](https://tech.ebu.ch/publications/r128)
- [Zoom LiveTrak L6 Operation Manual](https://zoomcorp.com/manuals/l6-en/)
- [Torso S-4 Manual §3.7 (Effects Processor mode)](https://downloads.torsoelectronics.com/s-4/manual/)
- [Endorphin.es Evil Pet — midi.guide](https://midi.guide/d/endorphines/evil-pet/)
