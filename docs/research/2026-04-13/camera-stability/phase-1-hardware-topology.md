# Phase 1 — Hardware and USB Topology Baseline

**Session:** beta, camera-stability research pass (queue 022)
**Date:** 2026-04-13, 16:05–16:10 CDT
**Host:** hapax-podium, uptime 4 h 01 min (boot 2026-04-13 12:05 CDT)
**Register:** neutral, scientific. Every number below has a reproduction command. Inferences are flagged `[inferred]`.
**Scope:** ground-truth the hardware layer before any software measurement in Phases 2–6.

## Summary

- Six physical cameras present and enumerated: 3× Logitech BRIO (`046d:085e`) and 3× Logitech C920 (2× modern `046d:08e5`, 1× older `046d:082d`).
- BRIO serial `43B0576A` on `bus 5 port 4` is still negotiating USB 2.0 only (`speed=480M`), carrying over the finding from `docs/research/2026-04-12-brio-usb-robustness.md`. The other two BRIOs negotiate `5000M` (USB 3.0).
- Shipped udev rule `70-studio-cameras.rules` sets `power/control="on"` on all three Logitech PIDs, but live state shows `power/control=auto` on all three BRIOs. This is cosmetically wrong but functionally inert because `autosuspend_delay_ms=-1` on every camera; runtime_active_time matches full uptime. Filed as a follow-up ticket below.
- Two camera-related rule gaps found: (1) only BRIO serial `5342C819` has a `/dev/webcam-brio` stable symlink in `90-webcams.rules`; serials `43B0576A` and `9726C031` have none. (2) the older C920 (`046d:082d`) is covered by the fallback `99-webcam-power.rules` autosuspend rule, but not by the `70-studio-cameras.rules` Phase 3 `studio-camera-reconfigure@%k.service` trigger, so it misses the on-add re-configure hook from the resilience epic.
- 24 h kernel log is remarkably clean: **1** USB reset event (BRIO `bus 8-3` at 12:14:04 CDT during the 13:14 compositor restart window), **0** EPROTO, **0** `error -71`, **0** camera disconnects. Compare to the error storms seen during the pre-epic 2026-04-12 investigation.
- Thermals at measurement time: CPU `Tctl=78.6°C`, GPU `56°C`, NVMe `40.9°C`. No camera-exposed temperatures (BRIOs do not publish v4l2 temperature controls).

## Device inventory

| video node | model | product ID | serial | bus-port | speed | stable symlink | notes |
|---|---|---|---|---|---|---|---|
| video0/video2 | BRIO | 046d:085e | 5342C819 | 6-2 | 5000M (USB3) | `/dev/webcam-brio` | has stable symlink via `90-webcams.rules` |
| video4/video6 | BRIO | 046d:085e | 43B0576A | 5-4 | **480M (USB 2.0)** | — | **degraded link speed**, no stable symlink |
| video14/video19 | BRIO | 046d:085e | 9726C031 | 8-3 | 5000M (USB3) | — | no stable symlink |
| video8 | C920 (modern) | 046d:08e5 | 86B6B75F | 1-1 | 480M | `/dev/webcam-c920-3` | |
| video12 | C920 (modern) | 046d:08e5 | 7B88C71F | 3-2 | 480M | `/dev/webcam-c920-1` | |
| video17 | C920 (older) | 046d:082d | 2657DFCF | 7-4 | 480M | `/dev/webcam-c920-2` | not covered by 70-studio-cameras reconfigure hook |

Virtual v4l2loopback nodes (not cameras; compositor outputs / OBS plumbing):

| video node | ID_V4L_PRODUCT | purpose `[inferred]` |
|---|---|---|
| video10 | OBS_Virtual_Camera | OBS virtual camera sink |
| video42 | StudioCompositor | compositor output (tee → v4l2sink) |
| video50 | YouTube0 | YouTube restream source 0 |
| video51 | YouTube1 | YouTube restream source 1 |
| video52 | YouTube2 | YouTube restream source 2 |

C920 model note: two distinct Logitech product IDs are in use. `08e5` is the "C920 PRO HD" family; `082d` is the older "HD Pro Webcam C920". Kernel reports the older unit as quirks-forced testing-purpose (`Forcing device quirks to 0x0 by module parameter for testing purpose` at boot on 7-4:1.0).

