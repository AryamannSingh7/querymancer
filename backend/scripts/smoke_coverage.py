"""Coverage smoke — 10 questions targeting pie chart + advanced SQL patterns.

Each question:
  1. is sent through prompt.build_prompt() + llm.generate_sql() (no HTTP layer —
     this is a pure prompt/LLM smoke, the FastAPI route is already covered by
     smoke_query.py and tests/test_app.py)
  2. its returned SQL is EXECUTED against backend/databases/northwind.db
     opened in mode=ro (no safety layer yet — that's Phase 2)
  3. results are reported with expected vs actual chart_hint

Rate-limit aware: paces calls 13s apart (under the free-tier 5 RPM cap), and
on a 429 backs off 65s and retries once.

Run from backend/:
    .venv/Scripts/python.exe scripts/smoke_coverage.py
"""

from __future__ import annotations

import os
import sqlite3
import sys
import time
from pathlib import Path

# Use the lite model for smokes — separate, much larger free-tier daily
# quota than gemini-2.5-flash. See smoke_query.py for the rationale.
os.environ.setdefault("GEMINI_MODEL", "gemini-2.5-flash-lite")

from google.genai.errors import ClientError  # noqa: E402

from app.core import llm, prompt  # noqa: E402

DB_PATH = Path(__file__).resolve().parents[1] / "databases" / "northwind.db"
DB_URI = f"file:{DB_PATH.as_posix()}?mode=ro"

# Free tier is 5 RPM on gemini-2.5-flash. 13s is a safe pace.
PACE_SECONDS = 13
INITIAL_WAIT_SECONDS = 65  # full window reset before we start


# (question, expected_chart_hint, label, sql_pattern_to_check_for)
QUESTIONS: list[tuple[str, str, str, str | None]] = [
    # --- pie chart tests ---
    (
        "What share of all orders does each shipper handle?",
        "pie",
        "pie / 3 shippers",
        None,
    ),
    (
        "Break down products by Discontinued vs active. How many of each?",
        "pie",
        "pie / binary breakdown",
        None,
    ),
    (
        "Show the distribution of products across the 8 categories.",
        "pie",
        "pie / 8 categories (boundary test)",
        None,
    ),
    # --- advanced SQL patterns ---
    (
        "Rank products by UnitPrice within each category and return the top 3 per category.",
        "table",
        "window function: ROW_NUMBER OVER PARTITION BY",
        "OVER",
    ),
    (
        "Which customers have placed more than 10 orders? Return CustomerID, CompanyName, OrderCount.",
        "table",
        "HAVING clause",
        "HAVING",
    ),
    (
        "List products with a UnitPrice above the average product price.",
        "table",
        "subquery (scalar)",
        "SELECT",
    ),
    (
        "Which customers have never placed an order?",
        "table",
        "anti-join (LEFT JOIN ... NULL or NOT EXISTS)",
        None,
    ),
    (
        "What is the average number of days between an order's OrderDate and ShippedDate?",
        "scalar",
        "date arithmetic (julianday)",
        "julianday",
    ),
    (
        "Bucket orders by freight cost: low (<10), medium (10-50), high (>50). Count orders in each bucket.",
        "bar",
        "CASE WHEN bucketing + GROUP BY",
        "CASE",
    ),
    (
        "How many distinct countries do we ship orders to?",
        "scalar",
        "COUNT DISTINCT",
        "DISTINCT",
    ),
]


def truncate(s: str, n: int = 220) -> str:
    return s if len(s) <= n else s[: n - 3] + "..."


def ask(question: str):
    """Build the prompt + call the LLM. Retries once on 429."""
    system, user = prompt.build_prompt(question, "northwind")
    try:
        return llm.generate_sql(prompt_text=user, system_instruction=system)
    except ClientError as e:
        if getattr(e, "code", None) == 429 or "RESOURCE_EXHAUSTED" in str(e):
            print(f"  [429] backing off {INITIAL_WAIT_SECONDS}s then retrying...")
            time.sleep(INITIAL_WAIT_SECONDS)
            return llm.generate_sql(prompt_text=user, system_instruction=system)
        raise


def main() -> None:
    db = sqlite3.connect(DB_URI, uri=True)
    n = len(QUESTIONS)

    print(f"Waiting {INITIAL_WAIT_SECONDS}s for rate-limit window to reset...")
    time.sleep(INITIAL_WAIT_SECONDS)

    gen_ok = exec_ok = chart_ok = pattern_ok = 0
    pattern_total = sum(1 for _, _, _, p in QUESTIONS if p is not None)
    failures: list[str] = []

    for i, (q, expected_chart, label, pattern) in enumerate(QUESTIONS, 1):
        if i > 1:
            time.sleep(PACE_SECONDS)

        print(f"=== {i:2}. [{label}] ===")
        print(f"Q: {q}")

        try:
            resp = ask(q)
        except Exception as e:
            print(f"  LLM call failed: {type(e).__name__}: {e}")
            failures.append(f"#{i} {label}: {type(e).__name__}: {e}")
            print()
            continue

        gen_ok += 1
        sql = resp.sql
        chart = resp.chart_hint.value
        chart_match = chart == expected_chart
        if chart_match:
            chart_ok += 1

        print(f"  chart: {chart}  (expected {expected_chart})  {'OK' if chart_match else 'MISMATCH'}")
        print(f"  sql:   {sql}")

        if pattern is not None:
            if pattern.upper() in sql.upper():
                pattern_ok += 1
                print(f"  pattern: contains '{pattern}'  OK")
            else:
                print(f"  pattern: missing '{pattern}'  FAIL")
                failures.append(f"#{i} {label}: SQL missing pattern '{pattern}'")

        try:
            cur = db.execute(sql)
            rows = cur.fetchall()
            cols = [d[0] for d in (cur.description or [])]
            exec_ok += 1
            print(f"  exec:  {len(rows)} rows, cols={cols}")
            if rows:
                # encode/decode dance for windows console (handles non-ASCII names)
                sample = repr(rows[0]).encode("ascii", "replace").decode("ascii")
                print(f"  sample: {truncate(sample)}")
        except sqlite3.Error as e:
            print(f"  exec FAIL: {e}")
            failures.append(f"#{i} {label}: {e}")

        print()

    print("=" * 60)
    print("SUMMARY")
    print(f"  generated cleanly:    {gen_ok}/{n}")
    print(f"  executed against DB:  {exec_ok}/{n}")
    print(f"  chart_hint matched:   {chart_ok}/{n}")
    print(f"  required pattern hit: {pattern_ok}/{pattern_total}")
    if failures:
        print("\nFAILURES:")
        for f in failures:
            print(f"  - {f}")
    sys.exit(0 if not failures else 1)


if __name__ == "__main__":
    main()
