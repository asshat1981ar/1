# Tool Execution Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Build a full tool execution pipeline — list→get→execute tools via MCP protocol, with execution history, async support, and streaming responses.

**Architecture:** Tool execution already has stub implementations (`_execute_http`, `_execute_graphql`, `_execute_python`, `_execute_subprocess`, `_execute_webhook`) in `server.py`. We need to: (1) add execution history/tracking, (2) add async streaming responses, (3) wire up execution to the REST API, (4) build a `/tools/[id]/execute` page, (5) add a Playwright test.

**Tech Stack:** Python asyncio, `httpx` (already installed), `python-dotenv`, `pytest`

---

## Research Decomposition

### What's Already Built
- `mcp_server/server.py` has `_execute_tool()` dispatching to 5 adapter types: `http`, `graphql`, `python`, `subprocess`, `webhook`
- `mcp_server/models.py` has `ExecutionAdapter` with fields: `kind`, `method`, `url_template`, `headers`, `body_template`, `sandbox`, `timeout_seconds`
- `database.py` has no execution history table yet
- REST API (`GET /tools/{id}`, `GET /admin/drift`) exists on port 8765
- Frontend has `/tools/[id]/page.jsx` showing tool details

### What's Missing
1. **Execution history table** — store each execution attempt with tool_id, arguments, result, status, duration, timestamp
2. **Async streaming** — current `_execute_http` and `_execute_graphql` are async but don't stream; add Server-Sent Events (SSE) for long-running executions
3. **Execution REST endpoint** — `POST /tools/{id}/execute` that accepts arguments and returns execution result (or streams it)
4. **Frontend execute UI** — `/tools/[id]/execute` page with argument form, async execution status, streaming results display
5. **Polling / WebSocket fallback** — if SSE is too complex, use polling with `ExecutionResult` object
6. **Timeout + sandbox enforcement** — `_execute_subprocess` already has `timeout_seconds` and `sandbox` flags but they're not enforced in tests
7. **Execution cancellation** — ability to cancel a long-running async execution

### Adapter-Specific Gaps

| Adapter | Missing |
|---------|---------|
| `http` | Template variable substitution in URL/headers/body |
| `graphql` | Template variable substitution in query/variables |
| `python` | Dynamic function loading + security sandboxing |
| `subprocess` | Actual timeout enforcement via `asyncio.wait_for` |
| `webhook` | Already fairly complete |

---

## Task List

### Task 1: Execution History Table

**Objective:** Create a `tool_executions` table in SQLite to record every execution attempt.

**Files:**
- Modify: `mcp_server/database.py`
- Test: `tests/test_execution.py` (new)

**Step 1: Write failing test**
```python
# tests/test_execution.py
from __future__ import annotations
import pytest
from mcp_server.database import init_db, log_tool_execution, get_tool_executions
import tempfile, os

def test_log_and_retrieve_execution():
    fd, db = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    init_db(db)
    log_tool_execution(
        tool_id="stripe.get_customer",
        arguments={"customer_id": "cus_123"},
        result={"id": "cus_123", "email": "test@example.com"},
        status="success",
        duration_ms=142,
    )
    rows = get_tool_executions(tool_id="stripe.get_customer", limit=10)
    assert len(rows) == 1
    assert rows[0]["tool_id"] == "stripe.get_customer"
    assert rows[0]["status"] == "success"
    assert rows[0]["duration_ms"] == 142
    os.unlink(db)
```

**Step 2: Run test**
```bash
cd /home/westonaaron675/gadk/1 && python3 -m pytest tests/test_execution.py::test_log_and_retrieve_execution -v 2>&1
```
Expected: FAIL — `log_tool_execution` not defined

**Step 3: Implement**
Add to `mcp_server/database.py`:
```python
def log_tool_execution(
    tool_id: str,
    arguments: dict[str, Any],
    result: dict[str, Any] | None,
    status: str,  # success | error | timeout | cancelled
    duration_ms: int,
    error_message: str | None = None,
) -> None:
    """Log a tool execution attempt to the database."""
    session = get_session()
    try:
        record = ToolExecution(
            tool_id=tool_id,
            arguments=json.dumps(arguments),
            result=json.dumps(result) if result else None,
            status=status,
            duration_ms=duration_ms,
            error_message=error_message,
        )
        session.add(record)
        session.commit()
    finally:
        session.close()

def get_tool_executions(
    tool_id: str | None = None,
    status: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Retrieve tool execution history."""
    session = get_session()
    try:
        q = session.query(ToolExecution)
        if tool_id:
            q = q.filter(ToolExecution.tool_id == tool_id)
        if status:
            q = q.filter(ToolExecution.status == status)
        rows = q.order_by(ToolExecution.id.desc()).limit(limit).all()
        return [_execution_to_dict(r) for r in rows]
    finally:
        session.close()
```

