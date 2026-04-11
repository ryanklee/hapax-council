## 24/7 Livestream Audit Plan: Legomena Live

**Date Created:** 2026-04-10  
**Stream Configuration:** 36-hour continuous livestream (Legomena Live)  
**Scope:** Complete system architecture verification and monitoring for production deployment

---

## A. COMPLETE COMPONENT INVENTORY

### A.1 Processing Pipeline Components

#### Graphics/Video Path
- **Studio Compositor (GStreamer)** — 6x camera inputs (Brio/C920) → CUDA tiling → overlay compositing → 24-slot GPU shader FX chain → v4l2loopback `/dev/video42` output
- **Shader Processors** — 24 preset slots with audio reactivity (brightness, vignette, bloom, flash scheduling)
- **Overlay Engines** (all on single Cairo layer post-FX):
  - YouTube Picture-in-Picture (ffmpeg subprocess, v4l2loopback read)
  - Album Cover overlay (512x512 colorized, bouncing)
  - Token Pole (Vitruvian Man spiral with particles)
  - Splattribution text (album ID + confidence)
  - Scrolling Lyrics
  - Pango text zones (85 docs, bouncing, multiple zones)

#### Video Input Sources
- 6x USB cameras: 3x Logitech Brio, 3x C920 (at `/dev/video0-9`)
- 3x Raspberry Pi NoIR (Pi-1 .78, Pi-2 .52, Pi-6 .81) with IR cameras (album detection)
- v4l2loopback devices: 5 total
  - `/dev/video10` (OBS capture)
  - `/dev/video42` (compositor output to OBS)
  - `/dev/video50-52` (YouTube video slots)

#### Audio Path
- **Audio Capture** (PipeWire direct):
  - `mixer_master` (music/vinyl, right channel only for track ID)
  - `echo_cancel_source` (voice, Yeti USB mic)
  - Contact Microphone (Cortado MKIII on PreSonus Studio 24c Input 2)
- **Audio Reactivity DSP** — RMS, beat detect, 3-band split (~60ms latency)
- **TTS Output** — Kokoro 82M (CPU, 24kHz) → WAV → pw-play

#### Video Decoding & Playback
- **YouTube Player daemon** — yt-dlp + ffmpeg (3-slot architecture):
  - Slot 0: Basquiat interview
  - Slot 1: Steve Jobs 1981
  - Slot 2: JCS Criminal Psychology
  - JPEG snapshot delivery (10fps) → `/dev/shm/hapax-compositor/yt-frame-{0,1,2}.jpg`
  - v4l2loopback output (`/dev/video50`)
  - PipeWire audio mix into `mixer_master`

### A.2 LLM/Processing Daemons

- **Album Identifier** — IR frame fetcher → Gemini Pro vision (splattributions) + audio fingerprinting + track ID + lyrics
- **Chat Monitor** — YouTube Live chat via chat-downloader → structural analysis (Gemini Flash) → token spend
- **Director Loop** (Reactor system) — 8s LLM perception (Gemini Flash multimodal) → Kokoro TTS → Obsidian logging
- **Logos API** (FastAPI `:8051`) — preset switching, graph mutations, orientation panel, vault relations
- **Logos Tauri App** — visual control surface, command registry, `__NV_DISABLE_EXPLICIT_SYNC=1` for Wayland

### A.3 Infrastructure Services

#### Docker Containers (all `restart: always`)
- **LiteLLM** (`:4000` council) — API gateway, Redis caching (1h TTL)
- **Qdrant** (vector DB) — 9 collections including affordances, studio-moments
- **PostgreSQL** — audit/observability
- **Langfuse** (`:3000`) — LLM observability
- **Prometheus** + **Grafana** — metrics/dashboards
- **Redis**, **ClickHouse**, **MinIO**, **n8n**, **ntfy**, **OpenWebUI**

#### Systemd User Services
- **hapax-secrets.service** (oneshot, credentials)
- **llm-stack.service** (Docker Compose, 13 containers)
- **logos-api.service** (`:8051`)
- **hapax-daimonion.service** (GPU STT, CPU TTS)
- **hapax-logos.service** (Tauri native app)
- **hapax-imagination.service** (GPU wgpu visual surface)
- **hapax-reverie.service** (visual expression daemon)
- **visual-layer-aggregator.service** (perception pipeline)
- **studio-compositor.service** (GPU GStreamer)
- **studio-fx-output.service** (ffmpeg `/dev/video50`)
- **chat-monitor.service** (NOT YET INSTALLED)
- **youtube-player.service** (system Python)
- **album-identifier.service** (created this session)
- **hapax-watch-receiver.service** (biometrics)
- **hapax-content-resolver.service**
- **hapax-imagination-loop.service**
- **rclone-gdrive-drop.timer** (5s bisync)
- 49 additional timers (sync, health, backups, rebuilds)

#### Pi NoIR Edge Daemons
- **hapax-pi1** (192.168.68.78) — ir-desk + HTTP frame server `:8090`
- **hapax-pi2** (192.168.68.52) — ir-room + HTTP frame server `:8090`
- **hapax-pi6** (192.168.68.81) — ir-overhead + album detection + HTTP frame server `:8090` + sync hub (8 tasks)

### A.4 Shared State Files (tmpfs + persistent)

#### `/dev/shm/hapax-compositor/` (tmpfs, ephemeral)
- `fx-snapshot.jpg` (1280x720, preview)
- `snapshot.jpg` (pre-FX, 1280x720)
- `album-cover.png` (512x512, colorized)
- `album-state.json` (splattribution state)
- `music-attribution.txt` (rendered text)
- `track-lyrics.txt` (scrolling overlay)
- `token-ledger.json` (pole state + cost tracking)
- `chat-state.json` (monitor metrics, when running)
- `yt-attribution.txt` (YouTube PiP credits)
- `youtube-video-id.txt` (chat-monitor input)
- `vinyl-mode.txt` ("true" for half-speed)
- `graph-mutation.json` (full graph updates)
- Per-camera snapshots: `brio-*.jpg`, `c920-*.jpg`
- Per-video slots: `yt-frame-{0,1,2}.jpg` (JPEG polling, 10fps)

#### Persistent State (Obsidian vault)
- `~/Documents/Personal/30-areas/legomena-live/attribution-log.md` (YouTube react content)
- `~/Documents/Personal/30-areas/legomena-live/reactor-log.md` (Director loop output)
- `~/Documents/Personal/30-areas/stream-overlays/` (85 Pango content docs)
- `~/Documents/Personal/30-areas/legomena-live/music-attribution-log.md` (splattributions)

#### Edge State (Pi fleet)
- `~/hapax-state/edge/hapax-pi*.json` (heartbeats)
- `~/hapax-state/pi-noir/{desk,room,overhead}.json` (IR detection reports)

### A.5 External Dependencies

| Dependency | Purpose | Fallback | Status |
|---|---|---|---|
| **Gemini Pro (LiteLLM)** | Album vision, splattributions, track audio | none | critical |
| **Gemini Flash (LiteLLM)** | Chat analysis, director perception | Sonnet (slower) | critical |
| **Claude Sonnet/Opus** | Fallback LLM routing | none | secondary |
| **YouTube Data API v3** | Live description auto-update, liveBroadcasts.list | manual | optional |
| **YouTube RTMP ingest** | Stream ingestion (via OBS) | none | critical |
| **KDE Connect** (D-Bus) | Phone → URL sharing | HTTP API fallback | optional |
| **Pi NoIR fleet HTTP** | Album detection frames | none | critical |
| **PipeWire mixer_master** | Vinyl audio capture | none | critical |
| **TabbyAPI** (GPU inference) | Local-fast routing | degraded (timeouts) | secondary |
| **Ollama** (CPU) | nomic-embed-cpu embedding | none | secondary |

---

## B. DEPENDENCY GRAPH

```
STREAM START
    ↓
OBS + NVENC H.264
    ↓
YouTube RTMP ← OBS is the SINGLE POINT OF FAILURE
    ↑
/dev/video42 (v4l2loopback) ← Studio Compositor feeds this
    ↑
┌─────────────────────────────────────────────┐
│ Studio Compositor (GPU GStreamer) — 30fps   │ ← depends on: CUDA, GStreamer plugins, cameras
│ ├─ 6x USB cameras                           │    no fallback to CPU in 36h (emergency only)
│ ├─ 24 shader slots (audio-reactive)         │    depends on: TabbyAPI for `local-fast` routing
│ ├─ Overlays (cairooverlay post-FX):         │    depends on: PipeWire (audio DSP)
│ │  ├─ YouTube PiP (ffmpeg subprocess)       │    depends on: youtube-player daemon
│ │  ├─ Album Cover + Splattribution          │    depends on: album-identifier daemon
│ │  ├─ Token Pole (spiral particles)         │    depends on: token-ledger.json writer
│ │  ├─ Lyrics scrolling                      │    depends on: album-identifier lyrics
│ │  └─ Pango text zones                      │    depends on: overlay_zones config
│ └─ Audio capture + DSP                      │
│    ├─ kick/bass detection → visual flash    │
│    └─ latency ~60ms                         │
└─────────────────────────────────────────────┘
    ↑           ↑                ↑
    │           │                │
    │    ┌──────┴────────┐      │
    │    │               │      │
    ↓    ↓               ↓      ↓
PipeWire mixer_master  v4l2loopback  Logos API
    ↑                      ↑          (preset switching)
    │                      │
    ├─ Vinyl audio (right channel, half-speed)
    │  ├─ album-identifier → track ID (2x speed-up)
    │  └─ album-identifier → lyrics (Gemini)
    │
    └─ Voice audio (echo_cancel_source)
       └─ hapax-daimonion TTS output
       └─ Contact mic (desk activity)

album-identifier daemon
    ├─ Pi-6 HTTP :8090 (IR frame fetch)
    ├─ Gemini Pro vision (splattributions)
    ├─ Gemini Flash audio (track ID)
    ├─ Gemini Flash text (lyrics)
    └─ token-ledger.json writer (WIRED? — P1 blocker)

youtube-player daemon (system Python)
    ├─ yt-dlp + ffmpeg (YouTube decode)
    ├─ KDE Connect D-Bus (phone URL share)
    ├─ v4l2loopback /dev/video50
    └─ PipeWire audio mix

chat-monitor daemon (NOT YET CREATED)
    ├─ YouTube Live chat-downloader
    ├─ nomic-embed (thread detection)
    ├─ Gemini Flash (batch analysis every 120s)
    ├─ token-ledger.json writer (superchat/membership boosts)
    └─ /dev/shm/hapax-compositor/youtube-video-id.txt (input)

hapax-daimonion (GPU STT, CPU TTS)
    ├─ Kokoro TTS (24kHz, CPU)
    ├─ Gemini Flash multimodal (8s perception)
    └─ Obsidian sync (reactor-log.md)

hapax-logos (Tauri) + Logos API (:8051)
    ├─ Command registry (preset switching)
    ├─ Visual surface HTTP (:8053)
    └─ FastAPI worker pool

hapax-imagination (GPU wgpu) — visual surface shader graphs
hapax-reverie — visual expression daemon
visual-layer-aggregator — perception pipeline
Pi-1/Pi-2/Pi-6 — edge daemons (IR detection)

SHUTDOWN DEPENDENCIES:
    systemd service restart chains:
    hapax-secrets → logos-api → hapax-daimonion (+10s delay)
                                      ↓
                              visual-layer-aggregator
                                      ↓
                              studio-compositor (+10s for cameras)
                                      ↓
                              studio-fx-output
    
    All services: Restart=on-failure with RestartSec < 10s
```

