---
name: cpu-audit
description: "Full CPU and process survey: load, per-core usage, top consumers, systemd services, Docker containers, and scheduled work. Auto-run when: system feels sluggish, CPU >80% in session-context, or user asks about CPU/process usage. Invoke proactively without asking."
---

Comprehensive CPU and process breakdown.

```bash
lscpu | grep -E 'Model name|CPU\(s\)|Thread|Core|MHz|cache'
```

```bash
cat /proc/loadavg && echo "---" && uptime
```

```bash
ps aux --sort=-%cpu | head -25
```

```bash
systemctl --user list-units --type=service --state=running --no-pager 2>/dev/null
```

```bash
systemctl list-units --type=service --state=running --no-pager 2>/dev/null | head -30
```

```bash
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.PIDs}}" 2>/dev/null
```

```bash
systemctl --user list-timers --no-pager 2>/dev/null | head -30
```

```bash
ps -eo pid,ppid,user,%cpu,%mem,etime,comm --sort=-%cpu | awk '$4 > 1.0' | head -20
```

Present a ranked breakdown of CPU consumers. Group by category (Docker, systemd user services, systemd system services, other). Identify anything unexpected or wasteful. If load average exceeds core count, diagnose the bottleneck.
