# (c) 2026 AgentFlow-Eval
"""AOLS structured logger factory + setup (structlog + stdlib bridge)."""

from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler
from typing import Any

from app.config import settings

try:
    import structlog
    from structlog.types import EventDict, Processor, WrappedLogger

    HAS_STRUCTLOG = True
except ImportError:  # pragma: no cover
    HAS_STRUCTLOG = False
    EventDict = dict  # type: ignore[misc, assignment]
    Processor = Any  # type: ignore[misc, assignment]
    WrappedLogger = Any  # type: ignore[misc, assignment]


def _add_service_fields(
    logger: WrappedLogger, method_name: str, event_dict: EventDict
) -> EventDict:
    """Inject service / environment / default trace_id."""
    event_dict.setdefault("service", getattr(settings, "LOG_SERVICE_NAME", "agentflow-api"))
    event_dict.setdefault(
        "environment",
        getattr(settings, "ENV", None) or getattr(settings, "APP_ENV", "dev"),
    )
    # Pull live TraceID if not already bound
    if not event_dict.get("trace_id"):
        try:
            from app.core.observability.tracing import get_trace_id

            tid = get_trace_id()
            if tid:
                event_dict["trace_id"] = tid
                event_dict.setdefault("request_id", tid)
        except Exception:
            pass
    return event_dict


def _redact_event_dict(
    logger: WrappedLogger, method_name: str, event_dict: EventDict
) -> EventDict:
    from app.core.observability.aols.redaction import redact_mapping

    # Never drop the event name
    event = event_dict.get("event")
    cleaned = redact_mapping(dict(event_dict))
    if event is not None:
        cleaned["event"] = event
    return cleaned  # type: ignore[return-value]


def _rename_event_key(
    logger: WrappedLogger, method_name: str, event_dict: EventDict
) -> EventDict:
    """Keep structlog's event key; ensure string."""
    if "event" in event_dict and event_dict["event"] is not None:
        event_dict["event"] = str(event_dict["event"])
    return event_dict


class _StructlogJsonFormatter(logging.Formatter):
    """Render stdlib LogRecord via structlog processors for file/console JSON."""

    def __init__(self, processors: list[Processor]) -> None:
        super().__init__()
        self._processors = processors

    def format(self, record: logging.LogRecord) -> str:
        event_dict: EventDict = {
            "event": record.getMessage(),
            "level": record.levelname.lower(),
            "logger": record.name,
        }
        if record.exc_info:
            event_dict["exc_info"] = record.exc_info
        # Merge extra fields (exclude private LogRecord attrs)
        for key, value in record.__dict__.items():
            if key.startswith("_") or key in {
                "name",
                "msg",
                "args",
                "created",
                "filename",
                "funcName",
                "levelname",
                "levelno",
                "lineno",
                "module",
                "msecs",
                "pathname",
                "process",
                "processName",
                "relativeCreated",
                "stack_info",
                "exc_info",
                "exc_text",
                "thread",
                "threadName",
                "message",
                "taskName",
            }:
                continue
            event_dict[key] = value

        for proc in self._processors:
            event_dict = proc(None, record.levelname.lower(), event_dict)  # type: ignore[arg-type]
        # Last processor should return str when using JSONRenderer/ConsoleRenderer
        if isinstance(event_dict, str):
            return event_dict
        return str(event_dict)


def setup_aols_logging() -> None:
    """Configure root logging + structlog for the process."""
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    use_json = (settings.LOG_FORMAT or "text").lower() == "json"

    # ---- shared processor chain (before renderer) ----
    shared: list[Any] = []
    if HAS_STRUCTLOG:
        shared = [
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.processors.TimeStamper(fmt="iso", utc=True, key="timestamp"),
            _add_service_fields,
            _rename_event_key,
            _redact_event_dict,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
        ]
        renderer: Any = (
            structlog.processors.JSONRenderer()
            if use_json
            else structlog.dev.ConsoleRenderer(colors=False)
        )

        structlog.configure(
            processors=[
                structlog.contextvars.merge_contextvars,
                structlog.stdlib.filter_by_level,
                structlog.stdlib.add_logger_name,
                structlog.stdlib.add_log_level,
                structlog.stdlib.PositionalArgumentsFormatter(),
                structlog.processors.TimeStamper(fmt="iso", utc=True, key="timestamp"),
                _add_service_fields,
                _rename_event_key,
                _redact_event_dict,
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
            ],
            wrapper_class=structlog.make_filtering_bound_logger(log_level),
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            cache_logger_on_first_use=True,
        )

        formatter: logging.Formatter = structlog.stdlib.ProcessorFormatter(
            processor=renderer,
            foreign_pre_chain=shared,
        )
    else:
        fmt = "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"
        formatter = logging.Formatter(fmt, datefmt="%Y-%m-%d %H:%M:%S")

    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(log_level)

    console = logging.StreamHandler(sys.stdout)
    console.setLevel(log_level)
    console.setFormatter(formatter)
    root.addHandler(console)

    try:
        file_handler = RotatingFileHandler(
            settings.LOG_FILE,
            maxBytes=settings.LOG_MAX_BYTES,
            backupCount=settings.LOG_BACKUP_COUNT,
            encoding="utf-8",
        )
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        root.addHandler(file_handler)
    except Exception as exc:  # pragma: no cover
        root.warning("File log handler unavailable: %s", exc)

    for lib in ("httpx", "openai", "aiosqlite", "celery", "asyncio", "uvicorn.access"):
        logging.getLogger(lib).setLevel(logging.WARNING)

    root.info(
        "aols.initialized format=%s level=%s service=%s",
        settings.LOG_FORMAT,
        settings.LOG_LEVEL,
        getattr(settings, "LOG_SERVICE_NAME", "agentflow-api"),
    )


def get_logger(name: str | None = None) -> Any:
    """Return a structured logger.

    Prefer::

        log = get_logger(__name__)
        log.info("http.request", method="GET", path="/health", status_code=200)

    Falls back to stdlib LoggerAdapter if structlog is missing.
    """
    if HAS_STRUCTLOG:
        return structlog.get_logger(name or "agentflow")
    return logging.getLogger(name or "agentflow")
