# Features

## Toolbank MCP — Feature Index

### 🔍 Tool Discovery (Harvester)

| Feature | Status | Description |
|---|---|---|
| OpenAPI 2/3 parsing | ✅ Implemented | Deterministic extraction from Swagger/OpenAPI specs |
| GitHub README extraction | ✅ Implemented | Heuristic extraction from GitHub README pages |
| LLM-based docs extraction | ✅ Implemented | OpenAI-backed fallback for unstructured documentation |
| robots.txt compliance | ✅ Implemented | Crawler respects disallow rules |
| Rate limiting | ✅ Implemented | Configurable per-request delay |
| HTTP cache | ✅ Implemented | Avoids re-fetching unchanged pages |
| llms.txt support | ✅ Implemented | Reads and follows LLM-friendly URL lists |
| Sitemap crawling | ✅ Implemented | Extracts URLs from `sitemap.xml` |
| Link discovery | ✅ Implemented | Follows API/docs-relevant links from seed pages |
| OpenAPI auto-probe | ✅ Implemented | Checks common OpenAPI/Swagger paths automatically |

### 🧹 Record Normalisation

| Feature | Status | Description |
|---|---|---|
| snake_case names | ✅ Implemented | All tool names normalised to `snake_case` |
| Side-effect inference | ✅ Implemented | GET→read, POST/PUT→write, DELETE→destructive |
| Permission policy auto-assign | ✅ Implemented | write→confirm, destructive→deny |
| Version hash | ✅ Implemented | SHA-256 of description + input schema |
| Tag enrichment | ✅ Implemented | Namespace automatically added to tags |
| Auth defaults | ✅ Implemented | Sensible defaults when auth info is absent |

### 🔁 Deduplication (Tool-DNA)

| Feature | Status | Description |
|---|---|---|
| Transport-signature dedup | ✅ Implemented | Same HTTP method + URL → merge records |
| Confidence-based winner | ✅ Implemented | Higher-confidence record survives merge |
| Source URL merging | ✅ Implemented | All source URLs retained on the winner |
| DNA fingerprint | ✅ Implemented | Semantic hash for cross-namespace dedup |

### ✅ Verification

| Feature | Status | Description |
|---|---|---|
| JSON Schema validation | ✅ Implemented | Input schema type checking |
| Required field gate | ✅ Implemented | id, name, namespace, description required |
| Safety check | ✅ Implemented | Destructive tools must have deny policy |
| Drift detection | ✅ Implemented | Flags records whose hash changed since last run |
| Confidence gate | ✅ Implemented | Records below threshold go to review queue |
| Auto-approve (≥ 0.9) | ✅ Implemented | High-confidence read tools auto-approved |
| Auto-verify (≥ 0.7) | ✅ Implemented | Medium-confidence records set to verified |

### 🗃 Registry & Storage

| Feature | Status | Description |
|---|---|---|
| SQLite tool registry | ✅ Implemented | Persistent canonical tool records |
| Review queue | ✅ Implemented | Human review dashboard backed by SQLite |
| JSON record files | ✅ Implemented | One `.json` file per approved tool in `toolbank/records/` |
| ChromaDB semantic index | ✅ Implemented | Vector embeddings for semantic search |

### 🔌 MCP Proxy

| Feature | Status | Description |
|---|---|---|
| `search_tools` | ✅ Implemented | Semantic + text fallback search |
| `execute_tool` | ✅ Implemented | Policy-checked tool execution |
| Namespace filter | ✅ Implemented | Filter search by provider namespace |
| Side-effect filter | ✅ Implemented | Filter search by read/write/destructive |
| Write confirmation gate | ✅ Implemented | Write tools require `confirmed=true` |
| Destructive deny | ✅ Implemented | Destructive tools blocked by default |
| HTTP adapter | ✅ Implemented | Execute REST APIs directly |
| Subprocess adapter | ✅ Implemented | Sandboxed CLI command execution |
| Failed query logging | ✅ Implemented | Every miss logged for gap mining |

### ♻ Gap Mining (Self-Improvement)

| Feature | Status | Description |
|---|---|---|
| Failed query logging | ✅ Implemented | Stores every unresolved search |
| Gap analysis | ✅ Implemented | Identifies missing capability clusters |
| Seed suggestions | ✅ Implemented | Generates new harvest seed URLs |

### 🖥 CLI

| Command | Description |
|---|---|
| `toolbank harvest --url <url>` | Harvest tools from a single URL |
| `toolbank harvest --config config/sources.yaml` | Harvest all curated sources |
| `toolbank list [--status] [--namespace]` | List registry contents |
| `toolbank review` | Interactive human review queue |
| `toolbank gaps` | Show capability gaps from failed queries |
| `toolbank server` | Start the MCP server (stdio transport) |

---

## No-Bull Marketing — Feature Index

| Feature | Status | Description |
|---|---|---|
| Full-screen hero video | ✅ Implemented | Autoplay muted loop with Framer Motion overlay |
| Animated headlines | ✅ Implemented | Fade + slide-in on mount |
| CTA form | ✅ Implemented | Name + email lead capture |
| Honeypot spam guard | ✅ Implemented | Hidden field blocks bot submissions |
| Pitch deck download | ✅ Implemented | PDF linked from CTA section |
| Fixed navigation | ✅ Implemented | Glassmorphism navbar, fixed top |
| Scroll-aware sticky nav | 🔲 Planned | Highlights active section on scroll |
| Social proof section | 🔲 Planned | Case studies, metrics, client logos |
| Dark/light mode | 🔲 Planned | Theme toggle |
| Analytics | 🔲 Planned | Privacy-first event tracking |
| CMS integration | 🔲 Planned | Headless CMS for case studies and copy |
