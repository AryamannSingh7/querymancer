"""Querymancer eval harness.

Loads eval/cases.yaml, POSTs each case to a running backend's /query, grades
the response by row-count assertion, and writes a dated markdown report under
eval/reports/. Latency is measured client-side (what users feel) and reported
as p50/p95/p99.

Usage:
    python eval/run_eval.py                              # local default
    python eval/run_eval.py --backend https://asinghby-querymancer-backend.hf.space
    python eval/run_eval.py --limit-per-db 10 --concurrency 3
    python eval/run_eval.py --only-db ipl --only-difficulty hard

The report is written **incrementally** — Ctrl-C leaves a partial-but-valid
report behind, with whatever cases completed.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import statistics
import subprocess
import sys
import time
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
import yaml

ROOT = Path(__file__).resolve().parent.parent
CASES_DEFAULT = ROOT / "eval" / "cases.yaml"
REPORTS_DIR = ROOT / "eval" / "reports"

# Per-request budget. The agent self-corrects up to 3 attempts, and Gemini
# itself can take several seconds per call on the free tier — be generous.
REQUEST_TIMEOUT_S = 90.0


# ---------- data model ----------


@dataclass
class Case:
    id: str
    database_id: str
    question: str
    expected_min_rows: int
    expected_max_rows: int
    difficulty: str
    expected_columns_subset: list[str] = field(default_factory=list)
    must_contain_value: Any = None


@dataclass
class Result:
    case: Case
    status: int
    rows_count: int
    attempts: int
    latency_ms: int
    sql: str
    error: str | None
    failure_mode: str | None  # None when passed
    soft_failures: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return self.failure_mode is None


# ---------- loading ----------


def load_cases(path: Path) -> list[Case]:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    cases: list[Case] = []
    for c in raw:
        cases.append(
            Case(
                id=c["id"],
                database_id=c["database_id"],
                question=c["question"],
                expected_min_rows=c["expected_min_rows"],
                expected_max_rows=c["expected_max_rows"],
                difficulty=c["difficulty"],
                expected_columns_subset=c.get("expected_columns_subset") or [],
                must_contain_value=c.get("must_contain_value"),
            )
        )
    return cases


def filter_cases(
    cases: list[Case], only_db: str | None, only_diff: str | None, limit_per_db: int | None
) -> list[Case]:
    out = cases
    if only_db:
        out = [c for c in out if c.database_id == only_db]
    if only_diff:
        out = [c for c in out if c.difficulty == only_diff]
    if limit_per_db:
        bucket: dict[str, int] = {}
        capped: list[Case] = []
        for c in out:
            if bucket.get(c.database_id, 0) >= limit_per_db:
                continue
            bucket[c.database_id] = bucket.get(c.database_id, 0) + 1
            capped.append(c)
        out = capped
    return out


# ---------- execution ----------


async def execute_case(
    client: httpx.AsyncClient, backend: str, case: Case, max_503_retries: int = 2
) -> Result:
    payload = {"question": case.question, "database_id": case.database_id}
    started = time.perf_counter()
    status_code = 0
    sql = ""
    attempts = 0
    rows: list[list[Any]] = []
    columns: list[str] = []
    error: str | None = None
    failure_mode: str | None = None
    soft: list[str] = []

    retries_used = 0
    try:
        while True:
            r = await client.post(f"{backend}/query", json=payload, timeout=REQUEST_TIMEOUT_S)
            status_code = r.status_code
            body = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
            # Free-tier Gemini RPM bursts surface as 503 with Retry-After.
            # The eval should treat these as transient: back off, then retry.
            # We cap retries so a genuine daily-quota exhaustion still fails fast.
            if status_code == 503 and retries_used < max_503_retries:
                ra = r.headers.get("Retry-After", "")
                try:
                    wait_s = max(1.0, float(ra)) if ra else 8.0
                except ValueError:
                    wait_s = 8.0
                wait_s = min(wait_s + 1.0, 60.0)  # tiny jitter, hard cap
                await asyncio.sleep(wait_s)
                retries_used += 1
                continue
            break

        if status_code == 200:
            sql = body.get("sql", "")
            attempts = body.get("attempts", 0)
            rows = body.get("rows", []) or []
            columns = body.get("columns", []) or []
        else:
            # FastAPI HTTPException puts the structured body under "detail"
            detail = body.get("detail", body)
            if isinstance(detail, dict):
                # agent exhausted → {message, attempts, errors[]}
                attempts = detail.get("attempts", 0)
                errs = detail.get("errors") or []
                error = (detail.get("message") or "") + (f" :: {errs[-1]}" if errs else "")
            else:
                error = str(detail)[:400]
    except httpx.TimeoutException:
        error = f"client timeout after {REQUEST_TIMEOUT_S}s"
        failure_mode = "TIMEOUT"
    except httpx.RequestError as e:
        error = f"transport error: {type(e).__name__}: {e}"
        failure_mode = "TRANSPORT_ERROR"
    except Exception as e:  # noqa: BLE001 — last-line safety
        error = f"unexpected: {type(e).__name__}: {e}"
        failure_mode = "TRANSPORT_ERROR"

    latency_ms = int((time.perf_counter() - started) * 1000)

    # Categorise non-200 outcomes first (only if we haven't already classified).
    if failure_mode is None and status_code != 200:
        if status_code == 422:
            failure_mode = "SQL_INVALID"  # agent loop exhausted (bad SQL / safety / runtime)
        elif status_code in (502, 503):
            failure_mode = "UPSTREAM_LLM"
        elif status_code == 400:
            failure_mode = "BAD_REQUEST"
        else:
            failure_mode = f"HTTP_{status_code}"

    rows_count = len(rows)

    # Hard assertion: row-count window (only graded if HTTP 200).
    if failure_mode is None:
        if not (case.expected_min_rows <= rows_count <= case.expected_max_rows):
            failure_mode = "ASSERTION_FAILED"
            error = (
                f"rows_count={rows_count} not in "
                f"[{case.expected_min_rows}, {case.expected_max_rows}]"
            )

    # Soft assertions (advisory — reported but do not flip pass/fail).
    if status_code == 200:
        if case.expected_columns_subset:
            lower_cols = [c.lower() for c in columns]
            for needed in case.expected_columns_subset:
                hit = any(needed.lower() in lc for lc in lower_cols)
                if not hit:
                    soft.append(f"missing column substring '{needed}' in {columns}")
        if case.must_contain_value is not None:
            target = str(case.must_contain_value).lower()
            flat = " ".join(str(v).lower() for row in rows for v in row)
            if target not in flat:
                soft.append(f"value '{case.must_contain_value}' not found in result rows")

    return Result(
        case=case,
        status=status_code,
        rows_count=rows_count,
        attempts=attempts,
        latency_ms=latency_ms,
        sql=sql,
        error=error,
        failure_mode=failure_mode,
        soft_failures=soft,
    )


async def run_all(
    backend: str, cases: list[Case], concurrency: int, pace_s: float, on_result
) -> list[Result]:
    sem = asyncio.Semaphore(concurrency)
    results: list[Result] = []
    last_dispatch = 0.0  # monotonic, shared across workers

    async def gate() -> None:
        nonlocal last_dispatch
        if pace_s <= 0:
            return
        # Minimum spacing between dispatches across all workers — this is
        # what keeps the global RPM under the free-tier ceiling. Holding
        # the semaphore while sleeping serialises the gate naturally
        # because the sleep happens inside the `async with sem` block.
        now = time.perf_counter()
        wait = (last_dispatch + pace_s) - now
        if wait > 0:
            await asyncio.sleep(wait)
        last_dispatch = time.perf_counter()

    async with httpx.AsyncClient() as client:
        async def worker(c: Case) -> None:
            async with sem:
                await gate()
                r = await execute_case(client, backend, c)
                results.append(r)
                on_result(r)

        await asyncio.gather(*(worker(c) for c in cases))
    return results


# ---------- reporting ----------


def percentile(values: list[int], q: float) -> int:
    if not values:
        return 0
    s = sorted(values)
    k = max(0, min(len(s) - 1, int(round((q / 100.0) * (len(s) - 1)))))
    return s[k]


def headline(results: list[Result]) -> dict[str, Any]:
    total = len(results)
    passed = sum(1 for r in results if r.passed)
    lat = [r.latency_ms for r in results]
    return {
        "total": total,
        "passed": passed,
        "rate": (passed / total * 100.0) if total else 0.0,
        "p50_ms": percentile(lat, 50),
        "p95_ms": percentile(lat, 95),
        "p99_ms": percentile(lat, 99),
    }


def per_db_breakdown(results: list[Result]) -> list[dict[str, Any]]:
    by_db: dict[str, list[Result]] = {}
    for r in results:
        by_db.setdefault(r.case.database_id, []).append(r)
    rows = []
    for db, rs in sorted(by_db.items()):
        h = headline(rs)
        rows.append({"db": db, **h})
    return rows


def per_difficulty_breakdown(results: list[Result]) -> list[dict[str, Any]]:
    by_d: dict[str, list[Result]] = {}
    for r in results:
        by_d.setdefault(r.case.difficulty, []).append(r)
    order = {"simple": 0, "medium": 1, "hard": 2}
    rows = []
    for d, rs in sorted(by_d.items(), key=lambda kv: order.get(kv[0], 99)):
        h = headline(rs)
        rows.append({"difficulty": d, **h})
    return rows


def attempts_histogram(results: list[Result]) -> str:
    c = Counter(r.attempts if r.passed else 0 for r in results)
    failed = sum(1 for r in results if not r.passed)
    lines = []
    for k in sorted(k for k in c if k > 0):
        bar = "#" * c[k]
        lines.append(f"  attempts={k}: {c[k]:>3}  {bar}")
    lines.append(f"  failed   : {failed:>3}  {'#' * failed}")
    return "\n".join(lines)


def failure_table(results: list[Result]) -> str:
    fails = [r for r in results if not r.passed]
    if not fails:
        return "_None — all cases passed._"
    head = "| id | db | difficulty | failure_mode | rows | attempts | error |\n"
    head += "|----|----|------------|--------------|------|----------|-------|\n"
    body = []
    for r in fails:
        err = (r.error or "").replace("|", "\\|").replace("\n", " ")[:140]
        body.append(
            f"| {r.case.id} | {r.case.database_id} | {r.case.difficulty} | "
            f"{r.failure_mode} | {r.rows_count} | {r.attempts} | {err} |"
        )
    return head + "\n".join(body)


def soft_table(results: list[Result]) -> str:
    soft = [r for r in results if r.soft_failures]
    if not soft:
        return "_None — every passing case satisfied its advisory assertions._"
    head = "| id | db | soft warning |\n|----|----|--------------|\n"
    body = []
    for r in soft:
        for s in r.soft_failures:
            s_e = s.replace("|", "\\|").replace("\n", " ")[:160]
            body.append(f"| {r.case.id} | {r.case.database_id} | {s_e} |")
    return head + "\n".join(body)


def previous_report(reports_dir: Path) -> Path | None:
    if not reports_dir.exists():
        return None
    files = sorted(reports_dir.glob("*.md"))
    return files[-1] if files else None


def parse_prev_metrics(path: Path) -> dict[str, Any] | None:
    """Best-effort extract of headline metrics from an earlier report."""
    try:
        text = path.read_text(encoding="utf-8")
        # JSON snapshot fenced at the bottom for stable diffing.
        marker = "```json snapshot"
        if marker in text:
            blob = text.split(marker, 1)[1].split("```", 1)[0].strip()
            return json.loads(blob)
    except Exception:
        return None
    return None


def delta_section(curr: dict[str, Any], prev: dict[str, Any] | None, results: list[Result]) -> str:
    if not prev:
        return "_No previous run found — this is the baseline._"
    lines = []
    lines.append(f"- Success rate: {prev['rate']:.1f}% → {curr['rate']:.1f}% "
                 f"(Δ {curr['rate'] - prev['rate']:+.1f} pts)")
    lines.append(f"- p95 latency: {prev['p95_ms']} ms → {curr['p95_ms']} ms "
                 f"(Δ {curr['p95_ms'] - prev['p95_ms']:+d} ms)")
    prev_fail = set(prev.get("failed_ids", []))
    curr_fail = {r.case.id for r in results if not r.passed}
    new_fail = sorted(curr_fail - prev_fail)
    fixed = sorted(prev_fail - curr_fail)
    if new_fail:
        lines.append(f"- **New failures** ({len(new_fail)}): {', '.join(new_fail)}")
    if fixed:
        lines.append(f"- **Fixed since last run** ({len(fixed)}): {', '.join(fixed)}")
    if not new_fail and not fixed:
        lines.append("- No id-level changes in pass/fail set.")
    return "\n".join(lines)


def md_table(rows: list[dict[str, Any]], columns: list[str]) -> str:
    head = "| " + " | ".join(columns) + " |\n"
    head += "|" + "|".join(["---"] * len(columns)) + "|\n"
    body_lines = []
    for r in rows:
        cells = []
        for c in columns:
            v = r.get(c, "")
            if isinstance(v, float):
                cells.append(f"{v:.1f}")
            else:
                cells.append(str(v))
        body_lines.append("| " + " | ".join(cells) + " |")
    return head + "\n".join(body_lines)


def write_report(
    path: Path,
    backend: str,
    cases: list[Case],
    results: list[Result],
    git_sha: str,
    started_iso: str,
    prev: dict[str, Any] | None,
) -> None:
    h = headline(results)
    out = []
    out.append(f"# Querymancer eval — {started_iso}")
    out.append("")
    out.append(f"- Backend: `{backend}`")
    out.append(f"- Git SHA: `{git_sha}`")
    out.append(f"- Cases run: **{len(results)} / {len(cases)}**")
    out.append("")
    out.append("## Headline")
    out.append("")
    out.append(md_table([h], ["total", "passed", "rate", "p50_ms", "p95_ms", "p99_ms"]))
    out.append("")
    out.append("## Per-database")
    out.append("")
    out.append(md_table(per_db_breakdown(results),
                        ["db", "total", "passed", "rate", "p50_ms", "p95_ms", "p99_ms"]))
    out.append("")
    out.append("## Per-difficulty")
    out.append("")
    out.append(md_table(per_difficulty_breakdown(results),
                        ["difficulty", "total", "passed", "rate", "p50_ms", "p95_ms", "p99_ms"]))
    out.append("")
    out.append("## Attempt distribution (successful runs)")
    out.append("")
    out.append("```")
    out.append(attempts_histogram(results))
    out.append("```")
    out.append("")
    out.append("## Failures")
    out.append("")
    out.append(failure_table(results))
    out.append("")
    out.append("## Soft assertion warnings (advisory)")
    out.append("")
    out.append(soft_table(results))
    out.append("")
    out.append("## Delta vs previous run")
    out.append("")
    out.append(delta_section(h, prev, results))
    out.append("")
    # Stable snapshot for the next run's delta to read.
    snapshot = {
        **h,
        "failed_ids": sorted(r.case.id for r in results if not r.passed),
    }
    out.append("```json snapshot")
    out.append(json.dumps(snapshot, indent=2))
    out.append("```")
    out.append("")
    path.write_text("\n".join(out), encoding="utf-8")


def short_git_sha() -> str:
    try:
        r = subprocess.run(
            ["git", "rev-parse", "--short=8", "HEAD"],
            cwd=ROOT, capture_output=True, text=True, check=False,
        )
        sha = r.stdout.strip()
        return sha or "nogit"
    except Exception:
        return "nogit"


# ---------- main ----------


def main() -> int:
    ap = argparse.ArgumentParser(description="Run the Querymancer eval suite.")
    ap.add_argument("--backend", default=os.environ.get("EVAL_BACKEND", "http://127.0.0.1:8000"))
    ap.add_argument("--cases", default=str(CASES_DEFAULT))
    ap.add_argument("--concurrency", type=int, default=1,
                    help="Max in-flight /query requests. Default 1 — the "
                    "google-genai SDK isn't safe under threadpool concurrency.")
    ap.add_argument("--pace-seconds", type=float, default=4.5,
                    help="Minimum spacing between dispatches (global) to "
                    "stay under Gemini free-tier RPM. 0 disables pacing.")
    ap.add_argument("--limit-per-db", type=int, default=None,
                    help="Cap to N cases per DB — useful for quick smoke runs.")
    ap.add_argument("--only-db", default=None, help="Only run cases for this database_id.")
    ap.add_argument("--only-difficulty", default=None,
                    help="Only run cases at this difficulty (simple|medium|hard).")
    args = ap.parse_args()

    backend = args.backend.rstrip("/")

    # Fail-fast health check.
    try:
        with httpx.Client(timeout=10) as c:
            r = c.get(f"{backend}/health")
            if r.status_code != 200:
                print(f"backend /health returned {r.status_code} — aborting", file=sys.stderr)
                return 2
    except Exception as e:
        print(f"backend unreachable at {backend}: {e}", file=sys.stderr)
        return 2

    cases_path = Path(args.cases)
    all_cases = load_cases(cases_path)
    cases = filter_cases(all_cases, args.only_db, args.only_difficulty, args.limit_per_db)
    if not cases:
        print("no cases match the filters — nothing to do", file=sys.stderr)
        return 2

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    prev_path = previous_report(REPORTS_DIR)
    prev = parse_prev_metrics(prev_path) if prev_path else None

    sha = short_git_sha()
    started_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    report_path = REPORTS_DIR / f"{started_iso}-{sha}.md"

    print(f"running {len(cases)} cases against {backend} (concurrency={args.concurrency})")
    print(f"report -> {report_path.relative_to(ROOT)}")
    if prev_path:
        print(f"prev report: {prev_path.name}")
    print()

    completed: list[Result] = []

    def on_result(r: Result) -> None:
        completed.append(r)
        mark = "OK " if r.passed else "FAIL"
        sfx = f" soft:{len(r.soft_failures)}" if r.soft_failures else ""
        print(f"  [{mark}] {r.case.id:>8} ({r.case.database_id}) "
              f"rows={r.rows_count:<4} attempts={r.attempts} "
              f"{r.latency_ms:>5}ms  {r.failure_mode or 'pass'}{sfx}",
              flush=True)
        # Incremental snapshot — overwrite on every result so Ctrl-C
        # always leaves a valid (partial) report behind.
        write_report(report_path, backend, all_cases, completed, sha, started_iso, prev)

    try:
        asyncio.run(run_all(backend, cases, args.concurrency, args.pace_seconds, on_result))
    except KeyboardInterrupt:
        print("\ninterrupted — partial report written", file=sys.stderr)

    # Final write (in case the last on_result was racy — cheap insurance).
    write_report(report_path, backend, all_cases, completed, sha, started_iso, prev)

    h = headline(completed)
    print()
    print(f"=== {h['passed']}/{h['total']} passed ({h['rate']:.1f}%) "
          f"p50={h['p50_ms']}ms p95={h['p95_ms']}ms p99={h['p99_ms']}ms ===")
    print(f"report: {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
