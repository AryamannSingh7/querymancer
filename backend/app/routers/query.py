import json
import logging
import re
import time
import uuid
from collections.abc import Iterator

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from google.genai.errors import ClientError, ServerError

from app.core import agent, retriever, sessions
from app.core.ratelimit import RATE_LIMIT, limiter
from app.core.sessions import TurnSnippet
from app.models import QueryRequest, QueryResponse

router = APIRouter()
logger = logging.getLogger(__name__)


def _retry_seconds(detail_text: str) -> int | None:
    """Extract the suggested retry delay from a Gemini RESOURCE_EXHAUSTED body."""
    match = re.search(r"retry in ([\d.]+)s", detail_text)
    return int(float(match.group(1))) if match else None


def _resolve_session_safely(
    session_id: str | None, database_id: str
) -> tuple[str, list[TurnSnippet], bool]:
    """Resolve session + prior turns, degrading gracefully on Supabase outages.

    Returns (session_id, prior_turns, persistent). When `persistent` is False
    the session layer was unreachable — the caller has a synthetic session id
    so the response stays well-formed, but `append_turn` should be skipped
    (no Postgres → nothing to write to). Multi-turn context is lost for that
    request, which is the right tradeoff: a user-facing 200 with no history
    beats a 500 from a transient pooler DNS hiccup.
    """
    try:
        sid = sessions.ensure_session(session_id, database_id)
        prior = sessions.recent_turns(sid, n=2)
        return sid, prior, True
    except Exception:  # noqa: BLE001 — degraded mode, see docstring
        logger.exception(
            "session layer unavailable; falling back to transient session"
        )
        return str(uuid.uuid4()), [], False


@router.post("/query", response_model=QueryResponse)
@limiter.limit(RATE_LIMIT)
def post_query(request: Request, req: QueryRequest) -> QueryResponse:
    # `request` is unused here but required: slowapi's @limiter.limit reads
    # the client IP off it. Removing the param breaks the decorator.
    # Resolve or create a session BEFORE the agent runs so the response
    # always has a session_id, even on failure paths. If the session
    # layer is unreachable, fall back to a transient session (no
    # persistence this turn) rather than 500ing on a Supabase blip.
    session_id, prior, persistent = _resolve_session_safely(
        req.session_id, req.database_id
    )

    started = time.perf_counter()
    try:
        result = agent.run(req.question, req.database_id, recent_turns=prior)
    except ValueError as e:
        # unknown database_id from build_prompt
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except retriever.RetrieverUnavailable as e:
        # Supabase pgvector unreachable (transient pooler DNS flap) — the
        # retriever exhausted its retry budget. 503, not 500: it's retryable.
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "message": "Schema search is temporarily unavailable. Try again in a moment.",
                "attempts": 0,
                "errors": [str(e)[:400]],
            },
        )
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
    # run must not fail the user's query. We log and move on. We also
    # skip when running in transient-session mode (Supabase was already
    # known-down at session resolution time).
    if persistent:
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


def _ndjson(obj: dict) -> str:
    """Serialise a dict to one NDJSON line. Enums fall through to str."""
    return json.dumps(obj, default=str) + "\n"


@router.post("/query/stream")
@limiter.limit(RATE_LIMIT)
def post_query_stream(request: Request, req: QueryRequest) -> StreamingResponse:
    """Streaming sibling of /query.

    Emits NDJSON events as the self-correction loop progresses so the
    frontend can render a live "self-correcting… attempt N of 3" status:

      {"event":"attempt_started","attempt":1}
      {"event":"attempt_failed","attempt":1,"reason":"safety: ..."}
      {"event":"attempt_started","attempt":2}
      {"event":"result", "session_id": "...", "sql": "...", ...}

    On any terminal failure (unknown DB, agent exhausted, upstream
    Gemini error) we emit a single `error` event and close the stream
    cleanly — the HTTP status stays 200 because the response body has
    already started. The frontend distinguishes outcomes by event kind.

    Session resolution happens SYNCHRONOUSLY before streaming begins.
    A Supabase outage at that step degrades to a transient session
    (the stream still starts; persistence is skipped for that turn).
    """
    session_id, prior, persistent = _resolve_session_safely(
        req.session_id, req.database_id
    )

    def event_stream() -> Iterator[str]:
        started = time.perf_counter()
        try:
            for event in agent.run_iter(
                req.question, req.database_id, recent_turns=prior
            ):
                if event.kind == "final":
                    result = event.result
                    assert result is not None
                    latency_ms = int((time.perf_counter() - started) * 1000)
                    if persistent:
                        try:
                            sessions.append_turn(
                                session_id=session_id,
                                question=req.question,
                                sql=result.sql,
                                rows_count=len(result.rows),
                                attempts=result.attempts,
                                latency_ms=latency_ms,
                            )
                        except Exception:  # noqa: BLE001
                            logger.exception(
                                "failed to persist turn for session %s", session_id
                            )
                    yield _ndjson(
                        {
                            "event": "result",
                            "session_id": session_id,
                            "sql": result.sql,
                            "explanation": result.explanation,
                            "chart_hint": result.chart_hint.value,
                            "columns": result.columns,
                            "rows": [list(r) for r in result.rows],
                            "attempts": result.attempts,
                        }
                    )
                else:
                    payload = {
                        "event": event.kind,
                        "attempt": event.attempt,
                    }
                    if event.reason:
                        payload["reason"] = event.reason
                    yield _ndjson(payload)
        except ValueError as e:
            yield _ndjson(
                {
                    "event": "error",
                    "kind": "unknown_database",
                    "session_id": session_id,
                    "message": str(e),
                }
            )
        except retriever.RetrieverUnavailable as e:
            yield _ndjson(
                {
                    "event": "error",
                    "kind": "retriever_unavailable",
                    "session_id": session_id,
                    "message": "Schema search is temporarily unavailable. Try again in a moment.",
                    "errors": [str(e)[:400]],
                }
            )
        except agent.AgentError as e:
            yield _ndjson(
                {
                    "event": "error",
                    "kind": "agent_exhausted",
                    "session_id": session_id,
                    "message": "agent failed to produce safe, executable SQL",
                    "attempts": e.attempts,
                    "errors": e.errors,
                }
            )
        except ClientError as e:
            if e.code == 429:
                retry_after = _retry_seconds(str(e))
                yield _ndjson(
                    {
                        "event": "error",
                        "kind": "upstream_rate_limit",
                        "session_id": session_id,
                        "message": (
                            "Gemini daily quota exhausted on the free tier. "
                            + (
                                f"Try again in ~{retry_after}s."
                                if retry_after
                                else "Try again later."
                            )
                        ),
                        "retry_after": retry_after,
                    }
                )
            else:
                yield _ndjson(
                    {
                        "event": "error",
                        "kind": "upstream_error",
                        "session_id": session_id,
                        "message": f"upstream Gemini error: {e.code}",
                        "errors": [str(e)[:400]],
                    }
                )
        except ServerError as e:
            yield _ndjson(
                {
                    "event": "error",
                    "kind": "upstream_unavailable",
                    "session_id": session_id,
                    "message": "Gemini is temporarily unavailable. Try again in a moment.",
                    "errors": [str(e)[:400]],
                }
            )

    return StreamingResponse(event_stream(), media_type="application/x-ndjson")
