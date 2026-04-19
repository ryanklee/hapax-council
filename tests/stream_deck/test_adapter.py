"""Tests for agents.stream_deck.adapter (task #140, Phase 1)."""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path

import pytest
from pydantic import ValidationError

from agents.stream_deck import (
    DispatchResult,
    StreamDeckAdapter,
    StreamDeckManifest,
    StreamDeckManifestError,
    load_manifest,
)
from agents.stream_deck.adapter import websocket_dispatcher

REPO_ROOT = Path(__file__).resolve().parents[2]
SHIPPED_MANIFEST = REPO_ROOT / "config" / "stream-deck" / "manifest.yaml"


class _RecordingDispatcher:
    """Async callable that records every call for later inspection."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []

    async def __call__(self, command: str, args: dict) -> None:
        self.calls.append((command, dict(args)))


class _RaisingDispatcher:
    """Async callable that always raises — for error-handling tests."""

    def __init__(self, exc: Exception) -> None:
        self._exc = exc

    async def __call__(self, command: str, args: dict) -> None:
        raise self._exc


def _manifest_dict(keys: list[dict] | None = None, device: str = "mini") -> dict:
    if keys is None:
        keys = [{"slot": 0, "command": "noop"}]
    return {"version": 1, "device": device, "keys": keys}


# ── Manifest loading + validation ───────────────────────────────────────────


class TestManifestLoad:
    def test_shipped_manifest_parses(self):
        manifest = load_manifest(SHIPPED_MANIFEST)
        assert isinstance(manifest, StreamDeckManifest)
        assert manifest.device == "mini"
        assert manifest.slot_count() == 15

    def test_shipped_manifest_has_15_unique_slots(self):
        manifest = load_manifest(SHIPPED_MANIFEST)
        assert len(manifest.keys) == 15
        slots = [k.slot for k in manifest.keys]
        assert sorted(slots) == list(range(15))
        # No duplicate slot got past the validator.
        assert len(set(slots)) == 15

    def test_shipped_manifest_slot_3_is_hero_clear(self):
        manifest = load_manifest(SHIPPED_MANIFEST)
        key = manifest.for_slot(3)
        assert key is not None
        assert key.command == "studio.hero.clear"
        assert key.label == "HERO/CLEAR"

    def test_shipped_manifest_has_expected_commands(self):
        """Smoke-check the spec'd command coverage: hero, vinyl, fx, mode, homage, degraded."""
        manifest = load_manifest(SHIPPED_MANIFEST)
        commands = {k.command for k in manifest.keys}
        expected = {
            "studio.hero.set",
            "studio.hero.clear",
            "audio.vinyl.rate_preset",
            "fx.chain.set",
            "mode.set",
            "homage.ward.next",
            "homage.rotation.pause",
            "homage.rotation.resume",
            "degraded.activate",
        }
        assert expected.issubset(commands)

    def test_missing_file_raises(self, tmp_path: Path):
        with pytest.raises(StreamDeckManifestError, match="manifest not found"):
            load_manifest(tmp_path / "nope.yaml")

    def test_malformed_yaml_raises(self, tmp_path: Path):
        p = tmp_path / "broken.yaml"
        p.write_text("version: 1\ndevice: mini\nkeys:\n  - slot: [unterminated", encoding="utf-8")
        with pytest.raises(StreamDeckManifestError):
            load_manifest(p)

    def test_non_mapping_root_raises(self, tmp_path: Path):
        p = tmp_path / "list.yaml"
        p.write_text("- just a list\n- not a mapping\n", encoding="utf-8")
        with pytest.raises(StreamDeckManifestError, match="root must be a mapping"):
            load_manifest(p)


class TestManifestValidation:
    """Validation failures surface via pydantic.ValidationError directly when
    ``model_validate`` is called; ``load_manifest`` wraps them in
    ``StreamDeckManifestError`` for the service entrypoint."""

    def test_duplicate_slot_rejected(self):
        raw = _manifest_dict(
            [
                {"slot": 0, "command": "a"},
                {"slot": 0, "command": "b"},
            ]
        )
        with pytest.raises(ValidationError, match="duplicate slot 0"):
            StreamDeckManifest.model_validate(raw)

    def test_mini_slot_out_of_range_rejected(self):
        raw = _manifest_dict([{"slot": 15, "command": "a"}])
        with pytest.raises(ValidationError, match="out of range"):
            StreamDeckManifest.model_validate(raw)

    def test_negative_slot_rejected(self):
        raw = _manifest_dict([{"slot": -1, "command": "a"}])
        with pytest.raises(ValidationError):
            StreamDeckManifest.model_validate(raw)

    def test_unknown_device_rejected(self):
        raw = _manifest_dict(device="jumbotron")
        with pytest.raises(ValidationError, match="unknown device"):
            StreamDeckManifest.model_validate(raw)

    def test_empty_command_rejected(self):
        raw = _manifest_dict([{"slot": 0, "command": ""}])
        with pytest.raises(ValidationError):
            StreamDeckManifest.model_validate(raw)

    def test_load_manifest_wraps_validation_errors(self, tmp_path: Path):
        import yaml as _yaml

        p = tmp_path / "dup.yaml"
        p.write_text(
            _yaml.safe_dump(
                _manifest_dict(
                    [
                        {"slot": 0, "command": "a"},
                        {"slot": 0, "command": "b"},
                    ]
                )
            ),
            encoding="utf-8",
        )
        with pytest.raises(StreamDeckManifestError, match="validation failed"):
            load_manifest(p)


