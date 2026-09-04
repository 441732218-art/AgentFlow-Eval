# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Runtime governance evidence aggregation coordinator."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from typing import Any

from app.runtime.analytics.models import ExecutionMetric
from app.runtime.audit.models import AuditRecord
from app.runtime.checkpoint.models import Checkpoint
from app.runtime.context.snapshot import RuntimeContextSnapshot
from app.runtime.context_memory.models import MemoryContext
from app.runtime.event_stream.models import RuntimeEventEnvelope
from app.runtime.evidence.models import (
    CheckpointSummary,
    EventSummary,
    EvidenceStatus,
    ExecutionEvidence,
    MemorySnapshotSummary,
    MetricsSummary,
    PermissionDecision,
    StateSnapshotSummary,
)
from app.runtime.evidence.store import EvidenceStore
from app.runtime.state.models import ExecutionState


class RuntimeEvidenceCollector:
    """Aggregate existing runtime artifacts into unified execution evidence."""

    def __init__(self, store: EvidenceStore) -> None:
        self._store = store

    @property
    def store(self) -> EvidenceStore:
        return self._store

    def collect(
        self,
        *,
        execution_id: str,
        agent_id: str,
        correlation_id: str | None,
        status: EvidenceStatus,
        context_snapshot: RuntimeContextSnapshot | None = None,
        execution_state: ExecutionState | None = None,
        checkpoint: Checkpoint | None = None,
        memory_context: MemoryContext | None = None,
        audit_records: Sequence[AuditRecord] | None = None,
        runtime_events: Sequence[RuntimeEventEnvelope] | None = None,
        execution_metric: ExecutionMetric | None = None,
        permission_decisions: Sequence[PermissionDecision] | None = None,
    ) -> ExecutionEvidence:
        """Aggregate read-only runtime inputs into one evidence record."""
        normalized_audit_records = tuple(audit_records or ())
        normalized_events = tuple(runtime_events or ())
        normalized_permissions = tuple(permission_decisions or ())
        if not normalized_permissions and normalized_audit_records:
            normalized_permissions = self.derive_permission_decisions(
                normalized_audit_records
            )

        return ExecutionEvidence(
            evidence_id=uuid.uuid4().hex,
            execution_id=execution_id,
            agent_id=agent_id,
            correlation_id=correlation_id,
            status=status,
            state_snapshot=self._build_state_snapshot(
                execution_state,
                context_snapshot=context_snapshot,
                agent_id=agent_id,
            ),
            checkpoint_summary=self._build_checkpoint_summary(
                checkpoint,
                context_snapshot=context_snapshot,
            ),
            memory_snapshot=self._build_memory_snapshot(
                memory_context,
                context_snapshot=context_snapshot,
                agent_id=agent_id,
                execution_id=execution_id,
            ),
            audit_records=normalized_audit_records,
            event_summary=self._build_event_summary(normalized_events),
            metrics_summary=self._build_metrics_summary(execution_metric),
            permission_decisions=normalized_permissions,
        )

    def collect_and_save(
        self,
        *,
        execution_id: str,
        agent_id: str,
        correlation_id: str | None,
        status: EvidenceStatus,
        context_snapshot: RuntimeContextSnapshot | None = None,
        execution_state: ExecutionState | None = None,
        checkpoint: Checkpoint | None = None,
        memory_context: MemoryContext | None = None,
        audit_records: Sequence[AuditRecord] | None = None,
        runtime_events: Sequence[RuntimeEventEnvelope] | None = None,
        execution_metric: ExecutionMetric | None = None,
        permission_decisions: Sequence[PermissionDecision] | None = None,
    ) -> ExecutionEvidence:
        """Aggregate runtime inputs and persist the resulting evidence."""
        evidence = self.collect(
            execution_id=execution_id,
            agent_id=agent_id,
            correlation_id=correlation_id,
            status=status,
            context_snapshot=context_snapshot,
            execution_state=execution_state,
            checkpoint=checkpoint,
            memory_context=memory_context,
            audit_records=audit_records,
            runtime_events=runtime_events,
            execution_metric=execution_metric,
            permission_decisions=permission_decisions,
        )
        self._store.save(evidence)
        return evidence

    @staticmethod
    def derive_permission_decisions(
        audit_records: Sequence[AuditRecord],
    ) -> tuple[PermissionDecision, ...]:
        """Derive permission decisions from existing audit records."""
        decisions: list[PermissionDecision] = []
        for record in audit_records:
            if "permission" not in record.event_type:
                continue
            decision: str = record.decision if record.decision in {"ALLOW", "DENY"} else "UNKNOWN"
            decisions.append(
                PermissionDecision(
                    execution_id=record.execution_id,
                    decision=decision,  # type: ignore[arg-type]
                    tool_name=record.resource,
                    permission=_optional_str(record.metadata.get("permission")),
                    correlation_id=record.correlation_id,
                    metadata=dict(record.metadata),
                )
            )
        return tuple(decisions)

    @staticmethod
    def _build_state_snapshot(
        execution_state: ExecutionState | None,
        *,
        context_snapshot: RuntimeContextSnapshot | None = None,
        agent_id: str | None = None,
    ) -> StateSnapshotSummary | None:
        if execution_state is not None:
            return StateSnapshotSummary(
                execution_id=execution_state.execution_id,
                agent_id=execution_state.agent_id,
                plan_id=execution_state.plan_id,
                status=execution_state.status,
                current_step=execution_state.current_step,
                metadata=dict(execution_state.metadata),
            )
        if context_snapshot is None or agent_id is None:
            return None
        metadata = dict(context_snapshot.metadata)
        if context_snapshot.latest_checkpoint_id is not None:
            metadata.setdefault(
                "latest_checkpoint_id",
                context_snapshot.latest_checkpoint_id,
            )
        return StateSnapshotSummary(
            execution_id=context_snapshot.execution_id,
            agent_id=agent_id,
            plan_id=str(metadata.get("plan_id", "")),
            status=context_snapshot.status,
            current_step=context_snapshot.current_step,
            metadata=metadata,
        )

    @staticmethod
    def _build_checkpoint_summary(
        checkpoint: Checkpoint | None,
        *,
        context_snapshot: RuntimeContextSnapshot | None = None,
    ) -> CheckpointSummary | None:
        if checkpoint is not None:
            snapshot = dict(checkpoint.state_snapshot)
            completed_steps = snapshot.get("completed_steps", [])
            return CheckpointSummary(
                checkpoint_id=checkpoint.checkpoint_id,
                execution_id=checkpoint.execution_id,
                plan_id=checkpoint.plan_id,
                step_id=checkpoint.step_id,
                status=_optional_str(snapshot.get("status")),
                completed_steps=tuple(str(step) for step in completed_steps),
                metadata=dict(checkpoint.metadata),
            )
        if context_snapshot is None or context_snapshot.latest_checkpoint_id is None:
            return None
        return CheckpointSummary(
            checkpoint_id=context_snapshot.latest_checkpoint_id,
            execution_id=context_snapshot.execution_id,
            status=context_snapshot.status,
            metadata=dict(context_snapshot.metadata),
        )

    @staticmethod
    def _build_memory_snapshot(
        memory_context: MemoryContext | None,
        *,
        context_snapshot: RuntimeContextSnapshot | None = None,
        agent_id: str | None = None,
        execution_id: str | None = None,
    ) -> MemorySnapshotSummary | None:
        if memory_context is not None:
            return MemorySnapshotSummary(
                memory_id=memory_context.memory_id,
                execution_id=memory_context.execution_id,
                agent_id=memory_context.agent_id,
                namespace=memory_context.namespace,
                data=dict(memory_context.data),
            )
        if (
            context_snapshot is None
            or context_snapshot.memory_namespace is None
            or agent_id is None
            or execution_id is None
        ):
            return None
        return MemorySnapshotSummary(
            memory_id=context_snapshot.memory_namespace,
            execution_id=execution_id,
            agent_id=agent_id,
            namespace=context_snapshot.memory_namespace,
            data={},
        )

    @staticmethod
    def _build_event_summary(
        runtime_events: Sequence[RuntimeEventEnvelope],
    ) -> EventSummary | None:
        if not runtime_events:
            return None
        event_types = tuple(dict.fromkeys(event.event_type for event in runtime_events))
        return EventSummary(
            total_events=len(runtime_events),
            event_types=event_types,
            first_event_id=runtime_events[0].event_id,
            last_event_id=runtime_events[-1].event_id,
        )

    @staticmethod
    def _build_metrics_summary(
        execution_metric: ExecutionMetric | None,
    ) -> MetricsSummary | None:
        if execution_metric is None:
            return None
        return MetricsSummary(
            duration_ms=execution_metric.duration_ms,
            step_count=execution_metric.step_count,
            tool_count=execution_metric.tool_count,
            failure_count=execution_metric.failure_count,
            status=execution_metric.status,
            metadata=dict(execution_metric.metadata),
        )


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)
