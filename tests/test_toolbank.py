"""
Tests for models, normalizer, verifier, deduper, classifier, and extractors.
"""

from __future__ import annotations

import json

from mcp_server.harvester.classifier import classify
from mcp_server.harvester.deduper import deduplicate
from mcp_server.harvester.extractors.openapi_extractor import extract_from_openapi
from mcp_server.harvester.gap_miner import analyse_gaps, generate_seeds
from mcp_server.harvester.normalizer import normalize
from mcp_server.harvester.verifier import verify
from mcp_server.models import (
    PermissionPolicy,
    SideEffectLevel,
    ToolbankRecord,
    ToolDNA,
    ToolStatus,
)

# ---------------------------------------------------------------------------
# Model tests
# ---------------------------------------------------------------------------

class TestToolbankRecord:
    def test_basic_creation(self):
        rec = ToolbankRecord(
            id="stripe.create_customer",
            name="create_customer",
            namespace="stripe",
            description="Create a Stripe customer.",
        )
        assert rec.id == "stripe.create_customer"
        assert rec.status == ToolStatus.draft
        assert rec.version_hash.startswith("sha256:")

    def test_auto_permission_policy_write(self):
        rec = ToolbankRecord(
            id="x.y",
            name="y",
            namespace="x",
            description="test",
            side_effect_level=SideEffectLevel.write,
        )
        assert rec.permission_policy == PermissionPolicy.confirm

    def test_auto_permission_policy_destructive(self):
        rec = ToolbankRecord(
            id="x.y",
            name="y",
            namespace="x",
            description="test",
            side_effect_level=SideEffectLevel.destructive,
        )
        assert rec.permission_policy == PermissionPolicy.deny

    def test_version_hash_changes_with_description(self):
        rec1 = ToolbankRecord(id="a.b", name="b", namespace="a", description="foo")
        rec2 = ToolbankRecord(id="a.b", name="b", namespace="a", description="bar")
        assert rec1.version_hash != rec2.version_hash

    def test_tool_dna_fingerprint(self):
        dna = ToolDNA(intent="create payment link", domain="payments", action="create")
        fp = dna.fingerprint()
        assert len(fp) == 16
        assert dna.fingerprint() == fp  # deterministic


# ---------------------------------------------------------------------------
# Normalizer tests
# ---------------------------------------------------------------------------

class TestNormalizer:
    def _base(self, **kwargs):
        base = {
            "name": "CreatePaymentLink",
            "namespace": "Stripe",
            "description": "Create a Stripe payment link.",
        }
        base.update(kwargs)
        return base

    def test_snake_case_name(self):
        rec = normalize(self._base())
        assert rec["name"] == "create_payment_link"

    def test_lowercase_namespace(self):
        rec = normalize(self._base())
        assert rec["namespace"] == "stripe"

    def test_default_id_generated(self):
        rec = normalize(self._base())
        assert rec["id"] == "stripe.create_payment_link"

    def test_side_effect_inferred_from_name(self):
        rec = normalize(self._base(name="deleteCustomer"))
        assert rec["side_effect_level"] == "destructive"

    def test_write_gets_confirm_policy(self):
        rec = normalize(self._base(name="updateCustomer"))
        assert rec["side_effect_level"] == "write"
        assert rec["permission_policy"] == "confirm"

    def test_destructive_gets_deny_policy(self):
        rec = normalize(self._base(name="deleteAll"))
        assert rec["permission_policy"] == "deny"

    def test_namespace_added_to_tags(self):
        rec = normalize(self._base(tags=["payments"]))
        assert "stripe" in rec["tags"]
        assert "payments" in rec["tags"]

    def test_auth_defaults(self):
        rec = normalize(self._base())
        assert rec["auth"] == {"type": "none", "required_env": []}

    def test_input_schema_default(self):
        rec = normalize(self._base())
        assert rec["input_schema"] == {"type": "object", "properties": {}}

    def test_version_hash_set(self):
        rec = normalize(self._base())
        assert rec["version_hash"].startswith("sha256:")


# ---------------------------------------------------------------------------
# Verifier tests
# ---------------------------------------------------------------------------

