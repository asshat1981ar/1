"""
Tests for mcp_server.harvester.crawler module.
Covers: HTTP cache expiry, --no-cache wiring, stale purge, DB-backed HttpCache.
"""

from __future__ import annotations

import time
from unittest.mock import MagicMock, patch

import pytest


class TestHttpCacheModel:
    """Tests for the HttpCache DB model and table."""

    def test_http_cache_table_exists_in_db(self):
        """The http_cache table should exist in the database schema."""
        from mcp_server.database import Base

        table_names = set(Base.metadata.tables.keys())
        assert "http_cache" in table_names, f"http_cache table not found. Available: {table_names}"

    def test_http_cache_columns(self):
        """http_cache table should have the required columns."""
        from mcp_server.database import Base

        table = Base.metadata.tables["http_cache"]
        col_names = {c.name for c in table.columns}
        required = {"url", "content", "etag", "last_modified", "expires_at", "cached_at"}
        missing = required - col_names
        assert not missing, f"http_cache missing columns: {missing}"

    def test_http_cache_url_is_primary_key(self):
        """url column should be the primary key."""
        from mcp_server.database import Base

        table = Base.metadata.tables["http_cache"]
        pk = table.primary_key.columns
        assert len(pk) == 1
        assert pk[0].name == "url"

    def test_http_cache_record_roundtrip(self):
        """Can insert and retrieve an http_cache record."""
        from mcp_server.database import Base
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker

        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine, expire_on_commit=False)

        from mcp_server.harvester.crawler import HttpCache

        now = time.time()
        with Session() as s:
            record = HttpCache(
                url="https://example.com/api",
                content='{"test": true}',
                etag='"abc123"',
                last_modified="Wed, 01 Jan 2025 00:00:00 GMT",
                expires_at=now + 3600,
                cached_at=now,
            )
            s.add(record)
            s.commit()

        with Session() as s:
            row = s.get(HttpCache, "https://example.com/api")
            assert row is not None
            assert row.content == '{"test": true}'
            assert row.etag == '"abc123"'
            assert row.expires_at == pytest.approx(now + 3600, abs=1)


class TestCrawlerNoCacheFlag:
    """Tests for --no-cache flag wiring."""

    def test_no_cache_flag_disables_use_cache(self):
        """When --no-cache is passed, use_cache should be False in Crawler."""
        from mcp_server.harvester.crawler import Crawler

        crawler = Crawler(use_cache=False)
        assert crawler._use_cache is False

    def test_default_use_cache_is_true(self):
        """By default Crawler should have caching enabled."""
        from mcp_server.harvester.crawler import Crawler

        crawler = Crawler()
        assert crawler._use_cache is True

    def test_cli_passes_no_cache_to_harvester(self):
        """The --no-cache CLI flag should set use_cache=False on ToolbankHarvester."""
        from mcp_server.cli import cmd_harvest
        from mcp_server.harvester import ToolbankHarvester
        from argparse import Namespace

        with patch("mcp_server.database.init_db"):
            with patch.object(ToolbankHarvester, "__init__", return_value=None) as mock_init:
                with patch.object(ToolbankHarvester, "harvest", return_value=[]):
                    with patch.object(ToolbankHarvester, "close"):
                        args = Namespace(
                            url="https://example.com", config=None, max_pages=5,
                            delay=1.0, no_cache=True,
                        )
                        cmd_harvest(args)
                mock_init.assert_called_once()
                call_kwargs = mock_init.call_args[1]
                assert call_kwargs.get("use_cache") is False


