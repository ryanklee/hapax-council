"""Tests for ``agents.publication_bus.bridgy_publisher``."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from agents.publication_bus.bridgy_publisher import (
    BRIDGY_PUBLISH_ENDPOINT,
    BridgyPublisher,
)
from agents.publication_bus.publisher_kit.base import PublisherPayload


def _mock_response(status_code: int, text: str = "") -> MagicMock:
    response = MagicMock()
    response.status_code = status_code
    response.text = text
    return response


class TestBridgyPublisherSuccess:
    """200/201/202 status codes return ok=True."""

    @patch("agents.publication_bus.bridgy_publisher.requests")
    def test_201_returns_ok(self, mock_requests: MagicMock) -> None:
        mock_requests.post.return_value = _mock_response(201)
        pub = BridgyPublisher()
        result = pub.publish(
            PublisherPayload(
                target="https://hapax.omg.lol/weblog",
                text="https://hapax.omg.lol/weblog/2026-04-25-entry",
            )
        )
        assert result.ok
        assert "bridgy 201" in result.detail

    @patch("agents.publication_bus.bridgy_publisher.requests")
    def test_200_returns_ok(self, mock_requests: MagicMock) -> None:
        mock_requests.post.return_value = _mock_response(200)
        pub = BridgyPublisher()
        result = pub.publish(
            PublisherPayload(
                target="https://hapax.omg.lol/weblog",
                text="https://hapax.omg.lol/weblog/entry",
            )
        )
        assert result.ok

    @patch("agents.publication_bus.bridgy_publisher.requests")
    def test_202_returns_ok(self, mock_requests: MagicMock) -> None:
        mock_requests.post.return_value = _mock_response(202)
        pub = BridgyPublisher()
        result = pub.publish(
            PublisherPayload(
                target="https://hapax.omg.lol/weblog",
                text="https://hapax.omg.lol/weblog/entry",
            )
        )
        assert result.ok


class TestBridgyPublisherRefused:
    @patch("agents.publication_bus.bridgy_publisher.requests")
    def test_404_returns_refused(self, mock_requests: MagicMock) -> None:
        mock_requests.post.return_value = _mock_response(404, "not found")
        pub = BridgyPublisher()
        result = pub.publish(
            PublisherPayload(
                target="https://hapax.omg.lol/weblog",
                text="https://hapax.omg.lol/weblog/entry",
            )
        )
        assert result.refused
        assert "bridgy 404" in result.detail

    @patch("agents.publication_bus.bridgy_publisher.requests")
    def test_403_returns_refused(self, mock_requests: MagicMock) -> None:
        """403 = unauthorized source URL (operator hasn't OAuth'd Bridgy
        for this domain). Refused at publisher level."""
        mock_requests.post.return_value = _mock_response(403, "unauthorized")
        pub = BridgyPublisher()
        result = pub.publish(
            PublisherPayload(
                target="https://hapax.omg.lol/weblog",
                text="https://hapax.omg.lol/weblog/entry",
            )
        )
        assert result.refused

    def test_allowlist_violation_refuses_pre_emit(self) -> None:
        """Source URL not in DEFAULT_BRIDGY_ALLOWLIST refuses at the
        AllowlistGate before the POST goes out."""
        pub = BridgyPublisher()
        result = pub.publish(
            PublisherPayload(
                target="https://evil.example.com/post",  # not in allowlist
                text="https://hapax.omg.lol/weblog/entry",
            )
        )
        assert result.refused
        assert "allowlist" in result.detail.lower()


class TestBridgyPublisherErrors:
    @patch("agents.publication_bus.bridgy_publisher.requests")
    def test_500_returns_error(self, mock_requests: MagicMock) -> None:
        mock_requests.post.return_value = _mock_response(500, "server error")
        pub = BridgyPublisher()
        result = pub.publish(
            PublisherPayload(
                target="https://hapax.omg.lol/weblog",
                text="https://hapax.omg.lol/weblog/entry",
            )
        )
        assert result.error

    @patch("agents.publication_bus.bridgy_publisher.requests")
    def test_request_exception_returns_error(self, mock_requests: MagicMock) -> None:
        # Make the POST raise RequestException
        import requests as _requests_lib

        mock_requests.post.side_effect = _requests_lib.RequestException("connection error")
        # Set the RequestException class so isinstance check works in publisher
        mock_requests.RequestException = _requests_lib.RequestException
        pub = BridgyPublisher()
        result = pub.publish(
            PublisherPayload(
                target="https://hapax.omg.lol/weblog",
                text="https://hapax.omg.lol/weblog/entry",
            )
        )
        assert result.error
        assert "transport failure" in result.detail.lower()


class TestBridgyPublisherIntegration:
    @patch("agents.publication_bus.bridgy_publisher.requests")
    def test_post_uses_correct_endpoint(self, mock_requests: MagicMock) -> None:
        mock_requests.post.return_value = _mock_response(201)
        pub = BridgyPublisher()
        pub.publish(
            PublisherPayload(
                target="https://hapax.omg.lol/weblog",
                text="https://hapax.omg.lol/weblog/entry",
            )
        )
        # Verify the POST was made to the correct endpoint
        mock_requests.post.assert_called_once()
        call_args = mock_requests.post.call_args
        assert call_args[0][0] == BRIDGY_PUBLISH_ENDPOINT

    @patch("agents.publication_bus.bridgy_publisher.requests")
    def test_post_carries_source_and_target(self, mock_requests: MagicMock) -> None:
        mock_requests.post.return_value = _mock_response(201)
        pub = BridgyPublisher()
        pub.publish(
            PublisherPayload(
                target="https://hapax.omg.lol/weblog",
                text="https://hapax.omg.lol/weblog/specific-entry",
            )
        )
        call_args = mock_requests.post.call_args
        data = call_args.kwargs["data"]
        assert data["source"] == "https://hapax.omg.lol/weblog/specific-entry"
        assert data["target"] == "https://hapax.omg.lol/weblog"

    def test_subclass_has_correct_surface_name(self) -> None:
        assert BridgyPublisher.surface_name == "bridgy-webmention-publish"

    def test_allowlist_carries_omg_lol_entries(self) -> None:
        pub = BridgyPublisher()
        assert pub.allowlist.permits("https://hapax.omg.lol/weblog")
        assert pub.allowlist.permits("https://hapax.omg.lol/now")
        assert not pub.allowlist.permits("https://other.example.com/")
