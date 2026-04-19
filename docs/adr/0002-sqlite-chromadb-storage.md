# ADR 0002 — SQLite + ChromaDB Storage Strategy

**Date:** 2025-01  
**Status:** Accepted

---

## Context

The tool registry needs two access patterns:
1. Exact lookup by tool ID (fast key-value)
2. Semantic search by natural language query

We also need a human review queue and a failed-query log.

## Decision

Use **SQLite** (via SQLAlchemy) as the canonical registry store for all structured data (tool records, review queue, failed queries). Use **ChromaDB** as a semantic vector index layered on top of SQLite.

ChromaDB is an **optional** dependency. If not installed, `search_tools` falls back to substring text search over SQLite.

## Rationale

- SQLite is zero-dependency, serverless, and ships in the Python standard library via `sqlite3`
- No external service required for initial deployment
- ChromaDB operates in local-first mode (persists to disk), consistent with the zero-dependency philosophy
- Layered architecture means the system degrades gracefully when ChromaDB is absent

## Consequences

- SQLite is the single source of truth; ChromaDB is a derived index that can be rebuilt
- Multi-process or multi-host deployments will require migrating to PostgreSQL (tracked in ROADMAP v0.4)
- ChromaDB must be kept in sync whenever records are upserted (`vector_store.index_tool` called in `harvester.publish`)
