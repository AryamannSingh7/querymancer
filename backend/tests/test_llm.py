"""Tests for app.core.llm — Gemini primary with Groq fallback.

Tests monkeypatch the two private dispatch helpers
(`_generate_with_gemini`, `_generate_with_groq`) so they don't touch
either SDK. The behaviours under test are the policy bits only: which
errors trigger fallback, when fallback is disabled, and what happens
when both providers fail.
"""

from __future__ import annotations

import pytest
from google.genai.errors import ClientError, ServerError

from app.core import llm
from app.models import ChartHint, LLMOutput


def _ok(sql: str = "SELECT 1") -> LLMOutput:
    return LLMOutput(sql=sql, explanation="ok", chart_hint=ChartHint.table)


def _client_error(code: int) -> ClientError:
    return ClientError(code, {"error": {"code": code, "message": "boom"}})


def _server_error(code: int = 500) -> ServerError:
    return ServerError(code, {"error": {"code": code, "message": "boom"}})


def _enable_groq(monkeypatch):
    monkeypatch.setattr(
        "app.core.llm.get_settings",
        lambda: type(
            "S", (), {"groq_api_key": "test-key", "groq_model": "llama-test"}
        )(),
    )


def _disable_groq(monkeypatch):
    monkeypatch.setattr(
        "app.core.llm.get_settings",
        lambda: type(
            "S", (), {"groq_api_key": "", "groq_model": "llama-test"}
        )(),
    )


def test_happy_path_no_fallback(monkeypatch):
    groq_called = {"n": 0}

    monkeypatch.setattr(
        "app.core.llm._generate_with_gemini",
        lambda p, s: _ok("SELECT gemini"),
    )
    monkeypatch.setattr(
        "app.core.llm._generate_with_groq",
        lambda p, s: (groq_called.__setitem__("n", groq_called["n"] + 1), _ok())[1],
    )
    _enable_groq(monkeypatch)

    out = llm.generate_sql("Q", "S")
    assert out.sql == "SELECT gemini"
    assert groq_called["n"] == 0


def test_gemini_429_triggers_groq(monkeypatch):
    def boom(p, s):
        raise _client_error(429)

    monkeypatch.setattr("app.core.llm._generate_with_gemini", boom)
    monkeypatch.setattr(
        "app.core.llm._generate_with_groq",
        lambda p, s: _ok("SELECT groq"),
    )
    _enable_groq(monkeypatch)

    out = llm.generate_sql("Q", "S")
    assert out.sql == "SELECT groq"


def test_gemini_5xx_triggers_groq(monkeypatch):
    def boom(p, s):
        raise _server_error(503)

    monkeypatch.setattr("app.core.llm._generate_with_gemini", boom)
    monkeypatch.setattr(
        "app.core.llm._generate_with_groq",
        lambda p, s: _ok("SELECT groq"),
    )
    _enable_groq(monkeypatch)

    out = llm.generate_sql("Q", "S")
    assert out.sql == "SELECT groq"


def test_gemini_400_does_not_fall_back(monkeypatch):
    """A 4xx that isn't 429 (bad request, auth) is a bug, not a quota issue."""
    groq_called = {"n": 0}

    def boom(p, s):
        raise _client_error(400)

    monkeypatch.setattr("app.core.llm._generate_with_gemini", boom)
    monkeypatch.setattr(
        "app.core.llm._generate_with_groq",
        lambda p, s: (groq_called.__setitem__("n", groq_called["n"] + 1), _ok())[1],
    )
    _enable_groq(monkeypatch)

    with pytest.raises(ClientError) as exc:
        llm.generate_sql("Q", "S")
    assert exc.value.code == 400
    assert groq_called["n"] == 0


def test_fallback_disabled_when_key_unset(monkeypatch):
    def boom(p, s):
        raise _client_error(429)

    monkeypatch.setattr("app.core.llm._generate_with_gemini", boom)
    monkeypatch.setattr(
        "app.core.llm._generate_with_groq",
        lambda p, s: _ok("SELECT groq"),
    )
    _disable_groq(monkeypatch)

    with pytest.raises(ClientError) as exc:
        llm.generate_sql("Q", "S")
    assert exc.value.code == 429


def test_both_providers_fail_reraises_gemini(monkeypatch):
    """When Groq also fails the user sees Gemini's exception — the router
    already knows how to render that into a 503; adding a new exception
    class would force every caller to learn about the dual-provider design."""
    gemini_exc = _client_error(429)

    def boom_gemini(p, s):
        raise gemini_exc

    def boom_groq(p, s):
        raise RuntimeError("groq down too")

    monkeypatch.setattr("app.core.llm._generate_with_gemini", boom_gemini)
    monkeypatch.setattr("app.core.llm._generate_with_groq", boom_groq)
    _enable_groq(monkeypatch)

    with pytest.raises(ClientError) as exc:
        llm.generate_sql("Q", "S")
    assert exc.value is gemini_exc
    # Groq failure is chained as the cause so it's recoverable from logs.
    assert isinstance(exc.value.__cause__, RuntimeError)
