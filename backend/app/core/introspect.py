"""SQLite schema introspection — structured JSON for the /databases/{id}/schema route.

Distinct from `cli.reindex`'s introspection (which builds embedding-friendly
plain-text chunks); this module returns typed dicts the frontend can render
directly.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from typing_extensions import TypedDict


class Column(TypedDict):
    name: str
    type: str
    notnull: bool
    pk: bool


class ForeignKey(TypedDict):
    from_col: str
    to_table: str
    to_col: str


class TableInfo(TypedDict):
    name: str
    row_count: int
    columns: list[Column]
    foreign_keys: list[ForeignKey]
    referenced_by: list[ForeignKey]  # FKs in OTHER tables that point to this one


def _user_tables(conn: sqlite3.Connection) -> list[str]:
    rows = conn.execute(
        "SELECT name FROM sqlite_master "
        "WHERE type='table' AND name NOT LIKE 'sqlite_%' "
        "ORDER BY name"
    ).fetchall()
    return [r[0] for r in rows]


def _columns(conn: sqlite3.Connection, table: str) -> list[Column]:
    rows = conn.execute(f'PRAGMA table_info("{table}")').fetchall()
    # (cid, name, type, notnull, dflt_value, pk)
    return [
        Column(
            name=r[1],
            type=(r[2] or "").upper() or "TEXT",
            notnull=bool(r[3]),
            pk=bool(r[5]),
        )
        for r in rows
    ]


def _foreign_keys(conn: sqlite3.Connection, table: str) -> list[ForeignKey]:
    rows = conn.execute(f'PRAGMA foreign_key_list("{table}")').fetchall()
    # (id, seq, table, from, to, on_update, on_delete, match)
    return [ForeignKey(from_col=r[3], to_table=r[2], to_col=r[4]) for r in rows]


def _row_count(conn: sqlite3.Connection, table: str) -> int:
    try:
        return int(conn.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0])
    except sqlite3.Error:
        return -1


def introspect(sqlite_path: Path) -> list[TableInfo]:
    """Open the SQLite file read-only and return structured table info.

    Each entry includes its own outbound FKs and the inbound `referenced_by`
    list — useful for the frontend to render relationship arrows without a
    second pass.
    """
    uri = f"file:{sqlite_path.as_posix()}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    try:
        names = _user_tables(conn)

        # Pre-compute outbound FKs per table — used twice (own list + reverse map)
        outbound: dict[str, list[ForeignKey]] = {n: _foreign_keys(conn, n) for n in names}

        # Reverse map: target table -> list of inbound FKs (with from_table tagged
        # via a synthesized ForeignKey whose to_table is preserved as the source).
        inbound: dict[str, list[ForeignKey]] = {n: [] for n in names}
        for owner, fks in outbound.items():
            for fk in fks:
                if fk["to_table"] in inbound:
                    inbound[fk["to_table"]].append(
                        ForeignKey(
                            from_col=fk["from_col"],
                            to_table=owner,            # the table that holds the FK
                            to_col=fk["to_col"],
                        )
                    )

        result: list[TableInfo] = []
        for name in names:
            result.append(
                TableInfo(
                    name=name,
                    row_count=_row_count(conn, name),
                    columns=_columns(conn, name),
                    foreign_keys=outbound[name],
                    referenced_by=inbound[name],
                )
            )
        return result
    finally:
        conn.close()
