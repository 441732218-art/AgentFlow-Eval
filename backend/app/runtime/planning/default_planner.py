# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Default placeholder planner for agent execution."""

from __future__ import annotations

import uuid

from app.runtime.agent.models import AgentDefinition
from app.runtime.executor.execution_context import ExecutionContext
from app.runtime.pipeline.models import ExecutionStep
from app.runtime.planning.models import ExecutionPlan


class DefaultPlanner:
    """Placeholder planner that emits a single generic execute step."""

    def create_plan(
        self,
        agent_definition: AgentDefinition,
        task: str,
        context: ExecutionContext,
    ) -> ExecutionPlan:
        _ = context
        return ExecutionPlan(
            plan_id=uuid.uuid4().hex,
            agent_id=agent_definition.id,
            steps=(
                ExecutionStep(
                    name="execute",
                    step_type="execute",
                    status="PENDING",
                    metadata={"task": task},
                ),
            ),
            metadata={"planner": "default"},
        )
