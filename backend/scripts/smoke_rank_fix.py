"""Targeted smoke — verify the rule-9 ranking split (nw_047 / hr_030).

Checks the prompt fix that distinguishes:
  (a) "top N / highest per group"  -> filter rn <= N
  (b) "rank X within each group"   -> keep all rows, rank as a column

Runs three eval cases in-process and asserts row counts + filter presence:
  nw_047  "Rank products by revenue within each category"  -> 50-77 rows, NO rn filter
  hr_030  "Show the single highest-paid employee ..."       -> 8 rows, HAS rn filter
  nw_028  "List the top product in each category by revenue" -> 8 rows, HAS rn filter (regression guard)

Uses gemini-2.5-flash-lite to preserve the flash 20-RPD quota.

Run from backend/:
    .venv/Scripts/python.exe scripts/smoke_rank_fix.py
"""

from __future__ import annotations

import os
import re
import time

os.environ.setdefault("GEMINI_MODEL", "gemini-2.5-flash-lite")

from fastapi.testclient import TestClient  # noqa: E402
from google.genai.errors import ClientError, ServerError  # noqa: E402

from app.main import app  # noqa: E402

CASES = [
    # (id, database_id, question, min_rows, max_rows, expect_rn_filter)
    ("nw_047", "northwind", "Rank products by revenue within each category.", 50, 77, False),
    ("hr_030", "hr", "Show the single highest-paid employee in each department.", 8, 8, True),
    ("nw_028", "northwind", "List the top product in each category by revenue.", 8, 8, True),
]

# Matches a WHERE/AND filter on the ROW_NUMBER alias, e.g. "WHERE rn = 1", "rn <= 5".
RN_FILTER = re.compile(r"\b(rn|rownum|\w*rank\w*)\s*(<=?|=)\s*\d", re.IGNORECASE)

PACE_SECONDS = 6


def main() -> None:
    client = TestClient(app)
    print(f"GET /health -> {client.get('/health').json()}\n")

    passed = 0
    for i, (cid, db, q, lo, hi, want_filter) in enumerate(CASES):
        if i:
            time.sleep(PACE_SECONDS)
        print(f"--- {cid}: {q}")
        try:
            resp = client.post("/query", json={"question": q, "database_id": db})
        except (ServerError, ClientError) as e:
            print(f"  [{type(e).__name__}] {e} — skipping (quota/transient)\n")
            continue
        if resp.status_code != 200:
            print(f"  status {resp.status_code}: {resp.text}\n")
            continue
        data = resp.json()
        sql = data["sql"]
        n = len(data["rows"])
        has_filter = bool(RN_FILTER.search(sql))
        rows_ok = lo <= n <= hi
        filter_ok = has_filter == want_filter
        verdict = "PASS" if (rows_ok and filter_ok) else "FAIL"
        if verdict == "PASS":
            passed += 1
        print(f"  attempts: {data['attempts']}")
        print(f"  sql:      {sql}")
        print(f"  rows:     {n} (want {lo}-{hi}, {'ok' if rows_ok else 'BAD'})")
        print(f"  rn-filter: {has_filter} (want {want_filter}, {'ok' if filter_ok else 'BAD'})")
        print(f"  => {verdict}\n")

    print(f"=== {passed}/{len(CASES)} passed")


if __name__ == "__main__":
    main()
