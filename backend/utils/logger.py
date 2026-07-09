"""
Structured Logger
-----------------
Provides a factory function returning a configured Python logger.
All log output is human-readable in development and structured (JSON-ready)
for production log aggregators.

Usage:
    from backend.utils.logger import get_logger
    logger = get_logger(__name__)
    logger.info("DEM loaded", extra={"rows": 200, "cols": 200})
"""

import logging
import sys
from backend.config import settings


class _StructuredFormatter(logging.Formatter):
    """
    Formats log records with key context fields prepended to the message,
    suitable for both human reading and log aggregator parsing.
    Format: LEVEL | logger_name | message [key=value ...]
    """

    def format(self, record: logging.LogRecord) -> str:
        base = super().format(record)
        # Collect any extra fields attached via `extra={}` to the log call
        standard_keys = {
            "name", "msg", "args", "levelname", "levelno", "pathname",
            "filename", "module", "exc_info", "exc_text", "stack_info",
            "lineno", "funcName", "created", "msecs", "relativeCreated",
            "thread", "threadName", "processName", "process", "message",
            "taskName",
        }
        extras = {
            k: v for k, v in record.__dict__.items()
            if k not in standard_keys and not k.startswith("_")
        }
        if extras:
            kv = " ".join(f"{k}={v}" for k, v in extras.items())
            base = f"{base} [{kv}]"
        return base


_configured = False


def _configure_root_logger() -> None:
    """Configures the root logger once at import time."""
    global _configured
    if _configured:
        return
    _configured = True

    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        _StructuredFormatter(
            fmt="%(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S",
        )
    )
    root = logging.getLogger()
    root.setLevel(level)
    # Only add handler if not already present (avoid duplicates on reload)
    if not root.handlers:
        root.addHandler(handler)
    # Silence noisy third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """
    Returns a named logger. Call once per module:
        logger = get_logger(__name__)

    Args:
        name: Usually ``__name__`` of the calling module.

    Returns:
        A configured ``logging.Logger`` instance.
    """
    _configure_root_logger()
    return logging.getLogger(name)
