# Camera and Visual Capability Abstraction — Investigation

**Date:** 2026-04-20
**Author:** alpha (research)
**Status:** Research; recommendation pending operator decision
**Trigger:** Operator question after 1+ minute of raw-evidence camera debug
(`lsusb` → `v4l2-ctl --list-devices` → `journalctl` → `OBS_Virtual_Camera`
inspection) on a BRIO disconnect/reconnect. Open question: does the camera
and visual surface need an abstraction layer parallel to `audio-topology`?

---

## Part 1 — What the audio-topology abstraction does

### Module surface

The audio-topology layer is implemented as four files plus one canonical YAML:

| File | LOC | Purpose |
|---|---|---|
| `shared/audio_topology.py` | 255 | Pydantic descriptor (`Node`, `Edge`, `ChannelMap`, `TopologyDescriptor`). Schema v1, frozen models, YAML round-trip. |
| `shared/audio_topology_generator.py` | 268 | Descriptor → PipeWire `.conf` fragments (one file per node), per-kind formatters (`alsa_source`, `alsa_sink`, `filter_chain`, `loopback`, `tap`). |
| `shared/audio_topology_inspector.py` | 298 | `pw-dump` JSON → live `TopologyDescriptor`. Heuristic `_classify_node_kind` covers PipeWire's gap (modules without `factory.name` props). |
| `scripts/hapax-audio-topology` | 452 | CLI: `describe`, `generate`, `diff`, `verify`, `audit`, `watchdog`. Exit codes match `diff(1)` (0 / 1 / 2). |
| `config/audio-topology.yaml` | ~1 file | Canonical descriptor — single source of truth. |

Total: ~1,273 LOC across four modules, with one canonical descriptor.

### What complexity it hides

From `shared/audio_topology.py:5-10`:

> "...today is a bag of `.conf` files under `config/pipewire/` plus a few
> WirePlumber policy drops; drift is silent (you only notice when the
> livestream goes dead or OBS clips) and there is no way to answer
> 'what is the current graph?' without reading `pw-dump` JSON by hand."

Specifically:
- Hand-authored PipeWire `.conf` files for filter-chains, loopbacks, taps,
  multitrack sources (12-channel L6), makeup-gain stages.
- WirePlumber policy drift.
- ALSA card profile glitches (Ryzen HDA codec pin-routing stale, see
  `reference_ryzen_codec_pin_glitch`).
- `pw-dump` JSON shape (interface nodes, links, ports, factory-less hapax-*
  module nodes that need name-pattern classification).

### API surface

The CLI is the operator-facing surface:

- `describe <yaml>` — human-readable node/edge dump.
- `generate <yaml> [--output-dir <dir>]` — emit `.conf` fragments.
- `diff <left.yaml> <right.yaml>` — structural drift between two descriptors.
- `verify <yaml> [--dump-file path] [--profile vinyl]` — descriptor vs
  live `pw-dump` graph; exit 2 on drift; vinyl-profile chain check.
- `audit <yaml>` — same comparison, exit 0 always (for log/ntfy piping).
- `watchdog [--card …] [--profile …] [--dry-run]` — Ryzen pin-glitch
  recovery (`pactl set-card-profile <card> off` then on).

### Layer it sits on top of

PipeWire (via `pw-dump` JSON, `pactl`, `.conf` fragments dropped into
`config/pipewire/`), WirePlumber policy drops, ALSA cards.

### Tests / verify

- `verify` subcommand in the CLI is the canonical "is the live graph
  what I declared?" check (`scripts/hapax-audio-topology:245-295`).
- Per-node round-trip pins (`tests/test_audio_topology_*`).
- Vinyl profile adds `shared.vinyl_chain_verify.verify_vinyl_chain` for
  broadcast-chain-specific findings.

### Operational pain that motivated it

Git log on `shared/audio_topology*.py` shows the build order:

