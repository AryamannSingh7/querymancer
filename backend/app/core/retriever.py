"""Top-K cosine retrieval over schema_embeddings (Supabase pgvector).

Filters by database_id, orders by cosine distance via the `<=>` operator,
returns the closest K chunks. The schema_embeddings table is populated
by `cli.reindex` (which is invoked once per sample DB).

We open a fresh psycopg connection per call. That is fine for the demo
volume (~10 chunks per DB, sub-millisecond DB time on the pooler). If we
ever need lower per-request latency, swap in psycopg_pool.ConnectionPool.
"""

import time
from dataclasses import dataclass

import numpy as np
import psycopg
from pgvector.psycopg import register_vector

from app.core.config import get_settings
from app.core.embed import embed_query


@dataclass(frozen=True)
class SchemaChunk:
    table_name: str
    content: str
    distance: float


_QUERY = """
SELECT table_name, content, embedding <=> %s AS distance
FROM public.schema_embeddings
WHERE database_id = %s
ORDER BY embedding <=> %s
LIMIT %s
"""

_CONNECT_ATTEMPTS = 3
_CONNECT_BASE_DELAY = 0.5


def top_k(database_id: str, question: str, k: int = 5) -> list[SchemaChunk]:
    """Return the top-K table chunks most relevant to `question` for `database_id`.

    K=5 is the project default per the RAG plan. Reduce for very small DBs
    if it would just return the whole schema anyway.

    Retries transient OperationalError up to 3 times with exponential backoff
    (0.5s, 1s) — getaddrinfo on Windows occasionally fails when called from
    threadpool workers in quick succession, and Supabase's pooler can close
    idle connections. A connection pool would be the right long-term fix
    (Phase 6 production polish); for now retrying covers the demo path.
    """
    qvec = np.array(embed_query(question), dtype=np.float32)
    url = get_settings().supabase_db_url
    if not url:
        raise RuntimeError(
            "SUPABASE_DB_URL is not set; configure it in backend/.env "
            "before calling retriever.top_k."
        )

    last_err: psycopg.OperationalError | None = None
    for attempt in range(_CONNECT_ATTEMPTS):
        try:
            with psycopg.connect(url, connect_timeout=10) as conn:
                register_vector(conn)
                with conn.cursor() as cur:
                    cur.execute(_QUERY, (qvec, database_id, qvec, k))
                    return [
                        SchemaChunk(
                            table_name=row[0],
                            content=row[1],
                            distance=float(row[2]),
                        )
                        for row in cur.fetchall()
                    ]
        except psycopg.OperationalError as e:
            last_err = e
            if attempt < _CONNECT_ATTEMPTS - 1:
                time.sleep(_CONNECT_BASE_DELAY * (2 ** attempt))

    assert last_err is not None
    raise last_err
