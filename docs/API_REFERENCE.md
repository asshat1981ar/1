# API Reference — Toolbank MCP

## MCP Tools

The MCP server exposes two public tools over stdio.

---

### `search_tools`

Search the toolbank for capabilities matching a natural language query.

**Input Schema:**

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `query` | string | ✅ | — | Natural language description of what you want to do |
| `n_results` | integer | — | 5 | Maximum number of results to return |
| `namespace` | string | — | — | Filter results to a specific provider (e.g. `stripe`) |
| `side_effect_level` | `read` \| `write` \| `destructive` | — | — | Filter by side-effect level |

**Example Request:**
```json
{
  "query": "send a transactional email",
  "n_results": 3,
  "namespace": "sendgrid"
}
```

**Example Response:**
```json
[
  {
    "id": "sendgrid.send_email",
    "name": "send_email",
    "namespace": "sendgrid",
    "description": "Send a transactional email via SendGrid.",
    "transport": "rest",
    "side_effect_level": "write",
    "permission_policy": "confirm",
    "tags": ["email", "sendgrid", "communications"],
    "status": "approved",
    "confidence": 0.92,
    "score": 0.871
  }
]
```

---

### `execute_tool`

Execute a tool from the toolbank by its ID. Write-level tools require explicit confirmation.

**Input Schema:**

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `tool_id` | string | ✅ | — | Unique tool ID (e.g. `stripe.get_customer`) |
| `arguments` | object | — | `{}` | Arguments to pass to the tool |
| `confirmed` | boolean | — | `false` | Set `true` to confirm execution of write-level tools |

**Example — Read tool (auto-executes):**
```json
{
  "tool_id": "stripe.get_customer",
  "arguments": { "customer_id": "cus_abc123" }
}
```

**Example — Write tool (confirmation required):**
```json
{
  "tool_id": "stripe.create_payment_link",
  "arguments": { "price": "price_xyz" },
  "confirmed": true
}
```

**Confirmation Required Response (write, `confirmed=false`):**
```json
{
  "status": "confirmation_required",
  "message": "Tool 'stripe.create_payment_link' performs a write action. Re-call execute_tool with confirmed=true to proceed.",
  "tool_id": "stripe.create_payment_link",
  "arguments": { "price": "price_xyz" },
  "side_effect_level": "write"
}
```

**Blocked Response (destructive):**
```json
{
  "error": "Destructive tools are blocked unless explicitly approved by an administrator.",
  "tool_id": "stripe.delete_customer",
  "side_effect_level": "destructive"
}
```

---

## CLI Reference

```
Usage: toolbank [OPTIONS] COMMAND [ARGS]...

Commands:
  harvest   Crawl and harvest tool definitions
  list      List registry contents
  review    Interactive human review queue
  gaps      Show capability gaps from failed queries
  server    Start the MCP server (stdio transport)
```

### `toolbank harvest`

```
Options:
  --url TEXT     Harvest a single URL
  --config PATH  Harvest from a sources.yaml config file  [default: config/sources.yaml]
  --max-pages N  Maximum pages to crawl per source       [default: 20]
  --no-cache     Disable HTTP cache
```

### `toolbank list`

```
Options:
  --status TEXT     Filter by status: draft|verified|approved|deprecated
  --namespace TEXT  Filter by namespace
  --json            Output raw JSON
```

### `toolbank review`

Interactive TUI to approve or reject queued tool candidates. Press:
- `a` — approve
- `r` — reject
- `q` — quit

### `toolbank gaps`

Prints a report of capability gaps derived from failed `search_tools` queries.

### `toolbank server`

Starts the MCP proxy server on stdio. Connect via an MCP-compatible LLM client.

---

## ToolbankRecord Schema

Full JSON Schema: `toolbank/schemas/toolbank_record.schema.json`

| Field | Type | Description |
|---|---|---|
| `id` | string | `namespace.name` (snake_case) |
| `name` | string | snake_case capability name |
| `namespace` | string | Provider namespace |
| `description` | string | What the tool does (≥ 10 chars) |
| `source_urls` | string[] | Documentation/spec URLs |
| `source_type` | enum | `openapi` \| `docs` \| `github` \| `mcp_server` \| `sdk` \| `cli` |
| `transport` | enum | `rest` \| `graphql` \| `cli` \| `python` \| `node` \| `webhook` \| `local` |
| `auth` | object | Auth type and required env vars |
| `input_schema` | object | JSON Schema for input parameters |
| `output_schema` | object | JSON Schema for response |
| `examples` | array | Usage examples with goal + arguments |
| `side_effect_level` | enum | `read` \| `write` \| `destructive` |
| `permission_policy` | enum | `auto` \| `confirm` \| `deny` |
| `execution_adapter` | object | HTTP or subprocess execution config |
| `tags` | string[] | Searchable tags |
| `confidence` | float | Extraction confidence 0.0–1.0 |
| `version_hash` | string | `sha256:<hash>` of description + input_schema |
| `status` | enum | `draft` \| `verified` \| `approved` \| `deprecated` |
| `dna` | object | Tool-DNA fingerprint for deduplication |