```
bb04ac104 feat(audio-topology): declarative descriptor schema (CLI Phase 1)
5760634af feat(audio-topology): descriptor → PipeWire conf generator (Phase 2)
3a7ec2670 feat(audio-topology): hapax-audio-topology CLI (Phase 3 — describe/generate/diff)
55491704a feat(audio-topology): pw-dump live-graph inspector (CLI Phase 4)
1d21747c7 feat(audio-topology): wire verify + audit subcommands (Phase 4+)
138de264f feat(audio-topology): Ryzen pin-glitch watchdog subcommand (Phase 5)
71ac1accf feat(audio-topology): canonical config/audio-topology.yaml + regression pins (Phase 6)
e6396c9f0 feat(audio-topology): match-by-pipewire-name + factory-less hapax-* classification (#216)
09c67e90d feat(audio-topology): verify --profile vinyl subcommand (D-24 §11.4)
```

Drivers, in order: silent drift between hand-authored confs and the live
graph; livestream going dead with no diagnostic command; Ryzen codec
pin-routing-stale glitches after PipeWire restarts; vinyl-broadcast chain
verification needs.

---

## Part 2 — Camera complexity audit

### USB device discovery and stable identifiers

- VID/PID enumeration is hand-coded inside `udev_monitor.py:104-107`
  (`046d:085e` BRIO, `046d:08e5` C920). Studio cameras are pinned to
  stable `/dev/v4l/by-id/usb-046d_..._SERIAL-video-index0` paths in
  `systemd/units/studio-camera-setup.sh:36-81` and
  `systemd/units/studio-camera-reconfigure.sh:35-49`.
- `pyudev` watches `video4linux` and `usb` subsystems
  (`agents/studio_compositor/udev_monitor.py:48-58`); `add` and
  `remove` events route into `PipelineManager.on_device_added` /
  `on_device_removed`.
- `PipelineManager.role_for_device_node` and `role_for_serial`
  (`agents/studio_compositor/pipeline_manager.py:347-370`) map device
  nodes and serials to roles.

### `/dev/video*` claim semantics

- `/dev/video42` — the compositor output (v4l2loopback), referenced
  across `agents/studio_compositor/{compositor,pipeline,fx_chain,
  models,layout_loader,output_router,...}` (10 files).
- `/dev/video10` — OBS Virtual Camera (v4l2loopback); documented in
  `docs/streaming/2026-04-10-stream-audit-plan.md:27-28` only. **No
  systemd unit, no descriptor, no enforcement.** It is operator-managed
  and visible only to whoever knows to grep `lsusb` is the wrong tool
  and `v4l2-ctl --list-devices` is the right one.
- `/dev/video50` — additional v4l2loopback (per
  `docs/streaming/2026-04-10-stream-audit-plan.md:46`).
- The `v4l2loopback` kernel module's loaded state, `video_nr` arguments,
  and per-device labels are not described anywhere structured. There is
  **no `v4l2loopback.conf` in the council repo** — the module is loaded
  out-of-band (modprobe/grub/manual).

### 5-state recovery FSM

`agents/studio_compositor/camera_state_machine.py:24-29` defines
`HEALTHY → DEGRADED → OFFLINE → RECOVERING → DEAD`. Surfacing:

- Internal: `CameraStateMachine.state` property (per-camera lock).
- External: Prometheus metrics exporter on `127.0.0.1:9482` (per
  `agents/manifests/studio_compositor.yaml` + `metrics.py`).
- Transition log: `journalctl --user -u studio-compositor.service`
  with a `camera state: role=… X→Y reason=…` log line
  (`camera_state_machine.py:113-120`).
- Operator query path: `studio-smoke-test.sh` parses
  `studio_camera_state{role=…,state=healthy}` from the metrics endpoint
  (`scripts/studio-smoke-test.sh:53,78,87`).

There is **no `hapax-camera verify` command**. The smoke test
(`studio-smoke-test.sh`) is the closest equivalent — but it is a
livestream-readiness gate, not a single-shot describe-the-graph tool.

### Operator's debug chain — could a single command have collapsed it?

The operator's path was:

1. `lsusb | grep BRIO` — confirm the device is attached.
2. `v4l2-ctl --list-devices` — see which `/dev/video*` it owns.
3. `journalctl --user -u studio-compositor.service` — find the udev
   event chain.
