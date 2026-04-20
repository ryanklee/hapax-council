# WirePlumber notification-loopback retarget research

**Environment:** WirePlumber 0.5.14-1.1 (Arch/CachyOS), PipeWire ≥ 1.4, Studio 24c default sink, config dir `~USER/.config/wireplumber/wireplumber.conf.d/`.

**TL;DR:** The previous attempt did not fail because of module syntax. It failed (and will keep failing) because `~USER/.local/state/wireplumber/stream-properties` contains a persisted match on `media.role=Loopback` that pins **all three** role-based loopback outputs to `hapax-livestream`. That persisted metadata overrides the module args, overrides `policy.role-based.preferred-target`, and overrides the default-sink lookup. The correct fix is a two-part change: (1) wipe the persisted metadata row that matches on `media.role=Loopback`, and (2) add `policy.role-based.preferred-target = "hapax-private"` to the notification loopback's `capture.props` in `50-hapax-voice-duck.conf`. Optionally suppress WP's `linking.allow-moving-streams` or the stream-properties persistence for loopback outputs so the issue cannot recur.

---

## §1. Current state

### §1.1 Loopback output node links (`pw-link -l`)

```
hapax-livestream:playback_FL
  |<- hapax-livestream-tap-dst:output_FL
  |<- output.loopback.sink.role.multimedia:output_FL
  |<- output.loopback.sink.role.notification:output_FL
  |<- output.loopback.sink.role.assistant:output_FL         (FL shown; FR identical)
```

All three role-based loopback *output* nodes are linked into `hapax-livestream` (the filter-chain virtual sink at id 86). None link into the 24c ALSA device directly; none link into `hapax-private`.

### §1.2 Node properties (`wpctl inspect 156` — notification output)

```
media.class  = Stream/Output/Audio
media.role   = Loopback                  (inherited from components.rules)
node.autoconnect = true
node.passive = true
node.link-group = loopback-4019199-19
node.virtual = true
target.object = (unset)
node.target   = (unset)
```

All three role loopback outputs (153, 156, 158) have `media.role = Loopback`, `node.autoconnect = true`, and no `target.object` / `node.target` on the node itself.

### §1.3 Where the livestream routing actually comes from

Not from `wireplumber.components.rules`. Not from `default.audio.sink` (which is correctly `alsa_output.usb-PreSonus_Studio_24c_...`, verified via `pw-metadata -n default 0 'default.audio.sink'`). Not from priority.session (hapax-livestream has none; the 24c is 2000 — find-best-target would prefer the 24c).

The override comes from **WirePlumber's `restore-stream` state file**:

```
~USER/.local/state/wireplumber/stream-properties
---
Output/Audio:media.role:Loopback={"volume":1.0,...,"target":"hapax-livestream"}
```

That single row matches on `media.role = Loopback`, which applies to all three role-based loopback *outputs* (multimedia, notification, assistant — all carry `media.role = Loopback` from the merge rule). WP's `linking/restore-stream` module writes `target.object` into the default metadata at per-node IDs when a match hits. Live proof from `pw-metadata`:

```
update: id:153 key:'target.object' value:'86' type:'Spa:Id'   # multimedia   -> hapax-livestream
update: id:156 key:'target.object' value:'86' type:'Spa:Id'   # notification -> hapax-livestream
update: id:158 key:'target.object' value:'86' type:'Spa:Id'   # assistant    -> hapax-livestream
```

Node id 86 is `hapax-livestream`. These per-node metadata entries are consumed by `linking/find-defined-target.lua` (line 45: `if si_props["target.object"] ~= nil then ...`) which runs BEFORE `find-media-role-sink-target`, `find-default-target`, and `find-best-target`. That is why the loopback outputs land in `hapax-livestream` regardless of any config we add.

How this got written: at some earlier point the operator (or pavucontrol, or `pactl move-sink-input`, or the `playback.props.target.object = "hapax-private"` attempt being misinterpreted by the `restore-stream` module as a user-initiated move) triggered a stream-move. With `linking.allow-moving-streams = true` (WP default — see `/usr/share/wireplumber/wireplumber.conf:912-917`) and `restore-stream`-style persistence, WP captured the move keyed on `media.role = Loopback` and has been replaying it on every restart since.