# ── Adapter routing ─────────────────────────────────────────────────────────


class TestAdapterRouting:
    def _build(self, dispatcher, *, keys: list[dict] | None = None) -> StreamDeckAdapter:
        manifest = StreamDeckManifest.model_validate(_manifest_dict(keys))
        return StreamDeckAdapter(manifest, dispatcher)

    def test_press_slot_3_dispatches_hero_clear(self):
        dispatcher = _RecordingDispatcher()
        manifest = load_manifest(SHIPPED_MANIFEST)
        adapter = StreamDeckAdapter(manifest, dispatcher)

        result = adapter.on_key_press(3)

        assert result.status == "dispatched"
        assert result.command == "studio.hero.clear"
        assert result.args == {}
        assert dispatcher.calls == [("studio.hero.clear", {})]

    def test_press_slot_0_dispatches_with_args(self):
        dispatcher = _RecordingDispatcher()
        manifest = load_manifest(SHIPPED_MANIFEST)
        adapter = StreamDeckAdapter(manifest, dispatcher)

        adapter.on_key_press(0)

        assert dispatcher.calls == [
            ("studio.hero.set", {"camera_role": "brio-operator"}),
        ]

    def test_unknown_slot_logs_and_drops(self, caplog: pytest.LogCaptureFixture):
        dispatcher = _RecordingDispatcher()
        adapter = self._build(dispatcher, keys=[{"slot": 0, "command": "only-one"}])

        with caplog.at_level(logging.INFO, logger="agents.stream_deck.adapter"):
            result = adapter.on_key_press(7)

        assert result.status == "unknown-slot"
        assert result.command is None
        assert dispatcher.calls == []
        assert any("slot 7 has no binding" in r.message for r in caplog.records)

    def test_out_of_range_slot_bounds_checked(self, caplog: pytest.LogCaptureFixture):
        dispatcher = _RecordingDispatcher()
        adapter = self._build(dispatcher, keys=[{"slot": 0, "command": "x"}])

        with caplog.at_level(logging.WARNING, logger="agents.stream_deck.adapter"):
            hi = adapter.on_key_press(15)  # Mini has slots 0..14
            lo = adapter.on_key_press(-1)

        assert hi.status == "out-of-range"
        assert lo.status == "out-of-range"
        assert dispatcher.calls == []
        assert sum("out of range" in r.message for r in caplog.records) == 2

    def test_dispatch_error_is_logged_not_propagated(self, caplog: pytest.LogCaptureFixture):
        dispatcher = _RaisingDispatcher(RuntimeError("relay down"))
        adapter = self._build(dispatcher, keys=[{"slot": 0, "command": "x"}])

        with caplog.at_level(logging.ERROR, logger="agents.stream_deck.adapter"):
            result = adapter.on_key_press(0)

        assert result.status == "error"
        assert result.error == "relay down"
        assert any("dispatch error" in r.message for r in caplog.records)

    def test_events_log_records_every_press(self):
        dispatcher = _RecordingDispatcher()
        adapter = self._build(
            dispatcher,
            keys=[
                {"slot": 0, "command": "a"},
                {"slot": 1, "command": "b"},
            ],
        )

        adapter.on_key_press(0)
        adapter.on_key_press(1)
        adapter.on_key_press(99)  # out-of-range — still recorded.

        statuses = [e.status for e in adapter.events]
        assert statuses == ["dispatched", "dispatched", "out-of-range"]

    def test_args_copied_on_dispatch(self):
        dispatcher = _RecordingDispatcher()
        adapter = self._build(dispatcher, keys=[{"slot": 0, "command": "x", "args": {"n": 1}}])

        adapter.on_key_press(0)
        # Mutating the dispatched arg dict must not leak into a second press.
        dispatcher.calls[0][1]["n"] = 999
        adapter.on_key_press(0)

        assert dispatcher.calls[1][1] == {"n": 1}


# ── WebSocket dispatcher ────────────────────────────────────────────────────


class TestWebsocketDispatcher:
    def test_posts_execute_frame(self):
        sent: list[str] = []
        closed: list[bool] = []

        class FakeWS:
            async def send(self, msg: str) -> None:
                sent.append(msg)

            async def __aenter__(self):
                return self

            async def __aexit__(self, *exc):
                closed.append(True)
                return None

        class FakeConnect:
            """Mirrors websockets.connect — awaitable and async context manager."""

            def __init__(self, ws: FakeWS) -> None:
                self._ws = ws

            def __await__(self):
                async def _inner():
                    return self._ws

                return _inner().__await__()

            async def __aenter__(self):
                return self._ws

            async def __aexit__(self, *exc):
                closed.append(True)
                return None

        def fake_connect(url: str):  # noqa: ARG001 — signature mirrors websockets.connect
            return FakeConnect(FakeWS())

        asyncio.run(
            websocket_dispatcher(
                "studio.hero.set",
                {"camera_role": "brio-operator"},
                url="ws://test/relay",
                connect=fake_connect,
            )
        )
        assert len(sent) == 1
        payload = json.loads(sent[0])
        assert payload == {
            "type": "execute",
            "command": "studio.hero.set",
            "args": {"camera_role": "brio-operator"},
        }
        assert closed == [True]


# ── DispatchResult shape ────────────────────────────────────────────────────


class TestDispatchResult:
    def test_defaults(self):
        r = DispatchResult(slot=0, command="x", status="dispatched")
        assert r.args == {}
        assert r.label == ""
        assert r.error is None