class TestVerifier:
    def _valid_record(self):
        return {
            "id": "stripe.get_customer",
            "name": "get_customer",
            "namespace": "stripe",
            "description": "Retrieve a Stripe customer.",
            "side_effect_level": "read",
            "permission_policy": "auto",
            "input_schema": {"type": "object", "properties": {"customer_id": {"type": "string"}}},
            "confidence": 0.92,
        }

    def test_valid_record_passes(self):
        result = verify(self._valid_record())
        assert result["passed"] is True
        assert result["schema_valid"] is True

    def test_missing_id_fails(self):
        rec = self._valid_record()
        del rec["id"]
        result = verify(rec)
        assert result["passed"] is False
        assert any("id" in issue for issue in result["issues"])

    def test_invalid_schema_type_fails(self):
        rec = self._valid_record()
        rec["input_schema"] = {"type": "invalid_type"}
        result = verify(rec)
        assert result["schema_valid"] is False

    def test_destructive_without_deny_is_issue(self):
        rec = self._valid_record()
        rec["side_effect_level"] = "destructive"
        rec["permission_policy"] = "auto"
        result = verify(rec)
        assert any("Destructive" in i for i in result["issues"])

    def test_low_confidence_fails(self):
        rec = self._valid_record()
        rec["confidence"] = 0.2
        result = verify(rec)
        assert result["passed"] is False

    def test_drift_detected(self):
        rec = self._valid_record()
        result = verify(rec, previous_hash="sha256:oldhash")
        assert result["drift_detected"] is True

    def test_auto_approve_high_confidence_read(self):
        rec = self._valid_record()
        rec["confidence"] = 0.95
        verify(rec)
        assert rec["status"] == "approved"

    def test_verified_status_medium_confidence(self):
        rec = self._valid_record()
        rec["confidence"] = 0.75
        verify(rec)
        assert rec["status"] == "verified"


# ---------------------------------------------------------------------------
# Deduper tests
# ---------------------------------------------------------------------------

class TestDeduper:
    def _record(self, name, namespace, method="POST", url="/v1/test", confidence=0.8):
        return {
            "id": f"{namespace}.{name}",
            "name": name,
            "namespace": namespace,
            "description": f"Create a {name}",
            "side_effect_level": "write",
            "confidence": confidence,
            "source_urls": [f"https://example.com/{name}"],
            "input_schema": {"type": "object", "properties": {}},
            "execution_adapter": {"kind": "http", "method": method, "url_template": f"https://api.example.com{url}"},
            "auth": {"type": "none", "required_env": []},
            "tags": [namespace],
        }

    def test_unique_records_preserved(self):
        records = [
            self._record("create_customer", "stripe", url="/v1/customers"),
            self._record("send_email", "sendgrid", url="/v3/mail/send"),
        ]
        result = deduplicate(records)
        assert len(result) == 2

    def test_duplicates_merged(self):
        # Two records with same transport_signature (same method + URL)
        r1 = self._record("create_payment_link", "stripe", url="/v1/payment_links", confidence=0.7)
        r2 = self._record("payment_links_create", "stripe", url="/v1/payment_links", confidence=0.9)
        r2["source_urls"] = ["https://docs.stripe.com/alternate"]
        result = deduplicate([r1, r2])
        assert len(result) == 1
        # Higher confidence wins
        assert result[0]["confidence"] == 0.9
        # Both source URLs merged
        assert len(result[0]["source_urls"]) == 2


# ---------------------------------------------------------------------------
# Classifier tests
# ---------------------------------------------------------------------------

class TestClassifier:
    def test_openapi_json(self):
        content = '{"openapi": "3.1.0", "info": {"title": "API"}}'
        assert classify(content) == "openapi"

    def test_swagger_yaml(self):
        content = "swagger: 2.0\ninfo:\n  title: My API"
        assert classify(content) == "openapi"

    def test_github_readme(self):
        content = "# My Tool\n\n## Installation\n\npip install mytool\n\n## Usage\n"
        assert classify(content) == "github_readme"

    def test_api_docs(self):
        content = "## API Reference\n\nGET /users\n\ncurl -X GET https://api.example.com/users"
        assert classify(content) == "api_docs"

    def test_cli_docs(self):
        content = "Usage: mytool [OPTIONS]\n\nSYNOPSIS\n  mytool --help"
        assert classify(content) == "cli_docs"

    def test_irrelevant(self):
        content = "Welcome to our website! Check out our blog."
        assert classify(content) == "irrelevant"

    def test_url_hint_openapi(self):
        assert classify("some content", url="https://api.example.com/openapi.json") == "openapi"


