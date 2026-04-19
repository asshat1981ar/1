"""
Main ToolbankHarvester orchestrator.

Pipeline:
  Seed Sources → Discovery → Classify → Extract → Normalize → Dedupe → Verify
  → Human Review Queue OR Tool Registry → ChromaDB Index
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

from .classifier import classify
from .crawler import Crawler
from .deduper import deduplicate
from .extractors import extract_from_docs, extract_from_github_readme, extract_from_openapi
from .normalizer import normalize
from .verifier import CONFIDENCE_THRESHOLD, verify

logger = logging.getLogger(__name__)

# Candidate confidence threshold for queuing vs. dropping
QUEUE_THRESHOLD = 0.30

_OPENAPI_PROBE_PATHS = [
    "/openapi.json",
    "/openapi.yaml",
    "/swagger.json",
    "/swagger.yaml",
    "/api-docs",
    "/api-docs.json",
    "/api/openapi.json",
    "/api/swagger.json",
    "/v1/openapi.json",
    "/v2/openapi.json",
    "/v3/openapi.json",
]


class ToolbankHarvester:
    """
    Crawls seed URLs, extracts tool candidates, normalises and verifies them,
    then writes approved records to the registry and vector store.
    """

    def __init__(
        self,
        db_path: str = "toolbank/registry.db",
        records_dir: str = "toolbank/records",
        evidence_dir: str = "toolbank/evidence",
        request_delay: float = 1.0,
        use_cache: bool = True,
    ):
        self.db_path = db_path
        self.records_dir = Path(records_dir)
        self.evidence_dir = Path(evidence_dir)
        self.records_dir.mkdir(parents=True, exist_ok=True)
        self.evidence_dir.mkdir(parents=True, exist_ok=True)
        self._crawler = Crawler(request_delay=request_delay, use_cache=use_cache)

        # Lazy imports to avoid hard deps at import time
        self._db_ready = False

    def _ensure_db(self):
        if not self._db_ready:
            from mcp_server.database import init_db
            init_db(self.db_path)
            self._db_ready = True

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def harvest(self, seed_url: str, max_pages: int = 20) -> list[dict[str, Any]]:
        """
        Full harvest pipeline for one seed URL.
        Returns list of record dicts that were published (approved/verified/queued).
        """
        logger.info("Starting harvest for seed: %s", seed_url)
        discovered = self.discover(seed_url, max_pages=max_pages)
        all_candidates: list[dict[str, Any]] = []

        for url in discovered:
            candidates = self._process_url(url)
            all_candidates.extend(candidates)

        # Deduplicate across all discovered pages
        deduped = deduplicate(all_candidates)
        logger.info("After dedup: %d candidates from %d raw", len(deduped), len(all_candidates))

        published = []
        for candidate in deduped:
            result = self._pipeline(candidate)
            if result:
                published.append(result)

        logger.info("Harvest complete: %d records published from %s", len(published), seed_url)
        return published

    def discover(self, seed_url: str, max_pages: int = 20) -> list[str]:
        """
        Find all harvestable URLs starting from a seed.
        Priority: OpenAPI probes → llms.txt → sitemap → docs links.
        """
        found: list[str] = []
        base = _base_url(seed_url)

        # 1. Probe for OpenAPI specs
        for probe in _OPENAPI_PROBE_PATHS:
            url = base + probe
            if self._url_responds(url):
                found.append(url)

        # 2. Check llms.txt
        llms_url = base + "/llms.txt"
        if self._url_responds(llms_url):
            found.append(llms_url)
            # Parse llms.txt for additional URLs
            try:
                content, _ = self._crawler.fetch(llms_url)
                found.extend(_extract_urls_from_llms_txt(content, base))
            except Exception:
                pass

        # 3. Sitemap
        sitemap_url = base + "/sitemap.xml"
        try:
            content, _ = self._crawler.fetch(sitemap_url)
            found.extend(_extract_urls_from_sitemap(content, base, max_pages))
        except Exception:
            pass

        # 4. Follow links from the seed page itself
        try:
            content, ct = self._crawler.fetch(seed_url)
            if "html" in ct.lower():
                links = self._crawler.discover_links(seed_url, content)
                found.extend(_filter_relevant_links(links, base, max_pages))
        except Exception:
            pass

        # Always include the seed itself
        if seed_url not in found:
            found.insert(0, seed_url)

        # Deduplicate preserving order
        return list(dict.fromkeys(found))[:max_pages]

    def fetch(self, url: str) -> str:
        """Fetch content respecting robots.txt, rate limits, and cache."""
        content, _ = self._crawler.fetch(url)
        return content

    def classify(self, content: str, url: str = "") -> str:
        """Classify page content type."""
        return classify(content, url)

    def extract(self, content: str, source_url: str) -> list[dict[str, Any]]:
        """Extract candidate records from content."""
        page_type = classify(content, source_url)

        if page_type == "openapi":
            try:
                import json as _json
                import yaml as _yaml  # type: ignore

                if content.lstrip().startswith("{"):
                    spec = _json.loads(content)
                else:
                    spec = _yaml.safe_load(content)
                return extract_from_openapi(spec, source_url)
            except Exception as exc:
                logger.warning("OpenAPI parse failed for %s: %s", source_url, exc)

        if page_type == "github_readme":
            return extract_from_github_readme(content, source_url)

        if page_type in ("api_docs", "cli_docs", "llms_txt"):
            results = extract_from_docs(content, source_url)
            # Unwrap ExtractionResult dicts
            return [r["record"] for r in results if r.get("record")]

        return []

    def normalize(self, candidate: dict[str, Any]) -> dict[str, Any]:
        """Normalise a raw candidate record."""
        return normalize(candidate)

    def verify(self, record: dict[str, Any]) -> dict[str, Any]:
        """Verify a normalised record."""
        return verify(record)

    def publish(self, record: dict[str, Any]) -> None:
        """Write approved/verified record to registry, disk, and vector index."""
        self._ensure_db()
        from mcp_server import database, vector_store

        # Persist to SQLite
        database.upsert_tool(record)

        # Persist to disk
        safe_id = record["id"].replace("/", "_").replace("\\", "_")
        record_path = self.records_dir / f"{safe_id}.json"
        record_path.write_text(json.dumps(record, indent=2), encoding="utf-8")

        # Index in ChromaDB
        if record.get("status") in ("approved", "verified"):
            vector_store.index_tool(record)

        logger.info("Published record: %s (status=%s)", record["id"], record.get("status"))

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _process_url(self, url: str) -> list[dict[str, Any]]:
        """Fetch + classify + extract one URL. Returns raw candidates."""
        try:
            content, _ = self._crawler.fetch(url)
        except ValueError as exc:
            logger.debug("Skipping %s: %s", url, exc)
            return []
        candidates = self.extract(content, url)
        return candidates

    def _pipeline(self, candidate: dict[str, Any]) -> dict[str, Any] | None:
        """
        Normalise → verify → publish or queue.
        Returns the final record dict if it was published/queued, else None.
        """
        self._ensure_db()
        from mcp_server import database

        rec = self.normalize(candidate)
        result = self.verify(rec)

        if result["passed"]:
            self.publish(rec)
            return rec

        confidence = float(rec.get("confidence", 0.0))
        if confidence >= QUEUE_THRESHOLD:
            # Queue for human review
            database.enqueue_for_review(
                rec["id"], rec, confidence, result["issues"]
            )
            # Still persist as draft
            database.upsert_tool(rec)
            logger.info(
                "Queued for review: %s (confidence=%.2f, issues=%s)",
                rec["id"],
                confidence,
                result["issues"],
            )
            return rec

        logger.debug(
            "Dropped candidate %s (confidence=%.2f, issues=%s)",
            rec.get("id", "?"),
            confidence,
            result["issues"],
        )
        return None

    def _url_responds(self, url: str) -> bool:
        """Quick HEAD check to see if a URL exists."""
        try:
            if not self._crawler.robots.allowed(url, self._crawler.user_agent):
                return False
            resp = self._crawler._client.head(url)
            return resp.status_code < 400
        except Exception:
            return False

    def close(self):
        self._crawler.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


# ------------------------------------------------------------------
# Utility functions
# ------------------------------------------------------------------

def _base_url(url: str) -> str:
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}"


def _extract_urls_from_llms_txt(content: str, base: str) -> list[str]:
    """Extract URLs referenced in llms.txt."""
    import re
    urls = re.findall(r"https?://[^\s\)\"]+", content)
    return [u for u in urls if urlparse(u).netloc]


def _extract_urls_from_sitemap(content: str, base: str, max_pages: int) -> list[str]:
    """Extract <loc> URLs from a sitemap.xml."""
    import re
    locs = re.findall(r"<loc>(.*?)</loc>", content, re.IGNORECASE)
    return locs[:max_pages]


def _filter_relevant_links(links: list[str], base: str, limit: int) -> list[str]:
    """Keep only links that look like API docs / reference pages."""
    keywords = ("api", "docs", "reference", "rest", "openapi", "swagger", "guide", "sdk")
    filtered = [
        l for l in links
        if any(k in l.lower() for k in keywords)
        and l.startswith(base)
    ]
    return filtered[:limit]
