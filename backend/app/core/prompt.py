"""Prompt builder.

Phase 3 swaps the hard-coded SCHEMA_TEXT for retrieval-augmented chunks.
For each call, we ask `retriever.top_k(database_id, question, k=5)` for
the most relevant table chunks and inline them as the schema context.

Few-shot examples and the system instruction are still Northwind-flavored
because Northwind is the only indexed DB right now. When HR / IPL land,
both will need to generalize (or be templated per database_id).
"""

from app.core import retriever
from app.core.sessions import TurnSnippet

SYSTEM_INSTRUCTION = """You are an expert SQLite SQL assistant. Given a schema and a question in natural \
language, produce a single safe SELECT query and a short explanation.

RULES — non-negotiable:
1. Output ONLY a single SELECT statement. NEVER INSERT, UPDATE, DELETE, DROP, ALTER, \
CREATE, PRAGMA, ATTACH, or any other DDL/DML.
2. Use SQLite dialect only — no Postgres- or MySQL-only functions (e.g. no DATE_TRUNC, \
no EXTRACT, no NOW(); use strftime, julianday, date()).
3. Identifiers with spaces MUST be double-quoted. The table named Order Details MUST \
always be written as "Order Details".
4. Always include LIMIT 100 (or a smaller user-requested limit) unless the user \
explicitly asks for "all" rows.
5. Use only the exact column names from the schema below — do not invent columns. \
The schema you see is the top-K most relevant tables; if a column you need \
is not in the schema, prefer to answer with what IS shown rather than guessing.
6. The Discontinued column on Products is TEXT (values "0" or "1"), not a boolean.
7. Choose chart_hint as follows:
   - "scalar" — a single number (e.g. COUNT, AVG of one value)
   - "line"   — time series (any ORDER BY of a date/time column with one numeric metric)
   - "bar"    — categorical comparison (group-by category with one numeric metric)
   - "pie"    — parts of a whole with at most 6 categories
   - "table"  — anything else, especially multi-column results
8. The explanation is one or two short plain-English sentences.
9. For "top N per group" / "highest in each X" / "best per Y" questions, use a CTE \
with ROW_NUMBER() OVER (PARTITION BY <group> ORDER BY <metric> DESC) AS rn and filter \
WHERE rn <= N in the outer query. A plain GROUP BY will return every row sorted, not \
the per-group winners."""

FEW_SHOTS = """EXAMPLES:

Q: How many customers are based in Germany?
A: {
  "sql": "SELECT COUNT(*) AS GermanCustomers FROM Customers WHERE Country = 'Germany'",
  "explanation": "Counts the customers whose Country column equals 'Germany'.",
  "chart_hint": "scalar"
}

Q: List the top 5 customers by number of orders placed.
A: {
  "sql": "SELECT c.CustomerID, c.CompanyName, COUNT(o.OrderID) AS OrderCount FROM Customers c JOIN Orders o ON c.CustomerID = o.CustomerID GROUP BY c.CustomerID, c.CompanyName ORDER BY OrderCount DESC LIMIT 5",
  "explanation": "Joins Customers with Orders, counts orders per customer, and returns the top 5.",
  "chart_hint": "bar"
}

Q: What were the top 5 product categories by total revenue?
A: {
  "sql": "SELECT cat.CategoryName, SUM(od.UnitPrice * od.Quantity * (1 - od.Discount)) AS Revenue FROM \\"Order Details\\" od JOIN Products p ON od.ProductID = p.ProductID JOIN Categories cat ON p.CategoryID = cat.CategoryID GROUP BY cat.CategoryID, cat.CategoryName ORDER BY Revenue DESC LIMIT 5",
  "explanation": "Aggregates line-item revenue (UnitPrice * Quantity * (1 - Discount)) from \\"Order Details\\", groups by category, and returns the top 5.",
  "chart_hint": "bar"
}

Q: Which is the top-selling product (by total quantity sold) for each supplier?
A: {
  "sql": "WITH ranked AS (SELECT s.CompanyName AS Supplier, p.ProductName, SUM(od.Quantity) AS UnitsSold, ROW_NUMBER() OVER (PARTITION BY s.SupplierID ORDER BY SUM(od.Quantity) DESC) AS rn FROM \\"Order Details\\" od JOIN Products p ON od.ProductID = p.ProductID JOIN Suppliers s ON p.SupplierID = s.SupplierID GROUP BY s.SupplierID, s.CompanyName, p.ProductID, p.ProductName) SELECT Supplier, ProductName, UnitsSold FROM ranked WHERE rn = 1 ORDER BY UnitsSold DESC LIMIT 100",
  "explanation": "Ranks products by units sold within each supplier using ROW_NUMBER, then keeps only the per-supplier winner.",
  "chart_hint": "table"
}"""