**Reproduction commands:**
```bash
# USB topology with speed + driver
lsusb -t

# All Logitech devices with vendor/product/speed/autosuspend state
for d in /sys/bus/usb/devices/*/idVendor; do
  v=$(cat "$d"); [ "$v" = "046d" ] || continue
  dir=$(dirname "$d"); pid=$(cat "$dir/idProduct"); speed=$(cat "$dir/speed")
  prod=$(cat "$dir/product" 2>/dev/null); path=$(cat "$dir/devpath")
  busnum=$(cat "$dir/busnum"); pwr=$(cat "$dir/power/control")
  asusp=$(cat "$dir/power/autosuspend_delay_ms")
  active=$(cat "$dir/power/runtime_active_time" 2>/dev/null)
  echo "bus=$busnum devpath=$path speed=${speed}M pid=$pid power=$pwr autosuspend=${asusp}ms active=${active}ms product=\"$prod\""
done

# Per-camera udev properties (repeat for each primary video node)
udevadm info --query=property --name=/dev/video0 | grep -E '^(ID_VENDOR|ID_MODEL|ID_PATH|ID_SERIAL_SHORT|DEVPATH)='
```

## USB bus topology

Excerpt from `lsusb -t` filtered to bus roots that host a camera:

| bus | xHCI controller | role | cameras attached |
|---|---|---|---|
| 1 | `xhci_hcd 0000:01:00.0` (4p, 480M) | USB 2.0 only | C920 86B6B75F at port 1 |
| 3 | `xhci_hcd 0000:03:00.0` (2p, 480M) | USB 2.0 only | C920 7B88C71F at port 2 |
| 5 | `xhci_hcd 0000:0c:00.3` (4p, 480M) | USB 2.0 only | **BRIO 43B0576A at port 4** |
| 6 | `xhci_hcd 0000:0c:00.3` (4p, 10000M) | USB 3.0 root | BRIO 5342C819 at port 2 |
| 7 | `xhci-pci-renesas 0000:05:00.0` (4p, 480M) | USB 2.0 only | C920 2657DFCF at port 4 |
| 8 | `xhci-pci-renesas 0000:05:00.0` (4p, 5000M) | USB 3.0 root | BRIO 9726C031 at port 3 |

Buses 1/3/5/7 are the 2.0 personalities of companion xHCI controllers; buses 2/4/6/8 are the 3.0 siblings. The BRIO on bus 5-4 is the documented 2.0-fallback case: the 3.0 personality of that xHCI pair is `bus 6` (currently holding BRIO 5342C819), so physically the port or cable for bus 5-4 is forcing fallback negotiation. `[inferred from prior research and the fact that the other two BRIOs negotiate 5000M cleanly on the other xHCI siblings]`

No TS4-branded external hub is currently enumerated on any camera path; the only hubs visible in `lsusb -t` are on bus 3 (internal BIOS path) and bus 4 (empty 4-port 3.0 hub chain). Cameras appear to be cabled direct to motherboard I/O panel ports. Cross-reference against `memory_studio_cameras.md`'s room layout and `docs/research/2026-04-12-brio-usb-robustness.md` if physical inspection is needed.

**Reproduction command:**
```bash
lsusb -t
```

## Autosuspend state

| bus-port | product | power.control live | autosuspend_delay_ms | runtime_active_time (ms) | effective |
|---|---|---|---|---|---|
| 1-1 | C920 (08e5) | on | -1 | 14498183 | on continuously |
| 3-2 | C920 (08e5) | on | -1 | 14497698 | on continuously |
| 5-4 | BRIO | auto | -1 | 14498042 | on continuously (delay=-1 overrides auto) |
| 6-2 | BRIO | auto | -1 | 14498391 | on continuously |
| 7-4 | C920 (082d) | on | -1 | 14490463 | on continuously |
| 8-3 | BRIO | auto | -1 | 14492457 | on continuously |

`runtime_active_time` values are 14.49–14.50 million ms = ~4 h 01 min = full uptime, so no camera has suspended even momentarily since boot. `autosuspend_delay_ms=-1` is what the udev rule intended, even though the BRIO `power/control` attribute drifted to `auto`. This is benign in the current kernel, but it is a latent drift worth fixing: a future kernel or systemd-udev policy change that stops honoring the -1 delay on `auto` control would re-enable autosuspend and could bring back latency spikes.

**Rule drift root cause:** `[inferred]` the BRIO autosuspend `ACTION=="add"` rule in `70-studio-cameras.rules` line 17 and `99-webcam-power.rules` line 5 both set `ATTR{power/control}="on"`. It is possible the kernel USB core applies a default `control=auto` after both rules fire and the udev write does not stick. The C920s observe `power/control=on`, so the rule writes are reaching sysfs for 08e5 and 082d; only 085e drifts. This is fixable with a `power/control=on` sysfs write at compositor startup, or with a periodic reassertion via a systemd path unit, but filing as a follow-up ticket rather than patching in this research pass.

