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
        self._label = Gtk.Label(css_classes=["activity-text"], use_markup=True)
        self.append(self._label)
        self.set_visible(False)

    def update(self, activity_mode: str) -> None:
        if not activity_mode or activity_mode == "idle":
            self.set_visible(False)
            return
        self.set_visible(True)
        mode_colors = {
            "coding": "#83a598",  # blue — digital work
            "creative": "#fe8019",  # orange — production
            "reading": "#b8bb26",  # green — learning
            "admin": "#fabd2f",  # yellow — tasks
        }
        c = mode_colors.get(activity_mode, "#665c54")
        self._label.set_markup(
            f'<span foreground="#665c54">\u00b7</span> <span foreground="{c}">{activity_mode}</span>'
        )
