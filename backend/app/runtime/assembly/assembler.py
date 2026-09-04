# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Runtime dependency composition assembler."""

from __future__ import annotations

from app.runtime.agent.runtime import AgentRuntime
from app.runtime.assembly.models import RuntimeAssembly, RuntimeAssemblyConfig, RuntimeProfile
from app.runtime.assembly.profiles import PRODUCTION_PROFILE, get_profile
from app.runtime.bootstrap.config import RuntimeConfig
from app.runtime.bootstrap.factory import ProductionRuntime, create_production_runtime
from app.runtime.checkpoint.memory_store import InMemoryCheckpointStore
from app.runtime.context.manager import RuntimeContextManager
from app.runtime.context_memory.manager import MemoryContextManager
from app.runtime.context_memory.memory_store import InMemoryMemoryStore
from app.runtime.correlation.manager import RuntimeCorrelationManager
from app.runtime.permissions.evaluator import PermissionEvaluator
from app.runtime.pipeline.agent_pipeline import AgentExecutionPipeline
from app.runtime.policy.engine import InMemoryPolicyEngine
from app.runtime.registry.memory_registry import InMemoryAgentRegistry
from app.runtime.state.memory_store import InMemoryExecutionStateStore
from app.runtime.tool_registry.memory_registry import InMemoryToolRegistry


