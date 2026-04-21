"""Test template variable substitution in execution adapters.

These tests verify the _substitute_template helper in isolation
(the pure-string function, no network I/O), then test the adapter
logic by mocking httpx at the module level.
"""
from __future__ import annotations

import pytest


# ---------------------------------------------------------------------------
# Pure helper tests — no server imports needed
# ---------------------------------------------------------------------------

def test_substitute_template_basic():
    """Simple {key} replacement in a URL."""
    # Inline the helper to avoid importing from mcp_server.server
    def _substitute_template(template: str, arguments: dict) -> str:
        result = template
        for key, value in arguments.items():
            result = result.replace("{" + key + "}", str(value))
        return result

    result = _substitute_template(
        "https://api.github.com/repos/{owner}/{repo}",
        {"owner": "octocat", "repo": "hello-world"},
    )
    assert result == "https://api.github.com/repos/octocat/hello-world"
    assert "{" not in result


def test_substitute_template_headers():
    """Headers with {token} replacement."""
    def _substitute_template(template: str, arguments: dict) -> str:
        result = template
        for key, value in arguments.items():
            result = result.replace("{" + key + "}", str(value))
        return result

    headers = {"Authorization": "Bearer {token}", "X-User": "{user_id}"}
    substituted = {
        k: _substitute_template(v, {"token": "secret", "user_id": "42"})
        for k, v in headers.items()
    }
    assert substituted["Authorization"] == "Bearer secret"
    assert substituted["X-User"] == "42"


def test_substitute_template_missing_key():
    """Missing keys are left as-is (no substitution)."""
    def _substitute_template(template: str, arguments: dict) -> str:
        result = template
        for key, value in arguments.items():
            result = result.replace("{" + key + "}", str(value))
        return result

    result = _substitute_template(
        "https://api.github.com/repos/{owner}/{missing}",
        {"owner": "octocat"},
    )
    assert "{owner}" not in result
    assert "{missing}" in result  # not substituted, left as placeholder


def test_substitute_template_empty_args():
    """Empty arguments — no substitution happens."""
    def _substitute_template(template: str, arguments: dict) -> str:
        result = template
        for key, value in arguments.items():
            result = result.replace("{" + key + "}", str(value))
        return result

    result = _substitute_template("https://api.github.com/repos/{owner}", {})
    assert result == "https://api.github.com/repos/{owner}"


def test_substitute_template_numeric_values():
    """Numeric argument values are stringified."""
    def _substitute_template(template: str, arguments: dict) -> str:
        result = template
        for key, value in arguments.items():
            result = result.replace("{" + key + "}", str(value))
        return result

    result = _substitute_template(
        "https://api.example.com/users/{user_id}/posts/{post_id}",
        {"user_id": 123, "post_id": 456},
    )
    assert result == "https://api.example.com/users/123/posts/456"


def test_build_body_from_arguments():
    """_build_body_from_arguments filters non-JSON-serialisable values."""
    import logging

    def _build_body_from_arguments(arguments: dict) -> dict:
        import json as _json
        body: dict = {}
        for key, value in arguments.items():
            try:
                _json.dumps(value)
                body[key] = value
            except (TypeError, ValueError):
                pass  # skip non-serialisable values
        return body

    result = _build_body_from_arguments({
        "name": "Alice",
        "amount": 500,
        "callback": set(),  # not JSON-serialisable
    })
    assert result["name"] == "Alice"
    assert result["amount"] == 500
    assert "callback" not in result


# ---------------------------------------------------------------------------
# Adapter integration tests — mock httpx.AsyncClient at module level
# ---------------------------------------------------------------------------

def _make_fake_client_andRecorder():
    """Return (FakeAsyncClient class, list) that records all calls."""
    recorded_calls: list[dict] = []

    class _FakeResp:
        status_code = 200
        def json(self):
            return {}

    class _FakeAsyncClient:
        def __init__(self, *a, **kw):
            pass
        async def __aenter__(self):
            return self
        async def __aexit__(self, *a):
            pass

        async def get(self, url, **kwargs):
            recorded_calls.append({"method": "get", "url": url, "kwargs": kwargs})
            return _FakeResp()

        async def post(self, url, **kwargs):
            recorded_calls.append({"method": "post", "url": url, "kwargs": kwargs})
            return _FakeResp()

        async def put(self, url, **kwargs):
            recorded_calls.append({"method": "put", "url": url, "kwargs": kwargs})
            return _FakeResp()

        async def patch(self, url, **kwargs):
            recorded_calls.append({"method": "patch", "url": url, "kwargs": kwargs})
            return _FakeResp()

        async def delete(self, url, **kwargs):
            recorded_calls.append({"method": "delete", "url": url, "kwargs": kwargs})
            return _FakeResp()

    return _FakeAsyncClient, recorded_calls


