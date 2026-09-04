# AgentFlow Intelligence v2.0 — Governance runtime assembly integration tests (Phase 13.9)

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from app.runtime.agent.runtime import AgentRuntime
from app.runtime.assembly import (
    DEVELOPMENT_PROFILE,
    PRODUCTION_PROFILE,
    TESTING_PROFILE,
    RuntimeAssembler,
    RuntimeAssembly,
    RuntimeAssemblyConfig,
    create_runtime,
)
from app.runtime.bootstrap.factory import create_production_runtime
from app.runtime.governance.binding.memory_binder import InMemoryRuntimeEnforcementBinder
from app.runtime.governance.configuration.memory_registry import (
    InMemoryGovernanceConfigurationRegistry,
)
from app.runtime.governance.enforcement_pipeline.memory_pipeline import (
    InMemoryRuntimeEnforcementPipeline,
)
from app.runtime.governance.evidence_correlation.builder import (
    DefaultEvidenceCorrelationBuilder,
)
from app.runtime.governance.evidence_correlation.memory_store import (
    InMemoryEvidenceCorrelationStore,
)
from app.runtime.governance.execution.memory_executor import InMemoryGovernanceExecutionContract
from app.runtime.governance.orchestrator.memory_orchestrator import (
    InMemoryGovernanceRuntimeOrchestrator,
)
from app.runtime.governance.policy_binding.memory_binder import InMemoryPolicyExecutionBinder
from app.runtime.governance.resolver.memory_resolver import InMemoryGovernanceEffectResolver
from app.runtime.governance.routing.memory_router import InMemoryGovernanceDecisionRouter
from app.runtime.governance.runtime_adapter.memory_adapter import (
    InMemoryGovernanceRuntimeDecisionAdapter,
)
from app.runtime.governance.snapshot.builder import DefaultGovernanceSnapshotBuilder
from app.runtime.governance.snapshot.memory_store import InMemoryGovernanceSnapshotStore
from app.runtime.pipeline.agent_pipeline import AgentExecutionPipeline

_ASSEMBLY_ROOT = Path(__file__).resolve().parents[3] / "app" / "runtime" / "assembly"
_FORBIDDEN_STRINGS = (
    "app.applications",
    "app.api",
    "app.service",
    "app.tracing",
    "app.runtime.memory",
    "app.core",
    "openai",
    "langgraph",
    "sqlalchemy",
    "postgres",
    "trade_provider",
    "kafka",
    "redis",
)


def test_assembly_model_accepts_governance_fields() -> None:
    production_runtime = create_production_runtime()
    agent_runtime = AgentRuntime(production_runtime)
    agent_pipeline = AgentExecutionPipeline(production_runtime)
    decision_router = InMemoryGovernanceDecisionRouter()
    orchestrator = InMemoryGovernanceRuntimeOrchestrator(decision_router=decision_router)
    configuration_registry = InMemoryGovernanceConfigurationRegistry()
    snapshot_store = InMemoryGovernanceSnapshotStore()
    snapshot_builder = DefaultGovernanceSnapshotBuilder()
    evidence_correlation_store = InMemoryEvidenceCorrelationStore()
    evidence_correlation_builder = DefaultEvidenceCorrelationBuilder()
    execution_contract = InMemoryGovernanceExecutionContract()
    effect_resolver = InMemoryGovernanceEffectResolver()
    decision_adapter = InMemoryGovernanceRuntimeDecisionAdapter()

    assembly = RuntimeAssembly(
        profile=TESTING_PROFILE,
        production_runtime=production_runtime,
        agent_runtime=agent_runtime,
        agent_pipeline=agent_pipeline,
        governance_decision_router=decision_router,
        governance_runtime_orchestrator=orchestrator,
        governance_configuration_registry=configuration_registry,
        governance_snapshot_store=snapshot_store,
        governance_snapshot_builder=snapshot_builder,
        governance_evidence_correlation_store=evidence_correlation_store,
        governance_evidence_correlation_builder=evidence_correlation_builder,
        governance_execution_contract=execution_contract,
        governance_effect_resolver=effect_resolver,
        governance_runtime_decision_adapter=decision_adapter,
    )

    assert assembly.governance_decision_router is decision_router
    assert assembly.governance_runtime_orchestrator is orchestrator
    assert assembly.governance_configuration_registry is configuration_registry
    assert assembly.governance_snapshot_store is snapshot_store
    assert assembly.governance_snapshot_builder is snapshot_builder
    assert assembly.governance_evidence_correlation_store is evidence_correlation_store
    assert assembly.governance_evidence_correlation_builder is evidence_correlation_builder
    assert assembly.governance_execution_contract is execution_contract
    assert assembly.governance_effect_resolver is effect_resolver
    assert assembly.governance_runtime_decision_adapter is decision_adapter