4. `v4l2-ctl --list-devices` again — confirm `/dev/video10` is
   `OBS_Virtual_Camera`, not BRIO.

A `hapax-camera verify` command analogous to `hapax-audio-topology
verify` could collapse all four. The required information is already
inside the running process (FSM state, role-to-device map, USB serial
binding) plus three fast subprocess calls (`lsusb`, `v4l2-ctl
--list-devices`, `pw-dump` for the loopback claim). All assembled into
one descriptor diff.

### udev rule contents

`systemd/udev/70-studio-cameras.rules` (3 stanzas, 28 lines) does two
things:
- Disables USB autosuspend for `046d:085e` and `046d:08e5` (Phase 1).
- On `add` of a video4linux capture device with one of the two VID/PIDs,
  triggers `studio-camera-reconfigure@<kernel-name>.service`
  (`SYSTEMD_USER_WANTS`) which re-applies model-specific `v4l2-ctl`
  settings.

It does **not** declare which roles attach to which serials — that
mapping is duplicated three times (in `shared/cameras.py`, in
`agents/studio_compositor/cameras.py` `CameraSpec`, and in
`systemd/units/studio-camera-setup.sh`).

### Pi NoIR fleet

3 Raspberry Pis (Pi-1 ir-desk, Pi-2 ir-room, Pi-6 ir-overhead) run
`hapax-ir-edge`, POST IR/biometric JSON to council. **No `/dev/video*`
on the workstation.** The fusion happens in
`agents/hapax_daimonion/backends/ir_presence.py`. Out of scope for the
camera abstraction; flagged as a separate concern, possibly worth
unifying later under a "perception sources" abstraction (workstation
v4l2 + edge HTTP) but not yet.

### Existing camera-topology layer?

- No `shared/camera_topology/` module.
- No `shared/visual_topology/` module.
- No `hapax-camera` script in `scripts/`.
- `shared/cameras.py` (140 LOC) is a static `CAMERAS` tuple of
  `CameraSpec(role, short, w, h, class, person_enrichment, position,
  yaw)`. No live-graph awareness. No claims-tracking. No verify.
- `agents/studio_compositor/cameras.py` (273 LOC) is a Pydantic
  `CameraSpec` per camera plus the snapshot/face-obscure GStreamer
  branch. Operates on roles, not on the v4l2 graph as a whole.
- `shared/compositor_model.py` (327 LOC) is the closest existing
  abstraction — it models `Source` / `Surface` / `Assignment` /
  `Layout` and validates references, but it is a **scene-description**
  abstraction (what to composite, where), not a **device-topology**
  abstraction (what claims `/dev/video*`, what the kernel sees).

So there is **no camera-topology layer**. The pieces that do exist
(per-camera FSM, metrics exporter, udev monitor, smoke test) are all
within the compositor process's own bookkeeping; nothing exposes the
USB ↔ `/dev/video*` ↔ role ↔ FSM-state ↔ pw-dump-claim mapping as a
single inspectable surface.

---

## Part 3 — Visual capability complexity audit

### Effect graph (`agents/effect_graph/`)

1,814 LOC across 9 files: `compiler.py`, `pipeline.py`, `registry.py`,
`runtime.py`, `types.py`, `visual_governance.py`, `wgsl_compiler.py`,
`wgsl_transpiler.py`, `modulator.py`. 57 WGSL shader nodes plus 60 JSON
node manifests in `agents/shaders/nodes/`. **This is itself an
abstraction layer**: shader nodes are JSON-described
(`registry.py:39-60`), composed into `EffectGraph`s, compiled into
`ExecutionPlan`s, and hot-loaded by the wgpu backend.

### Reverie / wgpu pipeline

- `agents/imagination/` is a stub directory (METADATA only).
- `agents/imagination_daemon/` ships the bootstrap (`__main__.py`).
- `agents/reverie/` is the active surface (12 modules: bootstrap,
  mixer, governance, content_injector, satellites, uniforms,
  graph_builder, ...).

Two render paths exist: the GStreamer compositor pipeline (CUDA tiling,
camera FX chain, `/dev/video42` egress) and the Rust `hapax-imagination`
wgpu daemon (8-pass vocabulary graph, content slots, JPEG to
`/dev/shm/hapax-visual/frame.jpg`). They share the effect_graph
abstraction (Python compiles the WGSL plan; Rust executes it).