### A.5.1 Critical Path Analysis

**Failure Impact Cascade:**

| Component | Fails | Immediate Impact | 36h Risk |
|---|---|---|---|
| OBS | crash | STREAM STOPS | operator must restart (manual) |
| NVENC | stuck | frame freezes → OBS timeout | operator restart |
| YouTube RTMP | drop | auto-reconnect (OBS feature) | brief buffering |
| `/dev/video42` | stops | black frames to OBS | compositor auto-restart (10s) |
| Studio Compositor | crash | all overlays + effects stop | systemd Restart=on-failure |
| youtube-player | crash | PiP disappears | systemd auto-restart (~5s) |
| album-identifier | crash | splattribution freezes | systemd auto-restart (~5s) |
| chat-monitor | crash | token pole stops | **manual restart needed** |
| Pi-6 HTTP | down | album detection fails | pole stops advancing |
| PipeWire mixer_master | dies (USB) | vinyl + voice audio lost | **manual USB replug** |
| Gemini API rate limit | hit | LLM calls fail silently | graceful degradation (keep last value) |
| Pi NoIR DHCP lease | renews | IP changes | config uses env var (may stale) |
| token-ledger.json | race condition | concurrent write corruption | pole shows stale state |
| hls segment pruning | fails | `/dev/shm` fills (tmpfs) | 36h risk: medium |
| gdrive rsync | stalls | screenshot drops fail | non-critical |

---

## C. CHECK CATEGORIES

### Layer 1: Infrastructure (Docker, systemd, networking)
- Container health + restart behavior
- Systemd lingering + user services boot order
- Service dependency chains (After, Wants, Requires)
- Resource isolation (cgroups, memory limits, OOM scores)
- Network connectivity (Pi fleet, LiteLLM, external APIs)

### Layer 2: GPU/Hardware
- CUDA runtime + plugin availability
- GStreamer CUDA element loading
- GPU VRAM allocation + fragmentation
- NVIDIA encoder (NVENC) session limits
- USB camera device enumeration + stability
- v4l2loopback module state

### Layer 3: Audio Pipeline
- PipeWire mixer status + device state
- Audio capture thread lifecycle (pw-cat subprocess)
- Latency characteristics (60ms target)
- Audio reactivity DSP correctness (beat detection)
- Contact microphone signal quality

### Layer 4: Video Processing (GStreamer)
- Pipeline state transitions (NULL → PLAYING)
- Element negotiation (caps, formats, resolution)
- Temporal drift (framerate consistency)
- Memory management (buffer pool leaks)
- Audio-video sync offset (75ms target)
- Fallback paths (CPU path if CUDA unavailable)

### Layer 5: Content Pipeline
- YouTube video fetch (yt-dlp URL expiry, 6h limit)
- FFmpeg subprocess lifecycle (PiP decoding)
- Album identification (Pi-6 HTTP, Gemini API)
- Track fingerprinting (fallback to Gemini context)
- Lyrics generation + scrolling overlay
- Splattribution confidence + hallucination quality

### Layer 6: Engagement System (Token Pole)
- Token ledger file state (concurrent writers)
- Token accumulation (chat, LLM calls, superchats)
- Pole position calculation + explosion triggers
- Particle effects rendering
- Vitruvian spiral mathematics + clipping

### Layer 7: Chat Monitoring
- Chat-downloader reconnect logic
- Embedding freshness (nomic-embed cache)
- Batch interval (120s) consistency
- Thread detection (cosine similarity threshold)
- Gemini Flash token spend tracking

### Layer 8: Logging & Observability
- Obsidian attribution/reactor logs (append-only)
- Persistent JSON state files (atomic writes)
- journalctl log volume + retention
- Langfuse trace accumulation
- Screenshot drop cadence (5s rsync)

### Layer 9: Fault Recovery
- Service auto-restart behavior + timing
- Manual intervention vectors (chat-monitor, mixer USB)
- Single points of failure (OBS, RTMP)
- Emergency CPU fallback path
- Graceful degradation (last-value caching)

---

## D. PER-CHECK SPECIFICATION

### Check Format Template

**[CHECK_ID] [Category] — [Component]**

**What to Verify:** [description of expected state]

**How to Verify:** [exact command(s)]

**PASS Criteria:** [conditions for success]

**FAIL Criteria:** [conditions for failure]

**WARN Criteria:** [conditions for concern but not failure]

**Remediation:** [action to fix]

---

### INFRASTRUCTURE CHECKS

**[I01] Container Health — LiteLLM**

**What to Verify:** All 13 Docker containers running with `restart: always` and accepting connections.

**How to Verify:**
```bash
docker ps --format "table {{.Names}}\t{{.Status}}"
curl -s http://localhost:4000/health -w "\n"  # LiteLLM council
curl -s http://localhost:4100/health -w "\n"  # LiteLLM officium
```

**PASS Criteria:**
- All 13 containers showing "Up" with no restarts in last 5 min
- Both LiteLLM health endpoints return 200 + valid JSON

**FAIL Criteria:**
- Any container in "Exited" state
- LiteLLM endpoints timeout or 500 error
- Log shows OOM kills in last 24h

**WARN Criteria:**
- Container restarted 1-2 times in last 5 min (may recover)
- LiteLLM response time >2s

**Remediation:**
```bash
docker logs <container-name> | tail -50  # check root cause
docker-compose up -d --force-recreate <service>  # rebuild if needed
```

---

**[I02] Systemd Boot Order — Service Dependencies**

**What to Verify:** All systemd user services have correct dependency chains and linger is enabled.

**How to Verify:**
```bash
loginctl user-status  # verify lingering
for svc in hapax-secrets llm-stack logos-api hapax-daimonion studio-compositor; do
  echo "=== $svc ==="
  systemctl --user cat $svc | grep -E "^After|^Requires|^Wants"
done
systemctl --user status graphical-session.target  # verify Wayland/X11 running
```

**PASS Criteria:**
- `loginctl show-user <name>` shows `Linger=yes`
- All services have explicit `After` dependencies matching the documented boot sequence
- `graphical-session.target` is `active`

**FAIL Criteria:**
- Linger is disabled
- Any service missing After dependencies
- Circular dependencies detected

**WARN Criteria:**
- Service restart count >5 in last hour (may be thrashing)

**Remediation:**
```bash
loginctl enable-linger  # if disabled
systemctl --user daemon-reload
systemctl --user restart multi-user.target
```

---

**[I03] Secrets Availability — hapax-secrets.service**

**What to Verify:** Credential loading service runs once at boot and all required keys are present.

**How to Verify:**
```bash
systemctl --user status hapax-secrets
ls -la /run/user/$(id -u)/hapax-secrets.env  # should exist, 0600
source /run/user/$(id -u)/hapax-secrets.env && \
  env | grep -E "LITELLM|LANGFUSE|HF_TOKEN"
pass show litellm/master-key >/dev/null 2>&1 && echo "OK" || echo "FAIL"
pass show google/token >/dev/null 2>&1 && echo "OK" || echo "FAIL"
```

**PASS Criteria:**
- `hapax-secrets.service` shows `Active: active (exited)` (oneshot)
- All required keys present in pass store
- `/run/user/.../hapax-secrets.env` exists with 0600 permissions
- All LLM services have sourced the env file (can verify via `ps e | grep LITELLM_API_KEY`)

**FAIL Criteria:**
- File missing or wrong permissions
- Any key missing from pass store
- Services not sourcing the env file

**WARN Criteria:**
- Google token scope missing `youtube.force-ssl` (checked at launch)

**Remediation:**
```bash
pass insert litellm/master-key  # if missing
systemctl --user restart hapax-secrets
systemctl --user restart logos-api  # force re-source
```

---

**[I04] Network Connectivity — Pi NoIR Fleet**

**What to Verify:** All 3 Pi edge daemons respond to HTTP frame server requests.

**How to Verify:**
```bash
for ip in 192.168.68.78 192.168.68.52 192.168.68.81; do
  echo "Pi at $ip:"
  curl -s -o /dev/null -w "HTTP %{http_code} " http://$ip:8090/frame.jpg
  curl -s -I http://$ip:8090/album.json | head -3
done
```

**PASS Criteria:**
- All 3 IPs respond with HTTP 200
- Response time <500ms for each

**FAIL Criteria:**
- Any IP unreachable or timeout (>5s)
- HTTP error codes (4xx, 5xx)

**WARN Criteria:**
- Response time 2-5s (network congestion)
- Intermittent 5xx on album.json (detection still computing)

**Remediation:**
```bash
# If Pi-6 IP changed (DHCP):
nmap -p 22 --open 192.168.68.0/24  # find new IP
ssh pi@192.168.68.NEW "systemctl status hapax_ir_edge"
# Update PI6_IP in album-identifier.service
```

