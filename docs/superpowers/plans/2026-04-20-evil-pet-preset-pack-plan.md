# Hapax Evil Pet `.evl` Preset Pack Plan

> **For agentic workers:** REQUIRED SUB-SKILL — superpowers:executing-plans.

**Goal:** ship a Hapax-curated preset pack on the Evil Pet SD card so
each voice tier has a recall-able scene with `midi_receive_cc: true`.
Solves the factory-preset trap where `.evl` files ship with
`midi_receive_cc: false`, silently dropping every CC write.

**Architecture:** the Evil Pet stores `.evl` preset files on its SD
card at `/presets/<slot>/<name>.evl`. Each is a JSON-ish document
with parameter values + a `midi_receive_cc` flag. Factory presets
default that flag to `false`, which means `vocal_chain` / `vinyl_chain`
CC emissions never land. A Hapax preset pack overwrites specific
slots with CC-receiving variants, one per tier plus Mode D, plus a
dry bypass.

**Tech stack:** `.evl` file generation in Python + an SD-card
deployment script.

**Research reference:** `docs/research/2026-04-20-evil-pet-factory-presets-midi.md`.

---

## Phase 1 — `.evl` format reverse

- [ ] Write failing test: `parse_evl(bytes)` returns a dataclass with
      `parameters: dict[int, int]` (CC → value), `name: str`,
      `midi_receive_cc: bool`, plus any additional fields the factory
      files carry.
- [ ] Locate a factory `.evl` on the SD card, capture its bytes via
      `hexdump`, document format in
      `docs/research/2026-04-20-evil-pet-factory-presets-midi.md` §4
      (write-up as the reverse progresses).
- [ ] Implement `shared/evil_pet/evl_format.py` parser + round-trip
      serializer.
- [ ] Commit.

## Phase 2 — Preset-pack authoring tool

- [ ] Write failing test: `build_preset(name, tier, cc_writes)`
      serializes a valid `.evl` with `midi_receive_cc=True` and the
      CCs from the tier's `cc_overrides` + base-scene CCs.
- [ ] Implement `scripts/evil-pet-build-preset-pack.py`.
- [ ] Emit 9 presets: `HAPAX-T0..T6`, `HAPAX-MODE-D`, `HAPAX-BYPASS`.
- [ ] Commit.

## Phase 3 — SD-card deployment

- [ ] Document operator flow: power-off Evil Pet, remove SD, mount,
      copy `preset-pack/*.evl` to `/presets/`, unmount, reinsert,
      boot, verify scroll through preset list shows the new entries.
- [ ] Optionally: a `scripts/evil-pet-deploy-preset-pack.sh` that
      copies the pack to a user-provided mount point with dry-run
      default.
- [ ] Commit.

## Phase 4 — Preset-recall MIDI glue

- [ ] Write failing test: `recall_preset(name)` sends the right
      bank-select + program-change CC sequence for the Evil Pet.
      (Needs Phase 5 operator-verified MIDI mapping of Program Change
      behavior — the Evil Pet's OS has historically not supported PC;
      verify current firmware.)
- [ ] Depending on Phase 5 result, implement as PC message OR as
      direct CC 16-burst of the preset's parameter values, bypassing
      preset-recall entirely.
- [ ] Commit.

## Phase 5 — Evil Pet firmware decision gate

- [ ] Research (or verify operator report) whether Evil Pet v1.42
      supports Program Change MIDI messages. If yes, Phase 4 uses PC.
      If no, Phase 4 falls back to CC-burst per-parameter.
- [ ] Upgrade firmware per
      `docs/research/2026-04-20-fx-firmware-upgrade-procedures.md` §3
      if a newer version adds PC support.

## Rollout gate

Phase 1–2 ship as pure Python. Phase 3 requires operator physical
action. Phase 4–5 deferred until format reverse + firmware
confirmation.

## Deferred

- Auto-export of current preset set from Evil Pet (no known MIDI
  dump command).
- Per-programme preset preference hinting — Programme envelope can
  name a preferred preset via a new `evil_pet_preset` field; Phase
  6 task.
