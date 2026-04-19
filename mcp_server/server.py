"""
MCP Proxy Server
Exposes two public tools:
  - search_tools(query, filters)   → semantic + registry search
  - execute_tool(tool_id, args)    → policy-checked execution

Internal tool (harvester pipeline):
  - ingest_tool_candidate(candidate_json)

Run with:
  python -m mcp_server.server
  or
  uvicorn mcp_server.server:app
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
import traceback
from pathlib import Path
from typing import Any

import httpx
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types

from mcp_server import database, vector_store
from mcp_server.harvester import ToolbankHarvester

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Side-effect policy
# ---------------------------------------------------------------------------

SIDE_EFFECT_POLICIES: dict[str, str] = {
    "read": "auto",
    "write": "confirm",
    "destructive": "deny_by_default",
}

# ---------------------------------------------------------------------------
# MCP Server setup
# ---------------------------------------------------------------------------

server = Server("toolbank-mcp")


@server.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="search_tools",
            description=(
                "Search the toolbank for capabilities matching a natural language query. "
                "Returns ranked tool records with descriptions, schemas, and metadata."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Natural language description of what you want to do.",
                    },
                    "n_results": {
                        "type": "integer",
                        "description": "Max number of results to return (default 5).",
                        "default": 5,
                    },
                    "namespace": {
                        "type": "string",
                        "description": "Filter by namespace (e.g. 'stripe', 'github').",
                    },
                    "side_effect_level": {
                        "type": "string",
                        "enum": ["read", "write", "destructive"],
                        "description": "Filter by side effect level.",
                    },
                },
                "required": ["query"],
            },
        ),
        types.Tool(
            name="execute_tool",
            description=(
                "Execute a tool from the toolbank by its ID. "
                "Write and destructive tools require explicit confirmation."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "tool_id": {
                        "type": "string",
                        "description": "The tool's unique ID (e.g. 'stripe.create_payment_link').",
                    },
                    "arguments": {
                        "type": "object",
                        "description": "Arguments to pass to the tool.",
                        "default": {},
                    },
                    "confirmed": {
                        "type": "boolean",
                        "description": "Set true to confirm execution of write-level tools.",
                        "default": False,
                    },
                },
                "required": ["tool_id"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[types.TextContent]:
    if name == "search_tools":
        return await _search_tools(arguments)
    if name == "execute_tool":
        return await _execute_tool(arguments)
    return [types.TextContent(type="text", text=f"Unknown tool: {name}")]


# ---------------------------------------------------------------------------
# search_tools implementation
# ---------------------------------------------------------------------------

async def _search_tools(args: dict[str, Any]) -> list[types.TextContent]:
    query = args.get("query", "")
    n_results = int(args.get("n_results", 5))
    namespace = args.get("namespace")
    side_effect_level = args.get("side_effect_level")

    if not query:
        return [types.TextContent(type="text", text='{"error": "query is required"}')]

    # Semantic search via ChromaDB
    chroma_filters: dict[str, Any] = {}
    if side_effect_level:
        chroma_filters["side_effect_level"] = side_effect_level
    if namespace:
        chroma_filters["namespace"] = namespace

    hits = vector_store.search_tools(query, n_results=n_results, filters=chroma_filters or None)

    results: list[dict[str, Any]] = []
    for hit in hits:
        record = database.get_tool(hit["id"])
        if record:
            results.append(
                {
                    "id": record["id"],
                    "name": record["name"],
                    "namespace": record["namespace"],
                    "description": record["description"],
                    "transport": record.get("transport"),
                    "side_effect_level": record.get("side_effect_level"),
                    "permission_policy": record.get("permission_policy"),
                    "tags": record.get("tags", []),
                    "status": record.get("status"),
                    "confidence": record.get("confidence"),
                    "score": round(hit["score"], 3),
                }
            )

    # Fallback: text search in SQLite if ChromaDB has no results
    if not results:
        rows = database.list_tools(status="approved") + database.list_tools(status="verified")
        query_lower = query.lower()
        for row in rows:
            if query_lower in (row.get("description", "") + row.get("name", "")).lower():
                results.append(
                    {
                        "id": row["id"],
                        "name": row["name"],
                        "namespace": row["namespace"],
                        "description": row["description"],
                        "transport": row.get("transport"),
                        "side_effect_level": row.get("side_effect_level"),
                        "permission_policy": row.get("permission_policy"),
                        "tags": row.get("tags", []),
                        "status": row.get("status"),
                        "confidence": row.get("confidence"),
                        "score": 0.0,
                    }
                )
            if len(results) >= n_results:
                break

    # Log failed query if no results
    if not results:
        database.log_failed_query(
            user_goal=query,
            failed_query=query,
            tools_returned=[],
        )

    return [types.TextContent(type="text", text=json.dumps(results, indent=2))]


# ---------------------------------------------------------------------------
# execute_tool implementation
# ---------------------------------------------------------------------------

async def _execute_tool(args: dict[str, Any]) -> list[types.TextContent]:
    tool_id = args.get("tool_id", "")
    arguments = args.get("arguments", {}) or {}
    confirmed = bool(args.get("confirmed", False))

    if not tool_id:
        return [types.TextContent(type="text", text='{"error": "tool_id is required"}')]

    record = database.get_tool(tool_id)
    if not record:
        return [
            types.TextContent(
                type="text",
                text=json.dumps({"error": f"Tool not found: {tool_id}"}),
            )
        ]

    if record.get("status") not in ("approved", "verified"):
        return [
            types.TextContent(
                type="text",
                text=json.dumps(
                    {
                        "error": "Tool is not approved for execution.",
                        "status": record.get("status"),
                        "tool_id": tool_id,
                    }
                ),
            )
        ]

    side_effect = record.get("side_effect_level", "read")

    # Policy enforcement
    if side_effect == "destructive":
        return [
            types.TextContent(
                type="text",
                text=json.dumps(
                    {
                        "error": "Destructive tools are blocked unless explicitly approved by an administrator.",
                        "tool_id": tool_id,
                        "side_effect_level": side_effect,
                    }
                ),
            )
        ]

    if side_effect == "write" and not confirmed:
        return [
            types.TextContent(
                type="text",
                text=json.dumps(
                    {
                        "status": "confirmation_required",
                        "message": (
                            f"Tool '{tool_id}' performs a write action. "
                            "Re-call execute_tool with confirmed=true to proceed."
                        ),
                        "tool_id": tool_id,
                        "arguments": arguments,
                        "side_effect_level": side_effect,
                    }
                ),
            )
        ]

    # Dispatch to adapter
    adapter = record.get("execution_adapter") or {}
    kind = adapter.get("kind", "http") if isinstance(adapter, dict) else "http"

    try:
        if kind == "http":
            result = await _execute_http(record, adapter, arguments)
        elif kind == "subprocess":
            result = _execute_subprocess(record, adapter, arguments)
        else:
            result = {"error": f"Unsupported adapter kind: {kind}"}
    except Exception as exc:
        logger.error("Execution error for %s: %s", tool_id, exc)
        result = {"error": str(exc), "traceback": traceback.format_exc()}

    return [types.TextContent(type="text", text=json.dumps(result, indent=2))]


async def _execute_http(
    record: dict[str, Any],
    adapter: dict[str, Any],
    arguments: dict[str, Any],
) -> dict[str, Any]:
    """Execute an HTTP adapter."""
    method = adapter.get("method", "GET").upper()
    url_template = adapter.get("url_template", "")
    if not url_template:
        return {"error": "No url_template in execution_adapter"}

    # Substitute path parameters from arguments
    url = url_template
    body: dict[str, Any] = {}
    params: dict[str, Any] = {}
    for key, value in arguments.items():
        placeholder = "{" + key + "}"
        if placeholder in url:
            url = url.replace(placeholder, str(value))
        elif method == "GET":
            params[key] = value
        else:
            body[key] = value

    # Auth
    headers: dict[str, str] = dict(adapter.get("headers", {}))
    auth_info = record.get("auth", {})
    for env_var in auth_info.get("required_env", []):
        value = os.environ.get(env_var)
        if value:
            headers["Authorization"] = f"Bearer {value}"
            break

    async with httpx.AsyncClient(timeout=30.0) as client:
        if method == "GET":
            response = await client.get(url, params=params, headers=headers)
        elif method == "POST":
            response = await client.post(url, json=body, headers=headers)
        elif method == "PUT":
            response = await client.put(url, json=body, headers=headers)
        elif method == "PATCH":
            response = await client.patch(url, json=body, headers=headers)
        elif method == "DELETE":
            response = await client.delete(url, headers=headers)
        else:
            return {"error": f"Unsupported HTTP method: {method}"}

    try:
        return response.json()
    except Exception:
        return {"status_code": response.status_code, "body": response.text}


def _execute_subprocess(
    record: dict[str, Any],
    adapter: dict[str, Any],
    arguments: dict[str, Any],
) -> dict[str, Any]:
    """Execute a subprocess adapter with sandboxing."""
    if not adapter.get("sandbox", True):
        return {"error": "Non-sandboxed subprocess execution is not permitted."}

    command = adapter.get("command", "")
    args_template = list(adapter.get("args_template", []))
    timeout = int(adapter.get("timeout_seconds", 30))

    if not command:
        return {"error": "No command in execution_adapter"}

    # Substitute {{variable}} placeholders in args
    rendered_args = []
    for arg in args_template:
        for key, value in arguments.items():
            arg = arg.replace("{{" + key + "}}", str(value))
        rendered_args.append(arg)

    cmd = [command] + rendered_args
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return {
            "exit_code": proc.returncode,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
        }
    except subprocess.TimeoutExpired:
        return {"error": f"Command timed out after {timeout}s"}
    except FileNotFoundError:
        return {"error": f"Command not found: {command}"}


# ---------------------------------------------------------------------------
# Internal ingest endpoint (used by harvester, not exposed to MCP clients)
# ---------------------------------------------------------------------------

def ingest_tool_candidate(candidate_json: dict[str, Any]) -> dict[str, Any]:
    """
    Internal-only: normalise, verify, and store a candidate record.
    Not exposed as an MCP tool.
    """
    with ToolbankHarvester() as harvester:
        rec = harvester.normalize(candidate_json)
        result = harvester.verify(rec)
        if result["passed"]:
            harvester.publish(rec)
            return {"status": "published", "id": rec["id"]}
        else:
            database.enqueue_for_review(
                rec["id"], rec, rec.get("confidence", 0.0), result["issues"]
            )
            database.upsert_tool(rec)
            return {"status": "queued_for_review", "id": rec["id"], "issues": result["issues"]}


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

async def main():
    database.init_db()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