SCHEMA_HEADER = (
    "RELEVANT SCHEMA — the top tables retrieved by similarity to the question. "
    "If the table you need is not here, say so in the explanation."
)

DEFAULT_K = 5


def _format_prior_turns(turns: list[TurnSnippet]) -> str:
    """Render the most-recent-first turn list as a PRIOR TURNS block.

    Newest is shown last (T-2 then T-1) so the model reads them in
    conversational order — the question right above Q: is the most
    recent. Older turns sit further away, matching natural recency.
    """
    if not turns:
        return ""
    ordered = list(reversed(turns))  # oldest first → newest last
    lines = [
        "PRIOR TURNS — the user may be following up. Resolve pronouns "
        "(\"those\", \"them\", \"that one\") and implicit references against "
        "the most recent turn shown below."
    ]
    for offset, t in enumerate(ordered):
        idx = len(ordered) - offset  # T-2, T-1, ...
        lines.append(f"  T-{idx}:")
        lines.append(f"    Q: {t.question.strip()}")
        lines.append(f"    SQL: {t.sql.strip()}")
    return "\n".join(lines) + "\n\n"


def build_prompt(
    question: str,
    database_id: str,
    errors: list[str] | None = None,
    recent_turns: list[TurnSnippet] | None = None,
    k: int = DEFAULT_K,
) -> tuple[str, str]:
    """Return (system_instruction, user_prompt) for the given question.

    On retries, pass `errors` — the verbatim DB / safety errors from prior
    attempts. They are inlined into the prompt so the model can see what
    went wrong and avoid repeating itself.

    For follow-up turns, pass `recent_turns` — the most-recent-first list
    of prior (question, sql) pairs from this session. They are inlined
    as a PRIOR TURNS block so the model can resolve pronouns.

    Raises ValueError if no chunks are indexed for `database_id` — the
    caller should treat this as a 400 (unknown / unindexed database).
    """
    chunks = retriever.top_k(database_id, question, k=k)
    if not chunks:
        raise ValueError(
            f"Unknown database_id={database_id!r}: no schema chunks indexed. "
            "Run `python -m cli.reindex --db-id <id> --sqlite-path <path>` "
            "from backend/ to index it first."
        )

    schema_block = "\n\n".join(c.content.rstrip() for c in chunks)

    prior_turns_block = _format_prior_turns(recent_turns or [])

    error_block = ""
    if errors:
        formatted = "\n".join(f"  attempt {i + 1}: {e}" for i, e in enumerate(errors))
        error_block = (
            "PRIOR ATTEMPTS FAILED. Read the errors and fix the SQL accordingly:\n"
            f"{formatted}\n\n"
        )

    user_prompt = (
        f"{SCHEMA_HEADER}\n\n"
        f"{schema_block}\n\n"
        f"{FEW_SHOTS}\n\n"
        f"{prior_turns_block}"
        f"{error_block}"
        f"Q: {question.strip()}\n"
        f"A:"
    )
    return SYSTEM_INSTRUCTION, user_prompt
