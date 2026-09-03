# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Runtime governance decision evaluator."""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from app.runtime.evidence.models import ExecutionEvidence
from app.runtime.governance.models import GovernanceDecision, GovernanceDecisionStatus
from app.runtime.governance.rules import GovernanceRule


class GovernanceEvaluator:
    """Execute governance rules and aggregate their decisions."""

    def evaluate(
        self,
        evidence: ExecutionEvidence,
        rules: Sequence[GovernanceRule],
    ) -> GovernanceDecision:
        """Evaluate evidence against rules and return an aggregated decision."""
        rule_decisions = [rule.evaluate(evidence) for rule in rules]
        return self.aggregate(evidence, rule_decisions)

    def aggregate(
        self,
        evidence: ExecutionEvidence,
        decisions: Sequence[GovernanceDecision],
    ) -> GovernanceDecision:
        """Aggregate rule decisions using DENY > WARN > ALLOW priority."""
        if not decisions:
            return GovernanceDecision(
                decision_id=uuid.uuid4().hex,
                execution_id=evidence.execution_id,
                agent_id=evidence.agent_id,
                status="ALLOW",
            )

        statuses = [decision.status for decision in decisions]
        final_status = self._resolve_status(statuses)
        reasons = tuple(reason for decision in decisions for reason in decision.reasons)
        metadata: dict[str, object] = {
            "rule_count": len(decisions),
            "statuses": [decision.status for decision in decisions],
        }
        for index, decision in enumerate(decisions):
            if decision.metadata:
                metadata[f"rule_{index}"] = dict(decision.metadata)

        return GovernanceDecision(
            decision_id=uuid.uuid4().hex,
            execution_id=evidence.execution_id,
            agent_id=evidence.agent_id,
            status=final_status,
            reasons=reasons,
            metadata=metadata,
        )

    @staticmethod
    def _resolve_status(statuses: Sequence[GovernanceDecisionStatus]) -> GovernanceDecisionStatus:
        if any(status == "DENY" for status in statuses):
            return "DENY"
        if any(status == "WARN" for status in statuses):
            return "WARN"
        return "ALLOW"