class TestCacheExpiry:
    """Tests for HTTP cache expiry behaviour."""

    def test_parse_expiry_from_max_age(self):
        """Cache-Control: max-age=N should produce expiry at now+N."""
        from mcp_server.harvester.crawler import Crawler

        headers = {"cache-control": "max-age=600"}
        before = time.time()
        expiry = Crawler._parse_expiry(headers)
        after = time.time()
        assert expiry is not None
        assert before + 600 <= expiry <= after + 600

    def test_parse_expiry_from_expires_header(self):
        """Expires header should produce a valid Unix timestamp."""
        from mcp_server.harvester.crawler import Crawler
        from datetime import datetime, timezone

        future_date = "Wed, 01 Jan 2031 12:00:00 GMT"
        headers = {"expires": future_date}
        expiry = Crawler._parse_expiry(headers)
        assert expiry is not None
        expected = datetime(2031, 1, 1, 12, 0, 0, tzinfo=timezone.utc).timestamp()
        assert abs(expiry - expected) < 60

    def test_parse_expiry_no_cache_control(self):
        """No Cache-Control or Expires should return None."""
        from mcp_server.harvester.crawler import Crawler

        headers = {}
        expiry = Crawler._parse_expiry(headers)
        assert expiry is None

    def test_parse_expiry_private_cache_control(self):
        """Cache-Control: private, max-age=600 should produce expiry."""
        from mcp_server.harvester.crawler import Crawler

        headers = {"cache-control": "private, max-age=600"}
        expiry = Crawler._parse_expiry(headers)
        assert expiry is not None

    def test_cache_hit_within_max_age(self):
        """Cache entry within max-age should be returned without fetch."""
        from mcp_server.harvester.crawler import Crawler

        crawler = Crawler(use_cache=True)
        future_expiry = time.time() + 3600
        crawler._cache["https://example.com"] = ("cached content", "text/html", future_expiry)

        with patch.object(crawler, "_client") as mock_client:
            content, ct = crawler.fetch("https://example.com")
            assert content == "cached content"
            assert mock_client.get.call_count == 0

    def test_cache_miss_when_stale(self):
        """Stale in-memory cache entry should trigger a re-fetch."""
        from mcp_server.harvester.crawler import Crawler

        crawler = Crawler(use_cache=True)
        past_expiry = time.time() - 1
        crawler._cache["https://example.com"] = ("stale content", "text/html", past_expiry)

        with patch.object(crawler, "_client") as mock_client:
            with patch.object(crawler, "_db_get", return_value=None):
                with patch.object(crawler, "robots") as mock_robots:
                    mock_robots.allowed.return_value = True
                    mock_response = MagicMock()
                    mock_response.text = "fresh content"
                    mock_response.headers = {"content-type": "text/html"}
                    mock_response.raise_for_status = MagicMock()
                    mock_client.get.return_value = mock_response

                    content, ct = crawler.fetch("https://example.com")
                    assert content == "fresh content"
                    assert mock_client.get.call_count == 1

    def test_force_flag_bypasses_cache(self):
        """force=True should bypass cache and re-fetch."""
        from mcp_server.harvester.crawler import Crawler

        crawler = Crawler(use_cache=True)
        future_expiry = time.time() + 3600
        crawler._cache["https://example.com"] = ("cached content", "text/html", future_expiry)

        with patch.object(crawler, "_client") as mock_client:
            with patch.object(crawler, "robots") as mock_robots:
                mock_robots.allowed.return_value = True
                mock_response = MagicMock()
                mock_response.text = "fresh content"
                mock_response.headers = {"content-type": "text/html"}
                mock_response.raise_for_status = MagicMock()
                mock_client.get.return_value = mock_response

                content, ct = crawler.fetch("https://example.com", force=True)
                assert content == "fresh content"
                assert mock_client.get.call_count == 1


