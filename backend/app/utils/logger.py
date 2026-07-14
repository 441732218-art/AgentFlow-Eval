# (c) 2026 AgentFlow-Eval
"""Structured logging with rotation support."""

import logging
import sys
from logging.handlers import RotatingFileHandler

from app.config import settings

try:
    import structlog
    HAS_STRUCTLOG = True
except ImportError:
    HAS_STRUCTLOG = False


def setup_logging() -> None:
    """Configure application logging with rotation and optional structlog."""
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    fmt = "%(asctime)s | %(levelname)-7s | %(name)s:%(lineno)d | %(message)s"
    date_fmt = "%Y-%m-%d %H:%M:%S"
    formatter = logging.Formatter(fmt, datefmt=date_fmt)

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Console handler
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(log_level)
    console.setFormatter(formatter)
    root_logger.addHandler(console)

    # File handler with rotation (10 MB per file, keep 30 backups)
    file_handler = RotatingFileHandler(
        settings.LOG_FILE,
        maxBytes=settings.LOG_MAX_BYTES,
        backupCount=settings.LOG_BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    # Quiet noisy libraries
    for lib in ("httpx", "openai", "aiosqlite", "celery", "asyncio"):
        logging.getLogger(lib).setLevel(logging.WARNING)

    # Optional structlog integration
    if HAS_STRUCTLOG:
        structlog.configure(
            processors=[
                structlog.contextvars.merge_contextvars,
                structlog.stdlib.filter_by_level,
                structlog.stdlib.add_logger_name,
                structlog.stdlib.add_log_level,
                structlog.stdlib.PositionalArgumentsFormatter(),
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.dev.ConsoleRenderer()
                    if settings.LOG_FORMAT == "text"
                    else structlog.processors.JSONRenderer(),
            ],
            wrapper_class=structlog.make_filtering_bound_logger(log_level),
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            cache_logger_on_first_use=True,
        )
        logging.getLogger().info("structlog initialized in %s mode", settings.LOG_FORMAT)
