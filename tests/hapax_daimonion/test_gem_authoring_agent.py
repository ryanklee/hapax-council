"""Tests for gem_authoring_agent + async_frames_for_impingement integration."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from pydantic import ValidationError

from agents.hapax_daimonion.gem_authoring_agent import (
    GEM_LLM_AUTHORING_ENV,
    MAX_FRAME_TEXT_CHARS,
    GemFramePayload,
    GemSequence,
    is_llm_authoring_enabled,
)
from agents.hapax_daimonion.gem_producer import async_frames_for_impingement
from shared.impingement import Impingement, ImpingementType

_SENTINEL: object = object()


def _make_imp(
    *,
    intent_family: str | None = "gem.emphasis.idea",
    content: dict | object = _SENTINEL,
) -> Impingement:
    if content is _SENTINEL:
        content = {"emphasis_text": "ACIDIC"}
    return Impingement(
        timestamp=1.0,
        source="test",
        type=ImpingementType.PATTERN_MATCH,
        strength=0.5,
        content=content,  # type: ignore[arg-type]
        intent_family=intent_family,
    )


# ── Env-flag gating ──────────────────────────────────────────────────────


def test_authoring_disabled_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(GEM_LLM_AUTHORING_ENV, raising=False)
    assert is_llm_authoring_enabled() is False


def test_authoring_enabled_when_flag_set(monkeypatch: pytest.MonkeyPatch) -> None:
    for v in ("1", "true", "yes", "on", "TRUE", "On"):
        monkeypatch.setenv(GEM_LLM_AUTHORING_ENV, v)
        assert is_llm_authoring_enabled() is True


def test_authoring_disabled_for_falsy_strings(monkeypatch: pytest.MonkeyPatch) -> None:
    for v in ("0", "false", "no", "off", "", "maybe"):
        monkeypatch.setenv(GEM_LLM_AUTHORING_ENV, v)
        assert is_llm_authoring_enabled() is False


# ── GemFramePayload validators ──────────────────────────────────────────


def test_payload_accepts_cp437_text() -> None:
    payload = GemFramePayload(text="┌─[ ACIDIC ]─┐", hold_ms=1500)
    assert payload.text == "┌─[ ACIDIC ]─┐"
    assert payload.hold_ms == 1500


def test_payload_default_hold_ms() -> None:
    assert GemFramePayload(text="x").hold_ms == 1500


def test_payload_rejects_emoji() -> None:
    with pytest.raises(ValidationError) as excinfo:
        GemFramePayload(text="hello 😀")
    assert "AntiPatternKind" in str(excinfo.value) or "emoji" in str(excinfo.value).lower()


def test_payload_rejects_empty_text() -> None:
    with pytest.raises(ValidationError):
        GemFramePayload(text="   ")


def test_payload_rejects_overlong_text() -> None:
    long = "x" * (MAX_FRAME_TEXT_CHARS + 1)
    with pytest.raises(ValidationError):
        GemFramePayload(text=long)


def test_payload_rejects_hold_ms_below_floor() -> None:
    with pytest.raises(ValidationError):
        GemFramePayload(text="x", hold_ms=50)


def test_payload_rejects_hold_ms_above_ceiling() -> None:
    with pytest.raises(ValidationError):
        GemFramePayload(text="x", hold_ms=10_000)


# ── GemSequence container ───────────────────────────────────────────────


def test_sequence_accepts_one_to_five_frames() -> None:
    seq = GemSequence(frames=[GemFramePayload(text="a")])
    assert len(seq.frames) == 1
    five = GemSequence(frames=[GemFramePayload(text=f"f{i}") for i in range(5)])
    assert len(five.frames) == 5


def test_sequence_rejects_zero_frames() -> None:
    with pytest.raises(ValidationError):
        GemSequence(frames=[])


def test_sequence_rejects_more_than_five_frames() -> None:
    with pytest.raises(ValidationError):
        GemSequence(frames=[GemFramePayload(text=f"f{i}") for i in range(6)])


# ── async_frames_for_impingement integration ────────────────────────────


@pytest.mark.asyncio
async def test_async_path_falls_back_to_template_when_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(GEM_LLM_AUTHORING_ENV, raising=False)
    imp = _make_imp(content={"emphasis_text": "ACIDIC"})
    frames = await async_frames_for_impingement(imp)
    # Template path produces 3 frames for emphasis
    assert len(frames) == 3
    assert "ACIDIC" in frames[1].text


@pytest.mark.asyncio
async def test_async_path_uses_llm_when_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(GEM_LLM_AUTHORING_ENV, "1")
    imp = _make_imp(content={"emphasis_text": "ACIDIC"})

    async def fake_author(imp_arg, narrative):
        return GemSequence(
            frames=[
                GemFramePayload(text="» llm one «", hold_ms=400),
                GemFramePayload(text="» llm two «", hold_ms=600),
            ]
        )

    with patch("agents.hapax_daimonion.gem_authoring_agent.author_sequence", new=fake_author):
        frames = await async_frames_for_impingement(imp)

    assert len(frames) == 2
    assert frames[0].text == "» llm one «"
    assert frames[0].hold_ms == 400
    assert frames[1].text == "» llm two «"


@pytest.mark.asyncio
async def test_async_path_falls_back_when_llm_returns_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(GEM_LLM_AUTHORING_ENV, "1")
    imp = _make_imp(content={"emphasis_text": "ACIDIC"})

    async def fake_author(imp_arg, narrative):
        return None  # simulates LLM call failure

    with patch("agents.hapax_daimonion.gem_authoring_agent.author_sequence", new=fake_author):
        frames = await async_frames_for_impingement(imp)

    # Falls back to 3-frame emphasis template
    assert len(frames) == 3
    assert "ACIDIC" in frames[1].text


@pytest.mark.asyncio
async def test_async_path_rejects_non_gem_intent() -> None:
    imp = _make_imp(intent_family="ward.highlight.token_pole")
    assert await async_frames_for_impingement(imp) == []


@pytest.mark.asyncio
async def test_async_path_rejects_empty_text() -> None:
    imp = _make_imp(content={})
    assert await async_frames_for_impingement(imp) == []
