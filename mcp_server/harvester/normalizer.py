"""
Schema normalizer: cleans and standardises candidate records before verification.
"""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any

_SIDE_EFFECT_KEYWORDS = {
    "destructive": ["delete", "destroy", "remove", "purge", "wipe", "terminate"],
    "write": ["create", "update", "patch", "put", "post", "write", "send", "deploy", "publish"],
    "read": ["get", "list", "fetch", "read", "search", "query", "describe"],
}


def _infer_side_effect(name: str, description: str, method: str = "") -> str:
    text = f"{name} {description} {method}".lower()
    for level in ("destructive", "write", "read"):
        for kw in _SIDE_EFFECT_KEYWORDS[level]:
            if kw in text:
                return level
    return "read"


def _clean_name(name: str) -> str:
    """Convert to snake_case, remove non-alnum chars."""
    name = re.sub(r"([A-Z])", r"_\1", name)  # camelCase → snake_case
    name = re.sub(r"[^a-z0-9_]", "_", name.lower())
    name = re.sub(r"_+", "_", name).strip("_")
    return name


def _default_id(namespace: str, name: str) -> str:
    ns = re.sub(r"[^a-z0-9_]", "_", namespace.lower()).strip("_")
    n = _clean_name(name)
    return f"{ns}.{n}"


def _version_hash(record: dict[str, Any]) -> str:
    canonical = json.dumps(
        {
            "input_schema": record.get("input_schema", {}),
            "description": record.get("description", ""),
        },
        sort_keys=True,
    )
    return "sha256:" + hashlib.sha256(canonical.encode()).hexdigest()


def normalize(candidate: dict[str, Any]) -> dict[str, Any]:
    """
    Produce a clean, fully-populated candidate record from raw extractor output.
    Does NOT validate – call verifier after this.
    """
    rec = dict(candidate)

    # Normalise name
    rec["name"] = _clean_name(rec.get("name", "") or "")
    rec["namespace"] = re.sub(r"[^a-z0-9_]", "_", (rec.get("namespace", "") or "unknown").lower()).strip("_")
    if not rec.get("id"):
        rec["id"] = _default_id(rec["namespace"], rec["name"])

    # Description
    if not rec.get("description"):
        rec["description"] = f"{rec['name']} tool"

    # Enums: coerce to valid values
    valid_source_types = {"openapi", "docs", "github", "mcp_server", "sdk", "cli"}
    if rec.get("source_type") not in valid_source_types:
        rec["source_type"] = "docs"

    valid_transports = {"rest", "graphql", "cli", "python", "node", "webhook", "local"}
    if rec.get("transport") not in valid_transports:
        rec["transport"] = "rest"

    # Side effect inference
    adapter = rec.get("execution_adapter") or {}
    method = adapter.get("method", "") if isinstance(adapter, dict) else ""
    if rec.get("side_effect_level") not in ("read", "write", "destructive"):
        rec["side_effect_level"] = _infer_side_effect(
            rec.get("name", ""), rec.get("description", ""), method
        )

    # Permission policy based on side effect
    if rec.get("side_effect_level") == "write" and rec.get("permission_policy") in (None, "auto"):
        rec["permission_policy"] = "confirm"
    elif rec.get("side_effect_level") == "destructive":
        rec["permission_policy"] = "deny"
    elif not rec.get("permission_policy"):
        rec["permission_policy"] = "auto"

    # Auth defaults
    if not rec.get("auth"):
        rec["auth"] = {"type": "none", "required_env": []}

    # Schema defaults
    if not rec.get("input_schema"):
        rec["input_schema"] = {"type": "object", "properties": {}}
    if not rec.get("output_schema"):
        rec["output_schema"] = {}

    # Tags
    tags = list(rec.get("tags", []))
    if rec["namespace"] not in tags:
        tags.append(rec["namespace"])
    rec["tags"] = list(dict.fromkeys(t for t in tags if t))

    # Status default
    if not rec.get("status"):
        rec["status"] = "draft"

    # Version hash
    rec["version_hash"] = _version_hash(rec)

    # Confidence default
    if "confidence" not in rec:
        rec["confidence"] = 0.5

    return rec
