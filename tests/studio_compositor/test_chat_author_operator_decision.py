"""Tests for _is_chat_author_operator helper — Phase 6c-ii.B.2 wire-in.

Pins the additive-permit semantics: existing literal substring match
on ``"oudepode" in author.lower()`` continues to permit (backward
compat), AND the ChatAuthorIsOperatorEngine asserts on handle membership
provides the new path. Either gate permits — never replaces the
literal match (per handoff §"6c-ii.B.3 specifically": engine posterior
is ADDITIVE, not replacement).
"""

from __future__ import annotations

from agents.studio_compositor.director_loop import _is_chat_author_operator


class TestLiteralSubstringPermit:
    """Backward compat: existing ``"oudepode" in author.lower()``
    substring match continues to permit."""

    def test_lowercase_oudepode_permits(self) -> None:
        assert _is_chat_author_operator("oudepode", operator_handles=frozenset()) is True

    def test_mixed_case_oudepode_permits(self) -> None:
        assert _is_chat_author_operator("Oudepode", operator_handles=frozenset()) is True

    def test_uppercase_oudepode_permits(self) -> None:
        assert _is_chat_author_operator("OUDEPODE", operator_handles=frozenset()) is True

    def test_oudepode_within_longer_handle_permits(self) -> None:
        """Substring match — ``"oudepode_studio"`` permits via literal."""
        assert _is_chat_author_operator("oudepode_studio", operator_handles=frozenset()) is True


class TestEngineAdditivePermit:
    """New behavior: engine asserts when author handle is in
    ``operator_handles`` set, regardless of substring match."""

    def test_handle_in_operator_set_permits_without_substring(self) -> None:
        """A handle like ``"UCxxx-yyy"`` (cryptographic YouTube ID)
        has no ``"oudepode"`` substring; engine permits via membership."""
        assert (
            _is_chat_author_operator(
                "UCxxx-cryptographic-id",
                operator_handles=frozenset({"UCxxx-cryptographic-id"}),
            )
            is True
        )

    def test_handle_in_operator_set_with_other_text_permits(self) -> None:
        """Engine permit fires even when display name is unrelated."""
        assert (
            _is_chat_author_operator(
                "did:plc:bluesky_id_here",
                operator_handles=frozenset({"did:plc:bluesky_id_here", "other"}),
            )
            is True
        )


class TestNeitherPermits:
    """No literal match + handle not in operator_handles → not operator."""

    def test_random_handle_no_substring_no_membership(self) -> None:
        assert _is_chat_author_operator("random_viewer_42", operator_handles=frozenset()) is False

    def test_empty_author_returns_false(self) -> None:
        assert _is_chat_author_operator("", operator_handles=frozenset()) is False

    def test_empty_author_with_populated_handles_returns_false(self) -> None:
        """Empty author can't match anything in operator_handles."""
        assert _is_chat_author_operator("", operator_handles=frozenset({"oudepode"})) is False


class TestAdditiveSemantic:
    """Compounding: literal match permits even when handle isn't in
    operator_handles, AND vice versa. The OR is the defining shape."""

    def test_substring_permit_when_handle_not_in_set(self) -> None:
        """Even when operator_handles has different handles, substring
        match still permits (additive — never blocks the existing path)."""
        assert (
            _is_chat_author_operator(
                "oudepode-author", operator_handles=frozenset({"different_handle"})
            )
            is True
        )

    def test_handle_membership_permit_overrides_no_substring(self) -> None:
        assert _is_chat_author_operator("UC123", operator_handles=frozenset({"UC123"})) is True


class TestDefaultArgument:
    """Default ``operator_handles=frozenset()`` is operationally inert
    for the engine path (engine sees handle_match=False always);
    falls back to literal substring."""

    def test_default_call_substring_path_works(self) -> None:
        assert _is_chat_author_operator("oudepode") is True

    def test_default_call_no_substring_returns_false(self) -> None:
        assert _is_chat_author_operator("random_viewer") is False
