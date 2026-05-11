"""Multi-turn session persistence over Supabase Postgres.

A "session" is a sequence of related `/query` turns the user has issued
against one database. Recent turns get inlined into the next prompt as
"PRIOR TURNS" context so the model can resolve pronouns / follow-ups
("show those by country", "what about for 2024?").

Public surface
--------------
- `TurnSnippet` — frozen dataclass of (question, sql) returned by `recent_turns`.
- `ensure_session(session_id, database_id) -> str` — returns a valid session id.
  If `session_id` is None, unknown, or bound to a *different* database, we
  create a fresh session instead of silently inlining mismatched context.
- `recent_turns(session_id, n=2) -> list[TurnSnippet]` — most-recent-first.
- `append_turn(session_id, ...) -> None` — fire-and-forget persistence.

Each call opens a short-lived `psycopg.connect` (same pattern as
`app.core.retriever`). A connection pool would lower per-request latency
on HF Spaces; until that becomes a problem the retry-with-backoff
covers transient pooler hiccups.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass

import psycopg

from app.core.config import get_settings


@dataclass(frozen=True)
class TurnSnippet:
    question: str
    sql: str


_CONNECT_ATTEMPTS = 3
_CONNECT_BASE_DELAY = 0.5


def _connect() -> psycopg.Connection:
    url = get_settings().supabase_db_url
    if not url:
        raise RuntimeError(
            "SUPABASE_DB_URL is not set; configure it in backend/.env "
            "before using app.core.sessions."
        )

    last_err: psycopg.OperationalError | None = None
    for attempt in range(_CONNECT_ATTEMPTS):
        try:
            return psycopg.connect(url, connect_timeout=10)
        except psycopg.OperationalError as e:
            last_err = e
            if attempt < _CONNECT_ATTEMPTS - 1:
                time.sleep(_CONNECT_BASE_DELAY * (2 ** attempt))

    assert last_err is not None
    raise last_err


def ensure_session(session_id: str | None, database_id: str) -> str:
    """Return a session id valid for `database_id`.

    Creates a fresh session and returns its id if:
      - `session_id` is None
      - the row does not exist in `public.sessions`
      - the row exists but is bound to a different `database_id`
        (would inline wrong-DB context — treat as a new conversation)
    """
    if session_id:
        with _connect() as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT database_id FROM public.sessions WHERE id = %s",
                (session_id,),
            )
            row = cur.fetchone()
            if row is not None and row[0] == database_id:
                return session_id

    new_id = str(uuid.uuid4())
    with _connect() as conn, conn.cursor() as cur:
        cur.execute(
            "INSERT INTO public.sessions (id, database_id) VALUES (%s, %s)",
            (new_id, database_id),
        )
        conn.commit()
    return new_id


def recent_turns(session_id: str, n: int = 2) -> list[TurnSnippet]:
    """Return the `n` most recent turns for `session_id`, newest first.

    Empty list if the session has no turns yet (e.g. first /query call
    in a new session). Caller is expected to handle that — prompt
    builder simply omits the PRIOR TURNS block when the list is empty.
    """
    with _connect() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT question, sql FROM public.turns "
            "WHERE session_id = %s "
            "ORDER BY created_at DESC "
            "LIMIT %s",
            (session_id, n),
        )
        return [TurnSnippet(question=r[0], sql=r[1]) for r in cur.fetchall()]


def append_turn(
    session_id: str,
    question: str,
    sql: str,
    rows_count: int,
    attempts: int,
    latency_ms: int,
) -> None:
    turn_id = str(uuid.uuid4())
    with _connect() as conn, conn.cursor() as cur:
        cur.execute(
            "INSERT INTO public.turns "
            "(id, session_id, question, sql, rows_count, attempts, latency_ms) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (turn_id, session_id, question, sql, rows_count, attempts, latency_ms),
        )
        conn.commit()
