# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Tool lifecycle governance hook adapter."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from app.runtime.evidence.models import ExecutionEvidence
from app.runtime.governance.lifecycle.manager import GovernanceLifecycleManager
from app.runtime.governance.lifecycle.models import GovernanceLifecycleContext
from app.runtime.governance.tool_hooks.models import ToolGovernanceHookContext
from app.runtime.hooks.hook import RuntimeHook
from app.runtime.hooks.models import TOOL_COMPLETED, TOOL_FAILED, TOOL_STARTED, RuntimeHookEvent
from app.runtime.policy.models import PolicyDecision
from app.runtime.tool_registry.models import ToolCapability

if TYPE_CHECKING:
    from app.runtime.audit.recorder import RuntimeAuditRecorder
    from app.runtime.evidence.collector import RuntimeEvidenceCollector
    from app.runtime.permissions.evaluator import PermissionEvaluator


def tool_governance_hook_context_from_event(event: RuntimeHookEvent) -> ToolGovernanceHookContext:
    """Convert a runtime hook event into a tool governance hook context."""
    payload = dict(event.payload)
    tool_name = str(payload.pop("tool_name", payload.get("tool_id", "unknown-tool")))
    return ToolGovernanceHookContext(
        execution_id=event.execution_id,
        agent_id=event.agent_id,
        tool_name=tool_name,
        event_type=event.event_type,
        timestamp=event.timestamp,
        metadata=payload,
    )


