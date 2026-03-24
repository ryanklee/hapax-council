"""Activity label — shows system's inference of what operator is doing."""

from __future__ import annotations

from gi.repository import Gtk


class ActivityLabel(Gtk.Box):
    """Shows '· coding' next to window title. Hidden when idle."""

    def __init__(self) -> None:
        super().__init__(
            orientation=Gtk.Orientation.HORIZONTAL,
            css_classes=["module", "activity-label"],
        )
        self._label = Gtk.Label(css_classes=["activity-text"])
        self.append(self._label)
        self.set_visible(False)

    def update(self, activity_mode: str) -> None:
        if not activity_mode or activity_mode == "idle":
            self.set_visible(False)
            return
        self.set_visible(True)
        self._label.set_label(f"\u00b7 {activity_mode}")
