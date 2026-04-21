"""
SQLite-backed tool registry using SQLAlchemy.
Stores canonical ToolbankRecord objects and failed query logs.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    Float,
    Integer,
    String,
    Text,
    create_engine,
    event,
)
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Engine / session factory
# ---------------------------------------------------------------------------

_engine = None
_SessionLocal = None


def init_db(db_path: str = "toolbank/registry.db") -> None:
    """Initialise (or re-use) the SQLite database."""
    global _engine, _SessionLocal
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    _engine = create_engine(f"sqlite:///{db_path}", echo=False)

    # Enable WAL mode for better concurrent reads
    @event.listens_for(_engine, "connect")
    def set_wal(dbapi_conn, _connection_record):
        dbapi_conn.execute("PRAGMA journal_mode=WAL")

    Base.metadata.create_all(_engine)
    _SessionLocal = sessionmaker(bind=_engine, expire_on_commit=False)
    logger.info("Database initialised at %s", db_path)


def get_session() -> Session:
    if _SessionLocal is None:
        init_db()
    return _SessionLocal()


# ---------------------------------------------------------------------------
# ORM models
# ---------------------------------------------------------------------------

class Base(DeclarativeBase):
    pass


class ToolRecord(Base):
    __tablename__ = "tools"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False, index=True)
    namespace = Column(String, nullable=False, index=True)
    description = Column(Text, nullable=False)
    source_type = Column(String, nullable=False)
    transport = Column(String, nullable=False)
    side_effect_level = Column(String, nullable=False)
    permission_policy = Column(String, nullable=False)
    status = Column(String, nullable=False, default="draft", index=True)
    confidence = Column(Float, nullable=False, default=0.0)
    version_hash = Column(String, nullable=False)
    tags = Column(JSON, nullable=False, default=list)
    full_record = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class FailedQueryLog(Base):
    __tablename__ = "failed_queries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_goal = Column(Text, nullable=False)
    failed_query = Column(Text, nullable=False)
    tools_returned = Column(JSON, nullable=False, default=list)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class ReviewQueueItem(Base):
    __tablename__ = "review_queue"

    id = Column(Integer, primary_key=True, autoincrement=True)
    record_id = Column(String, nullable=False, index=True)
    candidate_json = Column(JSON, nullable=False)
    confidence = Column(Float, nullable=False)
    issues = Column(JSON, nullable=False, default=list)
    status = Column(String, nullable=False, default="pending")  # pending|approved|rejected
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class DestructiveApproval(Base):
    __tablename__ = "destructive_approvals"

    tool_id = Column(String, primary_key=True)
    approver = Column(String, nullable=False)
    reason = Column(Text, nullable=True)
    approved_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


# ---------------------------------------------------------------------------
# Registry CRUD helpers
# ---------------------------------------------------------------------------

def upsert_tool(record_dict: dict[str, Any]) -> ToolRecord:
    """Insert or update a tool record."""
    with get_session() as session:
        existing = session.get(ToolRecord, record_dict["id"])
        row = ToolRecord(
            id=record_dict["id"],
            name=record_dict["name"],
            namespace=record_dict["namespace"],
            description=record_dict["description"],
            source_type=record_dict.get("source_type", "docs"),
            transport=record_dict.get("transport", "rest"),
            side_effect_level=record_dict.get("side_effect_level", "read"),
            permission_policy=record_dict.get("permission_policy", "auto"),
            status=record_dict.get("status", "draft"),
            confidence=record_dict.get("confidence", 0.0),
            version_hash=record_dict.get("version_hash", ""),
            tags=record_dict.get("tags", []),
            full_record=record_dict,
        )
        if existing:
            row.created_at = existing.created_at
            session.merge(row)
        else:
            session.add(row)
        session.commit()
        return row


def get_tool(tool_id: str) -> dict[str, Any] | None:
    """Retrieve a tool record by id."""
    with get_session() as session:
        row = session.get(ToolRecord, tool_id)
        return row.full_record if row else None


def list_tools(
    status: str | None = None,
    namespace: str | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """List tool records with optional filters."""
    with get_session() as session:
        query = session.query(ToolRecord)
        if status:
            query = query.filter(ToolRecord.status == status)
        if namespace:
            query = query.filter(ToolRecord.namespace == namespace)
        rows = query.limit(limit).all()
        return [r.full_record for r in rows]


def log_failed_query(user_goal: str, failed_query: str, tools_returned: list[str]) -> None:
    """Persist a failed search for the Gap Miner."""
    with get_session() as session:
        session.add(
            FailedQueryLog(
                user_goal=user_goal,
                failed_query=failed_query,
                tools_returned=tools_returned,
            )
        )
        session.commit()


def get_failed_queries(limit: int = 50) -> list[dict[str, Any]]:
    """Return recent failed queries for gap mining."""
    with get_session() as session:
        rows = (
            session.query(FailedQueryLog)
            .order_by(FailedQueryLog.timestamp.desc())
            .limit(limit)
            .all()
        )
        return [
            {
                "id": r.id,
                "user_goal": r.user_goal,
                "failed_query": r.failed_query,
                "tools_returned": r.tools_returned,
                "timestamp": r.timestamp.isoformat() if r.timestamp else "",
            }
            for r in rows
        ]


def enqueue_for_review(record_id: str, candidate: dict, confidence: float, issues: list[str]) -> None:
    """Add a candidate to the human review queue."""
    with get_session() as session:
        session.add(
            ReviewQueueItem(
                record_id=record_id,
                candidate_json=candidate,
                confidence=confidence,
                issues=issues,
            )
        )
        session.commit()


def get_review_queue(status: str = "pending") -> list[dict[str, Any]]:
    """Retrieve items awaiting human review."""
    with get_session() as session:
        rows = (
            session.query(ReviewQueueItem)
            .filter(ReviewQueueItem.status == status)
            .order_by(ReviewQueueItem.created_at)
            .all()
        )
        return [
            {
                "queue_id": r.id,
                "record_id": r.record_id,
                "candidate": r.candidate_json,
                "confidence": r.confidence,
                "issues": r.issues,
                "status": r.status,
            }
            for r in rows
        ]


def approve_review_item(queue_id: int) -> bool:
    """Approve a queued candidate and promote it to the registry."""
    with get_session() as session:
        row = session.get(ReviewQueueItem, queue_id)
        if not row:
            return False
        row.status = "approved"
        # Promote to tools table with approved status
        candidate = dict(row.candidate_json)
        candidate["status"] = "approved"
        session.commit()
    upsert_tool(candidate)
    return True


def reject_review_item(queue_id: int) -> bool:
    """Reject a queued candidate."""
    with get_session() as session:
        row = session.get(ReviewQueueItem, queue_id)
        if not row:
            return False
        row.status = "rejected"
        session.commit()
    return True


def approve_destructive_tool(tool_id: str, approver: str, reason: str = "") -> bool:
    """Record an administrator's approval for a destructive tool.

    Returns True if the approval was recorded (or already existed).
    Returns False if tool_id is empty.
    """
    if not tool_id:
        return False
    with get_session() as session:
        existing = session.get(DestructiveApproval, tool_id)
        if existing:
            # Idempotent – update reason and approver on re-approval
            existing.approver = approver
            existing.reason = reason
            existing.approved_at = datetime.now(timezone.utc)
        else:
            session.add(
                DestructiveApproval(
                    tool_id=tool_id,
                    approver=approver,
                    reason=reason,
                )
            )
        session.commit()
        return True


def is_destructive_approved(tool_id: str) -> bool:
    """Return True if a destructive tool has been administratively approved."""
    if not tool_id:
        return False
    with get_session() as session:
        row = session.get(DestructiveApproval, tool_id)
        return row is not None


def clear_destructive_approval(tool_id: str) -> bool:
    """Remove an approval record for a destructive tool.

    Returns True if a record was deleted, False if there was no record.
    """
    if not tool_id:
        return False
    with get_session() as session:
        row = session.get(DestructiveApproval, tool_id)
        if not row:
            return False
        session.delete(row)
        session.commit()
        return True