---

**[I05] Resource Isolation — Memory Limits**

**What to Verify:** All services have memory limits set via systemd and no OOM kills observed.

**How to Verify:**
```bash
for svc in hapax-daimonion studio-compositor logos-api visual-layer-aggregator; do
  echo "=== $svc ==="
  systemctl --user cat $svc | grep MemoryMax
done
journalctl --user -p crit -n 50 | grep -E "OOM|oom"
dmesg | tail -20 | grep -i oom
```

**PASS Criteria:**
- All services with MemoryMax set (hapax-daimonion: 8G, studio-compositor: 4G, etc.)
- No OOM-killer invocations in last 24h

**FAIL Criteria:**
- Any service missing MemoryMax
- Recent OOM kills (dmesg within 1h)

**WARN Criteria:**
- Service using >90% of its MemoryMax limit

**Remediation:**
```bash
# Add to systemd drop-in:
echo "[Service]\nMemoryMax=8G" > ~/.config/systemd/user/<svc>.service.d/memory.conf
systemctl --user daemon-reload && systemctl --user restart <svc>
```

---

### GPU & HARDWARE CHECKS

**[G01] CUDA Runtime — Plugin Registry**

**What to Verify:** CUDA 13.x is installed, GStreamer can load nvcodec elements, compositor uses CUDA path.

**How to Verify:**
```bash
# Check CUDA runtime
nvidia-smi --version  # expect 13.x
ldconfig -p | grep "libnvrtc-builtins.so.13"  # must exist
grep -r "libnvrtc-builtins" /etc/ld.so.conf.d/  # should be in cuda.conf

# Check GStreamer plugin
rm ~/.cache/gstreamer-1.0/registry.x86_64.bin  # force re-probe
gst-inspect-1.0 cudacompositor 2>&1 | head -20

# Check compositor logs
systemctl --user status studio-compositor
journalctl --user -u studio-compositor --since "5 min ago" | \
  grep -E "FX chain|fallback|CUDA|cudacompositor"
```

**PASS Criteria:**
- CUDA 13.x installed
- `libnvrtc-builtins.so.13.2` in ldconfig output
- `gst-inspect-1.0 cudacompositor` returns element definition (not "no such element")
- Compositor logs show "FX chain: 24 shader slots" within last 5 min
- No "falling back to CPU" message

**FAIL Criteria:**
- CUDA missing or wrong version
- Compositor running on CPU fallback (visible in logs)
- GStreamer element inspect fails

**WARN Criteria:**
- `ldconfig` warnings but element still loads

**Remediation:**
```bash
# If cudacompositor missing from registry:
pacman -Qk opencv-cuda  # check package state
rm -rf /var/lib/pacman/local/opencv-cuda-*/
pacman -U --overwrite '*' /var/cache/pacman/pkg/opencv-cuda-*.pkg.tar.zst
sudo ldconfig
systemctl --user restart studio-compositor
```

---

**[G02] GPU VRAM — Allocation & Fragmentation**

**What to Verify:** GPU VRAM usage is stable and has headroom for NVENC overlay.

**How to Verify:**
```bash
nvidia-smi --query-gpu=index,utilization.gpu,utilization.memory,memory.used,memory.free \
  --format=csv,noheader -l 5  # poll every 5s for 30s

# Capture baseline during no-load, then during streaming
nvidia-smi --query-compute-apps=pid,process_name,used_memory --format=csv,noheader
lsof -p $(pgrep -f studio-compositor) | grep -i gpu  # check mapped CUDA memory

# Check for fragmentation (if possible)
nvidia-smi -q -d MEMORY  # memory regions
```

**PASS Criteria:**
- VRAM usage stable (±200MB variation over 5 min)
- Total used <20GB on 24GB card (headroom for NVENC)
- GPU utilization 20-40% during streaming
- No memory fragmentation spikes

**FAIL Criteria:**
- VRAM growing >500MB/min (leak)
- Usage >23GB (OOM risk)
- GPU utilization <5% (not using CUDA)

**WARN Criteria:**
- VRAM usage oscillating between 15-20GB (near limit)
- GPU utilization >95% (thermal throttle risk)

**Remediation:**
```bash
nvidia-smi -pm 1  # enable persistence mode (reduces init overhead)
systemctl --user restart studio-compositor  # restart if leaking
kill -9 $(pgrep -f broken_gstreamer_process)  # force cleanup if needed
```

---

**[G03] USB Cameras — Device Enumeration**

**What to Verify:** All 6 USB cameras are enumerated and accessible to compositor process.

**How to Verify:**
```bash
ls -la /dev/video{0..9}  # all should exist
v4l2-ctl --list-devices | grep -E "Brio|C920"  # count
v4l2-ctl -d /dev/video0 --get-fmt-video 2>&1 | head -3  # test one

# Check compositor can read frames
ps aux | grep studio-compositor | grep -v grep  # confirm process
strace -p $(pgrep -f studio-compositor) -e openat 2>&1 | grep video | head -5 &
sleep 3 && kill %1  # sample 3s of syscalls
```

**PASS Criteria:**
- `/dev/video0` through `/dev/video9` all exist
- At least 6 camera devices detected (3 Brio, 3 C920)
- All devices readable (no permission errors)
- Compositor process has open file descriptors to camera devices

**FAIL Criteria:**
- Fewer than 6 cameras present
- Camera device inaccessible (permission error, uninitialized)

**WARN Criteria:**
- Camera device shows "Connection refused" (USB bus issue, may recover)

**Remediation:**
```bash
# Rescan USB bus
echo "Rescanning USB..."
for port in /sys/bus/usb/devices/*/power/autosuspend; do echo -1 > "$port"; done  # disable autosuspend
lsusb | grep -i "logitech\|razer"  # verify enumeration

# Restart compositor to re-open
systemctl --user restart studio-compositor
```

---

**[G04] v4l2loopback — Module State**

**What to Verify:** v4l2loopback module is loaded with correct parameters and `/dev/video42` is writable by compositor, readable by OBS.

**How to Verify:**
```bash
lsmod | grep v4l2loopback
modinfo v4l2loopback | grep -E "^parm"  # show available parameters

# Check devices
v4l2-ctl --list-devices | grep -E "video(10|42|50|51|52)"
ls -la /dev/video{10,42,50,51,52}

# Test compositor can write to /dev/video42
v4l2-ctl -d /dev/video42 --get-fmt-video 2>&1

# Test OBS can read (simulate)
cat /dev/video42 2>&1 | head -1  # should not hang; may show binary frame data
```

**PASS Criteria:**
- v4l2loopback module loaded
- `/dev/video42` exists, writable by compositor, readable by OBS (nobody)
- `v4l2-ctl` returns valid format (1920x1080)
- No caps renegotiation errors in journalctl

**FAIL Criteria:**
- Module not loaded
- Device file missing or wrong permissions
- Format negotiation fails

**WARN Criteria:**
- `exclusive_caps` mismatch (10/42 should be 1, 50-52 should be 0)

**Remediation:**
```bash
# If module not loaded:
sudo modprobe v4l2loopback exclusive_caps=1 devices=1,2,3,4,5
# Add to /etc/modprobe.d/v4l2loopback.conf to persist

# If caps negotiation failing, add probe to GStreamer:
# (already in pipeline.py::_add_v4l2sink_caps_dedup_probe)
systemctl --user restart studio-compositor
```

---

**[G05] NVENC Encoder — Session Limits**

**What to Verify:** NVIDIA NVENC encoder can open a session and OBS can use it without resource contention.

**How to Verify:**
```bash
# Check available NVENC sessions (free driver allows ~3)
nvidia-smi dmon -s pucvmet | head -20  # monitor while encoding

# Start test encode in OBS (if running)
systemctl --user is-active hapax-logos  # check if Logos UI might conflict
ps aux | grep OBS | grep -v grep  # check OBS status

# Query encoder state
nvidia-smi -q | grep -A 10 "Encoder Processes"
```

**PASS Criteria:**
- NVENC encoder sessions <3 at any time
- OBS can start streaming without encoder allocation failures
- No GPU memory errors related to NVENC in nvidia-smi or dmesg

**FAIL Criteria:**
- NVENC allocation failures in OBS logs
- >3 encoder sessions (driver limitation)

**WARN Criteria:**
- NVENC clock throttling detected (thermal)

**Remediation:**
```bash
# If NVENC stuck, restart OBS
killall -9 obs
# Give GPU 10s to release session
sleep 10
# Restart OBS
```

---

### AUDIO PIPELINE CHECKS

**[A01] PipeWire — Mixer Status & Device State**

**What to Verify:** PipeWire daemon is running, `mixer_master` device exists, audio is flowing.

**How to Verify:**
```bash
systemctl --user status pipewire pipewire-pulse  # both should be active
pactl list short sinks | grep mixer  # should see mixer_master
pactl list short sources | grep -E "Yeti|Contact|Cortado"  # input devices

# Test audio flow
pw-cat --record --target "mixer_master" -t float32 2>&1 | timeout 2 cat | wc -c
# should show bytes recorded (non-zero)

# Check latency
pw-dump | grep -A 5 "mixer_master" | grep -E "latency|rate"

# Check for underruns
journalctl --user -u pipewire -n 100 | grep -i "underrun\|xrun"
```

**PASS Criteria:**
- pipewire and pipewire-pulse both running
- `mixer_master` device exists and has active streams
- Audio bytes flowing (non-zero byte count on record)
- No recent underruns in logs

**FAIL Criteria:**
- pipewire daemon not running
- mixer_master device missing
- Latency >100ms
- Frequent xruns/underruns in last 5 min

**WARN Criteria:**
- Latency 50-100ms (borderline)
- Occasional underrun (may recover)

**Remediation:**
```bash
systemctl --user restart pipewire pipewire-pulse
# If devices missing, replug audio interface
pacmd rescan-devices
pactl set-default-sink @DEFAULT_SINK@  # reset default
```

---

**[A02] Audio Capture Thread — pw-cat Subprocess**

**What to Verify:** Compositor's audio capture thread is running and pw-cat subprocess is alive.

