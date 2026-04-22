"""
HTTP crawler with robots.txt compliance, rate limiting, and caching.
"""

from __future__ import annotations

import email.utils
import logging
import re
import time
from typing import Any, Optional
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import httpx

from mcp_server.database import HttpCache, get_session

logger = logging.getLogger(__name__)

_DEFAULT_USER_AGENT = "ToolbankHarvester/1.0 (+https://github.com/toolbank)"
_REQUEST_DELAY = 1.0  # seconds between requests to the same host


class RobotsCache:
    """Per-host robots.txt cache."""

    def __init__(self):
        self._cache: dict[str, RobotFileParser | None] = {}

    def allowed(self, url: str, user_agent: str = _DEFAULT_USER_AGENT) -> bool:
        parsed = urlparse(url)
        host_key = f"{parsed.scheme}://{parsed.netloc}"
        if host_key not in self._cache:
            robots_url = f"{host_key}/robots.txt"
            rp = RobotFileParser()
            rp.set_url(robots_url)
            try:
                rp.read()
            except Exception as exc:
                logger.debug("Could not fetch robots.txt for %s: %s", host_key, exc)
                # Default to allowed when robots.txt is unreachable
                rp = None
            self._cache[host_key] = rp
        rp = self._cache[host_key]
        if rp is None:
            return True
        return rp.can_fetch(user_agent, url)


