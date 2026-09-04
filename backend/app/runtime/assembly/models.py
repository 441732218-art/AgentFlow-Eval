# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Runtime assembly configuration and result models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.runtime.agent.runtime import AgentRuntime
    from app.runtime.analytics.collector import RuntimeAnalyticsCollector
    from app.runtime.audit.recorder import RuntimeAuditRecorder
    from app.runtime.bootstrap.config import RuntimeConfig
    from app.runtime.bootstrap.factory import ProductionRuntime
    from app.runtime.checkpoint.store import CheckpointStore
    from app.runtime.context.manager import RuntimeContextManager
    from app.runtime.context_memory.manager import MemoryContextManager
    from app.runtime.correlation.manager import RuntimeCorrelationManager
    from app.runtime.event_stream.publisher import EventPublisher
    from app.runtime.evidence.collector import RuntimeEvidenceCollector
    from app.runtime.governance.configuration.registry import GovernanceConfigurationRegistry
    from app.runtime.governance.evidence_correlation.store import EvidenceCorrelationStore
    from app.runtime.governance.hooks.adapter import GovernanceRuntimeHookAdapter
    from app.runtime.governance.lifecycle.manager import GovernanceLifecycleManager
    from app.runtime.governance.orchestrator.orchestrator import GovernanceRuntimeOrchestrator
    from app.runtime.governance.runtime_adapter.adapter import GovernanceRuntimeDecisionAdapter
    from app.runtime.governance.routing.router import GovernanceDecisionRouter
    from app.runtime.governance.snapshot.store import SnapshotStore
    from app.runtime.governance.tool_hooks.adapter import ToolLifecycleGovernanceAdapter
    from app.runtime.hooks.manager import RuntimeHookManager
    from app.runtime.permissions.evaluator import PermissionEvaluator
    from app.runtime.pipeline.agent_pipeline import AgentExecutionPipeline
    from app.runtime.registry.registry import AgentRegistry
    from app.runtime.state.store import ExecutionStateStore
    from app.runtime.tool_registry.registry import ToolRegistry


@dataclass(frozen=True)
class RuntimeProfile:
    """Immutable feature profile for runtime dependency composition."""

    name: str
    environment: str
    enable_governance: bool = True
    enable_observation: bool = True
    enable_audit: bool = True
    enable_agent_registry: bool = True
    enable_tool_registry: bool = True
    enable_permission_evaluator: bool = True
    enable_execution_state: bool = True
    enable_checkpoint: bool = True
    enable_memory_context: bool = True
    enable_runtime_context: bool = True
    enable_correlation: bool = True
    enable_analytics: bool = False
    enable_event_stream: bool = False
    enable_audit_recorder: bool = False
    enable_evidence_collector: bool = False
    enable_governance_lifecycle: bool = False
    enable_governance_hook_adapter: bool = False
    enable_tool_governance_hook: bool = False
    blocked_tools: tuple[str, ...] = ()


@dataclass
class RuntimeAssemblyConfig:
    """Optional overrides applied during runtime assembly."""

    profile: RuntimeProfile | None = None
    runtime_config: RuntimeConfig | None = None
    blocked_tools: list[str] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class RuntimeAssembly:
    """Composed runtime dependencies returned by ``RuntimeAssembler``."""

    profile: RuntimeProfile
    production_runtime: ProductionRuntime
    agent_runtime: AgentRuntime
    agent_pipeline: AgentExecutionPipeline
    agent_registry: AgentRegistry | None = None
    tool_registry: ToolRegistry | None = None
    permission_evaluator: PermissionEvaluator | None = None
    state_store: ExecutionStateStore | None = None
    checkpoint_store: CheckpointStore | None = None
    memory_manager: MemoryContextManager | None = None
    runtime_context_manager: RuntimeContextManager | None = None
    correlation_manager: RuntimeCorrelationManager | None = None
    analytics_collector: RuntimeAnalyticsCollector | None = None
    event_publisher: EventPublisher | None = None
    audit_recorder: RuntimeAuditRecorder | None = None
    evidence_collector: RuntimeEvidenceCollector | None = None
    governance_lifecycle_manager: GovernanceLifecycleManager | None = None
    governance_hook_adapter: GovernanceRuntimeHookAdapter | None = None
    tool_governance_adapter: ToolLifecycleGovernanceAdapter | None = None
    runtime_hook_manager: RuntimeHookManager | None = None
    governance_decision_router: GovernanceDecisionRouter | None = None
    governance_orchestrator: GovernanceRuntimeOrchestrator | None = None
    governance_configuration_registry: GovernanceConfigurationRegistry | None = None
    governance_snapshot_store: SnapshotStore | None = None
    governance_evidence_correlation_store: EvidenceCorrelationStore | None = None
    governance_runtime_decision_adapter: GovernanceRuntimeDecisionAdapter | None = None