class ToolLifecycleGovernanceAdapter(RuntimeHook):
    """Bridge tool lifecycle hooks into permission and governance observation."""

    def __init__(
        self,
        governance_lifecycle_manager: GovernanceLifecycleManager,
        permission_evaluator: PermissionEvaluator | None = None,
        *,
        evidence_collector: RuntimeEvidenceCollector | None = None,
        audit_recorder: RuntimeAuditRecorder | None = None,
    ) -> None:
        self._governance_lifecycle_manager = governance_lifecycle_manager
        self._permission_evaluator = permission_evaluator
        self._evidence_collector = evidence_collector
        self._audit_recorder = audit_recorder
        self._contexts: dict[str, GovernanceLifecycleContext] = {}

    @property
    def governance_lifecycle_manager(self) -> GovernanceLifecycleManager:
        return self._governance_lifecycle_manager

    @property
    def permission_evaluator(self) -> PermissionEvaluator | None:
        return self._permission_evaluator

    def before_tool(self, event: RuntimeHookEvent) -> None:
        if event.event_type == TOOL_STARTED:
            self._observe_tool_started(event)

    def after_tool(self, event: RuntimeHookEvent) -> None:
        if event.event_type == TOOL_COMPLETED:
            self._observe_tool_completed(event)

    def on_failure(self, event: RuntimeHookEvent) -> None:
        if event.event_type == TOOL_FAILED:
            self._observe_tool_failed(event)

    def get_lifecycle_context(
        self,
        execution_id: str,
        tool_name: str,
    ) -> GovernanceLifecycleContext | None:
        """Return the latest observed lifecycle context for a tool invocation."""
        return self._contexts.get(_context_key(execution_id, tool_name))

    def _observe_tool_started(self, event: RuntimeHookEvent) -> None:
        try:
            hook_context = tool_governance_hook_context_from_event(event)
            permission_result = self._observe_permission(hook_context)
            lifecycle_context = GovernanceLifecycleContext(
                execution_id=hook_context.execution_id,
                metadata=self._build_lifecycle_metadata(hook_context, permission_result),
            )
            started = self._governance_lifecycle_manager.start(lifecycle_context)
            self._contexts[_context_key(hook_context.execution_id, hook_context.tool_name)] = (
                started
            )
            self._record_governance_audit(
                hook_context,
                lifecycle_context=started,
                phase="tool.started",
            )
        except Exception:
            return

    def _observe_tool_completed(self, event: RuntimeHookEvent) -> None:
        self._observe_tool_end(event, status="COMPLETED")

    def _observe_tool_failed(self, event: RuntimeHookEvent) -> None:
        self._observe_tool_end(event, status="FAILED")

    def _observe_tool_end(self, event: RuntimeHookEvent, *, status: str) -> None:
        try:
            hook_context = tool_governance_hook_context_from_event(event)
            context_key = _context_key(hook_context.execution_id, hook_context.tool_name)
            lifecycle_context = self._contexts.get(context_key)
            if lifecycle_context is None:
                lifecycle_context = GovernanceLifecycleContext(
                    execution_id=hook_context.execution_id,
                    metadata=self._build_lifecycle_metadata(hook_context),
                )
            evidence = self._resolve_evidence(event, hook_context, status=status)
            if evidence is None:
                return
            evaluated = self._governance_lifecycle_manager.evaluate(
                lifecycle_context.with_updates(
                    evidence=evidence,
                    metadata={
                        **lifecycle_context.metadata,
                        "event_type": hook_context.event_type,
                        "tool_status": status,
                        **hook_context.metadata,
                    },
                )
            )
            self._contexts[context_key] = evaluated
            self._record_governance_audit(
                hook_context,
                lifecycle_context=evaluated,
                phase=f"tool.{status.lower()}",
            )
        except Exception:
            return

    def _observe_permission(
        self,
        hook_context: ToolGovernanceHookContext,
    ) -> PolicyDecision | None:
        if self._permission_evaluator is None:
            return None
        capability = _tool_capability_from_metadata(
            hook_context.tool_name,
            hook_context.metadata,
        )
        decision = self._permission_evaluator.evaluate_tool_access(None, capability)
        self._record_permission_audit(hook_context, decision)
        return decision

    def _record_permission_audit(
        self,
        hook_context: ToolGovernanceHookContext,
        decision: PolicyDecision,
    ) -> None:
        if self._audit_recorder is None:
            return
        try:
            self._audit_recorder.record_permission_event(
                event_type=hook_context.event_type,
                execution_id=hook_context.execution_id,
                agent_id=hook_context.agent_id,
                correlation_id=_optional_str(hook_context.metadata.get("correlation_id")),
                resource=hook_context.tool_name,
                decision="ALLOW" if decision.allowed else "DENY",
                severity="INFO" if decision.allowed else "WARNING",
                metadata={
                    "tool_name": hook_context.tool_name,
                    "policy_name": decision.policy_name,
                    "reason": decision.reason,
                    "observation_only": True,
                },
            )
        except Exception:
            return

    def _record_governance_audit(
        self,
        hook_context: ToolGovernanceHookContext,
        *,
        lifecycle_context: GovernanceLifecycleContext,
        phase: str,
    ) -> None:
        if self._audit_recorder is None:
            return
        try:
            decision = lifecycle_context.decision
            self._audit_recorder.record_governance_event(
                event_type=hook_context.event_type,
                execution_id=hook_context.execution_id,
                agent_id=hook_context.agent_id,
                correlation_id=_optional_str(hook_context.metadata.get("correlation_id")),
                action=phase,
                resource=hook_context.tool_name,
                decision=decision.status if decision is not None else "UNKNOWN",
                metadata={
                    "tool_name": hook_context.tool_name,
                    "phase": phase,
                    "observation_only": True,
                    **(
                        {"governance_reasons": list(decision.reasons)}
                        if decision is not None
                        else {}
                    ),
                },
            )
        except Exception:
            return

    def _build_lifecycle_metadata(
        self,
        hook_context: ToolGovernanceHookContext,
        permission_result: PolicyDecision | None = None,
    ) -> dict[str, Any]:
        metadata = {
            "agent_id": hook_context.agent_id,
            "tool_name": hook_context.tool_name,
            "event_type": hook_context.event_type,
            **hook_context.metadata,
        }
        if permission_result is not None:
            metadata["permission_allowed"] = permission_result.allowed
            metadata["permission_policy_name"] = permission_result.policy_name
            if permission_result.reason is not None:
                metadata["permission_reason"] = permission_result.reason
        return metadata

    def _resolve_evidence(
        self,
        event: RuntimeHookEvent,
        hook_context: ToolGovernanceHookContext,
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
            correlation_id=_optional_str(hook_context.metadata.get("correlation_id")),
            status=status,  # type: ignore[arg-type]
        )


def _context_key(execution_id: str, tool_name: str) -> str:
    return f"{execution_id}:{tool_name}"


def _tool_capability_from_metadata(
    tool_name: str,
    metadata: dict[str, Any],
) -> ToolCapability:
    permission_scope = metadata.get("permission_scope", ())
    if isinstance(permission_scope, list):
        permission_scope = tuple(permission_scope)
    capability_tags = metadata.get("capability_tags", ())
    if isinstance(capability_tags, list):
        capability_tags = tuple(capability_tags)
    return ToolCapability(
        tool_name=tool_name,
        version=str(metadata.get("version", "1.0")),
        description=str(metadata.get("description", tool_name)),
        capability_tags=capability_tags,
        permission_scope=permission_scope,
        enabled=bool(metadata.get("enabled", True)),
        metadata={
            key: value
            for key, value in metadata.items()
            if key
            not in {
                "version",
                "description",
                "permission_scope",
                "capability_tags",
                "enabled",
            }
        },
    )


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)
