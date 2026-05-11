"""Self-correction agent loop.

One call to `agent.run` (or `run_iter`) does up to N rounds of:
  1. build prompt (with prior errors, if any)
  2. ask the LLM for SQL
  3. run safety.is_safe()
  4. inject row cap
  5. execute against the read-only DB

On any failure in steps 3-5, the verbatim error is appended to the error
history and we go back to step 1 with the next attempt. After `max_attempts`
rounds we give up and raise AgentError with the full error history so the
route can return a structured 422.

`run_iter` yields AgentEvent objects as the loop progresses — the
`/query/stream` endpoint serialises each one to an NDJSON line so the
frontend can render a live "self-correcting… attempt N of 3" status.

`run` is a thin wrapper that drains run_iter and returns the final result.
The synchronous `/query` endpoint and the unit tests use it.

Public surface:
  AgentResult — dataclass with sql, explanation, chart_hint, columns, rows, attempts
  AgentEvent  — frozen dataclass: kind in {attempt_started, attempt_failed, final}
  AgentError  — raised after max_attempts with all errors attached
  run(question, database_id, *, recent_turns=None, max_attempts=3) -> AgentResult
  run_iter(...) -> Iterator[AgentEvent]
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field

from app.core import executor, llm, prompt, safety
from app.core.sessions import TurnSnippet
from app.models import ChartHint


@dataclass
class AgentResult:
    sql: str
    explanation: str
    chart_hint: ChartHint
    columns: list[str] = field(default_factory=list)
    rows: list[tuple] = field(default_factory=list)
    attempts: int = 0


@dataclass(frozen=True)
class AgentEvent:
    """Single step in the self-correction loop.

    kind:
      - "attempt_started"  → loop is about to call the LLM for `attempt`
      - "attempt_failed"   → this attempt was rejected (safety or execute);
                             `reason` is a short human-readable string
      - "final"            → `result` holds the successful AgentResult
    """

    kind: str
    attempt: int = 0
    reason: str | None = None
    result: AgentResult | None = None


class AgentError(Exception):
    """Raised when the agent exhausts its retry budget."""

    def __init__(self, attempts: int, errors: list[str]):
        super().__init__(f"agent failed after {attempts} attempts: {errors[-1] if errors else ''}")
        self.attempts = attempts
        self.errors = errors


def run_iter(
    question: str,
    database_id: str,
    *,
    recent_turns: list[TurnSnippet] | None = None,
    max_attempts: int = 3,
) -> Iterator[AgentEvent]:
    """Generator version of `run`. Yields one AgentEvent per loop boundary.

    Raises AgentError after `max_attempts` failed iterations — the caller
    is expected to handle that or let it propagate.
    """
    errors: list[str] = []

    for attempt in range(1, max_attempts + 1):
        yield AgentEvent(kind="attempt_started", attempt=attempt)

        # build_prompt validates database_id; let its ValueError propagate.
        system_instruction, user_prompt = prompt.build_prompt(
            question,
            database_id,
            errors=errors or None,
            recent_turns=recent_turns,
        )

        resp = llm.generate_sql(prompt_text=user_prompt, system_instruction=system_instruction)
        sql = resp.sql

        ok, reason = safety.is_safe(sql)
        if not ok:
            short = f"safety: {reason}"
            errors.append(f"{short} | sql={sql!r}")
            yield AgentEvent(kind="attempt_failed", attempt=attempt, reason=short)
            continue

        capped_sql = safety.inject_limit(sql, limit=1000)

        try:
            exec_result = executor.execute_ro(database_id, capped_sql)
        except executor.ExecutionError as e:
            short = f"execute: {e}"
            errors.append(f"{short} | sql={sql!r}")
            yield AgentEvent(kind="attempt_failed", attempt=attempt, reason=short)
            continue

        yield AgentEvent(
            kind="final",
            attempt=attempt,
            result=AgentResult(
                sql=sql,
                explanation=resp.explanation,
                chart_hint=resp.chart_hint,
                columns=exec_result.columns,
                rows=exec_result.rows,
                attempts=attempt,
            ),
        )
        return

    raise AgentError(attempts=max_attempts, errors=errors)


def run(
    question: str,
    database_id: str,
    *,
    recent_turns: list[TurnSnippet] | None = None,
    max_attempts: int = 3,
) -> AgentResult:
    """Drain run_iter and return the final AgentResult.

    Maintained as the synchronous entry point — used by `/query`,
    `agent.run`-style smoke scripts, and most of the unit tests.
    """
    for event in run_iter(
        question,
        database_id,
        recent_turns=recent_turns,
        max_attempts=max_attempts,
    ):
        if event.kind == "final":
            assert event.result is not None  # mypy / runtime invariant
            return event.result

    # run_iter raises AgentError on exhaustion before falling off the end,
    # so this line should be unreachable. Keep it for type-checker sanity.
    raise AgentError(attempts=max_attempts, errors=[])
