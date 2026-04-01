"""Tests for logos.data.session_inference — deterministic session context inference."""

from __future__ import annotations

from unittest.mock import patch

from logos.data.session_inference import SessionContext, infer_session

MODULE = "logos.data.session_inference"


def _patch_all(
    stimmung: dict | None = None,
    sprint: dict | None = None,
    git: dict[str, float] | None = None,
    vault: float = 999.0,
):
    """Return a stack of patches for the four internal readers."""
    return (
        patch(f"{MODULE}._read_stimmung", return_value=stimmung or {}),
        patch(f"{MODULE}._read_sprint_state", return_value=sprint or {}),
        patch(f"{MODULE}._git_recency", return_value=git or {}),
        patch(f"{MODULE}._vault_recency", return_value=vault),
    )


class TestEmptySignals:
    def test_defaults(self):
        p1, p2, p3, p4 = _patch_all()
        with p1, p2, p3, p4:
            ctx = infer_session()
        assert isinstance(ctx, SessionContext)
        assert ctx.last_active_domain == ""
        assert ctx.session_boundary is False


class TestAbsenceDetection:
    def test_ir_absence_3h(self):
        """last_person_detected_at 3h ago → absence ≥ 2.9, boundary True."""
        import time

        three_hours_ago = time.time() - 3 * 3600
        stimmung = {"last_person_detected_at": three_hours_ago}
        p1, p2, p3, p4 = _patch_all(stimmung=stimmung)
        with p1, p2, p3, p4:
            ctx = infer_session()
        assert ctx.absence_hours >= 2.9
        assert ctx.session_boundary is True

    def test_no_boundary_when_present(self):
        """last_person_detected_at 60s ago → absence < 1, boundary False."""
        import time

        recent = time.time() - 60
        stimmung = {"last_person_detected_at": recent}
        p1, p2, p3, p4 = _patch_all(stimmung=stimmung)
        with p1, p2, p3, p4:
            ctx = infer_session()
        assert ctx.absence_hours < 1.0
        assert ctx.session_boundary is False


class TestDomainRecency:
    def test_git_recency_maps_to_domain(self):
        """hapax-council at 1.5h → research domain recency ≤ 1.5."""
        git = {"hapax-council": 1.5}
        p1, p2, p3, p4 = _patch_all(git=git)
        with p1, p2, p3, p4:
            ctx = infer_session(domains={"research": {"repos": ["hapax-council"]}})
        assert "research" in ctx.domain_recency
        assert ctx.domain_recency["research"] <= 1.5

    def test_vault_recency_maps_to_domain(self):
        """Studio vault path at 0.5h → studio recency ≤ 0.5."""
        p1, p2, p3, p4 = _patch_all(vault=0.5)
        with p1, p2, p3, p4:
            ctx = infer_session(domains={"studio": {"vault_paths": ["Music/Studio"]}})
        assert "studio" in ctx.domain_recency
        assert ctx.domain_recency["studio"] <= 0.5

    def test_most_recent_domain_wins(self):
        """studio at 0.5h, research at 5.0h → last_active_domain == studio."""
        git = {"hapax-council": 5.0}
        p1, p2, p3, p4 = _patch_all(git=git, vault=0.5)
        with p1, p2, p3, p4:
            ctx = infer_session(
                domains={
                    "studio": {"vault_paths": ["Music/Studio"]},
                    "research": {"repos": ["hapax-council"]},
                }
            )
        assert ctx.last_active_domain == "studio"
