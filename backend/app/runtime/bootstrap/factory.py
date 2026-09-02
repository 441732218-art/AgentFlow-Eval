# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Production runtime assembly factory."""

from __future__ import annotations

from dataclasses import dataclass

from app.runtime.audit.memory_store import InMemoryAuditStore
from app.runtime.bootstrap.config import RuntimeConfig
from app.runtime.events.publisher import InMemoryEventPublisher
from app.runtime.governance.lifecycle import RuntimeGovernanceLifecycle
from app.runtime.observability.collector import InMemoryObservationCollector
from app.runtime.policy.engine import InMemoryPolicyEngine
from app.runtime.tools.credential_resolver import CredentialResolver
from app.runtime.tools.engine import ToolExecutionEngine
from app.runtime.tools.factory import (
    create_env_credential_resolver,
    create_http_remote_tool_client,
    create_tool_execution_engine,
)
from app.runtime.tools.policy import RemoteExecutionPolicy


@dataclass
class ProductionRuntime:
    """Assembled production Agent Runtime instance."""

    config: RuntimeConfig
    policy_engine: InMemoryPolicyEngine
    observation_collector: InMemoryObservationCollector | None
    event_publisher: InMemoryEventPublisher | None
    audit_store: InMemoryAuditStore | None
    governance_lifecycle: RuntimeGovernanceLifecycle | None
    tool_execution_engine: ToolExecutionEngine
    credential_resolver: CredentialResolver | None


def _build_credential_resolver(
    resolver_type: str,
) -> CredentialResolver | None:
    if resolver_type == "env":
        return create_env_credential_resolver()
    return None


def create_production_runtime(
    config: RuntimeConfig | None = None,
) -> ProductionRuntime:
    """Assemble a production Agent Runtime with governance infrastructure."""
    resolved_config = config or RuntimeConfig()

    audit_store = (
        InMemoryAuditStore() if resolved_config.enable_audit else None
    )
    observation_collector = (
        InMemoryObservationCollector()
        if resolved_config.enable_observation
        else None
    )
    event_publisher: InMemoryEventPublisher | None = None
    if resolved_config.enable_observation or resolved_config.enable_audit:
        event_publisher = InMemoryEventPublisher(audit_store=audit_store)

    policy_engine = InMemoryPolicyEngine()
    governance_lifecycle = (
        RuntimeGovernanceLifecycle()
        if resolved_config.enable_governance
        else None
    )

    credential_resolver = _build_credential_resolver(
        resolved_config.credential_resolver_type
    )
    remote_policy = RemoteExecutionPolicy()
    remote_client = create_http_remote_tool_client(
        remote_policy=remote_policy,
        credential_resolver=credential_resolver,
    )
    tool_execution_engine = create_tool_execution_engine(
        remote_client=remote_client,
        remote_policy=remote_policy,
    )

    return ProductionRuntime(
        config=resolved_config,
        policy_engine=policy_engine,
        observation_collector=observation_collector,
        event_publisher=event_publisher,
        audit_store=audit_store,
        governance_lifecycle=governance_lifecycle,
        tool_execution_engine=tool_execution_engine,
        credential_resolver=credential_resolver,
    )
