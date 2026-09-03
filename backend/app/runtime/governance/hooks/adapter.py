# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Governance runtime hook adapter."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from app.runtime.evidence.models import ExecutionEvidence
from app.runtime.governance.hooks.models import GovernanceHookContext
from app.runtime.governance.lifecycle.manager import GovernanceLifecycleManager
from app.runtime.governance.lifecycle.models import GovernanceLifecycleContext
from app.runtime.hooks.hook import RuntimeHook
from app.runtime.hooks.models import EXECUTION_COMPLETED, EXECUTION_FAILED, RuntimeHookEvent

if TYPE_CHECKING:
    from app.runtime.evidence.collector import RuntimeEvidenceCollector


def governance_hook_context_from_event(event: RuntimeHookEvent) -> GovernanceHookContext:
    """Convert a runtime hook event into a governance hook context."""
    return GovernanceHookContext(
        execution_id=event.execution_id,
        agent_id=event.agent_id,
        event_type=event.event_type,
        timestamp=event.timestamp,
        payload=dict(event.payload),
    )


class GovernanceRuntimeHookAdapter(RuntimeHook):
    """Bridge runtime lifecycle hooks into governance lifecycle observation."""

    def __init__(
        self,
        governance_lifecycle_manager: GovernanceLifecycleManager,
        *,
        evidence_collector: RuntimeEvidenceCollector | None = None,
    ) -> None:
        self._governance_lifecycle_manager = governance_lifecycle_manager
        self._evidence_collector = evidence_collector
        self._contexts: dict[str, GovernanceLifecycleContext] = {}

    @property
    def governance_lifecycle_manager(self) -> GovernanceLifecycleManager:
        return self._governance_lifecycle_manager

    def before_execution(self, event: RuntimeHookEvent) -> None:
        self._observe_started(event)

    def after_execution(self, event: RuntimeHookEvent) -> None:
        if event.event_type == EXECUTION_COMPLETED:
            self._observe_completed(event)

    def on_failure(self, event: RuntimeHookEvent) -> None:
        if event.event_type == EXECUTION_FAILED:
            self._observe_failed(event)

    def get_lifecycle_context(self, execution_id: str) -> GovernanceLifecycleContext | None:
        """Return the latest observed lifecycle context for an execution."""
        return self._contexts.get(execution_id)

    def _observe_started(self, event: RuntimeHookEvent) -> None:
        try:
            hook_context = governance_hook_context_from_event(event)
            lifecycle_context = GovernanceLifecycleContext(
                execution_id=hook_context.execution_id,
                metadata={
                    "agent_id": hook_context.agent_id,
                    "event_type": hook_context.event_type,
                    **hook_context.payload,
                },
            )
            self._contexts[hook_context.execution_id] = (
                self._governance_lifecycle_manager.start(lifecycle_context)
            )
        except Exception:
            return

    def _observe_completed(self, event: RuntimeHookEvent) -> None:
        self._observe_execution_end(event, status="COMPLETED")

    def _observe_failed(self, event: RuntimeHookEvent) -> None:
        self._observe_execution_end(event, status="FAILED")

    def _observe_execution_end(self, event: RuntimeHookEvent, *, status: str) -> None:
        try:
            lifecycle_context = self._contexts.get(event.execution_id)
            if lifecycle_context is None:
                hook_context = governance_hook_context_from_event(event)
                lifecycle_context = GovernanceLifecycleContext(
                    execution_id=hook_context.execution_id,
                    metadata={
                        "agent_id": hook_context.agent_id,
                        "event_type": hook_context.event_type,
                        **hook_context.payload,
                    },
                )
            evidence = self._resolve_evidence(event, status=status)
            if evidence is None:
                return
            evaluated = self._governance_lifecycle_manager.evaluate(
                lifecycle_context.with_updates(evidence=evidence)
            )
            self._contexts[event.execution_id] = evaluated
        except Exception:
            return

    def _resolve_evidence(
        self,
        event: RuntimeHookEvent,
        *,
        status: str,
    ) -> ExecutionEvidence | None:
        if self._evidence_collector is not None:
            stored = self._evidence_collector.store.get_by_execution(event.execution_id)
            if stored is not None:
                return stored
        return ExecutionEvidence(
            evidence_id=uuid.uuid4().hex,
            execution_id=event.execution_id,
            agent_id=event.agent_id,
            correlation_id=str(event.payload.get("correlation_id"))
            if event.payload.get("correlation_id") is not None
            else None,
            status=status,  # type: ignore[arg-type]
        )
