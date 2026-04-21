# Toolbank MCP + No-Bull Marketing — Optimal State Roadmap

> **Purpose:** Describes the project at its pinnacle point of operation, analyses the gap between
> the current state (v0.1 complete) and that vision, and provides a phased, ordered execution
> plan to get there. Implementation must follow `system_prompt.md` conventions at every step.

---

## 1 · Vision — What the System Looks Like at Its Peak

### Toolbank MCP (peak capability)

At full maturity the Toolbank MCP is a **self-healing, autonomous API intelligence layer** that
any LLM agent can plug into via the MCP protocol to discover and execute virtually any
publicly-documented API or CLI without the agent having prior knowledge of those APIs.

Key pinnacle behaviours:

| Capability | What it does |
|---|---|
| **Omnivorous harvesting** | Ingests OpenAPI 2/3, GraphQL introspection, GitHub READMEs, CLI `--help` outputs, llms.txt, MCP server listings, and Python SDK docstrings — whatever format a source publishes in. |
| **Semantic search** | Natural-language queries ("send a transactional email") resolve to the best-matching tools across thousands of records via ChromaDB embeddings, with namespace and side-effect filters. |
| **Policy-safe execution** | Every tool execution passes through a three-tier policy gate: read tools run immediately, write tools require an explicit confirmation pass, destructive tools are hard-blocked until an admin grants a time-bounded approval. |
| **Self-improving loop** | Failed `search_tools` queries are persisted. A gap-miner scheduled job analyses these failures, infers missing capability clusters, generates seed URLs, and triggers new harvest runs automatically. |
| **Zero-drift registry** | Each time a source page changes its API, the verifier detects schema drift (version_hash mismatch), demotes the record to `verified` status, and queues it for human review. |
| **Multi-tenant SaaS** | Teams access a hosted instance with per-workspace tool registries, verified publisher namespaces, and a public marketplace UI for browsing and previewing tools. |
| **Observable at scale** | Prometheus metrics, structured JSON logging, and an optional PostgreSQL backend allow horizontal scaling and standard DevOps tooling. |
| **Authenticated & audited** | Bearer-token auth on the MCP endpoint, full execution audit log, and rate-limit retry logic with exponential backoff. |

### No-Bull Marketing (peak capability)

At full maturity the marketing site is a **conversion-optimised, accessible, and CMS-driven
single-page experience** that communicates the Toolbank value proposition with zero fluff.

Key pinnacle behaviours:

| Capability | What it does |
|---|---|
| **Scroll-aware navigation** | `StickyNav` highlights the active section in real time as users scroll, giving instant orientation. |
| **Social proof** | `ProofSection` displays animated metric counters, client logos, and rotating case studies pulled from a headless CMS. |
| **CTA form** | Honeypot-protected form with server-side validation converts visitors directly from the page. |
| **Full-screen hero video** | `HeroVideo` plays a looping, muted background video with a low-res blur poster for fast initial paint. |
| **Dark/light mode** | Tailwind `dark:` classes + `localStorage` persistence. |
| **Privacy-first analytics** | Plausible or self-hosted Umami — no cookies, no GDPR consent banner. |
| **Accessibility** | WCAG 2.1 AA throughout; automated Lighthouse/axe CI gate. |

---

## 2 · Current State Gap Analysis

