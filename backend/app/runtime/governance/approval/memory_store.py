# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""In-memory governance approval store."""

from __future__ import annotations

import threading

from app.runtime.governance.approval.models import (
    ApprovalDecision,
    ApprovalRequest,
    ApprovalRequestStatus,
)


class InMemoryApprovalStore:
    """Thread-safe in-memory governance approval store."""

    def __init__(self) -> None:
        self._requests: dict[str, ApprovalRequest] = {}
        self._decisions: dict[str, list[ApprovalDecision]] = {}
        self._lock = threading.Lock()

    def create(self, request: ApprovalRequest) -> None:
        with self._lock:
            self._requests[request.request_id] = request
            self._decisions.setdefault(request.request_id, [])

    def get(self, request_id: str) -> ApprovalRequest | None:
        with self._lock:
            return self._requests.get(request_id)

    def update(self, request: ApprovalRequest) -> None:
        with self._lock:
            self._requests[request.request_id] = request

    def list_pending(self) -> list[ApprovalRequest]:
        with self._lock:
            pending = [
                request
                for request in self._requests.values()
                if request.status == "PENDING"
            ]
        return sorted(pending, key=lambda request: request.created_at)

    def record_decision(self, decision: ApprovalDecision) -> None:
        with self._lock:
            request = self._requests.get(decision.request_id)
            if request is None:
                raise KeyError(f"Approval request not found: {decision.request_id}")

            history = self._decisions.setdefault(decision.request_id, [])
            history.append(decision)

            next_status = _request_status_for_decision(decision.decision)
            self._requests[decision.request_id] = request.with_updates(status=next_status)

    def get_decisions(self, request_id: str) -> list[ApprovalDecision]:
        with self._lock:
            return list(self._decisions.get(request_id, []))


def _request_status_for_decision(decision: str) -> ApprovalRequestStatus:
    if decision == "APPROVE":
        return "APPROVED"
    return "REJECTED"
