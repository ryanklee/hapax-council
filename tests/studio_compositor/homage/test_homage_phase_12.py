"""Phase 12 tests (task #120).

Covers the three go-live behaviours:

1. ``HAPAX_HOMAGE_ACTIVE`` default flipped to ON. Unset env → active.
   Explicit falsy value → dormant.
2. Consent-safe variant engages when
   ``/dev/shm/hapax-compositor/consent-safe-active.json`` is present,
   and disengages cleanly when the file is removed.
3. Signature artefact emission runs per rotation cycle (selection is
   RNG-driven; we inject a seeded Random to make it deterministic).
"""

from __future__ import annotations

import json
import random
from pathlib import Path
from unittest import mock

import pytest

from agents.studio_compositor.homage import (
    BITCHX_CONSENT_SAFE_PACKAGE,
    BITCHX_PACKAGE,
    get_consent_safe_package,
)
from agents.studio_compositor.homage.choreographer import (
    Choreographer,
    _feature_flag_active,
)
from agents.studio_compositor.homage.transitional_source import (
    _feature_flag_active as _transitional_flag_active,
)

# ── 1. Feature flag default-ON ────────────────────────────────────────────


class TestFeatureFlagDefault:
    def test_unset_env_resolves_to_active(self, monkeypatch):
        """Phase 12 contract: missing env var → HOMAGE active."""
        monkeypatch.delenv("HAPAX_HOMAGE_ACTIVE", raising=False)
        assert _feature_flag_active() is True
        assert _transitional_flag_active() is True

    def test_empty_string_resolves_to_active(self, monkeypatch):
        monkeypatch.setenv("HAPAX_HOMAGE_ACTIVE", "")
        assert _feature_flag_active() is True
        assert _transitional_flag_active() is True

    @pytest.mark.parametrize("value", ["0", "false", "no", "off", "FALSE", "Off"])
    def test_explicit_falsy_disables(self, monkeypatch, value):
        monkeypatch.setenv("HAPAX_HOMAGE_ACTIVE", value)
        assert _feature_flag_active() is False
        assert _transitional_flag_active() is False

    @pytest.mark.parametrize("value", ["1", "true", "yes", "on", "anything-else"])
    def test_truthy_values_enable(self, monkeypatch, value):
        monkeypatch.setenv("HAPAX_HOMAGE_ACTIVE", value)
        assert _feature_flag_active() is True
        assert _transitional_flag_active() is True


# ── 2. Consent-safe variant ───────────────────────────────────────────────


class TestConsentSafeVariant:
    def test_registered_at_import(self):
        assert get_consent_safe_package() is BITCHX_CONSENT_SAFE_PACKAGE

    def test_variant_shares_grammar_with_primary(self):
        """Grammar is preserved — transitions, typography, raster."""
        assert BITCHX_CONSENT_SAFE_PACKAGE.grammar == BITCHX_PACKAGE.grammar
        assert BITCHX_CONSENT_SAFE_PACKAGE.typography == BITCHX_PACKAGE.typography
        assert (
            BITCHX_CONSENT_SAFE_PACKAGE.transition_vocabulary
            == BITCHX_PACKAGE.transition_vocabulary
        )

    def test_variant_strips_identity_accents(self):
        """Every accent collapses to the same muted grey as punctuation."""
        safe = BITCHX_CONSENT_SAFE_PACKAGE.palette
        muted = safe.muted
        assert safe.bright == muted
        assert safe.accent_cyan == muted
        assert safe.accent_magenta == muted
        assert safe.accent_green == muted
        assert safe.accent_yellow == muted
        assert safe.accent_red == muted
        assert safe.accent_blue == muted
        assert safe.terminal_default == muted

    def test_variant_strips_artefact_corpus(self):
        assert BITCHX_CONSENT_SAFE_PACKAGE.signature_artefacts == ()
        # Sanity: the primary package still has its 41 seed artefacts.
        assert len(BITCHX_PACKAGE.signature_artefacts) > 0

    def _make_chor(
        self,
        tmp_path: Path,
        *,
        consent_safe_present: bool,
        rng_seed: int = 0,
    ) -> tuple[Choreographer, Path]:
        flag_file = tmp_path / "consent-safe-active.json"
        if consent_safe_present:
            flag_file.write_text(json.dumps({"consent_safe": True}), encoding="utf-8")
        chor = Choreographer(
            pending_file=tmp_path / "homage-pending.json",
            uniforms_file=tmp_path / "uniforms.json",
            substrate_package_file=tmp_path / "homage-substrate-package.json",
            consent_safe_flag_file=flag_file,
            rng=random.Random(rng_seed),
        )
        return chor, flag_file

    def test_consent_gate_selects_safe_variant(self, tmp_path, monkeypatch):
        """When the flag file exists, reconcile rewrites with the safe variant."""
        monkeypatch.setenv("HAPAX_HOMAGE_ACTIVE", "1")
        chor, flag_file = self._make_chor(tmp_path, consent_safe_present=True)
        # Swap broadcast emits the consent-safe package name, not bitchx.
        chor.reconcile(BITCHX_PACKAGE, now=0.0)
        substrate_file = tmp_path / "homage-substrate-package.json"
        assert substrate_file.exists()
        payload = json.loads(substrate_file.read_text(encoding="utf-8"))
        assert payload["package"] == "bitchx_consent_safe"

    def test_consent_gate_clears_restores_default(self, tmp_path, monkeypatch):
        monkeypatch.setenv("HAPAX_HOMAGE_ACTIVE", "1")
        chor, flag_file = self._make_chor(tmp_path, consent_safe_present=True)
        # Tick 1: consent-safe engaged.
        chor.reconcile(BITCHX_PACKAGE, now=0.0)
        substrate_file = tmp_path / "homage-substrate-package.json"
        payload = json.loads(substrate_file.read_text(encoding="utf-8"))
        assert payload["package"] == "bitchx_consent_safe"
        # Remove flag file, tick 2: back to bitchx.
        flag_file.unlink()
        chor.reconcile(BITCHX_PACKAGE, now=90.0)
        payload = json.loads(substrate_file.read_text(encoding="utf-8"))
        assert payload["package"] == "bitchx"

    def test_consent_safe_emits_no_artefact(self, tmp_path, monkeypatch):
        """The safe variant's empty corpus must produce zero artefact events."""
        monkeypatch.setenv("HAPAX_HOMAGE_ACTIVE", "1")
        chor, _ = self._make_chor(tmp_path, consent_safe_present=True)
        # Drive through several rotation cycles — no emission should happen.
        for tick_s in (0.0, 90.0, 180.0, 270.0):
            chor.reconcile(BITCHX_PACKAGE, now=tick_s)
        artefact_file = tmp_path / "homage-active-artefact.json"
        assert not artefact_file.exists()