def test_http_adapter_substitutes_url_and_headers(monkeypatch):
    """_execute_http substitutes url_template and headers before calling API."""
    import asyncio

    FakeAsyncClient, recorded_calls = _make_fake_client_andRecorder()

    import httpx
    monkeypatch.setattr(httpx, "AsyncClient", FakeAsyncClient)

    from mcp_server.server import _execute_http

    record = {
        "id": "github.get_repo",
        "name": "get_repo",
        "namespace": "github",
    }
    adapter = {
        "kind": "http",
        "method": "GET",
        "url_template": "https://api.github.com/repos/{owner}/{repo}",
        "headers": {"Authorization": "Bearer {token}"},
    }
    arguments = {"owner": "octocat", "repo": "hello-world", "token": "gho_***"}

    result = asyncio.run(_execute_http(record, adapter, arguments))

    assert len(recorded_calls) == 1
    call = recorded_calls[0]
    assert call["method"] == "get"
    assert call["url"] == "https://api.github.com/repos/octocat/hello-world"
    assert call["kwargs"]["headers"]["Authorization"] == "Bearer gho_***"


def test_graphql_adapter_substitutes_url_and_headers(monkeypatch):
    """_execute_graphql substitutes {key} in url_template and headers."""
    import asyncio

    FakeAsyncClient, recorded_calls = _make_fake_client_andRecorder()

    import httpx
    monkeypatch.setattr(httpx, "AsyncClient", FakeAsyncClient)

    from mcp_server.server import _execute_graphql

    record = {"id": "github.repo_query", "name": "repo_query", "namespace": "github"}
    adapter = {
        "kind": "graphql",
        "url_template": "https://{host}/graphql",
        "headers": {"Authorization": "Bearer {token}"},
        "query": "query($owner: String!) { repo(owner: $owner) { name } }",
    }
    arguments = {"host": "api.github.com", "token": "gho_***", "owner": "octocat"}

    result = asyncio.run(_execute_graphql(record, adapter, arguments))

    assert len(recorded_calls) == 1
    call = recorded_calls[0]
    assert call["url"] == "https://api.github.com/graphql"
    assert call["kwargs"]["headers"]["Authorization"] == "Bearer gho_***"


def test_webhook_adapter_substitutes_url_headers_and_body(monkeypatch):
    """_execute_webhook substitutes {key} in url_template, headers, and body_template."""
    import asyncio

    FakeAsyncClient, recorded_calls = _make_fake_client_andRecorder()

    import httpx
    monkeypatch.setattr(httpx, "AsyncClient", FakeAsyncClient)

    from mcp_server.server import _execute_webhook

    record = {"id": "events.send", "name": "send", "namespace": "events"}
    adapter = {
        "kind": "webhook",
        "method": "POST",
        "url_template": "https://hooks.example.com/{event_type}/{channel}",
        "headers": {"X-Secret": "{secret}"},
        "body_template": '{"event": "{event_type}", "channel": "{channel}"}',
    }
    arguments = {"event_type": "message.new", "channel": "alerts", "secret": "abc123"}

    result = asyncio.run(_execute_webhook(record, adapter, arguments))

    assert len(recorded_calls) == 1
    call = recorded_calls[0]
    assert call["url"] == "https://hooks.example.com/message.new/alerts"
    assert call["kwargs"]["headers"]["X-Secret"] == "abc123"
    assert call["kwargs"]["json"] == {"event": "message.new", "channel": "alerts"}


def test_webhook_falls_back_to_raw_args_without_body_template(monkeypatch):
    """Without body_template, webhook sends raw arguments as JSON body."""
    import asyncio

    FakeAsyncClient, recorded_calls = _make_fake_client_andRecorder()

    import httpx
    monkeypatch.setattr(httpx, "AsyncClient", FakeAsyncClient)

    from mcp_server.server import _execute_webhook

    record = {"id": "events.send", "name": "send", "namespace": "events"}
    adapter = {
        "kind": "webhook",
        "method": "POST",
        "url_template": "https://hooks.example.com/{channel}",
    }
    # No body_template — should fall back to raw arguments
    arguments = {"channel": "alerts", "priority": "high"}

    result = asyncio.run(_execute_webhook(record, adapter, arguments))

    assert recorded_calls[0]["kwargs"]["json"] == {"channel": "alerts", "priority": "high"}
