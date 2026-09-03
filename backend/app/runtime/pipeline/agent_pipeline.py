# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Agent execution pipeline orchestrating runtime steps."""

from __future__ import annotations

import uuid
from typing import Any

from app.runtime.agent.lifecycle import complete_session, fail_session, start_session
from app.runtime.agent.models import AgentDefinition
from app.runtime.bootstrap.factory import ProductionRuntime
from app.runtime.checkpoint.manager import CheckpointManager
from app.runtime.checkpoint.store import CheckpointStore
from app.runtime.context import RuntimeContext
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

    def __init__(self, execution_pipeline: ExecutionPipeline, task: str) -> None:
        self._execution_pipeline = execution_pipeline
        self._task = task

    def execute_step(
        self,
        step: ExecutionStep,
        context: StepExecutionContext,
    ) -> Any:
        if step.step_type == "execute":
            step_task = str(step.metadata.get("task", context.task))
            return self._execution_pipeline.run(context.runtime_context, step_task)
        raise RuntimeError(f"Unsupported planned step type: {step.step_type}")


class AgentExecutionPipeline:
    """Orchestrates agent execution steps through the existing runtime toolchain."""

    def __init__(
        self,
        production_runtime: ProductionRuntime,
        planner: Planner | None = None,
        strategy: ExecutionStrategy | None = None,
        state_store: ExecutionStateStore | None = None,
        checkpoint_store: CheckpointStore | None = None,
    ) -> None:
        self._production_runtime = production_runtime
        self._planner = planner or DefaultPlanner()
        self._strategy = strategy or SequentialExecutionStrategy()
        self._state_store = state_store
        self._checkpoint_manager = (
            CheckpointManager(checkpoint_store) if checkpoint_store is not None else None
        )
        self._execution_pipeline = ExecutionPipeline(
            tool_execution_engine=production_runtime.tool_execution_engine,
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
    ) -> None:
        if self._checkpoint_manager is None:
            return
        self._checkpoint_manager.save_checkpoint(
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

        plan = self._planner.create_plan(agent_definition, task, context)
        if resume_checkpoint is not None:
            plan = self._checkpoint_manager.plan_for_resume(plan, resume_checkpoint)
        self._create_running_state(
            execution_id=session.execution_id,
            agent_id=agent_definition.id,
            plan_id=plan.plan_id,
            task=task,
        )
        self._save_execution_checkpoint(
            execution_id=session.execution_id,
            plan_id=plan.plan_id,
            agent_id=agent_definition.id,
            task=task,
            status="RUNNING",
            completed_steps=completed_steps,
            metadata={"phase": "execution_start"},
        )
        step_context = StepExecutionContext(runtime_context=runtime_context, task=task)
        step_executor = _PipelineStepExecutor(self._execution_pipeline, task)
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
            self._save_execution_checkpoint(
                execution_id=session.execution_id,
                plan_id=plan.plan_id,
                agent_id=agent_definition.id,
                task=task,
                status="COMPLETED",
                completed_steps=completed_steps,
                metadata={"phase": "execution_completed"},
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
        self._save_execution_checkpoint(
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