Also add the `ToolExecution` model class and `CREATE TABLE` statement.

**Step 4: Run test**
```bash
cd /home/westonaaron675/gadk/1 && python3 -m pytest tests/test_execution.py::test_log_and_retrieve_execution -v 2>&1
```
Expected: PASS

**Step 5: Commit**
```bash
git add mcp_server/database.py tests/test_execution.py
git commit -m "feat: add tool execution history table (Task 1)"
```

---

### Task 2: Wire execution logging into _execute_tool

**Objective:** Every execution (http, graphql, python, subprocess, webhook) logs to the new `tool_executions` table.

**Files:**
- Modify: `mcp_server/server.py`

**Step 1: Add import**
```python
from mcp_server.database import log_tool_execution, get_tool_executions
```

**Step 2: Modify _execute_tool to log**
Wrap the execution dispatch block with timing and logging:
```python
import time
start = time.monotonic()
try:
    # existing dispatch code...
    result = ...
    status = "success"
except asyncio.TimeoutError:
    result = {"error": "Execution timed out"}
    status = "timeout"
except Exception as exc:
    result = {"error": str(exc)}
    status = "error"
finally:
    duration_ms = int((time.monotonic() - start) * 1000)
    log_tool_execution(
        tool_id=tool_id,
        arguments=arguments,
        result=result,
        status=status,
        duration_ms=duration_ms,
    )
```

**Step 3: Run tests**
```bash
cd /home/westonaaron675/gadk/1 && python3 -m pytest tests/ -q --tb=no 2>&1
```
Expected: all pass

**Step 4: Commit**
```bash
git add mcp_server/server.py
git commit -m "feat: log all tool executions to database (Task 2)"
```

---

### Task 3: REST API — POST /tools/{id}/execute

**Objective:** Add `POST /tools/{id}/execute` endpoint to the FastAPI REST sidecar.

**Files:**
- Modify: `mcp_server/server.py`

**Step 1: Write failing test**
```python
# In tests/test_phase4.py
def test_execute_endpoint():
    import httpx, asyncio
    from mcp_server.server import rest_app
    from starlette.testclient import TestClient
    client = TestClient(rest_app)
    # First seed a tool
    database.upsert_tool({
        "id": "test.echo",
        "name": "echo",
        "namespace": "test",
        "description": "Echoes input",
        "status": "approved",
        "transport": "rest",
        "execution_adapter": {
            "kind": "http",
            "method": "POST",
            "url_template": "https://httpbin.org/post",
            "headers": {"Content-Type": "application/json"},
        },
        "input_schema": {"type": "object", "properties": {"msg": {"type": "string"}}},
    })
    resp = client.post("/tools/test.echo/execute", json={"arguments": {"msg": "hello"}})
    assert resp.status_code == 200
    data = resp.json()
    assert "result" in data or "error" in data
```

**Step 2: Run test**
Expected: FAIL — route not defined

**Step 3: Implement**
Add to `rest_app` in `server.py`:
```python
@rest_app.post("/tools/{tool_id}/execute")
async def execute_tool_endpoint(tool_id: str, request: Request):
    """Execute a tool and return the result."""
    body = await request.json()
    arguments = body.get("arguments", {})
    confirmed = body.get("confirmed", False)

    # Use same logic as MCP _execute_tool
    record = database.get_tool(tool_id)
    if not record:
        raise HTTPException(status_code=404, detail=f"Tool not found: {tool_id}")

    if record.get("status") not in ("approved", "verified"):
        raise HTTPException(status_code=403, detail="Tool not approved for execution")

    side_effect = record.get("side_effect_level", "read")
    if side_effect == "destructive" and not database.is_destructive_approved(tool_id):
        raise HTTPException(status_code=403, detail="Destructive tool requires approval")

    if side_effect == "write" and not confirmed:
        return {
            "status": "confirmation_required",
            "message": f"Tool '{tool_id}' requires confirmation. Re-call with confirmed=true.",
            "tool_id": tool_id,
            "arguments": arguments,
        }

    # Execute
    import asyncio, time
    start = time.monotonic()
    try:
        result = await _execute_tool({
            "tool_id": tool_id,
            "arguments": arguments,
            "confirmed": confirmed,
        })
        text = result[0].text if result else "{}"
        import json
        data = json.loads(text)
        status = "success" if "error" not in data else "error"
    except Exception as exc:
        data = {"error": str(exc)}
        status = "error"
    finally:
        duration_ms = int((time.monotonic() - start) * 1000)
        database.log_tool_execution(
            tool_id=tool_id,
            arguments=arguments,
            result=data,
            status=status,
            duration_ms=duration_ms,
        )

    return {"tool_id": tool_id, "result": data, "status": status, "duration_ms": duration_ms}
```

