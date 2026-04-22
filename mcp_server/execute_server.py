"""
FastMCP HTTP server for tool execution (no stdio blocking).
Exposes MCP tools via /mcp (JSON-RPC) AND REST endpoint via custom_route.

Run with:
    python -m mcp_server.execute_server
    or
    uvicorn mcp_server.execute_server:app --port 8765
"""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Any

import httpx
from mcp.server.fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse

from mcp_server import database, vector_store
from mcp_server.logging_config import setup_logging

setup_logging()
logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------
# FastMCP server (tools exposed at /mcp via JSON-RPC)
# --------------------------------------------------------------------------

mcp = FastMCP("toolbank-execute")


@mcp.tool()
async def search_tools(
    query: str,
    n_results: int = 5,
    namespace: str | None = None,
    side_effect_level: str | None = None,
) -> str:
    """Search the toolbank for capabilities matching a natural language query."""
    if not query:
        return json.dumps({"error": "query is required"})

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

    if not results:
        database.log_failed_query(
            user_goal=query,
            failed_query=query,
            tools_returned=[],
        )

    return json.dumps(results, indent=2)


# --------------------------------------------------------------------------
# Internal execution helpers
# --------------------------------------------------------------------------

def _substitute_template(template: str, args: dict[str, Any]) -> str:
    """Substitute {key} placeholders in a template string with values from args."""
    result = template
    for key, value in args.items():
        result = result.replace("{" + key + "}", str(value))
    return result


def _build_body_from_arguments(arguments: dict[str, Any]) -> dict[str, Any]:
    """Build a JSON-safe body dict from execution arguments."""
    body: dict[str, Any] = {}
    for key, value in arguments.items():
        try:
            json.dumps(value)
            body[key] = value
        except (TypeError, ValueError):
            logger.warning("Argument '%s' is not JSON-serialisable; skipped", key)
    return body


async def _execute_http(record, adapter, arguments):
    """Execute an HTTP adapter."""
    method = adapter.get("method", "GET").upper()
    raw_url = adapter.get("url_template", "")
    if not raw_url:
        return {"error": "No url_template in execution_adapter"}

    url = _substitute_template(raw_url, arguments)
    headers = {
        k: _substitute_template(v, arguments)
        for k, v in adapter.get("headers", {}).items()
    }
    headers.setdefault("Content-Type", "application/json")

    auth_info = record.get("auth", {})
    for env_var in auth_info.get("required_env", []):
        value = os.environ.get(env_var)
        if value:
            headers["Authorization"] = f"Bearer {value}"
            break

    body = _build_body_from_arguments(arguments) if method not in ("GET", "HEAD") else None

    async with httpx.AsyncClient(timeout=30.0) as client:
        if method == "GET":
            response = await client.get(url, headers=headers)
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


async def _execute_graphql(record, adapter, arguments):
    """Execute a GraphQL adapter."""
    raw_url = adapter.get("url_template", "")
    if not raw_url:
        return {"error": "No url_template in execution_adapter"}

    url = _substitute_template(raw_url, arguments)
    headers: dict[str, str] = {}
    for k, v in adapter.get("headers", {}).items():
        headers[k] = _substitute_template(v, arguments)

    auth_info = record.get("auth", {})
    for env_var in auth_info.get("required_env", []):
        value = os.environ.get(env_var)
        if value:
            headers["Authorization"] = f"Bearer {value}"
            break

    body: dict[str, Any] = {"query": adapter.get("query", "")}
    if adapter.get("variables"):
        body["variables"] = _build_body_from_arguments(arguments)

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(url, json=body, headers=headers)

    try:
        return response.json()
    except Exception:
        return {"status_code": response.status_code, "body": response.text}


async def _execute_webhook(record, adapter, arguments):
    """Execute a webhook POST to a URL with JSON body and custom headers."""
    raw_url = adapter.get("url_template", "")
    if not raw_url:
        return {"error": "No url_template in execution_adapter"}

    url = _substitute_template(raw_url, arguments)
    headers = {
        k: _substitute_template(v, arguments)
        for k, v in adapter.get("headers", {}).items()
    }
    headers.setdefault("Content-Type", "application/json")

    auth_info = record.get("auth", {})
    for env_var in auth_info.get("required_env", []):
        value = os.environ.get(env_var)
        if value:
            headers["Authorization"] = f"Bearer {value}"
            break

    method = adapter.get("method", "POST").upper()

    if adapter.get("body_template"):
        body_text = _substitute_template(adapter["body_template"], arguments)
        try:
            body: dict[str, Any] = json.loads(body_text)
        except (TypeError, ValueError):
            logger.warning("Webhook body_template is not valid JSON; using raw arguments")
            body = _build_body_from_arguments(arguments)
    else:
        body = _build_body_from_arguments(arguments)

    async with httpx.AsyncClient(timeout=30.0) as client:
        if method == "GET":
            response = await client.get(url, headers=headers)
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


