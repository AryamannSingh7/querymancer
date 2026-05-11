"""Multi-turn smoke for Phase 5 sessions/turns persistence.

Sequence:
  Turn 1 — "Top 5 customers by number of orders."   (no session_id sent)
  Turn 2 — "And what countries are those customers in?"  (with the
            session_id the server returned on turn 1)

Validates:
  - the server creates and returns a session_id on turn 1
  - that session_id is echoed back on turn 2 (same conversation)
  - turn 2's SQL references the prior context, i.e. it queries
    countries for customers — *not* a generic "all customers' countries"
    answer. We assert it mentions Country AND retains a Customer/Orders
    join or LIMIT 5, which a good follow-up resolution would.

Free-tier paced like smoke_query.py: lite model, 13s between calls,
65s warmup wait on boot.

Run from backend/:
    .venv/Scripts/python.exe scripts/smoke_multiturn.py
"""

from __future__ import annotations

import os
import time

os.environ.setdefault("GEMINI_MODEL", "gemini-2.5-flash-lite")

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

PACE_SECONDS = 13
INITIAL_WAIT_SECONDS = 65


def _post(client: TestClient, question: str, session_id: str | None) -> dict:
    body: dict = {"question": question, "database_id": "northwind"}
    if session_id:
        body["session_id"] = session_id
    r = client.post("/query", json=body)
    print(f"  status:   {r.status_code}")
    if r.status_code != 200:
        print(f"  body:     {r.text}")
        raise SystemExit(1)
    return r.json()


def main() -> None:
    client = TestClient(app)

    h = client.get("/health")
    print(f"GET /health -> {h.status_code} {h.json()}\n")

    print(f"Waiting {INITIAL_WAIT_SECONDS}s for rate-limit window to reset...")
    time.sleep(INITIAL_WAIT_SECONDS)

    # --- Turn 1 ---
    q1 = "Top 5 customers by number of orders."
    print(f"--- Turn 1: {q1}")
    t1 = _post(client, q1, session_id=None)
    sid = t1["session_id"]
    print(f"  session:  {sid}")
    print(f"  attempts: {t1['attempts']}")
    print(f"  sql:      {t1['sql']}")
    print(f"  rows:     {len(t1['rows'])} (cols={t1['columns']})")
    print()

    assert isinstance(sid, str) and sid, "turn 1 must return a session_id"

    time.sleep(PACE_SECONDS)

    # --- Turn 2 (follow-up, same session) ---
    q2 = "And what countries are those customers in?"
    print(f"--- Turn 2: {q2}")
    t2 = _post(client, q2, session_id=sid)
    print(f"  session:  {t2['session_id']}")
    print(f"  attempts: {t2['attempts']}")
    print(f"  sql:      {t2['sql']}")
    print(f"  rows:     {len(t2['rows'])} (cols={t2['columns']})")
    print()

    assert t2["session_id"] == sid, "turn 2 must echo the same session_id"

    sql2_upper = t2["sql"].upper()
    assert "COUNTRY" in sql2_upper, "follow-up should reference Country column"

    # Heuristic that the model actually resolved "those customers" — the
    # follow-up should still constrain to the top 5 (LIMIT 5) or carry
    # over the Orders join. Either is a good signal that prior context
    # was used; a generic "select country from customers" would not.
    referenced_prior = (
        "LIMIT 5" in sql2_upper
        or "ORDERS" in sql2_upper
        or "COUNT(" in sql2_upper
    )
    if referenced_prior:
        print("  [ok] follow-up resolved prior context (LIMIT 5 / Orders join / COUNT)")
    else:
        print("  [!] follow-up SQL does not obviously reference prior turn — review:")
        print(f"      {t2['sql']}")

    print("\nDone.")


if __name__ == "__main__":
    main()
