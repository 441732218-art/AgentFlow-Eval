# AgentFlow Intelligence v2.0 — Tool permission binding tests (Phase 10.13)

from __future__ import annotations

from pathlib import Path

import pytest

from app.runtime.agent.models import AgentDefinition
from app.runtime.agent.runtime import AgentRuntime
from app.runtime.bootstrap.context_factory import create_execution_context
from app.runtime.bootstrap.factory import create_production_runtime
from app.runtime.observability.collector import InMemoryObservationCollector
from app.runtime.observability.events import RuntimeEventType
from app.runtime.permissions.binding import ToolPermissionBinding
from app.runtime.permissions.evaluator import PermissionEvaluator
from app.runtime.permissions.models import PermissionRequirement
from app.runtime.policy.engine import InMemoryPolicyEngine
from app.runtime.policy.models import PolicyDeniedError
from app.runtime.tool_registry.errors import ToolDisabledError, ToolNotFoundError
from app.runtime.tool_registry.memory_registry import InMemoryToolRegistry
from app.runtime.tool_registry.models import ToolCapability
from app.runtime.tool_registry.registry import resolve_tool_capability

_PERMISSIONS_ROOT = Path(__file__).resolve().parents[3] / "app" / "runtime" / "permissions"
_FORBIDDEN_STRINGS = (
    "app.applications",
    "app.api",
    "app.service",
    "app.tracing",
    "app.runtime.memory",
    "openai",
    "langgraph",
    "sqlalchemy",
    "postgres",
    "oauth",
    "auth0",
)


def _capability(
    tool_name: str = "email.send",
    *,
    enabled: bool = True,
    permission_scope: tuple[str, ...] = ("email.send",),
) -> ToolCapability:
    return ToolCapability(
        tool_name=tool_name,
        version="1.0",
        description="Send email",
        capability_tags=("communication",),
        permission_scope=permission_scope,
        enabled=enabled,
    )


def test_permission_requirement_creation() -> None:
    requirement = PermissionRequirement(
        permission="email.send",
        description="Allow sending emails",
        metadata={"scope": "communication"},
    )

    assert requirement.permission == "email.send"
    assert requirement.description == "Allow sending emails"
    assert requirement.metadata["scope"] == "communication"


def test_tool_permission_binding_creation() -> None:
    binding = ToolPermissionBinding(
        tool_name="email.send",
        permissions=(
            PermissionRequirement(
                permission="email.send",
                description="Allow sending emails",
            ),
        ),
    )

    assert binding.tool_name == "email.send"
    assert binding.permissions[0].permission == "email.send"


def test_permission_evaluator_allows_registered_tool() -> None:
    capability = _capability()
    evaluator = PermissionEvaluator(InMemoryPolicyEngine())
    context = create_execution_context(
        create_production_runtime(),
        execution_id="exec-perm-allow",
        agent_id="agent-perm-allow",
    )

    decision = evaluator.evaluate_tool_access(context, capability)

    assert decision.allowed is True


def test_permission_evaluator_denies_blocked_tool() -> None:
    capability = _capability()
    evaluator = PermissionEvaluator(
        InMemoryPolicyEngine(blocked_tools=["email.send"]),
    )
    context = create_execution_context(
        create_production_runtime(),
        execution_id="exec-perm-deny",
        agent_id="agent-perm-deny",
    )

    decision = evaluator.evaluate_tool_access(context, capability)

    assert decision.allowed is False
    assert decision.reason is not None


def test_permission_evaluator_reports_missing_permission_scope() -> None:
    capability = _capability(permission_scope=())
    binding = ToolPermissionBinding(
        tool_name="email.send",
        permissions=(PermissionRequirement(permission="email.send"),),
    )
    evaluator = PermissionEvaluator(
        InMemoryPolicyEngine(),
        bindings={"email.send": binding},
    )

    decision = evaluator.evaluate_tool_access(None, capability)

    assert decision.allowed is False
    assert decision.policy_name == "tool_permission_binding"


def test_permission_evaluator_rejects_disabled_capability() -> None:
    capability = _capability(enabled=False)
    evaluator = PermissionEvaluator(InMemoryPolicyEngine())

    decision = evaluator.evaluate_tool_access(None, capability)

    assert decision.allowed is False
    assert "disabled" in (decision.reason or "").lower()


def test_agent_runtime_integrates_permission_evaluator() -> None:
    production_runtime = create_production_runtime()
    collector = InMemoryObservationCollector()
    tool_registry = InMemoryToolRegistry()
    tool_registry.register(_capability())
    permission_evaluator = PermissionEvaluator(
        InMemoryPolicyEngine(blocked_tools=["email.send"]),
    )
    runtime = AgentRuntime(
        production_runtime,
        tool_registry=tool_registry,
        permission_evaluator=permission_evaluator,
    )
    context = create_execution_context(
        production_runtime,
        execution_id="exec-runtime-permission",
        agent_id="agent-runtime-permission",
        metadata={},
    )
    context.observation_collector = collector
    agent = AgentDefinition(
        id="agent-runtime-permission",
        name="permission-agent",
        tool_names=["email.send"],
    )

    with pytest.raises(PolicyDeniedError, match="email.send"):
        runtime.execute(agent, "permission task", context)

    events = collector.get_events()
    assert len(events) == 1
    assert events[0].event_type == RuntimeEventType.TOOL_PERMISSION_DENIED
    assert events[0].tool_name == "email.send"


def test_agent_runtime_without_permission_evaluator_preserves_behavior() -> None:
    production_runtime = create_production_runtime()
    runtime = AgentRuntime(production_runtime)
    context = create_execution_context(
        production_runtime,
        execution_id="exec-no-permission-evaluator",
        agent_id="agent-no-permission-evaluator",
    )
    agent = AgentDefinition(
        id="agent-no-permission-evaluator",
        name="no-permission-evaluator-agent",
        tool_names=[],
    )

    result = runtime.execute(agent, "no permission evaluator task", context)

    assert result.error is None
    assert result.session.status == "COMPLETED"


def test_resolve_tool_capability_raises_for_missing_tool() -> None:
    registry = InMemoryToolRegistry()

    with pytest.raises(ToolNotFoundError, match="missing.tool"):
        resolve_tool_capability(registry, "missing.tool")


def test_resolve_tool_capability_raises_for_disabled_tool() -> None:
    registry = InMemoryToolRegistry()
    registry.register(_capability(enabled=False))

    with pytest.raises(ToolDisabledError, match="email.send"):
        resolve_tool_capability(registry, "email.send")


def test_permissions_module_has_no_forbidden_dependencies() -> None:
    for path in _PERMISSIONS_ROOT.rglob("*.py"):
        source = path.read_text(encoding="utf-8")
        lowered = source.lower()
        for forbidden in _FORBIDDEN_STRINGS:
            assert forbidden not in lowered, f"{forbidden!r} found in {path}"
