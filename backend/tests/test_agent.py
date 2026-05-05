"""Tests for app.core.agent — the self-correction loop.

The agent calls llm.generate_sql, then runs the result through safety + executor.
On any failure (safety reject OR execute error), it appends the error to a
list and re-prompts up to `max_attempts` times before giving up.

Tests use monkeypatch to fake llm.generate_sql so they're CI-safe (no live LLM
calls). Executor + safety are real — those layers are deterministic.
"""

from __future__ import annotations

from itertools import count

import pytest

from app.core import agent
from app.models import ChartHint, LLMOutput


def _resp(sql: str, chart: ChartHint = ChartHint.table, expl: str = "ok") -> LLMOutput:
    return LLMOutput(sql=sql, explanation=expl, chart_hint=chart)


def test_succeeds_on_first_attempt(monkeypatch):
    calls: list[list[str] | None] = []

    def fake_generate(prompt_text, system_instruction):
        # capture prompt to inspect retry behaviour
        calls.append(prompt_text)
        return _resp("SELECT CustomerID FROM Customers LIMIT 1", ChartHint.table)

    monkeypatch.setattr("app.core.agent.llm.generate_sql", fake_generate)

    result = agent.run("any question", "northwind")
    assert result.attempts == 1
    assert result.columns == ["CustomerID"]
    assert len(result.rows) == 1
    assert result.chart_hint == ChartHint.table
    # only one LLM call
    assert len(calls) == 1


def test_retries_on_safety_reject(monkeypatch):
    sequence = iter([
        _resp("DROP TABLE Customers"),                              # rejected by safety
        _resp("SELECT CustomerID FROM Customers LIMIT 1"),          # accepted
    ])

    monkeypatch.setattr(
        "app.core.agent.llm.generate_sql",
        lambda prompt_text, system_instruction: next(sequence),
    )

    result = agent.run("any", "northwind")
    assert result.attempts == 2
    assert len(result.rows) == 1


def test_retries_on_execute_error(monkeypatch):
    sequence = iter([
        _resp("SELECT NonexistentColumn FROM Customers"),           # SQLite error
        _resp("SELECT CustomerID FROM Customers LIMIT 2"),          # ok
    ])

    monkeypatch.setattr(
        "app.core.agent.llm.generate_sql",
        lambda prompt_text, system_instruction: next(sequence),
    )

    result = agent.run("any", "northwind")
    assert result.attempts == 2
    assert len(result.rows) == 2


def test_passes_errors_back_into_prompt(monkeypatch):
    captured_prompts: list[str] = []
    sequence = iter([
        _resp("DROP TABLE Customers"),
        _resp("SELECT 1"),
    ])

    def fake(prompt_text, system_instruction):
        captured_prompts.append(prompt_text)
        return next(sequence)

    monkeypatch.setattr("app.core.agent.llm.generate_sql", fake)

    agent.run("any", "northwind")
    assert len(captured_prompts) == 2
    # second prompt MUST contain the error from attempt 1
    assert "PRIOR ATTEMPTS FAILED" in captured_prompts[1]
    assert "DROP" in captured_prompts[1].upper()


def test_raises_after_max_attempts_exhausted(monkeypatch):
    counter = count(1)

    def always_bad(prompt_text, system_instruction):
        n = next(counter)
        return _resp(f"DROP TABLE x_{n}")  # always rejected

    monkeypatch.setattr("app.core.agent.llm.generate_sql", always_bad)

    with pytest.raises(agent.AgentError) as exc:
        agent.run("any", "northwind", max_attempts=3)

    err = exc.value
    assert err.attempts == 3
    assert len(err.errors) == 3


@pytest.mark.parametrize(
    "malicious_sql",
    [
        "DROP TABLE Customers",
        "SELECT 1; DROP TABLE Customers",
        "SELECT * FROM sqlite_master",
        "DELETE FROM Customers WHERE 1=1",
        "ATTACH DATABASE 'evil.db' AS evil",
    ],
)
def test_adversarial_sql_is_blocked_every_attempt(monkeypatch, malicious_sql):
    # If the LLM returned the same malicious SQL three times in a row,
    # safety must reject it every time and the agent must surface AgentError.
    monkeypatch.setattr(
        "app.core.agent.llm.generate_sql",
        lambda prompt_text, system_instruction: _resp(malicious_sql),
    )
    with pytest.raises(agent.AgentError) as exc:
        agent.run("any", "northwind", max_attempts=3)
    assert exc.value.attempts == 3
    # the rejection reason should be in every error
    assert all("safety" in e for e in exc.value.errors)


def test_unknown_database_id_does_not_loop(monkeypatch):
    # Unknown DB raises immediately at prompt-build time. We should NOT call
    # the LLM at all and surface a clean error.
    called = {"n": 0}

    def fake(prompt_text, system_instruction):
        called["n"] += 1
        return _resp("SELECT 1")

    monkeypatch.setattr("app.core.agent.llm.generate_sql", fake)

    with pytest.raises(ValueError):
        agent.run("any", "unknown_db")
    assert called["n"] == 0
