# AgentFlow-Eval Agent自动化评测工作台 V1.0
"""Tests for agent_config masking + agent runner factory model-config pass-through."""

from unittest.mock import patch

from app.core.agent_runner.factory import build_agent_runner
from app.utils.agent_config import mask_agent_config


class TestMaskAgentConfig:
    def test_recursive_and_nested(self):
        cfg = {
            "model": "deepseek-chat",
            "api_key": "sk-test",
            "headers": {
                "Authorization": "Bearer xxx",
                "nested": {"access_token": "abc"},
            },
            "items": [{"refresh_token": "r1"}, {"password": "p1"}],
        }
        out = mask_agent_config(cfg)
        assert out["model"] == "deepseek-chat"
        assert out["api_key"] == "[REDACTED]"
        assert out["headers"]["Authorization"] == "[REDACTED]"
        assert out["headers"]["nested"]["access_token"] == "[REDACTED]"
        assert out["items"][0]["refresh_token"] == "[REDACTED]"
        assert out["items"][1]["password"] == "[REDACTED]"

    def test_sensitive_key_coverage_and_case_insensitive(self):
        cfg = {
            "api_key": "1",
            "apikey": "2",
            "api-key": "3",
            "token": "4",
            "access_token": "5",
            "access-token": "6",
            "refresh_token": "7",
            "refresh-token": "8",
            "authorization": "9",
            "Authorization": "10",
            "secret": "11",
            "password": "12",
            "passwd": "13",
            "private_key": "14",
            "model": "keep",
        }
        out = mask_agent_config(cfg)
        assert out["model"] == "keep"
        for key in cfg:
            if key != "model":
                assert out[key] == "[REDACTED]", key

    def test_none_and_empty(self):
        assert mask_agent_config(None) == {}
        assert mask_agent_config({}) == {}


class TestFactoryModelConfig:
    def test_full_config_passed_through(self):
        cfg = {
            "runner": "openai",
            "model": "deepseek-chat",
            "api_key": "sk-a",
            "base_url": "https://example.com",
            "timeout_seconds": 45,
            "temperature": 0.7,
            "max_tokens": 1024,
            "provider": "deepseek",
        }
        with patch("app.core.agent_runner.openai_runner.AsyncOpenAI") as m:
            runner = build_agent_runner(cfg)
        assert m.call_args.kwargs["api_key"] == "sk-a"
        assert m.call_args.kwargs["base_url"] == "https://example.com"
        assert m.call_args.kwargs["timeout"] == 45.0
        assert runner.model == "deepseek-chat"
        assert runner.provider == "deepseek"
        assert runner.timeout_seconds == 45.0
        assert runner.temperature == 0.7
        assert runner.max_tokens == 1024

    def test_legacy_task_without_new_fields(self):
        cfg = {"model": "gpt-test"}
        with patch("app.core.agent_runner.openai_runner.AsyncOpenAI"):
            runner = build_agent_runner(cfg)
        assert runner.model == "gpt-test"
        assert runner.provider == "openai"
        assert isinstance(runner.timeout_seconds, float)
        assert runner.temperature == 0.0
        assert runner.max_tokens is None
