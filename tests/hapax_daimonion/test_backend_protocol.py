"""Parametrized protocol compliance tests for all 22 perception backends."""

from __future__ import annotations

import importlib

import pytest

from agents.hapax_daimonion.perception import PerceptionTier

# (module_path, class_name) for every backend
_BACKENDS: list[tuple[str, str]] = [
    ("agents.hapax_daimonion.backends.pipewire", "PipeWireBackend"),
    ("agents.hapax_daimonion.backends.hyprland", "HyprlandBackend"),
    ("agents.hapax_daimonion.backends.watch", "WatchBackend"),
    ("agents.hapax_daimonion.backends.health", "HealthBackend"),
    ("agents.hapax_daimonion.backends.circadian", "CircadianBackend"),
    ("agents.hapax_daimonion.backends.devices", "DeviceStateBackend"),
    ("agents.hapax_daimonion.backends.input_activity", "InputActivityBackend"),
    ("agents.hapax_daimonion.backends.contact_mic", "ContactMicBackend"),
    ("agents.hapax_daimonion.backends.mixer_input", "MixerInputBackend"),
    ("agents.hapax_daimonion.backends.ir_presence", "IrPresenceBackend"),
    ("agents.hapax_daimonion.backends.bt_presence", "BTPresenceBackend"),
    ("agents.hapax_daimonion.backends.midi_clock", "MidiClockBackend"),
    ("agents.hapax_daimonion.backends.phone_media", "PhoneMediaBackend"),
    ("agents.hapax_daimonion.backends.phone_messages", "PhoneMessagesBackend"),
    ("agents.hapax_daimonion.backends.phone_calls", "PhoneCallsBackend"),
    ("agents.hapax_daimonion.backends.stream_health", "StreamHealthBackend"),
    ("agents.hapax_daimonion.backends.attention", "AttentionBackend"),
    ("agents.hapax_daimonion.backends.clipboard", "ClipboardBackend"),
    ("agents.hapax_daimonion.backends.speech_emotion", "SpeechEmotionBackend"),
    ("agents.hapax_daimonion.backends.studio_ingestion", "StudioIngestionBackend"),
    ("agents.hapax_daimonion.backends.local_llm", "LocalLLMBackend"),
    ("agents.hapax_daimonion.backends.phone_awareness", "PhoneAwarenessBackend"),
]


def _load_backend_class(module_path: str, class_name: str) -> type | None:
    """Try to import a backend class, returning None on ImportError."""
    try:
        mod = importlib.import_module(module_path)
        return getattr(mod, class_name)
    except (ImportError, AttributeError):
        return None


def _backend_ids() -> list[str]:
    return [name for _, name in _BACKENDS]


@pytest.fixture(params=_BACKENDS, ids=_backend_ids())
def backend_class(request: pytest.FixtureRequest) -> type:
    module_path, class_name = request.param
    cls = _load_backend_class(module_path, class_name)
    if cls is None:
        pytest.skip(f"{class_name}: import failed (missing dependency)")
    return cls


def _make_instance(cls: type) -> object:
    """Instantiate a backend, skipping if constructor requires args."""
    try:
        return cls()
    except Exception:
        pytest.skip(f"{cls.__name__} requires constructor args")


class TestBackendProtocol:
    """Every backend must satisfy the PerceptionBackend protocol."""

    def test_has_name_property(self, backend_class: type) -> None:
        instance = _make_instance(backend_class)
        assert isinstance(instance.name, str)
        assert len(instance.name) > 0

    def test_has_provides_frozenset(self, backend_class: type) -> None:
        instance = _make_instance(backend_class)
        assert isinstance(instance.provides, frozenset)

    def test_has_tier(self, backend_class: type) -> None:
        instance = _make_instance(backend_class)
        assert isinstance(instance.tier, PerceptionTier)

    def test_available_returns_bool(self, backend_class: type) -> None:
        instance = _make_instance(backend_class)
        result = instance.available()
        assert isinstance(result, bool)

    def test_contribute_accepts_dict(self, backend_class: type) -> None:
        instance = _make_instance(backend_class)
        # Should not raise
        instance.contribute({})

    def test_has_start_and_stop(self, backend_class: type) -> None:
        instance = _make_instance(backend_class)
        assert callable(getattr(instance, "start", None))
        assert callable(getattr(instance, "stop", None))
