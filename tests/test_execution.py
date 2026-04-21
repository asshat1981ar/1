"""
Tests for tool execution history tracking.
"""
from __future__ import annotations

import json
import os
import tempfile
import pytest
from mcp_server.database import init_db, log_tool_execution, get_tool_executions


@pytest.fixture(autouse=True)
def fresh_db():
    """Use an in-memory database for each test."""
    fd, db = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    init_db(db)
    yield db
    try:
        os.unlink(db)
    except OSError:
        pass


class TestLogAndRetrieveExecution:
    def test_log_single_execution(self, fresh_db):
        log_tool_execution(
            tool_id="stripe.get_customer",
            arguments={"customer_id": "cus_123"},
            result={"id": "cus_123", "email": "test@example.com"},
            status="success",
            duration_ms=142,
        )
        rows = get_tool_executions(tool_id="stripe.get_customer", limit=10)
        assert len(rows) == 1
        assert rows[0]["tool_id"] == "stripe.get_customer"
        assert rows[0]["status"] == "success"
        assert rows[0]["duration_ms"] == 142
        # Arguments and result should be deserialized
        assert rows[0]["arguments"] == {"customer_id": "cus_123"}
        assert rows[0]["result"] == {"id": "cus_123", "email": "test@example.com"}

    def test_log_multiple_executions(self, fresh_db):
        for i in range(5):
            log_tool_execution(
                tool_id=f"github.get_repo_{i}",
                arguments={"owner": f"org_{i}", "repo": f"repo_{i}"},
                result={"id": i},
                status="success",
                duration_ms=100 + i,
            )
        rows = get_tool_executions(limit=10)
        assert len(rows) == 5

    def test_filter_by_status(self, fresh_db):
        log_tool_execution("tool.1", {}, {"ok": True}, "success", 10)
        log_tool_execution("tool.2", {}, {"ok": True}, "error", 20)
        log_tool_execution("tool.3", {}, {"ok": True}, "timeout", 30)
        rows = get_tool_executions(status="error", limit=10)
        assert len(rows) == 1
        assert rows[0]["tool_id"] == "tool.2"
        assert rows[0]["status"] == "error"

    def test_filter_by_tool_id(self, fresh_db):
        log_tool_execution("specific.tool", {}, {}, "success", 10)
        log_tool_execution("other.tool", {}, {}, "success", 10)
        rows = get_tool_executions(tool_id="specific.tool", limit=10)
        assert len(rows) == 1
        assert rows[0]["tool_id"] == "specific.tool"

    def test_error_status_logged(self, fresh_db):
        log_tool_execution(
            tool_id="failing.tool",
            arguments={"bad": "input"},
            result=None,
            status="error",
            duration_ms=5,
            error_message="Connection refused",
        )
        rows = get_tool_executions(tool_id="failing.tool", limit=10)
        assert len(rows) == 1
        assert rows[0]["error_message"] == "Connection refused"

    def test_limit_parameter(self, fresh_db):
        for i in range(20):
            log_tool_execution(f"tool.{i}", {}, {}, "success", 10)
        rows = get_tool_executions(limit=5)
        assert len(rows) == 5
