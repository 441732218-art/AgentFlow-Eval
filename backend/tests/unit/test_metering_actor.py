# (c) 2026 AgentFlow-Eval
"""observe_* metering must accept and forward actor."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from app.core.observability.metrics import observe_judge, observe_suite_run


def test_observe_suite_run_passes_actor_to_meter():
    meter = MagicMock()
    with patch("app.core.profiles.get_meter", return_value=meter):
        with patch(
            "app.core.observability.metrics._metrics_enabled", return_value=False
        ):
            observe_suite_run(
                status="success",
                duration_seconds=1.2,
                total_tokens=42,
                actor="alice",
                ref_id="trace-1",
            )
    meter.record.assert_called()
    kwargs = meter.record.call_args.kwargs
    assert kwargs["actor"] == "alice"
    assert kwargs["metric"] == "token"
    assert kwargs["quantity"] == 42.0
    assert kwargs["ref_id"] == "trace-1"


def test_observe_judge_passes_actor():
    meter = MagicMock()
    with patch("app.core.profiles.get_meter", return_value=meter):
        with patch(
            "app.core.observability.metrics._metrics_enabled", return_value=False
        ):
            observe_judge(
                mode="rule_only",
                status="ok",
                duration_seconds=0.5,
                token_cost=10,
                actor="bob",
                ref_id="tr-2",
            )
    actors = {c.kwargs.get("actor") for c in meter.record.call_args_list}
    assert "bob" in actors