| Area | Status | Gap |
|---|---|---|
| Toolbank MCP v0.1 foundation | ✅ Complete | — |
| No-Bull hero + CTA + nav + footer | ✅ Complete | — |
| `StickyNav` component | 🔲 Stub | Not implemented |
| `ProofSection` component | 🔲 Stub | Not implemented |
| Public media assets | 🔲 Missing | `hero.mp4`, `hero-blur.jpg`, `no-bull-deck.pdf` absent |
| GraphQL execution adapter | 🔲 Not started | `execute_tool` only handles HTTP + subprocess |
| Python function adapter | 🔲 Not started | No local-function execution path |
| `toolbank review` TUI | 🔲 Plain text | No rich interactive interface |
| `toolbank export` command | 🔲 Not started | No CSV/JSON export |
| HTTP cache expiry & `--no-cache` | 🔲 Partial | Flag exists in CLI but not wired to crawler logic |
| CI/CD workflows | ✅ Files exist | Need status badge + pip-audit + npm audit |
| Scheduled harvest commit-back | 🔲 Partial | Workflow harvests but does not commit new records |
| GraphQL introspection extractor | 🔲 Not started | No `graphql_extractor.py` |
| MCP server listing extractor | 🔲 Not started | No smithery.ai / mcp.so scraper |
| SDK extractor | 🔲 Not started | No `sdk_extractor.py` |
| Multi-source evidence merging | 🔲 Not started | Deduper keeps winner only |
| Tool versioning | 🔲 Not started | No `tool_versions` table |
| Admin approval API | 🔲 Not started | No `approve_destructive_tool` MCP tool |
| Webhook adapter | 🔲 Not started | No webhook execution kind |
| Namespace priority weighting | 🔲 Not started | ChromaDB scores not boosted by priority |
| PostgreSQL registry option | 🔲 Not started | Hard-coded SQLite only |
| Prometheus metrics | 🔲 Not started | No `/metrics` endpoint |
| Structured JSON logging | 🔲 Not started | Using `print` / basic logging |
| Rate-limit retry with backoff | 🔲 Not started | Crawler does not retry on 429 |
| Distributed harvest queue | 🔲 Not started | No Celery/ARQ backend |
| API token auth on MCP server | 🔲 Not started | No Bearer token validation |
| Hosted SaaS / marketplace UI | 🔲 Not started | v1.0 milestone |
| CMS-driven case studies | 🔲 Not started | Static data only |
| Dark/light mode toggle | 🔲 Not started | No theme toggle |
| Privacy-first analytics | 🔲 Not started | No analytics integrated |
| End-to-end Playwright tests | 🔲 Not started | Unit tests only |
| Dependency audit in CI | 🔲 Not started | No pip-audit / npm audit step |

---

## 3 · Phased Execution Plan

Phases follow semantic versioning already established in `todo.md`. Each phase must leave the
codebase in a passing-tests, deployable state before the next phase begins.

---

### Phase 1 — v0.2 Hardening (current sprint)

All items produce visible, user-facing value and close the most critical gaps.

#### 1.1 Frontend — `StickyNav` component

**File:** `components/StickyNav.jsx`

- Mark `"use client"`.
- Accept a `sections` prop: `Array<{ id: string, label: string }>`.
- Use `IntersectionObserver` to track which section is currently in the viewport.
- Render a fixed left-side vertical nav; animate the active indicator with Framer Motion.
- Wire into `app/page.jsx` with a `SECTIONS` constant:
  `[{ id: "hero", label: "Home" }, { id: "proof", label: "Results" }, { id: "cta", label: "Contact" }]`.
- Add `id` props to `<HeroVideo>`, `<ProofSection>`, `<CTAFormSection>` wrapper divs.

#### 1.2 Frontend — `ProofSection` component

**File:** `components/ProofSection.jsx`

- Mark `"use client"`.
- Static data sourced from `lib/proof-data.js` (create this file).
  - Three case studies: `{ client, result, description }`.
  - Four metrics: `{ value, label }` (e.g. `{ value: "3.2×", label: "avg. ROI" }`).
  - Six client logo entries: `{ name, slug }` (rendered as text badges; real logos deferred to CMS).
- Animated metric counters using `useInView` + `useEffect`.
- Alternating card layout for case studies.
- Wire into `app/page.jsx`.

#### 1.3 Backend — GraphQL execution adapter

**Files:** `mcp_server/server.py`

- Add `elif kind == "graphql":` branch to `_execute_tool`.
- New `_execute_graphql(record, adapter, arguments)` async function.
- Adapter fields: `url_template`, `query` (GraphQL query string with `$variable` placeholders),
  `variables_map` (dict mapping adapter variables to argument keys).
- Policy enforcement identical to HTTP adapter.
- Add `AdapterKind.graphql` usage to tests.

#### 1.4 Backend — Python function adapter

**Files:** `mcp_server/server.py`

- Add `elif kind == "python_func":` branch.
- New `_execute_python_func(record, adapter, arguments)` function (synchronous).
- Adapter fields: `module` (dotted path), `function` (function name), `allowlist`
  (list of allowed module prefixes).
- Dynamically import via `importlib.import_module`; validate module against `allowlist` before
  importing.
- Reject execution if module is not in `allowlist`.

#### 1.5 CLI — `toolbank review` rich TUI