async def _do_execute(tool_id: str, arguments: dict[str, Any], confirmed: bool) -> dict[str, Any]:
    """Core execution logic — used by both MCP tool and REST endpoint."""
    if not tool_id:
        return {"error": "tool_id is required"}

    record = database.get_tool(tool_id)
    if not record:
        return {"error": f"Tool not found: {tool_id}"}

    if record.get("status") not in ("approved", "verified"):
        return {
            "error": "Tool is not approved for execution.",
            "status": record.get("status"),
            "tool_id": tool_id,
        }

    side_effect = record.get("side_effect_level", "read")

    if side_effect == "destructive" and not database.is_destructive_approved(tool_id):
        return {
            "error": "Destructive tools are blocked unless explicitly approved by an administrator.",
            "tool_id": tool_id,
            "side_effect_level": side_effect,
        }

    if side_effect == "write" and not confirmed:
        return {
            "status": "confirmation_required",
            "message": (
                f"Tool '{tool_id}' performs a write action. "
                "Re-call with confirmed=true to proceed."
            ),
            "tool_id": tool_id,
            "arguments": arguments,
            "side_effect_level": side_effect,
        }

    adapter = record.get("execution_adapter") or {}
    kind = adapter.get("kind", "http") if isinstance(adapter, dict) else "http"
    start_ms = int(time.monotonic() * 1000)
    status = "success"
    result: dict[str, Any] = {}

    try:
        if kind == "http":
            result = await _execute_http(record, adapter, arguments)
        elif kind == "graphql":
            result = await _execute_graphql(record, adapter, arguments)
        elif kind == "webhook":
            result = await _execute_webhook(record, adapter, arguments)
        else:
            result = {"error": f"Unsupported adapter kind: {kind}"}
    except Exception as exc:
        logger.error("Execution error for %s: %s", tool_id, exc)
        result = {"error": str(exc)}
        status = "error"
    finally:
        duration_ms = int(time.monotonic() * 1000) - start_ms
        error_msg = result.get("error") if isinstance(result, dict) else None
        database.log_tool_execution(
            tool_id=tool_id,
            arguments=arguments,
            result=result,
            status=status,
            duration_ms=duration_ms,
            error_message=error_msg,
        )

    return result


# --------------------------------------------------------------------------
# REST endpoint (added via custom_route on the FastMCP app)
# --------------------------------------------------------------------------

@mcp.custom_route("/tools/execute", methods=["POST"], name="execute_tool_rest")
async def execute_tool_rest(request: Request) -> JSONResponse:
    """REST endpoint: POST /tools/execute

    Body: { "tool_id": "...", "arguments": {...}, "confirmed": false }
    """
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON body"}, status_code=400)

    tool_id = body.get("tool_id", "")
    arguments = body.get("arguments", {}) or {}
    confirmed = bool(body.get("confirmed", False))

    result = await _do_execute(tool_id, arguments, confirmed)
    status_code = 200
    if isinstance(result, dict) and result.get("status") == "confirmation_required":
        status_code = 202
    return JSONResponse(result, status_code=status_code)


@mcp.custom_route("/tools/list", methods=["GET"], name="list_tools_rest")
async def list_tools_rest(request: Request) -> JSONResponse:
    """REST endpoint: GET /tools/list?status=approved&limit=50"""
    from urllib.parse import parse_qs

    query = parse_qs(request.url.query)
    status = query.get("status", ["approved"])[0]
    limit = int(query.get("limit", ["50"])[0])

    tools = database.list_tools(status=status, limit=limit)
    return JSONResponse({"tools": tools, "count": len(tools)})


# --------------------------------------------------------------------------
# MCP tool wrappers (delegate to _do_execute)
# --------------------------------------------------------------------------

@mcp.tool()
async def execute_tool(
    tool_id: str,
    arguments: dict[str, Any] | None = None,
    confirmed: bool = False,
) -> str:
    """Execute a tool from the toolbank by its ID."""
    arguments = arguments or {}
    result = await _do_execute(tool_id, arguments, bool(confirmed))
    return json.dumps(result, indent=2)


@mcp.tool()
def approve_destructive_tool(tool_id: str, reason: str = "") -> str:
    """Administratively approve a destructive tool for execution."""
    if not tool_id:
        return json.dumps({"error": "tool_id is required"})

    record = database.get_tool(tool_id)
    if not record:
        return json.dumps({"error": f"Tool not found: {tool_id}"})

    if record.get("side_effect_level") != "destructive":
        return json.dumps(
            {
                "error": (
                    f"Tool '{tool_id}' is not destructive "
                    f"(side_effect_level='{record.get('side_effect_level')}'). "
                    "Only destructive tools require administrative approval."
                )
            }
        )

    approver = os.environ.get("MCP_ADMIN_EMAIL", "unknown@admin")
    success = database.approve_destructive_tool(tool_id, approver, reason)

    if success:
        return json.dumps(
            {
                "status": "approved",
                "tool_id": tool_id,
                "approver": approver,
                "message": f"Destructive tool '{tool_id}' has been approved for execution.",
            }
        )
    else:
        return json.dumps({"error": "Failed to record approval."})


# --------------------------------------------------------------------------
# ASGI app (uvicorn target)
# --------------------------------------------------------------------------

app = mcp.streamable_http_app()


# --------------------------------------------------------------------------
# Entry point (stdio — for MCP clients)
# --------------------------------------------------------------------------

async def main():
    database.init_db()
    await mcp.run()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
