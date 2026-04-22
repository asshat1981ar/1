"""
Tests for admin approval of destructive tools.
Covers:
  - approve_destructive_tool MCP tool
  - token validation against MCP_ADMIN_TOKEN env var
  - 24-hour expiration enforcement
  - execution blocking without valid approval

TDD: Write tests first, then implement.
"""
from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timedelta, timezone

import pytest

from mcp_server import database


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def fresh_db():
    """In-memory database for each test."""
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    database.init_db(db_path)
    yield db_path
    try:
        os.unlink(db_path)
    except OSError:
        pass


@pytest.fixture
def destructive_tool():
    """A minimal tool record marked destructive and approved."""
    record = {
        "id": "db.drop_table",
        "name": "drop_table",
        "namespace": "db",
        "description": "Drop a database table",
        "source_type": "spec",
        "transport": "subprocess",
        "side_effect_level": "destructive",
        "permission_policy": "deny_by_default",
        "status": "approved",
        "confidence": 0.95,
        "version_hash": "abc123",
        "tags": [],
        "full_record": {},
    }
    database.upsert_tool(record)
    return record


# ---------------------------------------------------------------------------
# Database-level helpers
# ---------------------------------------------------------------------------

def get_approval_record(tool_id: str):
    """Return a dict for a DestructiveApproval row or None."""
    with database.get_session() as s:
        row = s.get(database.DestructiveApproval, tool_id)
        if not row:
            return None
        return {
            "tool_id": row.tool_id,
            "approver": row.approver,
            "reason": row.reason,
            "approved_at": row.approved_at,
            "expires_at": row.expires_at,
        }


def expire_approval(tool_id: str, offset_hours: float = -1):
    """Force expires_at to a past time so the approval is considered expired."""
    with database.get_session() as s:
        row = s.get(database.DestructiveApproval, tool_id)
        if row:
            row.expires_at = datetime.utcnow() + timedelta(hours=offset_hours)
            s.commit()


# ---------------------------------------------------------------------------
# DB model changes required before tests will pass
# ---------------------------------------------------------------------------

class TestDestructiveApprovalSchema:
    """Verify the destructive_approvals table has the required columns."""

    def test_approvals_table_has_tool_id_pk(self, fresh_db):
        # The table must exist after init_db is called
        with database.get_session() as s:
            # Just inserting and reading back is enough
            s.add(database.DestructiveApproval(
                tool_id="test.tool",
                approver="admin@test",
                reason="test",
                expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
            ))
            s.commit()
        row = get_approval_record("test.tool")
        assert row is not None
        assert row["tool_id"] == "test.tool"

    def test_approvals_table_has_approver_column(self, fresh_db):
        database.approve_destructive_tool("test.tool", "admin@example.com", "")
        row = get_approval_record("test.tool")
        assert row is not None
        assert row["approver"] == "admin@example.com"

    def test_approvals_table_has_expires_at_column(self, fresh_db):
        database.approve_destructive_tool("test.tool", "admin@test", "testing")
        row = get_approval_record("test.tool")
        assert row is not None
        assert "expires_at" in row
        # Default should be 24h from now
        expected = datetime.utcnow() + timedelta(hours=24)
        assert abs((row["expires_at"] - expected).total_seconds()) < 10


