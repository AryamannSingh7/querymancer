"""Step 3 smoke test — proves the Gemini SDK contract works in isolation.

Run from backend/:
    .venv/Scripts/python.exe scripts/smoke_gemini.py
"""

from app.core.llm import generate_sql

SYSTEM = (
    "You are an expert SQLite SQL assistant. Given the schema below, "
    "write a single SELECT query (no DDL/DML, no INSERT/UPDATE/DELETE) "
    "that answers the user's question. Always return JSON matching the schema."
)

PROMPT = """\
Schema (Northwind, SQLite):
- Customers(CustomerID TEXT PK, CompanyName TEXT, Country TEXT)
- Orders(OrderID INTEGER PK, CustomerID TEXT FK -> Customers.CustomerID, OrderDate TEXT)

Question: How many orders has each customer placed? Order by count descending.
Return CustomerID, CompanyName, OrderCount. Limit to top 10.
"""


def main() -> None:
    resp = generate_sql(prompt_text=PROMPT, system_instruction=SYSTEM)
    print("=== Gemini smoke test ===")
    print(f"chart_hint: {resp.chart_hint.value}")
    print(f"explanation: {resp.explanation}")
    print(f"sql:\n{resp.sql}")

    assert resp.sql.strip(), "Empty SQL returned"
    sql_upper = resp.sql.upper()
    assert "SELECT" in sql_upper, "No SELECT keyword"
    assert "FROM" in sql_upper, "No FROM keyword"
    print("\nOK: QueryResponse parsed cleanly, SQL is well-formed.")


if __name__ == "__main__":
    main()
