"""Test consent ingestion filter suppresses person-adjacent behaviors."""


def test_no_guest_passes_through():
    from agents.hapax_daimonion.consent_filter import filter_behaviors

    behaviors = {"ir_person_count": type("B", (), {"_value": 3})()}
    suppressed = filter_behaviors(behaviors, "NO_GUEST")
    assert suppressed == 0
    assert behaviors["ir_person_count"]._value == 3


def test_guest_detected_suppresses():
    from agents.hapax_daimonion.consent_filter import filter_behaviors

    behaviors = {
        "ir_person_count": type("B", (), {"_value": 3})(),
        "ir_heart_rate_bpm": type("B", (), {"_value": 72.0})(),
        "flow_score": type("B", (), {"_value": 0.7})(),  # NOT person-adjacent
    }
    suppressed = filter_behaviors(behaviors, "GUEST_DETECTED")
    assert suppressed == 2
    assert behaviors["ir_person_count"]._value == 0
    assert behaviors["ir_heart_rate_bpm"]._value == 0
    assert behaviors["flow_score"]._value == 0.7  # preserved


def test_consent_granted_passes_through():
    from agents.hapax_daimonion.consent_filter import filter_behaviors

    behaviors = {"ir_person_count": type("B", (), {"_value": 3})()}
    suppressed = filter_behaviors(behaviors, "CONSENT_GRANTED")
    assert suppressed == 0


def test_consent_refused_suppresses():
    from agents.hapax_daimonion.consent_filter import filter_behaviors

    behaviors = {"face_count": type("B", (), {"_value": 2})()}
    suppressed = filter_behaviors(behaviors, "CONSENT_REFUSED")
    assert suppressed == 1
    assert behaviors["face_count"]._value == 0


def test_consent_pending_suppresses():
    from agents.hapax_daimonion.consent_filter import filter_behaviors

    behaviors = {"guest_count": type("B", (), {"_value": 1})()}
    suppressed = filter_behaviors(behaviors, "CONSENT_PENDING")
    assert suppressed == 1