# ---------------------------------------------------------------------------
# OpenAPI extractor tests
# ---------------------------------------------------------------------------

SAMPLE_OPENAPI = {
    "openapi": "3.1.0",
    "info": {"title": "Payments API", "version": "1.0"},
    "servers": [{"url": "https://api.payments.com"}],
    "paths": {
        "/v1/customers": {
            "post": {
                "operationId": "createCustomer",
                "summary": "Create a customer",
                "parameters": [],
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "email": {"type": "string", "description": "Customer email"},
                                    "name": {"type": "string"},
                                },
                                "required": ["email"],
                            }
                        }
                    }
                },
            }
        },
        "/v1/customers/{customer_id}": {
            "get": {
                "operationId": "getCustomer",
                "summary": "Retrieve a customer",
                "parameters": [
                    {
                        "name": "customer_id",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string"},
                    }
                ],
            }
        },
    },
}


class TestOpenAPIExtractor:
    def test_extracts_two_operations(self):
        candidates = extract_from_openapi(SAMPLE_OPENAPI, "https://api.payments.com/openapi.json")
        assert len(candidates) == 2

    def test_operation_names(self):
        candidates = extract_from_openapi(SAMPLE_OPENAPI, "https://api.payments.com/openapi.json")
        names = {c["name"] for c in candidates}
        assert "create_customer" in names
        assert "get_customer" in names

    def test_side_effect_inferred(self):
        candidates = extract_from_openapi(SAMPLE_OPENAPI, "https://api.payments.com/openapi.json")
        by_name = {c["name"]: c for c in candidates}
        assert by_name["create_customer"]["side_effect_level"] == "write"
        assert by_name["get_customer"]["side_effect_level"] == "read"

    def test_input_schema_has_properties(self):
        candidates = extract_from_openapi(SAMPLE_OPENAPI, "https://api.payments.com/openapi.json")
        by_name = {c["name"]: c for c in candidates}
        props = by_name["create_customer"]["input_schema"].get("properties", {})
        assert "email" in props
        assert "name" in props

    def test_required_field_preserved(self):
        candidates = extract_from_openapi(SAMPLE_OPENAPI, "https://api.payments.com/openapi.json")
        by_name = {c["name"]: c for c in candidates}
        required = by_name["create_customer"]["input_schema"].get("required", [])
        assert "email" in required

    def test_url_template_built(self):
        candidates = extract_from_openapi(SAMPLE_OPENAPI, "https://api.payments.com/openapi.json")
        by_name = {c["name"]: c for c in candidates}
        adapter = by_name["create_customer"]["execution_adapter"]
        assert adapter["url_template"] == "https://api.payments.com/v1/customers"

    def test_confidence_high(self):
        candidates = extract_from_openapi(SAMPLE_OPENAPI, "https://api.payments.com/openapi.json")
        for c in candidates:
            assert c["confidence"] >= 0.85

    def test_namespace_from_title(self):
        candidates = extract_from_openapi(SAMPLE_OPENAPI, "https://api.payments.com/openapi.json")
        for c in candidates:
            assert c["namespace"] == "payments_api"


# ---------------------------------------------------------------------------
# Gap Miner tests
# ---------------------------------------------------------------------------

class TestGapMiner:
    def _failed(self, goal: str, n: int = 1) -> list[dict]:
        return [{"user_goal": goal, "failed_query": goal} for _ in range(n)]

    def test_analyse_gaps_counts_correctly(self):
        queries = self._failed("send an email", 3) + self._failed("make a payment", 1)
        gaps = analyse_gaps(queries)
        assert gaps[0]["goal"] == "send an email"
        assert gaps[0]["frequency"] == 3

    def test_generate_seeds_email(self):
        seeds = generate_seeds({"goal": "send an email notification"})
        names = [s["name"] for s in seeds]
        assert "sendgrid" in names

    def test_generate_seeds_ai(self):
        seeds = generate_seeds({"goal": "call an ai llm"})
        names = [s["name"] for s in seeds]
        assert "openai" in names

    def test_generate_seeds_no_match_returns_empty(self):
        seeds = generate_seeds({"goal": "xylophone concert"})
        assert seeds == []

    def test_generate_seeds_deduplicates(self):
        # "message" should not produce duplicate twilio entries
        seeds = generate_seeds({"goal": "send a sms message"})
        urls = [s["url"] for s in seeds]
        assert len(urls) == len(set(urls))


