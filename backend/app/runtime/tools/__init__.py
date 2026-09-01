# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Tool registration and discovery for Runtime integrations."""

from __future__ import annotations

from app.runtime.tools.adapter import ToolExecutorAdapter
from app.runtime.tools.auth import ToolProviderAuth
from app.runtime.tools.definition import (
    ALLOWED_EXECUTOR_TYPES,
    ToolDefinition,
    validate_tool_definition,
)
from app.runtime.tools.engine import ToolExecutionEngine, ToolExecutionResult
from app.runtime.tools.errors import (
    RemoteProviderError,
    RemoteResponseValidationError,
    RemoteTimeoutError,
    ToolExecutionError,
    ToolInputValidationError,
)
from app.runtime.tools.executor_registry import (
    DuplicateExecutorAdapterError,
    ToolExecutorRegistry,
    UnknownExecutorTypeError,
)
from app.runtime.tools.factory import (
    create_default_tool_execution_engine,
    create_tool_execution_engine,
)
from app.runtime.tools.local_adapter import LocalToolExecutorAdapter
from app.runtime.tools.local_handler_registry import (
    DuplicateLocalHandlerError,
    LocalHandlerRegistry,
    MissingLocalHandlerError,
    register_legacy_tool_handler,
)
from app.runtime.tools.policy import RemoteExecutionPolicy
from app.runtime.tools.provider import (
    ToolProviderProtocol,
    ToolProviderRequest,
    ToolProviderResponse,
)
from app.runtime.tools.remote_adapter import RemoteToolExecutorAdapter
from app.runtime.tools.remote_client import InMemoryRemoteClient, RemoteToolClient
from app.runtime.tools.registry import (
    DuplicateToolError,
    Tool,
    ToolMetadata,
    ToolRegistry,
    tool_definition_from_legacy,
)
from app.runtime.tools.validation import validate_arguments

__all__ = [
    "ALLOWED_EXECUTOR_TYPES",
    "DuplicateExecutorAdapterError",
    "DuplicateLocalHandlerError",
    "DuplicateToolError",
    "InMemoryRemoteClient",
    "LocalHandlerRegistry",
    "LocalToolExecutorAdapter",
    "MissingLocalHandlerError",
    "RemoteExecutionPolicy",
    "RemoteProviderError",
    "RemoteResponseValidationError",
    "RemoteTimeoutError",
    "RemoteToolClient",
    "RemoteToolExecutorAdapter",
    "Tool",
    "ToolDefinition",
    "ToolExecutionEngine",
    "ToolExecutionError",
    "ToolExecutionResult",
    "ToolExecutorAdapter",
    "ToolExecutorRegistry",
    "ToolInputValidationError",
    "ToolMetadata",
    "ToolProviderAuth",
    "ToolProviderProtocol",
    "ToolProviderRequest",
    "ToolProviderResponse",
    "ToolRegistry",
    "UnknownExecutorTypeError",
    "create_default_tool_execution_engine",
    "create_tool_execution_engine",
    "register_legacy_tool_handler",
    "tool_definition_from_legacy",
    "validate_arguments",
    "validate_tool_definition",
]
