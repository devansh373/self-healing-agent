"""
Structured logging configuration using structlog.

Sets up JSON-formatted logging to stdout. Called once at app startup.
All log entries are machine-readable JSON objects, not human-formatted text —
this is critical for searchability and observability in production.
"""

import logging
import sys

import structlog

from app.core.config import settings


def setup_logging() -> None:
    """
    Configure structlog for the entire application.

    This should be called exactly once, during app startup (in main.py's lifespan).
    After this call, every structlog.get_logger() in the codebase will produce
    JSON output to stdout.
    """

    # ── Shared processors ─────────────────────────────────────────────────
    # Processors are a pipeline: each one transforms the log event dict before
    # the final renderer outputs it. They run in order.
    shared_processors: list[structlog.types.Processor] = [
        # Adds the log level as a string (e.g. "info", "error")
        structlog.stdlib.add_log_level,
        # Adds an ISO-8601 timestamp (e.g. "2026-06-19T10:00:00Z")
        structlog.processors.TimeStamper(fmt="iso"),
        # Converts the stack info into a readable string (for exceptions)
        structlog.processors.StackInfoRenderer(),
        # Formats exception tracebacks
        structlog.processors.format_exc_info,
    ]

    structlog.configure(
        processors=[
            *shared_processors,
            # This must be the LAST processor — it turns the event dict into
            # a JSON string for output
            structlog.processors.JSONRenderer(),
        ],
        # Use a standard library logger as the underlying transport
        wrapper_class=structlog.stdlib.BoundLogger,
        # Factory: create a new PrintLogger for each structlog.get_logger() call
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        # Cache the logger configuration (performance optimization)
        cache_logger_on_first_use=True,
    )

    # ── Also configure the standard library root logger ────────────────────
    # Libraries like uvicorn, sqlalchemy, and alembic use stdlib logging, not
    # structlog. This ensures their output also goes to stdout at the correct level.
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    )
