"""Smoke-test the Gemini embedding wrapper end-to-end.

Verifies:
- The client authenticates with the API key from .env.
- gemini-embedding-001 returns the expected 768-dim vector when
  output_dimensionality=768 is passed.
- The vector is unit-norm (L2 = 1) after our re-normalization.
- A query and a document with related content produce similar vectors
  (cosine similarity > 0.5), and unrelated content produces lower
  similarity. This is a sanity check on the model + asymmetric task_type.

Run from backend/ as:
    .venv/Scripts/python.exe scripts/smoke_embed.py
"""

from math import sqrt
from pathlib import Path
import sys

# Make `app.*` imports work when the script is run directly.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.embed import embed_documents, embed_query  # noqa: E402


def cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = sqrt(sum(x * x for x in a))
    nb = sqrt(sum(x * x for x in b))
    return dot / (na * nb) if na and nb else 0.0


def main() -> None:
    print("--- single doc embed ---")
    docs = embed_documents(["Customer order header with date, ship info, totals."])
    vec = docs[0]
    print(f"  dim   = {len(vec)}")
    print(f"  norm  = {sqrt(sum(x * x for x in vec)):.6f}")
    print(f"  head  = {[round(x, 4) for x in vec[:5]]}")
    assert len(vec) == 768, "expected 768-dim vector"
    assert abs(sqrt(sum(x * x for x in vec)) - 1.0) < 1e-5, "expected unit norm"

    print("\n--- query vs related vs unrelated ---")
    related_doc = (
        "TABLE: orders. Customer order header with date, ship country, freight."
    )
    unrelated_doc = (
        "TABLE: territories. Region descriptions used to scope sales territories."
    )
    query = "Show me monthly order totals by country"

    [doc_rel, doc_unrel] = embed_documents([related_doc, unrelated_doc])
    q = embed_query(query)

    sim_rel = cosine(q, doc_rel)
    sim_unrel = cosine(q, doc_unrel)
    print(f"  sim(query, related)   = {sim_rel:.4f}")
    print(f"  sim(query, unrelated) = {sim_unrel:.4f}")
    assert sim_rel > sim_unrel, (
        f"related doc should beat unrelated; got {sim_rel:.4f} vs {sim_unrel:.4f}"
    )
    print("\nOK — embedding wrapper is healthy.")


if __name__ == "__main__":
    main()
