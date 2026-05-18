"""Structured logging for SquadOS.

Provides correlation-aware logging that attaches mission_id, task_id,
and agent_id to every log entry for traceability across multi-agent
concurrent execution.

Usage:
    from squad_os.core.logging import get_logger

    # At mission start
    log = get_logger(mission_id=42)
    log.info("Mission started", goal="Research API")

    # Within task execution
    task_log = log.bind(task_id=7, agent_role="Researcher")
    task_log.info("Executing task", description="Research API docs")

    # Tool execution
    task_log.info("Tool called", tool="web_search", query="API trends")

Output (JSON structured):
    {"timestamp": "...", "level": "INFO", "mission_id": 42, "task_id": 7,
     "agent_role": "Researcher", "event": "Tool called", "tool": "web_search"}
"""

import json
import logging
import os
import sys
import time
import uuid
from typing import Any, Dict, Optional


# Configuration from environment
_LOG_FORMAT = os.environ.get("SQUAD_OS_LOG_FORMAT", "text")  # "text" or "json"
_LOG_LEVEL = os.environ.get("SQUAD_OS_LOG_LEVEL", "INFO").upper()
_LOG_FILE = os.environ.get("SQUAD_OS_LOG_FILE", "")  # empty = stdout only


class CorrelationFilter(logging.Filter):
    """Inject correlation IDs into every log record."""

    def __init__(
        self,
        mission_id: Optional[int] = None,
        task_id: Optional[int] = None,
        agent_role: Optional[str] = None,
        run_id: Optional[str] = None,
    ):
        super().__init__()
        self.mission_id = mission_id
        self.task_id = task_id
        self.agent_role = agent_role
        self.run_id = run_id or str(uuid.uuid4())[:8]

    def filter(self, record: logging.LogRecord) -> bool:
        record.mission_id = self.mission_id
        record.task_id = self.task_id
        record.agent_role = self.agent_role
        record.run_id = self.run_id
        return True


class JSONFormatter(logging.Formatter):
    """Format log records as JSON for machine-readable output."""

    def format(self, record: logging.LogRecord) -> str:
        log_data: Dict[str, Any] = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "run_id": getattr(record, "run_id", None),
        }

        # Add correlation IDs if present
        mission_id = getattr(record, "mission_id", None)
        if mission_id is not None:
            log_data["mission_id"] = mission_id
        task_id = getattr(record, "task_id", None)
        if task_id is not None:
            log_data["task_id"] = task_id
        agent_role = getattr(record, "agent_role", None)
        if agent_role is not None:
            log_data["agent_role"] = agent_role

        # Add extra fields from log call
        if hasattr(record, "extra_fields"):
            log_data.update(record.extra_fields)

        # Add exception info if present
        if record.exc_info and record.exc_info[0] is not None:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data, default=str)


class TextFormatter(logging.Formatter):
    """Human-readable format with correlation IDs."""

    def format(self, record: logging.LogRecord) -> str:
        parts = []

        # Correlation prefix
        run_id = getattr(record, "run_id", None)
        if run_id:
            parts.append(f"[{run_id}]")

        mission_id = getattr(record, "mission_id", None)
        if mission_id is not None:
            parts.append(f"M#{mission_id}")

        task_id = getattr(record, "task_id", None)
        if task_id is not None:
            parts.append(f"T#{task_id}")

        agent_role = getattr(record, "agent_role", None)
        if agent_role:
            parts.append(f"[{agent_role}]")

        prefix = " ".join(parts)
        if prefix:
            prefix += " "

        return f"{prefix}{record.levelname}: {record.getMessage()}"


def _make_handler(fmt: logging.Formatter) -> logging.Handler:
    """Create a log handler based on configuration."""
    if _LOG_FILE:
        handler = logging.FileHandler(_LOG_FILE, encoding="utf-8")
    else:
        handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(fmt)
    return handler


def setup_root_logger():
    """Configure the root SquadOS logger. Call once at startup."""
    if _LOG_FORMAT == "json":
        fmt = JSONFormatter()
    else:
        fmt = TextFormatter()

    root = logging.getLogger("squad_os")
    root.setLevel(getattr(logging, _LOG_LEVEL, logging.INFO))
    root.handlers.clear()
    root.addHandler(_make_handler(fmt))

    # Silence noisy third-party loggers
    for noisy in ["litellm", "aiosqlite", "httpx"]:
        logging.getLogger(noisy).setLevel(logging.WARNING)


class SquadLogger:
    """Correlation-aware logger wrapper for SquadOS components."""

    def __init__(
        self,
        name: str,
        mission_id: Optional[int] = None,
        task_id: Optional[int] = None,
        agent_role: Optional[str] = None,
        run_id: Optional[str] = None,
    ):
        self._logger = logging.getLogger(name)
        self._correlation = CorrelationFilter(
            mission_id=mission_id,
            task_id=task_id,
            agent_role=agent_role,
            run_id=run_id,
        )
        self._logger.addFilter(self._correlation)

    def bind(
        self,
        mission_id: Optional[int] = None,
        task_id: Optional[int] = None,
        agent_role: Optional[str] = None,
    ) -> "SquadLogger":
        """Return a new logger with additional correlation context."""
        new_logger = SquadLogger(
            name=self._logger.name,
            mission_id=mission_id or self._correlation.mission_id,
            task_id=task_id or self._correlation.task_id,
            agent_role=agent_role or self._correlation.agent_role,
            run_id=self._correlation.run_id,
        )
        return new_logger

    def _log(self, level: int, msg: str, **kwargs):
        if kwargs:
            # Store extra fields for JSON formatter
            record = self._logger.makeRecord(
                self._logger.name, level, "", 0, msg, (), None
            )
            record.extra_fields = kwargs
            self._logger.handle(record)
        else:
            self._logger.log(level, msg)

    def debug(self, msg: str, **kwargs):
        self._log(logging.DEBUG, msg, **kwargs)

    def info(self, msg: str, **kwargs):
        self._log(logging.INFO, msg, **kwargs)

    def warning(self, msg: str, **kwargs):
        self._log(logging.WARNING, msg, **kwargs)

    def error(self, msg: str, **kwargs):
        self._log(logging.ERROR, msg, **kwargs)

    def critical(self, msg: str, **kwargs):
        self._log(logging.CRITICAL, msg, **kwargs)

    def exception(self, msg: str, **kwargs):
        self._logger.exception(msg, extra={"extra_fields": kwargs} if kwargs else None)


def get_logger(
    name: str = "squad_os",
    mission_id: Optional[int] = None,
    task_id: Optional[int] = None,
    agent_role: Optional[str] = None,
    run_id: Optional[str] = None,
) -> SquadLogger:
    """Get a correlation-aware logger."""
    return SquadLogger(
        name=name,
        mission_id=mission_id,
        task_id=task_id,
        agent_role=agent_role,
        run_id=run_id,
    )


class Timer:
    """Context manager for timing operations with structured logging."""

    def __init__(self, logger: SquadLogger, operation: str):
        self.logger = logger
        self.operation = operation
        self.start_time: float = 0
        self.elapsed_ms: float = 0

    def __enter__(self):
        self.start_time = time.monotonic()
        self.logger.debug(f"{self.operation} started")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.elapsed_ms = (time.monotonic() - self.start_time) * 1000
        if exc_type:
            self.logger.error(
                f"{self.operation} failed",
                duration_ms=round(self.elapsed_ms, 1),
                error=str(exc_val),
            )
        else:
            self.logger.info(
                f"{self.operation} completed",
                duration_ms=round(self.elapsed_ms, 1),
            )
        return False
