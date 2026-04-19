"""
Page classifier: determines what kind of content a fetched page contains.
"""

from __future__ import annotations

import re

# Ordered patterns – first match wins
_PATTERNS: list[tuple[str, list[str]]] = [
    (
        "openapi",
        [
            r'"openapi"\s*:\s*"3\.',
            r'"swagger"\s*:\s*"2\.',
            r"openapi:\s*3\.",
            r"swagger:\s*2\.",
        ],
    ),
    (
        "mcp_server",
        [
            r'"mcp"\s*:',
            r"mcp\.json",
            r"FastMCP",
            r"ModelContextProtocol",
            r"mcp_server",
        ],
    ),
    (
        "github_readme",
        [
            r"github\.com/",
            r"## Installation",
            r"## Usage",
            r"pip install",
            r"npm install",
            r"cargo add",
        ],
    ),
    (
        "api_docs",
        [
            r"## Endpoints",
            r"## API Reference",
            r"Request Parameters",
            r"Response Body",
            r"curl -X",
            r"Authorization: Bearer",
        ],
    ),
    (
        "cli_docs",
        [
            r"Usage:\s+\w+",
            r"SYNOPSIS",
            r"--help",
            r"\$ \w+ \w+",
        ],
    ),
    (
        "llms_txt",
        [
            r"^#\s+\w",  # llms.txt starts with a heading
            r"llms\.txt",
        ],
    ),
]


def classify(content: str, url: str = "") -> str:
    """
    Returns one of: openapi | mcp_server | github_readme | api_docs |
                    cli_docs | llms_txt | irrelevant
    """
    for label, patterns in _PATTERNS:
        for pattern in patterns:
            if re.search(pattern, content, re.IGNORECASE | re.MULTILINE):
                return label
    # Fallback heuristics on URL
    url_lower = url.lower()
    if any(k in url_lower for k in ("openapi", "swagger", "api-docs")):
        return "openapi"
    if "readme" in url_lower:
        return "github_readme"
    if any(k in url_lower for k in ("docs", "reference", "api")):
        return "api_docs"
    return "irrelevant"
