-- One-time Supabase setup for the Querymancer schema vector store.
-- Run ONCE in the Supabase SQL Editor against the `querymancer` project.
-- Idempotent: safe to re-run.

-- 1. pgvector — provides VECTOR type and the cosine `<=>` operator.
CREATE EXTENSION IF NOT EXISTS vector;

-- 2. schema_embeddings — one row per (database_id, table_name).
--    embedding is 768-dim because we ask gemini-embedding-001 to truncate
--    via output_dimensionality=768. That keeps us comfortably under
--    pgvector's 2000-dim HNSW limit on the standard `vector` type.
CREATE TABLE IF NOT EXISTS public.schema_embeddings (
    id              BIGSERIAL PRIMARY KEY,
    database_id     TEXT        NOT NULL,
    table_name      TEXT        NOT NULL,
    content         TEXT        NOT NULL,
    content_hash    TEXT        NOT NULL,
    embedding       VECTOR(768) NOT NULL,
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (database_id, table_name)
);

-- 3. Row Level Security — enabled with NO policies, which is default-deny
--    for the anon and authenticated roles. The backend uses the
--    service_role key, which bypasses RLS unconditionally, so retrieval
--    and reindex still work. This locks the table from any caller using
--    a leaked publishable key.
ALTER TABLE public.schema_embeddings ENABLE ROW LEVEL SECURITY;

-- 4. B-tree on database_id — used as the pre-filter in retrieval queries
--    (`WHERE database_id = $1 ORDER BY embedding <=> $2 LIMIT 5`).
CREATE INDEX IF NOT EXISTS idx_schema_embeddings_db
    ON public.schema_embeddings (database_id);

-- 5. HNSW cosine index. m=16, ef_construction=64 (defaults) are right for
--    a tiny corpus (~10 chunks per DB). Bump if/when corpus grows.
CREATE INDEX IF NOT EXISTS idx_schema_embeddings_vec
    ON public.schema_embeddings
    USING hnsw (embedding vector_cosine_ops);

-- 6. Trigger to keep updated_at fresh on UPSERT-driven re-embed.
CREATE OR REPLACE FUNCTION public.set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_schema_embeddings_updated_at
    ON public.schema_embeddings;

CREATE TRIGGER trg_schema_embeddings_updated_at
    BEFORE UPDATE ON public.schema_embeddings
    FOR EACH ROW
    EXECUTE FUNCTION public.set_updated_at();

-- 7. Sanity check — the SQL Editor will show this as the result of the run.
SELECT
    'schema_embeddings ready' AS status,
    COUNT(*)                  AS existing_row_count
FROM public.schema_embeddings;
