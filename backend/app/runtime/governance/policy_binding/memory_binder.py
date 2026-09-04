# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""In-memory policy execution binder."""

from __future__ import annotations

import threading
import uuid
from typing import TYPE_CHECKING, Any

from app.runtime.governance.policy_binding.binder import PolicyExecutionBinder
from app.runtime.governance.policy_binding.models import (
    PolicyBindingRequest,
    PolicyBindingResult,
    PolicyBindingStatus,
)

if TYPE_CHECKING:
    from app.runtime.governance.versioning.registry import GovernancePolicyRegistry

_BINDING_KEY_SEPARATOR = "\x1f"


class InMemoryPolicyExecutionBinder:
    """Thread-safe in-memory policy execution binder."""

    def __init__(
        self,
        *,
        enabled: bool = True,
        policy_registry: GovernancePolicyRegistry | None = None,
    ) -> None:
        self._enabled = enabled
        self._policy_registry = policy_registry
        self._bindings: dict[str, PolicyBindingResult] = {}
        self._lock = threading.Lock()

    @property
    def enabled(self) -> bool:
        return self._enabled

    def set_enabled(self, enabled: bool) -> None:
        """Enable or disable policy execution binding."""
        with self._lock:
            self._enabled = enabled

    def bind(self, request: PolicyBindingRequest) -> PolicyBindingResult:
        """Bind a policy version to an execution observation record."""
        with self._lock:
            if not self._enabled:
                result = self._build_result(
                    request,
                    status="DISABLED",
                    applied=False,
                    extra_metadata={"binding_enabled": False},
                )
            else:
                policy_status = self._resolve_policy_status(request)
                if policy_status == "NOT_FOUND":
                    result = self._build_result(
                        request,
                        status="NOT_FOUND",
                        applied=False,
                    )
                elif policy_status == "DISABLED":
                    result = self._build_result(
                        request,
                        status="DISABLED",
                        applied=False,
                        extra_metadata={"policy_status": "DISABLED"},
                    )
                else:
                    result = self._build_result(
                        request,
                        status="BOUND",
                        applied=True,
                        extra_metadata={"observation_only": True},
                    )
            self._bindings[_binding_key(request)] = result
            return result

    def get_binding(
        self,
        execution_id: str,
        policy_id: str,
        policy_version: str,
    ) -> PolicyBindingResult | None:
        """Return one recorded binding by execution and policy identity."""
        with self._lock:
            return self._bindings.get(
                _binding_key_from_parts(execution_id, policy_id, policy_version)
            )

    def list_bindings(
        self,
        *,
        execution_id: str | None = None,
        policy_id: str | None = None,
    ) -> list[PolicyBindingResult]:
        """Return recorded policy binding results."""
        with self._lock:
            records = list(self._bindings.values())
        if execution_id is not None:
            records = [record for record in records if record.execution_id == execution_id]
        if policy_id is not None:
            records = [record for record in records if record.policy_id == policy_id]
        return records

    def clear(self) -> None:
        """Remove all recorded policy binding results."""
        with self._lock:
            self._bindings.clear()

    def _resolve_policy_status(self, request: PolicyBindingRequest) -> PolicyBindingStatus:
        if self._policy_registry is None:
            return "BOUND"
        policy_version = self._policy_registry.get(
            request.policy_id,
            request.policy_version,
        )
        if policy_version is None:
            return "NOT_FOUND"
        if policy_version.status == "DISABLED":
            return "DISABLED"
        return "BOUND"

    def _build_result(
        self,
        request: PolicyBindingRequest,
        *,
        status: PolicyBindingStatus,
        applied: bool,
        extra_metadata: dict[str, Any] | None = None,
    ) -> PolicyBindingResult:
        return PolicyBindingResult(
            binding_id=uuid.uuid4().hex,
            policy_id=request.policy_id,
            policy_version=request.policy_version,
            execution_id=request.execution_id,
            status=status,
            applied=applied,
            metadata=_build_metadata(request, status=status, extra=extra_metadata),
        )


def _binding_key(request: PolicyBindingRequest) -> str:
    return _binding_key_from_parts(
        request.execution_id,
        request.policy_id,
        request.policy_version,
    )


def _binding_key_from_parts(
    execution_id: str,
    policy_id: str,
    policy_version: str,
) -> str:
    return _BINDING_KEY_SEPARATOR.join((execution_id, policy_id, policy_version))


def _build_metadata(
    request: PolicyBindingRequest,
    *,
    status: PolicyBindingStatus,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    metadata: dict[str, Any] = {
        "agent_id": request.agent_id,
        "binding_status": status,
    }
    if request.runtime_context:
        metadata["runtime_context"] = dict(request.runtime_context)
    if request.metadata:
        metadata.update(dict(request.metadata))
    if extra:
        metadata.update(dict(extra))
    return metadata
