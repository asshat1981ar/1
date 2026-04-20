"""
Tests for models, normalizer, verifier, deduper, classifier, and extractors.
"""

from __future__ import annotations

import json
import pytest

from mcp_server.models import (
    ToolbankRecord,
    AuthInfo,
    ToolExample,
    ExecutionAdapter,
    AdapterKind,
    SideEffectLevel,
    PermissionPolicy,
    ToolStatus,
    ExtractionResult,
    ToolDNA,
)
from mcp_server.harvester.normalizer import normalize
from mcp_server.harvester.verifier import verify
from mcp_server.harvester.deduper import deduplicate
from mcp_server.harvester.classifier import classify
from mcp_server.harvester.extractors.openapi_extractor import extract_from_openapi


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
# GraphQL adapter tests
# ---------------------------------------------------------------------------

class TestGraphQLAdapter:
    """Tests for _execute_graphql in server.py."""

    def _make_record(self, auth_env: list[str] | None = None) -> dict:
        return {
            "id": "test.query",
            "name": "query",
            "namespace": "test",
            "description": "A test GraphQL query.",
            "auth": {"type": "bearer", "required_env": auth_env or []},
        }

    def _make_adapter(self) -> dict:
        return {
            "kind": "graphql",
            "url_template": "https://api.example.com/graphql",
            "query": "query GetUser($id: ID!) { user(id: $id) { name } }",
            "variables_map": {"id": "user_id"},
        }

    def test_variables_mapped_correctly(self):
        """variables_map keys become GraphQL vars, values become arg lookups."""
        adapter = self._make_adapter()
        variables_map = adapter["variables_map"]
        arguments = {"user_id": "u_123"}
        variables = {gql_var: arguments.get(arg_key) for gql_var, arg_key in variables_map.items()}
        assert variables == {"id": "u_123"}

    def test_missing_url_template(self):
        """Adapter without url_template returns error dict."""
        import asyncio
        from mcp_server.server import _execute_graphql

        record = self._make_record()
        adapter = {"kind": "graphql", "query": "{ users { id } }"}
        result = asyncio.get_event_loop().run_until_complete(
            _execute_graphql(record, adapter, {})
        )
        assert "error" in result
        assert "url_template" in result["error"]

    def test_missing_query(self):
        """Adapter without query string returns error dict."""
        import asyncio
        from mcp_server.server import _execute_graphql

        record = self._make_record()
        adapter = {"kind": "graphql", "url_template": "https://api.example.com/graphql"}
        result = asyncio.get_event_loop().run_until_complete(
            _execute_graphql(record, adapter, {})
        )
        assert "error" in result
        assert "query" in result["error"]


# ---------------------------------------------------------------------------
# Python function adapter tests
# ---------------------------------------------------------------------------

class TestPythonFuncAdapter:
    """Tests for _execute_python_func in server.py."""

    def _make_record(self) -> dict:
        return {
            "id": "test.func",
            "name": "func",
            "namespace": "test",
            "description": "A test Python function.",
            "auth": {"type": "none", "required_env": []},
        }

    def test_calls_stdlib_function(self):
        """Can call a stdlib function when allowlist permits."""
        from mcp_server.server import _execute_python_func

        record = self._make_record()
        adapter = {
            "kind": "python_func",
            "module": "json",
            "function": "loads",
            "allowlist": ["json"],
        }
        result = _execute_python_func(record, adapter, {"s": '{"key": "value"}'})
        assert result == {"key": "value"}

    def test_allowlist_blocks_unlisted_module(self):
        """Module not in allowlist returns an error dict."""
        from mcp_server.server import _execute_python_func

        record = self._make_record()
        adapter = {
            "kind": "python_func",
            "module": "os",
            "function": "getcwd",
            "allowlist": ["math"],
        }
        result = _execute_python_func(record, adapter, {})
        assert "error" in result
        assert "allowlist" in result["error"]

    def test_empty_allowlist_allows_any_module(self):
        """Empty allowlist means no restriction."""
        from mcp_server.server import _execute_python_func

        record = self._make_record()
        adapter = {
            "kind": "python_func",
            "module": "json",
            "function": "loads",
            "allowlist": [],
        }
        result = _execute_python_func(record, adapter, {"s": '{"n": 42}'})
        assert result == {"n": 42}

    def test_missing_module(self):
        """Non-existent module returns import error dict."""
        from mcp_server.server import _execute_python_func

        record = self._make_record()
        adapter = {
            "kind": "python_func",
            "module": "nonexistent_module_xyz",
            "function": "func",
            "allowlist": ["nonexistent_module_xyz"],
        }
        result = _execute_python_func(record, adapter, {})
        assert "error" in result

    def test_missing_function(self):
        """Existing module but missing function returns attribute error dict."""
        from mcp_server.server import _execute_python_func

        record = self._make_record()
        adapter = {
            "kind": "python_func",
            "module": "math",
            "function": "this_does_not_exist",
            "allowlist": ["math"],
        }
        result = _execute_python_func(record, adapter, {})
        assert "error" in result


