"""Always-visible system indicators: network, CPU, GPU — with severity colors."""

from __future__ import annotations

import subprocess

from gi.repository import GLib, Gtk

from hapax_bar.logos_client import _fetch_json

# Severity colors from §3.7
_GREEN = "#b8bb26"
_YELLOW = "#fabd2f"
_ORANGE = "#fe8019"
_RED = "#fb4934"
_DIM = "#665c54"
_BLUE = "#83a598"


class NetworkIndicator(Gtk.Label):
    """Shows wifi SSID or eth status with connection color."""

    def __init__(self) -> None:
        super().__init__(css_classes=["module", "sysind"], use_markup=True)
        self._update()
        GLib.timeout_add(10_000, self._update)

    def _update(self) -> bool:
        try:
            result = subprocess.run(
                ["nmcli", "-t", "-f", "TYPE,STATE,CONNECTION", "device"],
                capture_output=True,
                text=True,
                timeout=2,
            )
            for line in result.stdout.strip().split("\n"):
                parts = line.split(":")
                if len(parts) >= 3 and parts[1] == "connected":
                    name = parts[2][:10]
                    if parts[0] == "wifi":
                        self.set_markup(f'<span foreground="{_BLUE}">W:</span>{name}')
                        return GLib.SOURCE_CONTINUE
                    elif parts[0] == "ethernet":
                        self.set_markup(f'<span foreground="{_GREEN}">E:</span>up')
                        return GLib.SOURCE_CONTINUE
            self.set_markup(f'<span foreground="{_RED}">net:--</span>')
        except Exception:
            self.set_markup(f'<span foreground="{_DIM}">net:?</span>')
        return GLib.SOURCE_CONTINUE


class CpuIndicator(Gtk.Label):
    """Shows CPU load average with severity color."""

    def __init__(self) -> None:
        super().__init__(css_classes=["module", "sysind"], use_markup=True)
        self._update()
        GLib.timeout_add(5_000, self._update)

    def _update(self) -> bool:
        try:
            with open("/proc/loadavg") as f:
                load1 = float(f.read().split()[0])
            if load1 >= 12:
                c = _RED
            elif load1 >= 8:
                c = _ORANGE
            elif load1 >= 4:
                c = _YELLOW
            else:
                c = _DIM
            self.set_markup(
                f'<span foreground="{_DIM}">C:</span><span foreground="{c}">{load1:.1f}</span>'
            )
        except Exception:
            self.set_markup(f'<span foreground="{_DIM}">C:?</span>')
        return GLib.SOURCE_CONTINUE


class GpuIndicator(Gtk.Label):
    """Shows GPU temp and VRAM with severity colors."""

    def __init__(self) -> None:
        super().__init__(css_classes=["module", "sysind"], use_markup=True)
        self._update()
        GLib.timeout_add(30_000, self._update)

    def _update(self) -> bool:
        data = _fetch_json("/api/gpu") or {}
        temp = data.get("temperature_c", 0)
        used = data.get("used_mb", 0)
        total = data.get("total_mb", 24576)
        used_g = used / 1024 if isinstance(used, (int, float)) else 0

        # Temp color
        t = float(temp) if isinstance(temp, (int, float)) else 0
        tc = _RED if t >= 85 else _ORANGE if t >= 75 else _YELLOW if t >= 65 else _DIM

        # VRAM color
        pct = (used / total * 100) if total > 0 else 0
        vc = _RED if pct >= 90 else _ORANGE if pct >= 75 else _YELLOW if pct >= 60 else _DIM

        self.set_markup(
            f'<span foreground="{_DIM}">G:</span>'
            f'<span foreground="{tc}">{int(t)}°</span> '
            f'<span foreground="{vc}">{used_g:.0f}G</span>'
        )
        return GLib.SOURCE_CONTINUE
