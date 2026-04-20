"""Tests for preset_family_selector — Phase 3 of the volitional-director epic."""

from __future__ import annotations

import pytest

from agents.studio_compositor import preset_family_selector as pfs


@pytest.fixture(autouse=True)
def _reset_memory():
    pfs.reset_memory()
    yield
    pfs.reset_memory()


class TestFamilyMapping:
    def test_all_documented_families_present(self):
        # The four documented families plus neutral-ambient fallback.
        names = pfs.family_names()
        assert "audio-reactive" in names
        assert "calm-textural" in names
        assert "glitch-dense" in names
        assert "warm-minimal" in names
        assert "neutral-ambient" in names

    def test_each_family_has_presets(self):
        for fam in pfs.family_names():
            presets = pfs.presets_for_family(fam)
            assert presets, f"family {fam} has no presets"
            assert all(isinstance(p, str) and p for p in presets)

    def test_unknown_family_returns_empty(self):
        assert pfs.presets_for_family("does-not-exist") == ()


class TestPickFromFamily:
    def test_returns_member_of_family(self):
        pick = pfs.pick_from_family("calm-textural")
        assert pick in pfs.presets_for_family("calm-textural")

    def test_avoids_back_to_back_repeat(self):
        # Pick twice — second pick should differ from first when the
        # family has > 1 preset.
        first = pfs.pick_from_family("glitch-dense")
        second = pfs.pick_from_family("glitch-dense")
        assert first != second, (
            "back-to-back repeat in family with multiple presets — non-repeat memory not applied"
        )

    def test_avoids_explicit_last(self):
        family_presets = pfs.presets_for_family("audio-reactive")
        # Pin "last" to first preset; pick should not return that one.
        pick = pfs.pick_from_family("audio-reactive", last=family_presets[0])
        assert pick != family_presets[0]

    def test_filters_against_available(self):
        family_presets = pfs.presets_for_family("warm-minimal")
        # Make only one family member available; selector must return that one.
        only = family_presets[0]
        pick = pfs.pick_from_family("warm-minimal", available=[only])
        assert pick == only

    def test_returns_none_when_unknown_family(self):
        assert pfs.pick_from_family("not-a-real-family") is None

    def test_returns_none_when_no_family_member_available(self):
        # All family members filtered out → None.
        result = pfs.pick_from_family("calm-textural", available=["completely-unrelated-preset"])
        assert result is None

    def test_falls_back_when_only_one_candidate_after_non_repeat(self):
        family_presets = pfs.presets_for_family("neutral-ambient")
        only = family_presets[0]
        # Force a single available candidate; non-repeat should be relaxed.
        pick = pfs.pick_from_family("neutral-ambient", available=[only], last=only)
        assert pick == only  # only candidate, returned despite being "last"


class TestMemoryReset:
    def test_reset_clears_per_family_memory(self):
        pfs.pick_from_family("glitch-dense")
        pfs.reset_memory()
        # After reset, the next pick has no last-pick anchor.
        # Just verify the memory dict is empty by checking the module attr.
        assert pfs._LAST_PICK == {}


# ── preset-variety Phase 2 — director-prompt ↔ catalog parity ─────────


class TestFamilyAliases:
    """Closes the gap where director_loop offers `audio-abstract` to the
    LLM but the catalog only knew `neutral-ambient` — pre-fix, an
    audio-abstract pick returned an empty preset list and recruitment
    fell through to the random_mode neutral-ambient fallback (silent
    monoculture amplifier per task #166 research §1).
    """

    def test_audio_abstract_alias_resolves_to_neutral_ambient(self):
        """presets_for_family must return non-empty for the alias name."""
        canonical = pfs.presets_for_family("neutral-ambient")
        aliased = pfs.presets_for_family("audio-abstract")
        assert canonical, "neutral-ambient catalog gone — fallback broken"
        assert aliased == canonical

    def test_pick_from_family_resolves_alias(self):
        """pick_from_family with the alias name must return a real preset."""
        pick = pfs.pick_from_family("audio-abstract")
        assert pick is not None
        # The returned preset must be a member of the canonical family.
        assert pick in pfs.presets_for_family("neutral-ambient")

    def test_alias_does_not_pollute_family_names(self):
        """family_names() must still return canonical families only —
        aliases are query-time conveniences, not first-class entries."""
        names = pfs.family_names()
        assert "audio-abstract" not in names

    def test_family_for_preset_returns_canonical_name(self):
        """family_for_preset reverse-lookup must return the canonical
        family name (so emitted FXEvent labels are stable)."""
        # neutral-ambient's first preset reverse-resolves to neutral-ambient,
        # NOT audio-abstract.
        nightvision_family = pfs.family_for_preset("nightvision")
        assert nightvision_family == "neutral-ambient"

    def test_aliases_dict_is_exported(self):
        """FAMILY_ALIASES is the public extension point. If a future
        prompt adds another alias, this is where it lives."""
        assert "FAMILY_ALIASES" in pfs.__all__
        assert pfs.FAMILY_ALIASES["audio-abstract"] == "neutral-ambient"


class TestDirectorPromptCatalogParity:
    """Pin the invariant: every family the director_loop prompt offers
    to the LLM must be queryable from the catalog (canonical or alias).
    Closes the bug class where prompt vocabulary drifts from catalog.
    """

    # The five families currently enumerated in the director_loop
    # preset-family vocabulary. Updating the prompt MUST update this
    # list AND ensure the family is queryable.
    PROMPT_FAMILIES = (
        "audio-reactive",
        "glitch-dense",
        "calm-textural",
        "warm-minimal",
        "audio-abstract",
    )

    def test_every_prompt_family_is_queryable(self):
        for family in self.PROMPT_FAMILIES:
            presets = pfs.presets_for_family(family)
            assert presets, (
                f"prompt family {family!r} has no presets — director can offer "
                f"this family to the LLM but recruitment will return empty"
            )

    def test_every_prompt_family_has_at_least_three_presets(self):
        """Plan §Phase 2 success criterion: ≥3 presets per family so
        the cosine retrieval doesn't repeat the same top-1."""
        for family in self.PROMPT_FAMILIES:
            presets = pfs.presets_for_family(family)
            assert len(presets) >= 3, (
                f"family {family!r} has {len(presets)} presets; "
                "Plan §Phase 2 requires ≥3 to avoid top-1 monoculture"
            )
