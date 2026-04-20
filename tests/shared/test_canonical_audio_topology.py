"""Regression pin: the canonical config/audio-topology.yaml must always parse.

If this test fails, someone edited config/audio-topology.yaml into an
invalid state — CI should catch it before the descriptor lands and
breaks the Phase 6 CI verify job. Run the actual YAML through the same
TopologyDescriptor validators the live CLI uses.
"""

from __future__ import annotations

from pathlib import Path

from shared.audio_topology import TopologyDescriptor

CANONICAL_YAML = Path(__file__).resolve().parents[2] / "config" / "audio-topology.yaml"


def test_canonical_descriptor_parses() -> None:
    """config/audio-topology.yaml must always satisfy the schema."""
    assert CANONICAL_YAML.exists(), (
        "config/audio-topology.yaml missing — canonical descriptor deleted?"
    )
    d = TopologyDescriptor.from_yaml(CANONICAL_YAML)
    assert d.schema_version == 1


def test_canonical_has_expected_node_ids() -> None:
    """The livestream-critical node IDs must all be present.

    If any of these disappear, the generator won't emit the confs
    daimonion + TTS + OBS depend on — a silent livestream regression.
    Pin them here so a rename has to be explicit in the test too.
    """
    d = TopologyDescriptor.from_yaml(CANONICAL_YAML)
    ids = {n.id for n in d.nodes}
    expected = {
        "l6-capture",
        "livestream-tap",
        "main-mix-tap",
        "voice-fx",
        "livestream-loopback",
        "private-loopback",
        "ryzen-analog-out",
    }
    assert expected.issubset(ids), f"missing expected node ids: {expected - ids}"


def test_canonical_main_mix_tap_has_plus12db() -> None:
    """The L6 Main Mix tap must carry +12 dB makeup gain to hit broadcast LUFS.

    History: the descriptor was tuned empirically against -18 dBFS
    broadcast target (see config/pipewire/hapax-l6-evilpet-capture.conf).
    If a future edit drops the gain back to unity, livestream audio
    reads quiet in OBS.
    """
    d = TopologyDescriptor.from_yaml(CANONICAL_YAML)
    mix_edges = [e for e in d.edges if e.source == "l6-capture" and e.target == "main-mix-tap"]
    assert len(mix_edges) == 2  # AUX10 + AUX11
    for e in mix_edges:
        assert e.makeup_gain_db == 12.0, (
            f"main-mix-tap gain regressed: {e.source_port} at {e.makeup_gain_db} dB"
        )


def test_canonical_voice_fx_targets_ryzen() -> None:
    """TTS must route to Ryzen analog-stereo (→ L6 ch 5 hardware)."""
    d = TopologyDescriptor.from_yaml(CANONICAL_YAML)
    voice_fx = d.node_by_id("voice-fx")
    assert voice_fx.target_object == "alsa_output.pci-0000_73_00.6.analog-stereo"
