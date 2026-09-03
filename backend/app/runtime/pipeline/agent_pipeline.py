# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Agent execution pipeline orchestrating runtime steps."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from app.runtime.agent.lifecycle import complete_session, fail_session, start_session
from app.runtime.agent.models import AgentDefinition
from app.runtime.bootstrap.factory import ProductionRuntime
from app.runtime.checkpoint.manager import CheckpointManager
from app.runtime.checkpoint.models import Checkpoint
from app.runtime.checkpoint.store import CheckpointStore
from app.runtime.context import RuntimeContext
from app.runtime.context.manager import RuntimeContextManager
from app.runtime.context_memory.manager import MemoryContextManager
from app.runtime.context_memory.models import MemoryContext
from app.runtime.correlation.context import attach_correlation_context, get_correlation_context
from app.runtime.correlation.manager import RuntimeCorrelationManager
from app.runtime.correlation.models import CorrelationContext
from app.runtime.executor.context_fields import attach_execution_context
from app.runtime.executor.execution_context import ExecutionContext
from app.runtime.execution.executor import StepExecutionContext, StepExecutor
from app.runtime.execution.sequential import SequentialExecutionStrategy
from app.runtime.execution.strategy import ExecutionStrategy
from app.runtime.pipeline.models import AgentExecutionResult, ExecutionStep
from app.runtime.pipeline.pipeline import ExecutionPipeline
from app.runtime.pipeline.steps import complete_step, create_step
from app.runtime.planning.default_planner import DefaultPlanner
from app.runtime.planning.planner import Planner
from app.runtime.state.models import ExecutionState
from app.runtime.state.store import ExecutionStateStore

if TYPE_CHECKING:
    from app.runtime.analytics.collector import RuntimeAnalyticsCollector
    from app.runtime.audit.recorder import RuntimeAuditRecorder
    from app.runtime.event_stream.publisher import EventPublisher


@dataclass
class _EventStreamRunTracker:
    """Mutable event chain state collected during one pipeline run."""

    last_event_id: str | None = None


def _publish_stream_envelope(
    publisher: EventPublisher,
    tracker: _EventStreamRunTracker,
    *,
    event_type: str,
    execution_id: str,
    correlation_id: str,
    payload: dict[str, Any] | None = None,
) -> str:
    from app.runtime.event_stream.models import RuntimeEventEnvelope

    event_id = uuid.uuid4().hex
    publisher.publish(
        RuntimeEventEnvelope(
            event_id=event_id,
            event_type=event_type,
            correlation_id=correlation_id,
            parent_event_id=tracker.last_event_id,
            execution_id=execution_id,
            payload=dict(payload or {}),
        )
    )
    tracker.last_event_id = event_id
    return event_id


@dataclass
class _AnalyticsRunTracker:
    """Mutable counters collected during one pipeline run."""

    start_time: float = field(default_factory=time.monotonic)
    tool_count: int = 0
    failure_count: int = 0


