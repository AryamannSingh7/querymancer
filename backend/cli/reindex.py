"""Schema indexer: SQLite → Gemini embeddings → Supabase pgvector.

Usage (from backend/):
    .venv/Scripts/python.exe -m cli.reindex --db-id northwind --sqlite-path databases/northwind.db

Idempotent: rows whose content_hash is unchanged are skipped entirely —
the embed call is never made and the DB is not updated.

Summary line printed at the end:
    <N> indexed, <M> unchanged, <K> failed
"""

from __future__ import annotations

import argparse
import hashlib
import logging
import sqlite3
import sys
import time
from pathlib import Path

import psycopg
from pgvector.psycopg import register_vector

# Make `app.*` importable when running as `python -m cli.reindex` from backend/.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import get_settings  # noqa: E402
from app.core.embed import embed_documents  # noqa: E402
from app.core.llm import _client as llm_client  # noqa: E402

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("reindex")

# ---------------------------------------------------------------------------
# Column type helpers
# ---------------------------------------------------------------------------

# SQLite affinity groups we will attempt to sample as plain text values.
_SAMPLEABLE_AFFINITIES = {"TEXT", "INTEGER", "NUMERIC", "REAL", "DATE", "DATETIME", "BOOLEAN"}
# Affinity prefixes that indicate binary data — skip sampling.
_BLOB_PREFIXES = ("BLOB", "BINARY", "IMAGE", "PICTURE", "PHOTO", "VARBINARY")


def _is_sampleable(type_str: str) -> bool:
    """Return True if the column's declared type is safe to SELECT as sample values."""
    upper = (type_str or "").upper().strip()
    for prefix in _BLOB_PREFIXES:
        if upper.startswith(prefix):
            return False
    return True


# ---------------------------------------------------------------------------
# SQLite introspection
# ---------------------------------------------------------------------------

def _get_user_tables(conn: sqlite3.Connection) -> list[str]:
    rows = conn.execute(
        "SELECT name FROM sqlite_master "
        "WHERE type='table' AND name NOT LIKE 'sqlite_%' "
        "ORDER BY name"
    ).fetchall()
    return [r[0] for r in rows]


def _get_columns(conn: sqlite3.Connection, table: str) -> list[dict]:
    """Return list of column dicts from PRAGMA table_info."""
    rows = conn.execute(f'PRAGMA table_info("{table}")').fetchall()
    # (cid, name, type, notnull, dflt_value, pk)
    return [
        {
            "cid": r[0],
            "name": r[1],
            "type": r[2],
            "notnull": bool(r[3]),
            "pk": r[5],  # 0 = not PK; >0 = pk position in composite
        }
        for r in rows
    ]


def _get_foreign_keys(conn: sqlite3.Connection, table: str) -> list[dict]:
    """Return list of FK dicts from PRAGMA foreign_key_list."""
    rows = conn.execute(f'PRAGMA foreign_key_list("{table}")').fetchall()
    # (id, seq, table, from, to, on_update, on_delete, match)
    return [
        {
            "from_col": r[3],
            "to_table": r[2],
            "to_col": r[4],
        }
        for r in rows
    ]


def _get_sample_values(
    conn: sqlite3.Connection,
    table: str,
    col: str,
    limit: int = 5,
) -> list[str]:
    """Fetch up to `limit` distinct non-null values for a column.

    Returns an empty list on any error (e.g. empty table, all-null column).
    """
    try:
        rows = conn.execute(
            f'SELECT DISTINCT "{col}" FROM "{table}" WHERE "{col}" IS NOT NULL LIMIT {limit}'
        ).fetchall()
        return [str(r[0]) for r in rows if r[0] is not None]
    except Exception:
        return []


def _row_count(conn: sqlite3.Connection, table: str) -> int:
    try:
        return conn.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
    except Exception:
        return -1


# ---------------------------------------------------------------------------
# LLM-generated table descriptions (one call per table, never re-called
# if content_hash is unchanged).
# ---------------------------------------------------------------------------