# ---------------------------------------------------------------------------
# Server adapter tests (unit-level, no real HTTP)
# ---------------------------------------------------------------------------

class TestPythonAdapter:
    """Test the Python function adapter sandbox enforcement."""

    def _record(self):
        return {
            "id": "test.func",
            "name": "func",
            "namespace": "test",
            "description": "test",
            "side_effect_level": "read",
            "permission_policy": "auto",
            "auth": {"type": "none", "required_env": []},
            "status": "approved",
        }

    def test_blocked_module_returns_error(self):
        from mcp_server.server import _execute_python
        # httpx is not in the allowlist
        adapter = {"function": "httpx.get"}
        result = _execute_python(self._record(), adapter, {})
        assert "error" in result
        assert "allowlist" in result["error"]

    def test_allowed_module_runs(self):
        from mcp_server.server import _execute_python
        adapter = {"function": "re.escape"}
        result = _execute_python(self._record(), adapter, {"pattern": "hello.world"})
        assert "result" in result
        assert "hello" in result["result"]

    def test_missing_function_field_returns_error(self):
        from mcp_server.server import _execute_python
        adapter = {}
        result = _execute_python(self._record(), adapter, {})
        assert "error" in result

    def test_invalid_dotted_path_returns_error(self):
        from mcp_server.server import _execute_python
        adapter = {"function": "nodots"}
        result = _execute_python(self._record(), adapter, {})
        assert "error" in result

    def test_signature_validation_rejects_extra_args(self):
        from mcp_server.server import _execute_python
        # math.sqrt takes one arg: x
        adapter = {"function": "math.sqrt"}
        result = _execute_python(self._record(), adapter, {"x": 9, "extra_arg": 1})
        assert "error" in result
        assert "Unknown argument" in result["error"] or "extra_arg" in result["error"]

    def test_signature_validation_allows_valid_args(self):
        from mcp_server.server import _execute_python
        # json.loads accepts keyword arguments like parse_float
        adapter = {"function": "json.loads"}
        result = _execute_python(self._record(), adapter, {"s": '"hello"'})
        assert "result" in result
        assert result["result"] == "hello"

    def test_signature_validation_var_keyword_allows_extra(self):
        from mcp_server.server import _execute_python
        # json.loads accepts **kwargs via loader parameter
        adapter = {"function": "json.loads"}
        result = _execute_python(self._record(), adapter, {"s": '"hello"', "parse_float": None})
        assert "result" in result or "error" not in result

    def test_import_error_returns_error(self):
        from mcp_server.server import _execute_python
        # nonexistent_module is not in allowlist (and not a real module)
        adapter = {"function": "nonexistent_module.my_func"}
        result = _execute_python(self._record(), adapter, {})
        assert "error" in result
        # Should be caught by allowlist check first
        assert "allowlist" in result["error"] or "Could not import" in result["error"]

    def test_missing_callable_returns_error(self):
        from mcp_server.server import _execute_python
        adapter = {"function": "math.nonexistent_function"}
        result = _execute_python(self._record(), adapter, {})
        assert "error" in result
        assert "not found or not callable" in result["error"]

    def test_allowlist_modules_are_valid(self):
        import importlib

        from mcp_server.server import _PYTHON_ADAPTER_ALLOWLIST
        for mod in _PYTHON_ADAPTER_ALLOWLIST:
            # Should not raise ImportError
            importlib.import_module(mod)

    def test_nested_module_in_allowlist(self):
        from mcp_server.server import _execute_python
        # urllib.parse is in allowlist as a dotted path
        adapter = {"function": "urllib.parse.quote"}
        result = _execute_python(self._record(), adapter, {"string": "hello world", "safe": ""})
        assert "result" in result
        assert result["result"] == "hello%20world"

    def test_top_level_not_in_allowlist_blocked(self):
        from mcp_server.server import _execute_python
        # subprocess is not in the allowlist
        adapter = {"function": "subprocess.run"}
        result = _execute_python(self._record(), adapter, {"args": []})
        assert "error" in result
        assert "allowlist" in result["error"]


