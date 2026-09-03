# AgentFlow Intelligence v2.0 — Runtime assembly tests (Phase 10.15)

from __future__ import annotations

from pathlib import Path

from dataclasses import replace

import pytest

from app.runtime.agent.models import AgentDefinition
from app.runtime.agent.runtime import AgentRuntime
from app.runtime.assembly import (
    DEVELOPMENT_PROFILE,
    PRODUCTION_PROFILE,
    TESTING_PROFILE,
    RuntimeAssembler,
    RuntimeAssemblyConfig,
    create_runtime,
    get_profile,
)
from app.runtime.bootstrap.factory import create_production_runtime
from app.runtime.bootstrap.context_factory import create_execution_context

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
)


def test_development_profile_creation() -> None:
    assembly = create_runtime("development")

    assert assembly.profile is DEVELOPMENT_PROFILE
    assert assembly.profile.environment == "development"
    assert assembly.production_runtime.config.environment == "development"
    assert assembly.agent_runtime is not None
    assert assembly.agent_pipeline is not None
    assert assembly.agent_registry is not None
    assert assembly.tool_registry is not None
    assert assembly.permission_evaluator is not None
    assert assembly.state_store is not None
    assert assembly.checkpoint_store is not None
    assert assembly.memory_manager is not None
    assert assembly.runtime_context_manager is not None
    assert assembly.correlation_manager is not None
    assert assembly.analytics_collector is not None
    assert assembly.event_publisher is not None
    assert assembly.audit_recorder is not None
    assert assembly.evidence_collector is not None
    assert assembly.governance_lifecycle_manager is not None


def test_production_profile_creation() -> None:
    assembly = create_runtime("production")

    assert assembly.profile is PRODUCTION_PROFILE
    assert assembly.profile.environment == "production"
    assert assembly.production_runtime.governance_lifecycle is not None
    assert assembly.production_runtime.policy_engine is not None
    assert assembly.agent_registry is not None
    assert assembly.tool_registry is not None


def test_component_wiring_shares_production_runtime() -> None:
    assembly = create_runtime("production")

    assert assembly.agent_pipeline._production_runtime is assembly.production_runtime
    assert assembly.permission_evaluator is not None
    assert (
        assembly.permission_evaluator._policy_engine
        is assembly.production_runtime.policy_engine
    )

    execution_context = create_execution_context(
        assembly.production_runtime,
        execution_id="exec-assembly-1",
        agent_id="agent-assembly-1",
    )
    assert execution_context.policy_engine is assembly.production_runtime.policy_engine
    assert (
        execution_context.governance_lifecycle
        is assembly.production_runtime.governance_lifecycle
    )


def test_optional_components_disabled_for_testing_profile() -> None:
    assembly = create_runtime("testing")

    assert assembly.profile is TESTING_PROFILE
    assert assembly.production_runtime.config.enable_governance is False
    assert assembly.production_runtime.governance_lifecycle is None
    assert assembly.production_runtime.audit_store is None
    assert assembly.agent_registry is not None
    assert assembly.tool_registry is not None
    assert assembly.permission_evaluator is None
    assert assembly.state_store is None
    assert assembly.checkpoint_store is None
    assert assembly.memory_manager is None
    assert assembly.runtime_context_manager is None
    assert assembly.correlation_manager is None
    assert assembly.analytics_collector is None
    assert assembly.event_publisher is None
    assert assembly.audit_recorder is None
    assert assembly.evidence_collector is None
    assert assembly.governance_lifecycle_manager is None


def test_assembler_supports_profile_overrides() -> None:
    profile = replace(
        get_profile("testing"),
        enable_execution_state=True,
        enable_correlation=True,
    )
    assembly = RuntimeAssembler().assemble(RuntimeAssemblyConfig(profile=profile))

    assert assembly.state_store is not None
    assert assembly.correlation_manager is not None
    assert assembly.permission_evaluator is None


def test_backward_compatible_direct_construction() -> None:
    production_runtime = create_production_runtime()
    agent_runtime = AgentRuntime(production_runtime)

    assert agent_runtime._production_runtime is production_runtime
    assert agent_runtime._agent_registry is None
    assert agent_runtime._tool_registry is None
    assert agent_runtime._permission_evaluator is None


def test_agent_runtime_from_assembly_executes_without_registry() -> None:
    assembly = create_runtime("testing")
    agent = AgentDefinition(
        id="agent-assembly-direct",
        name="assembly-agent",
        tool_names=[],
    )

    result = assembly.agent_runtime.execute(
        agent,
        "assembly task",
        create_execution_context(
            assembly.production_runtime,
            execution_id="exec-assembly-direct",
            agent_id=agent.id,
        ),
    )

    assert result.session.agent_id == agent.id
    assert result.error is None


def test_get_profile_rejects_unknown_name() -> None:
    with pytest.raises(KeyError, match="Unknown runtime profile"):
        get_profile("unknown-profile")


def test_assembly_module_has_no_forbidden_dependencies() -> None:
    for path in _ASSEMBLY_ROOT.rglob("*.py"):
        source = path.read_text(encoding="utf-8")
        lowered = source.lower()
        for forbidden in _FORBIDDEN_STRINGS:
            assert forbidden not in lowered, f"{forbidden!r} found in {path}"