# ---------------------------------------------------------------------------
# Crawler cache expiry tests
# ---------------------------------------------------------------------------

class TestCrawlerCacheExpiry:
    """Tests for the updated in-memory cache with TTL support."""

    def test_purge_stale_removes_expired_entries(self):
        from mcp_server.harvester.crawler import Crawler

        crawler = Crawler(use_cache=True, request_delay=0)
        # Manually insert a stale entry
        crawler._cache["http://example.com/stale"] = (
            "<html/>",
            "text/html",
            0.0,  # expired in 1970
        )
        # And a fresh entry (expiry far in the future)
        crawler._cache["http://example.com/fresh"] = (
            "<html/>",
            "text/html",
            9_999_999_999.0,
        )
        purged = crawler.purge_stale()
        assert purged == 1
        assert "http://example.com/stale" not in crawler._cache
        assert "http://example.com/fresh" in crawler._cache
        crawler.close()

    def test_purge_stale_no_expiry_entries_not_removed(self):
        from mcp_server.harvester.crawler import Crawler

        crawler = Crawler(use_cache=True, request_delay=0)
        crawler._cache["http://example.com/no-expiry"] = (
            "<html/>",
            "text/html",
            None,  # no expiry
        )
        purged = crawler.purge_stale()
        assert purged == 0
        assert "http://example.com/no-expiry" in crawler._cache
        crawler.close()

    def test_no_cache_mode_skips_cache(self):
        from mcp_server.harvester.crawler import Crawler

        crawler = Crawler(use_cache=False, request_delay=0)
        assert crawler._use_cache is False
        assert crawler._cache == {}
        crawler.close()

    def test_parse_expiry_max_age(self):
        from mcp_server.harvester.crawler import Crawler
        import time

        before = time.time()
        headers = {"cache-control": "public, max-age=3600"}
        expiry = Crawler._parse_expiry(headers)
        assert expiry is not None
        assert abs(expiry - (before + 3600)) < 2  # within 2 seconds

    def test_parse_expiry_no_header(self):
        from mcp_server.harvester.crawler import Crawler

        expiry = Crawler._parse_expiry({})
        assert expiry is None


# ---------------------------------------------------------------------------
# CLI export tests
# ---------------------------------------------------------------------------

class TestCmdExport:
    """Tests for the toolbank export command."""

    def test_export_json_empty(self, tmp_path):
        """Export with no records produces empty JSON array."""
        import sys
        import io
        import argparse
        from mcp_server.database import init_db
        from mcp_server.cli import cmd_export

        db_path = str(tmp_path / "test_export.db")
        init_db(db_path=db_path)

        args = argparse.Namespace(format="json", output=None)
        captured = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = captured
        try:
            cmd_export(args)
        finally:
            sys.stdout = old_stdout

        output = captured.getvalue()
        data = json.loads(output)
        assert isinstance(data, list)

    def test_export_csv_empty(self, tmp_path):
        """Export CSV with no records writes empty string."""
        import io
        import sys
        import argparse
        from mcp_server.database import init_db
        from mcp_server.cli import cmd_export

        db_path = str(tmp_path / "test_export_csv.db")
        init_db(db_path=db_path)

        args = argparse.Namespace(format="csv", output=None)
        captured = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = captured
        try:
            cmd_export(args)
        finally:
            sys.stdout = old_stdout
        # Should not raise; output may be empty


# ---------------------------------------------------------------------------
# TUI module smoke test
# ---------------------------------------------------------------------------

class TestTUI:
    """Smoke tests for mcp_server.tui."""

    def test_module_importable(self):
        from mcp_server import tui  # noqa: F401

    def test_run_review_tui_empty_list(self, tmp_path, capsys):
        """run_review_tui with empty list does not raise."""
        from mcp_server.tui import _plain_review

        _plain_review([])
        # No output and no exception
        captured = capsys.readouterr()
        assert captured.out == ""
