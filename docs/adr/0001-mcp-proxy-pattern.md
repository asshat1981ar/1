# ADR 0001 — MCP Proxy Pattern

**Date:** 2025-01  
**Status:** Accepted

---

## Context

We need a way to expose a dynamically growing set of third-party API capabilities to LLM clients in a standardised way. The tool set is not known at build time — it grows as the harvester discovers new capabilities.

## Decision

Use the **Model Context Protocol (MCP)** as the interface between the LLM client and the tool registry. The MCP server acts as a proxy: it exposes two stable tools (`search_tools` and `execute_tool`) that abstract over the entire, dynamically-populated registry.

The server communicates over **stdio** so it can be spawned as a subprocess by any MCP-compatible client (Claude Desktop, VS Code Copilot, etc.) without requiring a separate network service.

## Rationale

- MCP is the emerging standard for LLM tool integration (Anthropic, GitHub Copilot, etc.)
- Two-tool interface (`search` + `execute`) is minimal and stable regardless of how many tools are in the registry
- Stdio transport avoids the operational complexity of running a persistent HTTP service
- The proxy pattern means the harvester can update the registry without restarting the MCP server

## Consequences

- The server process lifetime is tied to the LLM client session
- All tool discovery must happen via `search_tools` — clients cannot enumerate the full registry
- Adding new MCP transport types (HTTP SSE, WebSockets) requires a new ADR