class _AnalyticsTrackingStepExecutor:
    """Records step and tool analytics metrics around step execution."""

    def __init__(
        self,
        step_executor: StepExecutor,
        analytics_collector: RuntimeAnalyticsCollector,
        *,
        execution_id: str,
        tracker: _AnalyticsRunTracker,
    ) -> None:
        self._step_executor = step_executor
        self._analytics_collector = analytics_collector
        self._execution_id = execution_id
        self._tracker = tracker

    def execute_step(
        self,
        step: ExecutionStep,
        context: StepExecutionContext,
    ) -> Any:
        from app.runtime.analytics.models import StepMetric, ToolMetric
        from app.runtime.executor.context_fields import get_tool_definition

        tool_definition = get_tool_definition(context.runtime_context)
        started_at = time.monotonic()
        try:
            output = self._step_executor.execute_step(step, context)
        except Exception as exc:
            duration_ms = int((time.monotonic() - started_at) * 1000)
            resolved_tool = get_tool_definition(context.runtime_context) or tool_definition
            self._tracker.failure_count += 1
            self._analytics_collector.collect_step_metric(
                StepMetric(
                    execution_id=self._execution_id,
                    step_id=step.name,
                    duration_ms=duration_ms,
                    status="FAILED",
                    error=str(exc),
                )
            )
            if resolved_tool is not None:
                self._tracker.tool_count += 1
                self._analytics_collector.collect_tool_metric(
                    ToolMetric(
                        execution_id=self._execution_id,
                        tool_name=resolved_tool.name,
                        duration_ms=duration_ms,
                        status="FAILED",
                        error=str(exc),
                    )
                )
            raise

        duration_ms = int((time.monotonic() - started_at) * 1000)
        resolved_tool = get_tool_definition(context.runtime_context) or tool_definition
        self._analytics_collector.collect_step_metric(
            StepMetric(
                execution_id=self._execution_id,
                step_id=step.name,
                duration_ms=duration_ms,
                status="COMPLETED",
            )
        )
        if resolved_tool is not None:
            self._tracker.tool_count += 1
            self._analytics_collector.collect_tool_metric(
                ToolMetric(
                    execution_id=self._execution_id,
                    tool_name=resolved_tool.name,
                    duration_ms=duration_ms,
                    status="COMPLETED",
                )
            )
        return output


class _AuditTrackingStepExecutor:
    """Records step failure audit events around step execution."""

    def __init__(
        self,
        step_executor: StepExecutor,
        audit_recorder: RuntimeAuditRecorder,
        *,
        execution_id: str,
        agent_id: str,
        fallback_correlation_id: str,
    ) -> None:
        self._step_executor = step_executor
        self._audit_recorder = audit_recorder
        self._execution_id = execution_id
        self._agent_id = agent_id
        self._fallback_correlation_id = fallback_correlation_id

    def _resolve_correlation_id(self, context: StepExecutionContext) -> str:
        correlation = get_correlation_context(context.runtime_context)
        if correlation is not None:
            return correlation.correlation_id
        return self._fallback_correlation_id

    def execute_step(
        self,
        step: ExecutionStep,
        context: StepExecutionContext,
    ) -> Any:
        try:
            return self._step_executor.execute_step(step, context)
        except Exception as exc:
            self._audit_recorder.record_failure_event(
                event_type="step.failed",
                execution_id=self._execution_id,
                agent_id=self._agent_id,
                correlation_id=self._resolve_correlation_id(context),
                action="step.execute",
                resource=step.name,
                error=str(exc),
                metadata={"step_type": step.step_type},
            )
            raise


class _EventStreamTrackingStepExecutor:
    """Publishes step lifecycle events to the runtime event stream."""

    def __init__(
        self,
        step_executor: StepExecutor,
        event_publisher: EventPublisher,
        *,
        execution_id: str,
        tracker: _EventStreamRunTracker,
        fallback_correlation_id: str,
    ) -> None:
        self._step_executor = step_executor
        self._event_publisher = event_publisher
        self._execution_id = execution_id
        self._tracker = tracker
        self._fallback_correlation_id = fallback_correlation_id

    def _resolve_correlation_id(self, context: StepExecutionContext) -> str:
        correlation = get_correlation_context(context.runtime_context)
        if correlation is not None:
            return correlation.correlation_id
        return self._fallback_correlation_id

    def execute_step(
        self,
        step: ExecutionStep,
        context: StepExecutionContext,
    ) -> Any:
        from app.runtime.event_stream.models import STEP_COMPLETE, STEP_FAILED, STEP_START

        correlation_id = self._resolve_correlation_id(context)
        _publish_stream_envelope(
            self._event_publisher,
            self._tracker,
            event_type=STEP_START,
            execution_id=self._execution_id,
            correlation_id=correlation_id,
            payload={"step_id": step.name, "step_type": step.step_type},
        )
        try:
            output = self._step_executor.execute_step(step, context)
        except Exception as exc:
            _publish_stream_envelope(
                self._event_publisher,
                self._tracker,
                event_type=STEP_FAILED,
                execution_id=self._execution_id,
                correlation_id=correlation_id,
                payload={
                    "step_id": step.name,
                    "step_type": step.step_type,
                    "error": str(exc),
                },
            )
            raise

        _publish_stream_envelope(
            self._event_publisher,
            self._tracker,
            event_type=STEP_COMPLETE,
            execution_id=self._execution_id,
            correlation_id=correlation_id,
            payload={"step_id": step.name, "step_type": step.step_type},
        )
        return output