def _generate_description(table: str, columns: list[dict]) -> str:
    """Ask Gemini for a one-sentence summary of what this table stores."""
    col_summary = ", ".join(
        f"{c['name']} ({c['type'] or 'TEXT'})" for c in columns
    )
    prompt = (
        f"In one short sentence (no more than 20 words), describe what the "
        f"database table '{table}' stores. Its columns are: {col_summary}. "
        f"Reply with only the sentence, no quotes."
    )
    try:
        from google.genai import types as genai_types
        response = llm_client().models.generate_content(
            model=get_settings().gemini_indexer_model,
            contents=prompt,
            config=genai_types.GenerateContentConfig(temperature=0.0),
        )
        return response.text.strip().rstrip(".")
    except Exception as exc:
        log.warning("Description generation failed for %s: %s", table, exc)
        return f"Stores {table} data"


# ---------------------------------------------------------------------------
# Chunk builder
# ---------------------------------------------------------------------------

def _build_chunk(
    conn: sqlite3.Connection,
    table: str,
    description: str,
) -> str:
    """Build the canonical chunk text for one table."""
    columns = _get_columns(conn, table)
    fks = _get_foreign_keys(conn, table)

    # Index FK by from_col for quick lookup
    fk_map: dict[str, dict] = {fk["from_col"]: fk for fk in fks}

    # ---- COLUMNS section ----
    col_lines: list[str] = []
    for c in columns:
        parts = [f"  - {c['name']}", c["type"] or "TEXT"]
        flags: list[str] = []
        if c["pk"]:
            flags.append("PRIMARY KEY")
        if c["name"] in fk_map:
            fk = fk_map[c["name"]]
            flags.append(f"FK→{fk['to_table']}.{fk['to_col']}")
        elif c["notnull"] and not c["pk"]:
            flags.append("NOT NULL")
        if flags:
            parts.append("  [" + "|".join(flags) + "]")
        col_lines.append("  ".join(parts))

    # ---- SAMPLE_VALUES section ----
    n_rows = _row_count(conn, table)
    sample_lines: list[str] = []
    if n_rows > 0:
        for c in columns:
            if not _is_sampleable(c["type"]):
                continue
            vals = _get_sample_values(conn, table, c["name"])
            if vals:
                quoted = ", ".join(f'"{v}"' for v in vals)
                sample_lines.append(f"  {c['name']}: [{quoted}]")

    # ---- RELATIONSHIPS section (has-many) ----
    # Find other tables that have FKs pointing TO this table.
    all_tables = _get_user_tables(conn)
    rel_lines: list[str] = []
    for other in all_tables:
        if other == table:
            continue
        for fk in _get_foreign_keys(conn, other):
            if fk["to_table"] == table:
                rel_lines.append(f"  - has many {other} (FK on {fk['from_col']})")

    # ---- Assemble ----
    lines = [
        f"TABLE: {table}",
        f"DESCRIPTION: {description}",
        "COLUMNS:",
    ]
    lines.extend(col_lines)
    lines.append("SAMPLE_VALUES:")
    if sample_lines:
        lines.extend(sample_lines)
    else:
        lines.append("  (none)")
    lines.append("RELATIONSHIPS:")
    if rel_lines:
        lines.extend(rel_lines)
    else:
        lines.append("  (none)")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# SHA-256 hash
# ---------------------------------------------------------------------------

def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Embedding with retry + exponential backoff
# ---------------------------------------------------------------------------

def _embed_with_retry(text: str, table: str, retries: int = 3) -> list[float]:
    delay = 2.0
    last_exc: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            return embed_documents([text])[0]
        except Exception as exc:
            last_exc = exc
            if attempt < retries:
                log.warning(
                    "Embedding failed for table '%s' (attempt %d/%d): %s — retrying in %.0fs",
                    table, attempt, retries, exc, delay,
                )
                time.sleep(delay)
                delay *= 2
    raise RuntimeError(
        f"Embedding failed for table '{table}' after {retries} attempts"
    ) from last_exc