**How to Verify:**
```bash
ps aux | grep "studio-compositor" | grep -v grep
pgrep -a -f "pw-cat.*mixer_master\|pw-cat.*Contact"  # should find subprocesses

# Check thread count
ps -eLf | grep studio-compositor | wc -l  # should be multiple

# Monitor for stalls
python3 -c "
import subprocess, json, time
while True:
    result = subprocess.run(['pw-stat'], capture_output=True, text=True)
    print(f'{time.time()}: {len(result.stdout)} bytes')
    time.sleep(1)
" &
BG_PID=$!
sleep 10 && kill $BG_PID  # sample for 10s

# Check thread health
journalctl --user -u studio-compositor --since "5 min ago" | \
  grep -iE "thread|capture|audio|error"
```

**PASS Criteria:**
- Compositor process alive with multiple threads
- pw-cat subprocesses for mixer_master and Contact mic both running
- Thread count stable over 5 min
- No "thread died" errors in logs

**FAIL Criteria:**
- Compositor has no audio threads
- pw-cat subprocess not running or frequently restarting
- Thread count declining (threads dying without restart)

**WARN Criteria:**
- Thread count increasing slowly (memory leak)

**Remediation:**
```bash
# If thread died, restart compositor:
systemctl --user restart studio-compositor

# If pw-cat stuck, kill and let supervisor restart it:
pkill -f "pw-cat.*mixer_master"
# Compositor will spawn new one within 1s
```

---

**[A03] Audio Reactivity DSP — Beat Detection**

**What to Verify:** Audio reactivity is responding to music with beat flashes and brightness sidechaining.

**How to Verify:**
```bash
# Play test audio through mixer_master
ffplay ~/music/test-kick-heavy.mp3  # ~20s track with clear kicks

# Monitor beat detection in logs
journalctl --user -u studio-compositor --follow | \
  grep -E "kick|beat|flash|sidechain" &
LOG_PID=$!

# Watch output
watch -n 0.5 'convert /dev/shm/hapax-compositor/fx-snapshot.jpg -format "%[fx:mean]" info: | head -1' &
WATCH_PID=$!

# Sleep while watching
sleep 30
kill $LOG_PID $WATCH_PID
# Brightness should pulse with kicks
```

**PASS Criteria:**
- Visual flash appears on kick onset (within 100ms)
- Brightness ducks on bass (smooth -0.7 curve)
- No audio glitches or DSP errors in logs
- Latency <100ms from kick to visual response

**FAIL Criteria:**
- No visual response to audio
- DSP errors in logs (e.g., "RMS calculation failed")

**WARN Criteria:**
- Response latency 100-200ms (perceptible delay)

**Remediation:**
```bash
# If DSP broken, restart compositor:
systemctl --user restart studio-compositor

# If latency high, check CPU usage:
top -p $(pgrep -f studio-compositor)  # if >80% CPU, reduce shader slot count
```

---

**[A04] Audio-Video Sync Offset**

**What to Verify:** Audio and video are synchronized with 75ms offset (configured in OBS).

**How to Verify:**
```bash
# Check OBS config (requires manual inspection):
grep -r "sync_offset\|delay" ~/.config/obs-studio/ 2>/dev/null

# Run lip-sync test: play video with visible speaker + audio
# Mark video frame where mouth moves, count frames to audio playback
# At 30fps, each frame is 33ms; expected offset ~2-3 frames = 66-99ms

# Or use ffmpeg to compare:
ffmpeg -i /dev/video42 -af "aformat=sample_rates=48000" -t 30 test_sync.mp4
# Manually inspect or use sync detection tool
```

**PASS Criteria:**
- OBS configured with 75ms sync offset
- Visual speaker mouth movement aligns with audio within 1 frame (33ms)

**FAIL Criteria:**
- Audio leading video by >100ms (hearing before seeing)
- Video leading audio by >50ms (seeing before hearing)

**WARN Criteria:**
- Offset 50-99ms (acceptable but verify manually)

**Remediation:**
```bash
# Adjust OBS Settings → Audio → Sync Offset on video source:
# Increase offset if audio leading; decrease if video leading
# Retest with lip-sync reference video
```

---

### VIDEO PROCESSING CHECKS

**[V01] GStreamer Pipeline — State Transitions**

**What to Verify:** Compositor pipeline successfully transitions to PLAYING state and stays stable.

**How to Verify:**
```bash
# Monitor pipeline state
journalctl --user -u studio-compositor --since "10 min ago" | \
  grep -E "state|PLAYING|NULL|ERROR"

# Check for bus errors
GST_DEBUG=3 gst-launch-1.0 videotestsrc ! queue ! v4l2sink device=/dev/video99 2>&1 | \
  grep -i error  # simple test pipeline

# Real pipeline state
systemctl --user status studio-compositor | grep Active
ps aux | grep studio-compositor | grep -v grep  # process running

# Trigger source change and observe caps negotiation
# (if input-selector implemented)
curl -s -X POST http://localhost:8051/api/studio/source/switch \
  -H 'Content-Type: application/json' -d '{"source":"brio-operator"}' || true
sleep 2
journalctl --user -u studio-compositor -n 20 | grep -i "caps\|negotiat"
```

**PASS Criteria:**
- Pipeline reaches PLAYING state on startup
- Stays in PLAYING state for duration of check (no ERROR bus messages)
- Source switching negotiates caps without hangs

**FAIL Criteria:**
- Pipeline fails to reach PLAYING (shows ERROR in logs)
- Pipeline constantly transitioning (thrashing between states)

**WARN Criteria:**
- Caps negotiation takes >5s
- Bus warnings (non-fatal, but flag for investigation)

**Remediation:**
```bash
# If pipeline stalls:
systemctl --user restart studio-compositor

# If specific element fails:
GST_DEBUG=<element>:6 systemctl --user restart studio-compositor
journalctl --user -u studio-compositor | head -100  # check what failed
```

---

**[V02] v4l2sink — Caps Renegotiation**

**What to Verify:** Output device `/dev/video42` doesn't experience caps cascades during source switching.

**How to Verify:**
```bash
# Monitor caps events during source switch
journalctl --user -u studio-compositor --follow | \
  grep -E "caps|renegotiat|v4l2sink" &
LOG_PID=$!

# Trigger source switch if available
curl -s -X POST http://localhost:8051/api/studio/source/switch \
  -H 'Content-Type: application/json' -d '{"source":"brio-room"}' || true

sleep 5
kill $LOG_PID

# Count caps events
journalctl --user -u studio-compositor -n 500 | grep -c "CAPS"
# Should be <5; >10 indicates cascading
```

**PASS Criteria:**
- Source switch negotiates caps 1-2 times (not cascading)
- No v4l2sink device-busy errors
- Output resolution stays 1920x1080

**FAIL Criteria:**
- Caps events >10 in 5s (cascade)
- v4l2sink "device busy" errors

**WARN Criteria:**
- Single "NEW CAPS" event (normal, but verify no cascade follows)

**Remediation:**
```bash
# If cascading, caps dedup probe should catch it:
# (already implemented in pipeline.py::_add_v4l2sink_caps_dedup_probe)
systemctl --user restart studio-compositor

# If still cascading, disable dynamic source switching (use fixed source)
```

---

**[V03] Temporal Drift — Framerate Consistency**

**What to Verify:** Output framerate stays at 30 fps with <1 frame variance.

**How to Verify:**
```bash
# Measure framerate from fx-snapshot.jpg timestamp deltas
python3 << 'EOF'
import os, time
import subprocess

times = []
for i in range(30):  # collect 30 samples
    stat = os.stat("/dev/shm/hapax-compositor/fx-snapshot.jpg")
    times.append(stat.st_mtime)
    time.sleep(0.1)

deltas = [times[i+1] - times[i] for i in range(len(times)-1)]
fps = [1 / (d or 1) for d in deltas if d > 0]
fps_avg = sum(fps) / len(fps) if fps else 0
fps_std = (sum((f - fps_avg)**2 for f in fps) / len(fps))**0.5 if fps else 0

print(f"FPS avg: {fps_avg:.2f}, std: {fps_std:.2f}, samples: {len(fps)}")
print(f"Range: {min(fps) if fps else 0:.2f} - {max(fps) if fps else 0:.2f}")
EOF

# Or use ffmpeg to measure from v4l2sink output
ffmpeg -f v4l2 -i /dev/video42 -t 5 -vstats_file /tmp/vstats.txt -f null - 2>&1 | tail -5
grep "frame=" /tmp/vstats.txt | tail -1  # check frame count
```

**PASS Criteria:**
- FPS average 29.5-30.5
- FPS standard deviation <0.5
- No frame drops (every frame timestamp present)

**FAIL Criteria:**
- FPS <28 or >31 (off-speed)
- FPS std >1.5 (jittery)
- Dropped frames

**WARN Criteria:**
- FPS std 0.5-1.5 (acceptable but monitor)

**Remediation:**
```bash
# If off-speed, check smooth_delay config:
grep -n "fps\|framerate" agents/studio_compositor/smooth_delay.py
# Must match models.py:73 (framerate=30)

# If jittery, check GPU overload:
nvidia-smi  # if >95% util, reduce shader slots or preset complexity

systemctl --user restart studio-compositor
```

---

**[V04] Memory Leaks — Buffer Pool & Surface Caching**

**What to Verify:** GStreamer buffer pools don't leak and cairo surfaces are freed.

**How to Verify:**
```bash
# Monitor RSS growth over 5 minutes
baseline=$(pmap -x $(pgrep -f studio-compositor) 2>/dev/null | grep total | awk '{print $3}')
echo "Baseline RSS: ${baseline} KB"

sleep 300  # wait 5 min

final=$(pmap -x $(pgrep -f studio-compositor) 2>/dev/null | grep total | awk '{print $3}')
echo "Final RSS: ${final} KB"

growth=$((final - baseline))
rate=$((growth / 5))  # KB/min
echo "Growth: ${growth} KB, rate: ${rate} KB/min"

# Safe threshold: <50 MB/hour = <833 KB/min
if [ "$rate" -gt 833 ]; then
  echo "WARNING: Memory leak detected"
fi

# Check for cairo surface accumulation
journalctl --user -u studio-compositor | grep -i "cairo\|surface" | wc -l
# Should be minimal; expect <10 per 5min operation
```

