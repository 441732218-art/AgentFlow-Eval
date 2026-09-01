# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Runtime service boundary between API adapters and ``AgentExecutor``."""

from __future__ import annotations

from app.runtime.context import RuntimeContext
from app.runtime.execution import ExecutionRecord, ExecutionStore, InMemoryExecutionStore
from app.runtime.executor import AgentExecutor, ExecutionResult
from app.runtime.service.dto import ExecutionResponseDTO


class RuntimeService:
    """Orchestrates execution and persists lifecycle records via ``ExecutionStore``."""

    def __init__(
        self,
        executor: AgentExecutor | None = None,
        execution_store: ExecutionStore | None = None,
    ) -> None:
        self.executor = executor or AgentExecutor()
        self.execution_store = execution_store or InMemoryExecutionStore()

    def execute(
        self,
        agent_id: str,
        task: str,
        context: RuntimeContext | None = None,
    ) -> ExecutionResponseDTO:
        """Run an agent task, persist ``ExecutionRecord``, return service DTO."""
        result = self.executor.execute(agent_id=agent_id, task=task, context=context)
        record = self._to_record(result)
        self.execution_store.save(record)
        return self._to_dto(result)

    def get_execution(self, execution_id: str) -> ExecutionRecord | None:
        """Return a persisted execution record."""
        return self.execution_store.get(execution_id)

    def _to_record(self, result: ExecutionResult) -> ExecutionRecord:
        return ExecutionRecord(
            execution_id=result.execution_id,
            agent_id=result.agent_id,
            status=result.status,
            output=result.output,
            error=result.error,
            trace_reference=result.execution_id,
        )

    def _to_dto(self, result: ExecutionResult) -> ExecutionResponseDTO:
        return ExecutionResponseDTO(
            execution_id=result.execution_id,
            status=result.status,
            output=result.output,
            error=result.error,
        )
