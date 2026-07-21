# (c) 2026 AgentFlow-Eval
"""Unit tests for AOLS structured logging (Phase 2)."""

from __future__ import annotations


from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.middleware import RequestIDMiddleware
from app.core.observability.aols.context import (
    bind_request_context,
    clear_request_context,
    get_bound_context,
    new_error_id,
)
from app.core.observability.aols.events import LogEvent
from app.core.observability.aols.logger import get_logger, setup_aols_logging
from app.core.observability.aols.redaction import redact_mapping, redact_value
from app.utils.exceptions import error_response


class TestRedaction:
    def test_redacts_api_key_and_password(self):
        raw = {
            "user": "alice",
            "password": "s3cret",
            "openai_api_key": "sk-xxx",
            "nested": {"Authorization": "Bearer abc", "ok": 1},
        }
        out = redact_mapping(raw)
        assert out["user"] == "alice"
        assert out["password"] == "[REDACTED]"
        assert out["openai_api_key"] == "[REDACTED]"
        assert out["nested"]["Authorization"] == "[REDACTED]"
        assert out["nested"]["ok"] == 1

    def test_redact_value_truncates_long_string(self):
        s = "x" * 5000
        out = redact_value(s, max_str=100)
        assert isinstance(out, str)
        assert out.startswith("x" * 100)
        assert "chars" in out


class TestEvents:
    def test_event_wire_format(self):
        assert str(LogEvent.HTTP_REQUEST) == "http.request"
        assert LogEvent.SYSTEM_ERROR.value == "system.error"
        assert LogEvent.LLM_COMPLETED == "llm.completed"


class TestContext:
    def test_bind_and_clear(self):
        clear_request_context()
        bind_request_context(
            request_id="rid-1",
            trace_id="tid-1",
            actor="alice",
            path="/api/v1/tasks",
        )
        ctx = get_bound_context()
        assert ctx.get("request_id") == "rid-1"
        assert ctx.get("trace_id") == "tid-1"
        assert ctx.get("actor") == "alice"
        clear_request_context()
        assert get_bound_context().get("request_id") in (None, "")

    def test_error_id_length(self):
        eid = new_error_id()
        assert len(eid) == 16
        assert eid.isalnum()


class TestErrorResponse:
    def test_includes_error_id(self):
        body = error_response(500, "boom", request_id="r1", error_id="e1")
        assert body["error"]["request_id"] == "r1"
        assert body["error"]["error_id"] == "e1"


class TestLoggerSetup:
    def test_get_logger_emits_event(self, capsys):
        setup_aols_logging()
        log = get_logger("test.aols")
        # structlog BoundLogger
        log.info("test.event", foo="bar", password="secret")
        # Should not raise; redaction applied in processor chain when rendered


class TestRequestMiddleware:
    def test_access_log_headers(self):
        app = FastAPI()
        app.add_middleware(RequestIDMiddleware)

        @app.get("/ping")
        async def ping():
            return {"ok": True}

        client = TestClient(app)
        r = client.get("/ping", headers={"X-Request-ID": "fixed-req-id-001"})
        assert r.status_code == 200
        assert r.headers.get("X-Request-ID") == "fixed-req-id-001"
        assert r.headers.get("X-Trace-ID") == "fixed-req-id-001"

    def test_generates_request_id_when_missing(self):
        app = FastAPI()
        app.add_middleware(RequestIDMiddleware)

        @app.get("/pong")
        async def pong():
            return {"ok": True}

        client = TestClient(app)
        r = client.get("/pong")
        assert r.status_code == 200
        assert r.headers.get("X-Request-ID")
        assert r.headers.get("X-Trace-ID") == r.headers.get("X-Request-ID")
