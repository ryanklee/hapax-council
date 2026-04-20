# FX Firmware Upgrade Procedures — Torso S-4 + Endorphin.es Evil Pet

**Date:** 2026-04-20
**Register:** Scientific, operator-facing
**Scope:** Concrete, safe firmware-upgrade procedures for the two hardware FX
devices in the LegomenaLive vocal chain: Torso Electronics S-4 and Endorphin.es
Evil Pet. Operator has approved upgrades in principle; this document specifies
discovery, latest versions, exact update sequences, safety checklists,
post-upgrade smoke tests, a separately scoped SD-card preset-authoring
opportunity for the Evil Pet, and a combined risk summary with recommended
execution order.
**Parent chain documents:**
- `docs/research/2026-04-19-evil-pet-s4-base-config.md` (signal chain + base CCs)
- `docs/research/2026-04-20-evil-pet-cc-exhaustive-map.md` (full Evil Pet CC surface)
- `docs/research/2026-04-20-evil-pet-factory-presets-midi.md` (`.evl` format + factory preset pack)
- `docs/research/2026-04-20-voice-transformation-tier-spectrum.md` (T0–T6 tier ladder)
- `shared/voice_tier.py` (7-tier catalog in code)

---

## §1. Torso S-4 firmware

### §1.1 Current-version discovery

The S-4 displays its installed OS version in the CONFIG menu. Path: tap the
`[CONFIG]` hardware button, scroll to `SYSTEM`, and the firmware version is
reported as a line item adjacent to `INSTALL UPDATE`, `USB MASS STORAGE`,
`INSTALL FACTORY SAMPLES`, and `DISPLAY BRIGHTNESS`. This is the only reliable
in-device path; Torso does not expose version via USB class-compliant MIDI or
SysEx, and the device does not auto-advertise a version string over its USB
audio interface descriptor. The version also appears briefly at boot on the
OLED splash before the main UI loads — watch for a string of the form
`S-4 OS 2.x.x`. The base-config research cites the device manual as
`The S-4 Manual 1v0v4a.pdf` (§1 of `2026-04-19-evil-pet-s4-base-config.md`),
which implies OS 1.0.4 was the installed version at the time of that manual
capture, but the operator should read the actual device and not infer from
documentation age.

There is no SD-card metadata path. The S-4's updater ingests a zipped OS
image via USB mass storage; it does not maintain an accessible `VERSION.TXT`
on any removable media. USB sysex or HID version queries are not documented by
Torso.

### §1.2 Latest version

As of 2026-04-20 the published S-4 changelog tops out at **OS 2.1.4**, released
**2026-03-05**. The 2.x generation is an entirely new engine — the June 2025
OS 2.0 release was a ground-up rewrite. Release history relevant to the
upgrade path (from the Torso changelog):

| Version | Release | Highlights |
|---|---|---|
| 2.1.4 | 2026-03-05 | DISC/TAPE audio-artifact fixes; sample-load lag fix; DEFORM corrections; TAPE shows loaded sample name |
| 2.1.3 hotfix | 2026-02-20 | USB flash drives inserted before startup detected |
| 2.1.2 hotfix | 2026-02-18 | Fix glitchy DISC playback when changing scenes |
| 2.1.1 hotfix | 2026-02-17 | Sample-load from old projects fixed; DISC `[LOAD]` restored |
| 2.1.0 | 2026-02-16 | WET mode selector (MIX / SEND); XFADE added to TAPE; new SCENE RULE |
| 2.0.4 | 2025-11-24 | LED visibility for modulated devices; **CC lag fixes across multiple params** |
| 2.0.3 | 2025-09-11 | Display boot fix; removed unintended output low-cut |
| 2.0.2 | 2025-08-25 | Light theme; LED backlight toggle; stability |
| 2.0.1 | 2025-07-17 | Display + disc stability |
| **2.0** | **2025-06-17** | Landmark rewrite: PERFORM macros, 128 SCENE snapshots per project, TEMP parameter override, COPY, MATERIAL/DISC streaming |
| 1.2.2 hotfix | 2024-12-09 | Buffer for long samples; DEFORM DECAY fix |
| 1.2.1 hotfix | 2024-11-05 | TAPE post-trim init fix |
| 1.2.0 | 2024-11-04 | TAPE TRIM; STRETCH mode; DENSITY; DJ filter smoothness; reduced CPU |
| 1.0.4 | 2024-06-19 | External USB drive support for updates; encoder browser improvements |

Three observations relevant to the vocal chain:

1. **CC lag fixes in 2.0.4.** `vocal_chain.py` emits CCs to S-4 at up to 20 Hz
   per CC (§5.3 of the base-config doc). OS 1.0.4 has known per-parameter CC
   latency issues that were addressed across the 2.0.x hotfix cycle. This is
   a direct benefit for the Hapax chain.
2. **128 SCENE snapshots per project (2.0).** The base-config doc §4.6
   specifies `HAPAX-VOX-BASE` saved to Scene 1 of 128. On 1.0.4 the scene
   ceiling is lower; on 2.0+ the 128-slot ceiling aligns exactly with the
   research's assumption. This is load-bearing for the tier ladder rollout
   if per-tier scenes become useful as fast recalls.
3. **DEFORM fixes.** DEFORM is the Color slot in the vocal chain and carries
   `intensity` (CC 95 drive) and `presence` (CC 96 compress). Any 2.x DEFORM
   correction directly benefits the chain.

### §1.3 Upgrade procedure (step by step)

The S-4 uses **USB mass storage** for firmware update. No SysEx, no dedicated
updater app, no SD-card path. Canonical flow per the Torso support page:

1. **Download the latest update.** Fetch the 2.1.4 zip from the Torso support
   page at `https://torsoelectronics.com/pages/support`. **Do not unzip**.
   Torso and community threads both call out that Safari on recent macOS
   auto-unzips downloads and this silently breaks the update flow; on Linux
   the default Firefox/Chromium behaviour is to preserve the archive, so this
   hazard does not apply here, but operator should confirm the download is a
   `.zip` and not an unzipped directory before proceeding.
2. **Cable the S-4.** USB-C to USB-A (or USB-C to USB-C) from the workstation
   to the S-4. Any stable data-capable cable works; the S-4's class-compliant
   audio interface enumeration is unaffected.
3. **Enter USB MASS STORAGE mode on the S-4.** Tap `[CONFIG]` → `SYSTEM` →
   `USB MASS STORAGE`. The S-4 mounts as a removable volume on the
   workstation. It should appear in `lsblk` within a few seconds. On
   CachyOS the volume auto-mounts under `/run/media/hapax/` (udisks2).
4. **Drag the zip to the root of the S-4 volume.** Do not place it in a
   subfolder. Do not rename it.
5. **Eject the S-4 from the workstation.** On Linux: `udisksctl unmount -b
   /dev/sdX1` followed by `udisksctl power-off -b /dev/sdX`, or right-click
   → Eject in the file manager. Do *not* physically unplug the USB cable
   before the eject completes — the S-4 detects eject before exiting mass
   storage mode cleanly.
6. **Install.** On the S-4: `[CONFIG]` → `SYSTEM` → `INSTALL UPDATE`. The
   device reboots, performs the install, and automatically deletes the
   update file. Do not power-cycle during install. The device stays
   connected to USB throughout.
7. **2.x first-time gotcha (only applies if installed OS is 1.x).** The
   2.x installer refuses to proceed if any user samples, recordings, or
   projects remain on the S-4 storage. On install, the device will prompt
   to wipe and then auto-enter USB MASS STORAGE mode so the operator can
   back up everything off the drive first. Backup procedure is in §1.4.
8. **Verify.** On reboot, watch the splash for the new version string;
   confirm in `[CONFIG]` → `SYSTEM`.

Community-verified — this procedure is the one demonstrated in the "Torso
S4 Firmware Update Guide" video on the Torso-Electronics channel and
corroborated across the Elektronauts S-4 thread.

### §1.4 Safe-upgrade checklist

**Power.** The S-4 is mains-only via its 12 V / 2 A centre-positive DC
adapter. No internal battery. Back the workstation and the S-4 with the same
UPS if possible; at minimum, ensure the studio UPS is healthy and the next
~15 minutes are not scheduled for any utility work.

**Backup of user content** (required for any 1.x → 2.x crossing; strongly
recommended for all updates):

- In USB MASS STORAGE mode, copy the entire S-4 volume to a timestamped
  directory on the workstation: `rsync -a --info=progress2
  /run/media/hapax/S-4/ ~/backups/s-4/$(date +%Y%m%d-%H%M)/`.
- Specifically, ensure the `HAPAX-VOX-BASE` project file (base-config §4.6)
  is in the backup. Without this, the chain must be re-dialled from the §3
  and §4 tables by hand.
- Preserve timestamps — S-4 scene-recall ordering can depend on them.

**Version skipping.** The 2.x release line supersedes 1.x entirely; there is
no evidence of a known-bad intermediate version that must be skipped through.
The published changelog shows hotfixes 2.0.1, 2.0.3, 2.1.1, 2.1.2, 2.1.3
explicitly addressing regressions in the immediately preceding release —
always install the latest (2.1.4) rather than stepping through minors.

**Rollback.** Torso does not publish downgrade images on the public support
page. A 2.x → 1.x rollback would require the old .zip, which the Torso
archive has historically included under prior-version URLs but is not
a guaranteed artefact. Ask the operator to confirm before upgrade whether
downgrade matters; if it does, mirror the current 1.x image from
`downloads.torsoelectronics.com` before starting. **Practical rollback
posture:** if 2.1.4 misbehaves on the vocal chain, the recovery path is to
reach out to Torso support via the support page, not to self-downgrade.

**Known failure modes.**

- **Zip auto-unzipped on download.** The installer sees a folder instead of
  a file and reports an error. Recovery: re-download with a browser that
  preserves the archive.
- **Install halted mid-flash.** The 2.x installer has been reported in
  community threads to occasionally stall at 50–70% on first run. The
  documented recovery is to power-cycle and re-enter `INSTALL UPDATE`; the
  device retains the zip in an unprocessed state and can retry. No
  community report of a hard brick from an interrupted S-4 flash on the
  2.x line.
- **Data-refusal on 1.x → 2.x.** The installer will insist on a wipe. This
  is expected — the §1.3 step-7 flow accommodates it.

**Risk assessment.** Low-moderate. The S-4 is a USB-mass-storage updater
with no OTA or partial-flash mechanism; the device either flashes the
full image or refuses. The highest-risk moment is the 1.x → 2.x crossing,
because user content must be wiped. With the backup in §1.4 taken first,
the move is reversible within the 2.x series at a minimum and almost
certainly recoverable across the full archive. No evidence in public
reporting of an S-4 brick caused by an interrupted USB flash on 2.x.

### §1.5 Post-upgrade smoke tests

Run these in order. Each should pass before moving to the next. All tests
take ~2 minutes and do not require livestream infrastructure.

1. **Boot + version.** Splash reports `S-4 OS 2.1.4`. `[CONFIG]` → `SYSTEM`
   confirms the same string.
2. **USB audio class-compliant enumeration.** `lsusb` shows the S-4;
   `arecord -l` and `aplay -l` list the S-4 card; `pw-cli list-objects |
   grep -i torso` shows the 10-in/10-out device at 48 kHz. This is the
   input/output contract the base-config §2 signal chain depends on.
