"""
Verifier: validates candidate ToolbankRecords before admission to the registry.

Checks performed:
1. Schema validation – does input_schema parse as valid JSON Schema?
2. Example validation – do examples conform to the input_schema?
3. Safety check – confirm side_effect_level and permission_policy are coherent.
4. Drift detection – has the source document changed since last harvest?
5. Confidence gate – reject below threshold.
"""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

CONFIDENCE_REVIEW_THRESHOLD = 0.40  # records below this go straight to review queue
AUTO_APPROVE_THRESHOLD = 0.85  # records above this are auto-approved (read-only only)

# Simple JSON Schema meta-schema check fields
_VALID_SCHEMA_TYPES = {"object", "array", "string", "number", "integer", "boolean", "null"}


def _validate_json_schema(schema: dict[str, Any]) -> list[str]:
    """Lightweight JSON Schema sanity check (no external deps)."""
    issues = []
    if not isinstance(schema, dict):
        issues.append("input_schema must be a JSON object")
        return issues
    top_type = schema.get("type")
    if top_type and top_type not in _VALID_SCHEMA_TYPES:
        issues.append(f"input_schema.type '{top_type}' is not a valid JSON Schema type")
    props = schema.get("properties")
    if props is not None and not isinstance(props, dict):
        issues.append("input_schema.properties must be a JSON object")
    return issues


def _validate_examples(record: dict[str, Any]) -> list[str]:
    """Check that example arguments are dicts and contain keys declared in the schema."""
    issues = []
    examples = record.get("examples", [])
    schema_props = set(
        record.get("input_schema", {}).get("properties", {}).keys()
    )
    for i, ex in enumerate(examples):
        args = ex.get("arguments", {}) if isinstance(ex, dict) else {}
        if not isinstance(args, dict):
            issues.append(f"examples[{i}].arguments must be a JSON object")
            continue
        unknown = set(args.keys()) - schema_props
        if unknown and schema_props:
            issues.append(
                f"examples[{i}].arguments contains unknown keys: {unknown}"
            )
    return issues


def _safety_check(record: dict[str, Any]) -> list[str]:
    issues = []
    side_effect = record.get("side_effect_level", "read")
    policy = record.get("permission_policy", "auto")

    if side_effect == "destructive" and policy not in ("deny", "confirm"):
        issues.append(
            "Destructive tools must have permission_policy='deny' or 'confirm'"
        )
    if side_effect == "write" and policy == "auto":
        issues.append("Write tools should have permission_policy='confirm', not 'auto'")
    return issues


def _drift_hash(record: dict[str, Any]) -> str:
    canonical = json.dumps(
        {
            "description": record.get("description", ""),
            "input_schema": record.get("input_schema", {}),
        },
        sort_keys=True,
    )
    return "sha256:" + hashlib.sha256(canonical.encode()).hexdigest()


def verify(
    record: dict[str, Any],
    previous_hash: str | None = None,
) -> dict[str, Any]:
    """
    Run all verification checks on a candidate record.
    Returns a VerificationResult-like dict.
    """
    issues: list[str] = []

    # 1. Required fields
    for field in ("id", "name", "namespace", "description"):
        if not record.get(field):
            issues.append(f"Missing required field: {field}")

    # 2. JSON Schema validation
    schema_issues = _validate_json_schema(record.get("input_schema", {}))
    issues.extend(schema_issues)
    schema_valid = len(schema_issues) == 0

    # 3. Example validation
    example_issues = _validate_examples(record)
    issues.extend(example_issues)
    examples_valid = len(example_issues) == 0

    # 4. Safety
    safety_issues = _safety_check(record)
    issues.extend(safety_issues)

    # 5. Drift detection
    current_hash = _drift_hash(record)
    drift_detected = bool(previous_hash and previous_hash != current_hash)
    if drift_detected:
        issues.append(f"Source drift detected: hash changed from {previous_hash} to {current_hash}")

    # 6. Confidence gate
    confidence = float(record.get("confidence", 0.0))
    if confidence < CONFIDENCE_REVIEW_THRESHOLD:
        issues.append(
            f"Confidence {confidence:.2f} is below threshold {CONFIDENCE_REVIEW_THRESHOLD}"
        )

    passed = len(issues) == 0

    # Auto-approve read-only, high-confidence, schema-valid records
    if passed and confidence >= AUTO_APPROVE_THRESHOLD and record.get("side_effect_level") == "read":
        record["status"] = "approved"
    elif passed:
        record["status"] = "verified"

    return {
        "record_id": record.get("id", ""),
        "schema_valid": schema_valid,
        "examples_valid": examples_valid,
        "safety_checked": len(safety_issues) == 0,
        "drift_detected": drift_detected,
        "issues": issues,
        "passed": passed,
        "current_hash": current_hash,
    }