**This also explains why the previous attempt "broke all three loopbacks."** Setting `playback.props.target.object = "hapax-private"` inside the notification loopback module's args produced an initial link to `hapax-private`, which `restore-stream` then persisted under the overly-broad `media.role=Loopback` key, propagating to multimedia and assistant. The *module args were correct enough to work*; the persistence layer then corrupted the other two.

---

## §2. Canonical retarget pattern

WirePlumber 0.5.x (>= 0.5.5) ships a dedicated hook, `linking/find-media-role-sink-target.lua`, whose sole purpose is retargeting the output side of role-based loopbacks. It reads `policy.role-based.preferred-target` from the sink (input) node of the link-group. See `/usr/share/wireplumber/scripts/linking/find-media-role-sink-target.lua:55`:

```lua
local target_name = input_node.properties["policy.role-based.preferred-target"]
```

The upstream example already uses this for the `Alert` role (`/usr/share/doc/wireplumber/examples/wireplumber.conf.d/media-role-nodes.conf:153`):

```
policy.role-based.preferred-target = "Speaker"
```

This is the blessed way. It runs AFTER `find-defined-target` (which is why the persisted metadata wins today) and BEFORE `find-default-target`. Once we delete the stale metadata, the preferred-target takes effect.

### §2.1 File to edit (not create) — `50-hapax-voice-duck.conf` notification block

Add **one line** inside the notification loopback's `capture.props` map. Do NOT put it on `playback.props` (which is the output-side sub-map and is merged/clobbered by `components.rules`); do NOT use `target.object` (which would also work but persists via `restore-stream` and will recur on every restart via the same mechanism we're fixing).

```conf
  # Notifications: system sounds, desktop notifications.
  # Priority 20. Routed to hapax-private (24c RIGHT, operator-only) — not broadcast.
  {
    name = libpipewire-module-loopback, type = pw-module
    arguments = {
      node.name = "loopback.sink.role.notification"
      node.description = "System Notifications"
      capture.props = {
        device.intended-roles = [ "Notification" ]
        policy.role-based.priority = 20
        policy.role-based.action.same-priority = "mix"
        policy.role-based.action.lower-priority = "mix"
        policy.role-based.preferred-target = "hapax-private"   # <-- ADD THIS LINE
      }
    }
    provides = loopback.sink.role.notification
  }
```

Why `capture.props` not `playback.props`: the `find-media-role-sink-target` hook looks up `policy.role-based.preferred-target` on the **input/sink** node of the link-group (line 45 of that script: `Constraint { "media.class", "=", "Audio/Sink" }`). The `capture.props` block on `module-loopback` produces that input sink.

Why this is resilient to the `components.rules` merge: the rule's `merge.arguments.capture.props` injects `{ policy.role-based.target, audio.position, media.class }`. These are additive — distinct keys — and do not collide with `policy.role-based.preferred-target`. SPA JSON config merge is key-level union on objects at the same depth; no entry in the rule shares this key.

### §2.2 Purge the persisted override (mandatory one-shot)

The config change has no effect until the persisted metadata is cleared. Two complementary steps:

```fish
# 1. Clear in-memory metadata for the three loopback output nodes.
pw-metadata 153 target.object
pw-metadata 156 target.object
pw-metadata 158 target.object

# 2. Remove the persisted row that repopulates on restart.
systemctl --user stop wireplumber
sed -i '/^Output\/Audio:media\.role:Loopback=/d' \
  "$HOME/.local/state/wireplumber/stream-properties"
systemctl --user start wireplumber
```

(The `sed` line deletes only the offending `media.role:Loopback` row; other persisted state — per-sink volumes, `hapax-livestream-tap` links, voice-fx routing — is preserved.)

### §2.3 Prophylactic: stop future moves from re-corrupting this row

Simplest, version-portable fix: add `state.restore = false` to each loopback's `playback.props`. This key is read by `linking/restore-stream.lua`; when false the stream is excluded from the `stream-properties` state file. Because `components.rules` applies a shared `playback.props` merge to every role loopback, add it once in the rule block and it covers all three:

