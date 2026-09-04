# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""In-memory governance runtime orchestrator."""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING, Any

from app.runtime.governance.binding.models import RuntimeBindingRequest
from app.runtime.governance.enforcement_pipeline.models import EnforcementRequest
from app.runtime.governance.gateway.models import GovernanceGateResult
from app.runtime.governance.orchestrator.models import (
    GovernanceExecutionRequest,
    GovernanceExecutionResult,
    GovernanceOrchestratorAction,
    GovernanceOrchestratorRouteType,
)
from app.runtime.governance.policy_binding.models import PolicyBindingRequest
from app.runtime.governance.routing.models import GovernanceRouteRequest

if TYPE_CHECKING:
    from app.runtime.governance.binding.binder import RuntimeEnforcementBinder
    from app.runtime.governance.enforcement_pipeline.pipeline import RuntimeEnforcementPipeline
    from app.runtime.governance.policy_binding.binder import PolicyExecutionBinder
    from app.runtime.governance.reporting.generator import GovernanceReportGenerator
    from app.runtime.governance.routing.router import GovernanceDecisionRouter


class InMemoryGovernanceRuntimeOrchestrator:
    """Thread-safe in-memory governance runtime orchestrator."""

    def __init__(
        self,
        *,
        enabled: bool = True,
        decision_router: GovernanceDecisionRouter | None = None,
        enforcement_pipeline: RuntimeEnforcementPipeline | None = None,
        enforcement_binder: RuntimeEnforcementBinder | None = None,
        policy_binder: PolicyExecutionBinder | None = None,
        report_generator: GovernanceReportGenerator | None = None,
    ) -> None:
        self._enabled = enabled
        self._decision_router = decision_router
        self._enforcement_pipeline = enforcement_pipeline
        self._enforcement_binder = enforcement_binder
        self._policy_binder = policy_binder
        self._report_generator = report_generator
        self._results: list[GovernanceExecutionResult] = []
        self._lock = threading.Lock()

    @property
    def enabled(self) -> bool:
        return self._enabled

    def set_enabled(self, enabled: bool) -> None:
        """Enable or disable governance orchestration."""
        with self._lock:
            self._enabled = enabled

    def execute(self, request: GovernanceExecutionRequest) -> GovernanceExecutionResult:
        """Coordinate optional governance components for one execution."""
        with self._lock:
            if not self._enabled:
                result = _build_disabled_result(request)
            else:
                result = self._coordinate(request)
            self._results.append(result)
            return result

    def get_result(self, execution_id: str) -> GovernanceExecutionResult | None:
        """Return the latest orchestration result for an execution."""
        with self._lock:
            matches = [
                result for result in self._results if result.execution_id == execution_id
            ]
        if not matches:
            return None
        return matches[-1]

    def list_results(
        self,
        *,
        execution_id: str | None = None,
    ) -> list[GovernanceExecutionResult]:
        """Return recorded orchestration results."""
        with self._lock:
            records = list(self._results)
        if execution_id is not None:
            records = [record for record in records if record.execution_id == execution_id]
        return records

    def clear(self) -> None:
        """Remove all recorded orchestration results."""
        with self._lock:
            self._results.clear()

    def _coordinate(self, request: GovernanceExecutionRequest) -> GovernanceExecutionResult:
        metadata: dict[str, Any] = {"observation_only": True}
        enforcement_applied = False
        report_generated = False

        enforcement_result = self._evaluate_enforcement(request, metadata)
        if enforcement_result is not None:
            enforcement_applied = True

        binding_result = self._bind_enforcement(request, enforcement_result, metadata)
        policy_binding_result = self._bind_policy(request, metadata)

        route_result = self._route_request(request, metadata)
        report_generated = self._generate_report(request, metadata)

        if route_result is not None:
            return GovernanceExecutionResult(
                execution_id=request.execution_id,
                route_type=route_result.route_type,
                action=route_result.action,
                enforcement_applied=enforcement_applied,
                approval_required=route_result.approval_required,
                blocked=route_result.blocked,
                report_generated=report_generated,
                metadata=_finalize_metadata(
                    request,
                    metadata,
                    route_id=route_result.route_id,
                    binding_id=binding_result.binding_id if binding_result else None,
                    policy_binding_id=(
                        policy_binding_result.binding_id if policy_binding_result else None
                    ),
                ),
            )

        route_type, action, approval_required, blocked = _fallback_route(request)
        return GovernanceExecutionResult(
            execution_id=request.execution_id,
            route_type=route_type,
            action=action,
            enforcement_applied=enforcement_applied,
            approval_required=approval_required,
            blocked=blocked,
            report_generated=report_generated,
            metadata=_finalize_metadata(
                request,
                metadata,
                binding_id=binding_result.binding_id if binding_result else None,
                policy_binding_id=(
                    policy_binding_result.binding_id if policy_binding_result else None
                ),
            ),
        )

    def _evaluate_enforcement(
        self,
        request: GovernanceExecutionRequest,
        metadata: dict[str, Any],
    ) -> Any | None:
        if self._enforcement_pipeline is None:
            return None
        gate_result = _build_gate_result(request)
        enforcement_result = self._enforcement_pipeline.evaluate(
            EnforcementRequest(
                execution_id=request.execution_id,
                gate_result=gate_result,
                context=dict(request.metadata.get("runtime_context", {})),
                metadata={"source": "governance_orchestrator"},
            )
        )
        metadata["enforcement_id"] = enforcement_result.enforcement_id
        metadata["enforcement_status"] = enforcement_result.status
        return enforcement_result

    def _bind_enforcement(
        self,
        request: GovernanceExecutionRequest,
        enforcement_result: Any | None,
        metadata: dict[str, Any],
    ) -> Any | None:
        if self._enforcement_binder is None or enforcement_result is None:
            return None
        binding_result = self._enforcement_binder.bind(
            RuntimeBindingRequest(
                execution_id=request.execution_id,
                enforcement_result=enforcement_result,
                runtime_context=dict(request.metadata.get("runtime_context", {})),
                metadata={"source": "governance_orchestrator"},
            )
        )
        metadata["runtime_binding_id"] = binding_result.binding_id
        metadata["runtime_binding_decision"] = binding_result.decision
        return binding_result

    def _bind_policy(
        self,
        request: GovernanceExecutionRequest,
        metadata: dict[str, Any],
    ) -> Any | None:
        if self._policy_binder is None or request.policy_id is None:
            return None
        policy_version = str(request.metadata.get("policy_version", "1.0.0"))
        agent_id = str(request.metadata.get("agent_id", "unknown-agent"))
        binding_result = self._policy_binder.bind(
            PolicyBindingRequest(
                policy_id=request.policy_id,
                policy_version=policy_version,
                execution_id=request.execution_id,
                agent_id=agent_id,
                runtime_context=dict(request.metadata.get("runtime_context", {})),
                metadata={"source": "governance_orchestrator"},
            )
        )
        metadata["policy_binding_id"] = binding_result.binding_id
        metadata["policy_binding_status"] = binding_result.status
        return binding_result

    def _route_request(
        self,
        request: GovernanceExecutionRequest,
        metadata: dict[str, Any],
    ) -> Any | None:
        if self._decision_router is None:
            return None
        route_result = self._decision_router.route(
            GovernanceRouteRequest(
                execution_id=request.execution_id,
                decision_status=request.decision_status,
                enforcement_status=request.enforcement_status,
                policy_id=request.policy_id,
                metadata=dict(request.metadata),
            )
        )
        metadata["route_id"] = route_result.route_id
        metadata["route_reason"] = route_result.reason
        return route_result

    def _generate_report(
        self,
        request: GovernanceExecutionRequest,
        metadata: dict[str, Any],
    ) -> bool:
        if self._report_generator is None:
            return False
        evidence = request.metadata.get("evidence")
        decision = request.metadata.get("governance_decision")
        action = request.metadata.get("governance_action")
        if evidence is None or decision is None or action is None:
            return False
        approval = request.metadata.get("approval_decision")
        try:
            report = self._report_generator.generate(
                evidence,
                decision,
                action,
                approval,
            )
        except Exception:
            return False
        metadata["report_id"] = report.report_id
        metadata["report_summary"] = report.summary
        return True


