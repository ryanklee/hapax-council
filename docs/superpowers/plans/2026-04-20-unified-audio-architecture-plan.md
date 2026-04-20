# Unified Audio Topology Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL — superpowers:subagent-driven-development
> or superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax.

**Goal:** ship the `hapax-audio-topology` CLI + descriptor format that
turns the ad-hoc PipeWire conf collection into a declarative,
verifiable, single-source-of-truth topology for every audio path
the livestream depends on.

**Architecture:** one declarative YAML descriptor per logical graph
(today's graph = hapax-livestream + hapax-private + voice-fx-chain +
l6-evilpet-capture). A CLI generates the set of PipeWire/WirePlumber
conf files from the descriptor, a verifier asserts live-graph parity
with the descriptor, an audit subcommand diffs current vs declared,
a migration subcommand applies descriptor changes to the live graph
atomically.

**Tech stack:** Python 3.12+, Pydantic for descriptors, `pactl` /
`pw-dump` for live-graph inspection, PipeWire `filter-chain` +
WirePlumber policy conf as outputs.

**Research reference:** `docs/research/2026-04-20-unified-audio-architecture-design.md`.

---

## Phase 1 — Descriptor schema

- [ ] Write failing test: `TopologyDescriptor` Pydantic model parses
      a sample descriptor capturing hapax-livestream + hapax-private +
      voice-fx-chain + l6-evilpet-capture as nodes + edges.
- [ ] Run test, verify fail.
- [ ] Implement `shared/audio_topology.py` with `Node`, `Edge`,
      `TopologyDescriptor` Pydantic models. Node types:
      `{alsa-source, alsa-sink, filter-chain, loopback, tap}`. Edge
      carries `source`, `target`, `channels`, `makeup_gain_db`.
- [ ] Run tests, verify pass.
- [ ] Commit.

## Phase 2 — Descriptor → conf generator

- [ ] Write failing test: `generate_confs(descriptor)` emits a dict
      `{"pipewire/stream-split.conf": "...", ...}` and the generated
      content round-trips through the descriptor parser without loss.
- [ ] Implement `shared/audio_topology/generator.py`. Jinja-free;
      f-string templates per node type.
- [ ] Commit.

## Phase 3 — CLI scaffolding

- [ ] Write failing test: `hapax-audio-topology describe` prints
      descriptor YAML for the current topology. `hapax-audio-topology
      verify` exits 0 when live graph matches, 1 when drift detected.
- [ ] Implement `scripts/hapax-audio-topology` (argparse; commands
      `describe|generate|verify|switch|audit|diff`).
- [ ] `verify` uses `pw-dump` JSON output compared against the
      descriptor's expected graph. Drift report prints specific
      node/edge diffs.
- [ ] Commit.

## Phase 4 — Live-graph inspection

- [ ] Write failing test: `pw_dump_to_descriptor(json)` converts
      `pw-dump` output into a `TopologyDescriptor` instance.
- [ ] Implement parser in `shared/audio_topology/inspect.py`.
- [ ] Covers filter-chain nodes, loopback modules, multitrack ALSA
      sources. Unknown node types surface in the audit diff but don't
      block verify.
- [ ] Commit.

## Phase 5 — Ryzen-codec pin-glitch watchdog

- [ ] Write failing test: `verify` detects
      "sink RUNNING + sink-input active + >5 s elapsed + zero RMS on
      monitor port" and returns a specific `PIN_GLITCH` diagnostic.
- [ ] Implement detection (monitor port RMS via `pactl` metering).
- [ ] Auto-fix subcommand: runs the `pactl set-card-profile … off &&
      … output:analog-stereo` sequence from
      `reference_ryzen_codec_pin_glitch` memory.
- [ ] Commit.

## Phase 6 — Migration to canonical descriptor

- [ ] Author `config/audio-topology.yaml` — the canonical descriptor
      capturing current live state.
- [ ] Generate conf files via `hapax-audio-topology generate`; commit
      them alongside the descriptor.
- [ ] Add CI job running `hapax-audio-topology verify` against the
      descriptor under the smoketest environment — catches drift
      before a PR merges.
- [ ] Commit.

## Rollout gate

Phase 1–4 ship as pure code. Phase 5–6 require a running
PipeWire + ALSA environment and should be rolled on the workstation
before CI.

## Dependencies

- `pactl`, `pw-dump`, `pw-cli` — all already present on CachyOS.
- No new Python deps (Pydantic already pinned).

## Deferred

- Cross-device audio graph (Wear OS → phone → council receiver).
- Redundancy failover between Ryzen + L6 USB paths.
