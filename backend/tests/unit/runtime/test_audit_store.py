# AgentFlow Intelligence v2.0 — Runtime audit store tests (Phase 9.7)

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest

from app.runtime.audit.memory_store import InMemoryAuditStore
from app.runtime.audit.models import AuditRecord
from app.runtime.context import RuntimeContext
from app.runtime.events.event_types import RuntimeEventType
from app.runtime.events.models import RuntimeEvent
from app.runtime.events.publisher import InMemoryEventPublisher
from app.runtime.executor.context_fields import attach_execution_context, attach_tool_request
from app.runtime.executor.execution_context import ExecutionContext
from app.runtime.observability.events import RuntimeEventType as ObservationEventType
from app.runtime.observability.recording import build_runtime_event, record_runtime_event
from app.runtime.pipeline.tool_step import execute_tool_via_engine
from app.runtime.tools.adapter import ToolExecutorAdapter
from app.runtime.tools.definition import ToolDefinition
from app.runtime.tools.engine import ToolExecutionEngine
from app.runtime.tools.executor_registry import ToolExecutorRegistry

_AUDIT_ROOT = Path(__file__).resolve().parents[3] / "app" / "runtime" / "audit"
_AUDIT_SCAN_PATHS = (
    _AUDIT_ROOT,
    Path(__file__).resolve().parents[3] / "app" / "runtime" / "events",
)
_FORBIDDEN_STRINGS = ("trade_provider", "CRM", "Email", "database")


def test_audit_record_creation() -> None:
    timestamp = datetime(2026, 3, 1, tzinfo=timezone.utc)
    record = AuditRecord(
        audit_id="audit-1",
        event_type=RuntimeEventType.TOOL_STARTED,
        execution_id="exec-1",
        agent_id="agent-1",
        timestamp=timestamp,
        metadata={"tool_name": "probe.tool", "tenant_id": "tenant-1"},
    )

    assert record.id == "audit-1"
    assert record.execution_id == "exec-1"
    assert record.payload["tool_name"] == "probe.tool"
    assert record.tenant_id == "tenant-1"


def test_memory_store_append_and_query() -> None:
    store = InMemoryAuditStore()
    record = AuditRecord(
        audit_id="audit-2",
        event_type=RuntimeEventType.EXECUTION_STARTED,
        execution_id="exec-2",
        timestamp=datetime.now(timezone.utc),
        metadata={"task": "run"},
    )

    store.append(record)

    assert len(store.query()) == 1
    store.clear()
    assert store.query() == []


def test_query_by_execution_id() -> None:
    store = InMemoryAuditStore()
    store.append(
        AuditRecord(
            audit_id="audit-3a",
            event_type=RuntimeEventType.TOOL_STARTED,
            execution_id="exec-a",
            timestamp=datetime.now(timezone.utc),
        )
    )
    store.append(
        AuditRecord(
            audit_id="audit-3b",
            event_type=RuntimeEventType.TOOL_STARTED,
            execution_id="exec-b",
            timestamp=datetime.now(timezone.utc),
        )
    )

    results = store.query(execution_id="exec-a")

    assert len(results) == 1
    assert results[0].execution_id == "exec-a"


def test_query_by_tenant_id() -> None:
    store = InMemoryAuditStore()
    store.append(
        AuditRecord(
            audit_id="audit-4a",
            event_type=RuntimeEventType.TOOL_COMPLETED,
            execution_id="exec-4a",
            timestamp=datetime.now(timezone.utc),
            metadata={"tenant_id": "tenant-x"},
        )
    )
    store.append(
        AuditRecord(
            audit_id="audit-4b",
            event_type=RuntimeEventType.TOOL_COMPLETED,
            execution_id="exec-4b",
            timestamp=datetime.now(timezone.utc),
            metadata={"tenant_id": "tenant-y"},
        )
    )

    results = store.query(tenant_id="tenant-x")

    assert len(results) == 1
    assert results[0].tenant_id == "tenant-x"


def test_publisher_writes_audit_record() -> None:
    store = InMemoryAuditStore()
    publisher = InMemoryEventPublisher(audit_store=store)
    event = RuntimeEvent(
        event_type=RuntimeEventType.TOOL_COMPLETED,
        execution_id="exec-5",
        agent_id="agent-5",
        tenant_id="tenant-5",
        timestamp=datetime.now(timezone.utc),
        payload={"tool_name": "done.tool", "status": "success"},
    )

    publisher.publish(event)

    assert len(publisher.get_events()) == 1
    records = store.query(execution_id="exec-5")
    assert len(records) == 1
    assert records[0].event_type == RuntimeEventType.TOOL_COMPLETED
    assert records[0].payload["tool_name"] == "done.tool"


class LocalProbeAdapter(ToolExecutorAdapter):
    executor_type = "local"

    def execute(
        self,
        tool_definition: ToolDefinition,
        arguments: dict[str, Any],
        *,
        execution_context: ExecutionContext | None = None,
    ) -> Any:
        _ = tool_definition, arguments, execution_context
        return {"ok": True}


def test_audit_failure_does_not_affect_runtime() -> None:
    class BrokenAuditStore:
        def append(self, _record: AuditRecord) -> None:
            raise RuntimeError("audit unavailable")

        def query(
            self,
            execution_id: str | None = None,
            tenant_id: str | None = None,
        ) -> list[AuditRecord]:
            _ = execution_id, tenant_id
            return []

        def clear(self) -> None:
            return None

    store = BrokenAuditStore()
    publisher = InMemoryEventPublisher(audit_store=store)
    execution_context = ExecutionContext(
        execution_id="exec-6",
        agent_id="agent-6",
        event_publisher=publisher,
        audit_store=store,
    )
    registry = ToolExecutorRegistry()
    registry.register(LocalProbeAdapter())
    engine = ToolExecutionEngine(adapter_registry=registry)
    definition = ToolDefinition(
        name="probe.safe",
        description="Safe probe",
        executor_type="local",
        input_schema={"type": "object"},
    )
    runtime = attach_tool_request(
        RuntimeContext(execution_id="exec-6", agent_id="agent-6"),
        definition,
        {},
    )
    attach_execution_context(runtime, execution_context)

    output = execute_tool_via_engine(runtime, engine)

    assert output == {"ok": True}
    assert len(publisher.get_events()) >= 1


def test_remote_payload_does_not_leak_internal_stores() -> None:
    store = InMemoryAuditStore()
    publisher = InMemoryEventPublisher(audit_store=store)
    execution_context = ExecutionContext(
        execution_id="exec-7",
        agent_id="agent-7",
        tenant_id="tenant-7",
        event_publisher=publisher,
        audit_store=store,
    )

    payload = execution_context.to_remote_payload()

    assert payload == {
        "execution_id": "exec-7",
        "agent_id": "agent-7",
        "tenant_id": "tenant-7",
    }
    assert "event_publisher" not in payload
    assert "audit_store" not in payload
    assert "observation_collector" not in payload


def test_runtime_audit_code_has_no_business_leakage() -> None:
    for root in _AUDIT_SCAN_PATHS:
        for path in root.rglob("*.py"):
            source = path.read_text(encoding="utf-8")
            for forbidden in _FORBIDDEN_STRINGS:
                assert forbidden not in source, f"{forbidden!r} found in {path}"
