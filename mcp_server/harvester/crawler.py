"""
HTTP crawler with robots.txt compliance, rate limiting, and caching.
"""

from __future__ import annotations

import hashlib
import logging
import time
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import httpx

logger = logging.getLogger(__name__)

_CACHE_DIR = Path("toolbank/.crawler_cache")
_DEFAULT_USER_AGENT = "ToolbankHarvester/1.0 (+https://github.com/toolbank)"
_REQUEST_DELAY = 1.0  # seconds between requests to the same host


class RobotsCache:
    """Per-host robots.txt cache."""

    def __init__(self):
        self._cache: dict[str, RobotFileParser] = {}

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
                rp = None  # type: ignore[assignment]
            self._cache[host_key] = rp
        rp = self._cache[host_key]
        if rp is None:
            return True
        return rp.can_fetch(user_agent, url)


class PageCache:
    """Simple on-disk page cache keyed by URL hash."""

    def __init__(self, cache_dir: Path = _CACHE_DIR):
        self.dir = cache_dir
        self.dir.mkdir(parents=True, exist_ok=True)

    def _key(self, url: str) -> Path:
        return self.dir / (hashlib.sha256(url.encode()).hexdigest() + ".html")

    def get(self, url: str) -> str | None:
        path = self._key(url)
        if path.exists():
            return path.read_text(encoding="utf-8", errors="replace")
        return None

    def set(self, url: str, content: str) -> None:
        self._key(url).write_text(content, encoding="utf-8")


class Crawler:
    """
    Polite HTTP crawler.
    - Checks robots.txt (RFC 9309) before fetching.
    - Rate-limits requests per host.
    - Caches responses on disk to avoid re-fetching.
    - Supports both HTML and JSON responses.
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
        self.cache = PageCache() if use_cache else None
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
        """
        Fetch URL content.
        Returns (content, content_type).
        Raises ValueError if blocked by robots.txt.
        """
        if not self.robots.allowed(url, self.user_agent):
            raise ValueError(f"Blocked by robots.txt: {url}")

        # Check cache
        if self.cache and not force:
            cached = self.cache.get(url)
            if cached is not None:
                logger.debug("Cache hit: %s", url)
                return cached, "text/html"

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

        if self.cache:
            self.cache.set(url, content)

        return content, content_type

    def fetch_json(self, url: str, force: bool = False) -> Any:
        """Fetch and parse JSON from URL."""
        import json

        content, _ = self.fetch(url, force=force)
        return json.loads(content)

    def discover_links(self, base_url: str, content: str) -> list[str]:
        """Extract absolute links from HTML content."""
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

    def close(self) -> None:
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
