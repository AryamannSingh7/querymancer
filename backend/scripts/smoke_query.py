"""Step 6 smoke test — hits POST /query in-process via FastAPI TestClient.

Exercises 5 varied questions and prints the generated SQL + chart_hint.

Run from backend/:
    .venv/Scripts/python.exe scripts/smoke_query.py
"""

from fastapi.testclient import TestClient

from app.main import app

QUESTIONS = [
    "How many products are discontinued?",                           # scalar
    "Top 5 customers by number of orders.",                          # bar / single join
    "Top 5 product categories by total revenue.",                    # bar / multi-join
    "Show monthly order count for the year 1997.",                   # line / time-series
    "Which employees report to the employee named Andrew Fuller?",    # self-join
]


def main() -> None:
    client = TestClient(app)

    h = client.get("/health")
    print(f"GET /health -> {h.status_code} {h.json()}\n")

    for i, q in enumerate(QUESTIONS, 1):
        print(f"--- {i}. {q}")
        resp = client.post("/query", json={"question": q, "database_id": "northwind"})
        print(f"  status: {resp.status_code}")
        if resp.status_code != 200:
            print(f"  body:   {resp.text}")
            continue
        data = resp.json()
        print(f"  chart:  {data['chart_hint']}")
        print(f"  expl:   {data['explanation']}")
        print(f"  sql:    {data['sql']}")
        print()


if __name__ == "__main__":
    main()
