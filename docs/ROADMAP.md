# Roadmap

> Status legend: ✅ Done · 🚧 In Progress · 🔲 Planned · 💡 Idea

---

## v0.1 — Foundation ✅

- [x] Pydantic `ToolbankRecord` schema
- [x] SQLite registry with SQLAlchemy
- [x] OpenAPI 2/3 extractor
- [x] GitHub README extractor
- [x] LLM-based docs extractor (OpenAI fallback)
- [x] robots.txt-aware crawler with rate-limiting and cache
- [x] Page classifier (openapi / api_docs / github_readme / cli_docs / llms_txt)
- [x] Normaliser (snake_case, side-effect inference, permission policy)
- [x] Tool-DNA deduplication
- [x] Verifier (schema · safety · drift · confidence gate)
- [x] MCP proxy (`search_tools` + `execute_tool`)
- [x] Gap miner (logs failed queries, suggests seeds)
- [x] CLI (`harvest`, `list`, `review`, `gaps`, `server`)
- [x] ChromaDB semantic index
- [x] Unit test suite
- [x] ToolBank Webapp (hero search, scrape form, sources section, nav)

---

## v0.2 — Hardening 🚧

- [x] `StickyNav` component (scroll-aware section highlighting)
- [x] `ProofSection` component (supported sources, stat counters)
- [ ] GraphQL adapter for `execute_tool`
- [ ] Python function adapter for local tool execution
- [ ] CI pipeline (GitHub Actions — lint + test on every PR)
- [ ] Scheduled harvest workflow (GitHub Actions cron)
- [ ] `toolbank review` TUI (curses or rich-based)
- [ ] HTTP cache expiry and invalidation strategy
- [ ] `toolbank export` command (JSON / CSV registry dump)
- [ ] `.env.example` file

---

## v0.3 — Extensibility 🔲

- [ ] Multi-source evidence merging (same tool, multiple docs pages)
- [ ] GraphQL introspection extractor
- [ ] MCP server listing extractor (smithery.ai, mcp.so)
- [ ] SDK extractor (Python package docstrings via AST)
- [ ] Tool versioning (track schema changes over time)
- [ ] Admin approval API for destructive tools
- [ ] Webhook/event adapter support
- [ ] Namespace priority weighting in search

---

## v0.4 — Scale & Observability 🔲

- [ ] PostgreSQL registry option (replace SQLite for multi-instance)
- [ ] Prometheus metrics for search latency, harvest throughput
- [ ] Structured logging (JSON)
- [ ] Rate-limit retry with exponential backoff
- [ ] Distributed harvest queue (Celery or ARQ)
- [ ] API token authentication for the MCP server

---

## v1.0 — Production 💡

- [ ] Hosted Toolbank SaaS (multi-tenant registry)
- [ ] Public tool marketplace UI
- [ ] Verified publisher program
- [ ] Toolbank SDK (Python + TypeScript client)
- [ ] ToolBank Webapp — tool browse/search page
- [ ] ToolBank Webapp — tool detail page
- [ ] ToolBank Webapp — dark/light mode toggle
- [ ] ToolBank Webapp — privacy-first analytics
