"""Moksha palette + authentic-daywork chain registration pins.

Phase 1 of ``ytb-AUTH-PALETTE`` (Moksha portion). The two Moksha
palettes (``moksha-dark-chrome``, ``moksha-light-paper``) are authored
in-YAML as aesthetic approximations of the E17/Moksha default theme.
Phase 2 (``shared.aesthetic_library_loader``) will replace these
approximations with values extracted from the authentic Moksha .edc
theme file when Moksha assets are acquired.

The ``authentic-daywork`` chain bridges ``mirc-16-standard`` (BitchX
lineage, from AUTH-PALETTE-MIRC #1289) with ``moksha-light-paper`` for
research-mode palette oscillation between terminal precision and UI
readability.

Spec: cc-task ``ytb-AUTH-PALETTE-scrim-extension``.
"""

from __future__ import annotations

from shared.palette_registry import PaletteRegistry


class TestMokshaPalettesRegistered:
    """Both Moksha palettes must load into the default registry."""

    def test_moksha_dark_chrome_present(self) -> None:
        reg = PaletteRegistry.load()
        assert "moksha-dark-chrome" in reg.palette_ids()

    def test_moksha_light_paper_present(self) -> None:
        reg = PaletteRegistry.load()
        assert "moksha-light-paper" in reg.palette_ids()


class TestMokshaDarkChrome:
    """Dark-chrome palette shape pins."""

    def test_display_name(self) -> None:
        reg = PaletteRegistry.load()
        pal = reg.get_palette("moksha-dark-chrome")
        assert pal.display_name == "Moksha Dark Chrome"

    def test_tags_include_moksha_and_enlightenment(self) -> None:
        reg = PaletteRegistry.load()
        pal = reg.get_palette("moksha-dark-chrome")
        assert "moksha" in pal.semantic_tags
        assert "enlightenment" in pal.semantic_tags
        assert "dark" in pal.semantic_tags

    def test_dominant_is_mid_lightness(self) -> None:
        """E-panel chrome skeleton sits mid-L (steel-grey), not at the extremes."""
        reg = PaletteRegistry.load()
        pal = reg.get_palette("moksha-dark-chrome")
        # Moksha dark chrome: mid L*, low-chroma.
        assert 30.0 <= pal.dominant_lab[0] <= 60.0


class TestMokshaLightPaper:
    """Light-paper palette shape pins."""

    def test_display_name(self) -> None:
        reg = PaletteRegistry.load()
        pal = reg.get_palette("moksha-light-paper")
        assert pal.display_name == "Moksha Light Paper"

    def test_tags_include_paper_and_warm(self) -> None:
        reg = PaletteRegistry.load()
        pal = reg.get_palette("moksha-light-paper")
        assert "moksha" in pal.semantic_tags
        assert "paper" in pal.semantic_tags
        assert "warm" in pal.semantic_tags

    def test_dominant_is_high_lightness(self) -> None:
        """Light-paper: warm off-white, high L*."""
        reg = PaletteRegistry.load()
        pal = reg.get_palette("moksha-light-paper")
        assert pal.dominant_lab[0] >= 75.0

    def test_research_affinity(self) -> None:
        reg = PaletteRegistry.load()
        pal = reg.get_palette("moksha-light-paper")
        assert "research" in pal.working_mode_affinity


class TestAuthenticDayworkChain:
    """The chain bridging mIRC and Moksha for research-mode oscillation."""

    def test_chain_registered(self) -> None:
        reg = PaletteRegistry.load()
        chain = reg.find_chain("authentic-daywork")
        assert chain is not None

    def test_chain_loops(self) -> None:
        reg = PaletteRegistry.load()
        chain = reg.get_chain("authentic-daywork")
        assert chain.loop is True

    def test_chain_bridges_mirc_and_moksha_paper(self) -> None:
        reg = PaletteRegistry.load()
        chain = reg.get_chain("authentic-daywork")
        palette_ids = [step.palette_id for step in chain.steps]
        assert "mirc-16-standard" in palette_ids
        assert "moksha-light-paper" in palette_ids

    def test_chain_has_two_steps(self) -> None:
        reg = PaletteRegistry.load()
        chain = reg.get_chain("authentic-daywork")
        assert len(chain.steps) == 2

    def test_chain_uses_crossfade(self) -> None:
        reg = PaletteRegistry.load()
        chain = reg.get_chain("authentic-daywork")
        for step in chain.steps:
            assert step.transition_mode == "crossfade"

    def test_chain_dwell_times_reasonable(self) -> None:
        """Research-mode oscillation: 30-120s dwell per step."""
        reg = PaletteRegistry.load()
        chain = reg.get_chain("authentic-daywork")
        for step in chain.steps:
            assert 30.0 <= step.dwell_s <= 120.0
