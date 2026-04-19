"""
LLM-based docs extractor.
Uses structured output to extract ToolbankRecord candidates from unstructured
API documentation pages. Falls back gracefully if no LLM is configured.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

_EXTRACTION_PROMPT = """You are a tool metadata extractor. Given the following API documentation page, extract up to 5 tool/endpoint definitions.

For each tool, output a JSON object matching this schema:
{{
  "id": "<namespace>.<name>",
  "name": "<snake_case_name>",
  "namespace": "<service_name>",
  "description": "<one_sentence_description>",
  "source_urls": ["{source_url}"],
  "source_type": "docs",
  "transport": "rest|graphql|cli|python|node|webhook|local",
  "auth": {{"type": "api_key|oauth|none|env_var", "required_env": []}},
  "input_schema": {{"type": "object", "properties": {{}}}},
  "output_schema": {{}},
  "examples": [],
  "side_effect_level": "read|write|destructive",
  "permission_policy": "auto",
  "rate_limit_notes": "",
  "pricing_notes": "",
  "install_notes": "",
  "execution_adapter": null,
  "tags": [],
  "confidence": 0.0,
  "status": "draft"
}}

Also output:
- "evidence": list of {{"field": ..., "source_url": ..., "quote": ...}}
- "missing_fields": list of field names you could not fill
- "confidence": float 0-1 (your confidence that the extracted data is accurate)

Documentation page (URL: {source_url}):
---
{content}
---

Respond ONLY with valid JSON in this format:
{{
  "tools": [<tool objects>],
  "evidence": [<evidence objects>],
  "missing_fields": [],
  "confidence": 0.0
}}"""


def _call_openai(prompt: str) -> str | None:
    """Call OpenAI chat completions API."""
    try:
        import openai  # type: ignore

        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            return None
        client = openai.OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0,
        )
        return response.choices[0].message.content
    except Exception as exc:
        logger.warning("OpenAI call failed: %s", exc)
        return None


def extract_from_docs(
    content: str,
    source_url: str,
    max_content_chars: int = 8000,
) -> list[dict[str, Any]]:
    """
    Extract tool candidates from unstructured documentation.
    Returns list of ExtractionResult-like dicts.
    """
    # Truncate to avoid token limits
    truncated = content[:max_content_chars]
    prompt = _EXTRACTION_PROMPT.format(
        source_url=source_url,
        content=truncated,
    )

    raw = _call_openai(prompt)
    if not raw:
        logger.debug("LLM extractor skipped (no API key or call failed) for %s", source_url)
        return []

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.warning("LLM returned invalid JSON for %s: %s", source_url, exc)
        return []

    tools = parsed.get("tools", [])
    evidence = parsed.get("evidence", [])
    missing_fields = parsed.get("missing_fields", [])
    confidence = float(parsed.get("confidence", 0.0))

    results = []
    for tool in tools:
        tool["confidence"] = confidence
        results.append(
            {
                "record": tool,
                "evidence": evidence,
                "missing_fields": missing_fields,
                "confidence": confidence,
                "source_url": source_url,
                "extractor": "llm_docs",
            }
        )

    logger.info(
        "LLM extractor produced %d candidates from %s (confidence=%.2f)",
        len(results),
        source_url,
        confidence,
    )
    return results
