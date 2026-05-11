import logging
import re
import time

from fastapi import APIRouter, HTTPException, status
from google.genai.errors import ClientError, ServerError

from app.core import agent, sessions
from app.models import QueryRequest, QueryResponse

router = APIRouter()
logger = logging.getLogger(__name__)


def _retry_seconds(detail_text: str) -> int | None:
    """Extract the suggested retry delay from a Gemini RESOURCE_EXHAUSTED body."""
    match = re.search(r"retry in ([\d.]+)s", detail_text)
    return int(float(match.group(1))) if match else None


@router.post("/query", response_model=QueryResponse)
def post_query(req: QueryRequest) -> QueryResponse:
    # Resolve or create a session BEFORE the agent runs so the response
    # always has a session_id, even on failure paths (router currently
    # returns errors, not partial responses — but the contract is cleaner).
    session_id = sessions.ensure_session(req.session_id, req.database_id)
    prior = sessions.recent_turns(session_id, n=2)

    started = time.perf_counter()
    try:
        result = agent.run(req.question, req.database_id, recent_turns=prior)
    except ValueError as e:
        # unknown database_id from build_prompt
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except agent.AgentError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "message": "agent failed to produce safe, executable SQL",
                "attempts": e.attempts,
                "errors": e.errors,
            },
        )
    except ClientError as e:
        # Gemini surfaced a 4xx — almost always a rate-limit / quota issue.
        if e.code == 429:
            retry_after = _retry_seconds(str(e))
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "message": (
                        "Gemini daily quota exhausted on the free tier. "
                        + (
                            f"Try again in ~{retry_after}s."
                            if retry_after
                            else "Try again later."
                        )
                    ),
                    "attempts": 0,
                    "errors": [f"upstream 429 from Gemini: quota exhausted"],
                },
                headers={"Retry-After": str(retry_after)} if retry_after else {},
            )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "message": f"upstream Gemini error: {e.code}",
                "attempts": 0,
                "errors": [str(e)[:400]],
            },
        )
    except ServerError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "message": "Gemini is temporarily unavailable. Try again in a moment.",
                "attempts": 0,
                "errors": [str(e)[:400]],
            },
        )

    latency_ms = int((time.perf_counter() - started) * 1000)

    # Persistence is best-effort: a Supabase blip after a successful agent
    # run must not fail the user's query. We log and move on.
    try:
        sessions.append_turn(
            session_id=session_id,
            question=req.question,
            sql=result.sql,
            rows_count=len(result.rows),
            attempts=result.attempts,
            latency_ms=latency_ms,
        )
    except Exception:  # noqa: BLE001 — intentional swallow, logged
        logger.exception("failed to persist turn for session %s", session_id)

    return QueryResponse(
        sql=result.sql,
        explanation=result.explanation,
        chart_hint=result.chart_hint,
        columns=result.columns,
        rows=[list(r) for r in result.rows],
        attempts=result.attempts,
        session_id=session_id,
    )