**Files:** `mcp_server/tui.py` (new), `mcp_server/cli.py`

- Install `rich` (check advisory DB first).
- New `mcp_server/tui.py` module exposing `run_review_tui(items)`.
- Use `rich.live.Live` + `rich.layout.Layout` for the panel.
- Left panel: full JSON record rendered with `rich.syntax.Syntax`.
- Right panel: action menu (`a` approve · `r` reject · `s` skip · `q` quit · `?` help).
- Replace the `input()` loop in `cmd_review` with `run_review_tui`.

#### 1.6 CLI — `toolbank export` command

**Files:** `mcp_server/cli.py`, `docs/API_REFERENCE.md`

- New `cmd_export(args)` function.
- Arguments: `--format {json,csv}` (default `json`), `--output PATH` (default stdout).
- Fetches all `approved` records from `database.list_tools(status="approved")`.
- JSON: write pretty-printed array.
- CSV: write header row + one row per record using `csv.DictWriter`.
- Register as `sub.add_parser("export", ...)`.
- Document in `docs/API_REFERENCE.md`.

#### 1.7 Crawler — HTTP cache expiry & `--no-cache`

**Files:** `mcp_server/harvester/crawler.py`

- In `Crawler.__init__`, accept `use_cache: bool` (already there); wire it so that when
  `use_cache=False` the in-memory cache dict is bypassed entirely.
- Parse `Cache-Control: max-age=N` and `Expires` headers from responses; store the expiry
  timestamp alongside cached content.
- On cache lookup, check expiry; evict and re-fetch stale entries.
- Add `purge_stale()` method called at the start of each `harvest()` run.

#### 1.8 CI — add dependency audit step

**File:** `.github/workflows/ci.yml`

- Add `pip install pip-audit` + `pip-audit --requirement requirements.txt --skip-editable`
  step after the install step.
- Add `npm audit --audit-level=high` step in the Next.js job.
- Add CI status badge to `README.md`.

---

### Phase 2 — v0.3 Extensibility

#### 2.1 GraphQL introspection extractor

**File:** `mcp_server/harvester/extractors/graphql_extractor.py`

- POST `{ query: "{ __schema { ... } }" }` to detected GraphQL endpoints.
- Convert every Query/Mutation/Subscription field to a `ToolbankRecord`.
- Register in `classifier.py` (detect `Content-Type: application/graphql`) and
  `mcp_server/harvester/extractors/__init__.py`.

#### 2.2 Multi-source evidence merging

**File:** `mcp_server/harvester/deduper.py`

- When `deduplicate` identifies a duplicate pair, merge `evidence` arrays instead of discarding
  the lower-confidence record's evidence.
- Recompute `confidence` as the weighted average of all merged source confidences.

#### 2.3 MCP server listing extractor

**File:** `mcp_server/harvester/extractors/mcp_listing_extractor.py`

- Scrape `smithery.ai` and `mcp.so` for published MCP server manifests.
- Map MCP tool schemas directly to `ToolbankRecord`.

#### 2.4 SDK extractor

**File:** `mcp_server/harvester/extractors/sdk_extractor.py`

- Parse Python package docstrings via the `ast` module.
- Target public functions decorated with `@tool`, `@mcp.tool`, or similar.

#### 2.5 Tool versioning

**Files:** `mcp_server/database.py`, `mcp_server/models.py`

- Add a `tool_versions` SQLAlchemy table: `(tool_id, version_hash, changed_at, diff TEXT)`.
- On every `upsert_tool`, check whether `version_hash` changed; if so, insert a row into
  `tool_versions` with a JSON diff of description and input_schema.
- Expose history via `toolbank list --history <tool_id>`.

#### 2.6 Admin approval API for destructive tools

**Files:** `mcp_server/server.py`, `docs/GUARDRAILS.md`

- New MCP tool: `approve_destructive_tool(tool_id: str, admin_token: str)`.
- Validates `admin_token` against `MCP_ADMIN_TOKEN` env var.
- Stores a time-bounded approval (24 h) in a new `destructive_approvals` SQLite table.
- `_execute_tool` checks this table before hard-blocking destructive tools.
- Document policy in `docs/GUARDRAILS.md`.

#### 2.7 Webhook adapter

**Files:** `mcp_server/server.py`, `mcp_server/models.py`

