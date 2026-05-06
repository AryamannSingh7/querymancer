"""Gemini embedding wrapper for the schema RAG layer.

We use `gemini-embedding-001` with `output_dimensionality=768`. The model's
native dimension is larger; truncating via Matryoshka representation keeps
us under pgvector's 2000-dim HNSW ceiling on the standard `vector` type
and matches the `vector(768)` column declared in seed_supabase.sql.

Truncated vectors lose unit-norm, so we re-normalize to L2 = 1 before
returning. With unit-norm vectors, cosine distance via pgvector's `<=>`
operator is well-conditioned and equivalent to dot-product distance.

Asymmetric retrieval: documents (chunks) are embedded with
`task_type=RETRIEVAL_DOCUMENT`, queries with `RETRIEVAL_QUERY`. Google's
embedding model is trained to project the two into the same space.
"""

from functools import lru_cache
from math import sqrt

from google import genai
from google.genai import types

from app.core.config import get_settings


@lru_cache(maxsize=1)
def _client() -> genai.Client:
    return genai.Client(api_key=get_settings().gemini_api_key)


def _normalize(vec: list[float]) -> list[float]:
    norm = sqrt(sum(x * x for x in vec))
    if norm == 0.0:
        return vec
    return [x / norm for x in vec]


def _embed_batch(texts: list[str], task_type: str) -> list[list[float]]:
    settings = get_settings()
    response = _client().models.embed_content(
        model=settings.embed_model,
        contents=texts,
        config=types.EmbedContentConfig(
            output_dimensionality=settings.embed_dim,
            task_type=task_type,
        ),
    )
    out: list[list[float]] = []
    for emb in response.embeddings:
        values = list(emb.values)
        if len(values) != settings.embed_dim:
            raise RuntimeError(
                f"Embedding dim mismatch: got {len(values)}, "
                f"expected {settings.embed_dim}"
            )
        out.append(_normalize(values))
    return out


def embed_documents(texts: list[str]) -> list[list[float]]:
    """Embed schema chunks for storage in schema_embeddings."""
    if not texts:
        return []
    return _embed_batch(texts, task_type="RETRIEVAL_DOCUMENT")


def embed_query(text: str) -> list[float]:
    """Embed a user question for top-K cosine retrieval."""
    return _embed_batch([text], task_type="RETRIEVAL_QUERY")[0]
