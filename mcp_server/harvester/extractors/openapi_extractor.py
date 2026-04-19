"""
OpenAPI spec extractor.
Converts each OpenAPI operation into a candidate ToolbankRecord dict.
"""

from __future__ import annotations

import logging
import re
from typing import Any
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


def _infer_side_effect(method: str) -> str:
    method = method.upper()
    if method == "GET":
        return "read"
    if method in ("DELETE",):
        return "destructive"
    return "write"


def _infer_transport(spec: dict) -> str:
    servers = spec.get("servers", [])
    if servers:
        url = servers[0].get("url", "")
        if "graphql" in url.lower():
            return "graphql"
    return "rest"


def _build_input_schema(operation: dict, parameters: list[dict]) -> dict:
    """Build a JSON Schema object from OpenAPI operation parameters + requestBody."""
    properties: dict[str, Any] = {}
    required: list[str] = []

    for param in parameters:
        name = param.get("name", "")
        if not name:
            continue
        schema = param.get("schema", {"type": "string"})
        if param.get("required"):
            required.append(name)
        properties[name] = {
            **schema,
            "description": param.get("description", ""),
        }

    # requestBody
    req_body = operation.get("requestBody", {})
    content = req_body.get("content", {})
    for media_type in ("application/json", "application/x-www-form-urlencoded"):
        if media_type in content:
            body_schema = content[media_type].get("schema", {})
            body_props = body_schema.get("properties", {})
            body_req = body_schema.get("required", [])
            for prop_name, prop_schema in body_props.items():
                properties[prop_name] = prop_schema
            required.extend(body_req)
            break

    schema: dict[str, Any] = {"type": "object", "properties": properties}
    if required:
        schema["required"] = list(dict.fromkeys(required))
    return schema


def _namespace_from_url(source_url: str, spec: dict) -> str:
    info = spec.get("info", {})
    title = info.get("title", "")
    if title:
        return re.sub(r"\W+", "_", title.lower()).strip("_")
    parsed = urlparse(source_url)
    parts = [p for p in parsed.netloc.split(".") if p not in ("www", "com", "io", "dev")]
    return parts[0] if parts else "unknown"


def extract_from_openapi(spec: dict, source_url: str) -> list[dict[str, Any]]:
    """
    Parse an OpenAPI 2/3 spec dict and return a list of candidate record dicts.
    Each operation → one candidate.
    """
    candidates: list[dict[str, Any]] = []
    namespace = _namespace_from_url(source_url, spec)
    transport = _infer_transport(spec)

    # Auth hints
    auth_info: dict[str, Any] = {"type": "none", "required_env": []}
    security_schemes = (
        spec.get("components", {}).get("securitySchemes", {})
        or spec.get("securityDefinitions", {})
    )
    for scheme_name, scheme in security_schemes.items():
        scheme_type = scheme.get("type", "").lower()
        if scheme_type in ("apikey", "api_key"):
            auth_info = {
                "type": "api_key",
                "required_env": [f"{namespace.upper()}_API_KEY"],
            }
        elif scheme_type in ("oauth2", "oauth"):
            auth_info = {"type": "oauth", "required_env": []}

    paths = spec.get("paths", {})
    for path, path_item in paths.items():
        if not isinstance(path_item, dict):
            continue
        # Shared parameters at path level
        path_level_params = path_item.get("parameters", [])

        for method in ("get", "post", "put", "patch", "delete"):
            operation = path_item.get(method)
            if not isinstance(operation, dict):
                continue

            operation_id = operation.get("operationId", "")
            summary = operation.get("summary", "")
            description = operation.get("description", summary)

            # Merge path-level + operation-level parameters
            op_params = path_level_params + operation.get("parameters", [])

            # Build name from operationId or path+method
            if operation_id:
                raw_name = operation_id
            else:
                clean_path = re.sub(r"[/{}\-]", "_", path).strip("_")
                raw_name = f"{method}_{clean_path}"

            # camelCase / PascalCase → snake_case, then sanitise
            raw_snake = re.sub(r"([A-Z])", r"_\1", raw_name).lstrip("_")
            name = re.sub(r"[^a-z0-9_]", "_", raw_snake.lower())
            name = re.sub(r"_+", "_", name).strip("_")
            tags = operation.get("tags", [])

            # Build execution adapter
            servers = spec.get("servers", [])
            base_url = servers[0].get("url", "") if servers else ""
            url_template = base_url.rstrip("/") + path

            candidates.append(
                {
                    "id": f"{namespace}.{name}",
                    "name": name,
                    "namespace": namespace,
                    "description": description or f"{method.upper()} {path}",
                    "source_urls": [source_url],
                    "source_type": "openapi",
                    "transport": transport,
                    "auth": auth_info,
                    "input_schema": _build_input_schema(operation, op_params),
                    "output_schema": {},
                    "examples": [],
                    "side_effect_level": _infer_side_effect(method),
                    "permission_policy": "auto",
                    "rate_limit_notes": "",
                    "pricing_notes": "",
                    "install_notes": "",
                    "execution_adapter": {
                        "kind": "http",
                        "method": method.upper(),
                        "url_template": url_template,
                    },
                    "tags": [namespace] + tags,
                    "confidence": 0.90,
                    "status": "draft",
                }
            )

    logger.info(
        "OpenAPI extractor produced %d candidates from %s", len(candidates), source_url
    )
    return candidates
