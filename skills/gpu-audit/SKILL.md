---
name: gpu-audit
description: "Full GPU survey: VRAM allocation, process-level usage, compute utilization, thermals, power, and model inventory. Auto-run when: OOM errors appear, before loading new models, GPU >80% in session-context, or user asks about GPU usage. Invoke proactively without asking."
---

Comprehensive GPU breakdown.

```bash
nvidia-smi
```

```bash
nvidia-smi --query-gpu=name,driver_version,power.draw,power.limit,temperature.gpu,temperature.memory,fan.speed,clocks.gr,clocks.mem,utilization.gpu,utilization.memory,memory.used,memory.total,memory.free --format=csv,noheader
```

```bash
nvidia-smi --query-compute-apps=pid,name,used_gpu_memory --format=csv,noheader 2>/dev/null
```

```bash
curl -s http://localhost:11434/api/ps 2>/dev/null || echo "Ollama not running or no models loaded"
```

```bash
curl -s http://localhost:5000/v1/model 2>/dev/null || echo "TabbyAPI not running"
```

```bash
systemctl --user status hapax-voice studio-compositor visual-layer-aggregator 2>/dev/null | grep -E '(●|Active|Memory|CPU)'
```

```bash
cat /sys/class/drm/card*/device/pp_dpm_sclk 2>/dev/null; echo "---"; cat /proc/driver/nvidia/gpus/*/power 2>/dev/null | head -10
```

Present a ranked breakdown of VRAM consumers by process. Show compute vs memory utilization split. Compare current thermals/power to limits. Identify capacity for additional workloads (how many more models, what sizes). Flag anything thermally throttled or power-limited.
