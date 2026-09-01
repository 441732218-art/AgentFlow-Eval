# AgentFlow Intelligence v2.0 — Agent Runtime MVP (Sprint 1)
"""Runner adapters. Wrap v1 runners via build_agent_runner; do not modify them."""

from __future__ import annotations

from app.core.runtime.adapters.base import (
    HTTP_RUNNER_TYPES,
    OPENAI_RUNNER_TYPES,
    RuntimeAdapter,
)
from app.core.runtime.adapters.http_adapter import HttpAdapter
from app.core.runtime.adapters.openai_adapter import OpenAIAdapter
from app.core.runtime.adapters.plugin_adapter import PluginAdapter


def resolve_adapter(runner_type: str) -> RuntimeAdapter:
    """Pick an adapter by Agent.runner_type. Does not construct LLM clients."""
    key = str(runner_type or "").strip().lower()
    if key in OPENAI_RUNNER_TYPES:
        return OpenAIAdapter()
    if key in HTTP_RUNNER_TYPES:
        return HttpAdapter()
    return PluginAdapter()


__all__ = [
    "HTTP_RUNNER_TYPES",
    "OPENAI_RUNNER_TYPES",
    "HttpAdapter",
    "OpenAIAdapter",
    "PluginAdapter",
    "RuntimeAdapter",
    "resolve_adapter",
]
