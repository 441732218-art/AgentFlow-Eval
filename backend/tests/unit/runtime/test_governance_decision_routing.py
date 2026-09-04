# AgentFlow Intelligence v2.0 — Governance decision routing tests (Phase 12.9)

from __future__ import annotations

import threading
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from app.runtime.governance.routing.memory_router import InMemoryGovernanceDecisionRouter
from app.runtime.governance.routing.models import GovernanceRouteRequest, GovernanceRouteResult

_ROUTING_ROOT = (
    Path(__file__).resolve().parents[3] / "app" / "runtime" / "governance" / "routing"
)
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
    "PolicyEngine",
    "PermissionEvaluator",
    "ToolExecutionEngine",
    "GovernanceLifecycleManager",
    "AgentRuntime",
    "AgentExecutionPipeline",
    "ExecutionContext",
)


def _request(
    *,
    decision_status: str,
    execution_id: str = "exec-route-1",
    enforcement_status: str | None = None,
    policy_id: str | None = "policy-1",
    metadata: dict[str, object] | None = None,
) -> GovernanceRouteRequest:
    return GovernanceRouteRequest(
        execution_id=execution_id,
        decision_status=decision_status,
        enforcement_status=enforcement_status,
        policy_id=policy_id,
        metadata=dict(metadata or {"source": "test"}),
    )


def test_governance_route_request_creation() -> None:
    request = _request(decision_status="ALLOW", metadata={"phase": "tool"})

    assert request.execution_id == "exec-route-1"
    assert request.decision_status == "ALLOW"
    assert request.policy_id == "policy-1"
    assert request.metadata["phase"] == "tool"


def test_governance_route_result_is_immutable() -> None:
    result = GovernanceRouteResult(
        route_id="route-1",
        execution_id="exec-route-1",
        route_type="ALLOW",
        action="CONTINUE",
        approval_required=False,
        blocked=False,
        reason="all clear",
    )

    with pytest.raises(FrozenInstanceError):
        result.blocked = True  # type: ignore[misc]

    updated = result.with_updates(blocked=True)
    assert updated.blocked is True
    assert result.blocked is False


def test_allow_routing() -> None:
    router = InMemoryGovernanceDecisionRouter()
    result = router.route(_request(decision_status="ALLOW"))

    assert result.route_type == "ALLOW"
    assert result.action == "CONTINUE"
    assert result.approval_required is False
    assert result.blocked is False


def test_warn_routing() -> None:
    router = InMemoryGovernanceDecisionRouter()
    result = router.route(_request(decision_status="WARN"))

    assert result.route_type == "WARNING"
    assert result.action == "CONTINUE_WITH_WARNING"
    assert result.approval_required is False
    assert result.blocked is False


def test_require_approval_routing() -> None:
    router = InMemoryGovernanceDecisionRouter()
    result = router.route(_request(decision_status="REQUIRE_APPROVAL"))

    assert result.route_type == "APPROVAL"
    assert result.action == "WAIT_APPROVAL"
    assert result.approval_required is True
    assert result.blocked is False


def test_deny_routing() -> None:
    router = InMemoryGovernanceDecisionRouter()
    result = router.route(_request(decision_status="DENY"))

    assert result.route_type == "BLOCK"
    assert result.action == "BLOCK"
    assert result.approval_required is False
    assert result.blocked is True
    assert result.reason == "governance decision deny"


def test_block_enforcement_routing() -> None:
    router = InMemoryGovernanceDecisionRouter()
    result = router.route(
        _request(decision_status="ALLOW", enforcement_status="BLOCK"),
    )

    assert result.route_type == "BLOCK"
    assert result.action == "BLOCK"
    assert result.blocked is True
    assert result.reason == "enforcement status block"


def test_unknown_routing() -> None:
    router = InMemoryGovernanceDecisionRouter()
    result = router.route(_request(decision_status="MYSTERY"))

    assert result.route_type == "UNKNOWN"
    assert result.action == "NO_ACTION"
    assert result.approval_required is False
    assert result.blocked is False


def test_metadata_preservation() -> None:
    router = InMemoryGovernanceDecisionRouter()
    result = router.route(
        _request(
            decision_status="WARN",
            enforcement_status="WARN",
            metadata={"correlation_id": "corr-1", "tool_name": "probe.echo"},
        )
    )

    assert result.metadata["decision_status"] == "WARN"
    assert result.metadata["enforcement_status"] == "WARN"
    assert result.metadata["policy_id"] == "policy-1"
    assert result.metadata["correlation_id"] == "corr-1"
    assert result.metadata["tool_name"] == "probe.echo"
    assert result.metadata["observation_only"] is True


def test_list_routes() -> None:
    router = InMemoryGovernanceDecisionRouter()
    router.route(_request(decision_status="ALLOW", execution_id="exec-a"))
    router.route(_request(decision_status="DENY", execution_id="exec-b"))

    all_routes = router.list_routes()
    filtered = router.list_routes(execution_id="exec-a")

    assert len(all_routes) == 2
    assert len(filtered) == 1
    assert filtered[0].execution_id == "exec-a"


def test_get_route_returns_latest_for_execution() -> None:
    router = InMemoryGovernanceDecisionRouter()
    router.route(_request(decision_status="ALLOW", execution_id="exec-route-1"))
    latest = router.route(_request(decision_status="WARN", execution_id="exec-route-1"))

    retrieved = router.get_route("exec-route-1")

    assert retrieved == latest
    assert retrieved.route_type == "WARNING"


def test_clear_history() -> None:
    router = InMemoryGovernanceDecisionRouter()
    router.route(_request(decision_status="ALLOW"))

    router.clear()

    assert router.list_routes() == []
    assert router.get_route("exec-route-1") is None


def test_disabled_behavior() -> None:
    router = InMemoryGovernanceDecisionRouter(enabled=False)
    result = router.route(_request(decision_status="DENY", enforcement_status="BLOCK"))

    assert result.route_type == "ALLOW"
    assert result.action == "CONTINUE"
    assert result.blocked is False
    assert result.metadata["routing_enabled"] is False


def test_router_is_thread_safe() -> None:
    router = InMemoryGovernanceDecisionRouter()
    errors: list[Exception] = []
    statuses = ("ALLOW", "WARN", "REQUIRE_APPROVAL", "DENY")

    def worker(index: int) -> None:
        try:
            router.route(
                _request(
                    decision_status=statuses[index % len(statuses)],
                    execution_id=f"exec-thread-{index}",
                )
            )
        except Exception as exc:  # pragma: no cover - surfaced via errors list
            errors.append(exc)

    threads = [threading.Thread(target=worker, args=(index,)) for index in range(24)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert errors == []
    assert len(router.list_routes()) == 24


def test_governance_decision_routing_has_no_forbidden_dependencies() -> None:
    for path in _ROUTING_ROOT.rglob("*.py"):
        source = path.read_text(encoding="utf-8")
        lowered = source.lower()
        for forbidden in _FORBIDDEN_STRINGS:
            assert forbidden not in lowered, f"{forbidden!r} found in {path}"
