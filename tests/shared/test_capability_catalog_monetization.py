"""CI-blocking monetization-risk invariants on the capability catalog.

Enforces the rubric in ``docs/governance/monetization-risk-
classification.md``:

1. Every ``CapabilityRecord`` in the static catalogs has an explicit
   ``monetization_risk`` attribute (a Pydantic default produces this;
   the test asserts no ``None`` sneaks in).
2. Every record with ``monetization_risk in ('low', 'medium', 'high')``
   has a non-empty ``risk_reason``. ``none`` records may have empty
   reasons — they are the majority of the catalog and the default
   coverage case.
3. ``high``-risk records carry a ``risk_reason`` that names the
   unconditional-block semantics explicitly (so an auditor skimming
   the catalog knows which records cannot be opted into by a
   Programme).

Failure fails the ``test`` CI check and blocks merge. Failure message
names the offending record so the fix is one-line.

Reference:
    - docs/governance/monetization-risk-classification.md
    - docs/superpowers/plans/2026-04-20-demonetization-safety-plan.md §2
    - shared/affordance.py (MonetizationRisk literal definition)
"""

from __future__ import annotations

from typing import Any, get_args

from shared.affordance import MonetizationRisk

_ALLOWED_RISK_LEVELS: frozenset[str] = frozenset(get_args(MonetizationRisk))


def _collect_all_capability_records() -> list[Any]:
    """Enumerate every CapabilityRecord reachable from static catalogs.

    Imports each catalog module and collects both module-level lists
    and nested records the affordance pipeline registers at startup.
    Pure data lookup — no DB / network / daemon dependency.
    """
    records: list[Any] = []

    # Primary registry — 20+ module-level _AFFORDANCES lists + the
    # compositional helpers.
    from shared import affordance_registry

    for name in dir(affordance_registry):
        if not name.endswith("_AFFORDANCES"):
            continue
        obj = getattr(affordance_registry, name)
        if isinstance(obj, list):
            records.extend(obj)

    # Compositional affordances — currently holds
    # compositional_affordance_record() builders + the compositor's
    # capability list.
    try:
        from shared import compositional_affordances

        for name in dir(compositional_affordances):
            obj = getattr(compositional_affordances, name)
            if isinstance(obj, list):
                # Filter to lists whose elements look like CapabilityRecords.
                if obj and hasattr(obj[0], "operational") and hasattr(obj[0], "name"):
                    records.extend(obj)
    except ImportError:
        pass

    return records


class TestMonetizationRiskInvariants:
    """Catalog-coverage tests — CI-blocking enforcement of the rubric."""

    def test_catalog_is_nonempty(self) -> None:
        """Sanity check: the test itself finds records. Catches import-graph regressions."""
        records = _collect_all_capability_records()
        assert len(records) > 20, (
            f"catalog collector found only {len(records)} records; expected >20 "
            "across ENV_/BODY_/SPACE_/DIGITAL_/SYSTEM_/KNOWLEDGE_/SOCIAL_/WORLD_ "
            "registries. Check the import graph in _collect_all_capability_records()."
        )

    def test_every_record_has_valid_risk_level(self) -> None:
        """monetization_risk must be one of the Literal members."""
        offenders: list[str] = []
        for rec in _collect_all_capability_records():
            risk = getattr(rec.operational, "monetization_risk", None)
            if risk not in _ALLOWED_RISK_LEVELS:
                offenders.append(f"{rec.name}: risk={risk!r}")
        assert not offenders, "CapabilityRecords with invalid monetization_risk:\n  " + "\n  ".join(
            offenders
        )

    def test_risky_records_have_reason(self) -> None:
        """low/medium/high risk requires non-empty risk_reason (rubric §each-level)."""
        offenders: list[str] = []
        for rec in _collect_all_capability_records():
            risk = rec.operational.monetization_risk
            reason = rec.operational.risk_reason or ""
            if risk != "none" and not reason.strip():
                offenders.append(f"{rec.name}: risk={risk}, reason is empty")
        assert not offenders, (
            "Records with non-'none' monetization_risk but empty risk_reason "
            "(violates governance rubric §2):\n  " + "\n  ".join(offenders)
        )

    def test_high_risk_reason_names_block_semantics(self) -> None:
        """high-risk records MUST mention their block semantics in risk_reason.

        Enforces the rubric's §high clause: the reason should tell a future
        auditor that this capability is unconditionally blocked (not just
        Programme-gated). We look for any of the keyword tokens an auditor
        might have used — substring match is enough; exhaustive phrasing
        check would be brittle.
        """
        offenders: list[str] = []
        required_any = ("block", "Content-ID", "Content ID", "unconditional", "curated")
        for rec in _collect_all_capability_records():
            if rec.operational.monetization_risk != "high":
                continue
            reason = (rec.operational.risk_reason or "").lower()
            if not any(tok.lower() in reason for tok in required_any):
                offenders.append(
                    f"{rec.name}: high-risk but reason lacks block semantics: {reason!r}"
                )
        assert not offenders, (
            "high-risk records should name their block semantics:\n  " + "\n  ".join(offenders)
        )
