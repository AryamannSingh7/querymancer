from fastapi.testclient import TestClient

from app.main import app
from app.models import ChartHint, LLMOutput

client = TestClient(app)


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