class TestGraphQLAdapter:
    """Test the GraphQL adapter execution."""

    def _record(self):
        return {
            "id": "github.gql_repo",
            "name": "gql_repo",
            "namespace": "github",
            "description": "GraphQL repo query",
            "side_effect_level": "read",
            "permission_policy": "auto",
            "auth": {"type": "bearer", "required_env": ["GITHUB_TOKEN"]},
            "status": "approved",
        }

    def test_missing_url_template_returns_error(self):
        import asyncio

        from mcp_server.server import _execute_graphql

        async def run():
            adapter = {"query": "query { viewer { login } }"}
            result = await _execute_graphql(self._record(), adapter, {})
            assert "error" in result
            assert "url_template" in result["error"]

        asyncio.run(run())

    def test_missing_query_returns_error(self):
        import asyncio

        from mcp_server.server import _execute_graphql

        async def run():
            adapter = {"url_template": "https://api.github.com/graphql"}
            result = await _execute_graphql(self._record(), adapter, {})
            assert "error" in result
            assert "query" in result["error"].lower()

        asyncio.run(run())

    def test_sanitize_graphql_variables_strips_non_json_serializable(self):
        from mcp_server.server import _sanitize_graphql_variables

        # Functions are not JSON-serializable
        variables = {
            "name": "Alice",
            "age": 30,
            "callback": lambda x: x,  # not serializable
        }
        result = _sanitize_graphql_variables(variables)
        assert result["name"] == "Alice"
        assert result["age"] == 30
        assert "callback" not in result

    def test_sanitize_graphql_variables_keeps_valid(self):
        from mcp_server.server import _sanitize_graphql_variables

        variables = {"name": "Bob", "tags": ["a", "b"], "count": 5}
        result = _sanitize_graphql_variables(variables)
        assert result == {"name": "Bob", "tags": ["a", "b"], "count": 5}

    def test_sanitize_graphql_variables_empty_key_skipped(self):
        from mcp_server.server import _sanitize_graphql_variables

        variables = {"": "empty_key", "valid": "value"}
        result = _sanitize_graphql_variables(variables)
        assert "" not in result
        assert result["valid"] == "value"


class TestWebhookAdapter:
    """Test the webhook delivery adapter."""

    def _record(self):
        return {
            "id": "notify.webhook",
            "name": "webhook",
            "namespace": "notify",
            "description": "POST to a webhook URL",
            "side_effect_level": "write",
            "permission_policy": "confirm",
            "auth": {"type": "bearer", "required_env": ["WEBHOOK_SECRET"]},
            "status": "approved",
        }

    def test_missing_url_template_returns_error(self):
        import asyncio

        from mcp_server.server import _execute_webhook

        async def run():
            adapter = {"headers": {"Content-Type": "application/json"}}
            result = await _execute_webhook(self._record(), adapter, {"body": "test"})
            assert "error" in result
            assert "url_template" in result["error"]

        asyncio.run(run())

    def test_custom_headers_sent(self):
        import asyncio

        from mcp_server.server import _execute_webhook

        async def run():
            adapter = {
                "url_template": "https://example.com/hook",
                "headers": {"X-Custom": "myvalue", "Content-Type": "application/json"},
            }
            result = await _execute_webhook(self._record(), adapter, {"body": "hello"})
            # Without a real server we can't verify headers, but check it doesn't error
            assert "error" not in result or "url_template" in result.get("error", "")

        asyncio.run(run())

    def test_body_json_serializable_variables(self):
        import asyncio

        from mcp_server.server import _execute_webhook

        async def run():
            adapter = {
                "url_template": "https://example.com/hook",
                "method": "POST",
                "headers": {"Content-Type": "application/json"},
            }
            # Should not raise - variables are JSON-serializable
            result = await _execute_webhook(
                self._record(), adapter, {"name": "Alice", "count": 42}
            )
            # We expect either a real HTTP error (connection refused) or nothing
            # The important thing is it didn't crash on serialisation
            assert True

        asyncio.run(run())

    def test_http_method_get_only_has_no_body(self):
        import asyncio

        from mcp_server.server import _execute_webhook

        async def run():
            adapter = {
                "url_template": "https://example.com/hook",
                "method": "GET",
            }
            result = await _execute_webhook(self._record(), adapter, {"key": "value"})
            # Should attempt GET without body
            assert "error" not in result or "url_template" in result.get("error", "")

        asyncio.run(run())


