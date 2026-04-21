# ZOOM LiveTrak USB Silent-Payload Recovery

**When it hits:** ZOOM LiveTrak mixer (L-6: `1686:089e/089f`, L-12: `1686:03d5/03a5`)
enumerates on the USB bus and the ALSA card appears with the right profile,
but every captured sample is binary zero. `/proc/asound/cardN/pcm0c/sub0/status`
shows `state=RUNNING` with `hw_ptr` advancing at ~50 frames/sec instead of the
expected 48 000 frames/sec. Factory reset, device power cycle, host warm reboot,
and even full AC power cycle (PSU off 30 s) do **not** recover it.

## Two compounding root causes

1. **WirePlumber persistent state pins the card to an incorrect profile.**
   `~/.local/state/wireplumber/default-profile` can save an entry like:
   ```
   alsa_card.usb-ZOOM_Corporation_L6-00=output:analog-stereo+input:analog-stereo
   ```
   forcing the card to 2-channel Stereo Mix every time it enumerates. If the
   filter-chain conf expects `multichannel-input` (12 ch / 14 ch), the target
   node simply does not exist under that profile and no binding happens.
   This gets saved accidentally during repeated `pactl set-card-profile` toggles.

2. **`snd-usb-audio` needs `QUIRK_FLAG_GENERIC_IMPLICIT_FB` (0x40)** for the
   LiveTrak family to actually stream audio at full rate. Without it, URBs
   are allocated and the stream looks alive, but the payload stays zero. The
   flag can only be applied as a module load parameter, so the quirk cannot
   be set live on an already-loaded module.

`/etc/modprobe.d/hapax-usb-reliability.conf` ships the quirk for our three
known LiveTrak USB product IDs:

```
options snd-usb-audio implicit_fb=1
options snd-usb-audio quirk_flags=0x1686:0x03d5:0x40,0x1686:0x089e:0x40,0x1686:0x089f:0x40
```

## Recovery procedure (no reboot)

Run in order. Each step is reversible.

```bash
# 1. Mask sockets so PipeWire cannot auto-respawn.
systemctl --user mask pipewire.socket pipewire-pulse.socket

# 2. Kill PipeWire/WirePlumber (systemctl stop is blocked by socket activation).
pkill -9 -u "$USER" pipewire
pkill -9 -u "$USER" wireplumber
pkill -9 -u "$USER" pipewire-pulse

# 3. Move WirePlumber persistent state aside.
mv ~/.local/state/wireplumber ~/.local/state/wireplumber.bak-$(date +%s)

# 4. Reload snd-usb-audio (now unblocked because no user holds it).
sudo modprobe -r snd_usb_audio snd_usbmidi_lib
sudo modprobe snd_usb_audio

# 5. Verify the quirks loaded:
cat /sys/module/snd_usb_audio/parameters/quirk_flags
# Should show the 0x1686:* entries, NOT (null).
cat /sys/module/snd_usb_audio/parameters/implicit_fb
# Should start with `Y,` (first device flag).

# 6. Unmask sockets + restart PipeWire.
systemctl --user unmask pipewire.socket pipewire-pulse.socket
systemctl --user start pipewire pipewire-pulse wireplumber

# 7. Verify. The active card profile should be multichannel-input:
pactl list cards | grep -A1 "Name: alsa_card.usb-ZOOM" | grep "Active Profile"
# Expect: output:analog-surround-40+input:multichannel-input

# 8. Capture-test:
timeout 3 pw-cat --target alsa_input.usb-ZOOM_*.multichannel-input \
  --record --channels 14 --format f32 --rate 48000 --raw /tmp/zoom-test.raw
# hw_ptr should advance ~96000 frames/sec; captured samples should be non-zero.
```

## Do not do this while a ZOOM is enumerated

These are the triggers that cause the silent-payload wedge:

- Repeated `pactl set-card-profile` toggles (off → profile → off → profile).
- Repeated `systemctl --user restart pipewire pipewire-pulse wireplumber`.
- Back-to-back boot-combo flips on the device (e.g. `USB 1/2 + SOUND PAD 2`
  followed by `USB 1/2 + SOUND PAD 1`).

When editing filter-chain configs under `~/.config/pipewire/pipewire.conf.d/`,
save the file, then do **one** clean PipeWire restart. Not a cycle.

## Why factory reset does not fix it

The wedge is not in the device. Both the L-6's and L-12's factory-reset
combos reset the mixer state only; the WirePlumber state file is host-side
and survives the device reset. The `snd-usb-audio` quirk is host-side and
has to be in the module parameters at load time.