**PASS Criteria:**
- RSS growth <50 MB/hour (<833 KB/min)
- Cairo surface log messages minimal

**FAIL Criteria:**
- RSS growth >100 MB/hour (1666+ KB/min)
- Thousands of surface log messages

**WARN Criteria:**
- Growth 50-100 MB/hour (borderline)

**Remediation:**
```bash
# If leaking, check Python GC:
python3 -c "
import gc
gc.collect()  # force full garbage collection in subprocess
" &
systemctl --user restart studio-compositor  # restart to clear

# If leak persists, profile with:
python3 -m tracemalloc studio_compositor.py
# (requires code changes; file a bug for investigation)
```

---

**[V05] Shader Slots — FX Chain Loading**

**What to Verify:** All 24 shader slots load successfully and are available for switching.

**How to Verify:**
```bash
# Check compositor logs on startup
journalctl --user -u studio-compositor --since "1 min ago" | \
  grep -i "FX chain\|shader\|slot\|loading"

# Query available presets via API
curl -s http://localhost:8051/api/studio/effect/list | jq '.presets | length'
# Should be >20

# Test switching to each preset
for preset in halftone ghost pixsort dither; do
  curl -s -X POST http://localhost:8051/api/studio/effect/select \
    -H 'Content-Type: application/json' -d "{\"preset\":\"${preset}_preset\"}"
  sleep 2
  # visually confirm effect appears
done
```

**PASS Criteria:**
- Startup logs show "FX chain: 24 shader slots"
- API returns >20 available presets
- Preset switches apply within 1-2s

**FAIL Criteria:**
- Fewer than 20 presets available
- Preset switch fails (HTTP 500 or timeout)
- Shader compilation errors in logs

**WARN Criteria:**
- Slot count <24 (some slots disabled due to shader errors)

**Remediation:**
```bash
# If slots missing:
journalctl --user -u studio-compositor | grep -i "error\|fail" | head -20
# Look for shader compilation errors

# Rebuild effect graph:
curl -s -X POST http://localhost:8051/api/studio/rebuild-graph

# Restart if needed:
systemctl --user restart studio-compositor
```

---

**[V06] Dithering — Sawtooth Pattern Detection**

**What to Verify:** Bayer dithering is disabled on all `videoconvert` elements (no sawtooth artifacts).

**How to Verify:**
```bash
# Check source code for dither=0 on all videoconvert instances
grep -r "videoconvert.*dither\|dither.*=.*0" \
  agents/studio_compositor/pipeline.py agents/studio_compositor/cameras.py

# Visually inspect output for vertical sawtooth pattern
# Capture 10 frames and look for diagonal lines:
for i in {1..10}; do
  convert /dev/shm/hapax-compositor/snapshot.jpg \
    -sampling-factor 1x1 /tmp/frame_$i.jpg
  sleep 0.3
done

# Subtle pattern = acceptable; obvious lines = problem
```

**PASS Criteria:**
- All `videoconvert` elements have `dither=0` in source
- Visual inspection shows no obvious sawtooth pattern
- Subtle dithering allowed (normal)

**FAIL Criteria:**
- Any `videoconvert` without `dither=0`
- Obvious diagonal or sawtooth pattern visible

**REMEDIATION:**
```bash
# Add dither=0 to GStreamer pipeline:
gst-element-check-1.0 videoconvert  # verify param exists

# If element doesn't support dither, use videoconvert property:
gst-launch-1.0 ... ! videoconvert dither=0 ! ...

systemctl --user restart studio-compositor
```

---

### CONTENT PIPELINE CHECKS

**[C01] YouTube Video Fetch — URL Expiry**

**What to Verify:** YouTube video URLs are refreshed before 6h expiry and videos decode without stalls.

**How to Verify:**
```bash
# Check youtube-player daemon logs
journalctl --user -u youtube-player --since "10 min ago" | \
  grep -E "URL|expir|refresh|ffmpeg"

# Monitor ffmpeg subprocess
ps aux | grep -E "ffmpeg.*youtube|yt-dlp" | grep -v grep

# Test URL fetch and decode
curl -s -X POST http://localhost:8055/status | jq '.current_url'

# Verify URL is fresh:
# yt-dlp shows "expires" field; should be >5h from now
youtube-dl --dump-json "https://youtube.com/watch?v=SHORT_ID" 2>/dev/null | \
  jq '.format[0].url' | grep -E "&expire=" | sed 's/.*expire=//' | \
  while read exp; do
    now=$(date +%s)
    diff=$((exp - now))
    hours=$((diff / 3600))
    echo "URL expires in $hours hours"
  done
```

**PASS Criteria:**
- ffmpeg subprocess actively decoding (shows in ps output)
- URL "expires" field shows >5 hours remaining
- No decode errors in logs

**FAIL Criteria:**
- ffmpeg exits with error (would appear in journalctl)
- URL already expired (ffmpeg returns 403)

**WARN Criteria:**
- URL expiring in <2 hours (refresh needed)

**Remediation:**
```bash
# Force URL refresh:
curl -s -X POST http://localhost:8055/refresh-url

# If daemon crashed:
systemctl --user restart youtube-player

# Manually trigger new yt-dlp fetch if needed:
yt-dlp -f best[ext=mp4] "https://youtube.com/watch?v=ID" --socket-timeout 30
```

---

**[C02] Album Identification — Pi-6 HTTP & Gemini API**

**What to Verify:** Album detection fetches frames from Pi-6 and Gemini returns splattributions.

**How to Verify:**
```bash
# Check album-identifier daemon
systemctl --user status album-identifier
journalctl --user -u album-identifier --since "5 min ago" | \
  grep -E "fetch|Gemini|splattribution|error"

# Test Pi-6 frame fetch
curl -s http://192.168.68.81:8090/frame.jpg -o /tmp/test_frame.jpg && \
  file /tmp/test_frame.jpg  # should be JPEG

# Test Gemini API (if LiteLLM is running)
python3 << 'EOF'
import requests
response = requests.post("http://localhost:4000/chat/completions",
  json={"model": "gemini-pro", "messages": [{"role": "user", "content": "test"}]},
  timeout=10)
print(f"Status: {response.status_code}, Tokens: {response.json().get('usage', {})}")
EOF

# Check current splattribution state
cat /dev/shm/hapax-compositor/album-state.json | jq '.artist,.title,.confidence'
```

**PASS Criteria:**
- album-identifier daemon active
- No errors in logs
- Pi-6 frame fetch succeeds (HTTP 200)
- Gemini API responding with token counts
- album-state.json updated within last 30s

**FAIL Criteria:**
- Daemon in failed state
- Pi-6 HTTP 404 or timeout
- Gemini API errors (401, 503, timeout)

**WARN Criteria:**
- album-state.json stale >2 min (may indicate slow detection)

**Remediation:**
```bash
# If Pi-6 unreachable, check IP:
nmap -p 22,8090 --open 192.168.68.0/24 | grep -A 1 "Nmap scan"
# Update PI6_IP env var in service if IP changed

# If Gemini API failing, check LiteLLM:
curl -s http://localhost:4000/health
systemctl --user status llm-stack  # Docker containers

# Restart daemon:
systemctl --user restart album-identifier
```

---

**[C03] Track Identification — Vinyl Audio & Gemini**

**What to Verify:** Right-channel vinyl audio is captured, speed-corrected, and sent to Gemini for track ID.

**How to Verify:**
```bash
# Verify right-channel extraction configured
grep -n "right channel\|c1\|pan=" agents/studio_compositor/audio_capture.py

# Check track identification in logs
journalctl --user -u album-identifier --since "5 min ago" | \
  grep -E "track.*ID\|track.*Gemini\|lyrics"

# Verify lyrics are rendered
cat /dev/shm/hapax-compositor/track-lyrics.txt | head -10
# Should contain song lyrics

# Manual test: place vinyl, wait 10-30s
sleep 30
cat /dev/shm/hapax-compositor/album-state.json | jq '.current_track'
```

**PASS Criteria:**
- Vinyl audio extracted to right channel only
- Speed correction applied (2x before sending to Gemini)
- Track ID returned within 30s
- Lyrics appear in track-lyrics.txt

**FAIL Criteria:**
- Both channels sent (left + right = stereo, wrong)
- No track ID returned (timeout or API error)
- Lyrics file empty or stale

**WARN Criteria:**
- Track ID takes >30s (API latency)

**Remediation:**
```bash
# Check channel extraction:
ffmpeg -i pipe:0 -af "pan=mono|c0=c1" -f s16le - < /dev/shm/hapax-compositor/vinyl-captured.wav | \
  ffplay -f s16le -ar 44100 -ac 1 -  # listen to right channel only

# Test Gemini audio call manually:
python3 -c "from agents.album_identifier import identify_track; identify_track(audio_bytes)"

# Restart if needed:
systemctl --user restart album-identifier
```

---

**[C04] Lyrics Scrolling Overlay**

**What to Verify:** Lyrics appear in scrolling overlay and move at correct speed.

**How to Verify:**
```bash
# Check lyrics file existence and content
ls -lh /dev/shm/hapax-compositor/track-lyrics.txt
wc -l /dev/shm/hapax-compositor/track-lyrics.txt  # expect >10 lines

# Verify scrolling is configured
grep -n "scroll\|lyrics" agents/studio_compositor/overlay_zones.py

# Visual test: play track with known lyrics, observe output
# Lyrics should move from bottom to top at ~1 line/sec

# Check for render errors
journalctl --user -u studio-compositor | grep -i "lyrics\|overlay\|error" | tail -20
```

**PASS Criteria:**
- Lyrics file populated with text
- Scrolling configured in overlay_zones.py
- Lyrics visible on compositor output
- Scroll speed ~1 line/sec

**FAIL Criteria:**
- Lyrics file missing or empty
- Text not rendering (Cairo error)

**WARN Criteria:**
- Scroll speed inconsistent (frame drops)

