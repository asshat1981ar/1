# TODO — Toolbank MCP + ToolBank Webapp

> Gap analysis from the current state (v0.1 complete, v0.2 in progress) to the finished v1.0 product.
> Status: ✅ Done · 🚧 In Progress · 🔲 Planned · 💡 Future

---

## v0.2 — Hardening (current sprint)

### Frontend — ToolBank Webapp

- [x] **`StickyNav` component** (`components/StickyNav.jsx`)
  - Scroll-aware section highlighting using `IntersectionObserver`
  - Smooth active-state indicator transitions via Framer Motion
  - Side-rail nav (hidden on mobile, visible on lg+ screens)
  - Wired into `app/page.jsx` alongside Hero, ProofSection, ScrapeSection

- [x] **`ProofSection` component** (`components/ProofSection.jsx`)
  - Displays supported source types (OpenAPI, GraphQL, MCP, Docs)
  - Animated stat counters
  - Wired into `app/page.jsx`

- [x] **Hero / tool-search component** (`components/HeroVideo.jsx`)
  - Full-screen gradient hero with tool search input
  - Links to Scrape and Sources sections

- [x] **Scrape form component** (`components/CTAFormSection.jsx`)
  - URL + source-type form to trigger a harvest
  - Honeypot spam prevention
  - Success state with "scrape another" reset

- [ ] **Public media assets** (`public/media/`)
  - No longer required — video hero removed

### Backend — Toolbank MCP

- [x] **GraphQL adapter** (`mcp_server/server.py`)
  - `execution_adapter.kind = "graphql"` supported in `execute_tool`
  - HTTP POST to `url_template` with `query` and `variables` fields
  - Policy enforcement identical to the REST adapter
  - ✅ Done: two `_execute_graphql` implementations at lines 548 and 743

- [x] **Python function adapter** (`mcp_server/server.py`)
  - `execution_adapter.kind = "python"` and `"python_func"` supported
  - Dynamically import and call a local Python function by dotted path
  - Sandbox: `_PYTHON_ADAPTER_ALLOWLIST` disallows unlisted modules
  - ✅ Done: `_execute_python` (line 628) and `_execute_python_func` (line 786)

- [x] **`toolbank review` TUI** (`mcp_server/tui.py`)
  - Rich-based interactive TUI with `run_review_tui`, `_plain_review`
  - Keyboard shortcuts: `a` approve · `r` reject · `q` quit · `?` help
  - `_build_table` (line 4) and `_show_detail` (line 14) helpers
  - ✅ Done

- [x] **`toolbank export` command** (`mcp_server/cli.py`)
  - CLI sub-command: `toolbank export [--format json|csv] [--output PATH]`
  - Exports all approved records from the SQLite registry
  - `cmd_export` at line 96
  - ✅ Done — docs/API_REFERENCE.md not yet created

- [x] **HTTP cache expiry & invalidation** (`mcp_server/harvester/crawler.py`)
  - `http_cache` SQLite table: url, content, etag, last_modified, expires_at, cached_at
  - `Cache-Control: max-age=N` and `Expires` header parsing
  - `--no-cache` wired: `use_cache=False` bypasses read, overwrites on write
  - Stale entries purged on each harvest run
  - Commit `72a9c4b`

### Infrastructure

- [ ] **CI pipeline** (`.github/workflows/ci.yml`)
  - Trigger: every PR and push to `main`
  - Steps: `pip install -e ".[all]"` → `pytest tests/ -v` → `npm install` → `npm run build`
  - Add status badge to `README.md`

- [ ] **Scheduled harvest workflow** (`.github/workflows/harvest-scheduled.yml`)
  - Cron: daily at 02:00 UTC
  - Step: `toolbank harvest --config config/sources.yaml`
  - Commit any new records back to the repo (or open a PR)

---

## v0.3 — Extensibility

- [x] **Multi-source evidence merging** (`mcp_server/harvester/deduper.py`)
  - Evidence arrays merged on duplicate (same name+namespace)
  - Weighted confidence: `sum(evidence_confidence * source_confidence) / sum(source_confidence)`
  - `merged_from` metadata tracks source_confidence per evidence item
  - Commit `fbd8eaf`

- [ ] **GraphQL introspection extractor** (`mcp_server/harvester/extractors/graphql_extractor.py`)
  - POST `{ __schema { ... } }` to detected GraphQL endpoints
  - Convert every Query/Mutation/Subscription field to a `ToolbankRecord`
  - Register in `classifier.py` and `__init__.py`

