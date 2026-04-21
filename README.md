# Toolbank MCP – Toolbank Harvester

![CI](https://github.com/asshat1981ar/1/actions/workflows/ci.yml/badge.svg)

A self-improving MCP proxy server backed by an autonomous **Toolbank Harvester** that crawls public docs, OpenAPI specs, GitHub READMEs, and MCP server listings to populate a validated tool registry.

---

## Architecture

```
Seed Sources (config/sources.yaml)
   ↓
Discovery Crawler  (respects robots.txt · rate-limits · caches)
   ↓
Page Classifier    (openapi | api_docs | github_readme | cli_docs | llms_txt)
   ↓
Extractor          (deterministic OpenAPI parser → LLM fallback for messy docs)
   ↓
Schema Normalizer  (snake_case · side-effect inference · permission policy)
   ↓
Deduper / Tool-DNA (collapses stripe_create_payment_link ≡ POST /v1/payment_links)
   ↓
Verifier           (JSON Schema · safety · drift · confidence gate)
   ↓
Human Review Queue (SQLite-backed review dashboard)
   ↓
Tool Registry      (SQLite canonical records)
   ↓
ChromaDB Index     (semantic search)
   ↓
MCP Proxy          search_tools + execute_tool
   ↓
Failed queries → Gap Miner → new harvest seeds (self-improving loop)
```

---

## MCP Tools

### `search_tools`
Natural language search over the toolbank.
```json
{
  "query": "send a transactional email",
  "n_results": 5,
  "namespace": "sendgrid",
  "side_effect_level": "write"
}
```

### `execute_tool`
Execute a tool by ID with policy enforcement.
```json
{
  "tool_id": "stripe.get_customer",
  "arguments": { "customer_id": "cus_123" }
}
```
Write-level tools return a `confirmation_required` response; re-call with `"confirmed": true`.
Destructive tools are blocked unless an admin explicitly approves them.

---

## Toolbank Record Schema

Every discovered capability is stored as a `ToolbankRecord`:

```json
{
  "id": "stripe.create_payment_link",
  "name": "create_payment_link",
  "namespace": "stripe",
  "description": "Create a Stripe payment link for a product or price.",
  "source_urls": ["https://docs.stripe.com/api/payment_links"],
  "source_type": "openapi",
  "transport": "rest",
  "auth": { "type": "api_key", "required_env": ["STRIPE_API_KEY"] },
  "input_schema": { "type": "object", "properties": {} },
  "output_schema": {},
  "examples": [{ "goal": "Create a payment link", "arguments": {} }],
  "side_effect_level": "write",
  "permission_policy": "confirm",
  "execution_adapter": {
    "kind": "http",
    "method": "POST",
    "url_template": "https://api.stripe.com/v1/payment_links"
  },
  "tags": ["payments", "commerce", "stripe"],
  "confidence": 0.91,
  "status": "verified"
}
```

---

## Installation

```bash
pip install -e ".[all]"
```

Or minimal:
```bash
pip install -e .
```

---

## Usage

### Harvest tools from a single URL
```bash
toolbank harvest --url https://docs.stripe.com/api
```

### Harvest from the curated sources config
```bash
toolbank harvest --config config/sources.yaml
```

### List registry contents
```bash
toolbank list --status approved
toolbank list --namespace stripe
```

### Interactive review queue
```bash
toolbank review
```

### Show capability gaps (from failed queries)
```bash
toolbank gaps
```

### Start the MCP server (stdio transport)
```bash
toolbank server
# or
python -m mcp_server.server
```

---

## Side-Effect Policies

| Level        | Default Policy  | Behaviour                                              |
|-------------|----------------|-------------------------------------------------------|
| `read`       | `auto`          | Executed immediately                                  |
| `write`      | `confirm`       | Returns `confirmation_required`; retry with `confirmed=true` |
| `destructive`| `deny`          | Blocked; requires explicit admin approval             |

---

## Gap Miner

Every failed `search_tools` query is logged. A scheduled job (or manual `toolbank gaps`) analyses these logs to identify missing capabilities and generates suggested seed URLs for the next harvest run.

---

## Directory Structure

```
mcp_server/
  server.py          # MCP server (search_tools + execute_tool)
  cli.py             # CLI entry point
  models.py          # Pydantic ToolbankRecord schema
  database.py        # SQLite registry (SQLAlchemy)
  vector_store.py    # ChromaDB semantic index
  harvester/
    harvester.py     # Main orchestrator
    crawler.py       # HTTP crawler (robots.txt aware)
    classifier.py    # Page type classifier
    normalizer.py    # Record normalizer
    deduper.py       # Tool-DNA deduplication
    verifier.py      # Schema + safety verifier
    gap_miner.py     # Failure-driven seed generator
    extractors/
      openapi_extractor.py   # OpenAPI 2/3 → ToolbankRecord
      github_extractor.py    # GitHub README → ToolbankRecord
      docs_extractor.py      # LLM-based docs extractor
toolbank/
  records/           # JSON tool records (one per tool)
  schemas/           # JSON Schema files
  adapters/          # Execution adapter files
  evidence/          # LLM extraction evidence
  review_queue/      # Pending human review
  registry.db        # SQLite database
  chroma_data/       # ChromaDB vector index
config/
  sources.yaml       # Curated seed sources
tests/
  test_toolbank.py   # Unit tests
```

---

## Environment Variables

| Variable          | Purpose                              |
|-------------------|--------------------------------------|
| `OPENAI_API_KEY`  | LLM-based docs extraction (optional) |
| `OPENAI_MODEL`    | Override model (default: gpt-4o-mini)|
| `STRIPE_API_KEY`  | Execute Stripe tools                 |
| `GITHUB_TOKEN`    | Execute GitHub tools                 |

---

## Running Tests

```bash
pytest tests/ -v
```