3. **`HAPAX-VOX-BASE` project recall.** Load the project; Track 1 Material
   and Granular slots should still be Bypass, Filter/Color/Space should
   carry Ring/Deform/Vast. If 1.x → 2.x wipe was performed, restore from
   backup and reload.
4. **Line-in passthrough.** Speak into the TTS path (or use a sine
   generator if the chain is not assembled). Audio should pass from IN 1
   → OUT 1 with the Ring/Deform/Vast active. Meter should behave as
   §6 step 11 of the base-config doc describes.
5. **MIDI CC reception.** Send `CC 79 = 60` (Ring cutoff) on channel 1;
   observe Ring cutoff knob LED move on the S-4. Repeat for CC 95 (Deform
   drive), CC 96 (Deform compress), CC 112 (Vast delay amount). These
   four CCs cover one parameter from each of the three active slots and
   validate the 2.0.4 CC-lag fix at the same time.
6. **Sync still works.** If the S-4 is slaved to a master clock via its
   3.5 mm `sync in`, verify that Vast delay sync still locks to the
   expected `1/8D` (or the operator's chosen subdivision). This is the
   primary behavioural regression risk in any minor-version bump.
7. **Scene save/recall.** Save the loaded project to Scene 1 of 128;
   recall Scene 2 (empty); recall Scene 1 — parameters should snap back.

A pass on all seven = the upgrade is safe for tonight's livestream. A
fail on any — document the failure mode in the handoff note and do not
livestream on the upgraded firmware until resolved.

---

## §2. Endorphin.es Evil Pet firmware

### §2.1 Current-version discovery

The Evil Pet's installed firmware version is readable from its front-panel
menu. Per the Endorphines manual and the v1.42 firmware string set
enumerated during the factory-preset research (§1.1 of the
`evil-pet-factory-presets-midi.md` doc), the Config-menu strings include
`MIDI MODE`, `MIDI CHANNEL`, `MIDI THRU`, `MIDI MAPPING` and a version
line. The Setup menu is entered with `SHIFT + LFO ASSIGN/expr*` held
for ~1 second; the version reports on the main Config/About screen as a
line of the form `FW 1.42`.

The Evil Pet also prints a version string to the OLED during boot splash.
Watch for `EVIL PET v1.xx` on the 2.42" display in the first ~2 seconds
of power-on.

There is no SD-card `VERSION.TXT` written by the firmware; the SD card
holds presets, firmware upload files, and WAV samples but is not used as
a version-metadata store.

### §2.2 Latest version

As of 2026-04-20 the published firmware on Endorphin.es' updates server
is **v1.42, released 2026-03-27**, corroborated by both the Endorphines
product page and the factory-preset research §1. No newer build is
advertised on `https://www.endorphines.info/updates/Evil_update.zip` or on
the product page. The base-config doc cites the same v1.42 build. The
operator's device may be on any version from v1.08 (the first post-launch
public build, 2025-10-09) up through v1.42 — specifically, the 2025-10-31
factory preset pack ships presets authored against v1.29+ and may have
been dropped on first boot. Release highlights from the firmware archive's
`EVIL_UPDATE_README.txt` changelog:

- **v1.42** (2026-03-27) — most recent.
- **v1.35** (2026-01-21) — bypass mode (`true` / `soft` / `trails`) moved
  from per-preset to global scope, so preset navigation does not thrash
  bypass behaviour during performance.
- **v1.29** (2025-12-30) — `VOLUME` moved from per-preset to global scope
  (prevents volume-spike transients during preset recall); `LOAD PRESET`
  folder long-press → delete-folder UX introduced; v1.27 hang on `...`
  ascend fixed.
- **v1.26** (2025-10-28) — input source (`mic` / `line` / `radio`)
  gained a user choice between "per preset" and "last used"; CC #58, #59
  added.
- **v1.15** — radio frequency gained the same per-preset vs last-used choice.
- **v1.08** (2025-10-09) — public baseline.

All three post-v1.26 globality carve-outs are directly relevant to the
Hapax chain, because they mean Hapax can load `.evl` presets during a
livestream without audible transients on volume or bypass routing.
If the operator's Evil Pet is running a pre-v1.29 build, the tier ladder
(`voice_tier.py`) will produce audible level bumps on tier transitions
that are not recoverable from the software side. **Upgrading to v1.42 is a
chain-integrity requirement, not just a nice-to-have.**

### §2.3 SD-card-based upgrade procedure

Endorphin.es's upgrade path is the one the operator already intuited: copy
a firmware image onto a microSD card, insert, follow on-screen prompts.
Canonical flow:

1. **Download the firmware archive.** Fetch
   `https://www.endorphines.info/updates/Evil_update.zip` to the
   workstation. The zip contains `evilpet1p42.fw` (the firmware binary,
   ~757 kB) plus `EVIL_UPDATE_README.txt` (the changelog). SHA verification
   from the factory-preset research confirms the file is ~756 784 bytes.
2. **Extract.** `unzip Evil_update.zip -d /tmp/evil-update/` — on Linux the
   default extraction is stable. The operator needs the single
   `evilpet1p42.fw` file; the README is informational.
3. **Prepare the SD card.** Power-down the Evil Pet and remove the microSD
   card. The Evil Pet's SD slot is front-panel (factory-preset research
   §2.3). Plug the SD into the workstation via a USB SD reader. The card
   is FAT32 or exFAT by default.
