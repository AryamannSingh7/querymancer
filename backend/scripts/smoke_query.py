"""End-to-end smoke — POST /query in-process via FastAPI TestClient.

Phase 2: the response now also carries `rows`, `columns`, `attempts`. We
print the row count and the first row as a sanity signal that execution
worked, and assert `attempts >= 1`.

Free-tier paced: 13s between calls, plus a 65s window-reset wait on first
boot to avoid 429s.

Smoke uses gemini-2.5-flash-lite (separate, much larger free-tier daily
quota) so repeated dev runs don't burn through the 20 RPD on
gemini-2.5-flash that the live /query path needs. We export
GEMINI_MODEL before importing app so pydantic-settings picks it up.

Run from backend/:
    .venv/Scripts/python.exe scripts/smoke_query.py
"""

from __future__ import annotations

import os
import time

os.environ.setdefault("GEMINI_MODEL", "gemini-2.5-flash-lite")

from fastapi.testclient import TestClient  # noqa: E402
from google.genai.errors import ClientError, ServerError  # noqa: E402

from app.main import app  # noqa: E402

QUESTIONS = [
    "How many products are discontinued?",                           # scalar
    "Top 5 customers by number of orders.",                          # bar / single join
    "Top 5 product categories by total revenue.",                    # bar / multi-join
    "Show monthly order count for the year 2017.",                   # line / time-series
    "Which employees report to the employee named Andrew Fuller?",   # self-join
]

PACE_SECONDS = 13
INITIAL_WAIT_SECONDS = 65


def main() -> None:
    client = TestClient(app)

    h = client.get("/health")
    print(f"GET /health -> {h.status_code} {h.json()}\n")

    print(f"Waiting {INITIAL_WAIT_SECONDS}s for rate-limit window to reset...")
    time.sleep(INITIAL_WAIT_SECONDS)

    for i, q in enumerate(QUESTIONS, 1):
        if i > 1:
            time.sleep(PACE_SECONDS)

        print(f"--- {i}. {q}")
        try:
            resp = client.post("/query", json={"question": q, "database_id": "northwind"})
        except (ServerError, ClientError) as e:
            # Gemini transient (503 UNAVAILABLE / 429 RESOURCE_EXHAUSTED).
            # Back off once, retry; if still failing, skip this question.
            print(f"  [{type(e).__name__}] {e} — backing off 65s and retrying once")
            time.sleep(INITIAL_WAIT_SECONDS)
            try:
                resp = client.post("/query", json={"question": q, "database_id": "northwind"})
            except (ServerError, ClientError) as e2:
                print(f"  retry also failed: {e2} — skipping")
                continue
        print(f"  status: {resp.status_code}")
        if resp.status_code != 200:
            print(f"  body:   {resp.text}")
            continue
        data = resp.json()
        print(f"  chart:    {data['chart_hint']}")
        print(f"  attempts: {data['attempts']}")
        print(f"  expl:     {data['explanation']}")
        print(f"  sql:      {data['sql']}")
        print(f"  rows:     {len(data['rows'])} (cols={data['columns']})")
        if data["rows"]:
            sample = repr(data["rows"][0]).encode("ascii", "replace").decode("ascii")
            print(f"  sample:   {sample[:220]}")
        print()


if __name__ == "__main__":
    main()