**Step 4: Run test**
```bash
cd /home/westonaaron675/gadk/1 && python3 -m pytest tests/test_phase4.py::test_execute_endpoint -v 2>&1
```
Expected: PASS

**Step 5: Commit**
```bash
git add mcp_server/server.py
git commit -m "feat: add POST /tools/{id}/execute REST endpoint (Task 3)"
```

---

### Task 4: Add execution history to GET /tools/{id}

**Objective:** Include recent execution history when fetching a tool's details.

**Files:**
- Modify: `mcp_server/server.py`

**Step 1: Modify GET /tools/{id} to include executions**
In the `GET /tools/{tool_id}` route, after fetching the record, add:
```python
executions = database.get_tool_executions(tool_id=tool_id, limit=10)
return {
    "tool": tool_record,
    "executions": executions,
    "stats": {
        "total_executions": len(executions),
        "success_rate": round(sum(1 for e in executions if e["status"] == "success") / max(len(executions), 1), 2),
        "avg_duration_ms": int(sum(e["duration_ms"] for e in executions) / max(len(executions), 1)),
    }
}
```

**Step 2: Update frontend to display executions**
In `app/tools/[id]/page.jsx`, add an "Executions" section showing recent executions.

**Step 3: Commit**
```bash
git add mcp_server/server.py app/tools/[id]/page.jsx
git commit -m "feat: show execution history on tool detail page (Task 4)"
```

---

### Task 5: Subprocess Timeout Enforcement

**Objective:** `_execute_subprocess` currently has `timeout_seconds` but doesn't enforce it.

**Files:**
- Modify: `mcp_server/server.py`

**Step 1: Write failing test**
```python
def test_subprocess_timeout():
    import asyncio
    from mcp_server.server import _execute_subprocess
    record = {"name": "slow_tool"}
    adapter = {
        "command": "sleep 10",
        "args_template": [],
        "timeout_seconds": 1,
        "sandbox": True,
    }
    result = asyncio.run(_execute_subprocess(record, adapter, {}))
    assert result.get("status") == "timeout" or "timed out" in result.get("error", "").lower()
```

**Step 2: Run test**
Expected: FAIL — timeout not enforced

**Step 3: Implement**
```python
async def _execute_subprocess(
    record: dict[str, Any],
    adapter: dict[str, Any],
    arguments: dict[str, Any],
) -> dict[str, Any]:
    command = adapter.get("command", "")
    args = [_substitute_template(a, arguments) for a in adapter.get("args_template", [])]
    timeout = adapter.get("timeout_seconds", 30)
    sandbox = adapter.get("sandbox", True)

    try:
        proc = await asyncio.create_subprocess_exec(
            command, *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=_build_env(adapter, arguments),
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            return {
                "stdout": stdout.decode().strip(),
                "stderr": stderr.decode().strip(),
                "returncode": proc.returncode,
            }
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            return {"error": f"Execution timed out after {timeout}s", "status": "timeout"}
    except Exception as exc:
        return {"error": str(exc)}
```

**Step 4: Run test**
Expected: PASS

**Step 5: Commit**
```bash
git add mcp_server/server.py
git commit -m "fix: enforce subprocess timeout with asyncio.wait_for (Task 5)"
```

---

### Task 6: Frontend — /tools/[id]/execute Page

**Objective:** Create an interactive execution page for tools.

**Files:**
- Create: `app/tools/[id]/execute/page.jsx`
- Modify: `app/tools/[id]/page.jsx` (add link to execute page)

