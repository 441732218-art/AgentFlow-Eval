# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""In-memory runtime governance decision engine."""

from __future__ import annotations

import threading
from dataclasses import dataclass

from app.runtime.evidence.models import ExecutionEvidence
from app.runtime.governance.evaluator import GovernanceEvaluator
from app.runtime.governance.models import GovernanceDecision, GovernanceRule as GovernanceRuleSpec
from app.runtime.governance.rules import GovernanceRule


@dataclass(frozen=True)
class _RegisteredRule:
    """Registered governance rule metadata and evaluator."""

    spec: GovernanceRuleSpec
    evaluator: GovernanceRule


class InMemoryGovernanceEngine:
    """Thread-safe in-memory governance decision engine."""

    def __init__(self) -> None:
        self._rules: dict[str, _RegisteredRule] = {}
        self._lock = threading.Lock()
        self._evaluator = GovernanceEvaluator()

    def register_rule(
        self,
        spec: GovernanceRuleSpec,
        evaluator: GovernanceRule,
    ) -> None:
        """Register a governance rule and its evaluator."""
        with self._lock:
            self._rules[spec.rule_id] = _RegisteredRule(spec=spec, evaluator=evaluator)

    def remove_rule(self, rule_id: str) -> None:
        """Remove a registered governance rule."""
        with self._lock:
            self._rules.pop(rule_id, None)

    def list_rules(self) -> list[GovernanceRuleSpec]:
        """Return registered governance rule metadata sorted by rule id."""
        with self._lock:
            specs = [entry.spec for entry in self._rules.values()]
        return sorted(specs, key=lambda spec: spec.rule_id)

    def evaluate(self, evidence: ExecutionEvidence) -> GovernanceDecision:
        """Evaluate evidence against all enabled registered rules."""
        with self._lock:
            enabled = [
                entry.evaluator
                for entry in self._rules.values()
                if entry.spec.enabled
            ]
        return self._evaluator.evaluate(evidence, enabled)
