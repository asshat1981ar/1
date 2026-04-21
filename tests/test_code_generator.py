"""Tests for code example generation from JSON schemas."""

from __future__ import annotations


def test_python_example_basic():
    from mcp_server.code_generator import _python_example

    schema = {
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "Customer name"},
            "amount": {"type": "integer", "description": "Amount in cents"},
        },
        "required": ["name", "amount"],
    }
    result = _python_example("stripe.create_charge", schema)
    assert "stripe.create_charge" in result
    assert '"name":' in result
    assert '"amount":' in result


def test_python_example_with_optional():
    from mcp_server.code_generator import _python_example

    schema = {
        "type": "object",
        "properties": {
            "email": {"type": "string", "description": "Email address"},
            "metadata": {"type": "object", "description": "Arbitrary metadata"},
        },
    }
    result = _python_example("auth0.create_user", schema)
    assert "email" in result
    assert "# optional" in result.lower() or "# metadata" in result


def test_js_example():
    from mcp_server.code_generator import _js_example

    schema = {
        "type": "object",
        "properties": {
            "to": {"type": "string", "description": "Recipient phone"},
            "body": {"type": "string", "description": "Message text"},
        },
        "required": ["to", "body"],
    }
    result = _js_example("twilio.send_sms", schema)
    assert "fetch" in result.lower() or "twilio" in result.lower()


def test_curl_example_post():
    from mcp_server.code_generator import _curl_example

    schema = {
        "type": "object",
        "properties": {
            "to": {"type": "string"},
            "body": {"type": "string"},
        },
        "required": ["to", "body"],
    }
    result = _curl_example("POST", "https://api.sendgrid.com/v3/mail/send", schema)
    assert "curl" in result
    assert "-X POST" in result


def test_curl_example_get():
    from mcp_server.code_generator import _curl_example

    schema = {"type": "object", "properties": {"repo": {"type": "string"}}}
    result = _curl_example("GET", "https://api.github.com/repos/{owner}/{repo}", schema)
    assert "curl" in result
    assert "-X GET" in result


def test_go_example():
    from mcp_server.code_generator import _go_example

    schema = {
        "type": "object",
        "properties": {
            "file_path": {"type": "string", "description": "Path to file"},
            "content": {"type": "string", "description": "File content"},
        },
        "required": ["file_path", "content"],
    }
    result = _go_example("filesystem.write_file", schema)
    assert "http.NewRequest" in result or "http.Post" in result or "os.WriteFile" in result


def test_generate_examples_returns_all_languages():
    from mcp_server.code_generator import generate_examples

    schema = {
        "type": "object",
        "properties": {"id": {"type": "string"}},
    }
    examples = generate_examples("github.get_repo", schema)
    assert set(examples.keys()) == {"python", "javascript", "curl", "go"}
    assert all(examples.values())


def test_generate_examples_with_empty_schema():
    from mcp_server.code_generator import generate_examples

    examples = generate_examples("admin.health_check", {})
    assert set(examples.keys()) == {"python", "javascript", "curl", "go"}
    assert all(examples.values())
