# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Governance report generation."""

from __future__ import annotations

import uuid

from app.runtime.evidence.models import ExecutionEvidence
from app.runtime.governance.approval.models import ApprovalDecision
from app.runtime.governance.enforcement.models import GovernanceAction
from app.runtime.governance.models import GovernanceDecision
from app.runtime.governance.reporting.models import GovernanceReport, GovernanceRiskLevel


class GovernanceReportGenerator:
    """Aggregate governance artifacts into a read-only report."""

    def generate(
        self,
        evidence: ExecutionEvidence,
        decision: GovernanceDecision,
        action: GovernanceAction,
        approval: ApprovalDecision | None = None,
    ) -> GovernanceReport:
        """Build a governance report without modifying source objects."""
        risk_level = self._resolve_risk_level(
            evidence=evidence,
            decision=decision,
            action=action,
            approval=approval,
        )
        approval_status = self._resolve_approval_status(approval)
        evidence_count = self._count_evidence_items(evidence)
        summary = self._build_summary(
            evidence=evidence,
            decision=decision,
            action=action,
            approval=approval,
            risk_level=risk_level,
        )
        metadata = {
            "decision_id": decision.decision_id,
            "action_id": action.action_id,
            "action_type": action.action_type,
            "evidence_id": evidence.evidence_id,
            "evidence_status": evidence.status,
        }
        if approval is not None:
            metadata["approval_request_id"] = approval.request_id
            metadata["approver"] = approval.approver

        return GovernanceReport(
            report_id=uuid.uuid4().hex,
            execution_id=evidence.execution_id,
            agent_id=evidence.agent_id,
            risk_level=risk_level,
            decision_status=decision.status,
            approval_status=approval_status,
            summary=summary,
            evidence_count=evidence_count,
            metadata=metadata,
        )

    @staticmethod
    def _resolve_risk_level(
        *,
        evidence: ExecutionEvidence,
        decision: GovernanceDecision,
        action: GovernanceAction,
        approval: ApprovalDecision | None,
    ) -> GovernanceRiskLevel:
        if decision.status == "DENY" or action.action_type == "BLOCK":
            if approval is not None and approval.decision == "APPROVE":
                return "HIGH"
            return "CRITICAL"
        if decision.status == "WARN" or action.action_type == "WARN":
            return "MEDIUM"
        if evidence.status == "FAILED":
            return "HIGH"
        if evidence.permission_decisions:
            return "MEDIUM"
        return "LOW"

    @staticmethod
    def _resolve_approval_status(approval: ApprovalDecision | None) -> str | None:
        if approval is None:
            return None
        if approval.decision == "APPROVE":
            return "APPROVED"
        return "REJECTED"

    @staticmethod
    def _count_evidence_items(evidence: ExecutionEvidence) -> int:
        event_count = evidence.event_summary.total_events if evidence.event_summary else 0
        return (
            1
            + len(evidence.audit_records)
            + len(evidence.permission_decisions)
            + event_count
        )

    @staticmethod
    def _build_summary(
        *,
        evidence: ExecutionEvidence,
        decision: GovernanceDecision,
        action: GovernanceAction,
        approval: ApprovalDecision | None,
        risk_level: GovernanceRiskLevel,
    ) -> str:
        parts = [
            f"execution={evidence.execution_id}",
            f"decision={decision.status}",
            f"action={action.action_type}",
            f"risk={risk_level}",
        ]
        if decision.reasons:
            parts.append(f"reasons={'; '.join(decision.reasons)}")
        if approval is not None:
            parts.append(f"approval={approval.decision}")
        return " | ".join(parts)
