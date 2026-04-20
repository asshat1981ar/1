# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Changed
- Rebranded frontend from "No-Bull Marketing" agency site to **ToolBank Webapp** — a tool-scraper and registry browser
- `components/HeroVideo.jsx` — replaced video hero with full-screen gradient hero featuring tool search input
- `components/CTAFormSection.jsx` — replaced marketing CTA form with "Scrape a New Source" form (URL + source-type selector, honeypot, success state)
- `components/ProofSection.jsx` — implemented as a supported-sources showcase (OpenAPI, GraphQL, MCP, Docs) with animated stat cards
- `components/StickyNav.jsx` — implemented scroll-aware side-rail nav using `IntersectionObserver` and Framer Motion
- `components/Navbar.jsx` / `components/Footer.jsx` — updated branding and nav links to match ToolBank identity
- `app/layout.jsx` — updated page title and description metadata
- `package.json` — renamed app from `no-bull-marketing` to `toolbank-webapp`
- `system_prompt.md` / `todo.md` — removed all No-Bull Marketing references

### Added
- `app/` — proper Next.js App Router directory structure
- `components/` — organised React component directory with `StickyNav` and `ProofSection` placeholders
- `toolbank/schemas/` — JSON Schema files for `ToolbankRecord` and `HarvestSource`
- `toolbank/records/`, `toolbank/adapters/`, `toolbank/evidence/`, `toolbank/review_queue/` — runtime data directories
- `next.config.js` — Next.js configuration
- `public/media/` — media assets directory with placeholder guide
- `docs/ARCHITECTURE.md` — full system architecture documentation
- `docs/TECH_STACK.md` — technology stack reference
- `docs/FEATURES.md` — feature index for both systems
- `docs/DEVELOPMENT_GUIDE.md` — developer onboarding guide
- `docs/DEPLOYMENT.md` — deployment instructions
- `docs/API_REFERENCE.md` — MCP tools and CLI reference
- `docs/ROADMAP.md` — versioned feature roadmap
- `docs/GUARDRAILS.md` — hard constraints and drift-prevention checklist
- `docs/adr/` — Architecture Decision Records (0001–0004)
- `CONTRIBUTING.md` — contribution guidelines
- `CODEOWNERS` — code ownership assignments
- `.editorconfig` — editor normalisation config
- `.github/ISSUE_TEMPLATE/` — bug, feature, and harvest request templates
- `.github/PULL_REQUEST_TEMPLATE.md` — PR description template
- `.github/workflows/ci.yml` — CI pipeline (lint + test)
- `.github/workflows/harvest-scheduled.yml` — scheduled harvest workflow

---

## [0.1.0] — 2025-01

### Added
- `ToolbankRecord` Pydantic schema with Tool-DNA fingerprinting
- SQLite registry via SQLAlchemy (`mcp_server/database.py`)
- ChromaDB semantic index (`mcp_server/vector_store.py`)
- OpenAPI 2/3 extractor
- GitHub README extractor
- LLM-based docs extractor (OpenAI fallback)
- robots.txt-aware crawler with rate-limiting and HTTP cache
- Page classifier (openapi / api_docs / github_readme / cli_docs / llms_txt)
- Normaliser (snake_case, side-effect inference, permission policy)
- Tool-DNA deduplication
- Verifier (schema · safety · drift · confidence gate)
- MCP proxy server (`search_tools` + `execute_tool`) over stdio
- Gap miner for self-improvement loop
- CLI (`toolbank harvest | list | review | gaps | server`)
- No-Bull Marketing site: hero video, CTA form, navbar, footer
- Initial unit test suite
