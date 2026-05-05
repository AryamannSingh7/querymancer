"""SQL safety gate.

Two layers, both required:
  1. Regex denylist on the raw text catches keywords sqlglot might tolerate
     when embedded in odd places.
  2. sqlglot AST parse + root-statement check confirms the query is a SELECT
     (and only one of them).

Plus an `inject_limit` helper that wraps a SELECT in `SELECT * FROM (<sql>) LIMIT N`
when the query has no top-level LIMIT, so a runaway projection cannot exceed
the row cap.

Public surface:
  is_safe(sql) -> tuple[bool, str]
  inject_limit(sql, limit=1000) -> str
"""

from __future__ import annotations

import re

import sqlglot
from sqlglot import expressions as exp

# Forbidden keywords. Word-boundary so we don't match "VACATION" or "DROPDOWN".
_DENYLIST = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|ATTACH|DETACH|PRAGMA|VACUUM|REINDEX|REPLACE|TRUNCATE)\b",
    re.IGNORECASE,
)

# sqlite internal tables — readable by default, must be blocked at the safety layer.
_SQLITE_INTERNAL = re.compile(r"\bsqlite_(master|schema|sequence|stat\d*|temp_master)\b", re.IGNORECASE)


def _strip_statements(sql: str) -> list[str]:
    """Split on `;` and drop empty fragments. Used only for the multi-statement check."""
    return [s.strip() for s in sql.split(";") if s.strip()]


def is_safe(sql: str) -> tuple[bool, str]:
    """Return (ok, reason). reason is empty when ok is True."""
    if not sql or not sql.strip():
        return False, "empty SQL"

    # 1. multi-statement check (cheap, does not require parse)
    parts = _strip_statements(sql)
    if len(parts) == 0:
        return False, "empty SQL"
    if len(parts) > 1:
        return False, "only a single statement is allowed"

    one = parts[0]

    # 2. denylist on the single statement
    if _DENYLIST.search(one):
        m = _DENYLIST.search(one)
        return False, f"forbidden keyword: {m.group(0).upper()}"

    # 3. sqlite internal tables
    if _SQLITE_INTERNAL.search(one):
        return False, "references to sqlite_* internal tables are not allowed"

    # 4. parse + AST root must be a Select (CTE wrapping a Select also OK)
    try:
        tree = sqlglot.parse_one(one, read="sqlite")
    except Exception as e:
        return False, f"could not parse SQL: {e}"

    if tree is None:
        return False, "empty parse tree"

    root = tree
    # `WITH ... SELECT` parses as a Select with a `with` arg in sqlglot.
    if not isinstance(root, exp.Select):
        return False, f"only SELECT statements are allowed (got {type(root).__name__})"

    return True, ""


def inject_limit(sql: str, limit: int = 1000) -> str:
    """Wrap the query so the result set is capped.

    If the query already has a top-level LIMIT, return it unchanged. Otherwise
    wrap as `SELECT * FROM (<sql>) LIMIT N`. Idempotent: running this twice on
    the same input yields the same output (the second call sees the wrapper's
    LIMIT and is a no-op).
    """
    sql_stripped = sql.strip().rstrip(";").strip()
    try:
        tree = sqlglot.parse_one(sql_stripped, read="sqlite")
    except Exception:
        # Don't try to be clever on unparseable input — caller should have
        # already run is_safe() and rejected it.
        return sql_stripped

    if tree is None:
        return sql_stripped

    # If the top-level select already has a LIMIT, leave it alone.
    if isinstance(tree, exp.Select) and tree.args.get("limit") is not None:
        return sql_stripped

    return f"SELECT * FROM ({sql_stripped}) LIMIT {limit}"
