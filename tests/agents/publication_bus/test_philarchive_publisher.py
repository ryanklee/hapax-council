"""Tests for ``agents.publication_bus.philarchive_publisher``."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from agents.publication_bus.philarchive_publisher import (
    PHILARCHIVE_DEPOSIT_ENDPOINT,
    PHILARCHIVE_SURFACE,
    PhilArchivePublisher,
)
from agents.publication_bus.publisher_kit import PublisherPayload
from agents.publication_bus.publisher_kit.allowlist import load_allowlist


def _mock_response(status_code: int, text: str = "") -> MagicMock:
    response = MagicMock()
    response.status_code = status_code
    response.text = text
    return response


class TestSurfaceMetadata:
    def test_surface_name_is_philarchive_deposit(self) -> None:
        assert PhilArchivePublisher.surface_name == PHILARCHIVE_SURFACE
        assert PHILARCHIVE_SURFACE == "philarchive-deposit"

    def test_requires_legal_name(self) -> None:
        # PhilArchive author field uses formal name per cc-task spec
        assert PhilArchivePublisher.requires_legal_name is True


class TestPublisher:
    @patch("agents.publication_bus.philarchive_publisher.requests")
    def test_emit_posts_to_philarchive_deposit_endpoint(self, mock_requests: MagicMock) -> None:
        mock_requests.post.return_value = _mock_response(
            200, text='{"id": "PHIL-2026-001", "url": "https://philarchive.org/rec/PHIL-2026-001"}'
        )
        PhilArchivePublisher.allowlist = load_allowlist(
            PHILARCHIVE_SURFACE, ["constitutional-brief-2026"]
        )
        publisher = PhilArchivePublisher(
            session_cookie="session=abc123",
            author_id="kleeberger-r",
        )
        result = publisher.publish(
            PublisherPayload(
                target="constitutional-brief-2026",
                text="Constitutional Brief body.",
                metadata={"title": "Hapax Constitutional Brief"},
            )
        )
        assert result.ok is True
        url = mock_requests.post.call_args[0][0]
        assert url.startswith(PHILARCHIVE_DEPOSIT_ENDPOINT)

    @patch("agents.publication_bus.philarchive_publisher.requests")
    def test_201_returns_ok(self, mock_requests: MagicMock) -> None:
        mock_requests.post.return_value = _mock_response(201, text='{"id": "x"}')
        PhilArchivePublisher.allowlist = load_allowlist(PHILARCHIVE_SURFACE, ["item-1"])
        publisher = PhilArchivePublisher(session_cookie="c", author_id="a")
        result = publisher.publish(PublisherPayload(target="item-1", text="body"))
        assert result.ok is True

    @patch("agents.publication_bus.philarchive_publisher.requests")
    def test_401_returns_error(self, mock_requests: MagicMock) -> None:
        mock_requests.post.return_value = _mock_response(401, text="unauthorized")
        PhilArchivePublisher.allowlist = load_allowlist(PHILARCHIVE_SURFACE, ["item-1"])
        publisher = PhilArchivePublisher(session_cookie="bad", author_id="a")
        result = publisher.publish(PublisherPayload(target="item-1", text="body"))
        assert result.error is True

    @patch("agents.publication_bus.philarchive_publisher.requests")
    def test_403_returns_error(self, mock_requests: MagicMock) -> None:
        mock_requests.post.return_value = _mock_response(403, text="forbidden")
        PhilArchivePublisher.allowlist = load_allowlist(PHILARCHIVE_SURFACE, ["item-1"])
        publisher = PhilArchivePublisher(session_cookie="c", author_id="a")
        result = publisher.publish(PublisherPayload(target="item-1", text="body"))
        assert result.error is True

    @patch("agents.publication_bus.philarchive_publisher.requests")
    def test_5xx_returns_error(self, mock_requests: MagicMock) -> None:
        mock_requests.post.return_value = _mock_response(503, text="server error")
        PhilArchivePublisher.allowlist = load_allowlist(PHILARCHIVE_SURFACE, ["item-1"])
        publisher = PhilArchivePublisher(session_cookie="c", author_id="a")
        result = publisher.publish(PublisherPayload(target="item-1", text="body"))
        assert result.error is True

    def test_missing_session_cookie_returns_refused(self) -> None:
        PhilArchivePublisher.allowlist = load_allowlist(PHILARCHIVE_SURFACE, ["item-1"])
        publisher = PhilArchivePublisher(session_cookie="", author_id="a")
        result = publisher.publish(PublisherPayload(target="item-1", text="body"))
        assert result.refused is True
        assert "credential" in result.detail.lower() or "cookie" in result.detail.lower()

    def test_missing_author_id_returns_refused(self) -> None:
        PhilArchivePublisher.allowlist = load_allowlist(PHILARCHIVE_SURFACE, ["item-1"])
        publisher = PhilArchivePublisher(session_cookie="c", author_id="")
        result = publisher.publish(PublisherPayload(target="item-1", text="body"))
        assert result.refused is True

    def test_allowlist_deny_short_circuits(self) -> None:
        PhilArchivePublisher.allowlist = load_allowlist(PHILARCHIVE_SURFACE, [])
        publisher = PhilArchivePublisher(session_cookie="c", author_id="a")
        result = publisher.publish(PublisherPayload(target="item-1", text="body"))
        assert result.refused is True

    @patch("agents.publication_bus.philarchive_publisher.requests")
    def test_request_exception_returns_error(self, mock_requests: MagicMock) -> None:
        import requests as _requests_lib

        mock_requests.post.side_effect = _requests_lib.RequestException("offline")
        mock_requests.RequestException = _requests_lib.RequestException
        PhilArchivePublisher.allowlist = load_allowlist(PHILARCHIVE_SURFACE, ["item-1"])
        publisher = PhilArchivePublisher(session_cookie="c", author_id="a")
        result = publisher.publish(PublisherPayload(target="item-1", text="body"))
        assert result.error is True

    @patch("agents.publication_bus.philarchive_publisher.requests")
    def test_session_cookie_in_headers(self, mock_requests: MagicMock) -> None:
        mock_requests.post.return_value = _mock_response(200)
        PhilArchivePublisher.allowlist = load_allowlist(PHILARCHIVE_SURFACE, ["item-1"])
        publisher = PhilArchivePublisher(session_cookie="phpsess=mysession", author_id="a")
        publisher.publish(PublisherPayload(target="item-1", text="body"))
        kwargs = mock_requests.post.call_args.kwargs
        # PhilArchive session cookie sent as Cookie header
        cookies = kwargs.get("cookies") or {}
        headers = kwargs.get("headers") or {}
        cookie_present = (
            "phpsess=mysession" in (cookies.values() if isinstance(cookies, dict) else [])
            or "phpsess=mysession" in (headers.get("Cookie") or "")
            or any("phpsess=mysession" in str(v) for v in cookies.values())
            if isinstance(cookies, dict)
            else False
        )
        assert cookie_present or headers.get("Cookie") == "phpsess=mysession"

    @patch("agents.publication_bus.philarchive_publisher.requests")
    def test_payload_includes_author_id(self, mock_requests: MagicMock) -> None:
        mock_requests.post.return_value = _mock_response(200)
        PhilArchivePublisher.allowlist = load_allowlist(PHILARCHIVE_SURFACE, ["item-1"])
        publisher = PhilArchivePublisher(session_cookie="c", author_id="kleeberger-r")
        publisher.publish(
            PublisherPayload(
                target="item-1",
                text="abstract body",
                metadata={"title": "T"},
            )
        )
        kwargs = mock_requests.post.call_args.kwargs
        data = kwargs.get("data") or kwargs.get("json") or {}
        # Author ID surfaces in the deposit payload
        flat = str(data)
        assert "kleeberger-r" in flat


class TestParseDepositResponse:
    def test_parses_id_from_json_response(self) -> None:
        from agents.publication_bus.philarchive_publisher import _parse_deposit_id

        json_body = '{"id": "PHIL-2026-007", "url": "https://philarchive.org/rec/PHIL-2026-007"}'
        assert _parse_deposit_id(json_body) == "PHIL-2026-007"

    def test_returns_none_when_response_unparseable(self) -> None:
        from agents.publication_bus.philarchive_publisher import _parse_deposit_id

        assert _parse_deposit_id("plain html with no id") is None

    def test_parses_id_from_html_fallback(self) -> None:
        from agents.publication_bus.philarchive_publisher import _parse_deposit_id

        html = '<html><body>Deposited as <a href="/rec/HUI-2026-005">HUI-2026-005</a></body></html>'
        assert _parse_deposit_id(html) == "HUI-2026-005"