class TestApproveDestructiveToolDb:
    """Unit tests for database.approve_destructive_tool()."""

    def test_approve_records_tool_id(self, fresh_db):
        result = database.approve_destructive_tool("db.drop_table", "admin@test", "")
        assert result is True
        row = get_approval_record("db.drop_table")
        assert row is not None

    def test_approve_records_approver(self, fresh_db):
        database.approve_destructive_tool("db.drop_table", "admin@test", "")
        row = get_approval_record("db.drop_table")
        assert row["approver"] == "admin@test"

    def test_approve_records_reason(self, fresh_db):
        database.approve_destructive_tool("db.drop_table", "admin@test", "migration needed")
        row = get_approval_record("db.drop_table")
        assert row["reason"] == "migration needed"

    def test_approve_sets_expires_at_to_24h_from_now(self, fresh_db):
        database.approve_destructive_tool("db.drop_table", "admin@test", "")
        row = get_approval_record("db.drop_table")
        expected = datetime.utcnow() + timedelta(hours=24)
        assert abs((row["expires_at"] - expected).total_seconds()) < 5

    def test_approve_idempotent(self, fresh_db):
        database.approve_destructive_tool("db.drop_table", "admin@test", "first")
        database.approve_destructive_tool("db.drop_table", "admin@test", "second")
        # Still only one record
        all_rows = database.list_destructive_approvals()
        assert len(all_rows) == 1
        # Reason updated
        row = get_approval_record("db.drop_table")
        assert row["reason"] == "second"

    def test_approve_empty_tool_id_returns_false(self, fresh_db):
        assert database.approve_destructive_tool("", "admin@test", "") is False

    def test_approve_none_tool_id_returns_false(self, fresh_db):
        assert database.approve_destructive_tool(None, "admin@test", "") is False


class TestIsDestructiveApproved:
    """Unit tests for database.is_destructive_approved()."""

    def test_returns_true_when_approval_exists_and_not_expired(self, fresh_db):
        database.approve_destructive_tool("db.drop_table", "admin@test", "")
        assert database.is_destructive_approved("db.drop_table") is True

    def test_returns_false_when_no_approval(self, fresh_db):
        assert database.is_destructive_approved("db.drop_table") is False

    def test_returns_false_when_approval_expired(self, fresh_db):
        database.approve_destructive_tool("db.drop_table", "admin@test", "")
        expire_approval("db.drop_table", offset_hours=-1)
        assert database.is_destructive_approved("db.drop_table") is False

    def test_returns_true_for_approval_expires_in_future(self, fresh_db):
        database.approve_destructive_tool("db.drop_table", "admin@test", "")
        expire_approval("db.drop_table", offset_hours=+48)
        assert database.is_destructive_approved("db.drop_table") is True

    def test_returns_false_for_empty_tool_id(self, fresh_db):
        assert database.is_destructive_approved("") is False

    def test_returns_false_for_none_tool_id(self, fresh_db):
        assert database.is_destructive_approved(None) is False


class TestListDestructiveApprovals:
    """Unit tests for database.list_destructive_approvals()."""

    def test_returns_empty_list_when_no_approvals(self, fresh_db):
        assert database.list_destructive_approvals() == []

    def test_returns_one_approval(self, fresh_db):
        database.approve_destructive_tool("tool.one", "admin@test", "")
        rows = database.list_destructive_approvals()
        assert len(rows) == 1
        assert rows[0]["tool_id"] == "tool.one"

    def test_returns_multiple_approvals(self, fresh_db):
        database.approve_destructive_tool("tool.one", "admin@test", "")
        database.approve_destructive_tool("tool.two", "admin@test", "")
        rows = database.list_destructive_approvals()
        assert len(rows) == 2

    def test_does_not_return_expired_approvals(self, fresh_db):
        database.approve_destructive_tool("tool.active", "admin@test", "")
        database.approve_destructive_tool("tool.expired", "admin@test", "")
        expire_approval("tool.expired", offset_hours=-1)
        rows = database.list_destructive_approvals()
        assert all(r["expires_at"] > datetime.utcnow() for r in rows)
        assert any(r["tool_id"] == "tool.active" for r in rows)
        assert not any(r["tool_id"] == "tool.expired" for r in rows)


class TestClearDestructiveApproval:
    """Unit tests for database.clear_destructive_approval()."""

    def test_deletes_existing_approval(self, fresh_db):
        database.approve_destructive_tool("db.drop_table", "admin@test", "")
        result = database.clear_destructive_approval("db.drop_table")
        assert result is True
        assert database.is_destructive_approved("db.drop_table") is False

    def test_returns_false_when_no_approval_exists(self, fresh_db):
        result = database.clear_destructive_approval("nonexistent.tool")
        assert result is False

    def test_empty_tool_id_returns_false(self, fresh_db):
        assert database.clear_destructive_approval("") is False


# ---------------------------------------------------------------------------
# Server-level tests (MCP tool)
# ---------------------------------------------------------------------------

