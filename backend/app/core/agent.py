"""Self-correction agent loop.

One call to `agent.run` does up to N rounds of:
  1. build prompt (with prior errors, if any)
  2. ask the LLM for SQL
  3. run safety.is_safe()
  4. inject row cap
  5. execute against the read-only DB

On any failure in steps 3-5, the verbatim error is appended to the error
history and we go back to step 1 with the next attempt. After `max_attempts`
rounds we give up and raise AgentError with the full error history so the
route can return a structured 422.

Public surface:
  AgentResult — dataclass with sql, explanation, chart_hint, columns, rows, attempts
  AgentError  — raised after max_attempts with all errors attached
  run(question, database_id, *, max_attempts=3) -> AgentResult
"""

from __future__ import annotations

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


class AgentError(Exception):
    """Raised when the agent exhausts its retry budget."""

    def __init__(self, attempts: int, errors: list[str]):
        super().__init__(f"agent failed after {attempts} attempts: {errors[-1] if errors else ''}")
        self.attempts = attempts
        self.errors = errors


def run(
    question: str,
    database_id: str,
    *,
    recent_turns: list[TurnSnippet] | None = None,
    max_attempts: int = 3,
) -> AgentResult:
    errors: list[str] = []

    for attempt in range(1, max_attempts + 1):
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
            errors.append(f"safety: {reason} | sql={sql!r}")
            continue

        capped_sql = safety.inject_limit(sql, limit=1000)

        try:
            exec_result = executor.execute_ro(database_id, capped_sql)
        except executor.ExecutionError as e:
            errors.append(f"execute: {e} | sql={sql!r}")
            continue

        return AgentResult(
            sql=sql,
            explanation=resp.explanation,
            chart_hint=resp.chart_hint,
            columns=exec_result.columns,
            rows=exec_result.rows,
            attempts=attempt,
        )

    raise AgentError(attempts=max_attempts, errors=errors)
