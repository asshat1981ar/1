# Guardrails — Preventing Architectural Drift

This document defines **hard constraints** and **soft conventions** for this project. It exists to prevent gradual deviation from the intended design.

---

## 🔴 Hard Constraints (never violate)

### Security

1. **Destructive tools are always blocked by default.** The `deny_by_default` policy for `side_effect_level = destructive` must never be removed or bypassed without explicit administrator approval. This is enforced in `server.py::_execute_tool`.

2. **Subprocess adapters must always run sandboxed.** `_execute_subprocess` must check `adapter.get("sandbox", True)` and refuse if False. Non-sandboxed subprocess execution is not permitted.

3. **No secrets in source code.** All credentials must come from environment variables. No API keys, tokens, or passwords in committed files.

4. **robots.txt compliance is mandatory.** The crawler must check `robots.txt` before every fetch. Removing this check would violate the terms of service of crawled sites.

### Data Integrity

5. **The `ToolbankRecord` Pydantic model is the single source of truth.** Any change to the record schema must be reflected simultaneously in `mcp_server/models.py`, `toolbank/schemas/toolbank_record.schema.json`, and the verifier in `mcp_server/harvester/verifier.py`.

6. **`version_hash` must be updated whenever `description` or `input_schema` changes.** It is the drift-detection signal. Do not hardcode or skip it.

7. **Tool IDs follow the pattern `namespace.name` (both snake_case).** IDs with different formats break registry lookups and ChromaDB indexing.

### Architecture Boundaries

8. **The MCP server communicates via stdio only.** Do not add HTTP/WebSocket transport to `server.py` without a new ADR and a versioned config flag.

9. **The harvester pipeline is unidirectional.** Data flows: Crawler → Classifier → Extractor → Normaliser → Deduper → Verifier → Registry. Do not add reverse flows (e.g. registry writes feeding back into the extractor) without explicit design review.

10. **`ingest_tool_candidate` is internal only.** It must not be exposed as an MCP tool to external clients.

---

## 🟡 Soft Conventions (follow unless there's a documented reason not to)

### Python

- All public functions must have type hints.
- All public classes and functions must have docstrings.
- Use `from __future__ import annotations` at the top of every Python module.
- Prefer `httpx.AsyncClient` for outbound HTTP; do not add `requests` as a dependency.
- Lazy-import optional dependencies (`chromadb`, `openai`) to avoid hard failures when extras are not installed.

### JavaScript / Next.js

- Use the App Router (`app/` directory). Do not mix App Router and Pages Router.
- Mark client components with `"use client"` at the top.
- All styling via Tailwind CSS utility classes. Do not introduce a new CSS-in-JS library.
- Framer Motion is the only animation library. Do not add a second.

### Testing

- Every new Python module in `mcp_server/` must have a corresponding test class in `tests/test_toolbank.py` (or a new file in `tests/`).
- Do not delete or comment out existing tests without a documented reason in the PR.

### Documentation

- Every new feature must be reflected in `docs/FEATURES.md`.
- Every new CLI command must be documented in `docs/API_REFERENCE.md`.
- Significant architectural decisions must have an ADR in `docs/adr/`.
- `CHANGELOG.md` must be updated with every PR that changes behaviour.

---

## 🔵 Drift Detection Checklist

Run this checklist before merging any PR:

- [ ] `ToolbankRecord` schema changes are reflected in all three locations (models, JSON Schema, verifier)?
- [ ] New side-effect level or policy? `server.py` policy enforcement updated?
- [ ] New dependency added? `pyproject.toml` updated and advisory DB checked?
- [ ] New environment variable? Added to `docs/TECH_STACK.md` env table?
- [ ] New CLI command? Added to `docs/API_REFERENCE.md`?
- [ ] Breaking change? `CHANGELOG.md` entry added?
- [ ] New React component? Added to `docs/FEATURES.md` feature table?
- [ ] Tests pass? (`pytest tests/ -v`)

---

## Architecture Decision Records

All significant design decisions are recorded in `docs/adr/`. See the index below:

| ADR | Title |
|---|---|
| [0001](adr/0001-mcp-proxy-pattern.md) | MCP Proxy Pattern |
| [0002](adr/0002-sqlite-chromadb-storage.md) | SQLite + ChromaDB Storage Strategy |
| [0003](adr/0003-nextjs-marketing.md) | Next.js for Marketing Site |
| [0004](adr/0004-side-effect-policies.md) | Side-Effect Policy Enforcement |