class TestApproveDestructiveToolServer:
    """Test the approve_destructive_tool MCP tool handler."""

    @pytest.fixture(autouse=True)
    def setup_env(self, fresh_db, monkeypatch):
        monkeypatch.setenv("MCP_ADMIN_TOKEN", "test-secret-token")

    def _call_approve(self, tool_id: str, admin_token: str, reason: str = "") -> dict:
        """Call _approve_destructive_tool as the server would."""
        from mcp_server.server import _approve_destructive_tool
        result = _approve_destructive_tool({
            "tool_id": tool_id,
            "admin_token": admin_token,
            "reason": reason,
        })
        # The handler returns list[TextContent]; parse JSON from first item
        return json.loads(result[0].text)

    def test_requires_admin_token_in_env(self, fresh_db, monkeypatch):
        """Without MCP_ADMIN_TOKEN set, approval must be rejected."""
        # Remove MCP_ADMIN_TOKEN entirely so os.environ.get returns ""
        monkeypatch.delenv("MCP_ADMIN_TOKEN", raising=False)
        monkeypatch.setenv("MCP_ADMIN_EMAIL", "admin@test")
        database.upsert_tool({
            "id": "db.drop_table",
            "name": "drop_table",
            "namespace": "db",
            "description": "Drop a table",
            "source_type": "spec",
            "transport": "subprocess",
            "side_effect_level": "destructive",
            "permission_policy": "deny_by_default",
            "status": "approved",
            "confidence": 0.9,
            "version_hash": "abc",
            "tags": [],
            "full_record": {},
        })
        resp = self._call_approve("db.drop_table", "any-token")
        assert resp.get("error") is not None
        assert "not configured" in resp["error"].lower() or "unauthorized" in resp["error"].lower()

    def test_rejects_wrong_token(self, fresh_db, monkeypatch):
        # Ensure clean env: remove any pre-existing token then set wrong one
        monkeypatch.delenv("MCP_ADMIN_TOKEN", raising=False)
        monkeypatch.setenv("MCP_ADMIN_TOKEN", "correct-token")
        database.upsert_tool({
            "id": "db.drop_table",
            "name": "drop_table",
            "namespace": "db",
            "description": "Drop a table",
            "source_type": "spec",
            "transport": "subprocess",
            "side_effect_level": "destructive",
            "permission_policy": "deny_by_default",
            "status": "approved",
            "confidence": 0.9,
            "version_hash": "abc",
            "tags": [],
            "full_record": {},
        })
        # Pass "wrong-token" when env has "correct-token" -> must be rejected
        resp = self._call_approve("db.drop_table", "wrong-token")
        assert resp.get("error") is not None
        assert "invalid" in resp["error"].lower() or "token" in resp["error"].lower()

    def test_accepts_correct_token(self, fresh_db, monkeypatch):
        monkeypatch.setenv("MCP_ADMIN_TOKEN", "correct-token")
        database.upsert_tool({
            "id": "db.drop_table",
            "name": "drop_table",
            "namespace": "db",
            "description": "Drop a table",
            "source_type": "spec",
            "transport": "subprocess",
            "side_effect_level": "destructive",
            "permission_policy": "deny_by_default",
            "status": "approved",
            "confidence": 0.9,
            "version_hash": "abc",
            "tags": [],
            "full_record": {},
        })
        resp = self._call_approve("db.drop_table", "correct-token", "migration")
        assert resp.get("status") == "approved"
        assert resp.get("tool_id") == "db.drop_table"

    def test_rejects_nonexistent_tool(self, fresh_db, monkeypatch):
        monkeypatch.setenv("MCP_ADMIN_TOKEN", "test-secret-token")
        resp = self._call_approve("nonexistent.tool", "test-secret-token")
        assert resp.get("error") is not None
        assert "not found" in resp["error"].lower()

    def test_rejects_non_destructive_tool(self, fresh_db, monkeypatch):
        monkeypatch.setenv("MCP_ADMIN_TOKEN", "test-secret-token")
        database.upsert_tool({
            "id": "db.read_table",
            "name": "read_table",
            "namespace": "db",
            "description": "Read a table",
            "source_type": "spec",
            "transport": "subprocess",
            "side_effect_level": "read",  # not destructive
            "permission_policy": "auto",
            "status": "approved",
            "confidence": 0.9,
            "version_hash": "abc",
            "tags": [],
            "full_record": {},
        })
        resp = self._call_approve("db.read_table", "test-secret-token")
        assert resp.get("error") is not None
        assert "not destructive" in resp["error"]

    def test_requires_tool_id(self, fresh_db, monkeypatch):
        monkeypatch.setenv("MCP_ADMIN_TOKEN", "test-secret-token")
        resp = self._call_approve("", "test-secret-token")
        assert resp.get("error") is not None


