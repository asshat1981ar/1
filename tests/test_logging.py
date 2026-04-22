"""
Tests for structured JSON logging in mcp_server.
"""

from __future__ import annotations

import json
import logging
import os
import sys
from io import StringIO
from unittest import mock

import pytest


class TestSetupLogging:
    """Tests for setup_logging() in logging_config.py."""

    def test_setup_logging_import(self):
        """Can import setup_logging from logging_config."""
        from mcp_server.logging_config import setup_logging
        assert callable(setup_logging)

    def test_setup_logging_returns_logger(self):
        """setup_logging returns a logger instance."""
        from mcp_server.logging_config import setup_logging
        logger = setup_logging()
        assert isinstance(logger, logging.Logger)

    def test_setup_logging_default_level_info(self):
        """Default LOG_LEVEL is INFO when env var not set."""
        from mcp_server.logging_config import setup_logging
        logger = setup_logging()
        assert logger.level == logging.INFO

    def test_setup_logging_env_level_debug(self):
        """LOG_LEVEL=DEBUG sets logger to DEBUG level."""
        with mock.patch.dict(os.environ, {"LOG_LEVEL": "DEBUG"}):
            from importlib import reload
            import mcp_server.logging_config as lc
            reload(lc)
            logger = lc.setup_logging()
            assert logger.level == logging.DEBUG

    def test_setup_logging_env_level_warning(self):
        """LOG_LEVEL=WARNING sets logger to WARNING level."""
        with mock.patch.dict(os.environ, {"LOG_LEVEL": "WARNING"}):
            from importlib import reload
            import mcp_server.logging_config as lc
            reload(lc)
            logger = lc.setup_logging()
            assert logger.level == logging.WARNING

    def test_setup_logging_env_level_error(self):
        """LOG_LEVEL=ERROR sets logger to ERROR level."""
        with mock.patch.dict(os.environ, {"LOG_LEVEL": "ERROR"}):
            from importlib import reload
            import mcp_server.logging_config as lc
            reload(lc)
            logger = lc.setup_logging()
            assert logger.level == logging.ERROR


class TestJsonLogFormat:
    """Tests for JSON log format compliance."""

    @pytest.fixture(autouse=True)
    def reset_mcp_server_loggers(self):
        """Reset mcp_server logger hierarchy before and after each test."""
        root = logging.getLogger("mcp_server")
        # Save existing handlers
        saved_handlers = root.handlers[:]
        saved_level = root.level
        yield
        # Restore
        root.handlers = saved_handlers
        root.setLevel(saved_level)

    def _make_json_logger(self):
        """Create a fresh mcp_server.test logger with JsonFormatter handler."""
        from mcp_server.logging_config import JsonFormatter
        logger = logging.getLogger("mcp_server.test")
        logger.setLevel(logging.DEBUG)
        logger.propagate = False
        # Capture to a StringIO
        stream = StringIO()
        handler = logging.StreamHandler(stream)
        handler.setLevel(logging.DEBUG)
        handler.setFormatter(JsonFormatter())
        logger.handlers = [handler]
        return logger, stream

    def test_json_log_contains_required_fields(self):
        """Each log line contains timestamp, level, logger, message."""
        logger, stream = self._make_json_logger()
        logger.info("test message")
        stream.seek(0)
        line = stream.read()
        record = json.loads(line)
        assert "timestamp" in record
        assert "level" in record
        assert "logger" in record
        assert "message" in record

    def test_json_log_timestamp_is_iso8601(self):
        """timestamp field is ISO8601 format."""
        logger, stream = self._make_json_logger()
        logger.info("test timestamp")
        stream.seek(0)
        line = stream.read()
        record = json.loads(line)
        from datetime import datetime
        dt = datetime.fromisoformat(record["timestamp"].replace("Z", "+00:00"))
        assert dt is not None

    def test_json_log_level_is_info_string(self):
        """level field is the string INFO."""
        logger, stream = self._make_json_logger()
        logger.info("test level")
        stream.seek(0)
        line = stream.read()
        record = json.loads(line)
        assert record["level"] == "INFO"

    def test_json_log_logger_includes_module(self):
        """logger field includes the module name."""
        logger, stream = self._make_json_logger()
        logger.info("test logger")
        stream.seek(0)
        line = stream.read()
        record = json.loads(line)
        assert "mcp_server" in record["logger"]

    def test_json_log_message_is_string(self):
        """message field matches the logged message."""
        logger, stream = self._make_json_logger()
        logger.info("hello world")
        stream.seek(0)
        line = stream.read()
        record = json.loads(line)
        assert record["message"] == "hello world"

    def test_json_log_debug_level(self):
        """DEBUG level logs produce level=DEBUG."""
        logger, stream = self._make_json_logger()
        logger.debug("debug test")
        stream.seek(0)
        line = stream.read()
        record = json.loads(line)
        assert record["level"] == "DEBUG"

    def test_json_log_warning_level(self):
        """WARNING level logs produce level=WARNING."""
        logger, stream = self._make_json_logger()
        logger.warning("warning test")
        stream.seek(0)
        line = stream.read()
        record = json.loads(line)
        assert record["level"] == "WARNING"

    def test_json_log_error_level(self):
        """ERROR level logs produce level=ERROR."""
        logger, stream = self._make_json_logger()
        logger.error("error test")
        stream.seek(0)
        line = stream.read()
        record = json.loads(line)
        assert record["level"] == "ERROR"


class TestRootLoggerSetup:
    """Tests that setup_logging configures all mcp_server loggers."""

    @pytest.fixture(autouse=True)
    def reset_mcp_server_loggers(self):
        root = logging.getLogger("mcp_server")
        saved_handlers = root.handlers[:]
        saved_level = root.level
        yield
        root.handlers = saved_handlers
        root.setLevel(saved_level)

    def test_mcp_server_logger_has_json_handler(self):
        """mcp_server logger gets a JSON handler attached."""
        from mcp_server.logging_config import setup_logging
        setup_logging()
        mcp_logger = logging.getLogger("mcp_server")
        assert len(mcp_logger.handlers) > 0

    def test_child_logger_level_inherited(self):
        """Child loggers inherit the mcp_server level via propagation."""
        from mcp_server.logging_config import setup_logging
        setup_logging()
        crawler_logger = logging.getLogger("mcp_server.crawler")
        # Child logger should effectively be at INFO level (via parent's level)
        assert crawler_logger.getEffectiveLevel() == logging.INFO