# ---------------------------------------------------------------------------
# Supabase upsert
# ---------------------------------------------------------------------------

_FETCH_HASH_SQL = """
SELECT content_hash
FROM public.schema_embeddings
WHERE database_id = %s AND table_name = %s
"""

_UPSERT_SQL = """
INSERT INTO public.schema_embeddings
    (database_id, table_name, content, content_hash, embedding)
VALUES
    (%s, %s, %s, %s, %s)
ON CONFLICT (database_id, table_name)
DO UPDATE SET
    content      = EXCLUDED.content,
    content_hash = EXCLUDED.content_hash,
    embedding    = EXCLUDED.embedding,
    updated_at   = NOW()
"""


def _fetch_existing_hash(cur: psycopg.Cursor, database_id: str, table: str) -> str | None:
    cur.execute(_FETCH_HASH_SQL, (database_id, table))
    row = cur.fetchone()
    return row[0] if row else None


def _upsert_row(
    cur: psycopg.Cursor,
    database_id: str,
    table: str,
    content: str,
    content_hash: str,
    embedding: list[float],
) -> None:
    import numpy as np
    cur.execute(_UPSERT_SQL, (database_id, table, content, content_hash, np.array(embedding)))


# ---------------------------------------------------------------------------
# Main indexing loop
# ---------------------------------------------------------------------------

def reindex(database_id: str, sqlite_path: Path) -> None:
    if not sqlite_path.exists():
        log.error("SQLite file not found: %s", sqlite_path)
        sys.exit(1)

    settings = get_settings()
    if not settings.supabase_db_url:
        log.error("SUPABASE_DB_URL is not set in .env")
        sys.exit(1)

    log.info("Opening SQLite: %s", sqlite_path)
    sqlite_conn = sqlite3.connect(str(sqlite_path))
    tables = _get_user_tables(sqlite_conn)
    log.info("Found %d user tables: %s", len(tables), tables)

    n_indexed = 0
    n_unchanged = 0
    n_failed = 0

    log.info("Connecting to Supabase …")
    with psycopg.connect(settings.supabase_db_url, connect_timeout=15) as pg_conn:
        register_vector(pg_conn)
        with pg_conn.cursor() as cur:
            for table in tables:
                log.info("[%s] Introspecting …", table)
                try:
                    columns = _get_columns(sqlite_conn, table)

                    # Build a preliminary column summary to get a description
                    # before the full chunk (description is part of the chunk,
                    # so we need to generate it first to compute the hash).
                    # Strategy: generate description → build chunk → hash → check.
                    description = _generate_description(table, columns)
                    chunk = _build_chunk(sqlite_conn, table, description)
                    content_hash = _sha256(chunk)

                    # Check if unchanged
                    existing_hash = _fetch_existing_hash(cur, database_id, table)
                    if existing_hash == content_hash:
                        log.info("[%s] Unchanged — skipping embed.", table)
                        n_unchanged += 1
                        continue

                    # Embed
                    log.info("[%s] Embedding chunk (%d chars) …", table, len(chunk))
                    embedding = _embed_with_retry(chunk, table)

                    # Upsert
                    _upsert_row(cur, database_id, table, chunk, content_hash, embedding)
                    pg_conn.commit()
                    log.info("[%s] Upserted.", table)
                    n_indexed += 1

                except Exception as exc:
                    log.error("[%s] FAILED: %s", table, exc)
                    n_failed += 1
                    try:
                        pg_conn.rollback()
                    except Exception:
                        pass

    sqlite_conn.close()
    print(f"\n{n_indexed} indexed, {n_unchanged} unchanged, {n_failed} failed")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Embed a SQLite schema into Supabase pgvector."
    )
    parser.add_argument(
        "--db-id",
        required=True,
        help='Slug identifying this database in schema_embeddings (e.g. "northwind")',
    )
    parser.add_argument(
        "--sqlite-path",
        required=True,
        type=Path,
        help="Path to the .db file (absolute or relative to cwd).",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    reindex(database_id=args.db_id, sqlite_path=args.sqlite_path.resolve())