```conf
# 50-hapax-voice-duck.conf — inside wireplumber.components.rules[0].actions.merge.arguments:
playback.props = {
  node.passive = true
  media.role = "Loopback"
  state.restore = false          # <-- new; excludes loopback outputs from stream-properties
}
```

Alternative, narrower: disable `linking.allow-moving-streams` globally (WP default true, see `/usr/share/wireplumber/wireplumber.conf:912-917`). This is too broad — you still want pavucontrol moves to work for normal streams. Prefer the `state.restore=false` form.

### §2.4 Expected `pw-link -l` after fix + WP restart

```
hapax-private:playback_FL
  |<- hapax-private-playback:output_FL                     (existing filter-chain internal)
  |<- output.loopback.sink.role.notification:output_FL     (NEW)
hapax-private:playback_FR
  |<- hapax-private-playback:output_FR
  |<- output.loopback.sink.role.notification:output_FR     (NEW)

hapax-livestream:playback_FL
  |<- hapax-livestream-tap-dst:output_FL
  |<- output.loopback.sink.role.multimedia:output_FL       (unchanged)
  |<- output.loopback.sink.role.assistant:output_FL        (unchanged)
hapax-livestream:playback_FR
  |<- hapax-livestream-tap-dst:output_FR
  |<- output.loopback.sink.role.multimedia:output_FR
  |<- output.loopback.sink.role.assistant:output_FR
```

The notification loopback output no longer appears on `hapax-livestream`.

---

## §3. Non-regression verification

Run each check after `systemctl --user restart wireplumber` and a manual stream trigger where appropriate.

1. **Notification isolated to hapax-private.**
   - `pw-link -l hapax-private | grep notification` — two matches (FL, FR).
   - `pw-link -l hapax-livestream | grep notification` — empty.
2. **Multimedia still on livestream.**
   - `pw-link -l hapax-livestream | grep role.multimedia` — two matches.
   - Sanity: `paplay --property=media.role=Music /usr/share/sounds/alsa/Front_Center.wav` — audible on livestream side only.
3. **Assistant still on livestream.**
   - `pw-link -l hapax-livestream | grep role.assistant` — two matches.
   - Sanity: run a Hapax TTS phrase (`media.role=Assistant` per `tts.py`). Audio on livestream. Other streams duck to 0.3x during the phrase.
4. **Ducking still works.**
   - Start a music player (implicit `media.role = Multimedia`). Trigger assistant TTS. Music volume should drop to ~30% and return. Confirmed behavior: `linking.role-based.duck-level = 0.3` is in `wireplumber.settings`, priorities are 10/20/40, `lower-priority = "duck"` is set on the assistant block.
5. **Ducking while notification plays.**
   - Notification (priority 20) vs multimedia (priority 10): `action.lower-priority = "mix"` on notification — multimedia does not duck. This is intentional and unchanged. The retarget does NOT alter duck semantics.
6. **Persisted state did not reappear.**
   - `grep 'media.role:Loopback' "$HOME/.local/state/wireplumber/stream-properties"` — empty after a restart + a manual stream move elsewhere in the system. If `state.restore=false` was added (§2.3), this will be empty forever.
7. **All three loopbacks present.**
   - `pw-cli ls Node | grep loopback.sink.role` — three nodes listed (multimedia, notification, assistant). None disappeared.
8. **No wireplumber errors.**
   - `journalctl --user -u wireplumber -b | grep -iE 'error|warn' | grep -v 'out of buffers'` — no new entries.

---

## §4. Rollback

One-line revert of the config change, one-line revert of the state purge. No data loss because we are not touching the filter-chains or the default sink.

```fish
# 1. Undo the preferred-target line in 50-hapax-voice-duck.conf
sed -i '/policy\.role-based\.preferred-target = "hapax-private"/d' \
  "$HOME/.config/wireplumber/wireplumber.conf.d/50-hapax-voice-duck.conf"

# 2. If state.restore=false was added, remove that line from the same file.
sed -i '/state\.restore = false/d' \
  "$HOME/.config/wireplumber/wireplumber.conf.d/50-hapax-voice-duck.conf"

# 3. Optionally restore the old "all three land on livestream" behaviour by
#    re-setting the metadata — not recommended, but included for completeness:
#    pw-metadata 156 target.object 86

# 4. Reload.
systemctl --user restart wireplumber
```

