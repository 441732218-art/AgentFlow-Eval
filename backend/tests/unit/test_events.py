# (c) 2026 AgentFlow-Eval
"""Unit tests for task activity events (no Redis required)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from app.core.events import build_task_event, publish_task_event, publish_task_status


def test_build_task_event_shape():
    ev = build_task_event(
        task_id="t1",
        task_name="Demo",
        status="running",
        prev_status="queued",
        actor="alice",
    )
    assert ev["type"] == "task_status"
    assert ev["task_id"] == "t1"
    assert ev["task_name"] == "Demo"
    assert ev["status"] == "running"
    assert ev["prev_status"] == "queued"
    assert ev["actor"] == "alice"
    assert "at" in ev


def test_publish_task_event_without_redis():
    """Publish should not raise when Redis is unavailable."""
    with patch("redis.from_url", side_effect=ConnectionError("no redis")):
        publish_task_event(
            build_task_event(task_id="x", task_name="n", status="completed")
        )


def test_publish_task_status_calls_publish():
    with patch("app.core.events.publish_task_event") as mock_pub:
        publish_task_status("id1", "Name", "failed", prev_status="running")
        assert mock_pub.called
        payload = mock_pub.call_args[0][0]
        assert payload["task_id"] == "id1"
        assert payload["status"] == "failed"
        assert payload["prev_status"] == "running"


def test_publish_with_mock_redis():
    client = MagicMock()
    with patch("redis.from_url", return_value=client):
        publish_task_status("id2", "T", "queued")
        assert client.publish.called
        client.close.assert_called()
