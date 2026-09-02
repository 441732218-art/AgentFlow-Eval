# AgentFlow Intelligence v2.0 — ExecutionContext governance tests (Phase 9.4)

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx
import pytest

from app.runtime.context import RuntimeContext
from app.runtime.executor.context_fields import (
    TENANT_ID_METADATA_KEY,
    USER_ID_METADATA_KEY,
    attach_execution_context,
    attach_tool_request,
    ensure_execution_context,
    get_execution_context,
)
from app.runtime.executor.execution_context import ExecutionContext
from app.runtime.pipeline import ExecutionPipeline
from app.runtime.pipeline.tool_step import execute_tool_via_engine
from app.runtime.tools.adapter import ToolExecutorAdapter
from app.runtime.tools.definition import ToolDefinition
from app.runtime.tools.engine import ToolExecutionEngine, ToolExecutionResult
from app.runtime.tools.executor_registry import ToolExecutorRegistry
from app.runtime.tools.http_client import HttpRemoteToolClient
from app.runtime.tools.invocation_event import ToolInvocationEvent
from app.runtime.tools.policy import RemoteExecutionPolicy
from app.runtime.tools.provider import ToolProviderRequest

_RUNTIME_ROOT = Path(__file__).resolve().parents[3] / "app" / "runtime"
_FORBIDDEN_RUNTIME_STRINGS = (
    "trade_provider",
    "trade.",
    "CRM",
    "Email",
)
_MOCK_ENDPOINT = "http://mock.test/tools/invoke"


def test_execution_context_initializes_with_defaults() -> None:
    context = ExecutionContext(
        execution_id="exec-001",
        agent_id="sales-agent",
        tenant_id="tenant-a",
        user_id="user-001",
    )

    assert context.execution_id == "exec-001"
    assert context.agent_id == "sales-agent"
    assert context.tenant_id == "tenant-a"
    assert context.user_id == "user-001"
    assert context.metadata == {}


def test_execution_context_to_remote_payload_omits_none_fields() -> None:
    context = ExecutionContext(
        execution_id="exec-002",
        agent_id="agent-1",
        tenant_id="tenant-b",
    )

    payload = context.to_remote_payload()

    assert payload == {
        "execution_id": "exec-002",
        "agent_id": "agent-1",
        "tenant_id": "tenant-b",
    }
    assert "user_id" not in payload


def test_ensure_execution_context_materializes_from_runtime_metadata() -> None:
    runtime = RuntimeContext(
        execution_id="exec-003",
        agent_id="agent-2",
        metadata={
            TENANT_ID_METADATA_KEY: "tenant-c",
            USER_ID_METADATA_KEY: "user-2",
        },
    )

    execution_context = ensure_execution_context(runtime)

    assert execution_context is not None
    assert execution_context.execution_id == "exec-003"
    assert execution_context.tenant_id == "tenant-c"
    assert execution_context.user_id == "user-2"
    assert get_execution_context(runtime) is execution_context


class ContextRecordingAdapter(ToolExecutorAdapter):
    executor_type = "local"

    def __init__(self) -> None:
        self.received_context: ExecutionContext | None = None

    def execute(
        self,
        tool_definition: ToolDefinition,
        arguments: dict[str, Any],
        *,
        execution_context: ExecutionContext | None = None,
    ) -> Any:
        _ = tool_definition, arguments
        self.received_context = execution_context
        return {"ok": True}


def test_pipeline_propagates_execution_context_to_engine() -> None:
    adapter = ContextRecordingAdapter()
    registry = ToolExecutorRegistry()
    registry.register(adapter)
    engine = ToolExecutionEngine(adapter_registry=registry)
    definition = ToolDefinition(
        name="context.tool",
        description="Context probe",
        executor_type="local",
        input_schema={"type": "object"},
    )
    execution_context = ExecutionContext(
        execution_id="exec-pipeline-1",
        agent_id="agent-pipeline",
        tenant_id="tenant-pipeline",
        user_id="user-pipeline",
    )
    runtime = attach_tool_request(
        RuntimeContext(execution_id="exec-pipeline-1", agent_id="agent-pipeline"),
        definition,
        {"query": "x"},
    )
    attach_execution_context(runtime, execution_context)

    output = execute_tool_via_engine(runtime, engine)

    assert output == {"ok": True}
    assert adapter.received_context == execution_context


def test_http_remote_payload_includes_execution_context() -> None:
    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["payload"] = json.loads(request.content.decode())
        return httpx.Response(
            200,
            json={"success": True, "output": {"ok": True}, "metadata": {}},
        )

    transport = httpx.MockTransport(handler)
    client = HttpRemoteToolClient(
        http_client=httpx.Client(transport=transport),
        remote_policy=RemoteExecutionPolicy(timeout_seconds=5.0),
    )
    request = ToolProviderRequest(
        tool_name="example.remote",
        arguments={"query": "ctx"},
        metadata={
            "endpoint": _MOCK_ENDPOINT,
            "execution_context": {
                "execution_id": "exec-http-1",
                "agent_id": "agent-http",
                "tenant_id": "tenant-http",
            },
        },
    )

    client.send(request)

    context_payload = captured["payload"]["context"]
    assert context_payload["execution_id"] == "exec-http-1"
    assert context_payload["agent_id"] == "agent-http"
    assert context_payload["tenant_id"] == "tenant-http"
    assert "credential" not in json.dumps(captured["payload"]).lower()
    assert "secret" not in json.dumps(captured["payload"]).lower()


def test_tool_invocation_event_model_fields() -> None:
    event = ToolInvocationEvent(
        execution_id="exec-event-1",
        tool_name="example.tool",
        started_at=1.0,
        finished_at=2.5,
        status="success",
    )

    assert event.execution_id == "exec-event-1"
    assert event.tool_name == "example.tool"
    assert event.status == "success"
    assert event.error_type is None
    assert event.start_time == 1.0
    assert event.end_time == 2.5
    assert event.duration_ms == 1500.0


def test_runtime_core_has_no_business_leakage() -> None:
    for path in _RUNTIME_ROOT.rglob("*.py"):
        source = path.read_text(encoding="utf-8")
        for forbidden in _FORBIDDEN_RUNTIME_STRINGS:
            assert forbidden not in source, f"{forbidden!r} found in {path}"


def test_pipeline_without_execution_context_keeps_backward_compatible_behavior() -> None:
    adapter = ContextRecordingAdapter()
    registry = ToolExecutorRegistry()
    registry.register(adapter)
    engine = ToolExecutionEngine(adapter_registry=registry)
    pipeline = ExecutionPipeline(tool_execution_engine=engine)
    definition = ToolDefinition(
        name="context.optional",
        description="Optional context",
        executor_type="local",
        input_schema={"type": "object"},
    )
    runtime = attach_tool_request(
        RuntimeContext(execution_id="exec-no-ctx", agent_id="agent-1"),
        definition,
        {},
    )

    output = pipeline.run(runtime, "task")

    assert output == {"ok": True}
    assert adapter.received_context is None