class RuntimeAssembler:
    """Compose existing runtime kernel components into a production-ready stack."""

    def assemble(self, config: RuntimeAssemblyConfig | None = None) -> RuntimeAssembly:
        """Assemble runtime dependencies according to a profile and optional overrides."""
        resolved = config or RuntimeAssemblyConfig()
        profile = resolved.profile or PRODUCTION_PROFILE
        blocked_tools = list(
            resolved.blocked_tools
            if resolved.blocked_tools is not None
            else profile.blocked_tools
        )

        runtime_config = resolved.runtime_config or RuntimeConfig(
            environment=profile.environment,
            enable_governance=profile.enable_governance,
            enable_observation=profile.enable_observation,
            enable_audit=profile.enable_audit,
        )
        production_runtime = create_production_runtime(runtime_config)
        if blocked_tools:
            production_runtime.policy_engine = InMemoryPolicyEngine(
                blocked_tools=blocked_tools
            )

        agent_registry = InMemoryAgentRegistry() if profile.enable_agent_registry else None
        tool_registry = InMemoryToolRegistry() if profile.enable_tool_registry else None
        permission_evaluator = self._build_permission_evaluator(
            profile,
            production_runtime,
        )
        state_store = (
            InMemoryExecutionStateStore() if profile.enable_execution_state else None
        )
        checkpoint_store = (
            InMemoryCheckpointStore() if profile.enable_checkpoint else None
        )
        memory_manager = (
            MemoryContextManager(InMemoryMemoryStore())
            if profile.enable_memory_context
            else None
        )
        runtime_context_manager = (
            RuntimeContextManager() if profile.enable_runtime_context else None
        )
        correlation_manager = (
            RuntimeCorrelationManager() if profile.enable_correlation else None
        )
        analytics_collector = (
            self._build_analytics_collector() if profile.enable_analytics else None
        )
        event_publisher = (
            self._build_event_publisher() if profile.enable_event_stream else None
        )
        audit_recorder = (
            self._build_audit_recorder() if profile.enable_audit_recorder else None
        )
        evidence_collector = (
            self._build_evidence_collector()
            if profile.enable_evidence_collector
            else None
        )
        governance_lifecycle_manager = (
            self._build_governance_lifecycle_manager()
            if profile.enable_governance_lifecycle
            else None
        )
        runtime_hook_manager = None
        governance_hook_adapter = None
        tool_governance_adapter = None
        if (
            profile.enable_governance_hook_adapter
            and governance_lifecycle_manager is not None
        ):
            runtime_hook_manager, governance_hook_adapter = (
                self._build_governance_hook_stack(
                    governance_lifecycle_manager,
                    evidence_collector=evidence_collector,
                )
            )
        if (
            profile.enable_tool_governance_hook
            and governance_lifecycle_manager is not None
            and permission_evaluator is not None
        ):
            runtime_hook_manager, tool_governance_adapter = (
                self._build_tool_governance_hook_stack(
                    governance_lifecycle_manager,
                    permission_evaluator,
                    runtime_hook_manager=runtime_hook_manager,
                    evidence_collector=evidence_collector,
                    audit_recorder=audit_recorder,
                )
            )

        agent_runtime = AgentRuntime(
            production_runtime,
            agent_registry=agent_registry,
            tool_registry=tool_registry,
            permission_evaluator=permission_evaluator,
            audit_recorder=audit_recorder,
        )
        agent_pipeline = AgentExecutionPipeline(
            production_runtime,
            state_store=state_store,
            checkpoint_store=checkpoint_store,
            memory_manager=memory_manager,
            runtime_context_manager=runtime_context_manager,
            correlation_manager=correlation_manager,
            analytics_collector=analytics_collector,
            event_publisher=event_publisher,
            audit_recorder=audit_recorder,
            evidence_collector=evidence_collector,
            runtime_hook_manager=runtime_hook_manager,
        )

        return RuntimeAssembly(
            profile=profile,
            production_runtime=production_runtime,
            agent_runtime=agent_runtime,
            agent_pipeline=agent_pipeline,
            agent_registry=agent_registry,
            tool_registry=tool_registry,
            permission_evaluator=permission_evaluator,
            state_store=state_store,
            checkpoint_store=checkpoint_store,
            memory_manager=memory_manager,
            runtime_context_manager=runtime_context_manager,
            correlation_manager=correlation_manager,
            analytics_collector=analytics_collector,
            event_publisher=event_publisher,
            audit_recorder=audit_recorder,
            evidence_collector=evidence_collector,
            governance_lifecycle_manager=governance_lifecycle_manager,
            governance_hook_adapter=governance_hook_adapter,
            tool_governance_adapter=tool_governance_adapter,
            runtime_hook_manager=runtime_hook_manager,
        )

    @staticmethod
    def _build_governance_hook_stack(
        governance_lifecycle_manager,
        *,
        evidence_collector=None,
    ):
        from app.runtime.governance.hooks.adapter import GovernanceRuntimeHookAdapter
        from app.runtime.hooks.memory_manager import InMemoryRuntimeHookManager

        runtime_hook_manager = InMemoryRuntimeHookManager()
        governance_hook_adapter = GovernanceRuntimeHookAdapter(
            governance_lifecycle_manager,
            evidence_collector=evidence_collector,
        )
        runtime_hook_manager.register_hook(governance_hook_adapter)
        return runtime_hook_manager, governance_hook_adapter

    @staticmethod
    def _build_tool_governance_hook_stack(
        governance_lifecycle_manager,
        permission_evaluator,
        *,
        runtime_hook_manager=None,
        evidence_collector=None,
        audit_recorder=None,
    ):
        from app.runtime.governance.tool_hooks.adapter import ToolLifecycleGovernanceAdapter
        from app.runtime.hooks.memory_manager import InMemoryRuntimeHookManager

        if runtime_hook_manager is None:
            runtime_hook_manager = InMemoryRuntimeHookManager()
        tool_governance_adapter = ToolLifecycleGovernanceAdapter(
            governance_lifecycle_manager,
            permission_evaluator,
            evidence_collector=evidence_collector,
            audit_recorder=audit_recorder,
        )
        runtime_hook_manager.register_hook(tool_governance_adapter)
        return runtime_hook_manager, tool_governance_adapter

    @staticmethod
    def _build_permission_evaluator(
        profile: RuntimeProfile,
        production_runtime: ProductionRuntime,
    ) -> PermissionEvaluator | None:
        if not profile.enable_permission_evaluator:
            return None
        return PermissionEvaluator(production_runtime.policy_engine)

    @staticmethod
    def _build_analytics_collector():
        from app.runtime.analytics.collector import RuntimeAnalyticsCollector
        from app.runtime.analytics.memory_store import InMemoryAnalyticsStore

        return RuntimeAnalyticsCollector(InMemoryAnalyticsStore())

    @staticmethod
    def _build_event_publisher():
        from app.runtime.event_stream.memory_publisher import InMemoryEventPublisher

        return InMemoryEventPublisher()

    @staticmethod
    def _build_audit_recorder():
        from app.runtime.audit.memory_store import InMemoryAuditStore
        from app.runtime.audit.recorder import RuntimeAuditRecorder

        return RuntimeAuditRecorder(InMemoryAuditStore())

    @staticmethod
    def _build_evidence_collector():
        from app.runtime.evidence.collector import RuntimeEvidenceCollector
        from app.runtime.evidence.memory_store import InMemoryEvidenceStore

        return RuntimeEvidenceCollector(InMemoryEvidenceStore())

    @staticmethod
    def _build_governance_lifecycle_manager():
        from app.runtime.governance.approval.memory_store import InMemoryApprovalStore
        from app.runtime.governance.enforcement.memory_enforcer import (
            InMemoryGovernanceEnforcer,
        )
        from app.runtime.governance.lifecycle.manager import GovernanceLifecycleManager
        from app.runtime.governance.memory_engine import InMemoryGovernanceEngine
        from app.runtime.governance.reporting.generator import GovernanceReportGenerator

        return GovernanceLifecycleManager(
            decision_engine=InMemoryGovernanceEngine(),
            enforcer=InMemoryGovernanceEnforcer(),
            report_generator=GovernanceReportGenerator(),
            approval_store=InMemoryApprovalStore(),
        )


def create_runtime(
    profile: str = "production",
    *,
    config: RuntimeAssemblyConfig | None = None,
) -> RuntimeAssembly:
    """Assemble runtime dependencies using a named profile."""
    resolved_config = config or RuntimeAssemblyConfig()
    if resolved_config.profile is None:
        resolved_config = RuntimeAssemblyConfig(
            profile=get_profile(profile),
            runtime_config=resolved_config.runtime_config,
            blocked_tools=resolved_config.blocked_tools,
            metadata=dict(resolved_config.metadata),
        )
    return RuntimeAssembler().assemble(resolved_config)
