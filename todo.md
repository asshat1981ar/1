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

- [ ] **GraphQL adapter** (`mcp_server/harvester/extractors/` + `server.py`)
  - New `execution_adapter.kind = "graphql"` support in `execute_tool`
  - HTTP POST to `url_template` with `query` and `variables` fields
  - Policy enforcement identical to the REST adapter

- [ ] **Python function adapter** (`mcp_server/server.py`)
  - New `execution_adapter.kind = "python"` support
  - Dynamically import and call a local Python function by dotted path
  - Sandbox: disallow any module not listed in an explicit allowlist

- [ ] **`toolbank review` TUI** (`mcp_server/cli.py` + new `mcp_server/tui.py`)
  - Replace the current plain-text review loop with a `rich`-based interactive TUI
  - Keyboard shortcuts: `a` approve · `r` reject · `q` quit · `?` help
  - Show full `ToolbankRecord` details in a panel alongside the action menu

- [ ] **`toolbank export` command** (`mcp_server/cli.py`)
  - New CLI sub-command: `toolbank export [--format json|csv] [--output PATH]`
  - Exports all approved records from the SQLite registry
  - Document in `docs/API_REFERENCE.md`

- [ ] **HTTP cache expiry & invalidation** (`mcp_server/harvester/crawler.py`)
  - Respect `Cache-Control` / `Expires` headers from crawled pages
  - Add `--no-cache` flag (already in CLI spec, must be wired through)
  - Purge stale cache entries on each harvest run

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

- [ ] **Multi-source evidence merging** (`mcp_server/harvester/deduper.py`)
  - When the same tool appears in multiple docs pages, merge evidence arrays
  - Weighted confidence: average of source confidences, not just the winner's

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

- [ ] **Admin approval API for destructive tools** (`mcp_server/server.py`)
  - New MCP tool: `approve_destructive_tool(tool_id, admin_token)`
  - One-time approval stored in the registry; expires after 24 h
  - Must be documented in `docs/GUARDRAILS.md`

- [ ] **Webhook/event adapter** (`mcp_server/server.py`)
  - New `execution_adapter.kind = "webhook"` support
  - POST event payload to `url_template`; optional HMAC signing

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

- [ ] **Structured JSON logging** (all `mcp_server/` modules)
  - Replace `print`/basic logging with `structlog` or `logging` + JSON formatter
  - Log level controlled by `LOG_LEVEL` env var

- [ ] **Rate-limit retry with exponential backoff** (`mcp_server/harvester/crawler.py`)
  - Detect HTTP 429; retry with jitter up to 3 attempts
  - Configurable via `config/sources.yaml` per-source `retry_policy`

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