def _build_disabled_result(request: GovernanceExecutionRequest) -> GovernanceExecutionResult:
    metadata = {
        "decision_status": request.decision_status,
        "orchestration_enabled": False,
        "observation_only": True,
    }
    if request.metadata:
        metadata.update(dict(request.metadata))
    return GovernanceExecutionResult(
        execution_id=request.execution_id,
        route_type="ALLOW",
        action="CONTINUE",
        enforcement_applied=False,
        approval_required=False,
        blocked=False,
        report_generated=False,
        metadata=metadata,
    )


def _build_gate_result(request: GovernanceExecutionRequest) -> GovernanceGateResult:
    import uuid

    status = _resolve_gate_status(request)
    return GovernanceGateResult(
        gate_id=uuid.uuid4().hex,
        execution_id=request.execution_id,
        status=status,
        reason=f"governance orchestrator gate for {request.decision_status.lower()}",
        metadata={"source": "governance_orchestrator"},
    )


def _resolve_gate_status(request: GovernanceExecutionRequest) -> str:
    if request.enforcement_status is not None and request.enforcement_status.upper() == "BLOCK":
        return "BLOCK"
    decision_status = request.decision_status.upper()
    if decision_status == "DENY":
        return "BLOCK"
    if decision_status in {"ALLOW", "WARN", "REQUIRE_APPROVAL", "BLOCK"}:
        return decision_status
    return "ALLOW"