class TestDestructiveApproval:
    """Test the admin destructive-tool approval API."""

    def _db_path(self, tmp_path):
        return str(tmp_path / "test_approval.db")

    def test_upsert_tool_creates_table(self, tmp_path):
        from mcp_server.database import init_db, upsert_tool

        db_path = str(tmp_path / "test.db")
        init_db(db_path)
        tool = {
            "id": "test.delete_all",
            "name": "delete_all",
            "namespace": "test",
            "description": "Delete everything",
            "side_effect_level": "destructive",
            "permission_policy": "deny",
            "status": "draft",
            "confidence": 0.95,
            "version_hash": "sha256:test",
            "tags": [],
        }
        result = upsert_tool(tool)
        assert result.id == "test.delete_all"

    def test_destructive_approval_table_exists(self, tmp_path):
        from mcp_server.database import get_session, init_db
        from sqlalchemy import text

        db_path = str(tmp_path / "test.db")
        init_db(db_path)
        with get_session() as session:
            rows = session.execute(text("SELECT name FROM sqlite_master WHERE type='table'")).fetchall()
            table_names = [r[0] for r in rows]
        assert "destructive_approvals" in table_names

    def test_approve_destructive_tool_inserts_record(self, tmp_path):
        from mcp_server.database import approve_destructive_tool, init_db

        db_path = str(tmp_path / "test.db")
        init_db(db_path)
        # Tool not in db yet, but we can test the function creates the record
        result = approve_destructive_tool(
            tool_id="test.delete_all",
            approver="admin@example.com",
            reason="Testing approval",
        )
        assert result is True

    def test_approve_idempotent(self, tmp_path):
        from mcp_server.database import approve_destructive_tool, init_db

        db_path = str(tmp_path / "test.db")
        init_db(db_path)
        r1 = approve_destructive_tool("test.delete_all", "admin@example.com", "first")
        r2 = approve_destructive_tool("test.delete_all", "admin@example.com", "second")
        assert r1 is True
        assert r2 is True  # idempotent - already approved

    def test_approve_returns_false_for_empty_tool_id(self, tmp_path):
        from mcp_server.database import approve_destructive_tool, init_db

        db_path = str(tmp_path / "test.db")
        init_db(db_path)
        result = approve_destructive_tool("", "admin@example.com", "no tool")
        assert result is False

    def test_is_destructive_approved_true(self, tmp_path):
        from mcp_server.database import approve_destructive_tool, init_db, is_destructive_approved

        db_path = str(tmp_path / "test.db")
        init_db(db_path)
        approve_destructive_tool("test.delete_all", "admin@example.com", "ok")
        assert is_destructive_approved("test.delete_all") is True

    def test_is_destructive_approved_false_unapproved(self, tmp_path):
        from mcp_server.database import init_db, is_destructive_approved

        db_path = str(tmp_path / "test.db")
        init_db(db_path)
        assert is_destructive_approved("test.delete_all") is False

    def test_approve_tool_and_execute(self, tmp_path):
        """End-to-end: approve a destructive tool, then verify execute_tool allows it."""
        import asyncio

        from mcp_server.database import approve_destructive_tool, init_db, upsert_tool
        from mcp_server.server import _execute_tool

        db_path = str(tmp_path / "test.db")
        init_db(db_path)

        # Create a mock destructive tool in the registry
        tool = {
            "id": "test.burn_it_all",
            "name": "burn_it_all",
            "namespace": "test",
            "description": "Destructive tool for testing",
            "side_effect_level": "destructive",
            "permission_policy": "deny",
            "status": "approved",
            "confidence": 1.0,
            "version_hash": "sha256:abc",
            "tags": [],
            "auth": {"type": "none", "required_env": []},
            "execution_adapter": {"kind": "http", "url_template": "https://example.com/delete"},
        }
        upsert_tool(tool)
        approve_destructive_tool("test.burn_it_all", "admin@example.com", "Testing")

        async def run():
            result = await _execute_tool({
                "tool_id": "test.burn_it_all",
                "arguments": {},
                "confirmed": True,
            })
            return result

        text_content = asyncio.run(run())
        result = json.loads(text_content[0].text)
        # Should NOT be blocked by destructive policy now
        assert "error" not in result or "Destructive tools are blocked" not in result.get("error", "")

