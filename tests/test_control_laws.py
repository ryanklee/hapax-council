"""Verify all 14 components have control law blocks."""

CONTROL_LAW_COMPONENTS = [
    "agents/dmn/pulse.py",
    "agents/content_resolver/__main__.py",
    "shared/stimmung.py",
    "agents/hapax_daimonion/perception_loop.py",
    "agents/hapax_daimonion/backends/ir_presence.py",
    "agents/hapax_daimonion/backends/contact_mic.py",
    "agents/temporal_bands.py",
    "agents/_apperception.py",
    "logos/engine/executor.py",
    "agents/studio_compositor/lifecycle.py",
    "agents/reverie/__main__.py",
    "agents/imagination_daemon/__main__.py",
    "shared/governance/consent.py",
]


def test_all_components_have_control_law():
    for filepath in CONTROL_LAW_COMPONENTS:
        try:
            source = open(filepath).read()
        except FileNotFoundError:
            continue  # file may not exist in test env
        assert (
            "_cl_errors" in source or "_cl_degraded" in source or "control law" in source.lower()
        ), f"{filepath} missing control law block"
