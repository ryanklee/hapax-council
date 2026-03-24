"""Nudge badge — colored dot + count showing pending action items."""

from __future__ import annotations

from gi.repository import Gtk


class NudgeBadge(Gtk.Box):
    """Shows ●N when nudges are pending. Hidden when 0."""

    def __init__(self) -> None:
        super().__init__(
            orientation=Gtk.Orientation.HORIZONTAL,
            css_classes=["module", "nudge-badge"],
        )
        self._label = Gtk.Label()
        self.append(self._label)
        self.set_visible(False)

    def update(self, count: int) -> None:
        if count == 0:
            self.set_visible(False)
            return

        self.set_visible(True)
        self._label.set_label(f"\u25cf{count}")

        classes = ["module", "nudge-badge"]
        if count >= 11:
            classes.append("critical")
        elif count >= 6:
            classes.append("warning")
        else:
            classes.append("low")
        self.set_css_classes(classes)
