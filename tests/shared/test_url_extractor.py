"""Tests for shared/url_extractor.py — Phase 1 of YouTube broadcast bundle."""

from __future__ import annotations

import pytest  # noqa: TC002

from shared.url_extractor import classify_url, extract_urls


class TestExtractUrls:
    def test_bare_url(self) -> None:
        assert extract_urls("check this https://example.com/path") == ["https://example.com/path"]

    def test_multiple_urls(self) -> None:
        text = "first https://a.com/x and second https://b.com/y"
        assert extract_urls(text) == ["https://a.com/x", "https://b.com/y"]

    def test_dedup_preserves_first_seen_order(self) -> None:
        text = "https://a.com/x ... https://b.com/y ... https://a.com/x again"
        assert extract_urls(text) == ["https://a.com/x", "https://b.com/y"]

    def test_strips_trailing_punctuation(self) -> None:
        assert extract_urls("see https://a.com/x.") == ["https://a.com/x"]
        assert extract_urls("see https://a.com/x,") == ["https://a.com/x"]
        assert extract_urls("see https://a.com/x?") == ["https://a.com/x"]
        assert extract_urls("(see https://a.com/x)") == ["https://a.com/x"]

    def test_markdown_link_extracted(self) -> None:
        # Bracketed URLs — the URL inside (...) gets extracted
        result = extract_urls("[click here](https://a.com/x) please")
        assert "https://a.com/x" in result

    def test_no_urls_returns_empty(self) -> None:
        assert extract_urls("just some text without links") == []

    def test_http_only_too_short_skipped(self) -> None:
        # "https://" alone is too short to be useful
        assert extract_urls("see https://") == []

    def test_case_preserved_in_path(self) -> None:
        urls = extract_urls("https://Example.com/MyPath")
        # We don't lowercase the URL itself (only the regex is case-i)
        assert urls == ["https://Example.com/MyPath"]


class TestClassifyUrl:
    @pytest.mark.parametrize(
        "url,expected",
        [
            ("https://doi.org/10.1234/abcd", "doi"),
            ("https://dx.doi.org/10.1234/abcd", "doi"),
            ("https://github.com/foo/bar", "github"),
            ("https://gist.github.com/foo/abc", "github"),
            ("https://twitter.com/user/status/123", "tweet"),
            ("https://x.com/user/status/123", "tweet"),
            ("https://www.youtube.com/watch?v=abc", "youtube"),
            ("https://youtu.be/abc", "youtube"),
            ("https://en.wikipedia.org/wiki/Foo", "wikipedia"),
            ("https://commons.wikimedia.org/wiki/Bar", "wikipedia"),
            ("https://artist.bandcamp.com/album/x", "album-ref"),
            ("https://soundcloud.com/user/track", "album-ref"),
            ("https://open.spotify.com/track/abc", "album-ref"),
            ("https://www.discogs.com/release/123", "album-ref"),
            ("https://www.nature.com/articles/123", "citation"),
            ("https://arxiv.org/abs/2024.01234", "citation"),
            ("https://www.sciencedirect.com/science/article/pii/abc", "citation"),
            ("https://example.com/random", "other"),
            ("https://news.ycombinator.com/item?id=1", "other"),
        ],
    )
    def test_classification(self, url: str, expected: str) -> None:
        assert classify_url(url) == expected

    def test_invalid_url_returns_other(self) -> None:
        assert classify_url("not a url") == "other"

    def test_no_scheme_returns_other(self) -> None:
        assert classify_url("example.com/path") == "other"


class TestEndToEnd:
    """Common chat-message shapes."""

    def test_realistic_chat_message_with_one_url(self) -> None:
        msg = "the paper is at https://nature.com/articles/abc123 — really good"
        urls = extract_urls(msg)
        assert urls == ["https://nature.com/articles/abc123"]
        assert classify_url(urls[0]) == "citation"

    def test_realistic_chat_with_album_ref_and_tweet(self) -> None:
        msg = (
            "track is https://artist.bandcamp.com/track/x and the artist "
            "tweeted about it https://twitter.com/artist/status/999"
        )
        urls = extract_urls(msg)
        kinds = [classify_url(u) for u in urls]
        assert "album-ref" in kinds
        assert "tweet" in kinds

    def test_message_with_no_urls(self) -> None:
        assert extract_urls("just chatting nothing linkable") == []