- [ ] **MCP server listing extractor** (`mcp_server/harvester/extractors/mcp_listing_extractor.py`)
  - Scrape smithery.ai and mcp.so for published MCP server manifests
  - Map MCP tool schemas directly to `ToolbankRecord`

- [ ] **SDK extractor** (`mcp_server/harvester/extractors/sdk_extractor.py`)
  - Parse Python package docstrings via `ast` module
  - Target: public functions decorated with `@tool` or similar

- [ ] **Tool versioning** (`mcp_server/database.py` + `mcp_server/models.py`)
  - Add a `tool_versions` table tracking `(tool_id, version_hash, changed_at, diff)`
  - Expose history via `toolbank list --history <tool_id>`

- [x] **Admin approval API for destructive tools** (`mcp_server/server.py`)
  - MCP tool `approve_destructive_tool(tool_id, admin_token)` registered
  - `MCP_ADMIN_TOKEN` env var validation
  - `destructive_approvals` table: tool_id, approved_at, expires_at, admin
  - 24h TTL; execution blocked without valid unexpired approval
  - Commit `6157c3c`

- [x] **Webhook/event adapter** (`mcp_server/server.py`)
  - `execution_adapter.kind = "webhook"` supported in `execute_tool`
  - `_execute_webhook` at line 432 with template substitution for URL/headers/body
  - ✅ Done — HMAC signing not yet implemented

- [ ] **Namespace priority weighting** (`mcp_server/vector_store.py`)
  - Allow `config/sources.yaml` entries to carry a `priority` float
  - Boost search scores for high-priority namespaces

---

## v0.4 — Scale & Observability

- [ ] **PostgreSQL registry option** (`mcp_server/database.py`)
  - Accept `DATABASE_URL` env var; fall back to SQLite when absent
  - Use SQLAlchemy dialects — no manual SQL

- [ ] **Prometheus metrics** (`mcp_server/server.py`)
  - Track: search latency, harvest throughput, tool execution count, error rates
  - Expose `/metrics` endpoint (optional HTTP sidecar, guarded by env flag)

- [x] **Structured JSON logging** (`mcp_server/logging_config.py`)
  - `JsonFormatter` class: JSON per log line with timestamp, level, logger, message
  - `setup_logging()` reads `LOG_LEVEL` env var (defaults INFO)
  - All `print()` in cli.py replaced with logger calls
  - Commit `d167046`

- [x] **Rate-limit retry with exponential backoff** (`mcp_server/harvester/crawler.py`)
  - Backoff formula: `min(base * 2^attempt + jitter, 60s)`
  - `Retry-After` header respected (integer seconds)
  - 3 retries max; WARNING per retry, ERROR after exhaustion
  - `retry_policy` dict configurable via sources.yaml
  - Commit `d167046` (combined with logging)

- [ ] **Distributed harvest queue** (`mcp_server/harvester/harvester.py`)
  - Optional Celery or ARQ backend when `REDIS_URL` env var is set
  - Fall back to in-process sequential harvesting when not set

- [ ] **API token authentication for MCP server** (`mcp_server/server.py`)
  - Read `MCP_API_TOKEN` from env; validate Bearer token on every call
  - Unauthenticated calls return `{"error": "Unauthorized"}`

---

## v1.0 — Production

### Platform

- [ ] **Hosted Toolbank SaaS** — multi-tenant registry with per-workspace isolation
- [ ] **Public tool marketplace UI** — browse, search, and preview tools in a web app
- [ ] **Verified publisher program** — namespace ownership verification flow
- [ ] **Toolbank SDK** — Python + TypeScript client libraries with type stubs

### ToolBank Webapp (v1.0)

- [ ] **Tool browse / search results page** — paginated registry listing with filters by source type and namespace
- [ ] **Tool detail page** — view full schema, evidence, and execution adapter for a single tool
- [ ] **Dark / light mode toggle** — Tailwind `dark:` classes + `localStorage` persistence
- [ ] **Privacy-first analytics** — Plausible or self-hosted Umami; no cookies

---

## Cross-cutting concerns (any version)

- [ ] **End-to-end test suite** — Playwright tests covering the full harvest → search → execute flow
- [ ] **Dependency audit** — run `pip-audit` + `npm audit` in CI on every PR
- [ ] **Secret scanning** — add `gitleaks` or GitHub secret scanning to CI
- [ ] **Accessibility audit** — run `axe` or Lighthouse on the marketing site in CI
- [ ] **`CHANGELOG.md` discipline** — every PR that changes behaviour must add an entry