4. **Copy the `.fw` file to the SD root.** `cp /tmp/evil-update/evilpet1p42.fw
   /run/media/hapax/EVILPET/` (or whatever the SD card's mount point is).
   File must live at the **root** of the SD filesystem — not inside
   `ENDORPHINES/`, not inside `JON MODULAR/`, not in any subfolder. The
   filename must remain `evilpetXpYY.fw` — do not rename.
5. **Eject cleanly.** `udisksctl unmount -b /dev/sdX1` then `udisksctl
   power-off -b /dev/sdX`. Physically remove the SD card.
6. **Insert into Evil Pet and power on.** The Evil Pet scans the SD root
   for a firmware file at boot. When it finds `evilpetXpYY.fw` with a
   version newer than the installed firmware, the OLED prompts to
   upgrade. Follow the on-screen prompts — typically "UPDATE FIRMWARE?
   YES / NO" via the main encoder. Confirm YES.
7. **Wait for the flash to complete.** The Evil Pet reports progress on
   the OLED. Do not power down. The process typically takes under 30
   seconds for a ~750 kB image.
8. **Post-install.** The device reboots automatically into the new
   firmware. The splash shows the new version.

If the version on the card is older than or equal to the installed
version, the device does not prompt and boots normally. The operator can
force a reinstall by temporarily placing a newer `.fw` (from Endorphin.es
archive) or by clearing the installed version via their support path —
but this is not necessary for a forward upgrade.

### §2.4 Safe-upgrade checklist

**Preset backup.** User-saved presets and WAV samples live on the same
SD card. **Before** copying the `.fw` file onto the card, snapshot the
entire card to the workstation: `rsync -a
/run/media/hapax/EVILPET/ ~/backups/evil-pet-sd/$(date +%Y%m%d-%H%M)/`.
This captures `ENDORPHINES/` (6 factory presets), `JON MODULAR/` (55
factory presets), and any user `.evl` files the operator has saved
through the front-panel `SAVE PRESET` flow. Do this even though the
firmware itself does not wipe the SD — a corrupted SD at any point
during the process makes the preset archive the single point of
recovery.

**Power stability.** The Evil Pet runs on 9–18 V DC at 500 mA from an
external adapter. No internal battery. Ensure the adapter is firmly
seated and not dangling over the edge of the desk; one bumped barrel
plug during the 30-second flash window is the primary brick vector.
Keep the desk still for the flash duration.

**Filename validation.** The firmware filename scheme is rigid:
`evilpetXpYY.fw` where `X` is the major version and `YY` is the minor.
`evilpet1p42.fw` = v1.42. The Evil Pet reads the filename to decide
whether the card holds a candidate firmware; a renamed file is ignored.
Do not strip the `1p42` portion. Case is preserved on the SD's FAT/exFAT
but the device is tolerant.

**Version skipping.** There are no known-bad intermediate firmware
versions that must be avoided. The v1.08 → v1.42 arc is linear and each
release carries hotfixes for the immediately preceding build. The Evil
Pet's updater flashes the full image regardless of the installed base
version, so skipping is safe and preferred — go straight to v1.42.

**Rollback.** Endorphin.es' public archive retains old `.fw` files on
`endorphines.info` — v1.29 (`evilpet1p29.fw`), v1.35
(`evilpet1p35.fw`), etc., are present. To roll back, replace the SD's
`.fw` file with the older binary and power-cycle. **This is a real,
operator-executable rollback path, unlike the S-4.** A community report
of Evil Pet bricking from an interrupted flash has not surfaced in the
reviewed threads (modwiggler, elektronauts, gearspace); the failure mode
is usually "device boots into firmware-recovery menu, re-apply from SD."

**Known failure modes.**

- **SD card not recognised.** The Evil Pet is specific about FAT32 or
  exFAT; NTFS cards are ignored. If the operator's card is NTFS (unlikely
  but possible if reformatted on Windows), reformat to exFAT first and
  restore the preset backup.
- **`.fw` placed in subfolder.** Device does not find it. Recovery: move
  to root.
- **Flash interrupted by power loss.** Device enters recovery mode on
  next boot and prompts to re-install from SD. No brick.

**Risk assessment.** Low. The Evil Pet's SD updater is a well-trodden
path, the rollback chain is concrete, no brick reports surfaced in
research. The one non-trivial hazard is the preset backup — if the
operator has saved custom presets from the front panel, those live only
on the SD and are vulnerable to a card-corruption event coinciding with
the upgrade. The `rsync` snapshot in §2.4 addresses this.

### §2.5 Post-upgrade smoke tests

Run these in order after the Evil Pet has rebooted into v1.42. Each
takes ~2 minutes; all can be done with the existing Hapax vocal chain
cabled and the S-4 idle.

1. **Version + boot.** OLED splash reports `v1.42`. Setup menu
   (`SHIFT + LFO ASSIGN/expr*`, 1-second hold) confirms the same.
2. **Global settings preserved across reboot.** Volume (global), bypass
   mode (global), input source (last-used or per-preset depending on
   menu setting) should be whatever was set before the flash.
3. **Factory preset load.** Load `STARTPOINT.EVL` from `JON MODULAR /
   LIVE_FX / STARTPOINT`. Confirm the preset loads without error and the
   OLED displays `STARTPOINT`. All 28 continuous parameters snap to the
   preset's stored values.
4. **MIDI receive CC still works.** Verify `MIDI RECEIVE CC` global flag
   is `ON` (factory-preset research §4.4 calls this the most important
   practical setting). Then send `CC 40 = 64` on channel 1 (Mix).
   Observe the Mix knob LED move; observe the audible wet/dry split
   change. Repeat for:
   - `CC 39` (saturator amount) — audible saturation colour change
   - `CC 70` (filter frequency) — audible cutoff sweep
   - `CC 91` (reverb amount) — audible reverb tail change
   - `CC 11` (grains volume) — should remain silent if the granular
     engine is off at the preset level; move to 64 and verify audible
     granular texture appears, then return to 0.