### Compositor sources / wards / effects

`shared/compositor_model.py` is already a structured abstraction with
`SourceKind` covering `camera`, `video`, `shader`, `image`, `text`,
`cairo`, `external_rgba`, `ndi`, `generative`. The "wards vs effects"
taxonomy (per memory `reference_wards_taxonomy`) maps cleanly:

- **effects** = `shader` sources (WGSL/effect_graph nodes).
- **wards** = `cairo`, `image`, `text`, `external_rgba` sources
  (sierpinski, vitruvian/token-pole, album art, captions, pango
  overlays, PiPs, hothouse panels).

The taxonomy is consistent and well-covered by `compositor_model.py`.
**Visual *content* is not the operator's pain point** — what is missing
is a verify-and-introspect entry point for *visual capabilities*: which
shader nodes loaded, which sources registered, which wards live, which
egress sinks attached.

### Single "what visual capabilities are available?" entry point

There isn't one. Operator's current options:

- Walk `agents/shaders/nodes/*.json` for the shader inventory.
- Read `SourceRegistry.ids()` from a running compositor process.
- Inspect `shared/compositor_model.SourceKind` literals.
- Read `/dev/shm/hapax-imagination/pipeline/` for the active wgpu plan.
- Curl `:9482/metrics` for camera FSM state.
- Curl `:8053/snapshot` for the visual surface JPEG.

Five surfaces, no aggregated answer.

---

## Part 4 — Recommendation

### Option A — Camera-topology layer parallel to audio-topology

**Shape:** `shared/camera_topology.py` (Pydantic `CameraSpec`, `V4l2Loopback`,
`Claim`, `CameraTopology`), `shared/camera_topology_inspector.py`
(reads `/sys/class/video4linux/`, `lsusb -v`, `v4l2-ctl
--list-devices`, `pw-dump` for loopback claims), `scripts/hapax-camera`
(subcommands `describe`, `verify`, `claims`, `recover`).

**What it solves:**
- Single command answers "what cameras exist, what `/dev/video*` they
  claim, what FSM state they're in, which loopbacks are loaded, who
  owns them."
- Eliminates the operator's 4-step debug chain.
- Codifies the v4l2loopback layout (`/dev/video10`, `/dev/video42`,
  `/dev/video50`) which is currently undocumented in this repo.
- De-duplicates the role/serial/device mapping (currently in three
  places: `shared/cameras.py`, `agents/studio_compositor/cameras.py`,
  `systemd/units/studio-camera-setup.sh`).

**What it costs:** ~1,000-1,200 LOC plus a canonical
`config/camera-topology.yaml`. Mirrors audio-topology's split (~255 +
~298 + ~268 + ~452 = ~1,273 LOC for descriptor + generator +
inspector + CLI; camera version probably skips the generator since
udev rules are already declarative).

**Risk:** Duplicates work the camera 24/7 resilience epic already
shipped (FSM, metrics exporter, smoke test, udev monitor). Distinct
because that epic owns *runtime* recovery; topology owns *description
and verification*. Risk is low if the topology layer reads from the
metrics exporter rather than re-implementing FSM state inspection.

**Owner:** alpha (compositor/HARDM/wards zone per trio split).

**Sequencing:** Does not block other work. Benefits from waiting for
Source-Registry Completion Epic (in flight) to land its observability
gauges first — those become inputs to `verify`.

### Option B — Unified visual-topology layer covering cameras AND effects/wards

**Shape:** `shared/visual_topology.py` aggregates camera devices,
v4l2loopback claims, registered shader nodes, registered cairo/text
sources, layouts, render targets, output sinks.

**What it solves:** A single `hapax-visual verify` answers all of "what
visual capabilities are available, what state are they in, what's
attached to what."

**What it costs:** ~2,000-2,500 LOC. Larger surface; cuts across
compositor + reverie + effect_graph.

