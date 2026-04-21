"""
GitHub repository extractor.
Inspects README, package.json, pyproject.toml, openapi files, etc.
"""

from __future__ import annotations

import logging
import re
from typing import Any
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

_GITHUB_API = "https://api.github.com"

# Patterns for env var extraction
_ENV_PATTERN = re.compile(r"\b([A-Z][A-Z0-9_]{3,})\b")
_CLI_COMMAND_PATTERN = re.compile(r"^\$\s+(\w[\w\-]+)", re.MULTILINE)
_INSTALL_PATTERN = re.compile(
    r"(pip install|npm install|cargo add|go install|brew install)\s+([\w\-@/]+)",
    re.IGNORECASE,
)


def _repo_from_url(url: str) -> tuple[str, str] | None:
    """Extract (owner, repo) from a GitHub URL."""
    m = re.match(r"https?://github\.com/([^/]+)/([^/\s#?]+)", url)
    if m:
        return m.group(1), m.group(2).rstrip(".git")
    return None


def _infer_transport(readme: str, pkg_name: str) -> str:
    if re.search(r"\bpip install\b|\bpyproject\b|\.py\b", readme, re.IGNORECASE):
        return "python"
    if re.search(r"\bnpm install\b|\bpackage\.json\b|\.js\b|\.ts\b", readme, re.IGNORECASE):
        return "node"
    if _CLI_COMMAND_PATTERN.search(readme):
        return "cli"
    return "local"


def _extract_env_vars(text: str) -> list[str]:
    candidates = _ENV_PATTERN.findall(text)
    # Filter for likely env var patterns (long, all-caps, contains underscore)
    return list(
        dict.fromkeys(
            v for v in candidates if len(v) >= 5 and "_" in v
        )
    )


def extract_from_github_readme(
    readme_content: str,
    source_url: str,
    repo_info: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """
    Extract tool candidates from a GitHub README.
    Returns a list of candidate dicts (usually 1 per repo – the repo itself as a tool).
    """
    repo_info = repo_info or {}
    parsed = urlparse(source_url)

    # Derive namespace + name from URL or repo metadata
    parts = parsed.path.strip("/").split("/")
    if len(parts) >= 2:
        owner, repo_name = parts[0], parts[1]
    else:
        owner, repo_name = "unknown", "unknown"

    namespace = owner.lower().replace("-", "_")
    name = repo_name.lower().replace("-", "_")
    description = repo_info.get("description") or _extract_first_description(readme_content)
    transport = _infer_transport(readme_content, name)

    # Env vars
    env_vars = _extract_env_vars(readme_content)
    auth_type = "env_var" if env_vars else "none"

    # Install notes
    install_matches = _INSTALL_PATTERN.findall(readme_content)
    install_notes = "; ".join(f"{m[0]} {m[1]}" for m in install_matches[:3])

    # CLI commands as sub-tools
    candidates = []
    cli_commands = _CLI_COMMAND_PATTERN.findall(readme_content)
    unique_commands = list(dict.fromkeys(cli_commands))

    if transport == "cli" and unique_commands:
        for cmd in unique_commands[:10]:
            cmd_name = re.sub(r"[^a-z0-9_]", "_", cmd.lower()).strip("_")
            candidates.append(
                {
                    "id": f"{namespace}.{cmd_name}",
                    "name": cmd_name,
                    "namespace": namespace,
                    "description": f"Run `{cmd}` CLI command from {repo_name}",
                    "source_urls": [source_url],
                    "source_type": "github",
                    "transport": "cli",
                    "auth": {"type": auth_type, "required_env": env_vars},
                    "input_schema": {"type": "object", "properties": {}},
                    "output_schema": {},
                    "examples": [],
                    "side_effect_level": "write",
                    "permission_policy": "confirm",
                    "rate_limit_notes": "",
                    "pricing_notes": "",
                    "install_notes": install_notes,
                    "execution_adapter": {
                        "kind": "subprocess",
                        "command": cmd,
                        "args_template": [],
                        "sandbox": True,
                    },
                    "tags": [namespace, "cli"],
                    "confidence": 0.55,
                    "status": "draft",
                }
            )
    else:
        # One record representing the whole library/tool
        candidates.append(
            {
                "id": f"{namespace}.{name}",
                "name": name,
                "namespace": namespace,
                "description": description,
                "source_urls": [source_url],
                "source_type": "github",
                "transport": transport,
                "auth": {"type": auth_type, "required_env": env_vars},
                "input_schema": {"type": "object", "properties": {}},
                "output_schema": {},
                "examples": [],
                "side_effect_level": "read",
                "permission_policy": "auto",
                "rate_limit_notes": "",
                "pricing_notes": "",
                "install_notes": install_notes,
                "execution_adapter": None,
                "tags": [namespace, transport],
                "confidence": 0.50,
                "status": "draft",
            }
        )

    logger.info(
        "GitHub extractor produced %d candidates from %s", len(candidates), source_url
    )
    return candidates


def _extract_first_description(readme: str) -> str:
    """Extract the first meaningful sentence from a README."""
    # Skip heading lines and get first non-empty paragraph
    lines = readme.splitlines()
    for line in lines:
        line = line.strip()
        if line and not line.startswith("#") and not line.startswith("!"):
            # Take first 200 chars
            return line[:200]
    return ""
