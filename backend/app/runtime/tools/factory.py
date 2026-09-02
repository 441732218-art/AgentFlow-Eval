# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Factory helpers for default tool execution wiring."""

from __future__ import annotations

from app.runtime.tools.engine import ToolExecutionEngine
from app.runtime.tools.executor_registry import ToolExecutorRegistry
from app.runtime.tools.http_client import HttpRemoteToolClient
from app.runtime.tools.local_adapter import LocalToolExecutorAdapter
from app.runtime.tools.local_handler_registry import LocalHandlerRegistry
from app.runtime.tools.policy import RemoteExecutionPolicy
from app.runtime.tools.remote_adapter import RemoteToolExecutorAdapter
from app.runtime.tools.remote_client import RemoteToolClient


def create_default_tool_execution_engine(
    handler_registry: LocalHandlerRegistry | None = None,
) -> ToolExecutionEngine:
    """Build a ``ToolExecutionEngine`` with the local adapter registered.

    Registers ``executor_type='local'`` only. Remote and other adapters are
    not registered by this factory.
    """
    handlers = handler_registry or LocalHandlerRegistry()
    adapter_registry = ToolExecutorRegistry()
    adapter_registry.register(LocalToolExecutorAdapter(handlers))
    return ToolExecutionEngine(adapter_registry=adapter_registry)


def create_tool_execution_engine(
    handler_registry: LocalHandlerRegistry | None = None,
    remote_client: RemoteToolClient | None = None,
    remote_policy: RemoteExecutionPolicy | None = None,
) -> ToolExecutionEngine:
    """Build a ``ToolExecutionEngine`` with local and optional remote adapters."""
    handlers = handler_registry or LocalHandlerRegistry()
    adapter_registry = ToolExecutorRegistry()
    adapter_registry.register(LocalToolExecutorAdapter(handlers))
    if remote_client is not None:
        adapter_registry.register(
            RemoteToolExecutorAdapter(remote_client, policy=remote_policy)
        )
    return ToolExecutionEngine(adapter_registry=adapter_registry)


def create_http_remote_tool_client(
    *,
    remote_policy: RemoteExecutionPolicy | None = None,
) -> HttpRemoteToolClient:
    """Build ``HttpRemoteToolClient`` with timeout from ``RemoteExecutionPolicy``."""
    return HttpRemoteToolClient(remote_policy=remote_policy)
