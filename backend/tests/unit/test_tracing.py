# (c) 2026 AgentFlow-Eval
from app.core.observability.tracing import (
    bind_from_mapping,
    ensure_trace_id,
    get_trace_id,
    set_trace_id,
    trace_headers,
)


def test_trace_id_roundtrip():
    set_trace_id("abc123")
    assert get_trace_id() == "abc123"
    assert trace_headers()["X-Trace-ID"] == "abc123"


def test_ensure_generates():
    set_trace_id("")
    tid = ensure_trace_id()
    assert len(tid) >= 8
    assert get_trace_id() == tid


def test_bind_from_mapping():
    set_trace_id("")
    tid = bind_from_mapping({"_trace_id": "from-job"})
    assert tid == "from-job"
    assert get_trace_id() == "from-job"