**Reproduction command:** see the `for d in ...` loop in § Device inventory.

## 24 h kernel log classification

`journalctl -k --since='24 hours ago'` filtered to `(usb|xhci|v4l2|uvcvideo|uas|EPROTO|-71)` returns 306 lines. Almost all are routine enumeration messages from the single boot window at 12:05 CDT (six cameras + audio interfaces + HID devices + hub trees). Non-routine events, fully classified:

| timestamp (CDT) | event | classification | camera? |
|---|---|---|---|
| 12:05:06 | uvcvideo: `nodrop parameter will be eventually removed` | benign kernel deprecation warning | — |
| 12:05:06–12:05:07 | six `uvcvideo X-X:1.0: Found UVC 1.00 device …` lines | routine enumeration | all 6 |
| 12:05:07 | `uvcvideo 7-4:1.0: Forcing device quirks to 0x0 by module parameter for testing purpose. Please report required quirks to the linux-media mailing list.` | informational: a module option (`uvcvideo.quirks=0`) is in effect | C920 082d only |
| 12:14:04 | `usb 8-3: reset SuperSpeed USB device number 2 using xhci-pci-renesas` followed by `uvcvideo 8-3:1.0: Found UVC 1.00 device Logitech BRIO (046d:085e)` | transient: one SuperSpeed reset that recovered on its own | BRIO 9726C031 |
| 12:42:00 | `usb 3-1.1.3: USB disconnect, device number 8` | not a camera — 3-1.1.3 is the Logi Bolt receiver's child HID, separate device | — |

Non-classified noise (counts from `uniq -c`):
- 18 `current rate 16000 is different from the runtime rate 48000` lines across buses 5-4, 6-2, 8-3. These are ALSA runtime-rate mismatches inside the BRIO integrated mics, not USB transport errors. Benign; audio subsystem resyncs automatically.

No `EPROTO`, no `error -71`, no `device not accepting address`, no HighSpeed reset storms, no `device descriptor read/64` cascades, no UVC decode errors. The resilience epic appears to have left the hardware substrate calmer than the pre-epic 2026-04-12 window, or the reboot reset transient state that had accumulated.

**Reproduction command:**
```bash
journalctl -k --since='24 hours ago' \
  | grep -iE '(usb|xhci|v4l2|uvcvideo|uas|EPROTO|-71)' \
  | grep -vE '(hid|bluetooth|Bolt|Yubi|cards)' \
  | awk '{$1=$2=$3=""; print $0}' | sort | uniq -c | sort -rn
```

## Thermal and system load at measurement time

| sensor | value | notes |
|---|---|---|
| NVIDIA 3090 GPU core | 56 °C | `nvidia-smi` |
| NVIDIA 3090 memory | N/A | not exposed by driver |
| NVIDIA 3090 power draw | 226.98 W | |
| NVIDIA 3090 GPU util | 63 % | compositor + streaming + LLM inference sharing GPU |
| NVIDIA 3090 VRAM | 12828 / 24576 MiB | |
| CPU `Tctl` | 78.6 °C | AMD k10temp |
| CPU `Tccd1` | 75.2 °C | |
| NVMe composite | 40.9 °C | |
| iwlwifi (virtual) | 70.0 °C | non-essential |
| ambient (room) | not measured | no room sensor wired |
| Load average | 53.05 / 57.15 / 50.01 | **unusually high**, to be characterized in Phase 2 |

**Load average observation.** A 1-min/5-min/15-min load of 53/57/50 on a host that was quiet 24 h ago is a concrete signal. This is not a hardware-topology finding per se but will anchor the Phase 2 steady-state baseline. `[inferred: compositor leak + streaming + concurrent imagination loop + session processes]`. It does not appear to have produced any USB-layer fault (kernel log is clean) but can affect UVC ISO packet dropping if CPU scheduling latency starves the uvcvideo kworker. Flag for Phase 2 investigation.

**Reproduction commands:**
```bash
sensors
nvidia-smi --query-gpu=name,temperature.gpu,power.draw,utilization.gpu,memory.used,memory.total --format=csv
uptime
```

## Differences vs 2026-04-12 research

Prior BRIO USB robustness research (`docs/research/2026-04-12-brio-usb-robustness.md`, alpha) identified the bus 5-4 BRIO on USB 2.0 as the primary driver of the error -71 fault class and proposed the full camera 24/7 resilience epic to contain it.