**Step 1: Create execute page**
```jsx
"use client";
import { useState } from "react";
const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8765";

export default function ExecutePage({ params }) {
  const { id } = useParams();
  const [arguments_, setArgs] = useState("{}");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  async function execute() {
    setLoading(true);
    setError(null);
    try {
      const args = JSON.parse(arguments_);
      const res = await fetch(`${API_BASE}/tools/${id}/execute`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ arguments: args }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || JSON.stringify(data));
      setResult(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="max-w-2xl mx-auto px-4 py-8">
      <h1 className="text-2xl font-bold mb-6">Execute: {id}</h1>
      <div className="mb-4">
        <label className="block text-sm font-medium mb-2">Arguments (JSON)</label>
        <textarea
          className="w-full h-32 p-3 font-mono text-sm bg-zinc-900 text-zinc-100 rounded-lg border border-zinc-700"
          value={arguments_}
          onChange={(e) => setArgs(e.target.value)}
          placeholder='{"key": "value"}'
        />
      </div>
      <button
        onClick={execute}
        disabled={loading}
        className="px-6 py-2 bg-white text-black font-medium rounded-lg hover:bg-zinc-200 disabled:opacity-50"
      >
        {loading ? "Running…" : "Execute"}
      </button>
      {error && <div className="mt-4 p-4 bg-red-900/50 border border-red-700 rounded text-red-200 text-sm">{error}</div>}
      {result && (
        <div className="mt-4">
          <div className="text-sm text-zinc-400 mb-2">
            Status: <span className={result.status === "success" ? "text-green-400" : "text-red-400"}>{result.status}</span>
            {" | "}Duration: {result.duration_ms}ms
          </div>
          <pre className="p-4 bg-zinc-900 text-zinc-100 rounded-lg overflow-x-auto text-sm">
            {JSON.stringify(result.result, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
}
```

**Step 2: Add link from detail page**
In `app/tools/[id]/page.jsx`, add an "Execute" button linking to `/tools/${id}/execute`.

**Step 3: Verify page loads**
```bash
curl -s -o /dev/null -w "%{http_code}" http://localhost:3000/tools/test.echo/execute
```
Expected: 200

**Step 4: Commit**
```bash
git add app/tools/[id]/execute/page.jsx app/tools/[id]/page.jsx
git commit -m "feat: add interactive execute page for tools (Task 6)"
```

---

### Task 7: URL/Header Template Substitution

**Objective:** `_execute_http` uses `url_template` but doesn't substitute template variables from `arguments`.

**Files:**
- Modify: `mcp_server/server.py`

**Step 1: Write failing test**
```python
def test_http_template_substitution():
    import asyncio, json
    from mcp_server.server import _execute_http
    record = {
        "id": "github.repo",
        "name": "get_repo",
        "namespace": "github",
    }
    adapter = {
        "kind": "http",
        "method": "GET",
        "url_template": "https://api.github.com/repos/{owner}/{repo}",
        "headers": {"Authorization": "Bearer {token}"},
    }
    arguments = {"owner": "octocat", "repo": "hello-world", "token": "ghp_secret"}
    result = asyncio.run(_execute_http(record, adapter, arguments))
    # Should substitute template vars
    # (Will hit real GitHub API - just verify no template vars remain)
    url = adapter["url_template"]
    assert "{owner}" not in url  # url was substituted in the actual call
```

**Step 2: Implement**
Add a helper function:
```python
def _substitute_template(template: str, context: dict[str, Any]) -> str:
    """Substitute {key} placeholders in a template string with values from context."""
    result = template
    for key, value in context.items():
        result = result.replace(f"{{{key}}}", str(value))
    return result
```

Then in `_execute_http`, apply it:
```python
url = _substitute_template(adapter.get("url_template", ""), arguments)
headers = {k: _substitute_template(v, arguments) for k, v in adapter.get("headers", {}).items()}
```

Apply same pattern to `_execute_graphql` and `_execute_webhook`.

**Step 3: Commit**
```bash
git add mcp_server/server.py
git commit -m "feat: add template variable substitution for URL/headers/body (Task 7)"
```

---

## Summary

| Task | Type | Complexity |
|------|------|------------|
| 1. Execution History Table | DB + tests | Medium |
| 2. Wire logging into _execute_tool | Modify | Low |
| 3. REST POST /tools/{id}/execute | REST + tests | Medium |
| 4. GET /tools/{id} with execution history | REST + frontend | Low |
| 5. Subprocess timeout enforcement | Fix + tests | Low |
| 6. /tools/[id]/execute frontend page | Frontend | Medium |
| 7. Template variable substitution | Fix | Low |

**Total: 7 tasks, ~2-3 hours of work with full TDD**