class TestPurgeStale:
    """Tests for stale cache purging."""

    def _mock_session(self, rowcount=0):
        """Create a mock session that execute() returns rowcount."""
        mock_result = MagicMock()
        mock_result.rowcount = rowcount
        mock_sess = MagicMock()
        mock_sess.execute.return_value = mock_result
        mock_sess.commit.return_value = None
        mock_sess.close.return_value = None
        return mock_sess

    def test_purge_stale_removes_expired_entries(self):
        """purge_stale should remove all entries with past expiry timestamps."""
        from mcp_server.harvester.crawler import Crawler

        crawler = Crawler(use_cache=True)
        past = time.time() - 10
        future = time.time() + 3600
        crawler._cache["https://stale.example.com"] = ("stale", "text/html", past)
        crawler._cache["https://fresh.example.com"] = ("fresh", "text/html", future)

        mock_sess = self._mock_session(rowcount=0)
        with patch("mcp_server.harvester.crawler.get_session", return_value=mock_sess):
            purged = crawler.purge_stale()
        assert purged == 1
        assert "https://stale.example.com" not in crawler._cache
        assert "https://fresh.example.com" in crawler._cache

    def test_purge_stale_with_no_expiry_preserved(self):
        """Entries with no expiry timestamp (None) should be preserved."""
        from mcp_server.harvester.crawler import Crawler

        crawler = Crawler(use_cache=True)
        crawler._cache["https://no-expiry.example.com"] = ("forever", "text/html", None)

        mock_sess = self._mock_session(rowcount=0)
        with patch("mcp_server.harvester.crawler.get_session", return_value=mock_sess):
            purged = crawler.purge_stale()
        assert purged == 0
        assert "https://no-expiry.example.com" in crawler._cache

    def test_purge_stale_empty_cache(self):
        """purge_stale on empty cache returns 0."""
        from mcp_server.harvester.crawler import Crawler

        crawler = Crawler(use_cache=True)
        mock_sess = self._mock_session(rowcount=0)
        with patch("mcp_server.harvester.crawler.get_session", return_value=mock_sess):
            purged = crawler.purge_stale()
        assert purged == 0

    def test_purge_stale_deletes_stale_db_entries(self):
        """purge_stale should also delete stale DB entries and count them."""
        from mcp_server.harvester.crawler import Crawler

        crawler = Crawler(use_cache=True)
        # No in-memory entries - only DB
        mock_sess = self._mock_session(rowcount=3)
        with patch("mcp_server.harvester.crawler.get_session", return_value=mock_sess):
            purged = crawler.purge_stale()
        assert purged == 3


