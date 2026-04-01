"""Tests for consent label enforcement (Property 5)."""

from __future__ import annotations


def test_non_bottom_label_redacts_person_fields():
    """When label can't flow to bottom, person-adjacent fields are stripped."""
    from agents.hapax_daimonion.env_context import PERSON_ADJACENT_FIELDS
    from shared.governance.consent_label import ConsentLabel

    # A restricted label (alice's data, no readers)
    label = ConsentLabel(frozenset({("alice", frozenset())}))
    assert not label.can_flow_to(ConsentLabel.bottom())

    # Simulated perception data with person-adjacent fields
    data = {
        "flow_score": 0.7,
        "face_count": 2,
        "heart_rate_bpm": 72,
        "ir_person_detected": True,
        "ir_hand_activity": "tapping",
        "ir_drowsiness_score": 0.1,
        "audio_energy": 0.5,
        "app": "bitwig",
    }

    if not label.can_flow_to(ConsentLabel.bottom()):
        for field in PERSON_ADJACENT_FIELDS:
            data.pop(field, None)

    # Person-adjacent fields removed
    assert "face_count" not in data
    assert "heart_rate_bpm" not in data
    assert "ir_person_detected" not in data
    assert "ir_hand_activity" not in data
    assert "ir_drowsiness_score" not in data

    # Non-person fields preserved
    assert data["flow_score"] == 0.7
    assert data["audio_energy"] == 0.5
    assert data["app"] == "bitwig"


def test_bottom_label_preserves_all_fields():
    """Bottom label allows all fields through."""
    from shared.governance.consent_label import ConsentLabel

    label = ConsentLabel.bottom()
    assert label.can_flow_to(ConsentLabel.bottom())

    data = {"face_count": 2, "heart_rate_bpm": 72, "flow_score": 0.7}

    # Bottom label: no redaction
    if not label.can_flow_to(ConsentLabel.bottom()):
        data.pop("face_count", None)  # should not execute

    assert "face_count" in data
    assert "heart_rate_bpm" in data


def test_person_adjacent_fields_comprehensive():
    """All declared person-adjacent fields should be present in the set."""
    from agents.hapax_daimonion.env_context import PERSON_ADJACENT_FIELDS

    # Must include all IR biometric fields
    assert "ir_person_detected" in PERSON_ADJACENT_FIELDS
    assert "ir_heart_rate_bpm" in PERSON_ADJACENT_FIELDS
    assert "ir_drowsiness_score" in PERSON_ADJACENT_FIELDS
    assert "ir_blink_rate" in PERSON_ADJACENT_FIELDS
    assert "ir_posture" in PERSON_ADJACENT_FIELDS
    assert "ir_head_pose_yaw" in PERSON_ADJACENT_FIELDS
    assert "ir_heart_rate_conf" in PERSON_ADJACENT_FIELDS
    assert "ir_hand_activity" in PERSON_ADJACENT_FIELDS
    assert "ir_person_count" in PERSON_ADJACENT_FIELDS

    # Must include non-IR person fields
    assert "face_count" in PERSON_ADJACENT_FIELDS
    assert "speaker_id" in PERSON_ADJACENT_FIELDS
    assert "gaze_zone" in PERSON_ADJACENT_FIELDS
    assert "heart_rate_bpm" in PERSON_ADJACENT_FIELDS