# ── 3. Signature artefact emission ────────────────────────────────────────


class TestSignatureArtefactEmission:
    @pytest.fixture
    def chor(self, tmp_path: Path) -> Choreographer:
        return Choreographer(
            pending_file=tmp_path / "homage-pending.json",
            uniforms_file=tmp_path / "uniforms.json",
            substrate_package_file=tmp_path / "homage-substrate-package.json",
            consent_safe_flag_file=tmp_path / "consent-safe-none.json",
            rng=random.Random(42),
        )

    def test_first_tick_emits_artefact(self, chor, tmp_path, monkeypatch):
        monkeypatch.setenv("HAPAX_HOMAGE_ACTIVE", "1")
        result = chor.reconcile(BITCHX_PACKAGE, now=0.0)
        assert result.coupled_payload.signature_artefact_intensity == 1.0
        artefact_file = tmp_path / "homage-active-artefact.json"
        assert artefact_file.exists()
        payload = json.loads(artefact_file.read_text(encoding="utf-8"))
        assert payload["package"] == "bitchx"
        assert payload["content"]
        assert payload["form"] in (
            "quit-quip",
            "join-banner",
            "motd-block",
            "kick-reason",
        )

    def test_within_cycle_does_not_re_emit(self, chor, monkeypatch):
        monkeypatch.setenv("HAPAX_HOMAGE_ACTIVE", "1")
        # Cadence is 90s; ticks at 0s and 30s share cycle 0.
        first = chor.reconcile(BITCHX_PACKAGE, now=0.0)
        second = chor.reconcile(BITCHX_PACKAGE, now=30.0)
        assert first.coupled_payload.signature_artefact_intensity == 1.0
        # Second tick in same cycle → no re-emission.
        assert second.coupled_payload.signature_artefact_intensity == 0.0

    def test_new_cycle_re_emits(self, chor, monkeypatch):
        monkeypatch.setenv("HAPAX_HOMAGE_ACTIVE", "1")
        first = chor.reconcile(BITCHX_PACKAGE, now=0.0)
        # Jump past the 90s rotation boundary into cycle 1.
        second = chor.reconcile(BITCHX_PACKAGE, now=95.0)
        assert first.coupled_payload.signature_artefact_intensity == 1.0
        assert second.coupled_payload.signature_artefact_intensity == 1.0

    def test_seeded_rng_is_deterministic(self, tmp_path, monkeypatch):
        """Same seed + same corpus → same artefact selected."""
        monkeypatch.setenv("HAPAX_HOMAGE_ACTIVE", "1")
        chor_a = Choreographer(
            pending_file=tmp_path / "a-pending.json",
            uniforms_file=tmp_path / "a-uniforms.json",
            substrate_package_file=tmp_path / "a-substrate.json",
            consent_safe_flag_file=tmp_path / "a-consent.json",
            rng=random.Random(7),
        )
        chor_b = Choreographer(
            pending_file=tmp_path / "b-pending.json",
            uniforms_file=tmp_path / "b-uniforms.json",
            substrate_package_file=tmp_path / "b-substrate.json",
            consent_safe_flag_file=tmp_path / "b-consent.json",
            rng=random.Random(7),
        )
        chor_a.reconcile(BITCHX_PACKAGE, now=0.0)
        chor_b.reconcile(BITCHX_PACKAGE, now=0.0)
        assert chor_a._last_emitted_artefact == chor_b._last_emitted_artefact
        assert chor_a._last_emitted_artefact is not None

    def test_metric_counter_incremented(self, chor, monkeypatch):
        monkeypatch.setenv("HAPAX_HOMAGE_ACTIVE", "1")
        with mock.patch("shared.director_observability.emit_homage_signature_artefact") as emit:
            chor.reconcile(BITCHX_PACKAGE, now=0.0)
        assert emit.call_count == 1
        call_args = emit.call_args
        assert call_args.args[0] == "bitchx"
        assert call_args.args[1] in (
            "quit-quip",
            "join-banner",
            "motd-block",
            "kick-reason",
        )

    def test_flag_off_suppresses_emission(self, chor, tmp_path, monkeypatch):
        monkeypatch.setenv("HAPAX_HOMAGE_ACTIVE", "0")
        result = chor.reconcile(BITCHX_PACKAGE, now=0.0)
        assert result.coupled_payload.signature_artefact_intensity == 0.0
        artefact_file = tmp_path / "homage-active-artefact.json"
        assert not artefact_file.exists()
