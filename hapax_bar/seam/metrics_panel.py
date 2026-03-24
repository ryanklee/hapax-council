"""Metrics panel — health, GPU, CPU, memory, disk for the seam layer."""

from __future__ import annotations

import os
from typing import Any

from gi.repository import Gtk


def _read_cpu_mem() -> tuple[str, str]:
    """Read CPU and memory from /proc."""
    cpu_str = "?"
    mem_str = "?"
    try:
        with open("/proc/meminfo") as f:
            info = {}
            for line in f:
                parts = line.split()
                if len(parts) >= 2:
                    info[parts[0].rstrip(":")] = int(parts[1])
            total = info.get("MemTotal", 1)
            avail = info.get("MemAvailable", 0)
            used_gb = (total - avail) / (1024 * 1024)
            total_gb = total / (1024 * 1024)
            pct = int(100 * (total - avail) / total)
            mem_str = f"{used_gb:.1f}G/{total_gb:.0f}G ({pct}%)"
    except Exception:
        pass
    try:
        with open("/proc/loadavg") as f:
            load1 = f.read().split()[0]
            cpu_str = f"load {load1}"
    except Exception:
        pass
    return cpu_str, mem_str


def _read_disk() -> str:
    try:
        st = os.statvfs("/")
        total = st.f_blocks * st.f_frsize
        used = (st.f_blocks - st.f_bfree) * st.f_frsize
        pct = int(100 * used / total) if total > 0 else 0
        return f"{used // (1024**3)}G/{total // (1024**3)}G ({pct}%)"
    except Exception:
        return "?"


class MetricsPanel(Gtk.Box):
    """Compact grid of system metrics."""

    def __init__(self) -> None:
        super().__init__(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=2,
            css_classes=["metrics-panel"],
        )
        self._row1 = Gtk.Label(xalign=0, css_classes=["metrics-row"])
        self._row2 = Gtk.Label(xalign=0, css_classes=["metrics-row"])
        self.append(self._row1)
        self.append(self._row2)

    def update(self, health: dict[str, Any], gpu: dict[str, Any]) -> None:
        # Health
        healthy = health.get("healthy", 0)
        total = health.get("total_checks", 0)
        status = health.get("overall_status", health.get("status", "?"))
        failed = health.get("failed_checks", [])
        failed_str = f"  [{', '.join(failed[:3])}]" if failed else ""

        # GPU — match actual API field names
        temp = gpu.get("temperature_c", gpu.get("temp", "?"))
        used_mb = gpu.get("used_mb", gpu.get("memory_used_mib", 0))
        total_mb = gpu.get("total_mb", gpu.get("memory_total_mib", 24576))
        usage = gpu.get("usage_pct", gpu.get("utilization", "?"))
        used_gb = used_mb / 1024 if isinstance(used_mb, (int, float)) else 0
        total_gb = total_mb / 1024 if isinstance(total_mb, (int, float)) else 24
        models = gpu.get("loaded_models", [])
        model_str = f"  [{', '.join(models[:2])}]" if models else ""

        self._row1.set_label(
            f"Health: {healthy}/{total} {status}{failed_str}    "
            f"GPU: {temp}\u00b0C  {used_gb:.1f}G/{total_gb:.0f}G  {usage}%{model_str}"
        )

        # CPU, memory, disk
        cpu_str, mem_str = _read_cpu_mem()
        disk_str = _read_disk()
        self._row2.set_label(f"CPU: {cpu_str}    Mem: {mem_str}    Disk: {disk_str}")