class TestRateLimitRetry:
    """Tests for HTTP 429 rate-limit retry with exponential backoff."""

    def _mock_429_response(self, retry_after: str | None = None, body="Rate limited"):
        """Factory for a 429 response mock."""
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.text = body
        mock_response.headers = {}
        if retry_after is not None:
            mock_response.headers["Retry-After"] = retry_after
        return mock_response

    def _mock_200_response(self, body="OK"):
        """Factory for a 200 response mock."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = body
        mock_response.headers = {"content-type": "text/html"}
        mock_response.raise_for_status = MagicMock()
        return mock_response

    def test_retry_on_429_retries_up_to_max_attempts(self):
        """On 429, crawler should retry up to 3 times before giving up."""
        from mcp_server.harvester.crawler import Crawler

        crawler = Crawler(use_cache=False)

        with patch.object(crawler, "_client") as mock_client:
            with patch.object(crawler, "robots") as mock_robots:
                mock_robots.allowed.return_value = True

                # Return 429 three times, then 200 (only 3 retries allowed)
                # total attempts: initial(429) + 3 retries(429,429,200) = success on 4th
                mock_client.get.side_effect = [
                    self._mock_429_response(),
                    self._mock_429_response(),
                    self._mock_429_response(),
                    self._mock_429_response(),
                ]

                # Should raise after max retries exhausted
                with pytest.raises(Exception) as exc_info:
                    with patch("time.sleep"):  # skip actual sleeps
                        crawler.fetch("https://example.com/api")
                assert "429" in str(exc_info.value)
                assert mock_client.get.call_count == 4  # initial + 3 retries

    def test_retry_succeeds_on_eventual_success(self):
        """If 429 resolves before max retries, return the successful response."""
        from mcp_server.harvester.crawler import Crawler

        crawler = Crawler(use_cache=False)

        with patch.object(crawler, "_client") as mock_client:
            with patch.object(crawler, "robots") as mock_robots:
                mock_robots.allowed.return_value = True

                # Return 429 once, then success
                mock_client.get.side_effect = [
                    self._mock_429_response(),
                    self._mock_200_response(body="success!"),
                ]

                with patch("time.sleep"):  # skip actual sleeps
                    content, ct = crawler.fetch("https://example.com/api")

                assert content == "success!"
                assert mock_client.get.call_count == 2

    def test_retry_after_header_used_when_present(self):
        """Retry-After header should override backoff calculation."""
        from mcp_server.harvester.crawler import Crawler

        crawler = Crawler(use_cache=False)

        with patch.object(crawler, "_client") as mock_client:
            with patch.object(crawler, "robots") as mock_robots:
                mock_robots.allowed.return_value = True

                # Return 429 with Retry-After: 5, then success
                mock_client.get.side_effect = [
                    self._mock_429_response(retry_after="5"),
                    self._mock_200_response(body="after retry-after"),
                ]

                sleep_calls = []
                original_sleep = time.sleep
                def track_sleep(duration):
                    sleep_calls.append(duration)
                    original_sleep(0)  # don't actually wait

                with patch.object(time, "sleep", side_effect=track_sleep):
                    content, _ = crawler.fetch("https://example.com/api")

                # First retry should wait for Retry-After value
                assert sleep_calls[0] == 5.0

    def test_retry_after_header_integer_seconds(self):
        """Retry-After header may be an integer (RFC 7231)."""
        from mcp_server.harvester.crawler import Crawler

        crawler = Crawler(use_cache=False)

        with patch.object(crawler, "_client") as mock_client:
            with patch.object(crawler, "robots") as mock_robots:
                mock_robots.allowed.return_value = True

                mock_client.get.side_effect = [
                    self._mock_429_response(retry_after="120"),
                    self._mock_200_response(),
                ]

                sleep_calls = []
                with patch.object(time, "sleep", side_effect=lambda d: sleep_calls.append(d)):
                    crawler.fetch("https://example.com/api")

                assert sleep_calls[0] == 120.0

    def test_exponential_backoff_formula(self):
        """Backoff = min(base * 2^attempt + jitter, 60s)."""
        from mcp_server.harvester.crawler import Crawler, _compute_backoff

        # Test the formula directly
        # base=1.0, attempt=0 -> 1.0 + jitter(0-1) -> clamped to 1.x
        delays = []
        for attempt in range(3):
            delay = _compute_backoff(base=1.0, attempt=attempt)
            delays.append(delay)
            assert delay <= 60.0, f"delay {delay} exceeds 60s cap"
            assert delay >= 0, f"delay {delay} is negative"

        # Verify exponential growth: each delay > previous (with high probability)
        # At attempt=0: ~1-2s, attempt=1: ~2-4s, attempt=2: ~4-8s
        assert delays[1] > delays[0], "backoff should grow with attempt"
        assert delays[2] > delays[1], "backoff should grow exponentially"

    def test_backoff_capped_at_60_seconds(self):
        """Backoff should never exceed 60 seconds."""
        from mcp_server.harvester.crawler import _compute_backoff

        # Very large base or many attempts should still be capped
        delay = _compute_backoff(base=100.0, attempt=10)
        assert delay == 60.0

    def test_each_retry_logged_at_warning(self):
        """Each retry attempt should be logged at WARNING level."""
        from mcp_server.harvester.crawler import Crawler

        crawler = Crawler(use_cache=False)

        with patch.object(crawler, "_client") as mock_client:
            with patch.object(crawler, "robots") as mock_robots:
                mock_robots.allowed.return_value = True
                mock_client.get.side_effect = [
                    self._mock_429_response(),
                    self._mock_429_response(),
                    self._mock_429_response(),
                    self._mock_429_response(),
                ]

                with patch("time.sleep"):
                    with patch("mcp_server.harvester.crawler.logger.warning") as mock_warn:
                        try:
                            crawler.fetch("https://example.com/api")
                        except Exception:
                            pass

                # Should have logged at least 3 warnings (one per retry)
                assert mock_warn.call_count >= 3
                for call in mock_warn.call_args_list:
                    args_str = " ".join(str(a) for a in call.args)
                    assert "429" in args_str or "retry" in args_str.lower()

    def test_error_logged_after_max_retries_exceeded(self):
        """After max retries exhausted, an error should be logged."""
        from mcp_server.harvester.crawler import Crawler

        crawler = Crawler(use_cache=False)

        with patch.object(crawler, "_client") as mock_client:
            with patch.object(crawler, "robots") as mock_robots:
                mock_robots.allowed.return_value = True
                mock_client.get.return_value = self._mock_429_response()

                with patch("time.sleep"):
                    with patch("mcp_server.harvester.crawler.logger.error") as mock_error:
                        try:
                            crawler.fetch("https://example.com/api")
                        except Exception:
                            pass

                assert mock_error.call_count >= 1

    def test_retry_policy_from_config_respected(self):
        """Crawler should accept a retry_policy dict from config."""
        from mcp_server.harvester.crawler import Crawler

        policy = {"max_retries": 5, "base_delay": 2.0}
        crawler = Crawler(use_cache=False, retry_policy=policy)

        with patch.object(crawler, "_client") as mock_client:
            with patch.object(crawler, "robots") as mock_robots:
                mock_robots.allowed.return_value = True

                # Return 429 five times
                mock_client.get.side_effect = [
                    self._mock_429_response() for _ in range(6)
                ]

                with patch("time.sleep"):
                    try:
                        crawler.fetch("https://example.com/api")
                    except Exception:
                        pass

                # 1 initial + 5 retries = 6 calls
                assert mock_client.get.call_count == 6

    def test_no_retry_on_other_http_errors(self):
        """Non-429 errors should NOT be retried (e.g. 500, 404)."""
        from mcp_server.harvester.crawler import Crawler
        import httpx

        crawler = Crawler(use_cache=False)

        with patch.object(crawler, "_client") as mock_client:
            with patch.object(crawler, "robots") as mock_robots:
                mock_robots.allowed.return_value = True

                mock_response = MagicMock()
                mock_response.status_code = 500
                mock_response.text = "Server Error"
                mock_response.headers = {}
                # Make raise_for_status raise HTTPStatusError
                mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                    "Server Error", request=MagicMock(), response=mock_response
                )
                mock_client.get.return_value = mock_response

                with patch("time.sleep"):
                    with pytest.raises(Exception) as exc_info:
                        crawler.fetch("https://example.com/api")
                    assert "500" in str(exc_info.value)

                # Should only be called once - no retries for non-429
                assert mock_client.get.call_count == 1


class TestDbCacheIntegration:
    """Integration tests for DB-backed http_cache table used by Crawler."""

    def test_crawler_purges_stale_on_run(self):
        """On each crawl run, stale DB entries should be purged."""
        from mcp_server.harvester.crawler import Crawler, HttpCache
        from mcp_server.database import Base
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker

        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine, expire_on_commit=False)

        # Insert a stale entry in the in-memory cache (simulate already-seen URL)
        mock_result = MagicMock()
        mock_result.rowcount = 1
        mock_ctx = MagicMock()
        mock_ctx.execute.return_value = mock_result
        mock_ctx.commit.return_value = None
        mock_ctx.close.return_value = None

        with patch("mcp_server.harvester.crawler.get_session", return_value=mock_ctx):
            crawler = Crawler(use_cache=True)
            # Simulate a stale in-memory entry
            crawler._cache["https://stale.example.com"] = (
                "stale content", "text/html", time.time() - 10
            )
            purged = crawler.purge_stale()
            # 1 stale in-memory + 1 DB rowcount
            assert purged == 2
            assert "https://stale.example.com" not in crawler._cache

    def test_crawler_stores_etag_and_last_modified(self):
        """Crawler should store etag/last_modified in DB cache on fetch."""
        from mcp_server.harvester.crawler import Crawler

        mock_session = MagicMock()
        mock_session.merge.return_value = None
        mock_session.close.return_value = None

        mock_session.get.return_value = None  # simulate DB cache miss
        with patch("mcp_server.harvester.crawler.get_session", return_value=mock_session):
            crawler = Crawler(use_cache=True)

            with patch.object(crawler, "_client") as mock_client:
                with patch.object(crawler, "robots") as mock_robots:
                    mock_robots.allowed.return_value = True
                    mock_response = MagicMock()
                    mock_response.text = "content"
                    mock_response.headers = {
                        "content-type": "text/html",
                        "etag": '"etag123"',
                        "last-modified": "Wed, 01 Jan 2025 00:00:00 GMT",
                    }
                    mock_response.raise_for_status = MagicMock()
                    mock_client.get.return_value = mock_response

                    crawler.fetch("https://example.com")

                    merge_call = mock_session.merge.call_args[0][0]
                    assert merge_call.url == "https://example.com"
                    assert merge_call.etag == '"etag123"'
                    assert merge_call.last_modified == "Wed, 01 Jan 2025 00:00:00 GMT"
