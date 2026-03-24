"""Voice panel — voice daemon state detail for the seam layer."""

from __future__ import annotations

from typing import TYPE_CHECKING

from gi.repository import Gtk

if TYPE_CHECKING:
    from hapax_bar.stimmung import StimmungState

_STATE_COLORS = {
    "off": "#665c54",
    "idle": "#665c54",
    "listening": "#fabd2f",
    "transcribing": "#83a598",
    "thinking": "#83a598",
    "processing": "#83a598",
    "speaking": "#b8bb26",
}


class VoicePanel(Gtk.Box):
    """Shows voice state with severity coloring. Hides when off."""

    def __init__(self) -> None:
        super().__init__(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=2,
            css_classes=["voice-panel"],
        )
        self._label = Gtk.Label(xalign=0, css_classes=["metrics-row"], use_markup=True)
        self.append(self._label)
        self.set_visible(False)

    def update(self, state: StimmungState) -> None:
        if state.voice_state == "off" and not state.voice_active:
            self.set_visible(False)
            return

        self.set_visible(True)
        sc = _STATE_COLORS.get(state.voice_state, "#665c54")
        hr = state.heart_rate
        hr_str = f"  HR: {hr}bpm" if hr > 0 else ""
        self._label.set_markup(f'Voice: <span foreground="{sc}">{state.voice_state}</span>{hr_str}')
