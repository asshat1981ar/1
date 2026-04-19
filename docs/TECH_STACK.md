# Tech Stack

## Toolbank MCP (Python Backend)

| Layer | Technology | Version | Purpose |
|---|---|---|---|
| Language | Python | ≥ 3.11 | Core runtime |
| Protocol | MCP (Model Context Protocol) | ≥ 1.0.0 | LLM ↔ tool communication |
| HTTP Client | httpx | ≥ 0.27.0 | Async HTTP for crawling + execution |
| ORM / DB | SQLAlchemy + SQLite | ≥ 2.0.0 | Tool registry & review queue |
| Validation | Pydantic | ≥ 2.0.0 | Record schemas & data validation |
| HTML Parsing | BeautifulSoup4 + lxml | ≥ 4.12 / 5.0 | Crawled page parsing |
| YAML | PyYAML | ≥ 6.0.0 | `config/sources.yaml` parsing |
| Vector Search | ChromaDB | ≥ 0.5.0 | Semantic tool search (optional) |
| LLM Extraction | OpenAI SDK | ≥ 1.0.0 | Unstructured docs extraction (optional) |
| Text Extraction | Trafilatura | ≥ 1.8.0 | Clean text from HTML (optional) |
| MD Conversion | Markdownify | ≥ 0.12.0 | HTML → Markdown pre-processing (optional) |
| Testing | pytest + pytest-asyncio | ≥ 8.0 / 0.23 | Unit & async tests |
| Build | setuptools | ≥ 61 | Package build |

## No-Bull Marketing (Next.js Frontend)

| Layer | Technology | Version | Purpose |
|---|---|---|---|
| Framework | Next.js | 14.1.0 | App Router SSR/SSG |
| UI Library | React | 18.2.0 | Component model |
| Animation | Framer Motion | ≥ 10.16 | Hero + interaction animations |
| Styling | Tailwind CSS | ≥ 3.4.1 | Utility-first CSS |
| CSS PostProcessor | PostCSS + Autoprefixer | ≥ 8.4 / 10.4 | CSS transforms |

## Infrastructure / Tooling

| Tool | Purpose |
|---|---|
| GitHub Actions | CI (lint, test, type-check) + scheduled harvests |
| SQLite | Zero-dep embedded database for registry & review queue |
| ChromaDB | Local-first vector database (no external service required) |
| Vercel | Recommended deployment for the Next.js marketing site |

## Environment Variables

| Variable | Required | Purpose |
|---|---|---|
| `OPENAI_API_KEY` | Optional | LLM-based docs extraction |
| `OPENAI_MODEL` | Optional | Override model (default: `gpt-4o-mini`) |
| `STRIPE_API_KEY` | Optional | Execute Stripe tools |
| `GITHUB_TOKEN` | Optional | Execute GitHub tools; higher crawl rate limit |

## Optional vs Required Dependencies

The package uses extras to keep the core install lean:

```bash
pip install -e .          # core only (no LLM, no vector search)
pip install -e ".[vector]" # + ChromaDB
pip install -e ".[llm]"    # + OpenAI
pip install -e ".[docs]"   # + Trafilatura + Markdownify
pip install -e ".[all]"    # everything including dev tools
```
