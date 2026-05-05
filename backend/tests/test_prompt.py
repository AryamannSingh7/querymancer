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