**Remediation:**
```bash
# Manually populate lyrics if missing:
echo "Sample lyrics line 1
Sample lyrics line 2" > /dev/shm/hapax-compositor/track-lyrics.txt

# Check Cairo text rendering:
systemctl --user restart studio-compositor
```

---

**[C05] Splattribution Quality**

**What to Verify:** Splattribution hallucinations are confidently wrong (feature, not bug).

**How to Verify:**
```bash
# Check recent splattributions
cat /dev/shm/hapax-compositor/album-state.json | jq '.artist,.title,.year,.confidence'

# Verify confidence is high (>0.9 means the model is sure)
confidence=$(cat /dev/shm/hapax-compositor/album-state.json | jq '.confidence')
if (( $(echo "$confidence > 0.85" | bc -l) )); then
  echo "HIGH confidence hallucination (good!)"
else
  echo "LOW confidence (model uncertain)"
fi

# Spot-check: manually verify splattribution is WRONG
# If it matches the actual album, there's a problem
```

**PASS Criteria:**
- Splattribution has high confidence (>0.85)
- Is demonstrably wrong (doesn't match actual album)
- Artist/title/year all present and formatted

**FAIL Criteria:**
- Splattribution is correct (defeats the purpose)
- Confidence <0.5 (model uncertain)
- Missing fields

**WARN Criteria:**
- Splattribution only partially wrong (e.g., correct artist, wrong title)

**Remediation:**
```bash
# If splattributions are too accurate, add constraints to prompt:
# (Remove hints from prompt; let Gemini hallucinate freely)
# Already in code: no genre hints, no artist context

# If model too uncertain, try Gemini Pro instead of Flash:
# (Currently uses Pro for vision; check config)

# Check and adjust model selection:
grep -n "gemini-pro\|gemini-flash" scripts/album-identifier.py
```

---

### ENGAGEMENT SYSTEM CHECKS

**[E01] Token Ledger — File State & Concurrent Writers**

**What to Verify:** Token ledger JSON is valid, up-to-date, and handles concurrent writes.

**How to Verify:**
```bash
# Check file validity
cat /dev/shm/hapax-compositor/token-ledger.json | jq '.' && echo "Valid JSON" || echo "INVALID"

# Check file age
stat /dev/shm/hapax-compositor/token-ledger.json | grep Modify

# Verify required fields
jq '.total_tokens,.total_cost_usd,.pole_position,.active_viewers' /dev/shm/hapax-compositor/token-ledger.json

# Test concurrent write (simulate multiple writers)
python3 << 'EOF'
import json, os, threading, time
path = "/dev/shm/hapax-compositor/token-ledger.json"

def write_token(n):
  for _ in range(5):
    with open(path + ".tmp", "w") as f:
      data = json.load(open(path))
      data["total_tokens"] += 100
      json.dump(data, f)
    os.rename(path + ".tmp", path)
    time.sleep(0.01)

threads = [threading.Thread(target=write_token, args=(i,)) for i in range(3)]
for t in threads: t.start()
for t in threads: t.join()

# Verify final state is valid
with open(path) as f: json.load(f)
print("Concurrent write test PASSED")
EOF
```

**PASS Criteria:**
- Token-ledger.json is valid JSON
- File modified within last 10s
- All required fields present and non-zero
- Concurrent write test completes without corruption

**FAIL Criteria:**
- Invalid JSON (parse error)
- File stale >60s
- Missing fields
- Concurrent write causes corruption

**WARN Criteria:**
- File stale 10-60s (writers may be slow)

**Remediation:**
```bash
# Reset ledger to zero before stream start:
echo '{"session_start":'$(date +%s)',"total_tokens":0,"total_cost_usd":0.0,"components":{},"pole_position":0.0,"explosions":0,"active_viewers":1}' > /dev/shm/hapax-compositor/token-ledger.json

# Check if writers are wired:
grep -r "record_spend\|token_ledger" scripts/ agents/ | head -10
# Should see calls from album-identifier, chat-monitor
```

---

**[E02] Token Pole — Position Calculation & Explosions**

**What to Verify:** Token pole position advances smoothly and triggers explosions at threshold.

**How to Verify:**
```bash
# Check pole position over time
for i in {1..10}; do
  pole=$(jq '.pole_position' /dev/shm/hapax-compositor/token-ledger.json)
  explosions=$(jq '.explosions' /dev/shm/hapax-compositor/token-ledger.json)
  echo "Position: $pole, Explosions: $explosions"
  sleep 5
done

# Pole should increase gradually; explosions should only increment at milestones

# Manual test: increment tokens and verify position changes
python3 << 'EOF'
import json
path = "/dev/shm/hapax-compositor/token-ledger.json"
with open(path) as f: data = json.load(f)
initial_pos = data["pole_position"]

data["total_tokens"] += 5000  # large increment
with open(path + ".tmp", "w") as f: json.dump(data, f)
import os; os.rename(path + ".tmp", path)

import time; time.sleep(1)
with open(path) as f: data = json.load(f)
final_pos = data["pole_position"]
print(f"Position change: {initial_pos} -> {final_pos}")
EOF

# Visual verification: watch fx-snapshot.jpg for pole animation
watch -n 0.5 'convert /dev/shm/hapax-compositor/fx-snapshot.jpg -crop 300x300+20+20 /tmp/pole.jpg && echo "Pole rendered"'
```

**PASS Criteria:**
- Pole position increases smoothly (not jumpy)
- Explosion counter increments on 0→1 threshold crossings
- Pole animation renders correctly

**FAIL Criteria:**
- Position jumps discontinuously
- Explosion counter not incrementing
- Pole not rendering (missing image)

**WARN Criteria:**
- Position advancement very slow (chat inactive or token writers not wired)

**Remediation:**
```bash
# Verify token writers are wired to LLM calls:
grep -A 5 "Gemini.*call\|LLM.*call" scripts/album-identifier.py | grep -i "record_spend"
# Should find calls; if not, see P1 blocker §6.2

# Test pole rendering:
python3 -m agents.studio_compositor.token_pole TokenPole  # direct test if possible

# If pole frozen, restart compositor:
systemctl --user restart studio-compositor
```

---

**[E03] Vitruvian Spiral — Geometry & Clipping**

**What to Verify:** Vitruvian Man image renders without clipping and spiral path is correct.

**How to Verify:**
```bash
# Check asset file
ls -lh assets/vitruvian_man_overlay.png
file assets/vitruvian_man_overlay.png  # should be PNG
identify assets/vitruvian_man_overlay.png  # check dimensions (500x500 expected)

# Verify overlay position and size
grep -n "OVERLAY_X\|OVERLAY_Y\|OVERLAY_SIZE" agents/studio_compositor/token_pole.py
# Expect: X=20, Y=20, SIZE=300

# Test spiral math
python3 << 'EOF'
import math
# Golden spiral: r = a * e^(b*θ)
# Expected: MAX_TURNS = 3.0, NUM_POINTS = 250
for i in range(250):
  t = (i / 250) * 3.0 * 2 * math.pi  # 3 full rotations
  r = 50 * math.exp(0.3 * t)  # exponential growth
  x = r * math.cos(t)
  y = r * math.sin(t)
  # Should start small (center) and grow outward
print(f"Spiral spans {r:.0f} px")
EOF

# Visual check: screenshot and verify Vitruvian is visible and unclipped
convert /dev/shm/hapax-compositor/fx-snapshot.jpg -crop 300x300+20+20 /tmp/pole_crop.jpg
identify /tmp/pole_crop.jpg  # should be 300x300
```

**PASS Criteria:**
- vitruvian_man_overlay.png exists (500x500 PNG)
- Overlay positioned at (20, 20) with size 300x300
- Spiral math produces 250 points over 3 rotations
- Visual check: Vitruvian clearly visible without clipping

**FAIL Criteria:**
- Image file missing or wrong format
- Overlay clipped by canvas edges
- Spiral radius incorrect

**WARN Criteria:**
- Image resolution <500x500 (may pixelate)

**Remediation:**
```bash
# If image missing, regenerate:
python3 << 'EOF'
from PIL import Image, ImageOps, ImageDraw
# Load from Wikimedia Commons
# Apply contrast 2.0x, brightness 0.85x
# Colorize to sepia/gold
# Save to assets/vitruvian_man_overlay.png
EOF

# If overlay clipped, adjust canvas size in token_pole.py
# If spiral wrong, verify MAX_TURNS and exponential growth formula

systemctl --user restart studio-compositor
```

---

### CHAT MONITORING CHECKS

**[CH01] Chat Monitor Service — Installation & Runtime**

**What to Verify:** chat-monitor.service is installed and running (created but not enabled yet).

**How to Verify:**
```bash
# Check if service file exists
ls -la ~/.config/systemd/user/chat-monitor.service

# Check if daemon is running
systemctl --user is-active chat-monitor
systemctl --user is-enabled chat-monitor

# If not running, check why
systemctl --user status chat-monitor
journalctl --user -u chat-monitor --since "10 min ago"
```

**PASS Criteria:**
- Service file exists in `~/.config/systemd/user/`
- Daemon is running (or enabled + will start on boot)
- Status shows "active" or "inactive" (not "failed")

**FAIL Criteria:**
- Service file doesn't exist
- Service in failed state

**WARN Criteria:**
- Service inactive (expected before stream start; must be enabled at launch)

**Remediation:**
```bash
# Create service file if missing:
cat > ~/.config/systemd/user/chat-monitor.service << 'EOF'
[Unit]
Description=Legomena Live Chat Monitor
After=multi-user.target
Requires=logos-api.service

[Service]
Type=simple
ExecStart=/usr/bin/python3 /home/hapax/projects/hapax-council/scripts/chat-monitor.py
Restart=on-failure
RestartSec=5
Environment="PYTHONUNBUFFERED=1"

[Install]
WantedBy=default.target
EOF

systemctl --user daemon-reload
# Don't enable yet (need video ID)
```

---

**[CH02] Chat Monitor — YouTube Video ID**

**What to Verify:** Chat monitor knows the livestream video ID for chat-downloader.

**How to Verify:**
```bash
# Check if video ID is configured
cat /dev/shm/hapax-compositor/youtube-video-id.txt  # should contain 11-char ID
grep -n "YOUTUBE_VIDEO_ID\|youtube-video-id" scripts/chat-monitor.py

# Verify ID format
id=$(cat /dev/shm/hapax-compositor/youtube-video-id.txt)
if [[ $id =~ ^[a-zA-Z0-9_-]{11}$ ]]; then
  echo "Video ID format valid: $id"
else
  echo "Invalid video ID format: $id"
fi
```

**PASS Criteria:**
- `/dev/shm/hapax-compositor/youtube-video-id.txt` exists and contains valid 11-char YouTube video ID

**FAIL Criteria:**
- File missing or empty
- ID format invalid (not 11 chars, contains invalid chars)

**WARN Criteria:**
- File will be created manually at stream start (expected before launch)

**Remediation:**
```bash
# At stream start, grab video ID from YouTube Studio and write:
# (Studio Live → Video ID shown at top right)
echo "PASTE_VIDEO_ID_HERE" > /dev/shm/hapax-compositor/youtube-video-id.txt

# Then start chat-monitor:
systemctl --user start chat-monitor
```

---

**[CH03] Chat Monitor — Reconnect Logic**

**What to Verify:** chat-downloader reconnects on chat stream drop and Gemini API failures gracefully.

**How to Verify:**
```bash
# Start chat-monitor and simulate chat disconnect
systemctl --user start chat-monitor
systemctl --user status chat-monitor

# Monitor logs for reconnect attempts
journalctl --user -u chat-monitor --follow | grep -i "reconnect\|error\|attempt" &
LOG_PID=$!

# Simulate disconnect by stopping chat (if possible) or wait for natural drop
# Check logs for "reconnecting..." message

# Monitor Gemini API errors
journalctl --user -u chat-monitor | grep -i "gemini\|api.*error\|quota"

kill $LOG_PID
```

**PASS Criteria:**
- Reconnect attempts logged with backoff
- No infinite error loops (exponential backoff visible)
- Graceful failure on Gemini API errors (logs continue, doesn't crash)

**FAIL Criteria:**
- Infinite error loop (same error repeated rapidly)
- Process crashes on API error

**WARN Criteria:**
- Backoff period very short (may cause rate limiting)

**Remediation:**
```bash
# Verify reconnect logic in chat-monitor.py:
grep -n "reconnect\|backoff\|attempt" scripts/chat-monitor.py

# Check backoff parameters:
# Should be exponential: 2s, 4s, 8s, 16s, ... up to max 120s

# If too aggressive, adjust and restart:
systemctl --user restart chat-monitor
```

---

**[CH04] Embedding Cache — Freshness & Deduplication**

**What to Verify:** Thread detection embeddings are cached and recent messages are deduplicated.

**How to Verify:**
```bash
# Check seen_bigrams and embedding cache
journalctl --user -u chat-monitor --since "5 min ago" | \
  grep -E "embed|cache|deduplicate|seen_bigrams"

# Verify embedding window size (should be ~20 recent messages)
grep -n "EMBED_WINDOW\|embed_window" scripts/chat-monitor.py

# Monitor cache growth
ps aux | grep chat-monitor | grep -v grep  # check memory
# Memory should stay <500 MB over 1h
```

**PASS Criteria:**
- Embedding window bounded (expected ~20 recent)
- Deduplication log shows message filtering
- Memory growth <500 MB/hour

**FAIL Criteria:**
- Embedding cache unbounded (growing indefinitely)
- Massive memory growth (>100 MB/hour)

**WARN Criteria:**
- seen_bigrams set very large (>10K unique bigrams = likely bot spam)

**Remediation:**
```bash
# If cache growing, ensure pruning is implemented:
grep -n "clear\|reset\|prune" scripts/chat-monitor.py
# Should see periodic pruning (e.g., every 100 messages)

# Manually clear cache if needed:
python3 << 'EOF'
# Reload chat-monitor to clear in-memory caches
import subprocess
subprocess.run(["systemctl", "--user", "restart", "chat-monitor"])
EOF
```

---

### LOGGING & OBSERVABILITY CHECKS

**[L01] Obsidian Attribution Log — Append-Only State**

**What to Verify:** Attribution log file exists, grows monotonically, and has correct format.

**How to Verify:**
```bash
# Check file existence and size
ls -lh ~/Documents/Personal/30-areas/legomena-live/attribution-log.md
wc -l ~/Documents/Personal/30-areas/legomena-live/attribution-log.md

# Verify entries have correct format (title | channel | url)
tail -10 ~/Documents/Personal/30-areas/legomena-live/attribution-log.md

# Check for corruption (swapped fields from old code)
head -5 ~/Documents/Personal/30-areas/legomena-live/attribution-log.md | \
  grep -E "^\|.*\|.*\|" | head -1
# Should show: | Title | Channel | URL |

# Monitor for appends
stat ~/Documents/Personal/30-areas/legomena-live/attribution-log.md | grep Modify
# Should be recent
```

**PASS Criteria:**
- File exists and grows monotonically
- Lines follow `| Title | Channel | URL |` format
- No swapped/corrupted entries
- Recent modification timestamp

**FAIL Criteria:**
- File missing or empty
- Corrupted format
- Lines showing "SP Pictures" as title (old bug from §6.1)

**WARN Criteria:**
- File not modified in >10 min (may indicate no new videos)

**Remediation:**
```bash
# If corrupted, clean up first 3 lines (known bug):
sed -i '1,3d' ~/Documents/Personal/30-areas/legomena-live/attribution-log.md

# Or regenerate from scratch:
echo "# Legomena Live Attribution Log" > ~/Documents/Personal/30-areas/legomena-live/attribution-log.md
echo "" >> ~/Documents/Personal/30-areas/legomena-live/attribution-log.md
echo "| Title | Channel | URL |" >> ~/Documents/Personal/30-areas/legomena-live/attribution-log.md
echo "|-------|---------|-----|" >> ~/Documents/Personal/30-areas/legomena-live/attribution-log.md
```

---

**[L02] Reactor Log — Decision & Perception Logging**

**What to Verify:** Director loop reactor log exists and LLM decisions are recorded.

**How to Verify:**
```bash
# Check reactor log file
ls -lh ~/Documents/Personal/30-areas/legomena-live/reactor-log.md
wc -l ~/Documents/Personal/30-areas/legomena-live/reactor-log.md

# Check for recent entries
tail -20 ~/Documents/Personal/30-areas/legomena-live/reactor-log.md | head -10

# Verify entries include timestamp, video slot, LLM output
grep -E "^\[.*\]|^##|^> " ~/Documents/Personal/30-areas/legomena-live/reactor-log.md | head -5
```

**PASS Criteria:**
- File exists and contains recent entries
- Entries timestamped and include LLM decisions
- Format readable (markdown with headers)

**FAIL Criteria:**
- File missing or empty
- Entries very stale (>1h old if director loop is running)

**WARN Criteria:**
- Director loop disabled (reactor-log won't grow)

**Remediation:**
```bash
# Check if director loop is enabled:
grep -r "DirectorLoop\|director_loop" agents/ | grep -v ".pyc"

# If disabled, enable:
# (Check CLAUDE.md for enable instructions)

# If file missing, create empty:
touch ~/Documents/Personal/30-areas/legomena-live/reactor-log.md
```

---

**[L03] journalctl Log Volume**

**What to Verify:** Systemd journal is rotating and not filling the disk.

**How to Verify:**
```bash
# Check journal size
journalctl --disk-usage

# Verify rotation is configured
grep -E "MaxSize|MaxRetentionDays" /etc/systemd/journald.conf ~/.config/systemd/user/

# Check for excessive log volume
journalctl --since "1 hour ago" | wc -l  # should be <10K lines/hour

# Look for log spam
journalctl --since "10 min ago" | sort | uniq -c | sort -rn | head -20
# Any single message repeated >100 times = spam
```

**PASS Criteria:**
- Journal disk usage <1 GB total
- Rotation configured (MaxSize/MaxRetentionDays set)
- Log volume <10K lines/hour
- No single message repeated >100 times

**FAIL Criteria:**
- Journal >10 GB (disk filling)
- Rotation disabled
- Spam evident

**WARN Criteria:**
- Log volume 5-10K lines/hour (high but manageable)

**Remediation:**
```bash
# Force journal rotation:
sudo journalctl --vacuum-time=7d  # delete logs older than 7d
sudo journalctl --vacuum-size=500M  # keep total <500MB

# Enable persistent logging:
sudo mkdir -p /var/log/journal
sudo chown root:systemd-journal /var/log/journal
sudo chmod 2755 /var/log/journal
sudo systemctl restart systemd-journald

# Fix spam by reducing log level:
# Check which service is spamming:
journalctl -u <spammy-service> -p debug | wc -l
# Then restart at INFO level (not DEBUG)
```

---

**[L04] Screenshot Drops — gdrive Sync**

**What to Verify:** fx-snapshot.jpg is being synced to gdrive every 5s for remote review.

**How to Verify:**
```bash
# Check rclone-gdrive-drop timer
systemctl --user status rclone-gdrive-drop.timer
journalctl --user -u rclone-gdrive-drop.service --since "5 min ago" | head -20

# Verify gdrive folder has recent screenshots
ls -lh ~/gdrive-drop/legomena-screenshots/ | head -10
# Should show files within last 10 min

# Check sync timestamp
stat ~/gdrive-drop/legomena-screenshots/*.jpg | grep Modify | head -3 | sort -r
```

**PASS Criteria:**
- Timer active and running every 5s (or 30s depending on config)
- Recent screenshot files in gdrive-drop
- No sync errors in journalctl

**FAIL Criteria:**
- Timer disabled or failed
- No recent files in gdrive-drop
- Sync errors (permission denied, network error)

**WARN Criteria:**
- Sync interval changed from 5s to 30s (slower feedback)

**Remediation:**
```bash
# Verify timer configuration:
systemctl --user cat rclone-gdrive-drop.timer | grep OnBootSec

# If sync not working:
systemctl --user restart rclone-gdrive-drop.timer

# Manual sync test:
rclone copy /dev/shm/hapax-compositor/fx-snapshot.jpg gdrive-drop:legomena-screenshots/manual-test.jpg
```

---

## E. PRE-LAUNCH VS CONTINUOUS MONITORING

### Pre-Launch Checks (Run Once, T-4h to T-0h)

**Must PASS before stream starts:**

1. **[I01] Container Health** — all 13 running
2. **[I02] Systemd Dependencies** — boot sequence verified
3. **[I03] Secrets Available** — LiteLLM keys present
4. **[I04] Pi Fleet Reachable** — all 3 Pis respond
5. **[G01] CUDA Runtime** — cudacompositor loads (verify `gst-inspect-1.0`)
6. **[G03] USB Cameras** — all 6 enumerated
7. **[G04] v4l2loopback** — `/dev/video42` writable
8. **[G05] NVENC** — encoder available
9. **[V01] Pipeline State** — reaches PLAYING
10. **[V02] v4l2sink Caps** — no renegotiation cascade
11. **[A01] PipeWire Status** — mixer_master active
12. **[A02] Audio Thread** — pw-cat subprocess alive
13. **[C01] YouTube URL** — fresh, >5h remaining
14. **[C02] Album ID** — Pi-6 accessible, Gemini responding
15. **[E01] Token Ledger** — reset to zero, valid JSON
16. **[CH01] Chat Monitor** — service installed
17. **[CH02] Video ID** — will be set at stream start
18. **[L01] Attribution Log** — file ready
19. **OBS Configuration** — profile, scene, stream key set (§6.1.b)

**Burn-in phase (4-6h continuous before launch):**

Run all checks every 30 min, watch for:

- **Memory growth** — <100 MB/hour per daemon
- **GPU VRAM drift** — <200 MB/hour
- **Frame rate jitter** — fps_std <0.5
- **Service crashes** — zero unexpected restarts
- **API errors** — Gemini, YouTube, LiteLLM all responding
- **Disk space** — tmpfs not filling
- **Temperature** — GPU <80°C

---

### Continuous Monitoring (Every 15 min during stream)

**Health snapshot (automated loop):**

```bash
#!/bin/bash
while true; do
  echo "=== $(date) ==="
  
  # GPU health
  nvidia-smi --query-gpu=utilization.gpu,memory.used --format=csv,noheader | \
    sed 's/^/GPU: /'
  
  # Service status
  for svc in studio-compositor youtube-player album-identifier logos-api; do
    status=$(systemctl --user is-active $svc)
    echo "Service $svc: $status"
  done
  
  # Memory check
  pmap -x $(pgrep -f studio-compositor) 2>/dev/null | grep total | \
    sed 's/^/Compositor RSS: /'
  
  # Pole position
  jq '.pole_position, .explosions' /dev/shm/hapax-compositor/token-ledger.json | \
    paste -d, - - | sed 's/^/Pole: /'
  
  # Network (Pi fleet)
  for ip in 192.168.68.78 192.168.68.52 192.168.68.81; do
    curl -s -m 2 -o /dev/null -w "Pi $ip: %{http_code}\n" http://$ip:8090/frame.jpg || \
      echo "Pi $ip: DOWN"
  done
  
  echo ""
  sleep 900  # 15 min
done
```

**Event-triggered checks (on anomaly):**

- Service enters failed state → [I02] + [I03] + restart
- GPU memory spike >500 MB/min → [G02] + memory profile
- Frame rate drops <25 fps → [V03] + check GPU/CPU load
- Chat monitor slow → [CH03] + check network + API quotas
- Gemini API error → check LiteLLM logs + fallback handling
- Token ledger stale >5 min → [E01] + check writers (album-id, chat-monitor)
- Any OBS error → manual intervention (operator restart)

---

## F. AUTOMATED VS MANUAL CHECKS

### Fully Automated (Can be scripted/cronjob)

- **[I01]** Container health (docker ps, HTTP health endpoints)
- **[I02]** Systemd dependencies (systemctl cat)
- **[G01]** CUDA element loading (gst-inspect)
- **[G02]** GPU VRAM polling (nvidia-smi every 30s)
- **[G03]** USB camera enumeration (ls -la /dev/video*)
- **[G04]** v4l2loopback device check (v4l2-ctl)
- **[V03]** Framerate sampling (fx-snapshot.jpg timestamp deltas)
- **[A01]** PipeWire device status (pactl list)
- **[E01]** Token ledger JSON validity (jq parse)
- **[L03]** Journal rotation (journalctl --disk-usage)
- **Token ledger continuity** (jq queries on scheduled timer)
- **Service restart counts** (journalctl -u service -n 1 | grep "Restart")

### Requires Human Judgment

- **[G05]** NVENC encoder (only visible via OBS streaming test)
- **[V04]** Memory leak detection (interpret growth rate meaningfully)
- **[C05]** Splattribution quality (is wrong actually funny?)
- **[A03]** Audio reactivity timing (perceptual latency, not just sampling)
- **[C03]** Track ID accuracy (did Gemini correctly ID the vinyl?)
- **[E03]** Vitruvian spiral clipping (visual inspection needed)
- **[L02]** Reactor log quality (is reaction genuine?)
- **[A04]** Audio-video sync (lip-sync test requires viewing)
- **[CH03]** Reconnect behavior (need to simulate failure)
- **OBS configuration** (NVENC settings, audio mix levels)
- **Content safety scan** (inspect camera feeds for employer data)
- **Splattribution hallucination quality** (only humans judge funny-wrong)

### Hybrid (Automated flagging + human assessment)

- **[E02]** Pole advancement (automated: check position increasing; manual: evaluate engagement quality)
- **[L01]** Attribution log format (automated: check file growth; manual: verify entries correct)
- **[C02]** Album ID freshness (automated: check file age; manual: verify splattribution matches actual vinyl)
- **[CH02]** Video ID validity (automated: check file exists; manual: confirm correct video ID)

---

## SAMPLE PRE-LAUNCH CHECKLIST (Copy & Run)

```bash
#!/bin/bash
set -e

echo "=== PRE-LAUNCH LEGOMENA LIVE AUDIT ==="
echo "Start time: $(date)"
echo ""

PASS=0; FAIL=0; WARN=0

check_pass() { echo "✓ $1"; ((PASS++)); }
check_fail() { echo "✗ $1"; ((FAIL++)); }
check_warn() { echo "⚠ $1"; ((WARN++)); }

# [I01] Containers
echo "Checking containers..."
if docker ps --format "{{.Names}} {{.Status}}" | grep -q "Up"; then
  check_pass "Containers running"
else
  check_fail "Some containers down"
fi

# [I03] Secrets
echo "Checking secrets..."
if source /run/user/$(id -u)/hapax-secrets.env 2>/dev/null && [ -n "$LITELLM_API_KEY" ]; then
  check_pass "Secrets loaded"
else
  check_fail "Secrets missing"
fi

# [I04] Pi fleet
echo "Checking Pi fleet..."
pi_fail=0
for ip in 192.168.68.78 192.168.68.52 192.168.68.81; do
  if curl -s -m 2 http://$ip:8090/frame.jpg >/dev/null; then
    :
  else
    pi_fail=$((pi_fail + 1))
  fi
done
if [ $pi_fail -eq 0 ]; then
  check_pass "All 3 Pis reachable"
else
  check_fail "$pi_fail Pis unreachable"
fi

# [G01] CUDA
echo "Checking CUDA..."
if gst-inspect-1.0 cudacompositor >/dev/null 2>&1; then
  check_pass "CUDA elements load"
else
  check_fail "cudacompositor not found"
fi

# [G03] Cameras
echo "Checking cameras..."
cameras=$(ls /dev/video{0..9} 2>/dev/null | wc -l)
if [ $cameras -ge 6 ]; then
  check_pass "$cameras camera devices found"
else
  check_warn "Only $cameras cameras found (expect 6)"
fi

# [V01] Pipeline
echo "Checking pipeline..."
if systemctl --user is-active studio-compositor >/dev/null; then
  check_pass "Compositor running"
else
  check_fail "Compositor not running"
fi

# [A01] Audio
echo "Checking audio..."
if pactl list short sinks | grep -q mixer_master; then
  check_pass "mixer_master device exists"
else
  check_fail "mixer_master missing"
fi

# [E01] Token ledger
echo "Checking token ledger..."
if jq empty /dev/shm/hapax-compositor/token-ledger.json 2>/dev/null; then
  check_pass "Token ledger valid JSON"
  tokens=$(jq .total_tokens /dev/shm/hapax-compositor/token-ledger.json)
  if [ "$tokens" -eq 0 ]; then
    check_pass "Token ledger reset to zero"
  else
    check_warn "Token ledger has $tokens tokens (should be reset to 0)"
  fi
else
  check_fail "Token ledger invalid JSON"
fi

# Summary
echo ""
echo "=== SUMMARY ==="
echo "PASS: $PASS, FAIL: $FAIL, WARN: $WARN"
if [ $FAIL -gt 0 ]; then
  echo "LAUNCH BLOCKED - Fix failures before starting stream"
  exit 1
else
  echo "READY FOR LAUNCH"
  exit 0
fi
```

---

## APPENDIX: Known Gotchas & Workarounds

### If CUDA disappears mid-stream:
1. CPU fallback should kick in (implemented in pipeline.py)
2. Output quality drops but stream continues
3. Not a blocker

### If Pi-6 IP changes (DHCP):
1. Album detection fails silently
2. Splattribution freezes at last good value
3. Run `nmap -p 22,8090 --open 192.168.68.0/24` to find new IP
4. Update env var in album-identifier.service

### If token-ledger.json corrupted:
1. Pole shows stale position
2. Reset file: `echo '...' > /dev/shm/hapax-compositor/token-ledger.json`
3. Restart compositor to reload

### If OBS loses connection:
1. **STREAM STOPS**
2. Operator must manually restart OBS
3. No automated recovery

### If chat-monitor crashes:
1. Pole stops advancing (no token spend from chat)
2. Manual restart: `systemctl --user restart chat-monitor`
3. No automatic recovery configured

---

This audit plan is the **design document** for execution by the operator or a monitoring system. Each check is specific, actionable, and tied to remediation steps. Use it as a runbook for the 36-hour stream.
