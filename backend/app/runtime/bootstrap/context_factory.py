# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""ExecutionContext factory for assembled production runtime."""

from __future__ import annotations

from typing import Any

from app.runtime.bootstrap.factory import ProductionRuntime
from app.runtime.executor.execution_context import ExecutionContext


def create_execution_context(
    runtime: ProductionRuntime,
    *,
    execution_id: str,
    agent_id: str | None = None,
    tenant_id: str | None = None,
    user_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> ExecutionContext:
    """Create an ``ExecutionContext`` wired to a ``ProductionRuntime`` instance."""
    enable_governance = runtime.config.enable_governance
    return ExecutionContext(
        execution_id=execution_id,
        agent_id=agent_id,
        tenant_id=tenant_id,
        user_id=user_id,
        metadata=dict(metadata or {}),
        observation_collector=runtime.observation_collector,
        event_publisher=runtime.event_publisher,
        audit_store=runtime.audit_store,
        policy_engine=runtime.policy_engine if enable_governance else None,
        governance_lifecycle=runtime.governance_lifecycle,
    )
