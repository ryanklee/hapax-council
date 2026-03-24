"""CSS theme loading and runtime mode switching.

Loads two CSS files: base (layout/animation) + mode (color tokens).
"""

from __future__ import annotations

from pathlib import Path

from gi.repository import Gdk, Gtk

STYLES_DIR = Path(__file__).parent / "styles"
WORKING_MODE_FILE = Path.home() / ".cache" / "hapax" / "working-mode"
BASE_CSS = STYLES_DIR / "hapax-bar-base.css"

_base_provider: Gtk.CssProvider | None = None
_mode_provider: Gtk.CssProvider | None = None


def _read_working_mode() -> str:
    try:
        return WORKING_MODE_FILE.read_text().strip()
    except FileNotFoundError:
        return "rnd"


def _css_path(mode: str) -> Path:
    return STYLES_DIR / f"hapax-bar-{mode}.css"


def load_initial_theme() -> None:
    """Load base CSS + mode CSS. Call once at startup."""
    global _base_provider

    display = Gdk.Display.get_default()
    if display is None:
        return

    # Load base CSS (layout, sizing, animation — never changes)
    if BASE_CSS.exists():
        _base_provider = Gtk.CssProvider()
        _base_provider.load_from_path(str(BASE_CSS))
        Gtk.StyleContext.add_provider_for_display(
            display, _base_provider, Gtk.STYLE_PROVIDER_PRIORITY_USER
        )

    # Load mode CSS (color tokens)
    mode = _read_working_mode()
    switch_theme(mode)


def switch_theme(mode: str) -> None:
    """Hot-swap the color theme. Base CSS stays loaded."""
    global _mode_provider

    css_file = _css_path(mode)
    if not css_file.exists():
        css_file = _css_path("rnd")

    display = Gdk.Display.get_default()
    if display is None:
        return

    if _mode_provider is not None:
        Gtk.StyleContext.remove_provider_for_display(display, _mode_provider)

    _mode_provider = Gtk.CssProvider()
    _mode_provider.load_from_path(str(css_file))
    Gtk.StyleContext.add_provider_for_display(
        display, _mode_provider, Gtk.STYLE_PROVIDER_PRIORITY_USER
    )


def current_mode() -> str:
    return _read_working_mode()