**Risk:** Premature unification. The wards/effects taxonomy is already
clean and covered by `compositor_model.py`; collapsing them with
device-topology mixes scene description with hardware enumeration. The
operator's pain is on the *device/claims* side, not the
*content/wards/effects* side. Building both at once would slow the
intervention that actually closes the operator's debug chain.

**Owner:** alpha + delta jointly (alpha=compositor; delta would only
be needed if the layer crosses into audio-topology cross-references).

**Sequencing:** Blocked by completion of Source-Registry Completion
Epic. Larger; pushes the actual debug-chain fix back two-three weeks.

### Option C — No new abstraction; add verify to existing pieces

**Shape:** Extend `studio-smoke-test.sh` into `hapax-camera-verify`
(read metrics endpoint, parse `lsusb`, parse `v4l2-ctl --list-devices`,
print one summary). Add a section to `compositor_model.py` describing
v4l2loopback expectations as a constant.

**What it solves:** The single-command debug chain at minimum cost.

**What it costs:** ~150-300 LOC, mostly bash + Python helpers.

**Risk:** Perpetuates the operator's pain in a different shape — every
new diagnostic surface needs hand-stitching, no canonical descriptor
to drift-check against, no `diff` between declared and live state, no
generator. Audio-topology started with similar small-script intent
and grew into a four-phase epic precisely because the small-script
approach kept failing to close the loop on drift.

**Owner:** alpha; trivially small.

**Sequencing:** Could ship in a single PR, no dependencies.

### Recommendation

**Option A.** Build a camera-topology layer, intentionally parallel to
audio-topology, scoped to *description, claims, and verify*. Skip the
generator phase (udev rules already declarative). Read FSM state from
the existing Prometheus metrics exporter. Read v4l2loopback from
`/sys/class/video4linux/`. Read PipeWire/OBS claims from `pw-dump` (the
inspector module already exists for audio-topology and the JSON shape
covers video nodes too).

The operator's debug pain has the same shape as the original
audio-topology pain (silent drift, no single source of truth, no
verify command, the operator finding out at livestream-dead time).
Audio-topology shipped a clean abstraction in ~1,273 LOC across six
phases; the camera version is smaller because it can skip generation
and reuse the inspector pattern. **LOC estimate: 800-1,000 across
descriptor (~200) + inspector (~300) + CLI (~400) + canonical
`config/camera-topology.yaml` (~100).**

Defer Option B (unified visual-topology). The wards/effects abstraction
is already clean (`compositor_model.SourceKind`); device-topology is
the missing piece. Unify only if a second debug-chain incident
specifically crosses scene-description and device-claims.

### What `hapax-camera verify` would output for the operator's bug

For the operator's current incident, the command would have printed
something like:

```
$ hapax-camera verify

# camera topology — declared 6 cameras, 3 v4l2loopbacks
declared cameras:
  brio-operator   serial=5342C819  device=/dev/v4l/by-id/usb-046d_Logitech_BRIO_5342C819-video-index0
  brio-room       serial=43B0576A  device=/dev/v4l/by-id/usb-046d_Logitech_BRIO_43B0576A-video-index0
  brio-synths     serial=9726C031  device=/dev/v4l/by-id/usb-046d_Logitech_BRIO_9726C031-video-index0
  c920-desk       serial=2657DFCF  device=/dev/v4l/by-id/usb-046d_HD_Pro_Webcam_C920_2657DFCF-video-index0
  c920-room       serial=86B6B75F  device=/dev/v4l/by-id/usb-046d_HD_Pro_Webcam_C920_86B6B75F-video-index0
  c920-overhead   serial=7B88C71F  device=/dev/v4l/by-id/usb-046d_HD_Pro_Webcam_C920_7B88C71F-video-index0

declared loopbacks:
  /dev/video42    label=hapax-compositor-out      claimed-by=studio-compositor.service
  /dev/video10    label=OBS_Virtual_Camera        claimed-by=obs (operator)
  /dev/video50    label=hapax-aux-out             claimed-by=(unclaimed)

live state:
  brio-operator   /dev/video2  HEALTHY  last-add=11:46  reconfigure-applied=yes
  brio-room       /dev/video6  HEALTHY  last-add=10:28
  brio-synths     /dev/video8  HEALTHY  last-add=10:28
  c920-desk       /dev/video0  HEALTHY  last-add=10:28
  c920-room       /dev/video4  HEALTHY  last-add=10:28
  c920-overhead   /dev/video12 HEALTHY  last-add=10:28
  /dev/video10    OBS_Virtual_Camera v4l2loopback (OK — operator-owned)
  /dev/video42    hapax-compositor-out v4l2loopback (claimed by gst-launch — OK)
  /dev/video50    hapax-aux-out v4l2loopback (unclaimed — OK)

drift: NONE (all declared roles healthy; no unexpected loopbacks)

note: brio-operator was re-added 11:46 (others 10:28) — this is a 5h
gap re-enumeration; FSM transitioned HEALTHY→OFFLINE→RECOVERING→
HEALTHY at 11:46:03 (see metrics studio_camera_recovery_total{role=
"brio-operator"}=1).
```

