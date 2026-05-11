"""Tests for app.core.prompt.build_prompt."""

from __future__ import annotations

import pytest

from app.core import prompt


def test_rejects_unknown_database():
    with pytest.raises(ValueError):
        prompt.build_prompt("anything", "mystery_db")


def test_basic_prompt_includes_question_and_schema():
    sysmsg, user = prompt.build_prompt("How many customers are in Germany?", "northwind")
    assert "SELECT" in sysmsg or "SELECT" in sysmsg.upper()
    assert "Customers" in user
    assert "How many customers are in Germany?" in user
    # no error block when not retrying
    assert "PRIOR ATTEMPTS FAILED" not in user


def test_error_history_inlined_on_retry():
    errors = [
        "no such column: CompanyNameX",
        "near 'FROMM': syntax error",
    ]
    _, user = prompt.build_prompt("List all customers", "northwind", errors=errors)
    assert "PRIOR ATTEMPTS FAILED" in user
    assert "attempt 1" in user and "attempt 2" in user
    assert "no such column: CompanyNameX" in user
    assert "near 'FROMM'" in user
    # error block appears before the question
    assert user.index("PRIOR ATTEMPTS FAILED") < user.index("List all customers")


def test_empty_errors_list_does_not_inject_block():
    _, user = prompt.build_prompt("anything", "northwind", errors=[])
    assert "PRIOR ATTEMPTS FAILED" not in user


def test_no_prior_turns_omits_block():
    _, user = prompt.build_prompt("anything", "northwind")
    assert "PRIOR TURNS" not in user

    _, user2 = prompt.build_prompt("anything", "northwind", recent_turns=[])
    assert "PRIOR TURNS" not in user2


def test_prior_turns_inlined_newest_last():
    from app.core.sessions import TurnSnippet

    # sessions.recent_turns returns newest-first; the builder should
    # reverse so older shows higher in the prompt and newest sits
    # right above the current Q.
    recent = [
        TurnSnippet(question="Top 5 customers by orders", sql="SELECT c.CompanyName ..."),
        TurnSnippet(question="How many customers in Germany?", sql="SELECT COUNT(*) ..."),
    ]
    _, user = prompt.build_prompt(
        "And what countries are they in?",
        "northwind",
        recent_turns=recent,
    )
    assert "PRIOR TURNS" in user
    # newest turn (Top 5...) should appear AFTER the older one (Germany count)
    assert user.index("How many customers in Germany?") < user.index("Top 5 customers by orders")
    # both SQL snippets and questions present
    assert "SELECT c.CompanyName ..." in user
    assert "SELECT COUNT(*) ..." in user
    # the PRIOR TURNS block sits before the current question
    assert user.index("PRIOR TURNS") < user.index("And what countries are they in?")
