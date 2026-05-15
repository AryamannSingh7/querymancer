import json

from fastapi.testclient import TestClient

from app.main import app
from app.models import ChartHint, LLMOutput

client = TestClient(app)


def _parse_ndjson(body: str) -> list[dict]:
    return [json.loads(line) for line in body.splitlines() if line.strip()]


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_query_rejects_unknown_database():
    r = client.post("/query", json={"question": "x", "database_id": "unknown"})
    assert r.status_code == 400
    detail = r.json()["detail"]
    assert "unknown" in detail.lower()
    assert "no schema" in detail.lower()


def test_query_validates_request():
    # missing required field
    r = client.post("/query", json={"question": "x"})
    assert r.status_code == 422


def test_query_returns_session_id_when_omitted(monkeypatch):
    """First turn: client omits session_id, server creates and returns one."""
    monkeypatch.setattr(
        "app.core.agent.llm.generate_sql",
        lambda prompt_text, system_instruction: LLMOutput(
            sql="SELECT CustomerID FROM Customers LIMIT 1",
            explanation="ok",
            chart_hint=ChartHint.table,
        ),
    )
    r = client.post("/query", json={"question": "list one", "database_id": "northwind"})
    assert r.status_code == 200
    body = r.json()
    assert isinstance(body["session_id"], str) and body["session_id"]


def test_query_degrades_gracefully_when_session_layer_down(monkeypatch):
    """If Supabase is unreachable, /query still answers (transient session, no persist)."""
    import psycopg

    def boom(*args, **kwargs):
        raise psycopg.OperationalError("DNS flap")

    # Make the *real* session helpers blow up — the router's wrapper
    # should catch this and fall back to a transient session.
    monkeypatch.setattr("app.routers.query.sessions.ensure_session", boom)
    monkeypatch.setattr("app.routers.query.sessions.recent_turns", boom)

    persisted: list[dict] = []
    def fake_append_turn(**kwargs):
        persisted.append(kwargs)
    monkeypatch.setattr("app.routers.query.sessions.append_turn", fake_append_turn)

    monkeypatch.setattr(
        "app.core.agent.llm.generate_sql",
        lambda prompt_text, system_instruction: LLMOutput(
            sql="SELECT CustomerID FROM Customers LIMIT 1",
            explanation="ok",
            chart_hint=ChartHint.table,
        ),
    )
    r = client.post("/query", json={"question": "list one", "database_id": "northwind"})
    assert r.status_code == 200
    body = r.json()
    assert body["session_id"]
    assert body["sql"].startswith("SELECT")
    # Persistence is skipped in transient-session mode — caller has no
    # session row to attach the turn to.
    assert persisted == []


def test_query_echoes_provided_session_id(monkeypatch):
    """Follow-up: client passes session_id; server echoes it back."""
    monkeypatch.setattr(
        "app.core.agent.llm.generate_sql",
        lambda prompt_text, system_instruction: LLMOutput(
            sql="SELECT CustomerID FROM Customers LIMIT 1",
            explanation="ok",
            chart_hint=ChartHint.table,
        ),
    )
    r = client.post(
        "/query",
        json={
            "question": "list one",
            "database_id": "northwind",
            "session_id": "abcd-1234",
        },
    )
    assert r.status_code == 200
    assert r.json()["session_id"] == "abcd-1234"


def test_query_stream_first_try_success(monkeypatch):
    monkeypatch.setattr(
        "app.core.agent.llm.generate_sql",
        lambda prompt_text, system_instruction: LLMOutput(
            sql="SELECT CustomerID FROM Customers LIMIT 1",
            explanation="ok",
            chart_hint=ChartHint.table,
        ),
    )
    r = client.post("/query/stream", json={"question": "list one", "database_id": "northwind"})
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/x-ndjson")
    events = _parse_ndjson(r.text)
    kinds = [e["event"] for e in events]
    assert kinds == ["attempt_started", "result"]
    assert events[0]["attempt"] == 1
    result = events[-1]
    assert result["session_id"]
    assert result["sql"].startswith("SELECT")
    assert result["attempts"] == 1
    assert result["chart_hint"] == "table"


def test_query_stream_emits_attempt_failed_then_result(monkeypatch):
    sequence = iter(
        [
            LLMOutput(sql="DROP TABLE Customers", explanation="bad", chart_hint=ChartHint.table),
            LLMOutput(
                sql="SELECT CustomerID FROM Customers LIMIT 1",
                explanation="ok",
                chart_hint=ChartHint.table,
            ),
        ]
    )
    monkeypatch.setattr(
        "app.core.agent.llm.generate_sql",
        lambda prompt_text, system_instruction: next(sequence),
    )
    r = client.post("/query/stream", json={"question": "list one", "database_id": "northwind"})
    assert r.status_code == 200
    events = _parse_ndjson(r.text)
    kinds = [e["event"] for e in events]
    assert kinds == ["attempt_started", "attempt_failed", "attempt_started", "result"]
    failed = events[1]
    assert failed["attempt"] == 1
    assert "safety" in failed["reason"]
    result = events[-1]
    assert result["attempts"] == 2


def test_query_stream_emits_error_event_when_agent_exhausted(monkeypatch):
    monkeypatch.setattr(
        "app.core.agent.llm.generate_sql",
        lambda prompt_text, system_instruction: LLMOutput(
            sql="DROP TABLE Customers", explanation="bad", chart_hint=ChartHint.table
        ),
    )
    r = client.post("/query/stream", json={"question": "x", "database_id": "northwind"})
    assert r.status_code == 200
    events = _parse_ndjson(r.text)
    kinds = [e["event"] for e in events]
    # 3 attempts, each with started+failed, then terminal error
    assert kinds.count("attempt_started") == 3
    assert kinds.count("attempt_failed") == 3
    assert kinds[-1] == "error"
    err = events[-1]
    assert err["kind"] == "agent_exhausted"
    assert err["attempts"] == 3
    assert err["session_id"]
