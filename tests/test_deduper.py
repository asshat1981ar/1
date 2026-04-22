"""
Tests for multi-source evidence merging in deduper.
"""

from __future__ import annotations

import pytest
from mcp_server.harvester.deduper import deduplicate


class TestMultiSourceEvidenceMerging:
    """Tests for weighted confidence merging when same tool appears in multiple sources."""

    def _record(self, name, namespace, confidence=0.8, source_urls=None, evidence=None, method="POST", url="/v1/test"):
        """Helper to create a test record."""
        return {
            "id": f"{namespace}.{name}",
            "name": name,
            "namespace": namespace,
            "description": f"Create a {name}",
            "side_effect_level": "write",
            "confidence": confidence,
            "source_urls": source_urls or [f"https://example.com/{name}"],
            "input_schema": {"type": "object", "properties": {}},
            "execution_adapter": {"kind": "http", "method": method, "url_template": f"https://api.example.com{url}"},
            "auth": {"type": "none", "required_env": []},
            "tags": [namespace],
            "evidence": evidence or [],
        }

    def test_single_source_evidence_unchanged(self):
        """Evidence from a single source passes through unchanged."""
        records = [
            self._record(
                "create_customer",
                "stripe",
                confidence=0.8,
                evidence=[
                    {"text": "Creates a customer object", "confidence": 0.9},
                    {"text": "Returns customer id", "confidence": 0.7},
                ],
            )
        ]
        result = deduplicate(records)
        assert len(result) == 1
        assert len(result[0]["evidence"]) == 2
        assert result[0]["evidence"][0]["confidence"] == 0.9

    def test_duplicate_tools_merge_evidence_arrays(self):
        """When same tool appears in multiple sources, evidence arrays are merged."""
        r1 = self._record(
            "create_payment_link",
            "stripe",
            confidence=0.7,
            url="/v1/payment_links",
            evidence=[{"text": "Creates payment link", "confidence": 0.8}],
        )
        r2 = self._record(
            "payment_links_create",
            "stripe",
            confidence=0.9,
            url="/v1/payment_links",
            evidence=[{"text": "Payment link creation endpoint", "confidence": 0.85}],
        )
        result = deduplicate([r1, r2])
        assert len(result) == 1
        # Both evidence items should be present
        assert len(result[0]["evidence"]) == 2

    def test_weighted_confidence_calculation(self):
        """Weighted confidence: sum(evidence_confidence * source_confidence) / sum(source_confidence)."""
        r1 = self._record(
            "create_payment_link",
            "stripe",
            confidence=0.6,
            url="/v1/payment_links",
            evidence=[{"text": "Creates a link", "confidence": 0.8}],
        )
        r2 = self._record(
            "payment_links_create",
            "stripe",
            confidence=0.9,
            url="/v1/payment_links",
            evidence=[{"text": "Creates a link", "confidence": 0.9}],
        )
        result = deduplicate([r1, r2])
        assert len(result) == 1
        
        # For evidence "Creates a link" from both sources:
        # weighted = (0.8 * 0.6 + 0.9 * 0.9) / (0.6 + 0.9) = (0.48 + 0.81) / 1.5 = 0.86
        ev = result[0]["evidence"][0]
        expected_confidence = (0.8 * 0.6 + 0.9 * 0.9) / (0.6 + 0.9)
        assert abs(ev["confidence"] - expected_confidence) < 1e-9

    def test_merged_from_metadata_stored(self):
        """When evidence is merged, merged_from metadata tracks the sources."""
        r1 = self._record(
            "create_customer",
            "stripe",
            confidence=0.7,
            url="/v1/customers",
            evidence=[{"text": "Creates customer", "confidence": 0.8}],
        )
        r2 = self._record(
            "customers_create",
            "stripe",
            confidence=0.9,
            url="/v1/customers",
            evidence=[{"text": "Creates customer", "confidence": 0.9}],
        )
        result = deduplicate([r1, r2])
        assert len(result) == 1
        
        # Each evidence item should have merged_from
        for ev in result[0]["evidence"]:
            assert "merged_from" in ev
            assert len(ev["merged_from"]) == 2

    def test_duplicate_evidence_same_source_not_duplicated(self):
        """Same evidence appearing in both sources is not duplicated after merge."""
        shared_evidence = [{"text": "Shared description", "confidence": 0.85}]
        r1 = self._record(
            "create_order",
            "shopify",
            confidence=0.7,
            url="/v1/orders",
            evidence=shared_evidence,
        )
        r2 = self._record(
            "orders_create",
            "shopify",
            confidence=0.9,
            url="/v1/orders",
            evidence=shared_evidence,
        )
        result = deduplicate([r1, r2])
        assert len(result) == 1
        # Evidence should be deduplicated (only one entry)
        assert len(result[0]["evidence"]) == 1

    def test_multiple_evidence_items_merged(self):
        """Multiple different evidence items from multiple sources are all merged."""
        r1 = self._record(
            "send_email",
            "sendgrid",
            confidence=0.6,
            url="/v3/mail/send",
            evidence=[
                {"text": "Sends an email", "confidence": 0.7},
                {"text": "Requires from address", "confidence": 0.8},
            ],
        )
        r2 = self._record(
            "mail_send",
            "sendgrid",
            confidence=0.85,
            url="/v3/mail/send",
            evidence=[
                {"text": "Sends transactional email", "confidence": 0.9},
                {"text": "Accepts HTML body", "confidence": 0.75},
            ],
        )
        result = deduplicate([r1, r2])
        assert len(result) == 1
        # All 4 unique evidence items should be present
        assert len(result[0]["evidence"]) == 4

    def test_three_sources_weighted_confidence(self):
        """Three sources with different confidences are weighted correctly."""
        r1 = self._record(
            "get_user",
            "api",
            confidence=0.5,
            url="/users",
            evidence=[{"text": "Fetch user", "confidence": 0.6}],
        )
        r2 = self._record(
            "fetch_user",
            "api",
            confidence=0.8,
            url="/users",
            evidence=[{"text": "Fetch user", "confidence": 0.7}],
        )
        r3 = self._record(
            "retrieve_user",
            "api",
            confidence=0.9,
            url="/users",
            evidence=[{"text": "Fetch user", "confidence": 0.85}],
        )
        result = deduplicate([r1, r2, r3])
        assert len(result) == 1
        
        # Weighted: (0.6*0.5 + 0.7*0.8 + 0.85*0.9) / (0.5 + 0.8 + 0.9)
        expected = (0.6 * 0.5 + 0.7 * 0.8 + 0.85 * 0.9) / (0.5 + 0.8 + 0.9)
        assert abs(result[0]["evidence"][0]["confidence"] - expected) < 1e-9

    def test_evidence_without_confidence_defaults_to_medium(self):
        """Evidence items without explicit confidence use a default (0.5)."""
        r1 = self._record(
            "create_item",
            "api",
            confidence=0.7,
            url="/items",
            evidence=[{"text": "Creates item"}],  # No confidence
        )
        r2 = self._record(
            "items_create",
            "api",
            confidence=0.9,
            url="/items",
            evidence=[{"text": "Creates item", "confidence": 0.8}],
        )
        result = deduplicate([r1, r2])
        assert len(result) == 1
        
        # Default confidence for first evidence is 0.5
        expected = (0.5 * 0.7 + 0.8 * 0.9) / (0.7 + 0.9)
        assert abs(result[0]["evidence"][0]["confidence"] - expected) < 1e-9

    def test_non_dict_evidence_preserved(self):
        """Non-dict evidence items (strings, etc.) are preserved without merging."""
        r1 = self._record(
            "simple_tool",
            "api",
            confidence=0.7,
            evidence=["Simple description 1"],
        )
        r2 = self._record(
            "simple_tool_alias",
            "api",
            confidence=0.9,
            evidence=["Simple description 2"],
        )
        result = deduplicate([r1, r2])
        assert len(result) == 1
        assert len(result[0]["evidence"]) == 2
        assert "Simple description 1" in result[0]["evidence"]
        assert "Simple description 2" in result[0]["evidence"]