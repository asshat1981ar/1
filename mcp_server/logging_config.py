"""
Structured JSON logging configuration for mcp_server.

All log output is JSON with the format:
{"timestamp": "ISO8601", "level": "INFO", "logger": "mcp_server.module", "message": "..."}

The log level is controlled by the LOG_LEVEL environment variable (defaults to INFO).
"""

from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime, timezone
from typing import Any


# --------------------------------------------------------------------------
# JSON log format helpers
# --------------------------------------------------------------------------


class JsonFormatter(logging.Formatter):
    """Formatter that outputs structured JSON log records."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

    def format(self, record: logging.LogRecord) -> str:
        log_obj: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        # Include exc_info if present
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_obj)


# --------------------------------------------------------------------------
# Public API
# --------------------------------------------------------------------------


def setup_logging() -> logging.Logger:
    """
    Configure the mcp_server logger hierarchy with structured JSON output.

    LOG_LEVEL env var controls the minimum log level.
    Valid values: DEBUG, INFO, WARNING, ERROR, CRITICAL (case-insensitive).
    Defaults to INFO.

    Returns the "mcp_server" root logger.
    """
    level_name = os.environ.get("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)

    # Remove any pre-existing handlers from the mcp_server hierarchy
    # to avoid duplicate or conflicting log configuration.
    root = logging.getLogger("mcp_server")
    for h in root.handlers[:]:
        root.removeHandler(h)

    # Configure the mcp_server root logger
    root.setLevel(level)
    root.propagate = True

    # JSON stdout handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)
    handler.setFormatter(JsonFormatter())
    root.addHandler(handler)

    return root
