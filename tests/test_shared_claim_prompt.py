"""Tests for ``shared.claim_prompt`` (Bayesian Phase 4 — prompt envelope)."""

from __future__ import annotations

from shared.claim import (
    Claim,
    EvidenceRef,
    TemporalProfile,
)
from shared.claim_prompt import (
    CLAIMS_BLOCK_HEADER,
    SURFACE_FLOORS,
    UNCERTAINTY_CONTRACT,
    render_claims,
    render_envelope,
)


def _make_claim(
    *,
    name: str = "vinyl_playing",
    proposition: str = "Turntable platter rotating ~33 RPM.",
    posterior: float = 0.88,
    signal_name: str = "vinyl_rpm_sensor",
    floor: float = 0.60,
) -> Claim:
    return Claim(
        name=name,
        domain="audio",
        proposition=proposition,
        posterior=posterior,
        prior_source="reference",
        prior_provenance_ref="vinyl_playing.v1",
        evidence_sources=[
            EvidenceRef(
                signal_name=signal_name,
                value=True,
                timestamp=1714000000.0,
                frame_source="raw_sensor",
            )
        ],
        last_update_t=1714000000.0,
        temporal_profile=TemporalProfile(
            enter_threshold=0.7, exit_threshold=0.3, k_enter=2, k_exit=24
        ),
        narration_floor=floor,
        staleness_cutoff_s=60.0,
    )


# ── Surface floors ──────────────────────────────────────────────────


class TestSurfaceFloors:
    def test_canonical_set(self):
        assert SURFACE_FLOORS == {
            "director": 0.60,
            "spontaneous_speech": 0.70,
            "autonomous_narrative": 0.75,
            "voice_persona": 0.80,
            "grounding_act": 0.90,
        }

    def test_floors_strictly_increasing(self):
        ordered = [
            "director",
            "spontaneous_speech",
            "autonomous_narrative",
            "voice_persona",
            "grounding_act",
        ]
        floors = [SURFACE_FLOORS[s] for s in ordered]
        assert floors == sorted(floors)


# ── Uncertainty contract ────────────────────────────────────────────


class TestUncertaintyContract:
    def test_contract_thresholds_match_spec(self):
        assert "0.85" in UNCERTAINTY_CONTRACT
        assert "0.6" in UNCERTAINTY_CONTRACT
        assert "ground" in UNCERTAINTY_CONTRACT
        assert "provisional" in UNCERTAINTY_CONTRACT

    def test_contract_warns_against_decorative_text(self):
        assert "decorative" in UNCERTAINTY_CONTRACT
        assert "NOT evidence" in UNCERTAINTY_CONTRACT


# ── render_claims ───────────────────────────────────────────────────


class TestRenderClaimsAboveFloor:
    def test_above_floor_renders_pXX_src_form(self):
        claim = _make_claim(posterior=0.88, signal_name="vinyl_rpm_sensor")
        out = render_claims([claim], floor=0.60)
        assert "[p=0.88 src=vinyl_rpm_sensor] Turntable platter rotating ~33 RPM." in out

    def test_posterior_formatted_two_decimals(self):
        claim = _make_claim(posterior=0.974321)
        out = render_claims([claim], floor=0.60)
        assert "[p=0.97" in out
        assert "0.974321" not in out

    def test_uses_first_evidence_source_signal_name(self):
        claim = _make_claim(signal_name="ir_hand_active")
        out = render_claims([claim], floor=0.60)
        assert "src=ir_hand_active" in out

    def test_falls_back_to_claim_name_if_no_evidence(self):
        claim = Claim(
            name="placeholder_claim",
            domain="meta",
            proposition="A meta-claim with no evidence.",
            posterior=0.91,
            prior_source="maximum_entropy",
            prior_provenance_ref="placeholder.v1",
            evidence_sources=[],
            last_update_t=0.0,
            temporal_profile=TemporalProfile(
                enter_threshold=0.7, exit_threshold=0.3, k_enter=2, k_exit=2
            ),
            narration_floor=0.60,
            staleness_cutoff_s=60.0,
        )
        out = render_claims([claim], floor=0.60)
        assert "src=placeholder_claim" in out