# ── B2 / L#27 — extended YouTube URL coverage ──────────────────────────


class TestYouTubeUrlForms:
    """Pin the URL forms operators paste in chat. Audit Low #27 flagged
    that the extractor was tested against only watch?v=… and youtu.be
    forms, missing shorts/live/m./music. + tracking-param obfuscation."""

    @pytest.mark.parametrize(
        "url",
        [
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "https://youtube.com/watch?v=dQw4w9WgXcQ",
            "https://m.youtube.com/watch?v=dQw4w9WgXcQ",
            "https://music.youtube.com/watch?v=dQw4w9WgXcQ",
            "https://youtu.be/dQw4w9WgXcQ",
            "https://www.youtube.com/shorts/abc123def",
            "https://youtube.com/shorts/abc123def",
            "https://www.youtube.com/live/dQw4w9WgXcQ",
            "https://youtube.com/live/dQw4w9WgXcQ",
            # Embed URLs (sometimes pasted from channel-page sources)
            "https://www.youtube.com/embed/dQw4w9WgXcQ",
            # Channel + playlist URLs (operators sometimes share the
            # source channel rather than a single video)
            "https://www.youtube.com/@SomeChannel",
            "https://www.youtube.com/playlist?list=PLabc",
        ],
    )
    def test_youtube_form_classifies_as_youtube(self, url: str) -> None:
        """Every YouTube URL form a chat author might paste classifies
        as `youtube` — not `other`. Subdomain (m./music./www.) +
        path variant (watch/shorts/live/embed/@channel/playlist) all
        route through the same kind label."""
        assert classify_url(url) == "youtube", f"misclassified: {url}"

    @pytest.mark.parametrize(
        "url",
        [
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=42s",
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ&list=PLabc&index=3",
            "https://youtu.be/dQw4w9WgXcQ?si=Tr4ckin9P4r4m",
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ#t=1m23s",
            # UTM tracking — sometimes appended by share dialogs
            ("https://www.youtube.com/watch?v=dQw4w9WgXcQ&utm_source=email&utm_medium=share"),
        ],
    )
    def test_youtube_obfuscated_with_tracking_params(self, url: str) -> None:
        """Tracking-param obfuscation (?si=, &utm_*=, &t=, #t=) does NOT
        change the classification — these are still YouTube videos."""
        extracted = extract_urls(f"check this {url} now")
        assert url in extracted, f"extractor dropped param-laden URL: {url}"
        assert classify_url(url) == "youtube"

    def test_youtube_url_in_markdown_link(self) -> None:
        """Operators sometimes paste markdown — the URL must come out
        clean (no leading [, no trailing ))."""
        msg = "watch [this](https://www.youtube.com/shorts/abc123)"
        extracted = extract_urls(msg)
        assert "https://www.youtube.com/shorts/abc123" in extracted

    def test_youtube_url_with_trailing_punctuation(self) -> None:
        """Common chat-end punctuation must be stripped without
        collapsing into the URL."""
        for trailer in (".", ",", "!", "?", ")", '"'):
            msg = f"see https://youtu.be/abc{trailer}"
            extracted = extract_urls(msg)
            assert "https://youtu.be/abc" in extracted, f"trailing {trailer!r} broke extraction"

    def test_multiple_youtube_forms_coexist(self) -> None:
        msg = (
            "old: https://www.youtube.com/watch?v=aaa "
            "short: https://youtube.com/shorts/bbb "
            "live: https://www.youtube.com/live/ccc "
            "share: https://youtu.be/ddd?si=xxx"
        )
        extracted = extract_urls(msg)
        kinds = {classify_url(u) for u in extracted}
        assert kinds == {"youtube"}
        assert len(extracted) == 4
