from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_query_rejects_unknown_database():
    r = client.post("/query", json={"question": "x", "database_id": "unknown"})
    assert r.status_code == 400
    assert "northwind" in r.json()["detail"]


def test_query_validates_request():
    # missing required field
    r = client.post("/query", json={"question": "x"})
    assert r.status_code == 422