| aspect | 2026-04-12 | 2026-04-13 (this phase) | delta |
|---|---|---|---|
| BRIO 43B0576A bus-port | 5-4 at 480M | 5-4 at 480M | unchanged |
| Other two BRIO speeds | mixed | 5000M clean (6-2, 8-3) | unchanged |
| dmesg error -71 count | non-zero (specific count in prior doc) | **0** in last 24 h | improvement |
| UVC decode errors | non-zero | **0** | improvement |
| Autosuspend disabled via delay=-1 | partially deployed | deployed on all 6 | done |
| `power/control` on BRIOs | not measured | `auto` despite rule saying `on` | drift found |
| Stable symlink per BRIO | none | one (`/dev/webcam-brio` for 5342C819) | partial |
| Bus 5-4 port audit / physical swap | not done | not done | unchanged |

The 2026-04-12 research ends with "physical root cause not re-verified; worth swapping the cable or moving to a different physical port and re-measuring." **That experiment has not been run** in the interval. The degraded link speed is therefore still a standing hardware question, not a closed one.

## Follow-up tickets (file, do not fix in this pass)

Filed as candidate work for subsequent sessions. Severity ordered by operator impact.

1. **`research/camera`: physically migrate BRIO 43B0576A off bus 5-4.** The 2.0-only negotiation has survived the epic and a reboot; the epic's software containment layer is masking a hardware question that should be answered. Physical inspection or a port swap is the next step. Operator action required. *(Severity: medium. Affects: livestream quality if that camera is a key angle.)*

2. **`fix(udev): reassert `power/control=on` on BRIOs reliably.** Current live state shows `auto` on all three BRIOs despite `70-studio-cameras.rules` line 17 setting `on`. Benign today because `autosuspend_delay_ms=-1` dominates, but latent if a future kernel honors `auto`. Options: (a) add a periodic sysfs reassertion via a systemd path unit, (b) write at compositor startup, (c) add a `change`-action udev rule to re-apply on every `change` event. *(Severity: low-latent. Affects: future-proofing against autosuspend regression.)*

3. **`fix(udev): add BRIO 43B0576A and 9726C031 to `90-webcams.rules`.** Only serial `5342C819` has a stable `/dev/webcam-brio` symlink. Add `webcam-brio-2` (43B0576A) and `webcam-brio-3` (9726C031) symlinks so operator and compositor code can reference the cameras by serial-anchored path instead of v4l2 enumeration order. *(Severity: low. Affects: code that assumes a fixed `/dev/video*` numbering; known-fragile pattern.)*

4. **`fix(udev): include C920 082d in 70-studio-cameras.rules Phase 3 reconfigure hook.** The older C920 has a different product ID (`082d` vs `08e5`) and therefore does not trigger `studio-camera-reconfigure@%k.service` on add. The 99-webcam-power rule catches autosuspend, but v4l2 settings reassertion after a replug won't happen automatically for this device. Add the PID to the reconfigure block. *(Severity: low. Affects: recovery-reconfigure path for the one older C920.)*

5. **`docs(research)`: capture a physical inventory diagram.** Room-layout + TS4 hub + cable routing snapshot is referenced in memory but has not been committed to the repo. Would unblock future research passes from having to re-walk the physical topology. *(Severity: low. Affects: research velocity only.)*

## Open questions

1. Why does `power/control=auto` survive on all three BRIOs when the udev rule sets `on`? Worth tracing the ordering of `70-studio-cameras.rules` vs `99-webcam-power.rules` and kernel USB core default policy. Not load-bearing for the Phase 2–6 investigation because `autosuspend_delay_ms=-1` dominates.
2. The older C920 (`082d`) has `uvcvideo.quirks=0` forced by module parameter. Who set that, and does any other camera rely on a different quirks value being applied? `grep -r quirks /etc/modprobe.d/` will answer.
3. What is behind the 53/57/50 load average? Does the compositor memory leak (ALPHA-FINDING-1) correlate with CPU oversubscription, or is it orthogonal? Phase 2 will characterize this.

## Acceptance check

- [x] Every camera accounted for: 6 physical + 5 virtual nodes enumerated with serials and bus-port mapping.
- [x] Every dmesg USB error classified: 1 transient reset + 1 non-camera disconnect + 18 audio rate-mismatch warnings + routine enumeration.
- [x] Autosuspend state captured: `autosuspend_delay_ms=-1` on all six; `power/control` drift noted.
- [x] Thermal snapshot: GPU, CPU, NVMe, no ambient room sensor.
- [x] Differences vs 2026-04-12 research captured.
- [x] Open questions filed explicitly; hardware inspection left as operator-action follow-up.
