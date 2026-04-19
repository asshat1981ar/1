"""
Deduplication and capability merging.
Uses Tool DNA fingerprinting to collapse tools with different names
but equivalent capabilities into a single canonical record.
"""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any


def _build_dna(record: dict[str, Any]) -> dict[str, Any]:
    """Extract the DNA fingerprint fields from a record."""
    name = record.get("name", "")
    desc = record.get("description", "")
    adapter = record.get("execution_adapter") or {}

    # Action words
    action_words = ["create", "get", "list", "update", "delete", "send", "run", "deploy"]
    action = next((w for w in action_words if w in name.lower()), "")

    # Object: words after the action in the name
    parts = re.split(r"[_\s]", name.lower())
    try:
        action_idx = parts.index(action) if action else -1
        obj = "_".join(parts[action_idx + 1 :]) if action_idx >= 0 else "_".join(parts)
    except ValueError:
        obj = name

    input_sig = sorted(
        record.get("input_schema", {}).get("properties", {}).keys()
    )
    auth = record.get("auth", {})
    env_vars = sorted(auth.get("required_env", []))
    auth_sig = env_vars[0].lower() if env_vars else "none"

    method = ""
    url_template = ""
    if isinstance(adapter, dict):
        method = adapter.get("method", "")
        url_template = adapter.get("url_template", "")
    transport_sig = f"{method} {url_template}".strip()

    return {
        "intent": desc[:80].lower() if desc else name,
        "domain": record.get("namespace", ""),
        "action": action,
        "object": obj[:40],
        "input_signature": input_sig,
        "auth_signature": auth_sig,
        "side_effect": record.get("side_effect_level", "read"),
        "transport_signature": transport_sig,
    }


def _dna_key(dna: dict[str, Any]) -> str:
    """Stable hash for dedup comparison.

    When the transport_signature contains a concrete URL path+method we use
    that as the primary key (two tools pointing at the same endpoint *are*
    the same capability regardless of how they're named).  Otherwise we fall
    back to the domain+action+object triple.
    """
    transport_sig = dna.get("transport_signature", "")
    # Use transport as primary key if it contains both a method and a path
    if transport_sig and " " in transport_sig and "/" in transport_sig:
        canonical = json.dumps(
            {
                "domain": dna["domain"],
                "transport_signature": transport_sig,
            },
            sort_keys=True,
        )
    else:
        canonical = json.dumps(
            {
                "domain": dna["domain"],
                "action": dna["action"],
                "object": dna["object"],
                "transport_signature": transport_sig,
            },
            sort_keys=True,
        )
    return hashlib.sha256(canonical.encode()).hexdigest()[:12]


def deduplicate(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Given a list of candidate records, return a deduplicated list.
    When duplicates are found, the highest-confidence record wins
    and its source_urls are merged.
    """
    clusters: dict[str, dict[str, Any]] = {}

    for rec in records:
        dna = _build_dna(rec)
        key = _dna_key(dna)
        rec["dna"] = dna

        if key not in clusters:
            clusters[key] = rec
        else:
            existing = clusters[key]
            # Merge source_urls
            merged_urls = list(
                dict.fromkeys(
                    existing.get("source_urls", []) + rec.get("source_urls", [])
                )
            )
            # Keep highest confidence
            if rec.get("confidence", 0) > existing.get("confidence", 0):
                rec["source_urls"] = merged_urls
                clusters[key] = rec
            else:
                existing["source_urls"] = merged_urls

    return list(clusters.values())