class _StateTrackingStepExecutor:
    """Updates execution state before each planned step runs."""

    def __init__(
        self,
        step_executor: StepExecutor,
        state_store: ExecutionStateStore,
        execution_id: str,
    ) -> None:
        self._step_executor = step_executor
        self._state_store = state_store
        self._execution_id = execution_id

    def execute_step(
        self,
        step: ExecutionStep,
        context: StepExecutionContext,
    ) -> Any:
        existing = self._state_store.get(self._execution_id)
        if existing is not None:
            self._state_store.update(
                existing.with_updates(current_step=step.name)
            )
        return self._step_executor.execute_step(step, context)


class _CheckpointTrackingStepExecutor:
    """Persists step-level checkpoints around each planned step execution."""

    def __init__(
        self,
        step_executor: StepExecutor,
        checkpoint_manager: CheckpointManager,
        *,
        execution_id: str,
        plan_id: str,
        agent_id: str,
        task: str,
        completed_steps: list[str],
    ) -> None:
        self._step_executor = step_executor
        self._checkpoint_manager = checkpoint_manager
        self._execution_id = execution_id
        self._plan_id = plan_id
        self._agent_id = agent_id
        self._task = task
        self._completed_steps = completed_steps

    def _snapshot(self, *, current_step: str | None, status: str) -> dict[str, Any]:
        return {
            "agent_id": self._agent_id,
            "task": self._task,
            "plan_id": self._plan_id,
            "status": status,
            "current_step": current_step,
            "completed_steps": list(self._completed_steps),
        }

    def execute_step(
        self,
        step: ExecutionStep,
        context: StepExecutionContext,
    ) -> Any:
        self._checkpoint_manager.save_checkpoint(
            execution_id=self._execution_id,
            plan_id=self._plan_id,
            step_id=step.name,
            state_snapshot=self._snapshot(current_step=step.name, status="RUNNING"),
            metadata={"phase": "before_step"},
        )
        try:
            output = self._step_executor.execute_step(step, context)
        except Exception as exc:
            self._checkpoint_manager.save_checkpoint(
                execution_id=self._execution_id,
                plan_id=self._plan_id,
                step_id=step.name,
                state_snapshot=self._snapshot(current_step=step.name, status="FAILED"),
                metadata={"phase": "step_failed", "error_message": str(exc)},
            )
            raise
        self._completed_steps.append(step.name)
        self._checkpoint_manager.save_checkpoint(
            execution_id=self._execution_id,
            plan_id=self._plan_id,
            step_id=step.name,
            state_snapshot=self._snapshot(current_step=step.name, status="RUNNING"),
            metadata={"phase": "after_step"},
        )
        return output


class _PipelineStepExecutor:
    """Adapts the runtime execution pipeline to the ``StepExecutor`` protocol."""

    def __init__(
        self,
        execution_pipeline: ExecutionPipeline,
        task: str,
        correlation_manager: RuntimeCorrelationManager | None = None,
    ) -> None:
        self._execution_pipeline = execution_pipeline
        self._task = task
        self._correlation_manager = correlation_manager

    def execute_step(
        self,
        step: ExecutionStep,
        context: StepExecutionContext,
    ) -> Any:
        if step.step_type == "execute":
            step_task = str(step.metadata.get("task", context.task))
            parent_correlation = get_correlation_context(context.runtime_context)
            tool_correlation: CorrelationContext | None = None
            if self._correlation_manager is not None and parent_correlation is not None:
                tool_correlation = self._correlation_manager.create_child_context(
                    parent_correlation
                )
                attach_correlation_context(context.runtime_context, tool_correlation)
            try:
                return self._execution_pipeline.run(context.runtime_context, step_task)
            finally:
                if tool_correlation is not None and self._correlation_manager is not None:
                    self._correlation_manager.close_context(tool_correlation.span_id)
                    if parent_correlation is not None:
                        attach_correlation_context(
                            context.runtime_context,
                            parent_correlation,
                        )
        raise RuntimeError(f"Unsupported planned step type: {step.step_type}")