class Crawler:
    """
    Polite HTTP crawler.

    - Checks robots.txt (RFC 9309) before fetching.
    - Rate-limits requests per host.
    - Caches responses in a SQLite-backed store (http_cache table) with HTTP
      Cache-Control expiry support (max-age).
    - Supports both HTML and JSON responses.
    - Purges stale DB entries on each run.
    """

    def __init__(
        self,
        user_agent: str = _DEFAULT_USER_AGENT,
        request_delay: float = _REQUEST_DELAY,
        timeout: float = 20.0,
        use_cache: bool = True,
        follow_redirects: bool = True,
    ):
        self.user_agent = user_agent
        self.request_delay = request_delay
        self.robots = RobotsCache()
        self._use_cache = use_cache
        # In-memory hot cache: url -> (content, content_type, expiry_ts | None)
        self._cache: dict[str, tuple[str, str, float | None]] = {}
        self._last_request: dict[str, float] = {}
        self._client = httpx.Client(
            headers={"User-Agent": user_agent},
            timeout=timeout,
            follow_redirects=follow_redirects,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def fetch(self, url: str, force: bool = False) -> tuple[str, str]:
        """Fetch URL content.

        Args:
            url: The URL to fetch.
            force: When True, bypass cache and re-fetch even if cached.

        Returns:
            Tuple of (content, content_type).

        Raises:
            ValueError: If blocked by robots.txt or an HTTP/request error occurs.
        """
        if not self.robots.allowed(url, self.user_agent):
            raise ValueError(f"Blocked by robots.txt: {url}")

        if self._use_cache and not force:
            # 1. Check in-memory cache first
            cached = self._cache.get(url)
            if cached is not None:
                content, content_type, expiry_ts = cached
                if expiry_ts is None or time.time() <= expiry_ts:
                    logger.debug("In-memory cache hit: %s", url)
                    return content, content_type
                # Stale — evict from in-memory and re-fetch
                logger.debug("In-memory cache stale, evicting: %s", url)
                del self._cache[url]

            # 2. Check DB cache
            db_entry = self._db_get(url)
            if db_entry is not None:
                content, content_type, expiry_ts = db_entry
                if expiry_ts is None or time.time() <= expiry_ts:
                    logger.debug("DB cache hit: %s", url)
                    # Promote to in-memory
                    self._cache[url] = (content, content_type, expiry_ts)
                    return content, content_type
                # Stale — delete from DB
                logger.debug("DB cache stale, deleting: %s", url)
                self._db_delete(url)

        # Rate limiting per host
        host = urlparse(url).netloc
        last = self._last_request.get(host, 0)
        sleep_time = self.request_delay - (time.monotonic() - last)
        if sleep_time > 0:
            time.sleep(sleep_time)
        self._last_request[host] = time.monotonic()

        try:
            response = self._client.get(url)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise ValueError(f"HTTP {exc.response.status_code} fetching {url}") from exc
        except httpx.RequestError as exc:
            raise ValueError(f"Request error fetching {url}: {exc}") from exc

        content = response.text
        content_type = response.headers.get("content-type", "text/html")

        if self._use_cache:
            expiry_ts = self._parse_expiry(response.headers)
            etag = response.headers.get("etag")
            last_modified = response.headers.get("last-modified")
            # Store in in-memory cache
            self._cache[url] = (content, content_type, expiry_ts)
            # Persist to DB
            self._db_set(url, content, etag, last_modified, expiry_ts)

        return content, content_type

    def fetch_json(self, url: str, force: bool = False) -> Any:
        """Fetch and parse JSON from URL.

        Args:
            url: The URL to fetch.
            force: Bypass cache when True.

        Returns:
            Parsed JSON object.
        """
        import json

        content, _ = self.fetch(url, force=force)
        return json.loads(content)

    def discover_links(self, base_url: str, content: str) -> list[str]:
        """Extract absolute links from HTML content.

        Args:
            base_url: Base URL for resolving relative links.
            content: Raw HTML content.

        Returns:
            Deduplicated list of absolute URLs.
        """
        try:
            from bs4 import BeautifulSoup

            soup = BeautifulSoup(content, "html.parser")
            links = []
            for tag in soup.find_all("a", href=True):
                href = tag["href"].strip()
                absolute = urljoin(base_url, href)
                parsed = urlparse(absolute)
                if parsed.scheme in ("http", "https"):
                    links.append(absolute)
            return list(dict.fromkeys(links))  # deduplicate preserving order
        except ImportError:
            logger.warning("beautifulsoup4 not installed – link discovery disabled")
            return []

    def purge_stale(self) -> int:
        """Remove all stale entries from in-memory cache, DB cache, and return count.

        Called at the start of each crawl run to keep the cache lean.

        Returns:
            Number of entries purged.
        """
        now = time.time()
        purged = 0

        # Purge in-memory
        stale_mem = [
            url
            for url, (_, _, expiry_ts) in self._cache.items()
            if expiry_ts is not None and now > expiry_ts
        ]
        for url in stale_mem:
            del self._cache[url]
            purged += 1

        # Purge DB
        if self._use_cache:
            session = get_session()
            try:
                from sqlalchemy import delete

                stmt = delete(HttpCache).where(
                    HttpCache.expires_at.isnot(None),
                    HttpCache.expires_at < now,
                )
                result = session.execute(stmt)
                session.commit()
                db_purged = result.rowcount
                purged += db_purged
                if db_purged:
                    logger.debug("Purged %d stale DB cache entries", db_purged)
            except Exception as exc:
                logger.warning("Failed to purge stale DB cache entries: %s", exc)
            finally:
                session.close()

        if purged:
            logger.debug("Purged %d stale cache entries total", purged)
        return purged

    def close(self) -> None:
        """Close the underlying HTTP client."""
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    # ------------------------------------------------------------------
    # DB cache helpers
    # ------------------------------------------------------------------

    def _db_get(self, url: str) -> Optional[tuple[str, str, float | None]]:
        """Fetch a cache entry from the DB. Returns (content, content_type, expiry_ts) or None."""
        try:
            session = get_session()
            try:
                row = session.get(HttpCache, url)
                if row is None:
                    return None
                # Reconstruct content_type - we store content only, but callers
                # expect (content, content_type). Default to text/html for DB entries.
                return (row.content, "text/html", row.expires_at)
            finally:
                session.close()
        except Exception as exc:
            logger.warning("DB cache get failed for %s: %s", url, exc)
            return None

    def _db_set(
        self,
        url: str,
        content: str,
        etag: Optional[str],
        last_modified: Optional[str],
        expires_at: Optional[float],
    ) -> None:
        """Write a cache entry to the DB, overwriting any existing entry."""
        try:
            session = get_session()
            try:
                now = time.time()
                session.merge(
                    HttpCache(
                        url=url,
                        content=content,
                        etag=etag,
                        last_modified=last_modified,
                        expires_at=expires_at,
                        cached_at=now,
                    )
                )
                session.commit()
            finally:
                session.close()
        except Exception as exc:
            logger.warning("DB cache set failed for %s: %s", url, exc)

    def _db_delete(self, url: str) -> None:
        """Delete a cache entry from the DB."""
        try:
            session = get_session()
            try:
                row = session.get(HttpCache, url)
                if row:
                    session.delete(row)
                    session.commit()
            finally:
                session.close()
        except Exception as exc:
            logger.warning("DB cache delete failed for %s: %s", url, exc)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_expiry(headers: Any) -> float | None:
        """Derive an expiry Unix timestamp from Cache-Control / Expires headers.

        Args:
            headers: httpx Headers (or any mapping) from the HTTP response.

        Returns:
            Unix timestamp when the cached value expires, or None for no expiry.
        """
        # Cache-Control: max-age takes precedence
        cache_control = headers.get("cache-control", "")
        match = re.search(r"max-age\s*=\s*(\d+)", cache_control, re.IGNORECASE)
        if match:
            max_age = int(match.group(1))
            return time.time() + max_age

        # Expires header fallback
        expires = headers.get("expires", "")
        if expires:
            try:
                dt = email.utils.parsedate_to_datetime(expires)
                return dt.timestamp()
            except Exception:
                pass

        return None
