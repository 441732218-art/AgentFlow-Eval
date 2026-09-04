# AgentFlow Intelligence v2.0 — Agent Runtime Platform
"""Default runtime assembly profiles."""

from __future__ import annotations

from app.runtime.assembly.models import RuntimeProfile

DEVELOPMENT_PROFILE = RuntimeProfile(
    name="development",
    environment="development",
    enable_governance=True,
    enable_observation=True,
    enable_audit=True,
    enable_agent_registry=True,
    enable_tool_registry=True,
    enable_permission_evaluator=True,
    enable_execution_state=True,
    enable_checkpoint=True,
    enable_memory_context=True,
    enable_runtime_context=True,
    enable_correlation=True,
    enable_analytics=True,
    enable_event_stream=True,
    enable_audit_recorder=True,
    enable_evidence_collector=True,
    enable_governance_lifecycle=True,
    enable_governance_runtime=True,
    enable_governance_activation=True,
)

PRODUCTION_PROFILE = RuntimeProfile(
    name="production",
    environment="production",
    enable_governance=True,
    enable_observation=True,
    enable_audit=True,
    enable_agent_registry=True,
    enable_tool_registry=True,
    enable_permission_evaluator=True,
    enable_execution_state=True,
    enable_checkpoint=True,
    enable_memory_context=True,
    enable_runtime_context=True,
    enable_correlation=True,
    enable_analytics=True,
    enable_event_stream=True,
    enable_audit_recorder=True,
    enable_evidence_collector=True,
    enable_governance_lifecycle=True,
    enable_governance_runtime=True,
    enable_governance_activation=True,
)

TESTING_PROFILE = RuntimeProfile(
    name="testing",
    environment="test",
    enable_governance=False,
    enable_observation=True,
    enable_audit=False,
    enable_agent_registry=True,
    enable_tool_registry=True,
    enable_permission_evaluator=False,
    enable_execution_state=False,
    enable_checkpoint=False,
    enable_memory_context=False,
    enable_runtime_context=False,
    enable_correlation=False,
    enable_analytics=False,
    enable_event_stream=False,
    enable_audit_recorder=False,
    enable_evidence_collector=False,
    enable_governance_lifecycle=False,
)

_PROFILES: dict[str, RuntimeProfile] = {
    DEVELOPMENT_PROFILE.name: DEVELOPMENT_PROFILE,
    PRODUCTION_PROFILE.name: PRODUCTION_PROFILE,
    TESTING_PROFILE.name: TESTING_PROFILE,
}


def get_profile(name: str) -> RuntimeProfile:
    """Return a named profile or raise ``KeyError``."""
    try:
        return _PROFILES[name]
    except KeyError as exc:
        raise KeyError(f"Unknown runtime profile: {name}") from exc


def list_profiles() -> tuple[str, ...]:
    """Return registered profile names."""
    return tuple(_PROFILES)
