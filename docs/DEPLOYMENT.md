# Deployment Guide

## Toolbank MCP Server

The MCP server communicates over **stdio** — it is launched by an MCP-compatible LLM client (e.g. Claude Desktop, VS Code Copilot) as a subprocess. It does **not** expose an HTTP port.

### Local / Development

```bash
pip install -e ".[all]"
toolbank server
```

### Claude Desktop Integration

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "toolbank": {
      "command": "toolbank",
      "args": ["server"],
      "env": {
        "OPENAI_API_KEY": "sk-...",
        "GITHUB_TOKEN": "ghp_..."
      }
    }
  }
}
```

### Docker (optional)

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN pip install -e ".[all]"
CMD ["toolbank", "server"]
```

```bash
docker build -t toolbank-mcp .
docker run --rm -i \
  -e OPENAI_API_KEY=$OPENAI_API_KEY \
  toolbank-mcp
```

---

## ToolBank Webapp

The Next.js webapp is deployed to **Vercel** (recommended) or any Node.js host.

### Vercel (recommended)

1. Connect the repository to Vercel
2. Vercel auto-detects Next.js and uses the `vercel-build` script from `package.json`
3. Set environment variables in the Vercel dashboard if needed

### Manual Build

```bash
npm install
npm run build
npm run start       # production server on :3000
```

### Static Export (optional)

Add to `next.config.js`:
```js
output: 'export'
```

Then:
```bash
npm run build       # produces /out directory
```

---

## Required Media Assets

No media assets are required. The video hero has been replaced with a CSS gradient hero.

---

## Database Persistence

The Toolbank registry stores data in `toolbank/registry.db` (SQLite). In production:

- Mount the `toolbank/` directory as a persistent volume
- The DB is created automatically on first run (`database.init_db()`)
- Back up `toolbank/registry.db` and `toolbank/records/` regularly

---

## Scheduled Harvesting

A GitHub Actions workflow (`.github/workflows/harvest-scheduled.yml`) can run harvests on a cron schedule. Configure `OPENAI_API_KEY` and `GITHUB_TOKEN` as repository secrets.
