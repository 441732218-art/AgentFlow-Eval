# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Remote executor adapter — routes tools through the Tool Provider Protocol."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

from app.runtime.tools.adapter import ToolExecutorAdapter
from app.runtime.tools.auth import ToolProviderAuth
from app.runtime.tools.definition import ToolDefinition
from app.runtime.tools.errors import (
    RemoteProviderError,
    RemoteResponseValidationError,
    RemoteTimeoutError,
    ToolExecutionError,
)
from app.runtime.tools.policy import RemoteExecutionPolicy
from app.runtime.tools.provider import ToolProviderRequest, ToolProviderResponse
from app.runtime.tools.remote_client import RemoteToolClient
from app.runtime.tools.validation import validate_arguments

if TYPE_CHECKING:
    from app.runtime.executor.execution_context import ExecutionContext


class RemoteToolExecutorAdapter(ToolExecutorAdapter):
    """Execute ``executor_type='remote'`` tools via ``RemoteToolClient``."""

    executor_type = "remote"

    def __init__(
        self,
        client: RemoteToolClient,
        policy: RemoteExecutionPolicy | None = None,
    ) -> None:
        self.client = client
        self.policy = policy or RemoteExecutionPolicy()

    def execute(
        self,
        tool_definition: ToolDefinition,
        arguments: dict[str, Any],
        *,
        execution_context: ExecutionContext | None = None,
    ) -> Any:
        normalized_arguments = dict(arguments)
        validate_arguments(tool_definition.input_schema, normalized_arguments)

        auth = ToolProviderAuth.from_metadata(tool_definition.metadata)
        request_metadata = self._build_request_metadata(tool_definition.metadata, auth)
        if execution_context is not None:
            request_metadata["execution_context"] = execution_context.to_remote_payload()
        request = ToolProviderRequest(
            tool_name=tool_definition.name,
            arguments=normalized_arguments,
            metadata=request_metadata,
        )

        last_error: ToolExecutionError | None = None
        for attempt in range(1, self.policy.max_attempts + 1):
            started_at = time.monotonic()
            try:
                response = self._send_once(request, tool_definition.name, started_at)
                self._validate_response(response, tool_definition.name)
                if not response.success:
                    raise RemoteProviderError(
                        response.error
                        or f"Remote provider failed for {tool_definition.name}",
                        tool_name=tool_definition.name,
                    )
                return response.output
            except ToolExecutionError as exc:
                last_error = self._ensure_tool_name(exc, tool_definition.name)
                if attempt >= self.policy.max_attempts or not self.policy.is_retryable(
                    last_error
                ):
                    raise last_error from last_error.cause

        if last_error is not None:
            raise last_error
        raise RemoteProviderError(
            f"Remote provider failed for {tool_definition.name}",
            tool_name=tool_definition.name,
        )

    def _send_once(
        self,
        request: ToolProviderRequest,
        tool_name: str,
        started_at: float,
    ) -> ToolProviderResponse:
        try:
            response = self.client.send(request)
        except ToolExecutionError:
            raise
        except Exception as exc:
            raise RemoteProviderError(
                f"Remote provider failed for {tool_name}",
                tool_name=tool_name,
                cause=exc,
            ) from exc

        elapsed = time.monotonic() - started_at
        if elapsed > self.policy.timeout_seconds:
            raise RemoteTimeoutError(
                f"Remote provider exceeded timeout ({self.policy.timeout_seconds}s)",
                tool_name=tool_name,
            )
        return response

    @staticmethod
    def _build_request_metadata(
        metadata: dict[str, Any],
        auth: ToolProviderAuth,
    ) -> dict[str, Any]:
        payload = {key: value for key, value in metadata.items() if key != "auth"}
        payload["auth"] = auth.to_metadata()
        return payload

    @staticmethod
    def _ensure_tool_name(error: ToolExecutionError, tool_name: str) -> ToolExecutionError:
        if error.tool_name is None:
            error.tool_name = tool_name
        return error

    @staticmethod
    def _validate_response(response: ToolProviderResponse, tool_name: str) -> None:
        if not isinstance(response, ToolProviderResponse):
            raise RemoteResponseValidationError(
                "Remote provider returned invalid response type",
                tool_name=tool_name,
            )
        if not isinstance(response.success, bool):
            raise RemoteResponseValidationError(
                "Remote provider response.success must be a bool",
                tool_name=tool_name,
            )
        if not isinstance(response.metadata, dict):
            raise RemoteResponseValidationError(
                "Remote provider response.metadata must be a dict",
                tool_name=tool_name,
            )
        if response.success is False and not (response.error or "").strip():
            raise RemoteResponseValidationError(
                "Remote provider failure response must include error",
                tool_name=tool_name,
            )

    @staticmethod
    def build_observation(
        *,
        tool_name: str,
        executor_type: str,
        duration_seconds: float,
        status: str,
        error_type: str | None = None,
    ) -> dict[str, str | float]:
        """Return a trace-safe observation payload (no secrets or customer payload)."""
        observation: dict[str, str | float] = {
            "tool_name": tool_name,
            "executor_type": executor_type,
            "duration_seconds": duration_seconds,
            "status": status,
        }
        if error_type:
            observation["error_type"] = error_type
        return observation
