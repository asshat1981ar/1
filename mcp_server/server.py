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
import time
import traceback
from typing import Any

import httpx
from mcp.server.stdio import stdio_server

from mcp import types
from mcp.server import Server
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
                "Supports http, graphql, python, subprocess, and webhook adapters. "
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
        types.Tool(
            name="approve_destructive_tool",
            description=(
                "Administratively approve a destructive tool for execution. "
                "Destructive tools (side_effect_level='destructive') are blocked by default. "
                "Calling this tool with a tool_id grants permission for that tool to run. "
                "Approvals are persisted in the registry and survive server restarts."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "tool_id": {
                        "type": "string",
                        "description": "The unique ID of the destructive tool to approve.",
                    },
                    "reason": {
                        "type": "string",
                        "description": "Optional reason for the approval (for audit trail).",
                        "default": "",
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
    if name == "approve_destructive_tool":
        return _approve_destructive_tool(arguments)
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

def _approve_destructive_tool(args: dict[str, Any]) -> list[types.TextContent]:
    """Handle the approve_destructive_tool MCP tool call."""
    tool_id = args.get("tool_id", "")
    admin_token = args.get("admin_token", "")
    reason = args.get("reason", "")

    # Validate admin token against env var
    expected_token = os.environ.get("MCP_ADMIN_TOKEN", "")
    if not expected_token:
        return [
            types.TextContent(
                type="text",
                text=json.dumps({"error": "Admin approval is not configured (MCP_ADMIN_TOKEN not set)."}),
            )
        ]
    if admin_token != expected_token:
        return [
            types.TextContent(
                type="text",
                text=json.dumps({"error": "Invalid admin token."}),
            )
        ]

    if not tool_id:
        return [
            types.TextContent(
                type="text",
                text=json.dumps({"error": "tool_id is required"}),
            )
        ]

    # Look up the tool to verify it exists and is destructive
    record = database.get_tool(tool_id)
    if not record:
        return [
            types.TextContent(
                type="text",
                text=json.dumps({"error": f"Tool not found: {tool_id}"}),
            )
        ]

    if record.get("side_effect_level") != "destructive":
        return [
            types.TextContent(
                type="text",
                text=json.dumps(
                    {
                        "error": f"Tool '{tool_id}' is not destructive (side_effect_level="
                        f"'{record.get('side_effect_level')}'). Only destructive tools "
                        "require administrative approval."
                    }
                ),
            )
        ]

    approver = os.environ.get("MCP_ADMIN_EMAIL", "unknown@admin")
    success = database.approve_destructive_tool(tool_id, approver, reason)

    if success:
        return [
            types.TextContent(
                type="text",
                text=json.dumps(
                    {
                        "status": "approved",
                        "tool_id": tool_id,
                        "approver": approver,
                        "message": f"Destructive tool '{tool_id}' has been approved for execution.",
                    }
                ),
            )
        ]
    else:
        return [
            types.TextContent(
                type="text",
                text=json.dumps({"error": "Failed to record approval."}),
            )
        ]


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
    if side_effect == "destructive" and not database.is_destructive_approved(tool_id):
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
    start_ms = int(time.monotonic() * 1000)
    status = "success"

    try:
        if kind == "http":
            result = await _execute_http(record, adapter, arguments)
        elif kind == "graphql":
            result = await _execute_graphql(record, adapter, arguments)
        elif kind == "python":
            result = _execute_python(record, adapter, arguments)
        elif kind == "subprocess":
            result = _execute_subprocess(record, adapter, arguments)
        elif kind == "graphql":
            result = await _execute_graphql(record, adapter, arguments)
        elif kind == "python_func":
            result = _execute_python_func(record, adapter, arguments)
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

    return [types.TextContent(type="text", text=json.dumps(result, indent=2))]


def _substitute_template(template: str, arguments: dict[str, Any]) -> str:
    """Substitute {key} placeholders in a template string with values from arguments.

    Missing keys are left as-is. Numeric values are stringified.
    """
    result = template
    for key, value in arguments.items():
        result = result.replace("{" + key + "}", str(value))
    return result


def _build_body_from_arguments(arguments: dict[str, Any]) -> dict[str, Any]:
    """Build a JSON-safe body dict from execution arguments."""
    import json as _json

    body: dict[str, Any] = {}
    for key, value in arguments.items():
        try:
            _json.dumps(value)  # verify serialisable
            body[key] = value
        except (TypeError, ValueError):
            logger.warning("Argument '%s' is not JSON-serialisable; skipped", key)
    return body


async def _execute_webhook(
    record: dict[str, Any],
    adapter: dict[str, Any],
    arguments: dict[str, Any],
) -> dict[str, Any]:
    """Execute a webhook POST to a URL with JSON body and custom headers."""
    raw_url = adapter.get("url_template", "")
    if not raw_url:
        return {"error": "No url_template in execution_adapter"}

    # Substitute {key} placeholders in URL and headers
    url = _substitute_template(raw_url, arguments)
    headers: dict[str, str] = {
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

    # Build body — prefer body_template with substitution, fall back to raw arguments
    import json as _json

    if adapter.get("body_template"):
        body_text = _substitute_template(adapter["body_template"], arguments)
        try:
            body: dict[str, Any] = _json.loads(body_text)
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


async def _execute_http(
    record: dict[str, Any],
    adapter: dict[str, Any],
    arguments: dict[str, Any],
) -> dict[str, Any]:
    """Execute an HTTP adapter."""
    method = adapter.get("method", "GET").upper()
    raw_url = adapter.get("url_template", "")
    if not raw_url:
        return {"error": "No url_template in execution_adapter"}

    # Substitute {key} placeholders in URL and headers
    url = _substitute_template(raw_url, arguments)
    headers: dict[str, str] = {
        k: _substitute_template(v, arguments)
        for k, v in adapter.get("headers", {}).items()
    }
    body: dict[str, Any] = {}
    params: dict[str, Any] = {}
    for key, value in arguments.items():
        placeholder = "{" + key + "}"
        if placeholder in raw_url:
            pass  # already substituted in URL
        elif method == "GET":
            params[key] = value
        else:
            body[key] = value

    # Auth
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


async def _execute_graphql(
    record: dict[str, Any],
    adapter: dict[str, Any],
    arguments: dict[str, Any],
) -> dict[str, Any]:
    """Execute a GraphQL adapter (POST query + variables to url_template)."""
    raw_url = adapter.get("url_template", "")
    if not raw_url:
        return {"error": "No url_template in execution_adapter"}

    gql_query = adapter.get("query", "")
    if not gql_query:
        return {"error": "No 'query' field in execution_adapter for graphql kind"}

    # Substitute {key} placeholders in URL and headers
    url = _substitute_template(raw_url, arguments)
    headers: dict[str, str] = {
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

    payload = {"query": gql_query, "variables": _sanitize_graphql_variables(arguments)}
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(url, json=payload, headers=headers)

    try:
        return response.json()
    except Exception:
        return {"status_code": response.status_code, "body": response.text}


def _sanitize_graphql_variables(variables: dict[str, Any]) -> dict[str, Any]:
    """
    Validate that all variable values are JSON-serialisable primitives or
    collections. Keys must be non-empty strings. This prevents injection of
    unexpected types while still allowing nested objects (which are valid
    GraphQL variable types).
    """
    import json as _json

    sanitized: dict[str, Any] = {}
    for key, value in variables.items():
        if not isinstance(key, str) or not key:
            continue
        try:
            # Round-trip through JSON to reject non-serialisable values
            sanitized[key] = _json.loads(_json.dumps(value))
        except (TypeError, ValueError):
            logger.warning("GraphQL variable '%s' is not JSON-serialisable; skipped", key)
    return sanitized


_PYTHON_ADAPTER_ALLOWLIST = frozenset(
    {
        "json",
        "math",
        "re",
        "datetime",
        "collections",
        "itertools",
        "functools",
        "string",
        "textwrap",
        "urllib.parse",
        "hashlib",
        "base64",
        "pathlib",
        "os",
    }
)


def _execute_python(
    record: dict[str, Any],
    adapter: dict[str, Any],
    arguments: dict[str, Any],
) -> dict[str, Any]:
    """
    Execute a Python function adapter.
    adapter.function must be a dotted path to a callable, e.g. 'mymodule.my_function'.
    Only modules listed in _PYTHON_ADAPTER_ALLOWLIST may be imported.
    """
    import importlib

    function_path = adapter.get("function", "")
    if not function_path:
        return {"error": "No 'function' field in execution_adapter for python kind"}

    parts = function_path.rsplit(".", 1)
    if len(parts) != 2:
        return {"error": f"Invalid function path '{function_path}' – expected 'module.callable'"}

    module_path, func_name = parts
    # Accept the full dotted path if allowlisted (e.g. urllib.parse),
    # otherwise fall back to the top-level module name.
    if module_path not in _PYTHON_ADAPTER_ALLOWLIST:
        top_level = module_path.split(".")[0]
        if top_level not in _PYTHON_ADAPTER_ALLOWLIST:
            return {
                "error": (
                    f"Module '{top_level}' is not in the Python adapter allowlist. "
                    f"Allowed: {sorted(_PYTHON_ADAPTER_ALLOWLIST)}"
                )
            }

    try:
        module = importlib.import_module(module_path)
    except ImportError as exc:
        return {"error": f"Could not import module '{module_path}': {exc}"}

    func = getattr(module, func_name, None)
    if func is None or not callable(func):
        return {"error": f"'{func_name}' not found or not callable in '{module_path}'"}

    # Validate argument names against the function signature to prevent
    # passing unexpected keyword arguments.
    import inspect as _inspect

    try:
        sig = _inspect.signature(func)
        has_var_keyword = any(
            p.kind == _inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values()
        )
        if not has_var_keyword:
            valid_params = set(sig.parameters.keys())
            bad_args = set(arguments.keys()) - valid_params
            if bad_args:
                return {
                    "error": (
                        f"Unknown argument(s) for '{function_path}': {sorted(bad_args)}. "
                        f"Expected parameters: {sorted(valid_params)}"
                    )
                }
    except (ValueError, TypeError):
        # inspect.signature may raise for built-ins; allow through
        pass

    try:
        output = func(**arguments)
        return {"result": output}
    except Exception as exc:
        logger.error("Python adapter error for %s: %s", record.get("id"), exc)
        return {"error": str(exc), "traceback": traceback.format_exc()}


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


async def _execute_graphql(
    record: dict[str, Any],
    adapter: dict[str, Any],
    arguments: dict[str, Any],
) -> dict[str, Any]:
    """Execute a GraphQL adapter by POSTing query + variables to the endpoint."""
    raw_url = adapter.get("url_template", "")
    if not raw_url:
        return {"error": "No url_template in execution_adapter"}

    # Substitute {key} placeholders in URL and headers
    url = _substitute_template(raw_url, arguments)
    headers: dict[str, str] = {
        k: _substitute_template(v, arguments)
        for k, v in adapter.get("headers", {}).items()
    }

    query = adapter.get("query", "")
    if not query:
        return {"error": "No query in execution_adapter"}

    variables_map: dict[str, str] = adapter.get("variables_map", {})
    variables = {gql_var: arguments.get(arg_key) for gql_var, arg_key in variables_map.items()}
    auth_info = record.get("auth", {})
    for env_var in auth_info.get("required_env", []):
        value = os.environ.get(env_var)
        if value:
            headers["Authorization"] = f"Bearer {value}"
            break

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            url,
            json={"query": query, "variables": variables},
            headers=headers,
        )

    try:
        return response.json()
    except Exception:
        return {"status_code": response.status_code, "body": response.text}


def _execute_python_func(
    record: dict[str, Any],
    adapter: dict[str, Any],
    arguments: dict[str, Any],
) -> dict[str, Any]:
    """Execute a Python function adapter via dynamic import."""
    import importlib

    module_path: str = adapter.get("module", "")
    func_name: str = adapter.get("function", "")
    allowlist: list[str] = adapter.get("allowlist", [])

    if not module_path:
        return {"error": "No module in execution_adapter"}
    if not func_name:
        return {"error": "No function in execution_adapter"}

    if allowlist and not any(module_path.startswith(prefix) for prefix in allowlist):
        return {"error": f"Module not in allowlist: {module_path}"}

    if not allowlist:
        logger.warning(
            "python_func adapter for '%s.%s' has an empty allowlist — "
            "any module may be imported; configure allowlist to restrict execution.",
            module_path,
            func_name,
        )

    try:
        mod = importlib.import_module(module_path)
        func = getattr(mod, func_name)
        return func(**arguments)
    except ImportError as exc:
        return {"error": f"Cannot import module '{module_path}': {exc}"}
    except AttributeError:
        return {"error": f"Function '{func_name}' not found in module '{module_path}'"}
    except Exception as exc:
        logger.error("python_func execution error: %s", exc)
        return {"error": str(exc), "traceback": traceback.format_exc()}



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
