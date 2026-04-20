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

    When duplicates are found:
    - Keep the record with the highest confidence as the primary.
    - Merge ``source_urls`` from all duplicates (union, order-preserving).
    - Merge ``evidence`` lists from all duplicates (union).
    - Recompute ``confidence`` as the weighted average of the group.
    """
    # Phase 1: group records by their DNA key
    groups: dict[str, list[dict[str, Any]]] = {}

    for rec in records:
        dna = _build_dna(rec)
        key = _dna_key(dna)
        rec["dna"] = dna
        groups.setdefault(key, []).append(rec)

    # Phase 2: merge each group into a single canonical record
    result: list[dict[str, Any]] = []
    for group in groups.values():
        if len(group) == 1:
            result.append(group[0])
            continue

        # Primary = highest confidence
        primary = max(group, key=lambda r: r.get("confidence", 0))

        # Merge source_urls (union, order-preserving)
        merged_urls: list[str] = []
        seen_urls: set[str] = set()
        for r in group:
            for url in r.get("source_urls", []):
                if url not in seen_urls:
                    merged_urls.append(url)
                    seen_urls.add(url)

        # Merge evidence lists (union)
        merged_evidence: list[Any] = []
        seen_evidence: set[str] = set()
        for r in group:
            for ev in r.get("evidence", []):
                ev_key = json.dumps(ev, sort_keys=True) if isinstance(ev, dict) else str(ev)
                if ev_key not in seen_evidence:
                    merged_evidence.append(ev)
                    seen_evidence.add(ev_key)

        # Weighted-average confidence
        avg_confidence = sum(r.get("confidence", 0) for r in group) / len(group)

        primary = dict(primary)
        primary["source_urls"] = merged_urls
        primary["evidence"] = merged_evidence
        primary["confidence"] = avg_confidence
        result.append(primary)

    return result