class TestRenderClaimsBelowFloor:
    def test_below_floor_renders_unknown(self):
        claim = _make_claim(
            proposition="Audio fingerprint matches 'Hoe Cakes' weakly.",
            posterior=0.31,
            signal_name="audio_fingerprint",
        )
        out = render_claims([claim], floor=0.60)
        assert "[UNKNOWN] Audio fingerprint matches 'Hoe Cakes' weakly." in out

    def test_below_floor_does_not_emit_posterior(self):
        claim = _make_claim(posterior=0.31)
        out = render_claims([claim], floor=0.60)
        assert "p=0.31" not in out
        assert "[UNKNOWN]" in out

    def test_at_floor_is_above(self):
        claim = _make_claim(posterior=0.60)
        out = render_claims([claim], floor=0.60)
        assert "p=0.60" in out
        assert "[UNKNOWN]" not in out


class TestRenderClaimsHeader:
    def test_header_includes_floor(self):
        out = render_claims([], floor=0.75)
        assert CLAIMS_BLOCK_HEADER.format(floor=0.75) in out
        assert "0.75" in out

    def test_empty_claims_emits_sentinel(self):
        out = render_claims([], floor=0.60)
        assert "(no perceptual claims active)" in out

    def test_mixed_above_and_below_floor(self):
        above = _make_claim(name="c1", proposition="claim A", posterior=0.90, signal_name="sig_a")
        below = _make_claim(name="c2", proposition="claim B", posterior=0.40, signal_name="sig_b")
        out = render_claims([above, below], floor=0.60)
        assert "[p=0.90 src=sig_a] claim A" in out
        assert "[UNKNOWN] claim B" in out


# ── render_envelope ──────────────────────────────────────────────────


class TestRenderEnvelope:
    def test_envelope_starts_with_contract(self):
        out = render_envelope([], floor=0.60)
        assert out.startswith(UNCERTAINTY_CONTRACT)

    def test_envelope_contains_claims_block(self):
        claim = _make_claim()
        out = render_envelope([claim], floor=0.60)
        assert UNCERTAINTY_CONTRACT in out
        assert "[p=" in out
        assert claim.proposition in out


# ── Surface migrations (Phase 4 wiring contract) ────────────────────


class TestPersonaSurfaceMigration:
    def test_persona_system_prompt_starts_with_uncertainty_contract(self):
        from agents.hapax_daimonion.persona import system_prompt

        out = system_prompt(guest_mode=True, policy_block="")
        assert out.startswith(UNCERTAINTY_CONTRACT)

    def test_persona_uses_voice_persona_floor(self):
        from agents.hapax_daimonion.persona import system_prompt

        out = system_prompt(guest_mode=True)
        assert "0.80" in out


class TestAutonomousNarrativeSurfaceMigration:
    def test_autonomous_narrative_prompt_includes_uncertainty_contract(self):
        from agents.hapax_daimonion.autonomous_narrative.compose import _build_prompt

        out = _build_prompt(context=None, seed="test seed")
        assert UNCERTAINTY_CONTRACT in out

    def test_autonomous_narrative_uses_correct_floor(self):
        from agents.hapax_daimonion.autonomous_narrative.compose import _build_prompt

        out = _build_prompt(context=None, seed="test seed")
        assert "0.75" in out


class TestDirectorSurfaceMigration:
    def test_director_loop_imports_envelope(self):
        from agents.studio_compositor import director_loop

        assert hasattr(director_loop, "render_envelope")
        assert hasattr(director_loop, "SURFACE_FLOORS")
        assert director_loop.SURFACE_FLOORS["director"] == 0.60
