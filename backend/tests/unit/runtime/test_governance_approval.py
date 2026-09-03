# AgentFlow Intelligence v2.0 — Runtime governance approval tests (Phase 11.9)

from __future__ import annotations

import threading
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from app.runtime.governance.approval.memory_store import InMemoryApprovalStore
from app.runtime.governance.approval.models import ApprovalDecision, ApprovalRequest

_APPROVAL_ROOT = (
    Path(__file__).resolve().parents[3] / "app" / "runtime" / "governance" / "approval"
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
    "GovernanceEvaluator",
    "InMemoryGovernanceEngine",
    "GovernanceEnforcer",
    "AgentRuntime",
    "AgentExecutionPipeline",
    "EvidenceCollector",
    "EvidenceQueryService",
    "ExecutionContext",
)


def _request(
    *,
    request_id: str = "request-1",
    execution_id: str = "exec-approval-1",
    reason: str = "manual review required",
    status: str = "PENDING",
) -> ApprovalRequest:
    return ApprovalRequest(
        request_id=request_id,
        execution_id=execution_id,
        policy_id="policy-approval-1",
        decision_id="decision-approval-1",
        reason=reason,
        status=status,  # type: ignore[arg-type]
        metadata={"source": "governance"},
    )


def _decision(
    *,
    request_id: str = "request-1",
    decision: str = "APPROVE",
    approver: str = "reviewer-1",
    reason: str = "approved after review",
) -> ApprovalDecision:
    return ApprovalDecision(
        request_id=request_id,
        decision=decision,  # type: ignore[arg-type]
        approver=approver,
        reason=reason,
        metadata={"channel": "manual"},
    )


def test_request_creation() -> None:
    request = _request()

    assert request.request_id == "request-1"
    assert request.execution_id == "exec-approval-1"
    assert request.status == "PENDING"
    assert request.policy_id == "policy-approval-1"
    assert request.metadata["source"] == "governance"


def test_approval_models_are_immutable() -> None:
    request = _request()
    decision = _decision()

    with pytest.raises(FrozenInstanceError):
        request.status = "APPROVED"  # type: ignore[misc]

    with pytest.raises(FrozenInstanceError):
        decision.decision = "REJECT"  # type: ignore[misc]

    updated_request = request.with_updates(status="APPROVED")
    updated_decision = decision.with_updates(decision="REJECT")

    assert updated_request.status == "APPROVED"
    assert updated_decision.decision == "REJECT"
    assert request.status == "PENDING"
    assert decision.decision == "APPROVE"


def test_create_and_get_request() -> None:
    store = InMemoryApprovalStore()
    request = _request()

    store.create(request)

    assert store.get("request-1") == request
    assert store.get("missing") is None


def test_update_request_status() -> None:
    store = InMemoryApprovalStore()
    store.create(_request())
    updated = _request(status="EXPIRED", reason="expired by policy")

    store.update(updated)

    stored = store.get("request-1")
    assert stored is not None
    assert stored.status == "EXPIRED"
    assert stored.reason == "expired by policy"


def test_list_pending_requests() -> None:
    store = InMemoryApprovalStore()
    store.create(_request(request_id="request-pending", status="PENDING"))
    store.create(_request(request_id="request-approved", status="APPROVED"))
    store.create(_request(request_id="request-pending-2", status="PENDING"))

    pending = store.list_pending()

    assert len(pending) == 2
    assert {request.request_id for request in pending} == {
        "request-pending",
        "request-pending-2",
    }


def test_record_decision() -> None:
    store = InMemoryApprovalStore()
    store.create(_request())

    store.record_decision(_decision(decision="APPROVE"))

    stored = store.get("request-1")
    assert stored is not None
    assert stored.status == "APPROVED"


def test_decision_history() -> None:
    store = InMemoryApprovalStore()
    store.create(_request())

    first = _decision(decision="APPROVE", approver="reviewer-1", reason="first")
    second = _decision(decision="REJECT", approver="reviewer-2", reason="override")

    store.record_decision(first)
    store.update(_request(status="PENDING"))
    store.record_decision(second)

    history = store.get_decisions("request-1")

    assert len(history) == 2
    assert history[0].approver == "reviewer-1"
    assert history[1].decision == "REJECT"
    assert store.get("request-1") is not None
    assert store.get("request-1").status == "REJECTED"


def test_duplicate_request_replacement() -> None:
    store = InMemoryApprovalStore()
    original = _request(reason="first")
    replacement = _request(reason="second")

    store.create(original)
    store.create(replacement)

    stored = store.get("request-1")
    assert stored is not None
    assert stored.reason == "second"
    assert len(store.list_pending()) == 1


def test_approval_store_is_thread_safe() -> None:
    store = InMemoryApprovalStore()
    errors: list[Exception] = []

    def create_many(prefix: str) -> None:
        try:
            for index in range(20):
                store.create(
                    _request(
                        request_id=f"request-{prefix}-{index}",
                        execution_id=f"exec-{prefix}-{index}",
                    )
                )
        except Exception as exc:  # pragma: no cover
            errors.append(exc)

    threads = [threading.Thread(target=create_many, args=(f"t{i}",)) for i in range(4)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert errors == []
    assert len(store.list_pending()) == 80


def test_approval_module_has_no_forbidden_dependencies() -> None:
    for path in _APPROVAL_ROOT.rglob("*.py"):
        source = path.read_text(encoding="utf-8")
        lowered = source.lower()
        for forbidden in _FORBIDDEN_STRINGS:
            assert forbidden not in lowered, f"{forbidden!r} found in {path}"
