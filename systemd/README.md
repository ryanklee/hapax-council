# systemd Service Management

All production services run as systemd user units under `user@1000.service` with lingering enabled. No process supervisors (process-compose, supervisord) in the boot chain.

## Directory Structure

```
systemd/
├── units/              Service and timer unit files (source of truth)
├── overrides/          Drop-in .conf files for dependency ordering and resource limits
│   ├── dev/            Timer frequency overrides for dev cycle mode
│   └── *.service.d/    Per-service drop-ins
├── scripts/            install-units.sh, backup.sh, camera-setup.sh
└── watchdogs/          Health check scripts
```

## Architecture

Three tiers, two managers:

```
Docker Compose (infrastructure)     systemd user units (application + utilities)
─────────────────────────────────   ─────────────────────────────────────────────
qdrant, postgres, redis,            hapax-secrets     → all credentials (oneshot)
litellm, langfuse, grafana,         logos-api         → FastAPI :8051
prometheus, clickhouse,             hapax-voice       → voice daemon (GPU)
n8n, open-webui, minio, ntfy       visual-layer-agg  → perception pipeline
                                    studio-compositor → camera tiling (GPU)
Managed by:                         studio-fx-output  → ffmpeg /dev/video50
  llm-stack.service (oneshot)       audio-recorder    → pw-record → FLAC
  llm-stack-analytics.service       hapax-watch-recv  → Wear OS biometrics
                                    rag-ingest        → document ingestion
                                    41 timers         → sync, health, backups
```

## Boot Sequence

```
1. hapax-secrets.service     Load credentials from pass store → /run/user/1000/hapax-secrets.env
2. llm-stack.service         docker compose --profile full up -d (waits 30s for Docker daemon)
3. llm-stack-analytics       docker compose --profile analytics up -d (60s after llm-stack)
4. logos-api.service         After: llm-stack, hapax-secrets
5. officium-api.service      After: llm-stack, hapax-secrets
6. hapax-voice.service       After: pipewire, hapax-secrets (+10s delay for GPU sequencing)
7. visual-layer-aggregator   After: logos-api, hapax-voice, hapax-secrets
8. studio-compositor         After: hapax-voice, visual-layer-aggregator (+10s for USB cameras)
9. studio-fx-output          After: studio-compositor
10. Timers activate          vram-watchdog (30s), health-monitor (15m), sync agents, backups
```

## Secrets

Single centralized service (`hapax-secrets.service`) loads all credentials once at boot:

- `LITELLM_API_KEY`, `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY` — API access
- `HF_TOKEN` — HuggingFace model downloads
- `LITELLM_BASE_URL`, `LANGFUSE_HOST` — service endpoints

Written to `/run/user/1000/hapax-secrets.env` (tmpfs, 0600). All services declare `Requires=hapax-secrets.service` and read via `EnvironmentFile=/run/user/1000/hapax-secrets.env`.

## Resource Isolation

| Service | MemoryMax | OOMScoreAdjust | Nice | CPUWeight |
|---------|-----------|----------------|------|-----------|
| hapax-voice | 8G | -500 | -10 | default |
| studio-compositor | 4G | default | default | 500 |
| rag-ingest | 4G | default | 10 | 25 |
| visual-layer-aggregator | 1G | default | default | default |
| logos-api | 1G | default | default | default |
| officium-api | 512M | default | default | default |
| studio-fx-output | 512M | default | 10 | default |
| hapax-watch-receiver | 256M | default | default | default |

System-level OOM overrides: earlyoom (-1000), docker (-900), pipewire/wireplumber (-900), ollama (-500).

## Installation

```bash
# Install/update all units from this directory
systemd/scripts/install-units.sh

# Or manually link a single unit
systemctl --user link "$PWD/systemd/units/my-service.service"
systemctl --user enable my-service.service
systemctl --user daemon-reload
```

## Development

For development, stop systemd services and use process-compose:

```bash
systemctl --user stop logos-api hapax-voice visual-layer-aggregator studio-compositor
process-compose up           # TUI mode
process-compose attach       # attach to running instance
```

See `process-compose.yaml` (development only, not in boot chain).

## Recovery

The system is configured for 24/7 unattended operation:

- **Kernel panic** → auto-reboot in 10s (`kernel.panic=10`, `softlockup_panic=1`, `hung_task_panic=1`)
- **systemd hang** → hardware watchdog reset in 30s (SP5100 TCO, `RuntimeWatchdogSec=30`)
- **Shutdown hang** → hardware watchdog reset in 10min (`RebootWatchdogSec=10min`)
- **Display manager** → greetd autologin (no password prompt)
- **User services** → lingering enabled, all services start at boot without login
- **Docker containers** → `restart: always` on all 13 containers
- **Service crash** → `Restart=always` or `Restart=on-failure` with rate limiting
- **Journal persistence** → `SyncIntervalSec=15s`, `ForwardToKMsg=yes`, pstore for crash dumps
