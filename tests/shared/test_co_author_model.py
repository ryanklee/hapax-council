"""Tests for ``shared.co_author_model``."""

from __future__ import annotations

import pytest

from shared.co_author_model import (
    ALL_CO_AUTHORS,
    CLAUDE_CODE,
    HAPAX,
    OUDEPODE,
    CoAuthor,
    compose_byline,
    get,
    to_cff_authors_block,
)

# ── Canonical registry ──────────────────────────────────────────────


class TestRegistry:
    def test_hapax_is_entity(self):
        assert HAPAX.name == "Hapax"
        assert HAPAX.cff_type == "entity"
        assert HAPAX.role == "primary"

    def test_claude_code_is_entity(self):
        assert CLAUDE_CODE.name == "Claude Code"
        assert CLAUDE_CODE.cff_type == "entity"
        assert CLAUDE_CODE.role == "substrate"

    def test_oudepode_is_person(self):
        assert OUDEPODE.name == "Oudepode"
        assert OUDEPODE.cff_type == "person"
        assert OUDEPODE.role == "operator-of-record"
        assert OUDEPODE.given_names == "Oudepode"
        assert OUDEPODE.alias == "OTO"

    def test_all_three_in_registry(self):
        assert ALL_CO_AUTHORS == (HAPAX, CLAUDE_CODE, OUDEPODE)

    def test_co_author_is_frozen(self):
        with pytest.raises(Exception):
            HAPAX.name = "mutated"  # type: ignore[misc]


# ── CFF rendering ───────────────────────────────────────────────────


class TestCffDict:
    def test_entity_renders_name_alias_website(self):
        d = HAPAX.to_cff_dict()
        assert d == {
            "name": "Hapax",
            "alias": "hapax",
            "website": "https://hapax.omg.lol",
        }

    def test_person_renders_given_family_alias(self):
        d = OUDEPODE.to_cff_dict()
        assert d == {
            "given-names": "Oudepode",
            "family-names": "The Operator",
            "alias": "OTO",
        }

    def test_entity_without_url_omits_website(self):
        bare = CoAuthor(name="Bare", role="primary", cff_type="entity")
        d = bare.to_cff_dict()
        assert d == {"name": "Bare"}


class TestCffAuthorsBlock:
    def test_default_order_primary_substrate_operator(self):
        block = to_cff_authors_block()
        assert len(block) == 3
        assert block[0]["name"] == "Hapax"
        assert block[1]["name"] == "Claude Code"
        assert block[2]["given-names"] == "Oudepode"

    def test_custom_keys_subset(self):
        block = to_cff_authors_block(["hapax", "oudepode"])
        assert len(block) == 2
        assert block[0]["name"] == "Hapax"
        assert "given-names" in block[1]


# ── Byline composition ──────────────────────────────────────────────


class TestComposeByline:
    def test_default_byline(self):
        assert compose_byline() == "Hapax, Claude Code, Oudepode"

    def test_custom_separator(self):
        assert compose_byline(separator=" × ") == "Hapax × Claude Code × Oudepode"

    def test_subset_keys(self):
        assert compose_byline(["hapax", "oudepode"]) == "Hapax, Oudepode"


# ── Lookup helper ───────────────────────────────────────────────────


class TestGet:
    def test_hapax(self):
        assert get("hapax") is HAPAX

    def test_case_insensitive(self):
        assert get("HAPAX") is HAPAX
        assert get("Claude_Code") is CLAUDE_CODE

    def test_alias_for_claude_code(self):
        assert get("claude-code") is CLAUDE_CODE

    def test_operator_alias_for_oudepode(self):
        assert get("operator") is OUDEPODE

    def test_unknown_raises(self):
        with pytest.raises(KeyError, match="unknown co-author"):
            get("ryan")