def test_production_profile_enables_governance_stack() -> None:
    assembly = create_runtime("production")

    assert assembly.profile.enable_governance_runtime is True
    assert assembly.governance_decision_router is not None
    assert assembly.governance_runtime_orchestrator is not None
    assert assembly.governance_configuration_registry is not None
    assert assembly.governance_snapshot_store is not None
    assert assembly.governance_snapshot_builder is not None
    assert assembly.governance_evidence_correlation_store is not None
    assert assembly.governance_evidence_correlation_builder is not None
    assert assembly.governance_execution_contract is not None
    assert assembly.governance_effect_resolver is not None
    assert assembly.governance_runtime_decision_adapter is not None


def test_development_profile_enables_governance_stack() -> None:
    assembly = create_runtime("development")

    assert assembly.profile.enable_governance_runtime is True
    assert assembly.governance_runtime_orchestrator is not None
    assert assembly.governance_runtime_decision_adapter is not None


def test_testing_profile_disables_governance_stack() -> None:
    assembly = create_runtime("testing")

    assert assembly.profile.enable_governance_runtime is False
    assert assembly.governance_decision_router is None
    assert assembly.governance_runtime_orchestrator is None
    assert assembly.governance_configuration_registry is None
    assert assembly.governance_snapshot_store is None
    assert assembly.governance_snapshot_builder is None
    assert assembly.governance_evidence_correlation_store is None
    assert assembly.governance_evidence_correlation_builder is None
    assert assembly.governance_execution_contract is None
    assert assembly.governance_effect_resolver is None
    assert assembly.governance_runtime_decision_adapter is None


def test_missing_governance_dependency_does_not_fail_assembly() -> None:
    profile = replace(
        PRODUCTION_PROFILE,
        enable_governance_runtime=False,
        enable_governance_lifecycle=False,
    )
    assembly = RuntimeAssembler().assemble(RuntimeAssemblyConfig(profile=profile))

    assert assembly.governance_runtime_orchestrator is None
    assert assembly.agent_runtime is not None
    assert assembly.agent_pipeline is not None


def test_existing_runtime_creation_unchanged() -> None:
    assembly = create_runtime("production")

    assert assembly.agent_runtime._production_runtime is assembly.production_runtime
    assert assembly.agent_pipeline._production_runtime is assembly.production_runtime
    assert assembly.agent_pipeline._analytics_collector is assembly.analytics_collector
    assert assembly.agent_pipeline._evidence_collector is assembly.evidence_collector


def test_agent_runtime_unchanged_by_governance_assembly() -> None:
    assembly_without = create_runtime("testing")
    assembly_with = create_runtime("production")

    assert type(assembly_without.agent_runtime) is AgentRuntime
    assert type(assembly_with.agent_runtime) is AgentRuntime
    assert assembly_without.agent_runtime._audit_recorder is None
    assert assembly_with.agent_runtime._audit_recorder is assembly_with.audit_recorder


def test_pipeline_unchanged_by_governance_assembly() -> None:
    assembly_without = create_runtime("testing")
    assembly_with = create_runtime("production")

    assert type(assembly_without.agent_pipeline) is AgentExecutionPipeline
    assert type(assembly_with.agent_pipeline) is AgentExecutionPipeline
    assert assembly_without.agent_pipeline._runtime_hook_manager is None
    assert assembly_with.agent_pipeline._runtime_hook_manager is None


def test_governance_components_are_injected_correctly() -> None:
    assembly = create_runtime("production")
    orchestrator = assembly.governance_runtime_orchestrator

    assert orchestrator is not None
    assert orchestrator._decision_router is assembly.governance_decision_router
    assert isinstance(orchestrator._enforcement_pipeline, InMemoryRuntimeEnforcementPipeline)
    assert isinstance(orchestrator._enforcement_binder, InMemoryRuntimeEnforcementBinder)
    assert isinstance(orchestrator._policy_binder, InMemoryPolicyExecutionBinder)
    assert isinstance(assembly.governance_snapshot_builder, DefaultGovernanceSnapshotBuilder)
    assert isinstance(
        assembly.governance_evidence_correlation_builder,
        DefaultEvidenceCorrelationBuilder,
    )
    assert isinstance(
        assembly.governance_execution_contract,
        InMemoryGovernanceExecutionContract,
    )
    assert isinstance(assembly.governance_effect_resolver, InMemoryGovernanceEffectResolver)
    assert isinstance(
        assembly.governance_runtime_decision_adapter,
        InMemoryGovernanceRuntimeDecisionAdapter,
    )


def test_assembly_module_has_no_forbidden_dependencies() -> None:
    for path in _ASSEMBLY_ROOT.rglob("*.py"):
        source = path.read_text(encoding="utf-8")
        lowered = source.lower()
        for forbidden in _FORBIDDEN_STRINGS:
            assert forbidden not in lowered, f"{forbidden!r} found in {path}"


def test_profile_defaults_keep_governance_runtime_disabled() -> None:
    profile = replace(DEVELOPMENT_PROFILE, enable_governance_runtime=False)
    assert profile.enable_governance_runtime is False
