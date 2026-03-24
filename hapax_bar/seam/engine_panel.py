"""Engine panel — reactive engine metrics for the seam layer."""

from __future__ import annotations

from gi.repository import Gtk

from hapax_bar.logos_client import _fetch_json


class EnginePanel(Gtk.Box):
    """Shows reactive engine uptime, events, actions, errors."""

    def __init__(self) -> None:
        super().__init__(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=2,
            css_classes=["engine-panel"],
        )
        self._label = Gtk.Label(xalign=0, css_classes=["metrics-row"], use_markup=True)
        self.append(self._label)

    def refresh(self) -> None:
        data = _fetch_json("/api/engine/status") or {}
        uptime = data.get("uptime_s", 0)
        hours = int(uptime / 3600)
        mins = int((uptime % 3600) / 60)
        events = data.get("events_processed", 0)
        actions = data.get("actions_executed", 0)
        errors = data.get("errors", 0)
        rules = data.get("rules_evaluated", 0)

        err_color = "#fb4934" if errors > 0 else "#665c54"
        err_str = f'<span foreground="{err_color}">{errors}</span>'

        self._label.set_markup(
            f"Engine: {hours}h{mins:02d}m up  "
            f"events:{events}  actions:{actions}  errors:{err_str}  "
            f"rules:{rules}"
        )