class _CorrelationStepExecutor:
    """Creates step-level child correlation contexts during plan execution."""

    def __init__(
        self,
        step_executor: StepExecutor,
        correlation_manager: RuntimeCorrelationManager,
        execution_correlation: CorrelationContext,
        runtime_context: RuntimeContext,
    ) -> None:
        self._step_executor = step_executor
        self._correlation_manager = correlation_manager
        self._execution_correlation = execution_correlation
        self._runtime_context = runtime_context

    def execute_step(
        self,
        step: ExecutionStep,
        context: StepExecutionContext,
    ) -> Any:
        step_correlation = self._correlation_manager.create_child_context(
            self._execution_correlation
        )
        attach_correlation_context(self._runtime_context, step_correlation)
        try:
            return self._step_executor.execute_step(step, context)
        finally:
            self._correlation_manager.close_context(step_correlation.span_id)
            attach_correlation_context(self._runtime_context, self._execution_correlation)


class AgentExecutionPipeline:
    """Orchestrates agent execution steps through the existing runtime toolchain."""

    def __init__(
        self,
        production_runtime: ProductionRuntime,
        planner: Planner | None = None,
        strategy: ExecutionStrategy | None = None,
        state_store: ExecutionStateStore | None = None,
        checkpoint_store: CheckpointStore | None = None,
        memory_manager: MemoryContextManager | None = None,
        runtime_context_manager: RuntimeContextManager | None = None,
        correlation_manager: RuntimeCorrelationManager | None = None,
        analytics_collector: RuntimeAnalyticsCollector | None = None,
        event_publisher: EventPublisher | None = None,
        audit_recorder: RuntimeAuditRecorder | None = None,
    ) -> None:
        self._production_runtime = production_runtime
        self._planner = planner or DefaultPlanner()
        self._strategy = strategy or SequentialExecutionStrategy()
        self._state_store = state_store
        self._checkpoint_manager = (
            CheckpointManager(checkpoint_store) if checkpoint_store is not None else None
        )
        self._memory_manager = memory_manager
        self._runtime_context_manager = runtime_context_manager
        self._correlation_manager = correlation_manager
        self._analytics_collector = analytics_collector
        self._event_publisher = event_publisher
        self._audit_recorder = audit_recorder
        self._execution_pipeline = ExecutionPipeline(
            tool_execution_engine=production_runtime.tool_execution_engine,
        )

    def _record_execution_analytics(
        self,
        *,
        tracker: _AnalyticsRunTracker,
        execution_id: str,
        agent_id: str,
        status: str,
        step_count: int,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        if self._analytics_collector is None:
            return
        from app.runtime.analytics.models import ExecutionMetric

        duration_ms = int((time.monotonic() - tracker.start_time) * 1000)
        self._analytics_collector.collect_execution_metric(
            ExecutionMetric(
                execution_id=execution_id,
                agent_id=agent_id,
                duration_ms=duration_ms,
                status="COMPLETED" if status == "COMPLETED" else "FAILED",
                step_count=step_count,
                tool_count=tracker.tool_count,
                failure_count=tracker.failure_count,
                metadata=dict(metadata or {}),
            )
        )

    def _publish_execution_stream_event(
        self,
        *,
        tracker: _EventStreamRunTracker,
        event_type: str,
        execution_id: str,
        correlation_id: str,
        payload: dict[str, Any] | None = None,
    ) -> None:
        if self._event_publisher is None:
            return
        _publish_stream_envelope(
            self._event_publisher,
            tracker,
            event_type=event_type,
            execution_id=execution_id,
            correlation_id=correlation_id,
            payload=payload,
        )

    def _record_execution_audit(
        self,
        *,
        event_type: str,
        execution_id: str,
        agent_id: str,
        correlation_id: str,
        metadata: dict[str, Any] | None = None,
        decision: str = "ALLOW",
        severity: str = "INFO",
    ) -> None:
        if self._audit_recorder is None:
            return
        self._audit_recorder.record_execution_event(
            event_type=event_type,
            execution_id=execution_id,
            agent_id=agent_id,
            correlation_id=correlation_id,
            actor=agent_id,
            action=event_type,
            decision=decision,  # type: ignore[arg-type]
            severity=severity,  # type: ignore[arg-type]
            metadata=metadata,
        )

    def _record_execution_failure_audit(
        self,
        *,
        event_type: str,
        execution_id: str,
        agent_id: str,
        correlation_id: str,
        error: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        if self._audit_recorder is None:
            return
        self._audit_recorder.record_failure_event(
            event_type=event_type,
            execution_id=execution_id,
            agent_id=agent_id,
            correlation_id=correlation_id,
            actor=agent_id,
            action=event_type,
            error=error,
            metadata=metadata,
        )

    def _create_running_state(
        self,
        *,
        execution_id: str,
        agent_id: str,
        plan_id: str,
        task: str,
    ) -> None:
        if self._state_store is None:
            return
        existing = self._state_store.get(execution_id)
        if existing is not None:
            self._state_store.update(
                existing.with_updates(
                    agent_id=agent_id,
                    plan_id=plan_id,
                    status="RUNNING",
                    current_step=None,
                    metadata={**existing.metadata, "task": task},
                )
            )
            return
        self._state_store.create(
            ExecutionState(
                execution_id=execution_id,
                agent_id=agent_id,
                plan_id=plan_id,
                status="RUNNING",
                current_step=None,
                metadata={"task": task},
            )
        )

    def _finalize_state(
        self,
        execution_id: str,
        *,
        status: str,
        current_step: str | None = None,
        error: str | None = None,
    ) -> None:
        if self._state_store is None:
            return
        existing = self._state_store.get(execution_id)
        if existing is None:
            return
        metadata = dict(existing.metadata)
        if error is not None:
            metadata["error_message"] = error
        self._state_store.update(
            existing.with_updates(
                status=status,
                current_step=current_step,
                metadata=metadata,
            )
        )

    def _save_execution_checkpoint(
        self,
        *,
        execution_id: str,
        plan_id: str,
        agent_id: str,
        task: str,
        status: str,
        current_step: str | None = None,
        completed_steps: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Checkpoint | None:
        if self._checkpoint_manager is None:
            return None
        return self._checkpoint_manager.save_checkpoint(
            execution_id=execution_id,
            plan_id=plan_id,
            step_id=current_step,
            state_snapshot={
                "agent_id": agent_id,
                "task": task,
                "plan_id": plan_id,
                "status": status,
                "current_step": current_step,
                "completed_steps": list(completed_steps or []),
            },
            metadata=dict(metadata or {}),
        )

    def _load_memory_context(
        self,
        *,
        execution_id: str,
        agent_id: str,
    ) -> MemoryContext | None:
        if self._memory_manager is None:
            return None
        return self._memory_manager.load_context(
            execution_id=execution_id,
            agent_id=agent_id,
        )

    def _finalize_memory_context(
        self,
        memory_context: MemoryContext | None,
        *,
        task: str,
        plan_id: str,
        status: str,
        output: Any | None = None,
        error: str | None = None,
    ) -> MemoryContext | None:
        if self._memory_manager is None or memory_context is None:
            return memory_context
        updates: dict[str, Any] = {
            "task": task,
            "plan_id": plan_id,
            "status": status,
            "output": output,
        }
        if error is not None:
            updates["error_message"] = error
        updated = self._memory_manager.update_context(memory_context, updates)
        self._memory_manager.persist_context(updated)
        return updated

    def _create_aggregated_context(
        self,
        *,
        execution_id: str,
        agent_id: str,
        task: str,
    ) -> None:
        if self._runtime_context_manager is None:
            return
        self._runtime_context_manager.create_context(
            execution_id=execution_id,
            agent_id=agent_id,
            metadata={"task": task},
        )

    def _sync_aggregated_state(self, execution_id: str) -> None:
        if self._runtime_context_manager is None or self._state_store is None:
            return
        state = self._state_store.get(execution_id)
        if state is not None:
            self._runtime_context_manager.update_state(execution_id, state)

    def _sync_aggregated_checkpoint(
        self,
        execution_id: str,
        checkpoint: Checkpoint | None,
    ) -> None:
        if self._runtime_context_manager is None or checkpoint is None:
            return
        self._runtime_context_manager.update_checkpoint(execution_id, checkpoint)

    def _sync_aggregated_memory(
        self,
        execution_id: str,
        memory_context: MemoryContext | None,
    ) -> None:
        if self._runtime_context_manager is None or memory_context is None:
            return
        self._runtime_context_manager.update_memory(execution_id, memory_context)

    def _finalize_aggregated_context(self, execution_id: str) -> None:
        if self._runtime_context_manager is None:
            return
        self._runtime_context_manager.snapshot(execution_id)

    def run(
        self,
        agent_definition: AgentDefinition,
        task: str,
        context: ExecutionContext,
        *,
        resume_from_checkpoint_id: str | None = None,
    ) -> AgentExecutionResult:
        """Run the agent execution pipeline and return a structured result."""
        completed_steps: list[str] = []
        resume_checkpoint = None
        if resume_from_checkpoint_id is not None:
            if self._checkpoint_manager is None:
                raise RuntimeError("checkpoint store is required for resume")
            resume_checkpoint = self._checkpoint_manager.get_checkpoint(
                resume_from_checkpoint_id
            )
            if resume_checkpoint is None:
                raise KeyError(f"Checkpoint not found: {resume_from_checkpoint_id}")
            completed_steps = list(
                resume_checkpoint.state_snapshot.get("completed_steps", [])
            )
            task = str(resume_checkpoint.state_snapshot.get("task", task))
        execution_correlation: CorrelationContext | None = None
        steps: list[ExecutionStep] = []
        prepare_step = create_step("prepare", "agent.prepare")
        steps.append(prepare_step)

        session = start_session(
            agent_definition,
            context,
            task=task,
            tenant_id=context.tenant_id,
            user_id=context.user_id,
            execution_id=context.execution_id or uuid.uuid4().hex,
        )
        runtime_context = RuntimeContext(
            execution_id=session.execution_id,
            agent_id=agent_definition.id,
            metadata=dict(context.metadata),
        )
        attach_execution_context(runtime_context, context)
        complete_step(prepare_step)

        if self._correlation_manager is not None:
            execution_correlation = self._correlation_manager.create_execution_context(
                session.execution_id
            )
            attach_correlation_context(runtime_context, execution_correlation)

        try:
            return self._run_with_correlation(
                agent_definition=agent_definition,
                task=task,
                context=context,
                session=session,
                runtime_context=runtime_context,
                steps=steps,
                resume_checkpoint=resume_checkpoint,
                completed_steps=completed_steps,
                execution_correlation=execution_correlation,
            )
        finally:
            if self._correlation_manager is not None and execution_correlation is not None:
                self._correlation_manager.close_context(execution_correlation.span_id)

    def _run_with_correlation(
        self,
        *,
        agent_definition: AgentDefinition,
        task: str,
        context: ExecutionContext,
        session: Any,
        runtime_context: RuntimeContext,
        steps: list[ExecutionStep],
        resume_checkpoint: Any,
        completed_steps: list[str],
        execution_correlation: CorrelationContext | None,
    ) -> AgentExecutionResult:
        plan = self._planner.create_plan(agent_definition, task, context)
        if resume_checkpoint is not None:
            plan = self._checkpoint_manager.plan_for_resume(plan, resume_checkpoint)
        self._create_aggregated_context(
            execution_id=session.execution_id,
            agent_id=agent_definition.id,
            task=task,
        )
        self._create_running_state(
            execution_id=session.execution_id,
            agent_id=agent_definition.id,
            plan_id=plan.plan_id,
            task=task,
        )
        self._sync_aggregated_state(session.execution_id)
        start_checkpoint = self._save_execution_checkpoint(
            execution_id=session.execution_id,
            plan_id=plan.plan_id,
            agent_id=agent_definition.id,
            task=task,
            status="RUNNING",
            completed_steps=completed_steps,
            metadata={"phase": "execution_start"},
        )
        self._sync_aggregated_checkpoint(session.execution_id, start_checkpoint)
        memory_context = self._load_memory_context(
            execution_id=session.execution_id,
            agent_id=agent_definition.id,
        )
        self._sync_aggregated_memory(session.execution_id, memory_context)
        step_context = StepExecutionContext(runtime_context=runtime_context, task=task)
        analytics_tracker = _AnalyticsRunTracker()
        stream_tracker = _EventStreamRunTracker()
        correlation_id = (
            execution_correlation.correlation_id
            if execution_correlation is not None
            else session.execution_id
        )
        from app.runtime.event_stream.models import EXECUTION_START

        self._publish_execution_stream_event(
            tracker=stream_tracker,
            event_type=EXECUTION_START,
            execution_id=session.execution_id,
            correlation_id=correlation_id,
            payload={
                "agent_id": agent_definition.id,
                "task": task,
                "plan_id": plan.plan_id,
            },
        )
        self._record_execution_audit(
            event_type=EXECUTION_START,
            execution_id=session.execution_id,
            agent_id=agent_definition.id,
            correlation_id=correlation_id,
            metadata={
                "agent_id": agent_definition.id,
                "task": task,
                "plan_id": plan.plan_id,
            },
        )
        step_executor = _PipelineStepExecutor(
            self._execution_pipeline,
            task,
            self._correlation_manager,
        )
        if self._event_publisher is not None:
            step_executor = _EventStreamTrackingStepExecutor(
                step_executor,
                self._event_publisher,
                execution_id=session.execution_id,
                tracker=stream_tracker,
                fallback_correlation_id=correlation_id,
            )
        if self._audit_recorder is not None:
            step_executor = _AuditTrackingStepExecutor(
                step_executor,
                self._audit_recorder,
                execution_id=session.execution_id,
                agent_id=agent_definition.id,
                fallback_correlation_id=correlation_id,
            )
        if self._analytics_collector is not None:
            step_executor = _AnalyticsTrackingStepExecutor(
                step_executor,
                self._analytics_collector,
                execution_id=session.execution_id,
                tracker=analytics_tracker,
            )
        if self._state_store is not None:
            step_executor = _StateTrackingStepExecutor(
                step_executor,
                self._state_store,
                session.execution_id,
            )
        if self._checkpoint_manager is not None:
            step_executor = _CheckpointTrackingStepExecutor(
                step_executor,
                self._checkpoint_manager,
                execution_id=session.execution_id,
                plan_id=plan.plan_id,
                agent_id=agent_definition.id,
                task=task,
                completed_steps=completed_steps,
            )
        if self._correlation_manager is not None and execution_correlation is not None:
            step_executor = _CorrelationStepExecutor(
                step_executor,
                self._correlation_manager,
                execution_correlation,
                runtime_context,
            )
        strategy_result = self._strategy.execute_plan(
            plan,
            step_context,
            step_executor,
        )

        for outcome in strategy_result.step_results:
            steps.append(outcome.step)

        if strategy_result.status == "COMPLETED":
            output = (
                strategy_result.step_results[-1].output
                if strategy_result.step_results
                else None
            )
            complete_session(
                session,
                context,
                agent_definition=agent_definition,
                output=output,
            )
            self._finalize_state(
                session.execution_id,
                status="COMPLETED",
                current_step=None,
            )
            self._sync_aggregated_state(session.execution_id)
            completion_checkpoint = self._save_execution_checkpoint(
                execution_id=session.execution_id,
                plan_id=plan.plan_id,
                agent_id=agent_definition.id,
                task=task,
                status="COMPLETED",
                completed_steps=completed_steps,
                metadata={"phase": "execution_completed"},
            )
            self._sync_aggregated_checkpoint(session.execution_id, completion_checkpoint)
            memory_context = self._finalize_memory_context(
                memory_context,
                task=task,
                plan_id=plan.plan_id,
                status="COMPLETED",
                output=output,
            )
            self._sync_aggregated_memory(session.execution_id, memory_context)
            self._finalize_aggregated_context(session.execution_id)
            self._record_execution_analytics(
                tracker=analytics_tracker,
                execution_id=session.execution_id,
                agent_id=agent_definition.id,
                status="COMPLETED",
                step_count=len(strategy_result.step_results),
                metadata={"task": task, "plan_id": plan.plan_id},
            )
            from app.runtime.event_stream.models import EXECUTION_COMPLETE

            self._publish_execution_stream_event(
                tracker=stream_tracker,
                event_type=EXECUTION_COMPLETE,
                execution_id=session.execution_id,
                correlation_id=correlation_id,
                payload={
                    "agent_id": agent_definition.id,
                    "task": task,
                    "plan_id": plan.plan_id,
                    "step_count": len(strategy_result.step_results),
                },
            )
            return AgentExecutionResult(
                execution_id=session.execution_id,
                agent_id=agent_definition.id,
                status="COMPLETED",
                output=output,
                steps=steps,
                metadata={"task": task, "plan_id": plan.plan_id},
            )

        fail_session(
            session,
            context,
            agent_definition=agent_definition,
            error=strategy_result.error or "execution strategy failed",
        )
        failed_step = (
            strategy_result.step_results[-1].step.name
            if strategy_result.step_results
            else None
        )
        self._finalize_state(
            session.execution_id,
            status="FAILED",
            current_step=failed_step,
            error=strategy_result.error or "execution strategy failed",
        )
        self._sync_aggregated_state(session.execution_id)
        failure_checkpoint = self._save_execution_checkpoint(
            execution_id=session.execution_id,
            plan_id=plan.plan_id,
            agent_id=agent_definition.id,
            task=task,
            status="FAILED",
            current_step=failed_step,
            completed_steps=completed_steps,
            metadata={
                "phase": "execution_failed",
                "error_message": strategy_result.error or "execution strategy failed",
            },
        )
        self._sync_aggregated_checkpoint(session.execution_id, failure_checkpoint)
        memory_context = self._finalize_memory_context(
            memory_context,
            task=task,
            plan_id=plan.plan_id,
            status="FAILED",
            error=strategy_result.error or "execution strategy failed",
        )
        self._sync_aggregated_memory(session.execution_id, memory_context)
        self._finalize_aggregated_context(session.execution_id)
        self._record_execution_analytics(
            tracker=analytics_tracker,
            execution_id=session.execution_id,
            agent_id=agent_definition.id,
            status="FAILED",
            step_count=len(strategy_result.step_results),
            metadata={
                "task": task,
                "plan_id": plan.plan_id,
                "error_message": strategy_result.error,
            },
        )
        from app.runtime.event_stream.models import EXECUTION_FAILED

        self._publish_execution_stream_event(
            tracker=stream_tracker,
            event_type=EXECUTION_FAILED,
            execution_id=session.execution_id,
            correlation_id=correlation_id,
            payload={
                "agent_id": agent_definition.id,
                "task": task,
                "plan_id": plan.plan_id,
                "error": strategy_result.error or "execution strategy failed",
            },
        )
        self._record_execution_failure_audit(
            event_type=EXECUTION_FAILED,
            execution_id=session.execution_id,
            agent_id=agent_definition.id,
            correlation_id=correlation_id,
            error=strategy_result.error or "execution strategy failed",
            metadata={
                "agent_id": agent_definition.id,
                "task": task,
                "plan_id": plan.plan_id,
            },
        )
        return AgentExecutionResult(
            execution_id=session.execution_id,
            agent_id=agent_definition.id,
            status="FAILED",
            output=None,
            steps=steps,
            metadata={
                "task": task,
                "plan_id": plan.plan_id,
                "error_message": strategy_result.error,
            },
        )