- New `AdapterKind.webhook`.
- `_execute_webhook(record, adapter, arguments)`: POST event payload to `url_template`;
  optional HMAC-SHA256 signing using `adapter.get("hmac_secret_env")`.

#### 2.8 Namespace priority weighting

**Files:** `mcp_server/vector_store.py`, `config/sources.yaml`

- Sources may carry a `priority` float (0.0–1.0) in `config/sources.yaml`.
- On index, store `priority` as ChromaDB metadata.
- In `search_tools`, multiply distance score by `(1 + priority)` before ranking.

---

### Phase 3 — v0.4 Scale & Observability

#### 3.1 PostgreSQL registry option

**File:** `mcp_server/database.py`

- Read `DATABASE_URL` env var; fall back to SQLite `toolbank/registry.db` when absent.
- Use SQLAlchemy engine factory — no manual SQL dialect switching.

#### 3.2 Structured JSON logging

**Files:** all `mcp_server/` modules

- Replace `logging.basicConfig` with a JSON formatter (use stdlib `logging` + a
  `JsonFormatter` class; do not add `structlog` unless it is already a dependency).
- `LOG_LEVEL` env var controls log level.

#### 3.3 Rate-limit retry with exponential backoff

**File:** `mcp_server/harvester/crawler.py`

- Detect HTTP 429; retry up to 3 times with jitter: `base * 2^attempt + random(0, 1)`.
- Configurable per-source `retry_policy` in `config/sources.yaml`.

#### 3.4 Distributed harvest queue

**File:** `mcp_server/harvester/harvester.py`

- If `REDIS_URL` env var is set, submit harvest tasks to an ARQ queue.
- Fall back to sequential in-process execution when `REDIS_URL` is absent.

#### 3.5 API token authentication for MCP server

**File:** `mcp_server/server.py`

- Read `MCP_API_TOKEN` from env at startup.
- Validate `Authorization: Bearer <token>` on every MCP call.
- Return `{"error": "Unauthorized"}` for unauthenticated calls when token is configured.

---

### Phase 4 — v1.0 Production

#### 4.1 Hosted Toolbank SaaS

- Multi-tenant registry with per-workspace tool isolation.
- Workspace creation + user management API.
- Namespace ownership verification flow (DNS TXT or GitHub membership check).

#### 4.2 Public tool marketplace UI

- Next.js App Router pages under `app/marketplace/`.
- Server-side rendered tool listings with search, filters, and preview panels.
- Authentication via NextAuth.js or Clerk.

#### 4.3 Toolbank SDK

- `toolbank-sdk` Python package with typed client wrapping `search_tools` + `execute_tool`.
- TypeScript client generated from the MCP tool schemas.

#### 4.4 No-Bull Marketing — CMS integration

- Connect `ProofSection` to Contentful or Sanity for CMS-driven case studies.
- Dark/light mode toggle using Tailwind `dark:` classes + `localStorage`.
- Integrate Plausible analytics (no cookies).

#### 4.5 End-to-end Playwright tests

- Full harvest → search → execute flow covered by Playwright.
- Run in CI on every PR.

---

## 4 · Cross-Cutting Concerns (apply to every phase)

1. **Every new Python module** → corresponding test class in `tests/`.
2. **Every new feature** → entry in `docs/FEATURES.md`.
3. **Every new CLI command or MCP tool** → entry in `docs/API_REFERENCE.md`.
4. **Every significant design decision** → new ADR in `docs/adr/`.
5. **Every PR that changes behaviour** → entry in `CHANGELOG.md`.
6. **Before adding any new dependency** → run `gh-advisory-database` tool + `pip-audit`.
7. **Hard constraints in `system_prompt.md` Section 5** → must be respected at all times.

---

## 5 · Definition of Done (per item)

A roadmap item is complete only when:

- [ ] Feature works as described in this document and in `todo.md`
- [ ] All existing tests pass (`pytest tests/ -v`)
- [ ] New code is covered by at least one new test
- [ ] `npm run build` succeeds (for frontend changes)
- [ ] No new linter warnings
- [ ] `docs/FEATURES.md` updated
- [ ] `CHANGELOG.md` entry added under `[Unreleased]`
- [ ] `todo.md` checkbox for this item is checked
- [ ] Hard constraints in `system_prompt.md` Section 5 respected
