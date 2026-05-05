"""Tests for app.core.executor — read-only SQLite execution.

Contract:
  execute_ro(database_id, sql, *, timeout_s=5.0, row_cap=1000) -> ExecutionResult
    .columns: list[str]
    .rows:    list[tuple]
"""

from __future__ import annotations

import pytest

from app.core import executor


def test_simple_select_returns_rows_and_columns():
    res = executor.execute_ro("northwind", "SELECT CustomerID, CompanyName FROM Customers LIMIT 3")
    assert res.columns == ["CustomerID", "CompanyName"]
    assert len(res.rows) == 3
    assert all(len(r) == 2 for r in res.rows)


def test_quoted_order_details_table():
    res = executor.execute_ro("northwind", 'SELECT OrderID FROM "Order Details" LIMIT 1')
    assert res.columns == ["OrderID"]
    assert len(res.rows) == 1


def test_unknown_database_raises():
    with pytest.raises(executor.ExecutionError):
        executor.execute_ro("does_not_exist", "SELECT 1")


def test_invalid_sql_raises_execution_error():
    with pytest.raises(executor.ExecutionError):
        executor.execute_ro("northwind", "SELECT FROM WHERE")


def test_write_attempt_rejected_by_mode_ro():
    # mode=ro should refuse any write attempt at the SQLite layer.
    with pytest.raises(executor.ExecutionError):
        executor.execute_ro("northwind", "DELETE FROM Customers")


def test_row_cap_truncates_oversized_result():
    # Order Details has 600k+ rows. With a small row_cap, executor must
    # stop fetching past the cap.
    res = executor.execute_ro(
        "northwind",
        'SELECT OrderID FROM "Order Details"',
        row_cap=50,
    )
    assert len(res.rows) == 50


def test_returns_python_native_types():
    res = executor.execute_ro("northwind", "SELECT 1 AS one, 'x' AS s")
    assert res.rows == [(1, "x")]
