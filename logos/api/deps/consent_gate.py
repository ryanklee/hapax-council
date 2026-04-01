"""API egress gate — check _consent labels before serving data."""

from __future__ import annotations

from shared.governance.consent_label import ConsentLabel
from shared.labeled_trace import deserialize_label


def gate_response(data: dict, target_label: ConsentLabel | None = None) -> dict:
    """Check _consent label before API egress.

    For single-operator: target is always bottom (operator reads everything).
    Gate exists for structural completeness.
    """
    if target_label is None:
        target_label = ConsentLabel.bottom()
    consent_data = data.pop("_consent", None)
    if consent_data is None:
        return data
    label, _prov = deserialize_label(consent_data)
    if label.can_flow_to(target_label):
        return data
    return {"_redacted": True, "reason": "consent_label_flow_denied"}
