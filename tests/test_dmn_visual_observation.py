"""Tests for multimodal visual observation (reverberation feedback loop)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture
def tmp_frame(tmp_path: Path) -> Path:
    """Create a minimal JPEG file for testing."""
    jpeg_bytes = bytes(
        [
            0xFF,
            0xD8,
            0xFF,
            0xE0,
            0x00,
            0x10,
            0x4A,
            0x46,
            0x49,
            0x46,
            0x00,
            0x01,
            0x01,
            0x00,
            0x00,
            0x01,
            0x00,
            0x01,
            0x00,
            0x00,
            0xFF,
            0xD9,
        ]
    )
    p = tmp_path / "frame.jpg"
    p.write_bytes(jpeg_bytes)
    return p


async def test_visual_observation_sends_image_to_gemini(tmp_frame):
    """The visual observation function must send the actual JPEG to gemini-flash."""
    from agents.dmn.vision import _generate_visual_observation

    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "A dark swirling pattern with blue noise"

    with patch("agents.dmn.vision._get_vision_client") as mock_get_client:
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_get_client.return_value = mock_client

        result = await _generate_visual_observation(str(tmp_frame), "abstract noise field")

    assert result == "A dark swirling pattern with blue noise"
    call_args = mock_client.chat.completions.create.call_args
    assert call_args.kwargs["model"] == "gemini-flash"
    user_content = call_args.kwargs["messages"][1]["content"]
    image_parts = [p for p in user_content if p.get("type") == "image_url"]
    assert len(image_parts) == 1
    assert image_parts[0]["image_url"]["url"].startswith("data:image/jpeg;base64,")


async def test_visual_observation_returns_empty_on_missing_frame(tmp_path):
    """Must return empty string when frame doesn't exist."""
    from agents.dmn.vision import _generate_visual_observation

    result = await _generate_visual_observation(str(tmp_path / "nonexistent.jpg"), "test")
    assert result == ""


async def test_visual_observation_returns_empty_on_api_failure(tmp_frame):
    """Must return empty string on API failure, not raise."""
    from agents.dmn.vision import _generate_visual_observation

    with patch("agents.dmn.vision._get_vision_client") as mock_get_client:
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(side_effect=Exception("API down"))
        mock_get_client.return_value = mock_client

        result = await _generate_visual_observation(str(tmp_frame), "test")

    assert result == ""
