# (c) 2026 AgentFlow-Eval
"""Application logging entrypoint — delegates to AOLS (structlog JSON)."""

from __future__ import annotations

from typing import Any


def setup_logging() -> None:
    """Configure process-wide logging (structlog + rotating file)."""
    from app.core.observability.aols.logger import setup_aols_logging

    setup_aols_logging()


def get_logger(name: str | None = None) -> Any:
    """Structured logger factory (compat re-export)."""
    from app.core.observability.aols.logger import get_logger as _get

    return _get(name)
