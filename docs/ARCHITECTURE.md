# Architecture — Toolbank MCP + No-Bull Marketing

This repository is a **monorepo** combining two systems that share a single deployment context:

| System | Role | Runtime |
|---|---|---|
| **Toolbank MCP** | Self-improving MCP proxy server + autonomous tool harvester | Python 3.11+ |
| **No-Bull Marketing** | Public-facing marketing site for the No-Bull agency | Next.js 14 (React 18) |

---

## Toolbank MCP — Architecture

```
Seed Sources  (config/sources.yaml)
       │
       ▼
Discovery Crawler          respects robots.txt · rate-limits · HTTP cache
       │
       ▼
Page Classifier            openapi │ api_docs │ github_readme │ cli_docs │ llms_txt
       │
       ▼
Extractor                  OpenAPI parser (deterministic) → LLM fallback (docs/messy)
       │
       ▼
Schema Normalizer           snake_case · side-effect inference · permission policy
       │
       ▼
Deduper / Tool-DNA          collapses functionally identical records across sources
       │
       ▼
Verifier                    JSON Schema · safety rules · drift detection · confidence gate
       │
       ├──── PASS ────────▶ Tool Registry (SQLite) ──▶ ChromaDB Index
       │
       └──── FAIL ────────▶ Human Review Queue (SQLite)
                                       │
                                       ▼
                            MCP Proxy  (search_tools + execute_tool)
                                       │
                            Failed queries ──▶ Gap Miner ──▶ new seeds  ♻
```

### Component Descriptions

| Module | Path | Responsibility |
|---|---|---|
| MCP Server | `mcp_server/server.py` | Stdio MCP transport; exposes `search_tools` + `execute_tool` |
| CLI | `mcp_server/cli.py` | `toolbank` command-line entry point |
| Models | `mcp_server/models.py` | Pydantic schemas for all internal data structures |
| Database | `mcp_server/database.py` | SQLite registry via SQLAlchemy; review queue |
| Vector Store | `mcp_server/vector_store.py` | ChromaDB semantic index |
| Harvester | `mcp_server/harvester/harvester.py` | Pipeline orchestrator |
| Crawler | `mcp_server/harvester/crawler.py` | robots.txt-aware HTTP crawler with cache |
| Classifier | `mcp_server/harvester/classifier.py` | Page-type heuristic classifier |
| Normalizer | `mcp_server/harvester/normalizer.py` | Canonicalises raw candidates |
| Deduper | `mcp_server/harvester/deduper.py` | Tool-DNA fingerprint deduplication |
| Verifier | `mcp_server/harvester/verifier.py` | Schema + safety + drift verification |
| Gap Miner | `mcp_server/harvester/gap_miner.py` | Mines failed queries for missing capabilities |
| OpenAPI Extractor | `mcp_server/harvester/extractors/openapi_extractor.py` | OpenAPI 2/3 → ToolbankRecord |
| GitHub Extractor | `mcp_server/harvester/extractors/github_extractor.py` | GitHub README → ToolbankRecord |
| Docs Extractor | `mcp_server/harvester/extractors/docs_extractor.py` | LLM-based unstructured docs extractor |

---

## No-Bull Marketing — Architecture

Next.js 14 App Router single-page marketing site.

```
app/
  layout.jsx      Root layout (Navbar + Footer wrapper)
  page.jsx        Home page (StickyNav + HeroVideo + ProofSection + CTAFormSection)
  globals.css     Tailwind base styles

components/
  Navbar.jsx         Fixed top navigation
  Footer.jsx         Page footer
  StickyNav.jsx      Scroll-aware sticky section nav  [TODO]
  HeroVideo.jsx      Full-screen video hero with Framer Motion overlay
  ProofSection.jsx   Social proof: case studies, metrics, logos  [TODO]
  CTAFormSection.jsx Lead-capture form with honeypot spam guard

public/
  media/
    hero.mp4           Hero background video
    hero-blur.jpg      Poster/blur placeholder
    no-bull-deck.pdf   Downloadable pitch deck
```

---

## Data Flow: Tool Execution

```
LLM client
    │
    │  MCP stdio
    ▼
server.py::call_tool("execute_tool", {tool_id, arguments, confirmed})
    │
    ├── Policy check (side_effect_level × confirmed flag)
    │       read       → auto execute
    │       write      → require confirmed=true
    │       destructive → deny always
    │
    ├── Fetch ToolbankRecord from SQLite
    │
    └── Dispatch adapter
            http        → httpx async request
            subprocess  → sandboxed subprocess
```

---

## Key Design Decisions

See `docs/adr/` for Architecture Decision Records.
