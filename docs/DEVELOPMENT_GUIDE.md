# Development Guide

## Prerequisites

| Tool | Min Version | Install |
|---|---|---|
| Python | 3.11 | [python.org](https://python.org) |
| Node.js | 18 | [nodejs.org](https://nodejs.org) |
| npm | 9 | bundled with Node.js |
| Git | any | [git-scm.com](https://git-scm.com) |

---

## Quick Start

### 1 — Clone & install

```bash
git clone https://github.com/asshat1981ar/1.git
cd 1
```

**Python (Toolbank MCP):**
```bash
pip install -e ".[all]"
```

**Node.js (Marketing site):**
```bash
npm install
```

---

### 2 — Run the MCP server (development)

```bash
toolbank server
# or
python -m mcp_server.server
```

The server communicates over **stdio** and is consumed by an MCP-compatible LLM client.

---

### 3 — Run the marketing site (development)

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

---

## Project Structure

```
1/
├── app/                    Next.js App Router root
│   ├── layout.jsx          Root layout (Navbar + Footer)
│   ├── page.jsx            Home page
│   └── globals.css         Tailwind base
├── components/             React components
│   ├── Navbar.jsx
│   ├── Footer.jsx
│   ├── HeroVideo.jsx
│   ├── CTAFormSection.jsx
│   ├── StickyNav.jsx       [TODO]
│   └── ProofSection.jsx    [TODO]
├── public/
│   └── media/              Static media assets (video, images, PDFs)
├── mcp_server/             Python MCP server package
│   ├── server.py
│   ├── cli.py
│   ├── models.py
│   ├── database.py
│   ├── vector_store.py
│   └── harvester/
│       ├── harvester.py
│       ├── crawler.py
│       ├── classifier.py
│       ├── normalizer.py
│       ├── deduper.py
│       ├── verifier.py
│       ├── gap_miner.py
│       └── extractors/
│           ├── openapi_extractor.py
│           ├── github_extractor.py
│           └── docs_extractor.py
├── toolbank/               Runtime data directory (git-ignored except schemas)
│   ├── records/            Approved JSON tool records
│   ├── schemas/            JSON Schema files
│   ├── adapters/           Custom execution adapter configs
│   ├── evidence/           LLM extraction evidence logs
│   └── review_queue/       Pending human review exports
├── config/
│   └── sources.yaml        Curated harvest seed sources
├── tests/
│   └── test_toolbank.py
├── docs/                   Project documentation
│   ├── ARCHITECTURE.md
│   ├── TECH_STACK.md
│   ├── FEATURES.md
│   ├── DEVELOPMENT_GUIDE.md  (this file)
│   ├── DEPLOYMENT.md
│   ├── API_REFERENCE.md
│   ├── ROADMAP.md
│   ├── GUARDRAILS.md
│   └── adr/                Architecture Decision Records
└── .github/
    ├── ISSUE_TEMPLATE/
    ├── PULL_REQUEST_TEMPLATE.md
    └── workflows/
```

---

## Running Tests

```bash
# All Python tests
pytest tests/ -v

# With coverage
pytest tests/ -v --cov=mcp_server --cov-report=term-missing
```

---

## Environment Variables

Copy `.env.example` to `.env` (not committed):

```bash
OPENAI_API_KEY=sk-...          # optional: LLM extraction
OPENAI_MODEL=gpt-4o-mini       # optional: override model
STRIPE_API_KEY=sk_test_...     # optional: execute Stripe tools
GITHUB_TOKEN=ghp_...           # optional: GitHub tools + higher rate limit
```

---

## Adding a New Seed Source

1. Edit `config/sources.yaml`
2. Add an entry following the schema in `toolbank/schemas/source.schema.json`
3. Run `toolbank harvest --config config/sources.yaml`

---

## Adding a New Extractor

1. Create `mcp_server/harvester/extractors/my_extractor.py`
2. Implement a function `extract_from_X(content: str, source_url: str) -> list[dict]`
3. Each returned dict must be normalisable to `ToolbankRecord` (see `mcp_server/models.py`)
4. Register the extractor in `mcp_server/harvester/extractors/__init__.py`
5. Add a classifier rule in `mcp_server/harvester/classifier.py`
6. Write tests in `tests/`

---

## Code Style

- **Python**: PEP 8, type hints on all public functions, docstrings on public classes/functions
- **JavaScript/JSX**: Functional components, `"use client"` directive where needed, Tailwind for all styling
- No new linting tooling is required; follow existing patterns

---

## Pull Request Checklist

- [ ] Tests pass (`pytest tests/ -v`)
- [ ] No new unrelated changes
- [ ] Documentation updated if behaviour changed
- [ ] `CHANGELOG.md` entry added
- [ ] PR description filled out (see `.github/PULL_REQUEST_TEMPLATE.md`)