5. **All 39 CCs mapped the same.** The v1.42 CC map is the one enumerated
   in `evil-pet-cc-exhaustive-map.md`. A spot-check of four CCs (step 4)
   is sufficient for livestream smoke testing; full-surface validation is
   an ops-script concern, not tonight-critical.
6. **Factory preset load across all four folders.** Load one preset from
   each of `ENDORPHINES/`, `JON MODULAR/SYNTHS/`, `JON MODULAR/SEQUENCES/`,
   `JON MODULAR/LIVE_FX/`. A fresh firmware sometimes rejects older preset
   schema — this is unlikely in the v1.42 line (the `.evl` format has been
   stable since v1.29) but confirm.
7. **Voice chain + Evil Pet.** Play a Hapax TTS line through the chain.
   Apply T2 BROADCAST-GHOST via `vocal_chain.apply_tier()` / the router.
   Confirm CCs arrive at the device and the voice exhibits the expected
   character (bandpass + light saturation + room reverb + short tail).

A pass on all seven = safe for livestream. A fail on step 4 (MIDI CC
receive) specifically is a blocker — the chain depends on every CC
landing.

---

## §3. Opportunity in the SD-card upgrade path — Hapax-curated `.evl` presets

### §3.1 Context — the `midi_receive_cc: false` gotcha

