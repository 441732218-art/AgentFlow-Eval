# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Governance lifecycle orchestration manager."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Protocol

from app.runtime.evidence.models import ExecutionEvidence
from app.runtime.governance.approval.store import ApprovalStore
from app.runtime.governance.enforcement.enforcer import GovernanceEnforcer
from app.runtime.governance.evaluator import GovernanceEvaluator
from app.runtime.governance.lifecycle.models import (
    GovernanceLifecycleContext,
    GovernanceLifecycleResult,
)
from app.runtime.governance.memory_engine import InMemoryGovernanceEngine
from app.runtime.governance.models import GovernanceDecision
from app.runtime.governance.reporting.generator import GovernanceReportGenerator
from app.runtime.governance.rules import GovernanceRule


class _DecisionEngine(Protocol):
    """Protocol for components that evaluate execution evidence."""

    def evaluate(self, evidence: ExecutionEvidence) -> GovernanceDecision:
        """Evaluate evidence and return a governance decision."""


class GovernanceLifecycleManager:
    """Coordinate governance evaluation, enforcement, approval, and reporting."""

    def __init__(
        self,
        *,
        decision_engine: GovernanceEvaluator | InMemoryGovernanceEngine,
        enforcer: GovernanceEnforcer,
        report_generator: GovernanceReportGenerator | None = None,
        approval_store: ApprovalStore | None = None,
        rules: Sequence[GovernanceRule] | None = None,
    ) -> None:
        self._decision_engine = decision_engine
        self._enforcer = enforcer
        self._report_generator = report_generator or GovernanceReportGenerator()
        self._approval_store = approval_store
        self._rules = tuple(rules or ())

    def start(self, context: GovernanceLifecycleContext) -> GovernanceLifecycleContext:
        """Initialize lifecycle orchestration metadata."""
        metadata = dict(context.metadata)
        metadata["lifecycle_status"] = "STARTED"
        return context.with_updates(metadata=metadata)

    def evaluate(self, context: GovernanceLifecycleContext) -> GovernanceLifecycleContext:
        """Evaluate governance evidence and attach the resulting decision."""
        evidence = self._require_evidence(context)
        decision = self._evaluate_evidence(evidence)
        metadata = dict(context.metadata)
        metadata["lifecycle_status"] = "EVALUATED"
        return context.with_updates(decision=decision, metadata=metadata)

    def apply_action(self, context: GovernanceLifecycleContext) -> GovernanceLifecycleContext:
        """Translate the governance decision into an enforcement action."""
        decision = self._require_decision(context)
        action = self._enforcer.enforce(decision)
        metadata = dict(context.metadata)
        metadata["lifecycle_status"] = "ENFORCED"
        return context.with_updates(action=action, metadata=metadata)

    def generate_report(
        self,
        context: GovernanceLifecycleContext,
    ) -> tuple[GovernanceLifecycleContext, GovernanceLifecycleResult]:
        """Generate a governance report and lifecycle result."""
        evidence = self._require_evidence(context)
        decision = self._require_decision(context)
        action = self._require_action(context)
        approval = self._resolve_approval(context)
        report = self._report_generator.generate(
            evidence,
            decision,
            action,
            approval,
        )
        metadata = dict(context.metadata)
        metadata["lifecycle_status"] = "REPORTED"
        updated_context = context.with_updates(report=report, metadata=metadata)
        result = GovernanceLifecycleResult(
            execution_id=context.execution_id,
            final_status=_resolve_final_status(action.action_type, approval),
            decision_status=decision.status,
            action_type=action.action_type,
            approval_status=_resolve_approval_status(approval),
            report_id=report.report_id,
            metadata={
                "risk_level": report.risk_level,
                "summary": report.summary,
            },
        )
        return updated_context, result

    def _evaluate_evidence(self, evidence: ExecutionEvidence) -> GovernanceDecision:
        if isinstance(self._decision_engine, InMemoryGovernanceEngine):
            return self._decision_engine.evaluate(evidence)
        return self._decision_engine.evaluate(evidence, self._rules)

    def _resolve_approval(
        self,
        context: GovernanceLifecycleContext,
    ) -> Any | None:
        if context.approval is not None:
            return context.approval
        if self._approval_store is None:
            return None
        pending = self._approval_store.list_pending()
        for request in pending:
            if request.execution_id == context.execution_id:
                decisions = self._approval_store.get_decisions(request.request_id)
                if decisions:
                    return decisions[-1]
        return None

    @staticmethod
    def _require_evidence(context: GovernanceLifecycleContext) -> ExecutionEvidence:
        if context.evidence is None:
            raise ValueError("Governance lifecycle evidence is required")
        return context.evidence

    @staticmethod
    def _require_decision(context: GovernanceLifecycleContext) -> GovernanceDecision:
        if context.decision is None:
            raise ValueError("Governance lifecycle decision is required")
        return context.decision

    @staticmethod
    def _require_action(context: GovernanceLifecycleContext) -> GovernanceAction:
        if context.action is None:
            raise ValueError("Governance lifecycle action is required")
        return context.action


def _resolve_final_status(action_type: str, approval: Any | None) -> str:
    if action_type == "BLOCK":
        if approval is not None and approval.decision == "APPROVE":
            return "APPROVED_OVERRIDE"
        return "BLOCKED"
    if action_type == "WARN":
        return "WARN"
    return "ALLOWED"


def _resolve_approval_status(approval: Any | None) -> str | None:
    if approval is None:
        return None
    if approval.decision == "APPROVE":
        return "APPROVED"
    return "REJECTED"
