"""Generate runnable code examples from tool JSON schemas."""

from __future__ import annotations

from typing import Any


def generate_examples(tool_name: str, schema: dict[str, Any]) -> dict[str, str]:
    """Generate code examples in all supported languages."""
    base_url = "https://api.example.com/v1"
    method = "POST"
    url = f"{base_url}/{tool_name.replace('.', '/')}"

    return {
        "python": _python_example(tool_name, schema),
        "javascript": _js_example(tool_name, schema),
        "curl": _curl_example(method, url, schema),
        "go": _go_example(tool_name, schema),
    }


def _python_example(tool_name: str, schema: dict[str, Any]) -> str:
    """Generate a Python example."""
    lines = ["```python", f"# {tool_name}", "import json"]

    lines.append("")
    lines.append("# Tool arguments")
    props = schema.get("properties", {})
    required = schema.get("required", [])

    if not props:
        lines.append("args = {}")
    else:
        lines.append("args = {")
        for name, spec in props.items():
            py_type = _json_type_to_python(spec.get("type", "string"))
            desc = spec.get("description", "")
            required_marker = "" if name in required else "  # optional"
            if desc:
                lines.append(f'    "{name}": {py_type},  # {desc}{required_marker}')
            else:
                lines.append(f'    "{name}": {py_type},{required_marker}')
        lines.append("}")

    lines.append("")
    lines.append("# Call via MCP server")
    lines.append(f'result = mcp.call_tool("{tool_name}", args)')
    lines.append("```")
    return "\n".join(lines)


def _js_example(tool_name: str, schema: dict[str, Any]) -> str:
    """Generate a JavaScript/TypeScript example."""
    lines = ["```javascript", f"// {tool_name}", "const response = await fetch("]
    lines.append(f'  "https://api.example.com/v1/{tool_name.replace(".", "/")}",')
    lines.append("  {")
    lines.append('    method: "POST",')
    lines.append('    headers: { "Content-Type": "application/json" },')
    lines.append("    body: JSON.stringify({")
    props = schema.get("properties", {})
    if props:
        for i, (name, spec) in enumerate(props.items()):
            js_type = _json_type_to_typescript(spec.get("type", "string"))
            desc = spec.get("description", "")
            comma = "," if i < len(props) - 1 else ""
            if desc:
                lines.append(f'      {name}: {js_type}, // {desc}{comma}')
            else:
                lines.append(f'      {name}: {js_type}{comma}')
    else:
        lines.append("      // no required fields")
    lines.append("    })")
    lines.append("  })")
    lines.append(");")
    lines.append("const result = await response.json();")
    lines.append("```")
    return "\n".join(lines)


def _curl_example(method: str, url: str, schema: dict[str, Any]) -> str:
    """Generate a curl example."""
    lines = ["```bash", f'curl -X {method} "{url}" \\']
    lines.append('  -H "Content-Type: application/json" \\')
    lines.append('  -d \'{')

    props = schema.get("properties", {})
    if props:
        pairs = []
        for name, spec in props.items():
            js_type = spec.get("type", "string")
            val = _example_value(js_type)
            pairs.append(f'    "{name}": {val}')
        lines.append("    \"args\": {")
        lines.append(",\n".join(f'      {p}' for p in pairs))
        lines.append("    }")
    else:
        lines.append("    \"args\": {}")
    lines.append("  }'")
    lines.append("```")
    return "\n".join(lines)


def _go_example(tool_name: str, schema: dict[str, Any]) -> str:
    """Generate a Go example."""
    lines = ["```go", f'// {tool_name}', "package main", ""]
    lines.append('import (')
    lines.append('\t"bytes"')
    lines.append('\t"encoding/json"')
    lines.append('\t"net/http"')
    lines.append(")")
    lines.append("")
    lines.append("func main() {")

    props = schema.get("properties", {})
    if props:
        lines.append("\targs := map[string]interface{}{")
        for name, spec in props.items():
            go_type = _json_type_to_go(spec.get("type", "string"))
            lines.append(f'\t\t"{name}": {go_type}, // {spec.get("description", "")}')
        lines.append("\t}")

    lines.append("")
    lines.append('\tbody, _ := json.Marshal(args)')
    lines.append('\treq, _ := http.NewRequest("POST",')
    lines.append(f'\t\t"https://api.example.com/v1/{tool_name.replace(".", "/")}",')
    lines.append("\t\tbytes.NewBuffer(body))")
    lines.append('\treq.Header.Set("Content-Type", "application/json")')
    lines.append("")
    lines.append('\tclient := &http.Client{}')
    lines.append('\tresp, err := client.Do(req)')
    lines.append("\tif err != nil {")
    lines.append("\t\tpanic(err)")
    lines.append("\t}")
    lines.append("\tdefer resp.Body.Close()")
    lines.append("}")
    lines.append("```")
    return "\n".join(lines)


def _json_type_to_python(json_type: str) -> str:
    """Map JSON types to Python types."""
    return {
        "string": '"string"',
        "integer": "123",
        "number": "1.5",
        "boolean": "true",
        "array": "[]",
        "object": "{}",
    }.get(json_type, "None")


def _json_type_to_typescript(json_type: str) -> str:
    """Map JSON types to TypeScript types."""
    return {
        "string": '"string"',
        "integer": "number",
        "number": "number",
        "boolean": "boolean",
        "array": "any[]",
        "object": "Record<string, any>",
    }.get(json_type, "any")


def _json_type_to_go(json_type: str) -> str:
    """Map JSON types to Go zero values."""
    mapping = {
        "string": '"string"',
        "integer": "0",
        "number": "0.0",
        "boolean": "false",
        "array": "[]interface{}{}",
        "object": "map[string]interface{}{}",
    }
    return mapping.get(json_type, "nil")


def _example_value(json_type: str) -> str:
    """Get an example value for a JSON type."""
    return {
        "string": '"example"',
        "integer": "123",
        "number": "1.5",
        "boolean": "true",
        "array": "[]",
        "object": "{}",
    }.get(json_type, "null")