class TestExecutionBlocksUnapprovedDestructive:
    """Test that execute_tool blocks destructive tools without valid approval."""

    @pytest.fixture(autouse=True)
    def setup_env(self, fresh_db, monkeypatch):
        monkeypatch.setenv("MCP_ADMIN_TOKEN", "test-secret-token")

    def _call_execute(self, tool_id: str, confirmed: bool = False) -> dict:
        """Call _execute_tool as the server would."""
        import asyncio
        from mcp_server.server import _execute_tool
        result = asyncio.get_event_loop().run_until_complete(
            _execute_tool({"tool_id": tool_id, "confirmed": confirmed})
        )
        return json.loads(result[0].text)

    def test_blocks_destructive_without_approval(self, fresh_db, monkeypatch):
        monkeypatch.setenv("MCP_ADMIN_TOKEN", "test-secret-token")
        database.upsert_tool({
            "id": "db.drop_table",
            "name": "drop_table",
            "namespace": "db",
            "description": "Drop a table",
            "source_type": "spec",
            "transport": "subprocess",
            "side_effect_level": "destructive",
            "permission_policy": "deny_by_default",
            "status": "approved",
            "confidence": 0.9,
            "version_hash": "abc",
            "tags": [],
            "full_record": {},
            "execution_adapter": {"kind": "subprocess", "command": "echo done"},
        })
        resp = self._call_execute("db.drop_table")
        assert resp.get("error") is not None
        assert "destructive" in resp["error"].lower()
        assert "approved" in resp["error"].lower()

    def test_blocks_expired_approval(self, fresh_db, monkeypatch):
        monkeypatch.setenv("MCP_ADMIN_TOKEN", "test-secret-token")
        database.upsert_tool({
            "id": "db.drop_table",
            "name": "drop_table",
            "namespace": "db",
            "description": "Drop a table",
            "source_type": "spec",
            "transport": "subprocess",
            "side_effect_level": "destructive",
            "permission_policy": "deny_by_default",
            "status": "approved",
            "confidence": 0.9,
            "version_hash": "abc",
            "tags": [],
            "full_record": {},
            "execution_adapter": {"kind": "subprocess", "command": "echo done"},
        })
        # Pre-approve then expire it
        database.approve_destructive_tool("db.drop_table", "admin@test", "testing")
        expire_approval("db.drop_table", offset_hours=-1)
        resp = self._call_execute("db.drop_table")
        assert resp.get("error") is not None

    def test_allows_destructive_with_valid_approval(self, fresh_db, monkeypatch):
        monkeypatch.setenv("MCP_ADMIN_TOKEN", "test-secret-token")
        database.upsert_tool({
            "id": "db.drop_table",
            "name": "drop_table",
            "namespace": "db",
            "description": "Drop a table",
            "source_type": "spec",
            "transport": "subprocess",
            "side_effect_level": "destructive",
            "permission_policy": "deny_by_default",
            "status": "approved",
            "confidence": 0.9,
            "version_hash": "abc",
            "tags": [],
            "full_record": {},
            "execution_adapter": {"kind": "subprocess", "command": "echo done"},
        })
        database.approve_destructive_tool("db.drop_table", "admin@test", "ok")
        resp = self._call_execute("db.drop_table")
        # Approval check passes; execution may fail due to environment but
        # the error must NOT be about destructive tool not approved
        err = resp.get("error", "")
        assert "destructive" not in err.lower() and "approved" not in err.lower(), \
            f"Expected approval error, got: {err}"