The factory-preset research §4.4 surfaced a load-bearing finding: **all 61
factory `.evl` presets have `"midi_receive_cc": false`**, which means after
any factory preset loads, the Evil Pet silently drops incoming CC messages
until the operator toggles `MIDI RECEIVE CC: ON` via the MIDI menu. This
breaks the Hapax vocal chain — `vocal_chain.py` streams CCs assuming the
device is listening, and the chain will appear frozen (no expression,
voice stuck on the preset's baseline) until the operator intervenes.

The Evil Pet's SD card is the same removable, writable FAT/exFAT medium
used for firmware upgrades (§2.3). The `.evl` format is plain JSON
(factory-preset research §1.2). Putting these together: any time the
operator mounts the SD card for firmware purposes, they are one `rsync`
away from being able to author Hapax-curated replacement presets with
`midi_receive_cc: true` already baked in. This is the opportunity — not
part of the firmware upgrade, but adjacent to it and cheap to ship.

This subsection is scoped as a **separate deliverable**. It can be
executed before, after, or wholly independent of the firmware upgrades.
No firmware work depends on it and no preset work depends on the
upgrade. The operator can ship one, the other, both, or neither tonight.

### §3.2 Proposed Hapax preset pack

Seven `.evl` files, one per voice tier (T0–T6 from
`shared/voice_tier.py`). File naming follows the Evil Pet's 10-character
OLED truncation limit:

| Tier | File | OLED name | Character |
|---|---|---|---|
| T0 | `HAPAX-T0-UNADORNED.EVL` | `HAPAX-T0-U` | Kokoro raw; all processing off |
| T1 | `HAPAX-T1-RADIO.EVL` | `HAPAX-T1-R` | Bandpass + compression, no reverb |
| T2 | `HAPAX-T2-BROADCAST.EVL` | `HAPAX-T2-B` | Default livestream voice |
| T3 | `HAPAX-T3-MEMORY.EVL` | `HAPAX-T3-M` | Warm tail, pitch jitter |
| T4 | `HAPAX-T4-UNDERWATER.EVL` | `HAPAX-T4-U` | LP + downward detune |
| T5 | `HAPAX-T5-GRANWASH.EVL` | `HAPAX-T5-G` | Granular engine engaged |
| T6 | `HAPAX-T6-OBLITERATE.EVL` | `HAPAX-T6-O` | Maximum engagement; ritual transitions |

Placement on SD: `/HAPAX/HAPAX-T0-UNADORNED.EVL`, etc. — a single `HAPAX/`
folder at the SD root, separate from `ENDORPHINES/` and `JON MODULAR/`
to avoid confusion and to keep the operator's presets discoverable in the
Evil Pet's file browser.

Every file sets `midi_receive_cc: true` at the top of the JSON. The
`params` block is derived from the tier's 9-dim vector via
`vocal_chain.py`'s existing CC mapping, sampled to the `.evl` parameter
names. Enum fields that the CC surface cannot reach (`reverb_type`,
`vcf_type`, `source`) are set explicitly per tier:

- **T0**: `source: line`, `reverb_type: room` (arbitrary — reverb is off),
  `vcf_type: lp` (arbitrary — filter opens full)
- **T1**: `source: line`, `reverb_type: plate_s`, `vcf_type: bp`
- **T2**: `source: line`, `reverb_type: room`, `vcf_type: bp` (base config)
- **T3**: `source: line`, `reverb_type: plate_l`, `vcf_type: bp`
- **T4**: `source: line`, `reverb_type: room`, `vcf_type: lp` (identity move)
- **T5**: `source: line`, `reverb_type: plate_l`, `vcf_type: bp`
- **T6**: `source: line`, `reverb_type: plate_l`, `vcf_type: comb`

Additional per-file settings:

- `autostart: off` (never auto-start playback — these are live-FX presets)
- `midi_send_cc: false` (do not flood our input with our own CCs)
- `midi_thru: true` (forward incoming MIDI to any chained device)
- `bypass: false` (engine engaged)
- LFO depth matrices set to zero across all three LFOs per HARDM
  governance (factory-preset research §1.2 enumerates the lfo depth
  maps; voice chain forbids LFO-to-pitch and LFO-to-filter that would
  add humanising wobble)

### §3.3 Implementation approach

Ship a single Python script that reads the authoritative tier catalog
from `shared/voice_tier.py` and emits seven `.evl` files. Proposed
location: `scripts/generate-hapax-evl-presets.py`. Sketch:

```python
#!/usr/bin/env python3
"""Generate Hapax-curated .evl files for the Evil Pet, one per voice tier.

Reads shared/voice_tier.TIER_CATALOG and emits .evl JSON conforming to the
v1.42 format (see docs/research/2026-04-20-evil-pet-factory-presets-midi.md).
The critical reason to ship these: all 61 factory presets carry
midi_receive_cc: false, which silences the Hapax CC stream after any
preset load. These files flip the flag to true.

Usage:
    scripts/generate-hapax-evl-presets.py --out /path/to/sd/HAPAX/
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from shared.voice_tier import TIER_CATALOG, VoiceTier

# Per-tier enum fields that the CC surface cannot reach (reverb_type,
# vcf_type). Derived from the §3.2 table above.
PER_TIER_ENUMS: dict[VoiceTier, dict[str, str]] = {
    VoiceTier.UNADORNED:       {"reverb_type": "room",    "vcf_type": "lp"},
    VoiceTier.RADIO:           {"reverb_type": "plate_s", "vcf_type": "bp"},
    VoiceTier.BROADCAST_GHOST: {"reverb_type": "room",    "vcf_type": "bp"},
    VoiceTier.MEMORY:          {"reverb_type": "plate_l", "vcf_type": "bp"},
    VoiceTier.UNDERWATER:      {"reverb_type": "room",    "vcf_type": "lp"},
    VoiceTier.GRANULAR_WASH:   {"reverb_type": "plate_l", "vcf_type": "bp"},
    VoiceTier.OBLITERATED:     {"reverb_type": "plate_l", "vcf_type": "comb"},
}

TIER_FILENAMES: dict[VoiceTier, str] = {
    VoiceTier.UNADORNED:       "HAPAX-T0-UNADORNED.EVL",
    VoiceTier.RADIO:           "HAPAX-T1-RADIO.EVL",
    VoiceTier.BROADCAST_GHOST: "HAPAX-T2-BROADCAST.EVL",
    VoiceTier.MEMORY:          "HAPAX-T3-MEMORY.EVL",
    VoiceTier.UNDERWATER:      "HAPAX-T4-UNDERWATER.EVL",
    VoiceTier.GRANULAR_WASH:   "HAPAX-T5-GRANWASH.EVL",
    VoiceTier.OBLITERATED:     "HAPAX-T6-OBLITERATE.EVL",
}


def dim_to_params(dim_vector: dict[str, float]) -> dict[str, float]:
    """Map 9-dim vocal_chain vector to the Evil Pet .evl params block.

    Uses the same piecewise-linear breakpoints vocal_chain.py does for CCs,
    but emits normalized 0..1 floats into the .evl params dict. Keys match
    the factory .evl schema (factory-preset research §1.2).
    """
    # Abbreviated; full mapping lives in vocal_chain and is shared.
    return {
        "mix":              0.4 + 0.5 * dim_vector["coherence"],
        "saturation":       0.8 * dim_vector["intensity"],
        "filter":           0.4 + 0.5 * dim_vector["tension"],
        "filter_resonance": 0.2 + 0.4 * dim_vector["tension"],
        "reverb":           0.2 + 0.6 * dim_vector["diffusion"],
        "reverb_tone":      0.4 + 0.4 * dim_vector["spectral_color"],
        "reverb_decay":     0.2 + 0.5 * dim_vector["depth"],
        "pitch":            dim_vector["pitch_displacement"],
        "grains":           dim_vector["temporal_distortion"] if dim_vector["temporal_distortion"] > 0.5 else 0.0,
        "shimmer":          0.0,  # permanently clamped per HARDM governance
        # ... remaining .evl params filled from the 9-dim vector or 0
    }


def build_evl(tier: VoiceTier) -> dict:
    profile = TIER_CATALOG[tier]
    enums = PER_TIER_ENUMS[tier]
    return {
        "source": "line",
        "autostart": "off",
        "bypass": False,
        "midi_mode": "midi",
        "midi_thru": True,
        "midi_send_cc": False,
        "midi_receive_cc": True,  # ← THE critical flag
        "reverb_type": enums["reverb_type"],
        "vcf_type": enums["vcf_type"],
        "saturator_type": "distortion",
        "antialiasing": True,
        "follower": {"gain": 0.5, "attack": 0.1, "release": 0.3},
        "params": dim_to_params(profile.dimension_vector),
        "lfos": {
            "lfo1": {"clock": "internal", "divider": 1, "params": {}},
            "lfo2": {"clock": "internal", "divider": 1, "params": {}},
            "lfo3": {"clock": "internal", "divider": 1, "params": {}},
        },
        "pedal": {"points": []},
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True, type=Path)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    for tier in VoiceTier:
        path = args.out / TIER_FILENAMES[tier]
        path.write_text(json.dumps(build_evl(tier), indent=2) + "\n")
        print(f"wrote {path}")


if __name__ == "__main__":
    main()
```

The actual `dim_to_params()` implementation should import from
`agents.hapax_daimonion.vocal_chain` rather than re-implement the
mapping — this is the authoritative map and duplicating it here would
drift.

Workflow for shipping the pack:

1. Run `scripts/generate-hapax-evl-presets.py --out /tmp/hapax-evl/` on
   the workstation.
2. Validate the seven `.evl` files by loading them in a text editor;
   confirm every file has `"midi_receive_cc": true`.
3. When the Evil Pet SD card is mounted (adjacent to or apart from any
   firmware upgrade), `rsync -a /tmp/hapax-evl/ /run/media/hapax/EVILPET/HAPAX/`.
4. Eject the SD card, reinsert into the device.
5. From the Evil Pet front panel: `LOAD PRESET` → scroll to `HAPAX/` →
   load `HAPAX-T2-B` (the operator's default livestream tier).
6. Verify CC reception with a test CC send from the workstation.

Open questions to resolve before shipping (some are also in the
factory-preset research §7):

- Does the Evil Pet auto-rescan SD card contents when a new `.evl`
  appears without a reboot? If no, the operator must power-cycle after
  copying the files.
- Is the per-preset `midi_receive_cc: true` flag definitive, or does a
  globally-off `MIDI RECEIVE CC: OFF` at the MIDI menu still win? The
  answer determines whether `midi_receive_cc: true` in the `.evl` alone
  is sufficient, or whether the operator must also flip the global
  menu to ON. Belt-and-braces: set both.

---

## §4. Risk summary + recommended execution order

### §4.1 What can go wrong?

**S-4 upgrade failure modes, ranked by likelihood:**

1. **Update file auto-unzipped at download** — visible immediately; fixed
   by re-download.
2. **Mid-flash USB disconnect or host sleep** — installer stalls; recovery
   is power-cycle + retry `INSTALL UPDATE`.
3. **1.x → 2.x content wipe refused / botched** — operator must back up
   content first; §1.4 procedure addresses this.
4. **New firmware misbehaves on the vocal chain** — unknown until 2.1.4 is
   live on the device. Mitigation: run the §1.5 smoke tests before any
   livestream; if they fail, do not livestream on the new firmware.
5. **Hard brick** — no public report on the 2.x line. Would require Torso
   support escalation.

**Evil Pet upgrade failure modes, ranked by likelihood:**

1. **SD card not FAT/exFAT** — device ignores the `.fw`. Mitigation:
   verify filesystem before copying.
2. **`.fw` placed in subfolder or renamed** — device does not find it.
   Mitigation: place at root, preserve filename.
3. **Power loss during flash** — device enters recovery on next boot and
   prompts to re-install. No brick.
4. **SD card corruption during backup or copy** — preset archive on the
   card is at risk. Mitigation: `rsync` snapshot to workstation before
   any writes to the card.
5. **Hard brick** — no public report. Would require Endorphines support
   escalation.

**Combined failure mode specific to the Hapax chain:**

- The Evil Pet upgrade is livestream-relevant (global volume + bypass
  carve-outs prevent transients during tier transitions); the S-4
  upgrade is chain-relevant (2.0.4 CC lag fix affects the Ring / Deform
  / Vast CC stream, and 2.0's SCENE count aligns with the research
  assumption). Both upgrades together put the chain on the footing the
  research docs assume. Neither upgrade alone is sufficient to deliver
  that footing.

### §4.2 What's the easiest rollback?

**S-4:** effectively none from the device side. A 2.x → 1.x downgrade
requires the old `.zip` from Torso's archive and is not a tested path.
Operator posture: if 2.1.4 misbehaves, contact Torso support; do not
self-downgrade.

**Evil Pet:** straightforward. Replace the SD's `.fw` file with an older
version from `endorphines.info` (v1.35, v1.29, etc. remain downloadable),
power-cycle the device, confirm re-flash. The preset backup taken in §2.4
restores anything the card might have lost.

Asymmetry: the Evil Pet is the safer of the two to flash first because
its rollback path is intact.

### §4.3 Which device first?

**Recommended order: Evil Pet first, then S-4.** Justification:

1. **Evil Pet rollback is concrete; S-4 rollback is not.** Starting with
   the Evil Pet locks in the safer experiment first. If the Evil Pet
   flash misbehaves, the operator rolls back in ~5 minutes and still has
   a working device for the livestream.
2. **The Evil Pet upgrade is the chain-integrity requirement.** Pre-v1.29
   firmware introduces transients on preset recall that the tier ladder
   cannot recover from in software. Closing this gap first is the
   higher-value move.
3. **The S-4 upgrade is larger and more disruptive.** If the installed
   version is 1.x, the 1.x → 2.x crossing wipes user content and requires
   a documentation-only restore path; the `HAPAX-VOX-BASE` project must
   survive the round-trip. This is where the operator's attention needs
   to be focused, uninterrupted, after the smaller Evil Pet upgrade is
   already verified stable.
4. **Tonight's livestream does not strictly require either upgrade.**
   The existing base-config § works with 1.0.4 and pre-v1.42 firmware.
   The upgrades improve the chain but are not gating. Operator should
   budget ~30 minutes for the Evil Pet upgrade + smoke tests, then
   decide whether to take the S-4 upgrade tonight or defer — the S-4
   1.x → 2.x work is a 45–60-minute investment that includes the
   content backup and restore, and is better done outside of a
   pre-livestream window.

**Recommended sequence:**

1. Snapshot the Evil Pet SD card (`rsync` to workstation).
2. Drop `evilpet1p42.fw` onto the SD card root.
3. Flash the Evil Pet; run §2.5 smoke tests.
4. **Decision gate:** if tonight's livestream is imminent (under 1 hour
   away), stop here and defer the S-4 upgrade to a post-stream window.
   Note the chain is now in mixed state — run the Evil Pet portion of
   the chain against the new firmware, leave the S-4 unchanged.
5. When the window is right: back up the S-4 (export `HAPAX-VOX-BASE`
   via USB mass storage).
6. Flash the S-4 to 2.1.4; navigate the 1.x → 2.x content-wipe prompt
   if applicable; restore the backup; run §1.5 smoke tests.
7. **Separate deliverable:** author and deploy the seven Hapax `.evl`
   files via `scripts/generate-hapax-evl-presets.py`; validate a tier
   recall + CC stream with the chain live.

If the operator wants both upgrades in a single block and has the time,
the total wall-clock budget is approximately:

- Evil Pet: 10 min (download + SD copy + flash) + 10 min smoke tests = 20 min
- S-4: 15 min (download + USB-mass-storage copy + flash, no wipe) or
  45 min (with 1.x → 2.x content wipe + restore) + 15 min smoke tests = 30–60 min
- Hapax `.evl` preset pack: 10 min (script + copy + recall test) = 10 min

**Total: 60–90 minutes** for all three deliverables, with the Evil Pet
branch completing first and providing a rollback shelter if the S-4
branch stumbles.

---

## §5. Sources

### Manufacturer (S-4)

- [Torso Electronics — Support page](https://torsoelectronics.com/pages/support)
- [Torso Electronics — S-4 Changelog](https://torsoelectronics.com/pages/s-4-changelog)
- [Torso Electronics — S-4 Manual OS 1.0.4 PDF](https://downloads.torsoelectronics.com/s-4/manual/The%20S-4%20Manual%201v0v4a.pdf)
- [Torso Electronics — S-4 Manual OS 1.2.0 PDF](https://downloads.torsoelectronics.com/s-4/manual/The%20S-4%20Manual%201v2v0a.pdf)
- [Torso Electronics — What's New in 2.0](https://docs.torsoelectronics.com/what-is-the-s4/whats-new-in-2.0)
- [Torso S4 Firmware Update Guide (official YouTube tutorial)](https://www.youtube.com/watch?v=l73ono246DA)

### Manufacturer (Evil Pet)

- [Endorphin.es — Evil Pet product page](https://www.endorphin.es/modules/p/evil-pet)
- [Endorphin.es — Evil Pet firmware archive](https://www.endorphines.info/updates/Evil_update.zip)
- [Endorphin.es — Shuttle Control / firmware portal](http://firmware.endorphin.es/)
- [Endorphines Evil Pet User Manual (manuals.plus mirror)](https://manuals.plus/m/068472d380f335f9e901241a8c81ed421e1fc3973820446abe12e8e5eaeb4335)
- [Endorphines Evil Pet User Manual (ManualsLib mirror)](https://www.manualslib.com/manual/4136664/Endorphines-Evil-Pet.html)
- [midi.guide — Endorphin.es Evil Pet CCs and NRPNs](https://midi.guide/d/endorphines/evil-pet/)

### Community practitioner / press (S-4)

- [Elektronauts — Torso Electronics S-4 thread](https://www.elektronauts.com/t/torso-electronics-s-4-sculpting-sampler/202434)
- [CDM — Torso S-4's 2.0 OS makes it the performance sampler it wanted to be](https://cdm.link/torso-s-4-os-2-0/)
- [Moog Audio — Free OS 2.0 Firmware Update for the Torso Electronics S-4](https://moogaudio.com/blogs/news/free-os-2-0-firmware-update-for-the-torso-electronics-s-4-sculpting-sampler)
- [MORDIO — The Torso S4 2.0 Update: Finally, This Little Box Is Complete](https://mordiomusic.com/blog/the-torso-s4-20-update-finally-this-little-box-is-complete)
- [SYNTH ANATOMY — Torso Electronics S-4 sculpting sampler OS 2.0: complete engine rewrite](https://synthanatomy.com/2025/06/torso-electronics-s-4-a-modern-tape-machine-with-advanced-sound-sculpting-features.html)
- [Gearspace — Torso Electronics announces OS 2.0](https://gearspace.com/board/new-product-alert-2-older-threads/1449184-torso-electronics-announces-os-2-0-s-4-sculpting-sampler.html)
- [Modwiggler — Torso S-4 sampler thread](https://www.modwiggler.com/forum/viewtopic.php?t=278858)
- [Sound on Sound — Torso Electronics S-4 review](https://www.soundonsound.com/reviews/torso-electronics-s-4)

### Community practitioner / press (Evil Pet)

- [Modwiggler — Endorphines Evil Pet primary thread](https://www.modwiggler.com/forum/viewtopic.php?t=296887)
- [Modwiggler — Endorphin.es firmware trouble (general reference for rollback patterns)](https://modwiggler.com/forum/viewtopic.php?t=239293)
- [Modwiggler — Problem Firmware Update Endorphin.es Ghost (sibling device failure mode reference)](https://www.modwiggler.com/forum/viewtopic.php?t=288115)
- [Elektronauts — Endorphin.es Evil Pet thread](https://www.elektronauts.com/t/endorphin-es-evil-pet/241103)
- [Gearspace — Endorphin.es Evil Pet thread](https://gearspace.com/board/electronic-music-instruments-and-electronic-music-production/1457103-endorphin-es-evil-pet.html)
- [SYNTH ANATOMY — Endorphin.es EVIL PET overview](https://synthanatomy.com/2025/10/endorphin-es-evil-pet-an-mpe-polyphonic-granular-synthesizer.html)
- [Gearnews — Endorphin.es Evil Pet Goes Against the Grain](https://www.gearnews.com/endorphin-es-evil-pet-synth/)

### Internal research

- `docs/research/2026-04-19-evil-pet-s4-base-config.md` — signal chain + base CCs
- `docs/research/2026-04-20-evil-pet-cc-exhaustive-map.md` — full CC surface
- `docs/research/2026-04-20-evil-pet-factory-presets-midi.md` — `.evl` format, 61 factory presets, `midi_receive_cc: false` finding (§4.4), firmware binary strings + changelog (§1.1, §2)
- `docs/research/2026-04-20-voice-transformation-tier-spectrum.md` — T0–T6 tier ladder
- `shared/voice_tier.py` — `VoiceTier` enum + `TIER_CATALOG` with seven `TierProfile` instances
- `agents/hapax_daimonion/vocal_chain.py` — 9-dim → CC mapping (authoritative)
