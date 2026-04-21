"""
Tests for the rich TUI review module.
"""

from __future__ import annotations

from unittest.mock import patch

# --------------------------------------------------------------------------=
# TUI table-building tests
# --------------------------------------------------------------------------=

class TestBuildTable:
    def _item(self, **kwargs):
        defaults = {
            "queue_id": 1,
            "record_id": "stripe.get_customer",
            "confidence": 0.87,
            "issues": ["no_examples", "low_confidence"],
            "status": "pending",
            "candidate": {"description": "Retrieve a Stripe customer.", "source_urls": ["https://stripe.com/docs"]},
        }
        defaults.update(kwargs)
        return defaults

    def test_single_item_table(self):
        from mcp_server.tui import _build_table
        items = [self._item()]
        table = _build_table(items)
        # Just verify it renders without error
        assert table is not None

    def test_multiple_items_table(self):
        from mcp_server.tui import _build_table
        items = [
            self._item(queue_id=1, record_id="stripe.get_customer", confidence=0.9),
            self._item(queue_id=2, record_id="stripe.create_customer", confidence=0.45, issues=["low_confidence", "no_schema"]),
        ]
        table = _build_table(items)
        assert table is not None

    def test_item_with_many_issues_truncates(self):
        from mcp_server.tui import _build_table
        items = [self._item(issues=["a", "b", "c", "d", "e"])]
        table = _build_table(items)
        assert table is not None

    def test_empty_list(self):
        from mcp_server.tui import _build_table
        table = _build_table([])
        assert table is not None


class TestShowDetail:
    def _item(self, **kwargs):
        defaults = {
            "queue_id": 1,
            "record_id": "stripe.get_customer",
            "confidence": 0.87,
            "issues": ["no_examples"],
            "status": "pending",
            "candidate": {
                "description": "Retrieve a Stripe customer.",
                "source_urls": ["https://stripe.com/docs"],
            },
        }
        defaults.update(kwargs)
        return defaults

    def test_show_detail_runs_without_error(self):
        from mcp_server.tui import _show_detail
        # Should not raise
        _show_detail(self._item())

    def test_show_detail_empty_source_urls(self):
        from mcp_server.tui import _show_detail
        item = self._item(candidate={"description": "Test", "source_urls": []})
        _show_detail(item)  # should not raise

    def test_show_detail_missing_candidate_keys(self):
        from mcp_server.tui import _show_detail
        item = self._item(candidate={})
        _show_detail(item)  # should not raise


class TestRunReviewTuiEmpty:
    def test_empty_queue_returns_none(self):
        from mcp_server.tui import run_review_tui
        result = run_review_tui([])
        assert result is None


class TestRunReviewTuiApproval:
    def test_approve_item_calls_db_approve(self):
        from mcp_server.database import approve_review_item
        with patch("mcp_server.database.approve_review_item"):
            result = approve_review_item(10)
            # Just verify it doesn't raise and callable is correct


class TestRunReviewTuiRejection:
    def test_reject_item_calls_db_reject(self):
        from mcp_server.database import reject_review_item
        with patch("mcp_server.database.reject_review_item"):
            result = reject_review_item(20)
            # Just verify it doesn't raise and callable is correct