def _fallback_route(
    request: GovernanceExecutionRequest,
) -> tuple[
    GovernanceOrchestratorRouteType,
    GovernanceOrchestratorAction,
    bool,
    bool,
]:
    if request.enforcement_status is not None and request.enforcement_status.upper() == "BLOCK":
        return ("BLOCK", "BLOCK", False, True)
    decision_status = request.decision_status.upper()
    if decision_status == "DENY":
        return ("BLOCK", "BLOCK", False, True)
    if decision_status == "ALLOW":
        return ("ALLOW", "CONTINUE", False, False)
    if decision_status == "WARN":
        return ("WARNING", "CONTINUE_WITH_WARNING", False, False)
    if decision_status == "REQUIRE_APPROVAL":
        return ("APPROVAL", "WAIT_APPROVAL", True, False)
    return ("UNKNOWN", "NO_ACTION", False, False)


def _finalize_metadata(
    request: GovernanceExecutionRequest,
    metadata: dict[str, Any],
    *,
    route_id: str | None = None,
    binding_id: str | None = None,
    policy_binding_id: str | None = None,
) -> dict[str, Any]:
    finalized = {
        "decision_status": request.decision_status,
        **metadata,
    }
    if request.enforcement_status is not None:
        finalized["request_enforcement_status"] = request.enforcement_status
    if request.policy_id is not None:
        finalized["policy_id"] = request.policy_id
    if route_id is not None:
        finalized.setdefault("route_id", route_id)
    if binding_id is not None:
        finalized.setdefault("runtime_binding_id", binding_id)
    if policy_binding_id is not None:
        finalized.setdefault("policy_binding_id", policy_binding_id)
    if request.metadata:
        finalized.update(
            {
                key: value
                for key, value in request.metadata.items()
                if key
                not in {
                    "evidence",
                    "governance_decision",
                    "governance_action",
                    "approval_decision",
                }
            }
        )
    return finalized
