"""Phase 6c-ii.B.3 — ChatAuthorIsOperatorEngine ADDITIVE permit in qdrant_gate.

Pins the wire-in semantics: the engine posterior is an ADDITIVE permit
on top of the existing literal-match (``DEFAULT_OPERATOR_IDS``) and
the consent-registry check. **Never replaces** the existing fail-
closed behavior.

The OR shape (per handoff §"6c-ii.B.3 specifically"):

  literal-match permits OR engine permits OR consent permits → write allowed
  none of the three → curtailed

This is the highest-risk wire-in in the 6c-ii.B series. The contract
under test:

  1. Default ``operator_handles=frozenset()`` → engine path inert,
     existing behavior byte-identical.
  2. With ``operator_handles`` populated, a chat-author handle in the
     set → permitted (no consent check needed).
  3. Engine path is ADDITIVE — literal-match operator_ids and the
     consent registry remain authoritative; engine never DENIES.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from unittest.mock import MagicMock

import pytest

from shared.governance.qdrant_gate import ConsentGatedQdrant


@dataclass
class _FakePoint:
    """Minimal Qdrant point stand-in — just the payload attribute."""

    payload: dict[str, Any]


def _deny_all_check(*_args: Any, **_kwargs: Any) -> bool:
    """ConsentRegistry stand-in that denies every person ID — isolates
    the test to the literal-match + engine-permit paths."""
    return False


def _make_gate(
    *,
    operator_handles: frozenset[str] = frozenset(),
    deny_all: bool = True,
) -> ConsentGatedQdrant:
    """Build a ConsentGatedQdrant with mocked inner client + consent
    check that defaults to DENY ALL (so any allow path must come from
    operator_ids OR engine permit)."""
    inner = MagicMock()
    gate = ConsentGatedQdrant(inner=inner, _operator_handles=operator_handles)
    if deny_all:
        gate._contract_check = _deny_all_check
    return gate


# ── Default behavior: engine path inert ─────────────────────────────


class TestDefaultEngineInert:
    """``operator_handles=frozenset()`` → engine path makes no decisions."""

    def test_unknown_handle_with_default_handles_is_curtailed(self) -> None:
        """No literal match + no engine handles + consent denies →
        curtailed (existing fail-closed behavior preserved)."""
        gate = _make_gate()
        point = _FakePoint(payload={"chat_authors": ["random_viewer_42"]})
        gate.upsert("stream-reactions", [point])
        # Inner upsert never called: all points curtailed.
        gate.inner.upsert.assert_not_called()
        decisions = gate.decisions
        assert len(decisions) == 1
        assert decisions[0].curtailed_count == 1
        assert "random_viewer_42" in decisions[0].unconsented

    def test_literal_operator_id_still_permitted(self) -> None:
        """Literal-match `"operator"` in DEFAULT_OPERATOR_IDS still
        bypasses the consent check (backward compat)."""
        gate = _make_gate()
        point = _FakePoint(payload={"chat_authors": ["operator"]})
        gate.upsert("stream-reactions", [point])
        # Point passed through (operator is in DEFAULT_OPERATOR_IDS).
        gate.inner.upsert.assert_called_once()


# ── Engine ADDITIVE permit: handle in operator_handles set ───────────


class TestEngineAdditivePermit:
    def test_handle_in_operator_handles_permits_write(self) -> None:
        """``operator_handles`` populated; a chat-author handle in the
        set engages the engine permit → write allowed despite consent
        denying."""
        gate = _make_gate(operator_handles=frozenset({"UCxxx-yt-id"}))
        point = _FakePoint(payload={"chat_authors": ["UCxxx-yt-id"]})
        gate.upsert("stream-reactions", [point])
        gate.inner.upsert.assert_called_once()
        decisions = gate.decisions
        assert decisions[0].curtailed_count == 0

    def test_handle_not_in_operator_handles_still_curtailed(self) -> None:
        """``operator_handles`` populated but THIS handle isn't in it.
        Consent denies → curtailed. Verifies the engine permit is
        scoped per-handle, not blanket-allow."""
        gate = _make_gate(operator_handles=frozenset({"UCxxx-yt-id"}))
        point = _FakePoint(payload={"chat_authors": ["random_viewer_42"]})
        gate.upsert("stream-reactions", [point])
        gate.inner.upsert.assert_not_called()
        decisions = gate.decisions
        assert decisions[0].curtailed_count == 1
        assert "random_viewer_42" in decisions[0].unconsented


# ── Mixed-batch: per-point curtailment is granular ───────────────────


class TestMixedBatch:
    def test_partial_curtailment_keeps_permitted_points(self) -> None:
        """One point with operator-handle + one with random viewer →
        first allowed, second curtailed. Inner upsert receives only
        the permitted points (per-point granularity preserved)."""
        gate = _make_gate(operator_handles=frozenset({"UCxxx-yt-id"}))
        permitted = _FakePoint(payload={"chat_authors": ["UCxxx-yt-id"]})
        denied = _FakePoint(payload={"chat_authors": ["random_viewer_42"]})
        gate.upsert("stream-reactions", [permitted, denied])
        # Inner upsert called with only the permitted point.
        gate.inner.upsert.assert_called_once()
        args, _ = gate.inner.upsert.call_args
        _, allowed_points = args[0], args[1]
        assert len(allowed_points) == 1
        assert allowed_points[0].payload["chat_authors"] == ["UCxxx-yt-id"]


# ── set_payload: same OR-gate semantic ───────────────────────────────


class TestSetPayloadAdditivePermit:
    def test_engine_permit_allows_set_payload(self) -> None:
        """set_payload also walks the same person-id check; engine
        permit applies symmetrically."""
        gate = _make_gate(operator_handles=frozenset({"UCxxx-yt-id"}))
        gate.set_payload(
            "stream-reactions",
            payload={"chat_authors": ["UCxxx-yt-id"]},
            points=[1, 2, 3],
        )
        gate.inner.set_payload.assert_called_once()

    def test_unknown_handle_still_blocks_set_payload(self) -> None:
        """Engine inert on unknown handle; consent denies; set_payload
        blocked (preserves fail-closed)."""
        gate = _make_gate(operator_handles=frozenset({"UCxxx-yt-id"}))
        result = gate.set_payload(
            "stream-reactions",
            payload={"chat_authors": ["random_viewer_42"]},
            points=[1, 2, 3],
        )
        assert result is None
        gate.inner.set_payload.assert_not_called()


# ── Defense-in-depth: engine path is ADDITIVE, never replacement ─────


class TestNeverReplacesFailClosed:
    """Pin the regression invariant: engine path adds a permit edge,
    never removes the existing literal-match or consent path. The
    existing fail-closed behavior is preserved when neither engine
    nor consent permits."""

    def test_no_handle_no_consent_no_permit_fails_closed(self) -> None:
        """Empty operator_handles + consent denies → fail-closed."""
        gate = _make_gate(operator_handles=frozenset())
        point = _FakePoint(payload={"chat_authors": ["nobody"]})
        gate.upsert("stream-reactions", [point])
        gate.inner.upsert.assert_not_called()
        assert gate.decisions[0].curtailed_count == 1

    def test_engine_does_not_curtail_consented_handle(self) -> None:
        """If the consent registry permits a handle (mock returns True),
        the engine path never DOWNGRADES that decision — consent
        permits → write allowed."""

        def _allow_all(*_args: Any, **_kwargs: Any) -> bool:
            return True

        gate = _make_gate(operator_handles=frozenset(), deny_all=False)
        gate._contract_check = _allow_all
        point = _FakePoint(payload={"chat_authors": ["consented_user"]})
        gate.upsert("stream-reactions", [point])
        gate.inner.upsert.assert_called_once()
        assert gate.decisions[0].curtailed_count == 0


# ── Empty handle / edge cases ────────────────────────────────────────


class TestEdgeCases:
    def test_empty_operator_handles_field_default(self) -> None:
        """Default field — no kwarg required to retain existing
        behavior. Test verifies the field default is empty frozenset."""
        gate = ConsentGatedQdrant(inner=MagicMock())
        assert gate._operator_handles == frozenset()

    def test_exempt_collection_unaffected_by_engine(self) -> None:
        """Collections NOT in PERSON_ADJACENT_COLLECTIONS pass through
        unchanged regardless of engine state."""
        gate = _make_gate(operator_handles=frozenset({"UCxxx-yt-id"}))
        point = _FakePoint(payload={"chat_authors": ["random_viewer_42"]})
        gate.upsert("operator-episodes", [point])
        # Exempt collection — no curtailment, inner upsert called directly.
        gate.inner.upsert.assert_called_once()
        # No QdrantGateDecision recorded (the gate short-circuits).
        assert gate.decisions == []


@pytest.mark.parametrize(
    "collection,field_in_payload",
    [
        ("documents", "people"),
        ("profile-facts", "audience_key"),
        ("stream-reactions", "chat_authors"),
        ("studio-moments", "audience"),
        ("hapax-apperceptions", "people"),
    ],
)
class TestAcrossPersonAdjacentCollections:
    """Engine permit fires across all 5 person-adjacent collections,
    not just stream-reactions."""

    def test_engine_permit_per_collection(self, collection: str, field_in_payload: str) -> None:
        gate = _make_gate(operator_handles=frozenset({"UCxxx"}))
        # ``audience_key`` is direct-mode; others are list-mode.
        if field_in_payload == "audience_key":
            payload = {field_in_payload: "UCxxx"}
        else:
            payload = {field_in_payload: ["UCxxx"]}
        point = _FakePoint(payload=payload)
        gate.upsert(collection, [point])
        gate.inner.upsert.assert_called_once()
