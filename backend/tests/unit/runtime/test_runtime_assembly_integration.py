# AgentFlow Intelligence v2.0 — Runtime assembly governance integration tests (Phase 11.12)

from __future__ import annotations

from pathlib import Path

from app.runtime.agent.runtime import AgentRuntime
from app.runtime.assembly import create_runtime
from app.runtime.bootstrap.factory import create_production_runtime
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


def test_assembly_creates_runtime_components() -> None:
    assembly = create_runtime("production")

    assert assembly.production_runtime is not None
    assert assembly.agent_runtime is not None
    assert assembly.agent_pipeline is not None
    assert assembly.agent_registry is not None
    assert assembly.tool_registry is not None


def test_governance_lifecycle_manager_attached_for_production() -> None:
    assembly = create_runtime("production")

    assert assembly.governance_lifecycle_manager is not None
    assert assembly.governance_lifecycle_manager._enforcer is not None
    assert assembly.governance_lifecycle_manager._report_generator is not None


def test_analytics_collector_attached_for_production() -> None:
    assembly = create_runtime("production")

    assert assembly.analytics_collector is not None
    assert assembly.agent_pipeline._analytics_collector is assembly.analytics_collector


def test_event_publisher_attached_for_production() -> None:
    assembly = create_runtime("production")

    assert assembly.event_publisher is not None
    assert assembly.agent_pipeline._event_publisher is assembly.event_publisher


def test_audit_recorder_attached_for_production() -> None:
    assembly = create_runtime("production")

    assert assembly.audit_recorder is not None
    assert assembly.agent_pipeline._audit_recorder is assembly.audit_recorder
    assert assembly.agent_runtime._audit_recorder is assembly.audit_recorder


def test_evidence_collector_attached_for_production() -> None:
    assembly = create_runtime("production")

    assert assembly.evidence_collector is not None
    assert assembly.agent_pipeline._evidence_collector is assembly.evidence_collector


def test_testing_profile_keeps_lightweight_optional_components() -> None:
    assembly = create_runtime("testing")

    assert assembly.analytics_collector is None
    assert assembly.event_publisher is None
    assert assembly.audit_recorder is None
    assert assembly.evidence_collector is None
    assert assembly.governance_lifecycle_manager is None
    assert assembly.agent_registry is not None
    assert assembly.tool_registry is not None


def test_backward_compatible_direct_construction() -> None:
    production_runtime = create_production_runtime()
    agent_runtime = AgentRuntime(production_runtime)
    agent_pipeline = AgentExecutionPipeline(production_runtime)

    assert agent_runtime._production_runtime is production_runtime
    assert agent_pipeline._analytics_collector is None
    assert agent_pipeline._event_publisher is None
    assert agent_pipeline._audit_recorder is None
    assert agent_pipeline._evidence_collector is None


def test_assembly_module_has_no_forbidden_dependencies() -> None:
    for path in _ASSEMBLY_ROOT.rglob("*.py"):
        source = path.read_text(encoding="utf-8")
        lowered = source.lower()
        for forbidden in _FORBIDDEN_STRINGS:
            assert forbidden not in lowered, f"{forbidden!r} found in {path}"
