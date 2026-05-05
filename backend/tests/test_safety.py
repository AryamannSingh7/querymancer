"""Tests for app.core.safety — the SQL safety gate.

Phase 2 contract:
  is_safe(sql) -> tuple[bool, str]   # (ok, reason_if_rejected)
  inject_limit(sql, limit=1000) -> str

Rejection rules:
  - non-SELECT root (INSERT/UPDATE/DELETE/DROP/ALTER/CREATE/etc.)
  - keyword denylist (also catches PRAGMA/ATTACH/VACUUM/REINDEX)
  - more than one statement (split on `;`)
  - sqlite_master / sqlite_schema references
  - unparseable SQL
"""

from __future__ import annotations

import pytest

from app.core import safety


# ---- accepted SELECTs ----

@pytest.mark.parametrize(
    "sql",
    [
        "SELECT 1",
        "SELECT * FROM Customers LIMIT 10",
        "SELECT c.CustomerID, COUNT(o.OrderID) FROM Customers c LEFT JOIN Orders o ON c.CustomerID = o.CustomerID GROUP BY c.CustomerID",
        'SELECT * FROM "Order Details" LIMIT 5',
        "WITH x AS (SELECT 1 AS v) SELECT * FROM x",  # CTE on top of SELECT
        "SELECT ProductID, ROW_NUMBER() OVER (PARTITION BY CategoryID ORDER BY UnitPrice DESC) FROM Products",
    ],
)
def test_accepts_select(sql):
    ok, reason = safety.is_safe(sql)
    assert ok, f"expected accept, got reject: {reason}"


# ---- rejected: dangerous statements ----

@pytest.mark.parametrize(
    "sql",
    [
        "DROP TABLE Customers",
        "DELETE FROM Customers",
        "INSERT INTO Customers (CustomerID) VALUES ('X')",
        "UPDATE Customers SET CompanyName = 'x'",
        "ALTER TABLE Customers ADD COLUMN x TEXT",
        "CREATE TABLE x (id INT)",
        "ATTACH DATABASE 'foo.db' AS foo",
        "PRAGMA table_info(Customers)",
        "VACUUM",
        "REINDEX",
    ],
)
def test_rejects_non_select(sql):
    ok, reason = safety.is_safe(sql)
    assert not ok
    assert reason


# ---- rejected: multi-statement injection ----

@pytest.mark.parametrize(
    "sql",
    [
        "SELECT 1; DROP TABLE Customers",
        "SELECT * FROM Customers; SELECT * FROM Orders",
        "SELECT 1;DELETE FROM Customers",
    ],
)
def test_rejects_multi_statement(sql):
    ok, reason = safety.is_safe(sql)
    assert not ok
    assert "single" in reason.lower() or "statement" in reason.lower()


def test_accepts_trailing_semicolon():
    # one real statement plus a trailing `;` is fine
    ok, _ = safety.is_safe("SELECT 1;")
    assert ok


# ---- rejected: sqlite internals ----

@pytest.mark.parametrize(
    "sql",
    [
        "SELECT * FROM sqlite_master",
        "SELECT name FROM sqlite_schema",
        "SELECT 1 UNION SELECT * FROM sqlite_master",
    ],
)
def test_rejects_sqlite_internals(sql):
    ok, reason = safety.is_safe(sql)
    assert not ok
    assert "sqlite_" in reason.lower() or "internal" in reason.lower()


# ---- rejected: unparseable ----

def test_rejects_unparseable():
    ok, reason = safety.is_safe("THIS IS NOT SQL @@@")
    assert not ok


def test_rejects_empty():
    ok, _ = safety.is_safe("")
    assert not ok
    ok, _ = safety.is_safe("   \n\t  ")
    assert not ok


# ---- inject_limit ----

def test_inject_limit_adds_when_missing():
    out = safety.inject_limit("SELECT * FROM Customers", limit=1000)
    assert "LIMIT" in out.upper()
    assert "1000" in out


def test_inject_limit_idempotent_when_present():
    sql = "SELECT * FROM Customers LIMIT 50"
    out = safety.inject_limit(sql, limit=1000)
    # should not re-wrap when an explicit LIMIT already exists
    assert out.upper().count("LIMIT") == 1
    assert "50" in out


def test_inject_limit_preserves_select():
    out = safety.inject_limit("SELECT CustomerID FROM Customers", limit=100)
    # the projected column still survives (either preserved verbatim or aliased)
    assert "Customer" in out
