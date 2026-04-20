# L6 Multitrack Retargets — Operator Runbook

**Author:** delta
**Date:** 2026-04-20
**Status:** Ready to apply — operator triggers.
**Source:** `~/.cache/hapax/relay/delta.yaml` `audio_config_retargets_queued`
**Related task:** delta #210

---

## §1. Purpose

Delta's pre-crash `delta.yaml` queued 5 config retargets that track the
operator's 24C retirement + L6 patching. This runbook consolidates
them into one applicable sequence + one verify command, so the
operator can apply when ready without re-deriving the topology from
the 6 hardware moves they've made since.

**Pre-condition** (operator already patched):
- L6 ch 2: Cortado MKIII contact mic (+48V)
- L6 ch 3: Evil Pet modulated TTS return
- L6 ch 5-6: Handytrax vinyl stereo
- L6 USB ↔ PC (multitrack Altset 2 via existing
  `hapax-l6-evilpet-capture.conf`)

**Pending operator confirm at apply-time:**
- Rode Wireless Pro receiver on ch 1 (not yet patched)
- AUX 1 routing:
  `PC → L6 USB playback → AUX 1 send → AUX 1 out → Evil Pet L-in
  → L6 ch 3 → Main Mix → OBS` (excluded from Main Mix to prevent
  feedback loop)

---

## §2. The five retargets

### 2.1 voice-fx-chain.conf → L6 USB playback

Current state: `config/pipewire/voice-fx-chain.conf` creates the
`hapax-voice-fx` virtual sink for TTS filtering; the canonical
descriptor (`config/audio-topology.yaml`) targets Ryzen analog for
the `voice-fx` node.

Target state: retarget the downstream playback to the L6 USB playback
sink (`alsa_output.usb-ZOOM_Corporation_L6-00.analog-stereo` or
equivalent — verify live name with `pw-cli ls Node | grep -i zoom`).

Once retargeted:
- TTS routes PC → L6 USB → AUX 1 send → Evil Pet → L6 ch 3.
- The Ryzen Rear line-out can return to general PC audio instead of
  doubling as the TTS path.

Apply:
```
sed -i 's|alsa_output.pci-0000_73_00.6.analog-stereo|<L6-USB-playback-node-name>|' \
    config/pipewire/voice-fx-chain.conf
# Update config/audio-topology.yaml the same way.
systemctl --user restart pipewire pipewire-pulse wireplumber
```

### 2.2 HAPAX_TTS_TARGET env → L6 USB sink

Current: operator env + daimonion systemd unit set
`HAPAX_TTS_TARGET=hapax-voice-fx-capture` (which is the `voice-fx`
filter-chain input sink).

Target: no change to this variable — voice-fx is still the entry
point. The retarget happens inside voice-fx (§2.1), not at the env
surface. **No action.** The operator inherits transparent re-routing
from the conf change.

### 2.3 Contact mic pw-cat target → L6 multitrack ch 2

Current: `agents/hapax_daimonion/backends/ir_presence.py` / contact_mic
backend captures via
`pw-cat --record --target "Contact Microphone"`.

Target: `pw-cat --record --target alsa_input.usb-ZOOM_Corporation_L6-00.multitrack`
with channel-extraction at ch 2 (AUX1). The `hapax-l6-evilpet-capture`
filter-chain already opens the multitrack source — the contact-mic
backend needs to consume a single-channel crop of AUX1 from that
same source.

Apply:
- Edit `agents/hapax_daimonion/backends/contact_mic.py` (wherever the
  pw-cat target string lives) to the multitrack node name + AUX1
  channel crop.
- Verify via `pw-cat --record --target <multitrack-node> --channels 1
  --raw` briefly, check RMS moves when operator taps the mic.

### 2.4 Vinyl capture → L6 multitrack ch 5-6

Current: any vinyl capture configured via external device URI.

Target: same multitrack source, AUX4+AUX5 (ch 5-6 is AUX4+AUX5
zero-indexed inside the multitrack layout). Stereo crop. Vinyl rate
BPM compensation continues to live in the Korg Handytrax logic, not
the pw-cat layer.

### 2.5 Collapse livestream-tap + l6-evilpet-capture → single L6 main-mix tap

Current: two filter-chain nodes (`hapax-livestream-tap` null-sink +
`hapax-l6-evilpet-capture` filter-chain) both mix into the OBS feed.

Target: delete `hapax-livestream-tap` entirely; let
`hapax-l6-evilpet-capture` be the sole broadcast tap. The
livestream-tap was a workaround for monitor-starvation when the
livestream-fx filter-chain was the primary broadcast path; since the
L6 Main Mix is now tapped directly at AUX10+AUX11 with +12 dB
makeup, the tap is redundant.

Apply:
- Delete `config/pipewire/hapax-livestream-tap.conf`.
- Delete `config/audio-topology.yaml` `livestream-tap` node + the
  edge from `main-mix-tap` to `livestream-tap`.
- Update `main-mix-tap.target_object` from `hapax-livestream-tap` to
  `v4l2-source-name-OBS-monitors` (operator confirms live name).
- Keep `hapax-livestream` + `hapax-private` virtual sinks — they
  serve applications with media.role targeting.

---

## §3. Verify command

After applying, run:
```
hapax-audio-topology verify config/audio-topology.yaml
```

Exit 0 ⇒ live graph matches descriptor. Exit 2 ⇒ drift with diff
printed to stdout. Exit 1 ⇒ pw-dump failed (pipewire down).

---

## §4. Rollback

Every change is git-reversible:
```
git revert <retarget-commit-sha>
systemctl --user restart pipewire pipewire-pulse wireplumber
```

The audio-topology descriptor CI test
(`tests/shared/test_canonical_audio_topology.py`) pins the +12 dB
Main Mix makeup gain + voice-fx target + seven node ids; any retarget
that drops those pins will fail in CI before merge.

---

## §5. Why not apply now (without operator)

Two risks if delta applies unilaterally:

1. **Rode Wireless Pro not yet on ch 1.** The system's presence signal
   currently uses the contact mic (ch 2). Retargeting the pw-cat source
   before the Rode is active means contact-mic detection could move to
   the Rode slot and report false operator-present when the Rode is
   switched off. Operator confirms patch before the backend retargets.

2. **OBS monitor-source name is environment-specific.** The livestream
   tap collapse (§2.5) needs the live OBS V4L2 source node name or the
   audio path lands on a different sink. Operator verifies with
   `pw-cli ls Node | grep -i obs` at apply time.

Both guard conditions are in §2 apply notes. Delta will re-attempt
apply-without-operator once the operator signals the Rode is patched.

---

## §6. References

- `~/.cache/hapax/relay/delta.yaml` §audio_config_retargets_queued
- `config/audio-topology.yaml` — canonical descriptor (post-retarget edits below)
- `config/pipewire/*.conf` — individual conf files
- `docs/superpowers/plans/2026-04-20-unified-audio-architecture-plan.md` §6
- `tests/shared/test_canonical_audio_topology.py` — regression pins
- `scripts/hapax-audio-topology` — verify / generate / diff CLI
