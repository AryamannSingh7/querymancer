"""Read-only SQLite executor.

Two non-negotiables:
  1. The DB is opened with `mode=ro` URI — even if a write somehow gets past
     the safety gate, SQLite refuses it.
  2. A wall-clock timeout is enforced via sqlite3's progress handler so a
     pathological query (cartesian explosion, recursive CTE) cannot hang.

Result is capped at `row_cap` rows; we stop calling fetchmany once the cap is
hit so a SELECT * on a 600k-row table doesn't materialise everything.

Public surface:
  ExecutionResult — dataclass with columns + rows
  ExecutionError  — wraps any sqlite3 error or DB-not-found
  execute_ro(database_id, sql, *, timeout_s=5.0, row_cap=1000) -> ExecutionResult
"""

from __future__ import annotations

import sqlite3
import time
from dataclasses import dataclass, field
from pathlib import Path

DB_DIR = Path(__file__).resolve().parents[2] / "databases"


@dataclass
class ExecutionResult:
    columns: list[str] = field(default_factory=list)
    rows: list[tuple] = field(default_factory=list)


class ExecutionError(Exception):
    """Anything that prevented us from returning a clean result."""


def _resolve_db_path(database_id: str) -> Path:
    # Whitelist-by-existence: the file must live in backend/databases/ and
    # the slug cannot escape via path traversal.
    if "/" in database_id or "\\" in database_id or ".." in database_id:
        raise ExecutionError(f"invalid database_id: {database_id!r}")
    p = DB_DIR / f"{database_id}.db"
    if not p.is_file():
        raise ExecutionError(f"database not found: {database_id}")
    return p


def execute_ro(
    database_id: str,
    sql: str,
    *,
    timeout_s: float = 5.0,
    row_cap: int = 1000,
) -> ExecutionResult:
    db_path = _resolve_db_path(database_id)
    uri = f"file:{db_path.as_posix()}?mode=ro"

    try:
        conn = sqlite3.connect(uri, uri=True, timeout=timeout_s)
    except sqlite3.Error as e:
        raise ExecutionError(f"could not open database: {e}") from e

    deadline = time.monotonic() + timeout_s

    def _interrupt_if_slow() -> int:
        # Returning non-zero from the progress handler aborts the running query.
        return 1 if time.monotonic() > deadline else 0

    # Tick frequently enough that a runaway query gets killed within ~ms of the
    # deadline, but not so often we add measurable overhead.
    conn.set_progress_handler(_interrupt_if_slow, 1000)

    try:
        cur = conn.execute(sql)
    except sqlite3.Error as e:
        conn.close()
        raise ExecutionError(str(e)) from e

    columns = [d[0] for d in (cur.description or [])]
    rows: list[tuple] = []
    try:
        # fetchmany lets us bail at the cap without paying for a full materialise.
        chunk = 200
        while len(rows) < row_cap:
            batch = cur.fetchmany(chunk)
            if not batch:
                break
            rows.extend(batch)
        if len(rows) > row_cap:
            rows = rows[:row_cap]
    except sqlite3.Error as e:
        raise ExecutionError(str(e)) from e
    finally:
        conn.close()

    return ExecutionResult(columns=columns, rows=rows)
