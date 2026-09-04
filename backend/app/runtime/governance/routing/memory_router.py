# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""In-memory governance decision router."""

from __future__ import annotations

import threading
import uuid
from typing import Any

from app.runtime.governance.routing.models import (
    GovernanceRouteAction,
    GovernanceRouteRequest,
    GovernanceRouteResult,
    GovernanceRouteType,
)

_ROUTE_KEY_SEPARATOR = "\x1f"


class InMemoryGovernanceDecisionRouter:
    """Thread-safe in-memory governance decision router."""

    def __init__(self, *, enabled: bool = True) -> None:
        self._enabled = enabled
        self._routes: dict[str, GovernanceRouteResult] = {}
        self._route_history: list[GovernanceRouteResult] = []
        self._lock = threading.Lock()

    @property
    def enabled(self) -> bool:
        return self._enabled

    def set_enabled(self, enabled: bool) -> None:
        """Enable or disable governance decision routing."""
        with self._lock:
            self._enabled = enabled

    def route(self, request: GovernanceRouteRequest) -> GovernanceRouteResult:
        """Route one governance outcome into a normalized routing decision."""
        with self._lock:
            if not self._enabled:
                result = _build_disabled_result(request)
            else:
                result = _build_route_result(request)
            self._routes[_route_key(request.execution_id, result.route_id)] = result
            self._route_history.append(result)
            return result

    def get_route(self, execution_id: str) -> GovernanceRouteResult | None:
        """Return the latest routing decision for an execution."""
        with self._lock:
            matches = [
                result for result in self._route_history if result.execution_id == execution_id
            ]
        if not matches:
            return None
        return matches[-1]

    def list_routes(
        self,
        *,
        execution_id: str | None = None,
    ) -> list[GovernanceRouteResult]:
        """Return recorded routing decisions."""
        with self._lock:
            records = list(self._route_history)
        if execution_id is not None:
            records = [record for record in records if record.execution_id == execution_id]
        return records

    def clear(self) -> None:
        """Remove all recorded routing decisions."""
        with self._lock:
            self._routes.clear()
            self._route_history.clear()


def _build_disabled_result(request: GovernanceRouteRequest) -> GovernanceRouteResult:
    metadata = _build_metadata(
        request,
        route_type="ALLOW",
        action="CONTINUE",
        source_status=request.decision_status,
    )
    metadata["routing_enabled"] = False
    return GovernanceRouteResult(
        route_id=uuid.uuid4().hex,
        execution_id=request.execution_id,
        route_type="ALLOW",
        action="CONTINUE",
        approval_required=False,
        blocked=False,
        reason="governance decision routing disabled",
        metadata=metadata,
    )


def _build_route_result(request: GovernanceRouteRequest) -> GovernanceRouteResult:
    route_type, action, approval_required, blocked, reason = _resolve_route(request)
    return GovernanceRouteResult(
        route_id=uuid.uuid4().hex,
        execution_id=request.execution_id,
        route_type=route_type,
        action=action,
        approval_required=approval_required,
        blocked=blocked,
        reason=reason,
        metadata=_build_metadata(
            request,
            route_type=route_type,
            action=action,
            source_status=request.decision_status,
        ),
    )


def _resolve_route(
    request: GovernanceRouteRequest,
) -> tuple[GovernanceRouteType, GovernanceRouteAction, bool, bool, str]:
    if _is_block_route(request):
        return (
            "BLOCK",
            "BLOCK",
            False,
            True,
            _block_reason(request),
        )

    decision_status = request.decision_status.upper()
    if decision_status == "ALLOW":
        return ("ALLOW", "CONTINUE", False, False, "governance decision allow")
    if decision_status == "WARN":
        return (
            "WARNING",
            "CONTINUE_WITH_WARNING",
            False,
            False,
            "governance decision warn",
        )
    if decision_status == "REQUIRE_APPROVAL":
        return (
            "APPROVAL",
            "WAIT_APPROVAL",
            True,
            False,
            "governance decision requires approval",
        )

    return (
        "UNKNOWN",
        "NO_ACTION",
        False,
        False,
        f"unsupported governance decision status: {request.decision_status}",
    )


def _is_block_route(request: GovernanceRouteRequest) -> bool:
    if request.enforcement_status is not None and request.enforcement_status.upper() == "BLOCK":
        return True
    return request.decision_status.upper() == "DENY"


def _block_reason(request: GovernanceRouteRequest) -> str:
    if request.enforcement_status is not None and request.enforcement_status.upper() == "BLOCK":
        return "enforcement status block"
    return "governance decision deny"


def _build_metadata(
    request: GovernanceRouteRequest,
    *,
    route_type: GovernanceRouteType,
    action: GovernanceRouteAction,
    source_status: str,
) -> dict[str, Any]:
    metadata: dict[str, Any] = {
        "decision_status": source_status,
        "route_type": route_type,
        "route_action": action,
        "observation_only": True,
    }
    if request.enforcement_status is not None:
        metadata["enforcement_status"] = request.enforcement_status
    if request.policy_id is not None:
        metadata["policy_id"] = request.policy_id
    if request.metadata:
        metadata.update(dict(request.metadata))
    return metadata


def _route_key(execution_id: str, route_id: str) -> str:
    return _ROUTE_KEY_SEPARATOR.join((execution_id, route_id))