That single command would have shipped instantly what took the original
agent 1+ minute of multi-tool investigation, and would also have made
clear that `/dev/video10 = OBS_Virtual_Camera` is **expected** rather
than a misclaimed BRIO node — a confusion that consumed real debug
time.

---

## Filed work item

Recommend filing as `operator_queue_adds_alpha`:

> **Build `shared/camera_topology` parallel to `audio_topology`.** Scope:
> Pydantic descriptor (`CameraSpec`, `V4l2LoopbackClaim`,
> `CameraTopology`), inspector reading `/sys/class/video4linux/`,
> `lsusb`, `v4l2-ctl --list-devices`, `pw-dump`, and the
> `studio-compositor` Prometheus metrics exporter; `scripts/hapax-camera`
> CLI with `describe`, `verify`, `claims` subcommands; canonical
> `config/camera-topology.yaml`. Skip the conf-generator phase (udev
> rules already declarative). Estimate ~900 LOC. Owner: alpha. Does
> not block other work. Should land after Source-Registry Completion
> Epic so observability gauges are inputs.

---

## Sources cited

- `shared/audio_topology.py` (descriptor, 255 LOC)
- `shared/audio_topology_generator.py` (generator, 268 LOC)
- `shared/audio_topology_inspector.py` (pw-dump → descriptor, 298 LOC)
- `scripts/hapax-audio-topology` (CLI, 452 LOC)
- `config/audio-topology.yaml` (canonical descriptor)
- `agents/studio_compositor/camera_state_machine.py` (235 LOC, 5-state FSM)
- `agents/studio_compositor/pipeline_manager.py:347-370`
  (`role_for_device_node` / `role_for_serial`)
- `agents/studio_compositor/udev_monitor.py` (118 LOC, pyudev bridge)
- `agents/studio_compositor/cameras.py` (273 LOC, snapshot branch +
  CameraSpec)
- `shared/cameras.py` (140 LOC, static `CAMERAS` tuple)
- `shared/compositor_model.py` (327 LOC, Source/Surface/Assignment/Layout)
- `agents/studio_compositor/source_registry.py` (SourceRegistry)
- `agents/effect_graph/` (1,814 LOC across 9 modules)
- `agents/shaders/nodes/` (57 WGSL + 60 JSON node manifests)
- `systemd/udev/70-studio-cameras.rules` (28 lines)
- `systemd/units/studio-camera-setup.sh` (82 lines, hard-coded
  per-serial v4l2-ctl)
- `systemd/units/studio-camera-reconfigure.sh` (58 lines, post-
  re-enumeration v4l2-ctl)
- `scripts/studio-install-udev-rules.sh` (41 lines)
- `scripts/studio-smoke-test.sh` (109 lines)
- `docs/streaming/2026-04-10-stream-audit-plan.md:27-28,46`
  (v4l2loopback `/dev/video10`, `/dev/video42`, `/dev/video50`)
- `docs/superpowers/handoff/2026-04-13-alpha-camera-247-epic-handoff.md`
  (camera 24/7 resilience epic retirement)
- Memory: `reference_wards_taxonomy`, `project_studio_cameras`,
  `reference_ryzen_codec_pin_glitch`