If ducking behaviour regresses, inspect `pw-metadata 0 current.role-based.volume.control` — it should list `input.loopback.sink.role.assistant` (the sink, priority 40). If it doesn't, the merge rule's `playback.props` was malformed.

---

## §5. Alternate architectures considered + rejected

1. **`playback.props.target.object = "hapax-private"` on the notification module** — the original attempt. Rejected for two reasons: (a) `components.rules` merges replacement `playback.props` on all role loopbacks; depending on WP's merge semantics for same-key nested objects this can either be a deep-merge (likely in 0.5.x, confirmed via source inspection of `components.rules` parser — merge is key-level union, not replace) or a replace. Even with deep-merge, (b) `restore-stream` persistence keyed on `media.role=Loopback` re-broadcasts the move to the other two loopbacks within a single run and the config change no longer has authority.

2. **New `51-notification-retarget.conf` with `wireplumber.settings.node.stream.rules`** matching on `node.name = "output.loopback.sink.role.notification"` and setting `node.target = "hapax-private"`. Works in principle, but duplicates state that already has a purpose-built path (`policy.role-based.preferred-target`), runs in a different hook (`find-defined-target`), and will be stomped by the same `restore-stream` metadata if it ever gets recorded. Strictly inferior.

3. **WirePlumber Lua script rule** (custom hook inheriting from `find-media-role-sink-target`). Unnecessary in WP >= 0.5.5 because the built-in hook already handles this use case. Lua hooks are the right tool for genuinely novel routing logic; this is not that.

4. **Match by `device.intended-roles = ["Notification"]` on a receiving-sink marker** on `hapax-private`. This would require `hapax-private` to advertise a role-receiver property, but `hapax-private` is created by `module-filter-chain` in `pipewire.conf.d`, not by WirePlumber, and the role-based target machinery in `find-media-role-sink-target.lua` looks up the target by `node.name` / `node.nick` (lines 63-71), not by a role-advertisement property on the sink. Using `preferred-target` with a name string is the only supported path.

5. **Move the split logic down to pavucontrol / manual per-stream routing at runtime**. Non-deterministic across reboots. Would re-create the exact `restore-stream` problem we are fixing. Rejected.

---

## Citations

- WirePlumber 0.5.x role-based linking policy: upstream example `media-role-nodes.conf` at `/usr/share/doc/wireplumber/examples/wireplumber.conf.d/media-role-nodes.conf` (Arch pkg `wireplumber-docs`, mirrors https://gitlab.freedesktop.org/pipewire/wireplumber/-/blob/master/src/config/wireplumber.conf.d.examples/media-role-nodes.conf).
- `policy.role-based.preferred-target` semantics: `/usr/share/wireplumber/scripts/linking/find-media-role-sink-target.lua` lines 38-79. Added upstream in wireplumber commit introducing `find-media-role-sink-target` (WP 0.5.5 cycle).
- Defined-target precedence: `/usr/share/wireplumber/scripts/linking/find-defined-target.lua` lines 45-69 — reads `si_props["target.object"]`, `si_props["node.target"]`, and default-metadata `target.object`/`target.node`.
- `linking.allow-moving-streams` default = true: `/usr/share/wireplumber/wireplumber.conf` lines 912-917.
- Stream restore state file: `~USER/.local/state/wireplumber/stream-properties` (documented at https://pipewire.pages.freedesktop.org/wireplumber/daemon/configuration/locations.html).
- Role-based ducking: `linking.role-based.duck-level` in settings schema (`/usr/share/wireplumber/wireplumber.conf` lines 904-910).

**File to edit:** `~USER/.config/wireplumber/wireplumber.conf.d/50-hapax-voice-duck.conf`
**State files touched:** `~USER/.local/state/wireplumber/stream-properties` (one row deleted)
**Service restart:** `systemctl --user restart wireplumber`
